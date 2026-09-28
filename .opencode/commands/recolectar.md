---
description: Fase 1 del pipeline. Recolecta evidencia del sector tecnológico o del mercado laboral. Argumentos: <region> <vertical o familia> <modo: quick|full> [laboral]
agent: build
---

Carga la skill `recolectar` y ejecuta la fase 1 del pipeline.

Parámetros recibidos: `$ARGUMENTS`

Si `$ARGUMENTS` está vacío, no asumas: pregunta por región, vertical y modo,
y ofrece como valores por defecto los de `config/verticales.json`.

Si los argumentos contienen `laboral` (o una región `galicia`, o una familia
`dam`/`asir`), es el dominio laboral: lee `config/mercado-laboral.json` en vez
de `config/verticales.json`, y pregunta por región, familia y modo.

Pasos:

1. Carga la skill `recolectar` y sigue su procedimiento al pie de la letra.
2. Antes de salir a la red, ejecuta `python3 scripts/fetch.py --dump-cache` y
   lee `config/semilla-espana.json`. En el dominio laboral no hay semilla de
   empresas: la semilla es `config/mercado-laboral.json`, y sus fuentes llegan
   con su `verificado: false` hasta que tú compruebes URL, fecha y que la fuente
   siga viva. El 2026-09-28 ya están verificadas 13 de 16: las demás, y las que
   estén bloqueadas a robots, siguen sin poder citarse.
3. Al terminar, la corrida debe haber dejado:
   - `datos/<corrida>/evidencia.json`
   - `datos/<corrida>/resumen.md`
4. Muéstrame el `resumen.md` entero. La línea de vacíos es la que decide qué
   puede hacer la fase 2.

No redactes nada del informe. Si quieres adelantar una conclusión, no la
adelantes: así queda registrada como pendiente para la fase 2, con evidencia.
