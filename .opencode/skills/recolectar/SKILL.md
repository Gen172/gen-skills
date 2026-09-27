---
name: recolectar
description: Fase 1 del pipeline. Busca, descarga, deduplica y verifica fuentes del sector tecnologico (España como region, resto del mundo como benchmark) y las deja como evidencia en JSON con metadatos verificados. Úsala ANTES de analizar, nunca después. NO redacta informes ni saca conclusiones: eso es la skill `analizar`.
license: MIT
metadata:
  fase: "1 de 2"
  produce: "datos/<corrida>/evidencia.json"
  prohibido: "redactar, sintetizar, recomendar, comparar verticales"
---

# recolectar — evidencia, no conclusiones

Tu salida es un fichero de evidencia. Nada más. Un lector humano (o la
skill `analizar`) tiene que poder mirar lo que produces y decir "esto está
respaldado" o "esto está inventado" sin fiarse de ti.

## Frontera dura

| Haces | NO haces |
|---|---|
| Buscar y descargar | Redactar informes |
| Extraer metadatos | Sintetizar tendencias |
| Deduplicar | Comparar verticales entre sí |
| Marcar calidad y región | Recomendar nada |
| Declarar vacíos | Rellenar vacíos |

Si notas que estás pensando "por tanto, esto significa que...", párate. Esa
frase es territorio de `analizar`. Tu trabajo termina en la frontera.

## Entrada

Necesitas tres cosas. Si falta alguna, **pregunta**; no las inventes:

- `--region`: `es` (España) o `global`. Por defecto `es`.
- `--vertical`: un id de `config/verticales.json` (ia-aplicada, saas-b2b,
  fintech, semiconductores, ciberseguridad, green-deeptech), o `todas`.
- `--modo`: `quick` o `full`.

Lee `config/verticales.json` para las consultas de búsqueda y los sesgos
conocidos de cada vertical. No adivines las consultas.

## Procedimiento

### 0. Antes de salir a la red: mira la caché

```bash
python3 scripts/fetch.py --dump-cache
```

Si la URL que necesitas ya está cacheada, no la vuelvas a pedir. La caché se
indexa por hash de URL canónica, así que el mismo artículo con distinto
parámetro de tracking cae en el mismo sitio.

### 1. Carga la semilla y verifícala

Lee `config/semilla-espana.json`. **Todos los nodos vienen con
`verificado: false`.** Eso no es una advertencia: es un veto. Un nodo sin
verificar no puede usarse como evidencia ni citarse. Sirve para generar
consultas.

Para usar un nodo como evidencia tienes que verificarlo: abrir su URL,
comprobar que el actor existe y opera en la fecha de corte, y poner
`verificado: true` con la fecha en `verificado_el`. **Modifica el fichero, no
tu memoria.** Si verificas nodos, dilo en el resumen de la corrida.

Ver `REGIONAL.md` para las reglas de clasificación regional/global y para el
snowballing.

### 2. Descarga

Dos rutas, con reglas distintas:

```bash
# Recurrente (reguladores, medios sectoriales) — el feed trae la fecha resuelta
python3 scripts/fetch.py --feed "URL" --salida datos/<corrida>/evidencia.json

# Puntual (una empresa, un evento concreto) — llegas aquí con websearch
python3 scripts/fetch.py --url "URL" --salida datos/<corrida>/evidencia.json
```

Reglas de la ruta:

- **Feed primero** para lo recurrente. La fecha que da el feed es más fiable
  que la que se puede extraer del HTML, y no hay coste de razonamiento.
- **`websearch` para descubrir, `fetch.py` para traer.** No pegues el texto
  crudo en tu contexto si lo puede normalizar el script: así las fechas y las
  URLs salen correctas por construcción, no por tu buen hacer.
- **No uses `webfetch` como atajo** para saltarte los metadatos. Si traes una
  página con `webfetch`, pásala después por `metadatos.py`:
  `echo '{"url":"...","html":"..."}' | python3 scripts/metadatos.py`
- Una fuente caída se registra con su `error` y se sigue. Una fuente caída
  **nunca** se sustituye por tu recuerdo de qué decía.

### 3. Filtra con criterio, no con Models de sensibilidad

`config/verticales.json` tiene un campo `riesgo_espana` por vertical. Léelo.

- `bajo` / `medio`: cobertura normal.
- `alto`: exige dos fuentes independientes para dar por firme un dato. En
  `semiconductores` ese listón está puesto a propósito, porque la cobertura
  global de chips es enorme y se cuela como regional si no se filtra.

### 4. Marca lo dudoso, no lo tires

Cada registro puede llevar un `notas` con estas etiquetas:

- `no_verificado` — la fuente existe pero no la he leído entera
- `autodeclarado` — la cifra viene de la propia empresa sin auditar
- `metodologia_desconocida` — hay cifra pero no se explica cómo se calculó
- `sin_fecha` — no se ha podido determinar la fecha
- `fuera_de_ventana` — publicada antes de la fecha de corte pedida
- `no_español` — el contenido relevante no está en español (relevante para
  el informe, no para la evidencia)

`flag_fecha` lo pone el script (`fecha_futura`, `antigua`, `sin_fecha`). Un
`fecha_futura` es prácticamente siempre un dato inventado o una página de
borrador: **no lo uses, y anótalo en el resumen.**

## Criterio de parada

No decidas por sensación. Para en cuanto se cumpla una de estas dos:

- **Modo `full`**: hay ≥10 fuentes utilizables para la vertical pedida, con
  fecha, medio y texto; **o** llevas 3 rondas de búsqueda completas sin
  encontrar nada nuevo que no esté ya en la caché.
- **Modo `quick`**: ≥4 fuentes utilizables para **una** vertical; **o** 2
  rondas sin novedad.

Cuenta "fuente utilizable" = tiene fecha, medio, texto no vacío y no es
duplicado por hash. Si no llegas al mínimo, **no tires más fuentes: dilo**.
Un vacío declarado es información. Un vacío rellenado es una mentira.

## Salida

1. `datos/<corrida>/evidencia.json` — lo produce `fetch.py`. No lo reescribas
   a mano: si corriges algo, se pierde en la siguiente corrida.
2. `datos/<corrida>/resumen.md` — un párrafo, en este formato exacto:

```
Corrida: <region> / <vertical(es)> / <modo>
Fuentes unicas: N (con fecha: N, con error: N, desde cache: N)
Nodos de semilla verificados en esta corrida: <nombres> | ninguno
Verticales sin evidencia regional: <ids> | ninguna
Senaladas: <etiquetas con conteo>
Limitaciones: <lo que no se pudo cubrir y por que>
```

La línea de vacíos es la más importante del archivo. Si `analizar` no la lee,
el hueco desaparece del informe sin dejar rastro.

Antes de seguir, lee `CRITERIOS.md` para los tipos de fuente y su peso.
