---
description: Fase 2 del pipeline. Analiza la evidencia y redacta el informe de sector o de mercado laboral. Argumentos: <ruta de datos/<corrida>>
agent: build
---

Carga la skill `analizar` y ejecuta la fase 2 del pipeline.

Ruta de la corrida: `$ARGUMENTS`

Si `$ARGUMENTS` está vacío, busca el `resumen.md` más reciente bajo `datos/` y
usa su carpeta. Si hay más de uno con la misma fecha, **pregunta**: no elijas
por ti una evidencia ambigua.

Pasos:

1. Carga la skill `analizar`, y con ella `INFORME.md` y `REDACCION.md`.
2. Mira el `resumen.md` y decide el dominio: si habla de ofertas, familias o
   salario, es `laboral` y la plantilla es `INFORME-LABORAL.md` con
   `config/mercado-laboral.json`. Si no, `sector` con `INFORME.md`.
3. Ejecuta los tres comandos de comprobación que pone la skill **antes** de
   redactar. Si `resumen.md` no existe, para y dilo.
4. Redacta el informe en `informes/<fecha>-<region>-<vertical>.md` siguiendo
   la plantilla elegida al pie de la letra, y pon `dominio: <sector|laboral>`
   en el frontmatter.
5. Valida:

```bash
python3 scripts/evaluar.py --informe informes/<fichero>.md --evidencia $ARGUMENTS/evidencia.json
```

En `laboral` el mismo comando mide además `salarios_verificables` y
`brecha_declarada`, y sale con código 1 si alguna de las dos falla.

6. Si el evaluador señala citas sin respaldo o celdas sin fuente, corrige el
   informe. No ajustes el script ni la métrica.
7. Ejecútalo también contra `golden/casos.json` si hay casos cuya vertical
   coincida con la de esta corrida:

```bash
python3 scripts/evaluar.py --informe informes/<fichero>.md --evidencia $ARGUMENTS/evidencia.json --golden
```

En el dominio laboral, los casos de golden se localizan por `familia`, no por
`vertical`, y el propio script marca con `*` los que encajan con la corrida.

Al final dame dos cosas y solo dos: la métrica de citas resolubles y qué
vacíos se declararon. Lo demás está en el fichero.
