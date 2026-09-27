# AGENTS.md

Instrucciones para cualquier agente (o persona) que trabaje en este repo.

## Que es esto

Un pipeline de dos fases para informes comparativos del sector tecnologico
espanol frente a benchmarks globales. Se ejecuta bajo demanda, no en bucle.

| Fase | Skill | Comando | Hace |
|---|---|---|---|
| 1 | `recolectar` | `/recolectar` | Busca, descarga, deduplica y califica evidencia |
| 2 | `analizar` | `/analizar` | Redacta el informe desde la evidencia. **No busca** |

La frontera es dura: `analizar` no tiene permiso de buscar. Si necesita un dato
que no esta en `evidencia.json`, se para y lo pide. Esa es la unica forma de que
`citas_resolubles` signifique algo.

## Comandos del dia a dia

```bash
# Fase 1: deja datos/<corrida>/{evidencia.json,resumen.md}
python3 scripts/fetch.py --feed "<RSS>" --salida datos/c1/evidencia.json
python3 scripts/fetch.py --url   "<URL>"  --salida datos/c1/evidencia.json

# Fase 2: redacta informes/<vertical>/<fecha>.md usando la plantilla
# SKILL.md de .opencode/skills/analizar/

# Evaluar (devuelve 1 si algo no llega al umbral)
python3 scripts/evaluar.py --informe informes/x.md --evidencia datos/c1/evidencia.json \
                           --json datos/c1/metricas.json --golden golden/casos.json

# Antes de commitear, siempre:
python3 scripts/revisar_docs.py      # caracteres, JSON, frontmatter
python3 scripts/test_pipeline.py     # 31 pruebas offline
python3 scripts/test_evaluar.py      # 12 pruebas del evaluador
```

## Reparto de trabajo: una persona, tres gorras

No hay tres personas. Hay tres trabajos que se hacen por turnos, y cada uno
tiene una regla propia para no contaminar a los otros dos.

### Gorra 1: recolector

Mantiene `config/semilla-espana.json` y las fuentes de `config/verticales.json`.

- **Regla:** no se amplia la semilla a mano con lo que uno "sabe". Se amplia
  con lo que se ha encontrado y verificado. Si crees que falta una empresa y no
  la has buscado, la anotas como no verificada.
- Un nodo solo pasa a `verificado: true` cuando constan URL, fecha de
  verificacion, y que se ha comprobado que sigue existiendo y operando.
- Revisa la semilla cada 4 semanas: comprueba que los nodos verificados siguen
  existiendo y operating, y añade los que hayan aparecido.

### Gorra 2: constructor del golden set

Mantiene `golden/casos.json`.

- **Regla:** escribe primero el fallo, despues el prompt que lo arregla. Al
  reves, el caso se ajusta a lo que el prompt ya hace y no prueba nada.
- Anade casos, no los edites (ver `golden/rubrica.md`).
- Prioriza un caso nuevo cuando `evaluar.py` marca un fallo que no sabemos
  detectar: el linter es solo la parte que sabemos automatizar.

### Gorra 3: auditor

Puntua los informes con `golden/rubrica.md` y escribe `docs/ADR` cuando algo
cambia de forma permanente.

- **Regla:** un ADR se escribe cuando cambia una decision, no cuando se
  ejecuta. Los experimentos que salen mal no son ADR; si exigen un parrafo para
  explicar por que se descartaron, no eran decisiones que tomar.
- Si el auditor se encuentra con que un informe "no cuadra" pero todas las
  metricas pasan, la parte 2 de la rubrica esta mal, no el informe.

## Reglas que no se negocian

1. **Ninguna cifra sin fuente.** Toda celda de datos lleva `[Enn]`.
2. **Ninguna cifra sin unidad, periodicidad y fecha.** "Ha crecido" no es un
   dato. `12,4 M EUR en 2025` si.
3. **Los vacios se declaran.** Un hueco es informacion; esconderlo en la tabla
   es mentir por omision.
4. **Un informe sin seccion de limites no esta terminado.** Ver G12.
5. **El golden set se escribe antes de arreglar el prompt.** Sin caso, un
   cambio de prompt es una opinion.
6. **`datos/` no se versiona.** Es reproducible, y versionarlo mete ruido
   generado en el historico.

## Cuando algo falla

1. `python3 scripts/revisar_docs.py` primero. Caracteres corruptos y JSON
   invalido son la causa mas frecuente de "el agente va raro".
2. Si el fallo es de metricas, mira `--json` y `detalle` antes que el
   porcentaje. El detalle dice linea y clave; el porcentaje solo dice que algo
   va mal.
3. Si el fallo es una cita sin respaldo, mira si `evidencia.json` tiene la URL.
   Casi siempre es que se cita de memoria en vez de de la evidencia.

## Ficheros que no se tocan sin motivo

- `.gitignore` — si `datos/` deja de estar ignorado, el historico se llena.
- `config/verticales.json` — cambiarlo cambia la rúbrica; requiere ADR.
- `golden/casos.json` — editar un caso invalida las metricas anteriores.
