#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
motor_tendencias.py  —  Motor de "TENDENCIA" (pieza satírica), v2
© 2026 Alejandro Osuna Pacheco. Todos los derechos reservados.

Recoge lo que aparece AHORA en fuentes ABIERTAS (de España y del mundo) y lo
convierte en un "speech" de campaña, metiendo el término real dentro de la frase.
Escribe trends.json, que lee la obra (index.html) en la misma carpeta.

Coge lo primero que devuelven las fuentes; no exige que sea "trending".

Fuentes (todas públicas y pensadas para lectura por programas):
  - Google Trends  (RSS de varios países: ES, US, GB, MX, AR, FR, IT, DE, BR, JP)
  - Wikipedia      (artículos más vistos ayer, ediciones es y en — API pública)
  - Titulares RSS  (nacionales e internacionales; edita la lista a tu gusto)
  - Reddit         (r/es y r/popular — JSON público)

NO usa X, TikTok, Instagram ni Facebook: no abren sus tendencias y sacárselas
incumple sus términos. Quedan fuera a propósito.

Uso:
  python3 motor_tendencias.py                # genera trends.json una vez
  python3 motor_tendencias.py --loop 300     # lo regenera cada 300 s (en bucle)

Solo librería estándar. Sin dependencias.
"""

import json, re, sys, time, random, datetime, urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (TendenciaArtPiece/2.0; proyecto artistico; Alejandro Osuna Pacheco)"
TIMEOUT = 12
MAX_ITEMS = 140

# --- Fuentes (edítalas libremente) --------------------------------------
GT_GEOS = ["ES", "US", "GB", "MX", "AR", "FR", "IT", "DE", "BR", "JP"]
GT_RSS = "https://trends.google.com/trending/rss?geo={geo}"

WIKI_LANGS = ["es", "en"]
WIKI_TOP = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{y}/{m}/{d}"

MEDIOS_RSS = [
    "https://www.eldiario.es/rss/",
    "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "https://e00-elmundo.uecdn.es/elmundo/rss/internacional.xml",
    "https://e00-elmundo.uecdn.es/loc/rss/portada.xml",            # gente / corazón
    "https://www.20minutos.es/rss/gente-television/",
    "https://feeds.bbci.co.uk/mundo/rss.xml",                       # internacional (ES)
    "https://feeds.bbci.co.uk/news/world/rss.xml",                  # internacional (EN)
]

REDDIT = [
    "https://www.reddit.com/r/es/hot.json?limit=20",
    "https://www.reddit.com/r/popular.json?limit=25",               # mundial
]
# ------------------------------------------------------------------------


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def safe(fn, label):
    try:
        return fn()
    except Exception as e:
        print(f"  [aviso] {label} no disponible: {e}", file=sys.stderr)
        return []


def from_google_trends():
    out = []
    for geo in GT_GEOS:
        try:
            root = ET.fromstring(fetch(GT_RSS.format(geo=geo)))
            for item in list(root.iter("item"))[:8]:
                t = item.findtext("title")
                if t:
                    out.append((t.strip(), f"Google Trends {geo}"))
        except Exception as e:
            print(f"  [aviso] Trends {geo} falló: {e}", file=sys.stderr)
    return out


def from_wikipedia():
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    out = []
    for lang in WIKI_LANGS:
        try:
            url = WIKI_TOP.format(lang=lang, y=ayer.year, m=f"{ayer.month:02d}", d=f"{ayer.day:02d}")
            data = json.loads(fetch(url).decode("utf-8"))
            for a in data["items"][0]["articles"][:25]:
                name = a["article"].replace("_", " ")
                if name.startswith(("Especial:", "Wikipedia:", "Special:", "Portada", "Main Page")):
                    continue
                out.append((name, f"Wikipedia {lang}"))
        except Exception as e:
            print(f"  [aviso] Wikipedia {lang} falló: {e}", file=sys.stderr)
    return out


def from_medios():
    out = []
    for feed in MEDIOS_RSS:
        try:
            root = ET.fromstring(fetch(feed))
            for item in list(root.iter("item"))[:8]:
                t = item.findtext("title")
                if t:
                    out.append((t.strip(), "titulares"))
        except Exception as e:
            print(f"  [aviso] RSS {feed} falló: {e}", file=sys.stderr)
    return out


def from_reddit():
    out = []
    for url in REDDIT:
        try:
            data = json.loads(fetch(url).decode("utf-8"))
            for c in data["data"]["children"]:
                t = c["data"].get("title")
                if t:
                    out.append((t.strip(), "Reddit"))
        except Exception as e:
            print(f"  [aviso] Reddit falló: {e}", file=sys.stderr)
    return out


# --- Convertir cualquier cosa en discurso de campaña --------------------
# Regla: el partido es el sujeto del disparate; el término «{t}» es solo el
# objeto. Nunca se le atribuyen declaraciones a una persona real.
PLANTILLAS = [
    # promesa vacía
    'Lo que España pide hoy es «{t}». Nosotros lo garantizamos.',
    '«{t}» será gratis para todas las familias antes de Navidad.',
    'Crearemos un Ministerio de «{t}», con partida propia.',
    '«{t}» para todos. Sin letra pequeña. Sin excusas.',
    'Escuchamos a la calle: «{t}» es ahora nuestra máxima prioridad.',
    'Declararemos «{t}» fiesta nacional a partir de hoy.',
    'Reparto gratuito de «{t}» en cada hogar antes del viernes.',
    'Renombraremos una calle de cada ciudad como «{t}».',
    'Si «{t}» existe, «{t}» ya está en nuestro programa.',
    # campaña 29-N / bloqueo
    'Si nos votáis el 29 de noviembre, «{t}» saldrá por decreto.',
    'Frente al bloqueo, «{t}». Frente al ruido, «{t}».',
    'Esto no va de izquierdas o de derechas: va de «{t}».',
    'Pediremos un pacto de Estado por «{t}». Nadie lo firmará. Da igual.',
    'Nos acusan de no tener programa. Tenemos «{t}».',
    '«{t}» es culpa del Gobierno anterior. Y del siguiente.',
    'Los españoles de bien ya han elegido: «{t}».',
    '¿Vivienda? Mañana. Hoy toca «{t}».',
    'Bajaremos los impuestos a «{t}» y se los subiremos a lo que no sea tendencia.',
    'Ni un paso atrás en «{t}». Hasta que deje de ser tendencia.',
    'Llevaremos «{t}» a Bruselas, al Supremo y a todas las tertulias.',
    'Tenemos un plan para «{t}». Lo presentaremos después de las elecciones.',
]

# Cuando el término es una desgracia, el partido también la aprovecha.
# Es la parte más dura de la crítica: la tragedia convertida en contenido.
PLANTILLAS_LUTO = [
    'Un minuto de silencio por «{t}». Y ahora, a lo nuestro.',
    'Lamentamos profundamente «{t}». Nuestro programa no cambia.',
    '«{t}»: lo usaremos en campaña con todo el respeto.',
    'Nuestro más sentido pésame por «{t}». Suscríbete para más.',
]
LUTO = re.compile(r"muert|muere|murió|fallec|asesin|víctima|victim|tragedia|killed|dead|death|dies|died|"
                  r"desaparec|missing|herid|injur|atentado|attack|bombard|masacre|massacre|desahuc|incendio|ablaze|"
                  r"inundaci|flood|terremoto|earthquake|guerra|war\b", re.I)


def limpiar(term):
    term = re.sub(r"\s+", " ", term).strip().rstrip(".!?:;,")
    term = term.replace("«", "").replace("»", "").replace('"', "'")
    if len(term) > 70:
        corto = re.split(r"[:–—]| - ", term)[0].strip()
        if len(corto) > 70 or len(corto) < 12:
            corto = term[:70].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        term = corto
    return term


def a_discurso(term):
    t = limpiar(term)
    banco = PLANTILLAS_LUTO if LUTO.search(term) else PLANTILLAS
    return random.choice(banco).format(t=t), banco is PLANTILLAS_LUTO


def recolectar():
    bruto = []
    bruto += safe(from_google_trends, "Google Trends")
    bruto += safe(from_wikipedia, "Wikipedia")
    bruto += safe(from_medios, "medios RSS")
    bruto += safe(from_reddit, "Reddit")

    vistos, items = set(), []
    for term, source in bruto:
        clave = limpiar(term).lower()
        if not clave or clave in vistos or len(clave) < 3:
            continue
        vistos.add(clave)
        speech, luto = a_discurso(term)
        items.append({"term": limpiar(term), "source": source, "speech": speech, "luto": luto})
    random.shuffle(items)
    return items[:MAX_ITEMS]


def escribir(path="trends.json"):
    items = recolectar()
    if not items:
        # Si todas las fuentes fallan, no se borra el discurso anterior.
        print("Ninguna fuente respondió; se conserva trends.json", file=sys.stderr)
        return
    payload = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(items),
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"trends.json actualizado · {len(items)} entradas · {payload['updated']}")


if __name__ == "__main__":
    loop = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[1] == "--loop" else None
    while True:
        escribir()
        if not loop:
            break
        time.sleep(loop)
