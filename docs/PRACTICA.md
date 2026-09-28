# Practica: un agente que audita lo que dice

Este repo es el entregable de una practica de agente. El encargo tiene dos
caras y aqui estan las dos.

1. **Un pipeline que ya funciona** para informes del sector tecnologico, y que
   se audita con metricas automaticas y con un golden set de fallos reales.
2. **Un segundo dominio**: el mercado laboral de DAM y ASIR en Galicia, con su
   config, su plantilla y dos metricas que solo existen ahi.

Lo que se entrega esta escrito en `AGENTS.md` (reparto de trabajo), en
`GLOSSARY.md` (las palabras que se usan con dos sentidos) y en `docs/ADR-*.md`
(las decisiones que cambiaron la forma del sistema). Este documento es el
**manual de uso**: que se hace, en que orden, y como se sabe que ha salido bien.

## Que hay que saber antes de empezar

- Un informe con una cita inventada **no vale**, por muy bueno que sea el
  resto. Por eso `citas_resolubles` es binaria y no un porcentaje: 0.95 quiere
  decir que hay una cita falsa.
- La fase 2 **no busca**. Si falta un dato, se queda vacio y se declara. Esa es
  la frontera que hace auditable el informe, y es lo primero que se rompe.
- Un hueco declarado es un hallazgo. Un hueco rellenado es una mentira.

## 0. Preparar (10 min)

```bash
python3 -c "import requests, bs4; print('ok')"   # o: pip install -r requirements.txt
python3 scripts/test_pipeline.py                  # 31 pruebas offline
python3 scripts/test_evaluar.py                   # 12 pruebas del evaluador
python3 scripts/test_laboral.py                   # 35 pruebas del dominio laboral
python3 scripts/revisar_docs.py                   # linter: debe dar 0 problemas
```

Si `revisar_docs.py` lista cientos de problemas en ficheros que no has
escrito, casi siempre es que esta recorriendo `node_modules`. Ya esta
excluido; si vuelve a pasar, mira `IGNORAR` en el script.

## 1. Fase 1: `/recolectar`

Sector:

```bash
/recolectar ES fintech full
```

Laboral:

```bash
/recolectar galicia dam quick laboral
```

Si te han dado ficheros (lo normal en el dominio laboral), ingestalos
directamente, en este orden, y antes de salir a la red:

```bash
python3 scripts/fetch.py --csv ofertas.csv --salida datos/laboral-2026-09-28/evidencia.json
python3 scripts/fetch.py --pdf informe.pdf --salida datos/laboral-2026-09-28/evidencia.json
python3 scripts/fetch.py --transcript charla.vtt --canal Devoxx --fecha 2026-06-10 \
    --salida datos/laboral-2026-09-28/evidencia.json
```

La corrida deja dos ficheros: `evidencia.json` y `resumen.md`. El `resumen.md`
tiene una linea de vacios que **manda**: es lo que la fase 2 puede callar a
propósito. Si esa linea no esta, la fase 2 no puede distinguir "no lo he
buscado" de "no lo se", y esa es la diferencia entre un informe y una
adivinanza.

Las fuentes de `config/mercado-laboral.json` llegaron con `verificado: false` y
`url: null`. **Es un veto, no un olvido**, y el 2026-09-28 se levanto fuente a
fuente: 12 de 16 verificadas con peticion HTTP real y con la validacion del
certificado activada (cada una con `url`, `verificado_el` y `metodo_verificacion`),
y 4 que siguen sin verificar. Verificar
es abrir la URL, mirar la fecha y comprobar que la fuente sigue viva. Si al
verificar resulta que el nombre del enunciado no es el oficial, se corrige en la
config con la correccion anotada, nunca de memoria: asi se corrigieron "Portal
Emprego" (que es **Emprego Galicia**, y en `emprego.xunta.gal`), OSIMGA (que
incluye "e da Modernización") y el "servicio autonomico" (que son el SEPE y el
Servizo Público de Emprego de Galicia).

Las cuatro que siguen sin verificar no se pueden citar. Dos devuelven 403 a
robots, OSIMGA tiene una cadena TLS que no valida desde este entorno, y la cuarta
no es una fuente sino una categoria. Los tres son bloqueos, no ausencias, y por eso
no se ha marcado ninguna como verificada: `fetch.py` no salta la validacion del
certificado, ni para inventar una URL, ni para entrar en un portal.

## 2. Fase 2: `/analizar`

```bash
/analizar datos/laboral-2026-09-28
```

El dominio se decide leyendo el `resumen.md`, no por el nombre de la carpeta:

| El resumen habla de | Dominio | Plantilla |
|---|---|---|
| verticales, empresas, mercado | `sector` | `INFORME.md` |
| ofertas, familias, DAM/ASIR, salario | `laboral` | `INFORME-LABORAL.md` |

En el informe laboral, las tres cosas que mas se cuelan:

- **El rango sin `n=`.** "De 30.000 a 45.000 EUR" suena a mercado y son dos
  ofertas. Pon `n=` y di de que fecha.
- **La media con muestra pequena.** Con 4 ofertas no hay media. Hay un rango y
  una advertencia.
- **La cita que resuelve y no respalda.** Un panel de ofertas donde el salario
  no aparece es una URL valida con una cifra inventada al lado. El evaluador lo
  comprueba; si lo dice, no discutas.

## 3. Evaluar

```bash
python3 scripts/evaluar.py \
  --informe informes/laboral/2026-09-28.md \
  --evidencia datos/laboral-2026-09-28/evidencia.json \
  --json datos/laboral-2026-09-28/metricas.json \
  --golden golden/casos.json --caso G15
```

Devuelve codigo 1 si hay citas sin respaldo, fechas que no cuadran, secciones
que faltan, o (en `laboral`) celdas de salario no auditables o una familia sin
seccion de brecha.

Antes de mirar el porcentaje, mira `detalle`: dice linea y clave. El porcentaje
solo dice que algo va mal; el detalle dice que.

## 4. Iterar contra el golden set

Este es el bucle, y es la parte de la practica que mas se aprende:

```
escribir caso  ->  correr  ->  medir  ->  ajustar prompt  ->  repetir
```

El golden set tiene 18 casos: G01-G12 de `sector` (se localizan por `vertical`)
y G13-G18 de `laboral` (se localizan por `familia`). El evaluador marca con `*`
los que encajan con la corrida y avisa si el caso y el informe no son del mismo
ambito.

Tres reglas que no se rompen:

- **El caso se escribe antes que el arreglo del prompt.** Al reves, el caso se
  ajusta a lo que el prompt ya hace y no prueba nada.
- **Un cambio de prompt, un caso nuevo.** Si cambias dos cosas, no sabes cual
  ha arreglado el fallo.
- **Los casos se anaden, no se editan.** Editar uno invalida las metricas
  anteriores sin dejar rastro.

## 5. Los cinco dias, y quien hace que

Un reparto de trabajo que funciona: una persona, tres gorras, por turnos.

| Dia | Gorra | Que sale |
|---|---|---|
| 1 | recolector | corrida completa de un dominio, con `resumen.md` con linea de vacios |
| 2 | recolector | ingesta de ficheros: CSV, PDF, transcripcion. El golden set no se toca |
| 3 | redactor | primer informe y sus metricas. Se escribe el primer caso que falla |
| 4 | auditor | casos G13+ del dominio laboral, parte 2 de la rubrica, primer ADR |
| 5 | entrega | empaquetado, indice con sha256, y revision de que el informe no promete mas de lo que demuestra |

Las tres gorras estan en `AGENTS.md`. La regla que las separa es una sola: cada
una no toca lo que hace la anterior. El recolector no redacta, el redactor no
verifica fuentes, el auditor no arregla prompts.

## 6. Entregar

```bash
python3 scripts/empaquetar.py
```

Deja tres zips en `dist/`, cada uno con `INDICE.md` y `INDICE.sha256` dentro:

| Paquete | Para quien |
|---|---|
| `kb-<fecha>.zip` | quien quiera auditar: config, scripts, plantillas, el informe, su evidencia y su resumen |
| `agente-<fecha>.zip` | quien quiera las dos fases en su proyecto: solo `.opencode/` |
| `docs-<fecha>.zip` | el profesor: ADR, rubrica, glosario, esta guia |

Para comprobar que nadie ha tocado el paquete por el camino:

```bash
unzip -q kb-<fecha>.zip -d /tmp/verificacion && cd /tmp/verificacion && sha256sum -c INDICE.sha256
```

Si algo falla, el paquete no es el que se entrego. Eso es mejor que un paquete
sin indice, donde no hay forma de saber.

## Donde esta el limite de todo esto

Las metricas automaticas no dicen si la tesis del informe es correcta. Dicen si
esta respaldada. Un informe puede tener las seis metricas a 1.0 y su tesis ser
falsa, y por eso la parte 2 de `golden/rubrica.md` la puntua una persona.

Y en el dominio laboral hay un limite mas: cuatro ofertas de un portal no son el
mercado. El informe puede ser impecable y seguir siendo inútil para decidir. La
forma de decirlo no es pedir mas fuentes, es decirlo en la seccion de riesgos.
