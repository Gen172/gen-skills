# Informes comparativos: sector tecnologico espanol frente al mundo

Pipeline de dos fases para producir informes comparativos del sector
tecnologico espanol frente a benchmarks globales, con evidencia trazable y
evaluacion reproducible.

Consta de dos skills de OpenCode y un evaluador. Se ejecuta bajo demanda.

## Requisitos

- `python3` (probado en 3.14) con `requests`, `beautifulsoup4` y `lxml`
- OpenCode 1.18 o superior
- Acceso a red para la fase 1

## Uso

```bash
# Fase 1: buscar, descargar, deduplicar y calificar evidencia
/recolectar ES fintech full

# Fase 2: redactar el informe desde la evidencia. No busca.
/analizar datos/fintech-2026-09-28
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

## Estructura

```
.opencode/
  skills/recolectar/     fase 1: busqueda, descarga, calificacion
  skills/analizar/       fase 2: redaccion desde evidencia. No busca.
  commands/              /recolectar y /analizar
config/
  verticales.json        6 verticales x 4 campos, con pesos de fuente y riesgos
  semilla-espana.json    47 nodos verificados + 8 no encontrados, con fecha
scripts/
  fetch.py               RSS/Atom/HTML -> evidencia.json, con cache
  metadatos.py           canonicalizacion de URL, hash, idioma, fechas
  evaluar.py             las seis metricas automaticas
  revisar_docs.py        linter de caracteres, JSON, frontmatter
  test_pipeline.py       31 pruebas offline
  test_evaluar.py        12 pruebas del evaluador, con fallos plantados
golden/
  casos.json             12 casos de fallo, con fecha de corte
  rubrica.md             parte automatica y parte humana, con iteracion
docs/ADR-001..005        las decisiones que cambiaron la forma del sistema
datos/                   generado, ignorado por git
informes/                versionado
AGENTS.md                reparto de trabajo y reglas que no se negocian
GLOSSARY.md              benchmark vs comparable, vacio vs cero, etc.
```

## Reglas del juego

- Ninguna cifra sin fuente `[Enn]`.
- Ninguna cifra sin unidad, periodicidad y fecha.
- Los huecos se declaran. Un hueco es informacion.
- Un informe sin seccion de limites no esta terminado.
- El golden set se escribe antes de arreglar el prompt.

Ver `AGENTS.md` para el reparto de trabajo y `golden/rubrica.md` para como se
evalua.

## Estado

Las dos skills, los scripts y el golden set estan listos. La semilla se verifico
el 2026-09-28: 47 nodos con URL comprobada, 8 que no existen o tenían el nombre
errado (retirados a `verificacion.no_encontrados`, con el motivo) y 2 candidatos
documentados pero sin URL, en `verificacion.candidatos_sin_url`. Cada nodo lleva
`verificado_el` y `metodo_verificacion`, para poder saber como se comprobó y
cuándo hay que repetirlo. La regla del veto sigue igual: un nodo solo sirve
como evidencia si consta su URL, su fecha y que sigue existiendo.

Lo que falta es una corrida completa de extremo a extremo, con red.
