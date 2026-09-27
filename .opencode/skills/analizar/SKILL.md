---
name: analizar
description: Fase 2 del pipeline. Toma la evidencia que produjo la skill `recolectar` y la convierte en un informe de sector tecnológico con tabla por vertical, fuente citada celda a celda y vacíos declarados. Úsala SOLO cuando ya existe evidencia.json y resumen.md. NO busques, NO descargues y NO completes huecos con lo que sepas: eso es la skill `recolectar`.
license: MIT
metadata:
  fase: "2 de 2"
  consume: "datos/<corrida>/evidencia.json + resumen.md"
  produce: "informes/<fecha>-<region>-<vertical>.md"
  prohibido: "buscar, descargar, inventar cifras, rellenar huecos"
---

# analizar — juicio, no coleccion

Tu entrada es evidencia ya fechada, deduplicada y marcada. Tu salida es un
informe donde **cada dato se puede audiciar sin fiarse de ti**.

## Frontera dura

| Haces | NO haces |
|---|---|
| Leer la evidencia | Buscar en la red |
| Cruzar y comparar | Descargar nada |
| Redactar con criterio | Completar un hueco de memoria |
| Declarar vacíos | Suavizar una cifra para que quede bien |
| Marcar calidad y región | Citar una URL que no esté en la evidencia |

Si te falta un dato, no lo busques: se queda vacío y se declara. Ese es el
contrato con `recolectar` y es lo que hace el informe auditable.

## Antes de escribir nada

```bash
# 1. Ver la evidencia
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(len(d),'registros');[print(' ',r.get('fecha'),r.get('medio'),(r.get('titulo') or '')[:60]) for r in d[:15]]" datos/<corrida>/evidencia.json

# 2. Leer el resumen de la corrida (sobre todo la línea de vacíos)
cat datos/<corrida>/resumen.md

# 3. Comprobar fechas imposibles y fuentes sin fecha
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));[print(' FECHA:',r['flag_fecha'],r['url']) for r in d if r.get('flag_fecha')]" datos/<corrida>/evidencia.json
```

Si el paso 3 lista `fecha_futura`, **ese registro no existe**: es una página de
borrador o un dato inventado. Se descarta y se anota en el informe.

Si no hay `resumen.md`, **para y dilo**. Sin esa línea de vacíos no puedes
saber qué parte del informe se calla a propósito y qué parte se te ha
olvidado. Son cosas muy distintas y una no se puede arreglar después.

## Reglas de construccion del informe

### Regla 1 — Toda celda con dato lleva su fuente

Formato de celda:

```
| Telefonica Tech | IA aplicada y cloud | Expansion 2026-09-25 [E07] |
```

El código `[E07]` es la clave de la entrada en el Registro de evidencia. Sin
código, la celda no está respaldada. `scripts/evaluar.py` cuenta esto, así que
es medible, no una intención.

### Regla 2 — Toda cifra lleva unidad, periodicidad y fecha

```
mal  : el mercado ha crecido mucho
bien : 3.200 empresas tecnologicas en Espana en 2024 (INE, publicado 2026-03)
```

### Regla 3 — La celda dice de dónde viene el dato, no solo cuánto vale

- `autodeclarado` si sale de la propia empresa
- `metodología desconocida` si la cifra no explica cómo se calculó
- `(fuente de prensa)` si hay dato oficial y has usado el de prensa
- `sin evidencia regional` si la celda regional está vacía

Estas marcas van **en la celda**, no en una nota al pie. Una nota al pie es
lo primero que se deja de leer.

### Regla 4 — Los vacíos se declaran en dos sitios

1. En la propia tabla, con `sin evidencia regional`.
2. En el resumen ejecutivo, con el motivo.

Un vacío escondido en una tabla parece un dato que se te olvidó. Declarado, es
un hallazgo.

### Regla 5 — No compares si no puedes citar los dos lados

Al contrastar España con lo global, ambos lados necesitan fuente. Si solo
tienes el global, no es una comparación: es un benchmark, y va marcado como
tal.

### Regla 6 — No uses lo que sabes

Si sabes algo que no está en `evidencia.json`, **no va al informe**. Puedes
apuntarlo en `resumen.md` como "pendiente de verificar" para la próxima
corrida, y en ningún otro sitio.

## Estructura del informe

El formato completo, con el frontmatter y el Registro de evidencia, está en
`INFORME.md`. Las reglas de idioma y de citación, en `REDACCION.md`. Lee los
dos antes de escribir.

Sección por sección:

1. **Resumen ejecutivo** — 5-8 líneas. Incluye los vacíos declarados.
2. **Panorama por vertical** — una tabla por vertical, con las 4 columnas de
   `config/verticales.json`. Las verticales con `riesgo_espana: alto` que no
   tengan evidencia se marcan aquí, no se esconden.
3. **Benchmarks globales** — separado del regional, con su propia tabla.
4. **Tesis y tensión** — qué está pasando y qué no encaja. Marcado como
   lectura, no como hecho.
5. **Riesgos y límites** — sesgos de las verticales, fuentes de pago, huecos.
6. **Registro de evidencia** — tabla `[E01]...` con URL, medio, fecha,
   idioma y peso (A-E de `CRITERIOS.md`).

## Antes de darlo por terminado

```bash
python3 scripts/evaluar.py --informe informes/<fichero>.md --evidencia datos/<corrida>/evidencia.json
```

Si el script dice que hay citas sin respaldo o celdas sin fuente, **arregla el
informe**. No ajustes el script.

## Al final

Dime, en una línea, la métrica que salió y qué te costó más. Eso es lo que
itera el golden set: `/evaluar`.
