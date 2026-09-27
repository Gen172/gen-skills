---
description: Fase 2 del pipeline. Analiza la evidencia y redacta el informe. Argumentos: <ruta de datos/<corrida>>
agent: build
---

Carga la skill `analizar` y ejecuta la fase 2 del pipeline.

Ruta de la corrida: `$ARGUMENTS`

Si `$ARGUMENTS` está vacío, busca el `resumen.md` más reciente bajo `datos/` y
usa su carpeta. Si hay más de uno con la misma fecha, **pregunta**: no elijas
por ti una evidencia ambigua.

Pasos:

1. Carga la skill `analizar`, y con ella `INFORME.md` y `REDACCION.md`.
2. Ejecuta los tres comandos de comprobación que pone la skill **antes** de
   redactar. Si `resumen.md` no existe, para y dilo.
3. Redacta el informe en `informes/<fecha>-<region>-<vertical>.md` siguiendo
   la plantilla de `INFORME.md` al pie de la letra.
4. Valida:

```bash
python3 scripts/evaluar.py --informe informes/<fichero>.md --evidencia $ARGUMENTS/evidencia.json
```

5. Si el evaluador señala citas sin respaldo o celdas sin fuente, corrige el
   informe. No ajustes el script ni la métrica.
6. Ejecútalo también contra `golden/casos.json` si hay casos cuya vertical
   coincida con la de esta corrida:

```bash
python3 scripts/evaluar.py --informe informes/<fichero>.md --evidencia $ARGUMENTS/evidencia.json --golden
```

Al final dame dos cosas y solo dos: la métrica de citas resolubles y qué
vacíos se declararon. Lo demás está en el fichero.
