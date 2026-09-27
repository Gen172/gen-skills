#!/usr/bin/env python3
"""Métricas objetivas sobre un informe. Sin LLM: solo texto y JSON.

Por qué existe: la calidad de un informe de análisis se debate de palabra y
nunca se resuelve. Estas cinco metricas no deciden la calidad, pero si detectan
las tres formas concretas de fallar que se han visto en la práctica:

  1. citar una URL que no está en la evidencia      -> citas_resolubles
  2. atribuir una fecha que no es la de la fuente   -> fechas_correctas
  3. rellenar un hueco con lo que se sabe           -> celdas_sin_fuente
  4. dejar el frontmatter o el registro incompletos -> estructura_completa
  5. no declarar los vacíos                          -> vacios_declarados

Uso:
  python3 scripts/evaluar.py --informe informes/x.md --evidencia datos/c/evidencia.json
  python3 scripts/evaluar.py --informe informes/x.md --evidencia datos/c/evidencia.json --golden
  python3 scripts/evaluar.py --informe informes/x.md --evidencia datos/c/evidencia.json --red
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import metadatos as M  # noqa: E402

CLAVE = re.compile(r"\[E(\d{2,})\]")
URL = re.compile(r"https?://[^\s|)\]]+")
ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MARCAS_VACIO = re.compile(
    r"sin evidencia regional|sin dato|no hay dato|no se ha encontrado|"
    r"sin equivalentes? p[uú]blico?|no comparable|vac[ií]a?s?\b|n/d|\u2014",
    re.I,
)

SECCIONES = [
    "Resumen ejecutivo",
    "Panorama por vertical",
    "Benchmarks globales",
    "Tesis",
    "Riesgos y l",
    "Registro de evidencia",
]


def frontmatter(texto: str) -> dict:
    if not texto.startswith("---"):
        return {}
    fin = texto.find("\n---", 3)
    if fin == -1:
        return {}
    bloque = texto[3:fin]
    datos: dict = {}
    clave = None
    for linea in bloque.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", linea)
        if m:
            clave = m.group(1)
            datos[clave] = m.group(2).strip()
        elif clave and linea.strip().startswith("["):
            datos[clave] = linea.strip()
        elif clave and linea.strip():
            datos[clave] = f"{datos.get(clave,'')} {linea.strip()}".strip()
    return datos


def clave_registro(texto: str) -> dict[str, dict]:
    """Lee la tabla del Registro de evidencia: clave -> fila."""
    out: dict[str, dict] = {}
    for linea in texto.splitlines():
        if not linea.strip().startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) < 3:
            continue
        m = re.match(r"^E(\d{2,})$", celdas[0])
        if not m:
            continue
        url = ""
        for c in celdas[1:]:
            if c.startswith("http"):
                url = c
                break
        out[m.group(1)] = {
            "url": M.canonical(url) if url else None,
            "medio": celdas[2] if len(celdas) > 2 else None,
            "fecha": M.parse_fecha(celdas[3]) if len(celdas) > 3 else None,
            "idioma": celdas[4] if len(celdas) > 4 else None,
            "peso": celdas[5] if len(celdas) > 5 else None,
        }
    return out


def es_separador(celdas: list[str]) -> bool:
    return bool(celdas) and all(re.match(r"^:?-{2,}:?$", c) for c in celdas if c)


def tablas(texto: str) -> list[tuple[int, list[str], bool]]:
    """(linea, celdas, es_cabecera) para cada fila de cada tabla markdown.

    Hay que agrupar por bloques porque la cabecera no se distingue por su texto
    sino por su posicion: es la fila que precede a la de separadores. Sin esto,
    "| Campo | Dato |" cuenta como celda de datos y falsea la metrica.
    """
    filas: list[tuple[int, list[str], bool]] = []
    bloque: list[tuple[int, list[str]]] = []

    def cerrar(bloque):
        sep = next((i for i, f in enumerate(bloque) if es_separador(f[1])), None)
        cab = sep - 1 if sep is not None and sep > 0 else None
        for i, (ln, celdas) in enumerate(bloque):
            filas.append((ln, celdas, i == cab))

    for i, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if s.startswith("|") and s.endswith("|"):
            bloque.append((i, [c.strip() for c in s.strip("|").split("|")]))
        elif bloque:
            cerrar(bloque)
            bloque = []
    if bloque:
        cerrar(bloque)
    return filas


def main() -> int:
    ap = argparse.ArgumentParser(description="Metricas objetivas de un informe.")
    ap.add_argument("--informe", type=Path, required=True)
    ap.add_argument("--evidencia", type=Path, required=True)
    ap.add_argument("--golden", type=Path, help="Compara con golden/casos.json")
    ap.add_argument("--caso", help="Id de caso del golden set, p.ej. G01")
    ap.add_argument("--red", action="store_true",
                    help="Comprueba ademas que las URLs responden. Lento y dependent de la red.")
    ap.add_argument("--json", type=Path, help="Vuelca las metricas a un JSON.")
    args = ap.parse_args()

    texto = args.informe.read_text(encoding="utf-8")
    ev = json.loads(args.evidencia.read_text(encoding="utf-8"))
    fm = frontmatter(texto)
    registro = clave_registro(texto)

    por_url: dict[str, dict] = {}
    for r in ev:
        por_url[r.get("url") or ""] = r

    # ---- 1. Citas resolubles -------------------------------------------
    usadas = sorted({m.group(1) for m in CLAVE.finditer(texto)})
    sin_respaldo = []
    for k in usadas:
        fila = registro.get(k)
        if fila is None:
            sin_respaldo.append({"clave": k, "motivo": "no esta en el registro de evidencia"})
        elif not fila["url"]:
            sin_respaldo.append({"clave": k, "motivo": "el registro no trae URL"})
        elif fila["url"] not in por_url:
            sin_respaldo.append({"clave": k, "motivo": "la URL no esta en evidencia.json"})
    citas_resolubles = 1 - (len(sin_respaldo) / len(usadas)) if usadas else 0.0

    # ---- 2. Fechas correctas -------------------------------------------
    fechas_mal = []
    for k, fila in registro.items():
        if not fila["url"] or fila["url"] not in por_url:
            continue
        real = por_url[fila["url"]].get("fecha")
        puesta = fila.get("fecha")
        if puesta and real and puesta != real:
            fechas_mal.append({"clave": k, "en_informe": puesta, "en_evidencia": real})
    fechas_correctas = 1 - (len(fechas_mal) / len(registro)) if registro else 0.0

    # ---- 3. Celdas con dato y sin fuente -------------------------------
    con_dato_sin_fuente = []
    celdas_con_dato = 0
    for ln, celdas, cabecera in tablas(texto):
        if cabecera or es_separador(celdas) or len(celdas) < 2:
            continue
        primera = celdas[0]
        if re.match(r"^(E\d{2,}|Clave|Campo|Region|Vertical|Mode)$", primera, re.I):
            continue
        resto = " | ".join(celdas[1:])
        if CLAVE.search(resto):
            continue
        if MARCAS_VACIO.search(resto) or not resto:
            continue
        # Solo celdas de datos: las de texto corrido no llevan clave por diseno.
        if len(resto) > 400:
            continue
        celdas_con_dato += 1
        con_dato_sin_fuente.append({"linea": ln, "celda": resto[:80]})
    celdas_sin_fuente = (len(con_dato_sin_fuente) / celdas_con_dato) if celdas_con_dato else 0.0

    # ---- 3b. Entradas del registro que no se citan ---------------------
    # Una entrada en el registro que no aparece en el cuerpo es una fuente
    # fantasma: o se cito mal o no hace falta. En ambos casos sobra.
    no_citadas = sorted(set(registro) - set(usadas))

    # ---- 4. Estructura ------------------------------------------------
    falta = [s for s in SECCIONES if s.lower() not in texto.lower()]
    claves_campos = [c for c in ("region", "verticales", "fecha_corte", "fuentes_totales")
                     if c not in fm]
    estructura = 1 - (len(falta) + len(claves_campos)) / (len(SECCIONES) + 4)

    # ---- 5. Vacios declarados -----------------------------------------
    verticales_cfg = json.loads((RAIZ / "config" / "verticales.json").read_text(encoding="utf-8"))
    pedidas = [v.strip() for v in re.split(r"[,\[\]]", fm.get("verticales", ""))
               if v.strip() and v.strip() != "todas"]
    marcados = set()
    for m in re.finditer(r"###\s*[\d.]*\s*([A-Za-zÀ-ÿ /]+)", texto):
        for v in verticales_cfg["verticales"]:
            if v["nombre"].split("/")[0].strip().lower() in m.group(1).lower():
                marcados.add(v["id"])
    vacios = [m.group(0).lower() for m in MARCAS_VACIO.finditer(texto)]
    vacios_declarados = (len(vacios) > 0 and not falta) if pedidas else 0.0

    # ---- Opcional: URLs vivas ------------------------------------------
    urls_muertas = []
    if args.red:
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError, URLError
        for k, fila in sorted(registro.items()):
            if not fila["url"]:
                continue
            try:
                req = Request(fila["url"], method="HEAD",
                              headers={"User-Agent": "analisis-sector/1.0"})
                with urlopen(req, timeout=10) as r:
                    if r.status >= 400:
                        urls_muertas.append({"clave": k, "codigo": r.status})
            except HTTPError as e:
                if e.code not in (403, 405):
                    urls_muertas.append({"clave": k, "codigo": e.code})
            except (URLError, OSError) as e:
                urls_muertas.append({"clave": k, "codigo": type(e).__name__})

    # ---- Resultado -----------------------------------------------------
    pct = lambda x: f"{x * 100:5.1f}%"  # noqa: E731
    print(f"\nInforme: {args.informe.relative_to(RAIZ) if args.informe.is_absolute() else args.informe}")
    print(f"Evidencia: {len(ev)} registros | claves citadas: {len(usadas)} | "
          f"en registro: {len(registro)}\n")
    print(f"  citas resolubles ....... {pct(citas_resolubles)}")
    print(f"  fechas correctas ....... {pct(fechas_correctas)}")
    print(f"  celdas sin fuente ...... {pct(celdas_sin_fuente)}  (cuanto mas bajo, mejor)")
    print(f"  estructura completa .... {pct(estructura)}")
    print(f"  vacios declarados ...... {pct(vacios_declarados)}")

    if sin_respaldo:
        print(f"\n  Citas sin respaldo ({len(sin_respaldo)}):")
        for x in sin_respaldo[:12]:
            print(f"    [{x['clave']:>3}] {x['motivo']}")
    if fechas_mal:
        print(f"\n  Fechas que no cuadran ({len(fechas_mal)}):")
        for x in fechas_mal[:12]:
            print(f"    [{x['clave']:>3}] informe {x['en_informe']} != evidencia {x['en_evidencia']}")
    if con_dato_sin_fuente:
        print(f"\n  Celdas con dato y sin clave de fuente ({len(con_dato_sin_fuente)}):")
        for x in con_dato_sin_fuente[:12]:
            print(f"    linea {x['linea']}: {x['celda'][:70]}")
    if no_citadas:
        print(f"\n  En el registro pero nunca citadas en el cuerpo ({len(no_citadas)}): "
              f"{', '.join('E' + k for k in no_citadas[:12])}")
    if falta or claves_campos:
        print(f"\n  Estructura: faltan secciones {falta}, faltan campos {claves_campos}")
    if urls_muertas:
        print(f"\n  URLs que no resuelven ({len(urls_muertas)}): {urls_muertas[:8]}")

    if args.golden and args.golden.exists():
        golden = json.loads(args.golden.read_text(encoding="utf-8"))
        casos = golden.get("casos", [])

        if args.caso:
            caso = next((c for c in casos if c["id"] == args.caso), None)
            if caso is None:
                print(f"\n  Golden: no existe el caso {args.caso}. "
                      f"Disponibles: {', '.join(c['id'] for c in casos)}")
            else:
                print(f"\n  Caso {caso['id']}: {caso['nombre']}")
                if caso.get("vertical") not in fm.get("verticales", ""):
                    print(f"    AVISO: el informe declara '{fm.get('verticales')}' y este caso "
                          f"es de '{caso['vertical']}'. La comparacion no es directa.")
                if caso.get("fecha_corte") != fm.get("fecha_corte"):
                    print(f"    AVISO: fecha de corte distinta (caso {caso.get('fecha_corte')}, "
                          f"informe {fm.get('fecha_corte')}). Las metricas no son comparables.")

                # Lo unico comprobable sin un LLM es la lista negativa: si algo
                # que el caso prohibe aparece, el caso falla. Lo positivo
                # (esperado_minimo) es semantico y lo revisa una persona.
                bajos = [c for c in caso.get("no_debe_contener", [])
                         if c.lower() in texto.lower()]
                print(f"    no_debe_contener: {'FALLA -> ' + str(bajos) if bajos else 'ok'}")
                print(f"    esperado_minimo: {len(caso.get('esperado_minimo', []))} "
                      f"puntos, requieren revision humana")
        else:
            verticales_informe = fm.get("verticales", "")
            print(f"\n  Golden: {len(casos)} casos definidos")
            for c in casos:
                encaja = " *" if c.get("vertical") in verticales_informe else "  "
                print(f"   {encaja} {c['id']}  {c.get('vertical', ''):<18} {c['nombre']}")
            print("    (* = vertical de este informe.  "
                  "Usa --caso G01 para comprobar uno.)")

    metricas = {
        "informe": str(args.informe),
        "fuentes_registro": len(registro),
        "claves_citadas": len(usadas),
        "citas_resolubles": round(citas_resolubles, 4),
        "fechas_correctas": round(fechas_correctas, 4),
        "celdas_sin_fuente": round(celdas_sin_fuente, 4),
        "estructura_completa": round(estructura, 4),
        "vacios_declarados": round(vacios_declarados, 4),
        "detalle": {
            "citas_sin_respaldo": sin_respaldo,
            "fechas_no_cuadran": fechas_mal,
            "celdas_sin_fuente": con_dato_sin_fuente,
            "registro_sin_citar": no_citadas,
            "secciones_faltantes": falta,
            "campos_faltantes": claves_campos,
            "urls_muertas": urls_muertas,
        },
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(metricas, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    return 1 if sin_respaldo or fechas_mal or falta else 0


if __name__ == "__main__":
    raise SystemExit(main())
