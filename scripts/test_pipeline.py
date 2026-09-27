"""Prueba offline del pipeline: fixtures locales, sin red y determinista.

Comprueba lo que fetch.py hace de verdad: parseo de RSS 2.0 y Atom, normalizacion
de URL, deduplicacion, cache por hash y deteccion de fechas imposibles.

    python3 scripts/test_pipeline.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import fetch  # noqa: E402
import metadatos as M  # noqa: E402

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Prueba RSS</title>
    <item>
      <title>Typeform levanta 100 M$</title>
      <link>https://www.ejemplo.com/a/uno?utm_source=twitter</link>
      <pubDate>Fri, 25 Sep 2026 09:00:00 +0200</pubDate>
      <dc:creator>Reuters</dc:creator>
      <description>La startup espanola cierra ronda.</description>
    </item>
    <item>
      <title>Nota con fecha imposible</title>
      <link>https://www.ejemplo.com/a/dos</link>
      <pubDate>Sat, 01 Jan 2028 09:00:00 +0100</pubDate>
      <description>Publicado el 1 de enero de 2028.</description>
    </item>
    <item>
      <title>Mismo articulo, otra URL</title>
      <link>https://www.ejemplo.com/a/uno/</link>
      <pubDate>Fri, 25 Sep 2026 09:00:00 +0200</pubDate>
      <description>Duplicado con redireccion.</description>
    </item>
    <item>
      <title>Sin enlace</title>
      <description>No debe aparecer.</description>
    </item>
  </channel>
</rss>
"""

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Prueba Atom</title>
  <entry>
    <title>Multiverse entra en el programa europeo</title>
    <link href="https://ejemplo.org/atom/uno"/>
    <published>2026-09-20T12:00:00Z</published>
    <summary>Deeptech espanola en un programa europeo.</summary>
  </entry>
  <entry>
    <title>Entrada sin fecha</title>
    <link href="https://ejemplo.org/atom/dos"/>
    <summary>Sin published ni updated.</summary>
  </entry>
</feed>
"""

HTML = """<html><head><title>Pagina de prueba</title>
<meta property="og:site_name" content="Medio de Prueba">
<meta property="article:published_time" content="2026-09-27T11:00:00+02:00">
</head><body><nav>MENU QUE NO DEBE APARECER</nav>
<article><p>Contenido en espanol de la empresa sobre inteligencia artificial
y el mercado deEtiquetaspublico nacional.</p></article>
<footer>PIE QUE NO DEBE APARECER</footer></body></html>"""

ok = fallos = 0


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    global ok, fallos
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallos += 1
        print(f"  FAIL {nombre}  {detalle}")


print("1. RSS 2.0")
rss = fetch.parsear_feed(RSS, "https://www.ejemplo.com/rss")
check("descarta la entrada sin enlace", len(rss) == 3, f"hay {len(rss)}")
check("medio viene del canal", rss[0]["medio"] == "Prueba RSS", rss[0]["medio"])
check("fecha RFC822", rss[0]["fecha"] == "2026-09-25", str(rss[0]["fecha"]))
check("autor via dc:creator", rss[0]["autor"] == "Reuters", str(rss[0]["autor"]))
check("quita utm de la URL", rss[0]["url"] == "https://ejemplo.com/a/uno", rss[0]["url"])
check("via = feed", rss[0]["vía"] == "feed")

print("2. Atom")
atom = fetch.parsear_feed(ATOM, "https://ejemplo.org/atom")
check("dos entradas", len(atom) == 2, f"hay {len(atom)}")
check("lee href del link", atom[0]["url"] == "https://ejemplo.org/atom/uno", atom[0]["url"])
check("fecha ISO en published", atom[0]["fecha"] == "2026-09-20", str(atom[0]["fecha"]))
check("entrada sin fecha -> None", atom[1]["fecha"] is None, str(atom[1]["fecha"]))

print("3. Deduplicacion")
todos = rss + atom
uniq = fetch.deduplicar(todos)
check("colapsa la URL duplicada", len(uniq) == 4, f"quedan {len(uniq)} de {len(todos)}")
uno = [r for r in uniq if r["url"] == "https://ejemplo.com/a/uno"]
check("la duplicada se funde en una", len(uno) == 1, f"quedan {len(uno)}")

print("4. HTML")
m = M.extraer(HTML, "https://www.ejemplo.com/pagina")
check("titulo", m["titulo"] == "Pagina de prueba", str(m["titulo"]))
check("medio", m["medio"] == "Medio de Prueba", str(m["medio"]))
check("fecha de article:published_time", m["fecha"] == "2026-09-27", str(m["fecha"]))
check("idioma es", m["idioma"] == "es", str(m["idioma"]))
check("quita nav", "MENU QUE NO" not in m["texto"])
check("quita footer", "PIE QUE NO" not in m["texto"])

print("5. Fechas imposibles")
check("detecta fecha futura", M.inconsistente("2028-01-01", "2026-09-28") == "fecha_futura")
check("detecta antiguedad", M.inconsistente("2016-01-01", "2026-09-28") == "antigua")
check("acepta fecha buena", M.inconsistente("2026-09-27", "2026-09-28") is None)
check("senalara sin_fecha", M.inconsistente(None, "2026-09-28") == "sin_fecha")

print("6. Cache por hash")
shutil.rmtree(RAIZ / "datos" / "cache", ignore_errors=True)
C = RAIZ / "datos" / "cache-test"
fetch.CACHE = C
url = "https://www.ejemplo.com/pagina?utm_campaign=abc"
reg = {"url": M.canonical(url), "hash": M.hash_url(url), "fecha": "2026-09-27",
       "texto": "x", "via_cache": False}
fetch.escribir_cache(url, reg)
otra = "https://www.Ejemplo.com//pagina/"
c = fetch.leer_cache(otra)
check("misma pagina con otra forma de URL cae en la misma cache", c is not None)
check("la entrada de cache se marca como tal",
      (fetch.leer_cache(url) or {}).get("fecha") == "2026-09-27")
shutil.rmtree(C, ignore_errors=True)

print("7. Config")
cfg = json.loads((RAIZ / "config" / "verticales.json").read_text(encoding="utf-8"))
check("6 verticales", len(cfg["verticales"]) == 6, str(len(cfg["verticales"])))
check("4 campos", len(cfg["campos"]) == 4, str(len(cfg["campos"])))
sem = json.loads((RAIZ / "config" / "semilla-espana.json").read_text(encoding="utf-8"))
nodos = [x for g in sem["nodos"].values() for x in g]
check("la semilla tiene nodos", len(nodos) > 20, str(len(nodos)))

# Invariante de AGENTS.md: verificado=true exige URL, fecha de verificacion y
# constancia de que la entidad existe. Un nodo sin una de las tres cosas es falso
# por construccion, aunque el JSON diga lo que diga.
sin_url = [x["nombre"] for x in nodos if x.get("verificado") and not x.get("url")]
check("todo nodo verificado tiene url", not sin_url, ", ".join(sin_url))
sin_fecha = [x["nombre"] for x in nodos if x.get("verificado") and not x.get("verificado_el")]
check("todo nodo verificado tiene fecha", not sin_fecha, ", ".join(sin_fecha))
sin_metodo = [x["nombre"] for x in nodos if x.get("verificado") and not x.get("metodo_verificacion")]
check("todo nodo verificado dice como se comprobó", not sin_metodo, ", ".join(sin_metodo))
malos = [x["nombre"] for x in sem.get("verificacion", {}).get("no_encontrados", []) if x.get("verificado")]
check("lo no encontrado sigue sin verificar", not malos, ", ".join(malos))

print(f"\n{ok} ok, {fallos} fallos")
raise SystemExit(1 if fallos else 0)
