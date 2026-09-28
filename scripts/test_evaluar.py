"""Prueba del evaluar contra un informe con errores plantados a proposito.

Un evaluador probado solo contra informes buenos no esta probado. Aqui se
plantan: una cita que no existe en la evidencia, una fecha que no cuadra, una
celda con dato y sin fuente, y una seccion que falta.

    python3 scripts/test_evaluar.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TMP = RAIZ / "datos" / "test-evaluar"

EVIDENCIA = [
    {"url": "https://expansion.com/a/typeform.html", "hash": "aaaa01",
     "medio": "Expansion", "fecha": "2026-09-25", "idioma": "es",
     "titulo": "Typeform levanta 100 M$", "texto": "x", "flag_fecha": None},
    {"url": "https://reuters.com/b/global-saas.html", "hash": "aaaa02",
     "medio": "Reuters", "fecha": "2026-09-27", "idioma": "en",
     "titulo": "Global SaaS funding", "texto": "x", "flag_fecha": None},
    {"url": "https://incibe.es/c/informe-2025.html", "hash": "aaaa03",
     "medio": "INCIBE", "fecha": "2026-02-09", "idioma": "es",
     "titulo": "Balance 2025", "texto": "x", "flag_fecha": None},
]

INFORME = """---
region: es
verticales: [ia-aplicada, ciberseguridad]
modo: full
fecha_corte: 2026-09-28
fuentes_totales: 3
---

# Informe: prueba

## 1. Resumen ejecutivo

Lectura principal. Vacios declarados: semiconductores sin evidencia regional.

## 2. Panorama por vertical

### 2.1 IA aplicada

| Campo | Dato | Calidad |
|---|---|---|
| Empresas | Telefonica Tech (Madrid), IA y cloud [E01] | tipo B |
| Empresas | Signalyst B, IA clinica, 40 empleados | tipo D, autodeclarado |
| Empresas | Startup fantasma que no existe [E04] | tipo B |
| Financiacion | <sin evidencia regional> | - |

## 3. Benchmarks globales

| Referencia global | Dato | Equivalente en Espana |
|---|---|---|
| Media Serie A UE [E02] | 6,2 M EUR | <sin equivalente publico> |

## 4. Tesis y tension

**Tesis 1.** Lectura, no hecho. Apoyada en [E01].

## 5. Riesgos y limites

Sesgo de fuente: 1 de 3 es comunicacion de empresa.

## 6. Registro de evidencia

| Clave | URL | Medio | Fecha | Idioma | Peso |
|---|---|---|---|---|---|
| E01 | https://expansion.com/a/typeform.html | Expansion | 2026-09-25 | es | B |
| E02 | https://reuters.com/b/global-saas.html | Reuters | 2026-09-27 | en | B |
| E03 | https://incibe.es/c/informe-2025.html | INCIBE | 2026-02-09 | es | A |
| E04 | https://ejemplo-fantasma.com/no-existe | Inventado | 2026-09-28 | es | A |
"""


def main() -> int:
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    ev, inf = TMP / "evidencia.json", TMP / "informe.md"
    ev.write_text(json.dumps(EVIDENCIA, ensure_ascii=False, indent=1), encoding="utf-8")
    inf.write_text(INFORME, encoding="utf-8")

    p = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "evaluar.py"),
         "--informe", str(inf), "--evidencia", str(ev),
         "--json", str(TMP / "metricas.json")],
        capture_output=True, text=True, cwd=RAIZ,
    )
    print(p.stdout)
    if p.stderr.strip():
        print("STDERR:", p.stderr)

    m = json.loads((TMP / "metricas.json").read_text(encoding="utf-8"))
    d = m["detalle"]
    fallos = []

    def check(nombre, cond, extra=""):
        print(("  ok   " if cond else "  FAIL ") + nombre + ("" if cond else f"  {extra}"))
        if not cond:
            fallos.append(nombre)

    print("Comprobaciones del evaluador")
    keys = {x["clave"] for x in d["citas_sin_respaldo"]}
    check("detecta [E04] sin respaldo", "04" in keys, d["citas_sin_respaldo"])
    check("no marca E01 ni E02", not ({"01", "02"} & keys), keys)
    check("acepta las fechas correctas", not d["fechas_no_cuadran"], d["fechas_no_cuadran"])
    check("detecta celda con dato y sin fuente",
          any("Signalyst" in x["celda"] for x in d["celdas_sin_fuente"]), d["celdas_sin_fuente"])
    check("no cuenta la celda vacia como celda sin fuente",
          not any("Financiacion" in x["celda"] for x in d["celdas_sin_fuente"]))
    check("no cuenta la fila de cabeceras", len(d["celdas_sin_fuente"]) == 1,
          d["celdas_sin_fuente"])
    check("detecta [E03] en el registro pero nunca citada",
          "03" in d["registro_sin_citar"], d["registro_sin_citar"])
    check("citas resolubles baja de 1", m["citas_resolubles"] < 1.0, m["citas_resolubles"])
    check("fechas correctas es 1.0", m["fechas_correctas"] == 1.0, m["fechas_correctas"])
    check("estructura completa (estan las 6 secciones)",
          not d["secciones_faltantes"], d["secciones_faltantes"])
    check("devuelve codigo de salida 1 por las citas sin respaldo", p.returncode == 1,
          p.returncode)
    check("el dominio sale en el JSON, y por defecto es sector",
          m.get("dominio") == "sector", m.get("dominio"))
    check("las metricas del dominio laboral salen a null en sector",
          m.get("salarios_verificables") is None and m.get("brecha_declarada") is None,
          f"{m.get('salarios_verificables')} {m.get('brecha_declarada')}")

    # Un informe puede estar fuera del repo: una copia de trabajo, /tmp, el
    # escritorio de quien lo esta revisando. Antes esto reventaba con
    # ValueError en el `print` de la cabecera, que es donde se pega uno a
    # mirar el resultado.
    fuera = Path("/tmp") / "evaluar-fuera-del-repo.md"
    fuera.write_text(inf.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        p2 = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "evaluar.py"),
             "--informe", str(fuera), "--evidencia", str(ev)],
            capture_output=True, text=True, cwd=RAIZ,
        )
        check("no revienta con un informe fuera del repo",
              p2.returncode == 1 and "Traceback" not in p2.stderr,
              p2.stderr.strip()[-120:])
    finally:
        fuera.unlink(missing_ok=True)

    print(f"\n{len(fallos)} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
