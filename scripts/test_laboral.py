"""Prueba del dominio laboral: ingesta de ficheros locales y metricas propias.

Cubre lo que el dominio sectorial no tiene: CSV de ofertas, PDF, transcripcion
y las dos metricas que solo existen aqui (`salarios_verificables`,
`brecha_declarada`). Offline y determinista, como el resto de la suite.

    python3 scripts/test_laboral.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TMP = RAIZ / "datos" / "test-laboral"
sys.path.insert(0, str(RAIZ / "scripts"))

import fetch  # noqa: E402

CSV = """Puesto;Empresa;Salario;Experiencia;Modalidad;Provincia;Fecha de publicación;Tecnologías;URL;Portal
"Desarrollador/a Flutter";Grupo Ejemplo;"30.000-45.000 EUR/año";"3 años";Híbrido;A Coruña;12/09/2026;"Flutter, Dart, SQL";"https://empleo.ejemplo.es/o/1";"Portal Emprego"
"Técnico/a de sistemas";Consultora Norte;"28.000 EUR/mes";"2 años";Presencial;Vigo;05/09/2026;"Windows Server";"https://empleo.ejemplo.es/o/2";"Tecnoempleo"
"Soporte usuario";Ayuntamiento;"sin salario";"sin experiencia";Presencial;Lugo;01/09/2026;"Office";"https://empleo.ejemplo.es/o/3";"Portal Emprego"
"DevOps junior";Startup Sur;"35.000 EUR/año";"0 años";Remoto;Pontevedra;2026-08-20;"Docker, Kubernetes";"https://empleo.ejemplo.es/o/4";"LinkedIn Jobs"
"""

VTT = """WEBVTT

Kind: captions
Language: es

00:00:01.000 --> 00:00:04.500
<c>Kubernetes</c> es lo que mas se pide en backend.

00:00:04.500 --> 00:00:08.000
Y el 87% de los equipos lo usan en produccion.

NOTE transcripcion automatica

00:00:08.000 --> 00:00:11.000
[aplauso] El wages gap es del 12% en nuestro sector.
"""

BUENO = """---
dominio: laboral
region: galicia
familias: [dam, asir]
modo: quick
fecha_corte: 2026-09-28
ofertas_con_salario: 3
n_salario: 3
---

# Informe: mercado laboral DAM/ASIR en Galicia — 2026-09-28

## 1. Resumen ejecutivo

- **Lectura principal.** Tres ofertas con salario publicado de cuatro, todas de agosto y septiembre de 2026.
- **Vacios declarados.** ASIR no tiene ofertas verificables en la ventana: no hay celda de salario que publicar.

## 2. Demanda actual por familia

### 2.1 DAM

| Campo | Dato | Calidad |
|---|---|---|
| Vacantes | 2 ofertas con fecha entre 2026-08-20 y 2026-09-12 en el Portal Emprego y Tecnoempleo [E01] [E02] | D |
| Salario | 30.000-45.000 EUR brutos anuales, rango observado, n=2, ofertas de 2026-09 [E01] | D. Muestra de 2: no da media |

### 2.2 ASIR

| Campo | Dato | Calidad |
|---|---|---|
| Vacantes | <sin evidencia> | — |
| Salario | <las ofertas no publican salario> | — |

## 3. Senales de horizonte 2-3 anos

| Senal | Que proyecta | Fuente | Tipo de dato |
|---|---|---|---|
| Contenedores | Uso en repos publicos, no contratacion [E06] | Charla de Devoxx | D. Una persona |

## 4. Brecha de habilidades

### 4.1 DAM

| Competencia | Se pide hoy | Se anuncia para 2-3 anos | Veredicto | Que haria falta en el plan |
|---|---|---|---|---|
| Contenedores | 1 de 2 ofertas [E01] | Kubernetes entre las mas anunciadas [E06] | Senal debil: un lado es una oferta suelta | Subir contenedores a troncal |
| Monitorizacion | Ninguna de las 2 lo pide [E03] | <sin evidencia> | No comparable: solo hay un lado | No se puede decidir con esta ventana |

### 4.2 ASIR

| Competencia | Se pide hoy | Se anuncia para 2-3 anos | Veredicto | Que haria falta en el plan |
|---|---|---|---|---|
| Monitorizacion | <sin evidencia> | <sin evidencia> | No comparable: no hay ninguna de las dos lados | No se puede decidir con esta ventana |

## 5. Riesgos y limites

- **Muestra.** Cuatro ofertas de tres portales. No es el mercado.
- **Salario.** n=3: hay rango, no hay media.
- **Huecos.** ASIR entero.

## 6. Registro de evidencia

| Clave | URL o clave local | Medio | Fecha | Idioma | Peso |
|---|---|---|---|---|---|
| E01 | https://empleo.ejemplo.es/o/1 | Portal Emprego | 2026-09-12 | es | D |
| E02 | https://empleo.ejemplo.es/o/2 | Tecnoempleo | 2026-09-05 | es | D |
| E03 | https://empleo.ejemplo.es/o/3 | Portal Emprego | 2026-09-01 | es | D |
| E06 | archivo:charla.vtt | Devoxx | 2026-06-10 | es | D |
"""

# Los tres fallos que hay que detectar: rango sin n, n= sobre una oferta que no
# publica salario, y una familia sin subseccion en la brecha.
MALO = BUENO.replace(
    "30.000-45.000 EUR brutos anuales, rango observado, n=2, ofertas de 2026-09 [E01]",
    "salarios de 30.000-45.000 EUR brutos anuales en 2026 [E03]",
).replace(
    "| 1 de 2 ofertas [E01] | Kubernetes entre las mas anunciadas [E06] |",
    "| 1 de 2 ofertas [E04] | Kubernetes entre las mas anunciadas [E06] |",
).replace("### 4.2 ASIR", "### 4.2 Admin").replace(
    "## 4. Brecha de habilidades", "## 4. Notas")

ok = fallos = 0


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    global ok, fallos
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallos += 1
        print(f"  FAIL {nombre}  {detalle}")


def main() -> int:
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    csv, vtt = TMP / "ofertas.csv", TMP / "charla.vtt"
    csv.write_text(CSV, encoding="utf-8")
    vtt.write_text(VTT, encoding="utf-8")

    print("1. Ingesta local")
    p = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "fetch.py"),
         "--csv", str(csv), "--transcript", str(vtt),
         "--canal", "Devoxx", "--fecha", "2026-06-10",
         "--salida", str(TMP / "evidencia.json")],
        capture_output=True, text=True, cwd=RAIZ,
    )
    ev = json.loads((TMP / "evidencia.json").read_text(encoding="utf-8"))
    check("fetch sale con 0", p.returncode == 0, p.stderr)
    check("4 ofertas + 1 transcripcion", len(ev) == 5, f"hay {len(ev)}")

    print("2. Salario estructurado")
    con_sal = [r for r in ev if (r.get("datos") or {}).get("salario_eur")]
    check("3 ofertas con salario", len(con_sal) == 3, f"hay {len(con_sal)}")
    rango = con_sal[0]["datos"]["salario_eur"]
    check("rango 30.000-45.000", (rango["min"], rango["max"]) == (30000.0, 45000.0),
          str(rango))
    check("periodicidad ano", rango["periodicidad"] == "ano", str(rango))
    mensual = next(r for r in con_sal if r["datos"]["salario_eur"]["periodicidad"] == "mes")
    check("mensual detectada", mensual["datos"]["salario_eur"]["max"] is None,
          str(mensual["datos"]["salario_eur"]))
    sin = [r for r in ev if r["datos"].get("salario_texto") == "sin salario"]
    check("'sin salario' no se convierte en 0", sin and not sin[0]["datos"].get("salario_eur"),
          str(sin[0]["datos"] if sin else "no esta"))
    check("fechas de las cuatro ofertas", all(r["fecha"] for r in ev[:4]))

    print("3. Clave local y hash")
    locales = [r for r in ev if r["url"].startswith("archivo:")]
    check("la transcripcion usa clave local", len(locales) == 1, str(len(locales)))
    hashes = {r["hash"] for r in ev}
    check("los 5 hashes son distintos", len(hashes) == 5, str(len(hashes)))
    check("la transcripcion va limpia de marcas de tiempo",
          "-->" not in locales[0]["texto"] and "aplauso" not in locales[0]["texto"],
          locales[0]["texto"][:60])
    check("la transcripcion avisa de que es automatica",
          any("transcripcion_automatica" in n for n in locales[0]["notas"]),
          str(locales[0]["notas"]))

    print("4. Informe laboral completo")
    inf = TMP / "laboral.md"
    inf.write_text(BUENO, encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "evaluar.py"),
         "--informe", str(inf), "--evidencia", str(TMP / "evidencia.json"),
         "--golden", str(RAIZ / "golden" / "casos.json"), "--caso", "G15",
         "--json", str(TMP / "m1.json")],
        capture_output=True, text=True, cwd=RAIZ,
    )
    m = json.loads((TMP / "m1.json").read_text(encoding="utf-8"))
    print(p.stdout)
    check("detecta el dominio", m["dominio"] == "laboral", m.get("dominio"))
    check("citas resolubles 1.0 (incluye la clave local)", m["citas_resolubles"] == 1.0,
          str(m["citas_resolubles"]))
    check("estructura completa 1.0", m["estructura_completa"] == 1.0,
          str(m["estructura_completa"]) + str(m["detalle"]["secciones_faltantes"]))
    check("celdas sin fuente 0", m["celdas_sin_fuente"] == 0.0,
          str(m["detalle"]["celdas_sin_fuente"]))
    check("salarios verificables 1.0", m["salarios_verificables"] == 1.0,
          str(m["detalle"]["salarios_no_auditables"]))
    check("sin fuentes fantasma en el registro bueno",
          not m["detalle"]["registro_sin_citar"], m["detalle"]["registro_sin_citar"])
    check("brecha declarada 1.0", m["brecha_declarada"] == 1.0,
          str(m["detalle"]["brecha_incompleta"]))
    check("sale con 0", p.returncode == 0, str(p.returncode))
    # G15 es un caso de la familia `asir`, que este informe declara. El enganche
    # con el golden set tiene que ser por familia y no por vertical.
    check("el caso de golden encaja por familia, no por vertical",
          "Caso G15" in p.stdout and "AVISO" not in p.stdout,
          p.stdout.split("Caso G15")[-1][:120])

    print("5. Informe laboral con los tres fallos")
    mal = TMP / "laboral-malo.md"
    mal.write_text(MALO, encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "evaluar.py"),
         "--informe", str(mal), "--evidencia", str(TMP / "evidencia.json"),
         "--json", str(TMP / "m2.json")],
        capture_output=True, text=True, cwd=RAIZ,
    )
    m2 = json.loads((TMP / "m2.json").read_text(encoding="utf-8"))
    print(p.stdout)
    d2 = m2["detalle"]
    motivos = {f for x in d2["salarios_no_auditables"] for f in x["faltan"]}
    check("detecta el rango sin n=", "sin n= (muestra)" in motivos, motivos)
    check("detecta la oferta que no publica salario",
          "ninguna de las fuentes citadas publica un salario" in motivos, motivos)
    check("detecta la familia que no aparece en la brecha",
          any("asir" in b for b in d2["brecha_incompleta"]), d2["brecha_incompleta"])
    check("detecta la seccion que no esta", d2["secciones_faltantes"], d2["secciones_faltantes"])
    check("sale con 1", p.returncode == 1, str(p.returncode))

    print("6. Config del dominio")
    cfg = json.loads((RAIZ / "config" / "mercado-laboral.json").read_text(encoding="utf-8"))
    check("2 familias", [f["id"] for f in cfg["familias"]] == ["dam", "asir"])
    check("6 campos", len(cfg["campos"]) == 6, str(len(cfg["campos"])))
    fuentes = [f for grupo in cfg["fuentes"].values() if isinstance(grupo, list) for f in grupo]
    # La regla, no la foto: una fuente verificada tiene que poder contarse como
    # verificada (url + fecha + metodo). Y tiene que quedar alguna sin verificar,
    # porque el veto de AGENTS.md no se retira: se comprueba fuente a fuente.
    verificadas = [f for f in fuentes if f.get("verificado")]
    check("toda fuente verificada tiene url, fecha y metodo",
          all(f.get("url") and f.get("verificado_el") and f.get("metodo_verificacion")
              for f in verificadas),
          str([f["nombre"] for f in verificadas
               if not (f.get("url") and f.get("verificado_el") and f.get("metodo_verificacion"))]))
    check("toda fuente sin verificar dice por que",
          all(f.get("motivo_no_verificacion") for f in fuentes if not f.get("verificado")),
          str([f["nombre"] for f in fuentes
               if not f.get("verificado") and not f.get("motivo_no_verificacion")]))
    check("sigue habiendo fuentes sin verificar (el veto no se retira)",
          len(verificadas) < len(fuentes), f"{len(verificadas)}/{len(fuentes)}")
    check("ningun nombre corregido se pierde: van con su correccion anotada",
          all(f.get("correccion") and f.get("nombre_del_enunciado")
              for f in fuentes if "nombre_del_enunciado" in f),
          str([f["nombre"] for f in fuentes
               if "nombre_del_enunciado" in f and not f.get("correccion")]))
    check("el mapa CSV cubre los 6 campos de recuento",
          set(cfg["csv"]["campos_de_conteo"]) <= set(cfg["csv"]["columnas"]))

    print("7. Una corrida sin ninguna fuente utilizable")
    p = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "fetch.py"),
         "--csv", str(TMP / "no-existe.csv"), "--salida", str(TMP / "vacia.json")],
        capture_output=True, text=True, cwd=RAIZ,
    )
    check("fetch sale con 1 si todo falla", p.returncode == 1, str(p.returncode))
    check("y aun asi deja constancia del error en el fichero",
          all(r.get("error") for r in json.loads(
              (TMP / "vacia.json").read_text(encoding="utf-8"))),
          (TMP / "vacia.json").read_text(encoding="utf-8")[:120])

    shutil.rmtree(TMP, ignore_errors=True)
    print(f"\n{ok} ok, {fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
