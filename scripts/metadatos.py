"""Extraccion de metadatos y limpieza de HTML.

Usado por fetch.py. Sin dependencias fuera de la stdlib mas requests/bs4/lxml,
que ya estan instaladas en este entorno.

Regla de diseno: aqui solo se extraen hechos observables sobre la pagina
(URL canonica, fecha publicada, medio, idioma, texto). Nada se interpreta.
La interpretacion es trabajo de la skill `analizar`, no de este modulo.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# --------------------------------------------------------------------------
# URL
# --------------------------------------------------------------------------

# Parametros de tracking: se eliminan para que dos enlaces al mismo articulo
# produzcan el mismo hash y, por tanto, la misma entrada de cache.
TRACKING = re.compile(
    r"^(utm_|ga_|gclid|fbclid|mc_|mc_|ref|ref_src|igshid|_ga|yclid|msclkid|"
    r"vero_id|wt_mc|cmpid|CMP|campaign|spm|share)",
    re.I,
)


def canonical(url: str) -> str:
    """Normaliza una URL para deduplicar y para citar de forma estable."""
    if not url:
        return ""
    p = urlsplit(url.strip())
    scheme = "https" if p.scheme in ("http", "https", "") else p.scheme
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    # m.example.com y www.m.example.com son el mismo medio
    if host.startswith("m."):
        host = host[2:]
    qs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=False)
          if not TRACKING.match(k)]
    qs.sort()
    path = re.sub(r"/{2,}", "/", p.path) or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((scheme, host, path, urlencode(qs), ""))


def hash_url(url: str, n: int = 16) -> str:
    """Identificador estable de una URL canonica. Clave de la cache."""
    return hashlib.sha256(canonical(url).encode("utf-8")).hexdigest()[:n]


def dominio(url: str) -> str:
    host = urlsplit(canonical(url)).netloc
    return host[4:] if host.startswith("www.") else host


# --------------------------------------------------------------------------
# Idioma
# --------------------------------------------------------------------------

STOP_ES = {
    "de", "la", "el", "los", "las", "en", "para", "con", "por", "que", "del",
    "una", "un", "se", "su", "al", "es", "como", "mas", "sobre", "entre",
    "espana", "espanola", "español", "empresa", "empresas", "dice", "ano",
    "año", "millones", "euros",
}
STOP_EN = {
    "the", "of", "and", "to", "in", "for", "with", "on", "that", "is", "was",
    "from", "by", "at", "as", "it", "this", "are", "be", "has", "have", "will",
    "million", "billion", "says", "company", "companies", "startup",
}


def idioma(texto: str) -> str:
    """Heuristica es/en por palabras funcionales. No es un detector de idioma.

    Se Enough porque la decision que toma el consumidor es binaria:
    'esta cita global hay que mantenerla literal o traducirla' (ADR de redaccion).
    Ante duda devuelve 'desconocido' en vez de adivinar.
    """
    words = re.findall(r"[a-zA-ZáéíóúñÁÉÍÓÚÑüÜ]+", (texto or "")[:4000].lower())
    if len(words) < 12:
        return "desconocido"
    es = sum(1 for w in words if w in STOP_ES)
    en = sum(1 for w in words if w in STOP_EN)
    if es == 0 and en == 0:
        return "desconocido"
    return "es" if es > en else "en"


# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------

ISO = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?")

# "28 de septiembre de 2026" es el formato que sale de DATE_TEXT al final de
# `extraer`, asi que tiene que poder volver a leerse como fecha.
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def parse_fecha(valor) -> str | None:
    """Convierte una fecha en ISO-8601 (YYYY-MM-DD) o devuelve None.

    Acepta ISO-8601, RFC 822/1123 (el formato de RSS) y YYYY-MM-DD suelto.
    Se corta a fecha, sin hora, porque a nivel de informe sectorial la hora
    no aporta nada y comparar fechas con horas produce falsos negativos.
    """
    if not valor:
        return None
    if isinstance(valor, (list, tuple)):
        valor = valor[0] if valor else None
        if not valor:
            return None
    s = str(valor).strip()
    if not s:
        return None

    m = ISO.search(s)
    if m:
        try:
            return datetime.fromisoformat(m.group(0).replace(" ", "T")).date().isoformat()
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(s).date().isoformat()
    except (TypeError, ValueError):
        pass
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})\s+de\s+([a-zA-Záéíóúñ]+)\s+de\s+(\d{4})", s)
    if m:
        mes = MESES.get(m.group(2).lower())
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1))).isoformat()
            except ValueError:
                return None
    m = re.search(r"(\d{1,2})\s+([a-zA-Z]{3,9})\.?\s+(\d{4})", s)
    if m:
        mes = MESES.get(m.group(2).lower().rstrip("."))
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1))).isoformat()
            except ValueError:
                return None
    return None


def dias(fecha_iso: str | None, referencia: str | None) -> int | None:
    """Antiguedad en dias. None si falta alguna de las dos fechas."""
    if not fecha_iso:
        return None
    ref = parse_fecha(referencia) if referencia else date.today().isoformat()
    try:
        a = date.fromisoformat(fecha_iso)
        b = date.fromisoformat(ref)
    except (ValueError, TypeError):
        return None
    return (b - a).days


def inconsistente(fecha_iso: str | None, hoy: str | None = None) -> str | None:
    """Senala una fecha que no puede ser cierta. Vacio si todo cuadra.

    Tres fallos reales que se han visto en la practica y que hay que cazarlos
    aqui, no a ojo en el informe:
      - fecha futura respecto a la fecha de corte (inventada o de un draft)
      - mas de 5 anos de antiguedad citada como si fuera atual
      - fecha nula en una pagina que si la declara
    """
    hoy = hoy or date.today().isoformat()
    if not fecha_iso:
        return "sin_fecha"
    try:
        f = date.fromisoformat(fecha_iso)
        h = date.fromisoformat(hoy)
    except (ValueError, TypeError):
        return "fecha_ilegible"
    if f > h:
        return "fecha_futura"
    if (h - f).days > 365 * 5:
        return "antigua"
    return None


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

META_KEYS = {
    "title": ["og:title", "twitter:title"],
    "medio": ["og:site_name", "application-name", "twitter:site"],
    "fecha": [
        "article:published_time", "article:published",
        "datepublished", "date", "pubdate", "dc.date", "dc.date.issued",
        "sailthru.date", "parsely-pub-date", "cXenseParse:recs:publishtime",
    ],
    "autor": ["author", "article:author", "dc.creator", "parsely-author"],
    "descripcion": ["og:description", "twitter:description", "description"],
    "imagen": ["og:image"],
}

DROP_TAGS = [
    "script", "style", "noscript", "nav", "header", "footer", "aside",
    "form", "iframe", "svg", "figure", "button",
]

DATE_TEXT = re.compile(
    r"(publicado|actualizado|publicaci[oó]n|noticia)\s*:?\s*"
    r"(\d{1,2}\s+de\s+[a-zA-Z]+\s+de\s+\d{4}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{4}|"
    r"\d{4}-\d{2}-\d{2})",
    re.I,
)


def _soup(html: str):
    from bs4 import BeautifulSoup
    for parser in ("lxml", "html.parser"):
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")


def a_texto(html: str, max_chars: int = 20000) -> str:
    """HTML -> texto plano legible, quitando navegacion y publicidad."""
    s = _soup(html or "")
    for tag in s(list(DROP_TAGS)):
        tag.decompose()
    texto = s.get_text("\n")
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    texto = re.sub(r"\n\s*\n\s*\n+", "\n\n", texto)
    return texto.strip()[:max_chars]


def _meta(soup, names) -> str | None:
    for name in names:
        for attr in ("property", "name", "itemprop"):
            tag = soup.find("meta", attrs={attr: name})
            if tag and tag.get("content", "").strip():
                return tag["content"].strip()
    return None


def extraer(html: str, url: str) -> dict:
    """Metadatos + texto de una pagina. Nunca lanza: devuelve flags si falla."""
    out = {
        "url": canonical(url),
        "hash": hash_url(url),
        "dominio": dominio(url),
        "titulo": None,
        "medio": None,
        "fecha": None,
        "autor": None,
        "descripcion": None,
        "imagen": None,
        "idioma": None,
        "canonical": None,
        "texto": "",
        "error": None,
    }
    try:
        soup = _soup(html or "")

        link = soup.find("link", rel=lambda v: v and "canonical" in (v if isinstance(v, list) else [v]))
        out["canonical"] = link["href"].strip() if link and link.get("href") else None

        out["titulo"] = (_meta(soup, META_KEYS["title"])
                         or (soup.title.get_text(strip=True) if soup.title else None))
        out["medio"] = _meta(soup, META_KEYS["medio"]) or out["dominio"]
        out["autor"] = _meta(soup, META_KEYS["autor"])
        out["descripcion"] = _meta(soup, META_KEYS["descripcion"])
        out["imagen"] = _meta(soup, META_KEYS["imagen"])

        # Fecha: JSON-LD, luego <time datetime>, luego metas, luego texto visible.
        fecha = None
        for tag in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
            try:
                data = json.loads(tag.string or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            for obj in (data if isinstance(data, list) else [data]):
                if isinstance(obj, dict):
                    fecha = obj.get("datePublished") or obj.get("dateCreated")
                    if fecha:
                        break
            if fecha:
                break
        if not fecha:
            t = soup.find("time", attrs={"datetime": True})
            if t:
                fecha = t["datetime"]
        if not fecha:
            fecha = _meta(soup, META_KEYS["fecha"])
        if not fecha:
            m = DATE_TEXT.search(soup.get_text(" ")[:4000])
            if m:
                fecha = m.group(2)
        out["fecha"] = parse_fecha(fecha)

        out["texto"] = a_texto(html)
        out["idioma"] = idioma(out["texto"] or out["titulo"] or "")
    except Exception as exc:  # una pagina rota no puede tumbar la corrida
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def resumen(meta: dict, largo: int = 320) -> str:
    """Texto de un parrafo, para que el modelo juzgue sin leer 20k caracteres."""
    texto = (meta.get("texto") or "").replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) <= largo:
        return texto
    corte = texto[:largo]
    if "." in corte[40:]:
        corte = corte[: corte.rfind(".") + 1]
    return corte.strip() + " [...]"


if __name__ == "__main__":
    # stdin: JSON {"url": ..., "html": ...}. stdout: una linea de metadatos.
    data = json.load(sys.stdin)
    m = extraer(data.get("html", ""), data.get("url", ""))
    m["texto"] = resumen(m)
    print(json.dumps(m, ensure_ascii=False))
