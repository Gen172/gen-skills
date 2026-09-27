---
description: Fase 1 del pipeline. Recolecta evidencia del sector tecnológico. Argumentos: <region: es|global> <vertical: id o todas> <modo: quick|full>
agent: build
---

Carga la skill `recolectar` y ejecuta la fase 1 del pipeline.

Parámetros recibidos: `$ARGUMENTS`

Si `$ARGUMENTS` está vacío, no asumas: pregunta por región, vertical y modo,
y ofrece como valores por defecto los de `config/verticales.json`.

Pasos:

1. Carga la skill `recolectar` y sigue su procedimiento al pie de la letra.
2. Antes de salir a la red, ejecuta `python3 scripts/fetch.py --dump-cache` y
   lee `config/semilla-espana.json`.
3. Al terminar, la corrida debe haber dejado:
   - `datos/<corrida>/evidencia.json`
   - `datos/<corrida>/resumen.md`
4. Muéstrame el `resumen.md` entero. La línea de vacíos es la que decide qué
   puede hacer la fase 2.

No redactes nada del informe. Si quieres adelantar una conclusión, no la
adelantes: así queda registrada como pendiente para la fase 2, con evidencia.
