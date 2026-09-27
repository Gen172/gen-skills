#!/usr/bin/env python3
"""Descarga y normaliza fuentes a un fichero JSON de evidencia.

Dos rutas, con reglas distintas (ADR-006):

  --feed  RSS/Atom. Es la via para lo recurrente (reguladores, medios
          sectoriales). Trae fecha y medio ya resueltos por el feed, que es
          informacion mas fiable que la que se puede sacar del HTML.

  --url   HTML suelto. Es la via para lo puntual (una empresa, un evento). El
          agente llega aqui con websearch/webfetch; este script sirve para
          dejar el resultado con metadatos normalizados y cacheado.

Cache por hash de URL canonica (ADR-004). Re-correr el golden set no vuelve a
pedir nada a la red, y el resultado no depende de que la fuente siga viva.

Uso:
  python3 scripts/fetch.py --feed URL_Feed [--feed ...] --salida datos/x.json
  python3 scripts/fetch.py --url  URL_HTML  [--url ...]  --salida datos/x.json
  python3 scripts/fetch.py --url URL --sin-cache            # fuerza red
  python3 scripts/fetch.py --dump-cache                     # inspecciona
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree.ElementTree import ParseError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metadatos as M  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "datos" / "cache"

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

    if not args.feed and not args.url:
        ap.error("hace falta --feed o --url")

    registros: list[dict] = []
    fallos = 0

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
            f" | desde cache: {sum(1 for r in registros if r.get('via_cache'))}",
            file=sys.stderr,
        )
    else:
        for r in registros:
            print(json.dumps({k: v for k, v in r.items() if k != "texto"},
                             ensure_ascii=False))

    return 1 if fallos and not registros else 0


if __name__ == "__main__":
    raise SystemExit(main())
