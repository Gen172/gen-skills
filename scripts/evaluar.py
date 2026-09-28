#!/usr/bin/env python3
"""Métricas objetivas sobre un informe. Sin LLM: solo texto y JSON.

Por qué existe: la calidad de un informe de análisis se debate de palabra y
nunca se resuelve. Estas metricas no deciden la calidad, pero si detectan
las formas concretas de fallar que se han visto en la práctica:

  1. citar una URL que no está en la evidencia      -> citas_resolubles
  2. atribuir una fecha que no es la de la fuente   -> fechas_correctas
  3. rellenar un hueco con lo que se sabe           -> celdas_sin_fuente
  4. dejar el frontmatter o el registro incompletos -> estructura_completa
  5. no declarar los vacíos                          -> vacios_declarados
  6. publicar un rango salarial sin n                -> salarios_verificables
  7. no comparar hoy con 2-3 años                    -> brecha_declarada

Las dos ultimas solo se exigen en el dominio `laboral` (ADR-007), y las dos son
binarias: un rango salarial sin n no es "un poco impreciso", es una cifra con
apariencia de rango, que es la forma que mas engaña al lector.

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
CLAVE_LOCAL = re.compile(r"archivo:[^\s|)\]]+")
ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
ANIO = re.compile(r"\b(19|20)\d{2}\b")
CELDA_SALARIO = re.compile(r"^salarios?(\s+publicados?)?$", re.I)
MARCAS_VACIO = re.compile(
    r"sin evidencia regional|sin evidencia local|sin evidencia en la ventana|"
    r"sin evidencia publicada|sin evidencia de servidor|sin evidencia\b|"
    r"sin dato|no hay dato|no se ha encontrado|"
    r"sin equivalentes? p[uú]blico?|no comparable|vac[ií]a?s?\b|n/d|\u2014",
    re.I,
)

SECCIONES_SECTOR = [
    "Resumen ejecutivo",
    "Panorama por vertical",
    "Benchmarks globales",
    "Tesis",
    "Riesgos y l",
    "Registro de evidencia",
]

SECCIONES_LABORAL = [
    "Resumen ejecutivo",
    "Demanda actual",
    "horizonte",
    "Brecha de habilidades",
    "Riesgos y l",
    "Registro de evidencia",
]

# El campo del frontmatter que declara el dominio. Sin el, dominio sectorial.
CAMPO_DOMINIO = "dominio"
CONFIG_DOMINIO = {
    "laboral": RAIZ / "config" / "mercado-laboral.json",
    "sector": RAIZ / "config" / "verticales.json",
}


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
            # `archivo:fichero#3` es una clave de fuente local (dominio laboral)
            # y se compara literal: canonical() le tiraria el fragmento.
            if c.startswith("http") or CLAVE_LOCAL.match(c):
                url = c
                break
        canonica = M.canonical(url) if url.startswith("http") else url
        out[m.group(1)] = {
            "url": canonica or None,
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


def celdas_salario(texto: str) -> list[tuple[int, str]]:
    """(linea, dato) de las celdas que afirman un salario.

    Solo las que traen numeros o simbolo de moneda: una celda que dice 'sin
    evidencia regional' no esta afirmando ningun salario, y marcarla como si
    lo hiciera solo servira para llenar el detalle de ruido.
    """
    out = []
    for ln, celdas, cabecera in tablas(texto):
        if cabecera or es_separador(celdas) or not celdas:
            continue
        if not CELDA_SALARIO.match(celdas[0].strip()):
            continue
        resto = " | ".join(celdas[1:])
        if re.search(r"[0-9€$]", resto):
            out.append((ln, resto))
    return out


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

    # ---- 4. Dominio, estructura ---------------------------------------
    dominio = (fm.get(CAMPO_DOMINIO) or "sector").strip().lower()
    if dominio not in CONFIG_DOMINIO:
        print(f"  aviso: dominio '{dominio}' no conocido. Se evalua como 'sector'. "
              f"Valores validos: {', '.join(CONFIG_DOMINIO)}")
        dominio = "sector"
    laboral = dominio == "laboral"
    secciones = SECCIONES_LABORAL if laboral else SECCIONES_SECTOR
    requeridas = (("dominio", "region", "familias", "fecha_corte",
                   "ofertas_con_salario", "n_salario") if laboral else
                  ("region", "verticales", "fecha_corte", "fuentes_totales"))
    claves_campos = [c for c in requeridas if c not in fm]
    falta = [s for s in secciones if s.lower() not in texto.lower()]
    estructura = 1 - (len(falta) + len(claves_campos)) / (len(secciones) + len(requeridas))

    # ---- 4b. Dominio laboral: salarios y brecha ------------------------
    salarios_malos: list[dict] = []
    brecha_faltan: list[str] = []
    celdas_sal = celdas_salario(texto) if laboral else []
    if laboral:
        cfg = json.loads(CONFIG_DOMINIO["laboral"].read_text(encoding="utf-8"))
        nombres = [f["nombre"] for f in cfg["familias"]]
        pedidos = [f.strip() for f in re.split(r"[,\[\]]", fm.get("familias", "")) if f.strip()]

        for ln, resto in celdas_sal:
            faltan = []
            if not CLAVE.search(resto):
                faltan.append("sin clave de fuente")
            if not re.search(r"(EUR|euros|€)", resto, re.I):
                faltan.append("sin unidad en EUR")
            if not re.search(r"\bn\s*=|\bn\s+de\s+\d|\bde\s+\d+\s+ofertas?", resto, re.I):
                faltan.append("sin n= (muestra)")
            if not (ISO.search(resto) or ANIO.search(resto)):
                faltan.append("sin fecha del dato")
            # Y lo mas importante: que exista una oferta citada que publique un
            # salario. "sin salario" es una ausencia, no una cifra: no cuenta.
            con_salario = False
            for k in CLAVE.findall(resto):
                fila = registro.get(k)
                if not fila or not fila["url"]:
                    continue
                datos = (por_url.get(fila["url"]) or {}).get("datos") or {}
                eur = datos.get("salario_eur") or {}
                if (eur.get("min") or eur.get("max")
                        or datos.get("salario_min") or datos.get("salario_max")):
                    con_salario = True
            if not con_salario:
                faltan.append("ninguna de las fuentes citadas publica un salario")
            if faltan:
                salarios_malos.append({"linea": ln, "faltan": faltan, "celda": resto[:80]})

        bloque_brecha = ""
        mbrecha = re.search(r"brecha de habilidades", texto, re.I)
        if mbrecha:
            bloque_brecha = texto[mbrecha.end():]
            corte = re.search(r"\n##\s", bloque_brecha)
            if corte:
                bloque_brecha = bloque_brecha[:corte.start()]
        subs = list(re.finditer(r"^#{3,4}\s*[\d.]*\s*(.+)$", bloque_brecha, re.M))
        for familia in pedidos:
            nombre = next((n for n in nombres if n.lower() == familia.lower()), familia)
            sub = next((s for s in subs if nombre.lower() in s.group(1).lower()), None)
            if not sub:
                brecha_faltan.append(f"{familia}: sin subseccion en la brecha")
                continue
            siguiente = next((s.start() for s in subs if s.start() > sub.start()),
                             len(bloque_brecha))
            filas = [l for l in bloque_brecha[sub.end():siguiente].splitlines()
                     if l.strip().startswith("|")]
            datos_filas = [l for l in filas if not es_separador(
                [c.strip() for c in l.strip().strip("|").split("|")])]
            if len(datos_filas) < 2:
                brecha_faltan.append(f"{familia}: subseccion sin filas de datos")
        n_familias = max(len(pedidos), 1)
        salarios_verificables = 1 - len(salarios_malos) / max(len(celdas_sal), 1)
        brecha_declarada = 1 - len(brecha_faltan) / n_familias
    else:
        cfg = json.loads(CONFIG_DOMINIO["sector"].read_text(encoding="utf-8"))
        n_familias = 0
        salarios_verificables = None
        brecha_declarada = None

    # ---- 5. Vacios declarados -----------------------------------------
    pedidas = [v.strip() for v in re.split(r"[,\[\]]",
              fm.get("familias" if laboral else "verticales", "")) if v.strip()]
    ids_cfg = ({f["id"] for f in cfg["familias"]} if laboral
               else {v["id"] for v in cfg["verticales"]})
    desconocidos = [p for p in pedidas if p not in ids_cfg and p != "todas"]
    vacios = [m.group(0).lower() for m in MARCAS_VACIO.finditer(texto)]
    vacios_declarados = (len(vacios) > 0 and not falta) if pedidas else 0.0
    if desconocidos:
        print(f"  aviso: {', '.join(desconocidos)} no existe en "
              f"{'mercado-laboral' if laboral else 'verticales'}.json")

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
    # Un informe puede estar fuera del repo (una copia de trabajo, /tmp). El
    # nombre relativo es cosmetico: no puede ser motivo de crash.
    nombre_informe = (args.informe.relative_to(RAIZ) if args.informe.is_relative_to(RAIZ)
                      else args.informe)
    print(f"\nInforme: {nombre_informe}")
    print(f"Evidencia: {len(ev)} registros | claves citadas: {len(usadas)} | "
          f"en registro: {len(registro)} | dominio: {dominio}\n")
    print(f"  citas resolubles ....... {pct(citas_resolubles)}")
    print(f"  fechas correctas ....... {pct(fechas_correctas)}")
    print(f"  celdas sin fuente ...... {pct(celdas_sin_fuente)}  (cuanto mas bajo, mejor)")
    print(f"  estructura completa .... {pct(estructura)}")
    print(f"  vacios declarados ...... {pct(vacios_declarados)}")
    if laboral:
        print(f"  salarios verificables ... {pct(salarios_verificables)}  "
              f"({len(celdas_sal)} celdas de salario)")
        print(f"  brecha declarada ....... {pct(brecha_declarada)}  "
              f"({len(brecha_faltan)} problemas)")

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
    if salarios_malos:
        print(f"\n  Celdas de salario que no se pueden auditar ({len(salarios_malos)}):")
        for x in salarios_malos[:12]:
            print(f"    linea {x['linea']}: {', '.join(x['faltan'])}")
            print(f"      {x['celda'][:70]}")
    if brecha_faltan:
        print(f"\n  Brecha de habilidades incompleta: {'; '.join(brecha_faltan)}")
    if urls_muertas:
        print(f"\n  URLs que no resuelven ({len(urls_muertas)}): {urls_muertas[:8]}")

    if args.golden and args.golden.exists():
        golden = json.loads(args.golden.read_text(encoding="utf-8"))
        casos = golden.get("casos", [])
        # El caso del golden lleva `vertical` en el dominio sectorial y `familia`
        # en el laboral. El informe declara `verticales` o `familias`.
        campo_caso = "familia" if laboral else "vertical"
        campo_fm = "familias" if laboral else "verticales"
        declarados = fm.get(campo_fm, "")

        if args.caso:
            caso = next((c for c in casos if c["id"] == args.caso), None)
            if caso is None:
                print(f"\n  Golden: no existe el caso {args.caso}. "
                      f"Disponibles: {', '.join(c['id'] for c in casos)}")
            else:
                print(f"\n  Caso {caso['id']}: {caso['nombre']}")
                if caso.get(campo_caso) not in declarados:
                    print(f"    AVISO: el informe declara '{declarados}' y este caso "
                          f"es de '{caso.get(campo_caso, caso.get('vertical'))}'. "
                          f"La comparacion no es directa.")
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
            print(f"\n  Golden: {len(casos)} casos definidos")
            for c in casos:
                ambito = c.get(campo_caso) or c.get("vertical") or ""
                encaja = " *" if ambito and ambito in declarados else "  "
                print(f"   {encaja} {c['id']}  {ambito:<18} {c['nombre']}")
            print("    (* = vertical o familia de este informe.  "
                  "Usa --caso G01 para comprobar uno.)")

    metricas = {
        "informe": str(args.informe),
        "dominio": dominio,
        "fuentes_registro": len(registro),
        "claves_citadas": len(usadas),
        "citas_resolubles": round(citas_resolubles, 4),
        "fechas_correctas": round(fechas_correctas, 4),
        "celdas_sin_fuente": round(celdas_sin_fuente, 4),
        "estructura_completa": round(estructura, 4),
        "vacios_declarados": round(vacios_declarados, 4),
        "salarios_verificables": (round(salarios_verificables, 4)
                                  if salarios_verificables is not None else None),
        "brecha_declarada": (round(brecha_declarada, 4)
                             if brecha_declarada is not None else None),
        "detalle": {
            "citas_sin_respaldo": sin_respaldo,
            "fechas_no_cuadran": fechas_mal,
            "celdas_sin_fuente": con_dato_sin_fuente,
            "registro_sin_citar": no_citadas,
            "secciones_faltantes": falta,
            "campos_faltantes": claves_campos,
            "salarios_no_auditables": salarios_malos,
            "brecha_incompleta": brecha_faltan,
            "familias_desconocidas": desconocidos,
            "urls_muertas": urls_muertas,
        },
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(metricas, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    fallo_dominio = bool(laboral and (salarios_malos or brecha_faltan))
    return 1 if sin_respaldo or fechas_mal or falta or fallo_dominio else 0


if __name__ == "__main__":
    raise SystemExit(main())
