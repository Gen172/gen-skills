#!/usr/bin/env python3
"""Linter de los ficheros que escriben los agentes y los prompts.

Existe por un motivo concreto: al generar texto largo en español se colaron
caracteres de otros alfabetos y fragmentos rotos dentro de palabras, y eso no
se ve leyendo. Esto lo caza siempre.

Uso:
  python3 scripts/revisar_docs.py            # todo el repo
  python3 scripts/revisar_docs.py --fix      # corrige lo corregible solo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXT = {".md", ".json", ".py"}
# Carpetas que no son nuestras. `node_modules` entra con thousands de ficheros
# de terceros y sus caracteres rarefiedos hunden el ratio de ruido: cuando el
# linter_findaba 297 problemas, 297 eran de ahi y el linter era inutil.
IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv",
           ".cache", "cache", "datos", "dist", "build", ".opencode/state"}

# Alfabetos que no pertenecen a ningun fichero de este proyecto.
EXTRANOS = re.compile(
    r"[\u0400-\u04FF\u4e00-\u9fff\uac00-\ud7af\u0600-\u06ff]"
)
# Fragmentos que se han colado dentro de palabras: una palabra con dos o mas
# almohadillas, o con @@, pegadas en medio. Solo marcadores de markdown
# duplicados; el snake_case de los identificadores es legitimo y no debe saltar.
# El patron se arma por partes para que este propio comentario no se dispare.
HASH = "#" * 2
PEGADO = re.compile(
    r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,}(?:" + HASH + r"+|@@+|\*\*\w)[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,}"
)
# # Parentesis o corchetes que se abren y no se cierran (texto cortado).
SIN_CERRAR = re.compile(r"[\(\[][^\)\]\n]{0,80}$")
# La fila que separa la cabecera del cuerpo de una tabla markdown. Sin ella, en
# el sitio donde se lee esto, el bloque entero sale como texto pegado.
SEPARADOR = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+$")


def no_ascii_sospechoso(t: str) -> list[tuple[str, str]]:
    """Caracteres no latinos que no sean puntuacion ni simbolos tipograficos."""
    malo = []
    permitidos = set("–—·«»“”‘’…€→←↑↓±×÷≤≥≠°¿¡")
    for ch in t:
        if ord(ch) < 128 or ch in permitidos:
            continue
        try:
            nombre = unicodedata.name(ch)
        except ValueError:
            continue
        # Acentos latinos y alfabeticos latinos/cercanos: bien.
        if "LATIN" in nombre or "ACUTE" in nombre or "GRAVE" in nombre \
           or "TILDE" in nombre or "DIAERESIS" in nombre or "CEDILLA" in nombre:
            continue
        malo.append((ch, nombre))
    return malo


def revisar_fichero(p: Path) -> list[str]:
    problemas: list[str] = []
    texto = p.read_text(encoding="utf-8", errors="replace")
    lineas = texto.splitlines()

    for i, linea in enumerate(lineas, 1):
        if EXTRANOS.search(linea):
            problemas.append(f"{i}: caracter de otro alfabeto -> {EXTRANOS.findall(linea)}")
        for m in PEGADO.finditer(linea):
            problemas.append(f"{i}: fragmento pegado dentro de palabra -> {m.group(0)!r}")
        for ch, nombre in no_ascii_sospechoso(linea):
            problemas.append(f"{i}: caracter no permitido {ch!r} ({nombre})")

    # Tablas markdown: todas las filas de un bloque deben llevar el mismo
    # numero de pipes. Un pipe suelto rompe la tabla en silencio.
    #
    # Y ademas: la segunda fila del bloque tiene que ser la separadora. Sin
    # ella el markdown no monta la tabla y todo el bloque se lee como un
    # parrafo pegado. El conteo de pipes no lo pilla (la fila separadora lleva
    # los mismos pipes que las demas), asi que hace falta mirar el contenido:
    # es el unico sintoma que se ve al final, cuando ya se ha escrito todo.
    bloque: list[tuple[int, int, str]] = []
    for i, linea in enumerate(lineas, 1):
        s = linea.strip()
        if s.startswith("|") and s.endswith("|"):
            bloque.append((i, s.count("|"), s))
        else:
            if len(bloque) > 1:
                moda = max({n for _, n, _ in bloque}, key=lambda n: sum(1 for _, x, _ in bloque if x == n))
                for ln, n, _ in bloque:
                    if n != moda:
                        problemas.append(
                            f"{ln}: fila de tabla con {n} pipes, el bloque usa {moda}"
                        )
                separadoras = [(ln, s) for ln, _, s in bloque if SEPARADOR.match(s)]
                if not separadoras:
                    problemas.append(
                        f"{bloque[0][0]}: bloque de tabla sin fila separadora "
                        f"(|---|---|); no se va a renderizar como tabla"
                    )
                for ln, _ in separadoras:
                    if ln != bloque[1][0]:
                        problemas.append(
                            f"{ln}: fila separadora fuera de sitio; tiene que ir "
                            f"justo debajo de la cabecera (linea {bloque[0][0]})"
                        )
            bloque = []

    if p.suffix == ".json":
        try:
            json.loads(texto)
        except json.JSONDecodeError as e:
            problemas.append(f"JSON invalido: linea {e.lineno}, columna {e.colno}: {e.msg}")

    if p.suffix == ".py":
        try:
            compile(texto, str(p), "exec")
        except SyntaxError as e:
            problemas.append(f"Python invalido: linea {e.lineno}: {e.msg}")

    # `name` es obligatorio en SKILL.md y no en los comandos: ahi el nombre del
    # comando es el nombre del fichero, y opencode no lee ese campo.
    if p.suffix == ".md" and texto.startswith("---") and p.name == "SKILL.md":
        if not re.search(r"^name:\s*\S+", texto, re.M):
            problemas.append("SKILL.md sin campo name")
        if not re.search(r"^description:\s*\S+", texto, re.M):
            problemas.append("SKILL.md sin campo description")
        m = re.search(r"^name:\s*(\S+)", texto, re.M)
        if m and p.parent.name != m.group(1):
            problemas.append(
                f"el campo name ({m.group(1)}) no coincide con la carpeta "
                f"({p.parent.name}); opencode no lo descubrira"
            )

    return problemas


def es_nuestro(p: Path) -> bool:
    """True si el fichero es del repo y no de una dependencia instalada."""
    try:
        partes = p.relative_to(RAIZ).parts
    except ValueError:
        return False
    return not any(x in IGNORAR for x in partes[:-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("rutas", nargs="*", default=None)
    args = ap.parse_args()

    if args.rutas:
        objetivos = [Path(r).resolve() for r in args.rutas]
    else:
        objetivos = [p for p in RAIZ.rglob("*")
                     if p.suffix in EXT and es_nuestro(p)]

    total = 0
    for p in sorted(objetivos):
        if not p.is_file():
            continue
        probs = revisar_fichero(p)
        rel = p.relative_to(RAIZ)
        if probs:
            print(f"\n{rel}")
            for x in probs:
                print(f"  - {x}")
            total += len(probs)
        else:
            print(f"ok  {rel}")

    print(f"\n{total} problemas en {len(objetivos)} ficheros")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
