#!/usr/bin/env python3
"""Descarga y normaliza fuentes a un fichero JSON de evidencia.

Dos rutas de red, con reglas distintas (ADR-006):

  --feed  RSS/Atom. Es la via para lo recurrente (reguladores, medios
          sectoriales). Trae fecha y medio ya resueltos por el feed, que es
          informacion mas fiable que la que se puede sacar del HTML.

  --url   HTML suelto. Es la via para lo puntual (una empresa, un evento). El
          agente llega aqui con websearch/webfetch; este script sirve para
          dejar el resultado con metadatos normalizados y cacheado.

Y tres rutas de fichero local, para el dominio laboral (ADR-007). No van a la
red, asi que no se cachean: son la base de conocimiento que se entrega en un
.zip, y su contenido no cambia hasta que cambie el fichero.

  --csv  Exportacion de ofertas de un portal de empleo. Una fila = una
         oferta, con sus campos estructurados en `datos`.
  --pdf  Informe en PDF (OSIMGA, Gartner, WEF). Texto plano o nada: si es
         una imagen escaneada, se dice, no se devuelve binario como texto.
  --transcript  Transcripcion de una charla (.vtt, .srt, .txt). El agente la
         consigue de YouTube o de la organizacion; aqui solo se limpia.
  --youtube  URL de YouTube: intenta los subtitulos automaticos. Si no los hay,
         falla con el motivo y se pasa a --transcript.

Cache por hash de URL canonica (ADR-004). Re-correr el golden set no vuelve a
pedir nada a la red, y el resultado no depende de que la fuente siga viva.

Uso:
  python3 scripts/fetch.py --feed URL_Feed [--feed ...] --salida datos/x.json
  python3 scripts/fetch.py --url  URL_HTML  [--url ...]  --salida datos/x.json
  python3 scripts/fetch.py --url URL --sin-cache            # fuerza red
  python3 scripts/fetch.py --dump-cache                     # inspecciona

  python3 scripts/fetch.py --csv ofertas.csv --salida datos/l1/evidencia.json
  python3 scripts/fetch.py --pdf informe.pdf --fecha 2026-05-12 \\
                           --salida datos/l1/evidencia.json
  python3 scripts/fetch.py --transcript charla.vtt --canal "Devoxx" \\
                           --fecha 2026-06-10 --salida datos/l1/evidencia.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree.ElementTree import ParseError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metadatos as M  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "datos" / "cache"
ESQUEMA = RAIZ / "config" / "mercado-laboral.json"

UA = "Mozilla/5.0 (compatible; analisis-sector/1.0; +estudio academico)"
ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"


def _get(url: str, timeout: int) -> tuple[str | None, str | None]:
    """Devuelve (cuerpo, error). Nunca lanza: una fuente caida no tumba la corrida."""
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es,en;q=0.8",
    })
    try:
        with urlopen(req, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(charset, errors="replace"), None
    except HTTPError as e:
        return None, f"HTTP {e.code}"
    except (URLError, TimeoutError, OSError) as e:
        return None, f"{type(e).__name__}: {e}"


def _texto_feed(el) -> str:
    """Saca el texto de un elemento de feed, priorizando content:encoded."""
    for tag in (CONTENT + "encoded", ATOM + "content", "description", "summary"):
        hijo = el.find(tag)
        if hijo is not None:
            if len(hijo):
                bruto = "".join(hijo.itertext())
            else:
                bruto = (hijo.text or "")
            if bruto and bruto.strip():
                return bruto.strip()
    return ""


def _campo_feed(el, *nombres) -> str | None:
    if el is None:
        return None
    for n in nombres:
        v = el.findtext(n)
        if v and v.strip():
            return v.strip()
    return None


def parsear_feed(xml: str, origen: str) -> list[dict]:
    """RSS 2.0 o Atom -> entradas normalizadas. Tolera feeds mal formados."""
    try:
        root = ET.fromstring(xml.strip())
    except ParseError as e:
        return [{"url": origen, "error": f"feed_malformado: {e}", "hash": M.hash_url(origen)}]

    entradas = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    medio_feed = (_campo_feed(root.find("channel"), "title")
                  or _campo_feed(root, f"{ATOM}title")
                  or M.dominio(origen))

    out = []
    for it in entradas:
        url = (_campo_feed(it, "link", f"{ATOM}link")
               or _campo_feed(it, "guid", f"{ATOM}id"))
        if not url or not url.startswith("http"):
            href = it.find(f"{ATOM}link")
            url = href.get("href") if href is not None else None
        if not url or not url.startswith("http"):
            continue

        fecha = M.parse_fecha(
            _campo_feed(it, "pubDate", f"{ATOM}published", f"{ATOM}updated",
                        f"{DC}date")
        )
        crudo = _texto_feed(it)
        titulo = _campo_feed(it, "title", f"{ATOM}title") or ""
        cuerpo = M.a_texto(crudo) if "<" in crudo else crudo

        out.append({
            "url": M.canonical(url),
            "hash": M.hash_url(url),
            "dominio": M.dominio(url),
            "titulo": titulo or None,
            "medio": medio_feed,
            "fecha": fecha,
            "autor": _campo_feed(it, "author", f"{DC}creator", f"{ATOM}author/{ATOM}name"),
            "descripcion": M.resumen({"texto": cuerpo}, 320) or None,
            "texto": cuerpo[:20000],
            "idioma": M.idioma(cuerpo or titulo),
            "canonical": None,
            "origen": origen,
            "vía": "feed",
            "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "error": None,
        })
    return out


# --------------------------------------------------------------------------
# Rutas de fichero local (dominio laboral, ADR-007)
# --------------------------------------------------------------------------

# Una fuente sin URL propia no se descarta: se le da una clave local estable
# `archivo:<nombre>#<detalle>`. La cita [E01] resuelve contra esa clave igual que
# contra una URL, y `evaluar.py` la acepta en la columna del registro.
PREFIXO_LOCAL = "archivo:"


def clave_local(nombre: str, detalle: str = "") -> str:
    return f"{PREFIXO_LOCAL}{nombre}" + (f"#{detalle}" if detalle else "")


def hash_texto(clave: str, n: int = 16) -> str:
    """Hash de una clave que no es URL. `M.hash_url` no sirve: canonical()
    descarta el fragmento y dos filas distintas del mismo CSV colisionarian."""
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()[:n]


def _sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _normaliza_cabecera(s: str) -> str:
    """'Fecha de publicación' -> 'fecha_de_publicacion'.

    Sin acentos, en minusculas y con espacios y guiones como separador. Asi el
    mapa de config se escribe como lo escribe la gente ('razon social') y
    funciona igual ('razón_social', 'razon-social').
    """
    s = _sin_acentos(s or "").strip().lower()
    return re.sub(r"[\s\-/.]+", "_", s)


def _lee_texto_flexible(p: Path) -> str:
    """CSV exportado desde Excel en Espana suele venir en cp1252 o latin-1."""
    bruto = p.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return bruto.decode(enc)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="replace")


def _delimitador(primera_linea: str) -> str:
    return ";" if primera_linea.count(";") > primera_linea.count(",") else ","


NUM = r"(\d{1,3}(?:[.\s]\d{3})*|\d+)"
RANGO_SALARIO = re.compile(NUM + r"\s*(?:-|–|—|a|hasta)\s*" + NUM, re.I)
SALARIO_SUELTO = re.compile(NUM + r"(?=\s*(?:eur|euros|€))", re.I)
ANUAL = re.compile(r"(?:/|por\s+|al\s+)?(?:a[nñ]o|anual|anualmente)", re.I)
MENSUAL = re.compile(r"(?:/|por\s+|al\s+)?(?:mes|mensual)", re.I)
BRUTO = re.compile(r"bruto", re.I)
NETO = re.compile(r"neto", re.I)


def _a_numero(s: str) -> float | None:
    try:
        return float(re.sub(r"[.\s]", "", s).replace(",", "."))
    except ValueError:
        return None


def _salario(texto: str) -> dict | None:
    """Salario publicado en una oferta -> datos estructurados, o None.

    Deliberadamente conservador: si no encuentra una cifra explicita en EUR, no
    inventa una. Devolver None es un resultado valido; devolver 0 no lo es.
    """
    if not texto:
        return None
    t = _sin_acentos(texto)
    tiene_moneda = bool(re.search(r"eur|euros|€", t, re.I))
    m = RANGO_SALARIO.search(t)
    periodicidad = "mes" if MENSUAL.search(t) else ("ano" if ANUAL.search(t) else None)
    out = {"texto": texto.strip(), "min": None, "max": None,
           "periodicidad": periodicidad, "bruto": None}
    if m:
        lo, hi = _a_numero(m.group(1)), _a_numero(m.group(2))
        if lo and hi and lo <= hi:
            out["min"], out["max"] = lo, hi
        elif lo:
            out["min"] = lo
    elif tiene_moneda:
        m2 = SALARIO_SUELTO.search(t)
        if m2:
            v = _a_numero(m2.group(1))
            if v:
                out["min"] = v
    if out["min"] is None and out["max"] is None:
        return None if not tiene_moneda else out
    if BRUTO.search(t):
        out["bruto"] = True
    elif NETO.search(t):
        out["bruto"] = False
    return out


def parsear_csv(ruta: Path, esquema: dict | None = None) -> list[dict]:
    """Una fila = una oferta. Los campos van en `datos`, el texto en `texto`.

    El mapa de cabeceras vive en config/mercado-laboral.json, no aqui: cambiar
    la lista de portales no es cambiar el script (ADR-007).
    """
    mapa = ((esquema or {}).get("csv") or {}).get("columnas", {})
    invertida: dict[str, str] = {}
    for canonico, alias in mapa.items():
        for a in alias:
            invertida.setdefault(_normaliza_cabecera(a), canonico)

    texto = _lee_texto_flexible(ruta)
    lineas = texto.splitlines()
    if not lineas:
        return [{"url": clave_local(ruta.name), "error": "csv_vacio",
                 "hash": hash_texto(clave_local(ruta.name))}]
    leitor = csv.DictReader(lineas, delimiter=_delimitador(lineas[0]))
    registros = []
    for i, fila in enumerate(leitor, 1):
        if not any((v or "").strip() for v in fila.values()):
            continue
        datos: dict = {}
        for cabecera, valor in fila.items():
            if valor is None:
                continue
            v = valor.strip()
            if not v:
                continue
            canonico = invertida.get(_normaliza_cabecera(cabecera or ""), "")
            if canonico:
                datos[canonico] = v
        url = datos.get("url") or ""
        if not url.startswith("http"):
            url = clave_local(ruta.name, str(i))
        salari = _salario(datos.get("salario_texto") or "")
        if salari and (salari["min"] or salari["max"]):
            # El rango explicito manda sobre la cifra suelta, siempre que haya.
            for campo in ("salario_min", "salario_max"):
                if datos.get(campo):
                    v = _a_numero(re.sub(r"[^\d.,]", "", datos[campo]) or "")
                    if v is not None:
                        salari["min" if campo == "salario_min" else "max"] = v
        if salari:
            datos["salario_eur"] = salari
        fecha = M.parse_fecha(datos.get("fecha"))
        denominacion = datos.get("denominacion") or "Oferta sin denominacion"
        empresa = datos.get("empresa")
        descripcion = datos.get("descripcion") or ""
        cuerpo = "\n".join(filter(None, [
            f"Puesto: {denominacion}",
            f"Empresa: {empresa}" if empresa else "",
            f"Familia: {datos.get('familia')}" if datos.get("familia") else "",
            f"Salario publicado: {salari['texto']}" if salari else "",
            f"Experiencia: {datos.get('experiencia')}" if datos.get("experiencia") else "",
            f"Modalidad: {datos.get('modalidad')}" if datos.get("modalidad") else "",
            f"Ubicacion: {datos.get('ubicacion')}" if datos.get("ubicacion") else "",
            f"Stack declarado: {datos.get('stack')}" if datos.get("stack") else "",
            descripcion,
        ]))
        nota = None
        if not fecha:
            nota = "sin_fecha"
        registros.append({
            "url": M.canonical(url) if url.startswith("http") else url,
            "hash": M.hash_url(url) if url.startswith("http") else hash_texto(url),
            "dominio": M.dominio(url) if url.startswith("http") else ruta.stem,
            "titulo": f"{denominacion} ({empresa})" if empresa else denominacion,
            "medio": datos.get("medio") or ruta.stem,
            "fecha": fecha,
            "autor": None,
            "descripcion": M.resumen({"texto": cuerpo}, 320) or None,
            "texto": cuerpo[:20000],
            "idioma": M.idioma(cuerpo),
            "canonical": None,
            "origen": str(ruta),
            "vía": "csv",
            "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "error": None,
            "via_cache": False,
            "datos": datos,
            "notas": [nota] if nota else [],
        })
    return registros


def texto_pdf(ruta: Path) -> tuple[str | None, str | None]:
    """PDF -> texto. Devuelve (texto, error) y nunca lanza.

    Tres salidas posibles, y las tres son informacion: texto, "es una imagen
    escaneada" o "no hay extractor en esta maquina". Lo que no hace es
    devolver los bytes del PDF como si fueran texto: eso fue lo que ensucio la
    corrida del 2026-09-28 (motivo_descartes: texto_binario_pdf).
    """
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        pass
    else:
        try:
            p = PdfReader(str(ruta))
            texto = "\n".join((pg.extract_text() or "") for pg in p.pages)
        except Exception as exc:
            return None, f"pdf_ilegible: {type(exc).__name__}: {exc}"
        if _parece_binario(texto):
            return None, "pdf_texto_binario: escaneado sin capa de texto. Requiere OCR."
        return texto, None

    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-q", "-layout", str(ruta), "-"],
                               capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            return None, f"pdf_ilegible: {type(exc).__name__}: {exc}"
        texto = r.stdout.decode("utf-8", errors="replace")
        if not texto.strip():
            return None, "pdf_texto_binario: pdftotext no extrajo texto. Requiere OCR."
        return texto, None

    return None, ("pdf_sin_extractor: instala pypdf (pip install pypdf) o "
                  "poppler-utils. Hasta entonces el PDF no es citable.")


def _parece_binario(texto: str) -> bool:
    if not texto:
        return True
    muestra = texto[:4000]
    controls = sum(1 for ch in muestra if ord(ch) < 32 and ch not in "\n\r\t")
    return controls / max(len(muestra), 1) > 0.02


def registro_local(ruta: Path, texto: str, medio: str, fecha: str | None,
                   vía: str, datos: dict | None = None,
                   notas: list[str] | None = None) -> dict:
    cuerpo = texto or ""
    return {
        "url": clave_local(ruta.name),
        "hash": hash_texto(clave_local(ruta.name)),
        "dominio": ruta.stem,
        "titulo": ruta.stem,
        "medio": medio,
        "fecha": fecha,
        "autor": None,
        "descripcion": M.resumen({"texto": cuerpo}, 320) or None,
        "texto": cuerpo[:20000],
        "idioma": M.idioma(cuerpo),
        "canonical": None,
        "origen": str(ruta),
        "vía": vía,
        "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "error": None,
        "via_cache": False,
        "datos": datos or {},
        "notas": notas or [],
    }


TIMELINE = re.compile(r"^\s*(\d{2}:)?\d{2}:\d{2}[.,]\d{2,3}\s*-->")
CUERPO_VTT = re.compile(r"<[^>]+>")


def limpiar_transcripcion(bruto: str) -> str:
    """VTT/SRT -> prosa. Sin esto el modelo lee 400 lineas de marcas de tiempo."""
    lineas, out = bruto.splitlines(), []
    for linea in lineas:
        s = linea.strip()
        if not s or s.upper().startswith(("WEBVTT", "KIND:", "LANGUAGE:", "NOTE")):
            continue
        if s.isdigit() or TIMELINE.match(s):
            continue
        s = CUERPO_VTT.sub("", s)
        s = re.sub(r"\[(música|aplauso|music|applause|sonido)[^\]]*\]", "", s, flags=re.I)
        out.append(s.strip())
    texto = " ".join(out)
    return re.sub(r"\s+", " ", texto).strip()


def id_youtube(valor: str) -> str | None:
    v = valor.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", v):
        return v
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})", v)
    return m.group(1) if m else None


def subtitulos_youtube(video: str, timeout: int) -> tuple[str | None, dict]:
    """YouTube -> transcripcion. (texto, datos) con datos = medio, fecha, canal.

    Falla a menudo y por razones que no son culpa del script: el video puede no
    tener subtitulos, estar restringido por edad o por pais, o la pagina puede
    pedir JavaScript. Por eso devuelve el motivo en vez de tirar la corrida.
    """
    vid = id_youtube(video)
    if not vid:
        return None, {"error": "youtube_url_invalida: no se reconoce el id del video"}
    html, err = _get(f"https://www.youtube.com/watch?v={vid}", timeout)
    if err:
        return None, {"error": f"youtube_pagina: {err}"}
    fecha = None
    m = re.search(r'"(?:uploadDate|datePublished)":"([0-9]{4}-[0-9]{2}-[0-9]{2})', html)
    if m:
        fecha = m.group(1)
    canal = None
    m = re.search(r'"(?:ownerChannelName|author)":"([^"]{1,80})"', html)
    if m:
        canal = m.group(1)
    tracks = re.search(r'"captionTracks":(\[.*?\])', html)
    if not tracks:
        return None, {"error": "youtube_sin_subtitulos: el video no expone subtitulos "
                               "automaticos. Descarga la transcripcion y usa --transcript.",
                      "fecha": fecha, "canal": canal, "video": vid}
    try:
        lista = json.loads(tracks.group(1).replace("\\u0026", "&"))
    except json.JSONDecodeError:
        return None, {"error": "youtube_subtitulos_ilegibles: no se pudo leer captionTracks",
                      "fecha": fecha, "canal": canal, "video": vid}
    elegido = next((t for t in lista if t.get("languageCode", "").startswith("es")), None) \
        or (lista[0] if lista else None)
    if not elegido:
        return None, {"error": "youtube_sin_subtitulos: captionTracks vacio",
                      "fecha": fecha, "canal": canal, "video": vid}
    cuerpo, err = _get(urljoin("https://www.youtube.com", elegido["baseUrl"]), timeout)
    if err:
        return None, {"error": f"youtube_subtitulos: {err}", "fecha": fecha,
                      "canal": canal, "video": vid}
    return cuerpo, {"fecha": fecha, "canal": canal, "video": vid,
                    "idioma_subtitulos": elegido.get("languageCode")}


def cache_path(url: str) -> Path:
    return CACHE / f"{M.hash_url(url)}.json"


def leer_cache(url: str) -> dict | None:
    p = cache_path(url)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return d if d.get("url") else None


def escribir_cache(url: str, registro: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path(url).write_text(
        json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def obtener(url: str, timeout: int, usar_cache: bool, via: str) -> dict:
    """Un registro de evidencia, de cache o de red."""
    if usar_cache:
        c = leer_cache(url)
        if c:
            c["via_cache"] = True
            return c

    cuerpo, err = _get(url, timeout)
    if err:
        reg = {
            "url": M.canonical(url), "hash": M.hash_url(url),
            "dominio": M.dominio(url), "titulo": None, "medio": None,
            "fecha": None, "autor": None, "descripcion": None, "texto": "",
            "idioma": None, "canonical": None, "origen": url, "vía": via,
            "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "error": err, "via_cache": False,
        }
    else:
        reg = M.extraer(cuerpo, url)
        reg.update({
            "origen": url,
            "vía": via,
            "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "via_cache": False,
        })
        reg["descripcion"] = M.resumen(reg, 320) or None
        if not reg.get("error"):
            escribir_cache(url, reg)
    return reg


def deduplicar(registros: list[dict]) -> list[dict]:
    """Una entrada por URL canonica. Gana la que tiene fecha y la que tiene texto.

    Sin esto, la misma nota llega tres veces: por feed, por busqueda y por URL
    directa, y el informe la cuenta tres veces.
    """
    mejor: dict[str, dict] = {}
    for r in registros:
        h = r.get("hash") or M.hash_url(r.get("url", ""))
        r["hash"] = h
        prev = mejor.get(h)
        if prev is None:
            mejor[h] = r
            continue
        puntos = lambda x: (bool(x.get("fecha")), len(x.get("texto") or ""))  # noqa: E731
        if r.get("error") and not prev.get("error"):
            continue
        if prev.get("error") and not r.get("error"):
            mejor[h] = r
        elif puntos(r) > puntos(prev):
            mejor[h] = r
    return list(mejor.values())


def escribir(registros: list[dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Descarga y normaliza fuentes.")
    ap.add_argument("--feed", action="append", default=[], metavar="URL")
    ap.add_argument("--url", action="append", default=[], metavar="URL")
    ap.add_argument("--csv", action="append", default=[], type=Path, metavar="RUTA",
                    help="Exportacion de ofertas de un portal. Una fila = una oferta.")
    ap.add_argument("--pdf", action="append", default=[], type=Path, metavar="RUTA")
    ap.add_argument("--transcript", action="append", default=[], type=Path, metavar="RUTA",
                    help="Transcripcion local .vtt, .srt o .txt.")
    ap.add_argument("--youtube", action="append", default=[], metavar="URL_O_ID",
                    help="Video de YouTube. Intenta los subtitulos automaticos.")
    ap.add_argument("--fecha", help="Fecha (YYYY-MM-DD) de los ficheros sin fecha propia.")
    ap.add_argument("--canal", help="Medio o canal para --transcript y --youtube.")
    ap.add_argument("--esquema", type=Path, default=ESQUEMA,
                    help="Configuracion con el mapa de cabeceras CSV.")
    ap.add_argument("--salida", type=Path, help="Fichero JSON de evidencia.")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--sin-cache", action="store_true",
                    help="Ignora la cache y vuelve a pedirlo todo a la red.")
    ap.add_argument("--espera", type=float, default=0.4,
                    help="Pausa entre peticiones, en segundos.")
    ap.add_argument("--dump-cache", action="store_true",
                    help="Lista el contenido de la cache y sale.")
    args = ap.parse_args()

    if args.dump_cache:
        if not CACHE.exists():
            print(f"cache vacia: {CACHE}")
            return 0
        for p in sorted(CACHE.glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                print(f"{p.stem}  {d.get('fecha') or 'sin-fecha':>10}  "
                      f"{(d.get('medio') or d.get('dominio'))[:34]:<34}  {d.get('url')}")
            except (json.JSONDecodeError, OSError):
                print(f"{p.stem}  <ilegible>")
        return 0

    if not (args.feed or args.url or args.csv or args.pdf or args.transcript or args.youtube):
        ap.error("hace falta --feed, --url, --csv, --pdf, --transcript o --youtube")

    esquema = None
    if args.csv and args.esquema.exists():
        esquema = json.loads(args.esquema.read_text(encoding="utf-8"))

    registros: list[dict] = []
    fallos = 0
    locales = 0

    for url in args.feed:
        c = leer_cache(url) if not args.sin_cache else None
        if c:
            print(f"[cache] {M.dominio(url)}", file=sys.stderr)
            for e in c.get("entradas", []):
                e["via_cache"] = True
            registros += c.get("entradas", [])
            continue
        cuerpo, err = _get(url, args.timeout)
        if err:
            fallos += 1
            print(f"[error] feed {url} -> {err}", file=sys.stderr)
            continue
        entradas = parsear_feed(cuerpo, url)
        CACHE.mkdir(parents=True, exist_ok=True)
        cache_path(url).write_text(
            json.dumps({"url": M.canonical(url), "entradas": entradas},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"[feed ] {M.dominio(url)} -> {len(entradas)} entradas", file=sys.stderr)
        registros += entradas
        time.sleep(args.espera)

    for url in args.url:
        r = obtener(url, args.timeout, not args.sin_cache, "html")
        if r.get("error"):
            fallos += 1
            print(f"[error] {url} -> {r['error']}", file=sys.stderr)
        else:
            marca = "cache" if r.get("via_cache") else "red"
            print(f"[{marca:<5}] {r['fecha'] or 'sin-fecha':>10}  {r['url']}", file=sys.stderr)
        registros.append(r)
        time.sleep(args.espera)

    for ruta in args.csv:
        if not ruta.exists():
            fallos += 1
            print(f"[error] csv {ruta} -> no existe", file=sys.stderr)
            continue
        ofer = parsear_csv(ruta, esquema)
        sin_fecha = sum(1 for o in ofer if not o.get("fecha"))
        con_salario = sum(1 for o in ofer if (o.get("datos") or {}).get("salario_eur"))
        print(f"[csv  ] {ruta.name} -> {len(ofer)} ofertas"
              f" | con fecha: {len(ofer) - sin_fecha} | con salario: {con_salario}",
              file=sys.stderr)
        registros += ofer
        locales += len(ofer)

    for ruta in args.pdf:
        if not ruta.exists():
            fallos += 1
            print(f"[error] pdf {ruta} -> no existe", file=sys.stderr)
            continue
        texto, err = texto_pdf(ruta)
        if err:
            fallos += 1
            print(f"[error] pdf {ruta.name} -> {err}", file=sys.stderr)
            registros.append({
                "url": clave_local(ruta.name), "hash": hash_texto(clave_local(ruta.name)),
                "dominio": ruta.stem, "titulo": ruta.stem, "medio": ruta.stem,
                "fecha": args.fecha, "autor": None, "descripcion": None, "texto": "",
                "idioma": None, "canonical": None, "origen": str(ruta), "vía": "pdf",
                "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "error": err, "via_cache": False, "datos": {}, "notas": ["ilegible"],
            })
            continue
        reg = registro_local(ruta, texto, args.canal or ruta.stem,
                             M.parse_fecha(args.fecha), "pdf")
        print(f"[pdf  ] {ruta.name} -> {len(reg['texto'])} caracteres"
              f" | fecha: {reg['fecha'] or 'sin-fecha'}", file=sys.stderr)
        registros.append(reg)
        locales += 1

    for ruta in args.transcript:
        if not ruta.exists():
            fallos += 1
            print(f"[error] transcript {ruta} -> no existe", file=sys.stderr)
            continue
        texto = limpiar_transcripcion(_lee_texto_flexible(ruta))
        reg = registro_local(
            ruta, texto, args.canal or "YouTube (transcripcion)",
            M.parse_fecha(args.fecha), "transcript",
            notas=["transcripcion_automatica: puede contener errores de reconocimiento automatico. "
                   "Verifica las cifras citadas contra el video antes de usarlas."],
        )
        if not reg["fecha"]:
            reg["notas"].append("sin_fecha")
        print(f"[vtt  ] {ruta.name} -> {len(texto)} caracteres"
              f" | fecha: {reg['fecha'] or 'sin-fecha'}", file=sys.stderr)
        registros.append(reg)
        locales += 1

    for video in args.youtube:
        texto, datos = subtitulos_youtube(video, args.timeout)
        vid = datos.get("video") or id_youtube(video) or "?"
        nombre = Path(f"{vid}.vtt")
        if not texto:
            fallos += 1
            print(f"[error] youtube {vid} -> {datos.get('error')}", file=sys.stderr)
            registros.append({
                "url": f"https://www.youtube.com/watch?v={vid}",
                "hash": M.hash_url(f"https://www.youtube.com/watch?v={vid}"),
                "dominio": "youtube.com", "titulo": f"Video {vid}", "medio": "YouTube",
                "fecha": datos.get("fecha"), "autor": datos.get("canal"),
                "descripcion": None, "texto": "", "idioma": None, "canonical": None,
                "origen": f"https://www.youtube.com/watch?v={vid}", "vía": "youtube",
                "capturado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "error": datos.get("error"), "via_cache": False, "datos": datos,
                "notas": ["sin_transcripcion"],
            })
            time.sleep(args.espera)
            continue
        limpio = limpiar_transcripcion(texto)
        reg = registro_local(nombre, limpio, args.canal or datos.get("canal") or "YouTube",
                             M.parse_fecha(args.fecha) or datos.get("fecha"), "transcript",
                             datos={"idioma_subtitulos": datos.get("idioma_subtitulos")},
                             notas=["transcripcion_automatica: puede contener errores de reconocimiento automatico."])
        reg["url"] = f"https://www.youtube.com/watch?v={vid}"
        reg["hash"] = M.hash_url(reg["url"])
        reg["dominio"] = "youtube.com"
        reg["origen"] = reg["url"]
        if not reg["fecha"]:
            reg["notas"].append("sin_fecha")
        print(f"[yt   ] {vid} -> {len(limpio)} caracteres"
              f" | fecha: {reg['fecha'] or 'sin-fecha'}", file=sys.stderr)
        registros.append(reg)
        locales += 1
        time.sleep(args.espera)

    registros = deduplicar(registros)
    fecha_corte = datetime.now(timezone.utc).date().isoformat()
    for r in registros:
        r["flag_fecha"] = M.inconsistente(r.get("fecha"), fecha_corte)

    if args.salida:
        escribir(registros, args.salida)
        con_fecha = sum(1 for r in registros if r.get("fecha"))
        print(
            f"\n{len(registros)} registros unicos -> {args.salida}\n"
            f"  con fecha: {con_fecha}/{len(registros)}"
            f" | con error: {fallos}"
            f" | de fichero local: {locales}"
            f" | desde cache: {sum(1 for r in registros if r.get('via_cache'))}",
            file=sys.stderr,
        )
    else:
        for r in registros:
            print(json.dumps({k: v for k, v in r.items() if k != "texto"},
                             ensure_ascii=False))

    # Un fallo de fuente no se propaga: una caida se registra y la corrida sigue.
    # Pero una corrida en la que **ninguna** fuente ha dado un registro usable no
    # es una corrida: sale con 1, o el `/recolectar` creera que tiene evidencia.
    utilizables = [r for r in registros if not r.get("error")]
    return 1 if fallos and not utilizables else 0


if __name__ == "__main__":
    raise SystemExit(main())
