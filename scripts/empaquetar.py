#!/usr/bin/env python3
"""Empaqueta los entregables de la practica en `dist/`.

Tres zips y un indice, porque son tres cosas que se entregan a tres personas
distintas:

  kb-*.zip         la base de conocimiento: config, scripts, plantillas, el
                   informe, su evidencia y su resumen. Es lo que lee quien
                   quiera auditar el resultado sin instalar nada.
  agente-*.zip     solo `.opencode/` (skills, comandos, agentes). Es lo que se
                   copia en otro proyecto de opencode para tener las dos fases.
 docs-*.zip        la documentacion de la practica: ADR, rubrica, glosario,
                   guia de los 5 dias. Es lo que se entrega al profesor.

El indice lleva el sha256 de cada fichero. Sin el, un paquete de evidencia es
una caja sin etiqueta: nadie puede demostrar que el PDF queulo entrego es el
mismo que se puede abrir.

    python3 scripts/empaquetar.py
    python3 scripts/empaquetar.py --salida dist --informe informes/x.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import shutil
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Ficheros que nunca entran en un paquete: son ruido, no entregables.
NUNCA = {"node_modules", ".git", "__pycache__", "dist", "cache", ".cache",
         ".venv", "venv", "datos"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def recoge(patrones: list[str], extra: list[Path] | None = None) -> list[Path]:
    """Ficheros que existen, sin duplicados y en orden estable."""
    vistos: set[Path] = set()
    salida: list[Path] = []
    for patron in patrones:
        for p in sorted(RAIZ.glob(patron)):
            if not p.is_file() or set(p.relative_to(RAIZ).parts) & NUNCA:
                continue
            rp = p.resolve()
            if rp in vistos:
                continue
            vistos.add(rp)
            salida.append(p)
    for p in extra or []:
        p = Path(p)
        if not p.is_absolute():
            p = RAIZ / p
        if p.is_file() and p not in salida:
            salida.append(p if p.is_relative_to(RAIZ) else p)
    return salida


def escribe_zip(destino: Path, entradas: list[tuple[Path, str]]) -> None:
    """entries: (ruta real, nombre dentro del zip)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for origen, nombre in entradas:
            z.write(origen, nombre)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="dist")
    ap.add_argument("--informe", help="informe a empaquetar (por defecto, el mas reciente)")
    ap.add_argument("--datos", help="carpeta de la corrida (por defecto, la del informe)")
    args = ap.parse_args()

    hoy = _dt.date.today().isoformat()
    salida = Path(args.salida)
    if not salida.is_absolute():
        salida = RAIZ / salida
    salida.mkdir(parents=True, exist_ok=True)

    informes = sorted((RAIZ / "informes").glob("*.md"))
    informe = Path(args.informe) if args.informe else (informes[-1] if informes else None)
    if informe and not informe.is_absolute():
        informe = RAIZ / informe
    if informe is None or not informe.is_file():
        print("aviso: no hay informe que empaquetar. Se empaqueta el resto igualmente.")
        informe = None

    datos: Path | None = None
    if args.datos:
        datos = Path(args.datos)
        if not datos.is_absolute():
            datos = RAIZ / datos
    elif informes:
        # La corrida se busca por la fecha del informe, ignorando las carpetas
        # de prueba (test_*) que no son entregables. Si quedan varias, se coge
        # la mas reciente y **se dice cual ha sido**: elegir en silencio una
        # evidencia ambigua es justo lo que el comando /analizar prohibe.
        prefijos = {f.stem.split("-")[0] for f in informes}
        candidatas = [c.parent for c in sorted((RAIZ / "datos").glob("*/evidencia.json"))
                      if not c.parent.name.startswith("test")
                      and (c.parent / "resumen.md").exists()]
        if prefijos:
            candidatas = [c for c in candidatas
                          if any(c.name.startswith(p) for p in prefijos)] or candidatas
        if candidatas:
            datos = max(candidatas, key=lambda p: (p / "evidencia.json").stat().st_mtime)
            if len(candidatas) > 1:
                print(f"aviso: varias corridas para la misma fecha "
                      f"({', '.join(c.name for c in candidatas)}). "
                      f"Empaqueto {datos.name}; usa --datos para fijar otra.")

    comunes = recoge([
        "config/*.json", "scripts/*.py", "golden/*.json", "golden/*.md",
        ".opencode/skills/*/*.md", ".opencode/commands/*.md",
        "docs/*.md", "AGENTS.md", "README.md", "GLOSSARY.md",
    ], [informe] if informe else None)
    if datos and datos.is_dir():
        # `datos/` no se empaqueta entero (AGENTS.md: es reproducible y su
        # historico es ruido), pero la corrida del informe es un entregable y
        # va dentro. Entra por `extra`, que es la unica puerta sin el filtro.
        comunes += recoge([], sorted(p for p in datos.iterdir() if p.is_file()))

    kb = [(p, f"kb/{p.relative_to(RAIZ)}") for p in comunes]
    agente = [(p, f"agente/{p.relative_to(RAIZ)}")
              for p in recoge([".opencode/skills/*/*.md", ".opencode/commands/*.md",
                               ".opencode/agents/*.md", "AGENTS.md"])]
    docs = [(p, f"docs/{p.relative_to(RAIZ)}")
            for p in recoge(["docs/*.md", "golden/rubrica.md", "GLOSSARY.md",
                             "AGENTS.md", "README.md"])]

    # El manifiesto va dentro de cada zip: un paquete sin indice obliga a
    # adivinar que contiene. En dos formatos, porque se leen de dos maneras:
    # la tabla para una persona, el .sha256 para `sha256sum -c`.
    cabecera = ["# Indice de " + hoy, "",
                f"Paquete generado por `scripts/empaquetar.py` el {hoy}.",
                f"Informe: {informe.relative_to(RAIZ) if informe else 'ninguno'}",
                "", "| sha256 (16) | fichero |", "|---|---|"]
    suma = []
    for origen, nombre in kb:
        h = sha256(origen)
        cabecera.append(f"| {h[:16]} | {nombre} |")
        suma.append(f"{h}  {nombre}")

    for grupo, entradas in (("kb", kb), ("agente", agente), ("docs", docs)):
        if not entradas:
            continue
        (salida / f"INDICE-{grupo}.md").write_text(
            "\n".join(cabecera) + "\n", encoding="utf-8")
        (salida / f"INDICE-{grupo}.sha256").write_text(
            "\n".join(suma) + "\n", encoding="utf-8")
        z = salida / f"{grupo}-{hoy}.zip"
        if z.exists():
            z.unlink()
        escribe_zip(z, entradas)
        with zipfile.ZipFile(z, "a", zipfile.ZIP_DEFLATED) as zz:
            zz.writestr("INDICE.md", (salida / f"INDICE-{grupo}.md").read_text(encoding="utf-8"))
            zz.writestr("INDICE.sha256", "\n".join(suma) + "\n")
        print(f"{z.relative_to(RAIZ)}  {len(entradas) + 2} entradas  "
              f"{z.stat().st_size // 1024} KB")

    if datos and datos.is_dir():
        print(f"incluye la corrida {datos.relative_to(RAIZ)}")
    print(f"indices en {salida.relative_to(RAIZ)}/INDICE-*.md y .sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
