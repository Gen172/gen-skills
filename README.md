# Informes con evidencia: sector tecnologico y mercado laboral

Pipeline de dos fases para producir informes **comparativos con evidencia
trazable**, en dos dominios: el sector tecnologico espanol frente a benchmarks
globales, y el mercado laboral de DAM y ASIR en Galicia frente a Espana y el
mundo.

Consta de dos skills de OpenCode y un evaluador. Se ejecuta bajo demanda.

La idea que sostiene todo: **cada dato del informe lleva la clave de la fuente
que lo respalda, y un script comprueba que esa clave existe en la evidencia**.
Un informe puede ser malo, pero no puede ser irreal sin que se note.

## Requisitos

- `python3` (probado en 3.14) con `requests`, `beautifulsoup4` y `lxml`
- `pdftotext` (poppler-utils) para la ruta `--pdf`. Opcional: sin el, un PDF
  escanea y se registra como tal
- OpenCode 1.18 o superior
- Acceso a red para la fase 1

## Uso

```bash
# Fase 1: buscar, descargar, deduplicar y calificar evidencia
/recolectar ES fintech full

# Fase 1, dominio laboral
/recolectar galicia dam quick laboral

# Fase 2: redacta el informe desde la evidencia. No busca.
/analizar datos/fintech-2026-09-28
```

En el dominio laboral la fuente primaria suele ser un fichero, y se ingiere
directamente, sin red:

```bash
python3 scripts/fetch.py --csv ofertas.csv --salida datos/l-2026-09-28/evidencia.json
python3 scripts/fetch.py --pdf informe.pdf --salida datos/l-2026-09-28/evidencia.json
python3 scripts/fetch.py --transcript charla.vtt --canal Devoxx --fecha 2026-06-10 \
    --salida datos/l-2026-09-28/evidencia.json
```

Fase 1 deja `datos/<corrida>/evidencia.json` y `datos/<corrida>/resumen.md`.
Fase 2 deja `informes/<vertical>/<fecha>.md`.

El informe se puntua:

```bash
python3 scripts/evaluar.py \
  --informe informes/fintech/2026-09-28.md \
  --evidencia datos/fintech-2026-09-28/evidencia.json \
  --json datos/fintech-2026-09-28/metricas.json \
  --golden golden/casos.json
```

Devuelve codigo de salida 1 si alguna metrica no llega al umbral. Los
porcentajes se miran despues: el campo `detalle` del JSON dice linea y clave.

En `laboral` el mismo comando mide ademas `salarios_verificables` y
`brecha_declarada`, y falla si alguna celda de salario no se puede auditar o si
una familia pedida no tiene subseccion en la tabla de brecha.

## Los dos dominios

| | `sector` (por defecto) | `laboral` |
|---|---|---|
| Config | `verticales.json`: 6 verticales x 4 campos | `mercado-laboral.json`: 2 familias x 6 campos, 3 regiones |
| Plantilla | `INFORME.md` | `INFORME-LABORAL.md` |
| Secciones | panorama, benchmarks, tesis, riesgos | demanda, senales de horizonte, brecha, riesgos |
| Metricas extra | — | `salarios_verificables`, `brecha_declarada` |
| Golden | G01-G12 (por `vertical`) | G13-G18 (por `familia`) |

El dominio se decide por el `resumen.md` de la corrida, no por el nombre de la
carpeta. Ver `docs/ADR-007.md`.

## Estructura

```
.opencode/
  skills/recolectar/     fase 1: busqueda, descarga, calificacion, ficheros
  skills/analizar/       fase 2: redaccion desde evidencia. No busca.
    INFORME.md           plantilla de sector
    INFORME-LABORAL.md   plantilla de mercado laboral
    REDACCION.md         reglas de idioma y citacion
  commands/              /recolectar y /analizar
config/
  verticales.json        6 verticales x 4 campos, con pesos de fuente y riesgos
  semilla-espana.json    47 nodos verificados + 8 no encontrados, con fecha
  mercado-laboral.json   DAM/ASIR, 6 campos, mapa de CSV, 16 fuentes (12 verificadas)
scripts/
  fetch.py               RSS/HTML + CSV + PDF + VTT/SRT + YouTube -> evidencia.json
  metadatos.py           canonicalizacion de URL, hash, idioma, fechas
  evaluar.py             las seis metricas automaticas + dos del dominio laboral
  revisar_docs.py        linter de caracteres, JSON, frontmatter, tablas
  empaquetar.py          kb-*.zip, agente-*.zip, docs-*.zip con indice sha256
  test_pipeline.py       31 pruebas offline
  test_evaluar.py        12 pruebas del evaluador, con fallos plantados
  test_laboral.py        35 pruebas del dominio laboral, offline
golden/
  casos.json             18 casos de fallo, con fecha de corte
  rubrica.md             parte automatica y parte humana, con iteracion
docs/ADR-001..007        las decisiones que cambiaron la forma del sistema
docs/PRACTICA.md         manual de uso: que se hace, en que orden, por quien
datos/                   generado, ignorado por git
dist/                    generado, ignorado por git
informes/                versionado
AGENTS.md                reparto de trabajo y reglas que no se negocian
GLOSSARY.md              benchmark vs comparable, vacio vs cero, oferta vs vacante, etc.
```

## Reglas del juego

- Ninguna cifra sin fuente `[Enn]`.
- Ninguna cifra sin unidad, periodicidad y fecha.
- Los huecos se declaran. Un hueco es informacion.
- Un informe sin seccion de limites no esta terminado.
- El golden set se escribe antes de arreglar el prompt.
- En `laboral`, un rango de salario sin `n=` no es un dato.
- Una fuente local se cita con `archivo:<fichero>#<fila>`, nunca con una URL
  inventada.

Ver `AGENTS.md` para el reparto de trabajo, `docs/PRACTICA.md` para el manual de
uso y `golden/rubrica.md` para como se evalua.

## Estado

**Sector.** Las dos skills, los scripts y el golden set estan listos. La semilla
se verifico el 2026-09-28: 47 nodos con URL comprobada, 8 que no existen o
tenian el nombre erroneo (retirados a `verificacion.no_encontrados`, con el
motivo) y 2 candidatos documentados pero sin URL. Cada nodo lleva `verificado_el`
y `metodo_verificacion`. La regla del veto sigue igual: un nodo solo sirve como
evidencia si consta su URL, su fecha y que sigue existiendo. Hay una corrida
completa con red en `datos/c1-2026-09-28/`.

**Laboral.** Config, plantilla, ingesta de ficheros, las dos metricas y los seis
casos de golden estan listos y probados offline (35 pruebas). Las 16 fuentes de
`mercado-laboral.json` se inventariaron el 2026-09-28 con una peticion HTTP real:
**12 verificadas** (con URL, fecha y metodo en cada una) y **4 sin verificar**:
Gartner y World Economic Forum devuelven 403 a robots, OSIMGA tiene una cadena TLS
que no valida desde este entorno, y la cuarta "fuente" no es una fuente sino una
categoria. Los tres bloqueos son bloqueos: no se ha marcado ninguna como verificada
saltandose la comprobacion. Se corrigieron
tres nombres que no eran los oficiales, con la correccion anotada en el propio
fichero: "Portal Emprego" es **Emprego Galicia** (`emprego.xunta.gal`, no
`emprego.gal`), OSIMGA es el "Observatorio da Sociedade da Información **e da
Modernización** de Galicia", y el "servicio autonomico de empleo" son en real el
SEPE y el Servizo Público de Emprego de Galicia. Se anadio el IGE, verificado con
HTTP 200, que es de donde sale la estadística Employment de Galicia.

Lo que queda pendiente es la primera corrida laboral completa: los CSV de ofertas
con fechas y salarios reales.
