# Criterios de evidencia

Qué clase de fuente es cada una y cuánto se le puede pedir. El objetivo es que
el informe se pueda auditar sin recalcular nada.

## Tipos, de más a menos fiable

### A · Dato primario (el mejor)

Lo emite quien tiene el dato: un regulador, un organismo oficial o la
empresa cuando la cifra va con responsabilidad legal: nota de prensa
oficial, presentación a inversores o información regulatoria.

- Ejemplos: series del INE, notas de prensa de CNMC o Banco de España,
  informes anuales de INCIBE o ENISA, y fichas del registro mercantil.

- Uso: **cifras de contexto**. Poblaciones, número de empresas por sector,
  volumen de pagos, número de incidentes.
- Límite: casi nunca habla del sector tech por sí solo, y sus taxonomías no
  suelen encajar con las 6 verticales. Requiere traducción cuidadosa.

### B · Medio especializado

Prensa que cubre tecnología de forma regular y con continuidad editorial.

- Ejemplos: Expansión/Cinco Días (mercados y financiación), Reuters
  Technology, TechCrunch, Genbeta, Xataka.
- Uso: **noticias de empresa, rondas, nombramientos e incidencias**.
- Límite: hay que distinguir la pieza original de la nota de agencia
  republicada. Citar a Reuters es mejor que citar a un medio que copió a
  Reuters.

### C · medio generalista

Prensa general con alguna sección económica.

- Uso: solo para contexto y para confirmar.
- Límite: **nunca como única fuente de una cifra.**

### D · comunicación de la empresa

Web de la propia empresa, nota de prensa, perfil en red social o
ponencia en un congreso.

- Uso: **hechos sobre la empresa**: qué hace, dónde, cuándo, con quién.
- Límite: `autodeclarado` por definición. No sirve para "el mercado ha
  crecido un 200%". Si la cifra sale de aquí, el informe lo dice.

### E · Segunda mano (no es fuente)

Portal de agregación, resumen sin enlace al original, artículo sin
fecha, hilo de foro, publicación sin autoría, o resumen de otro medio.

- Uso: **una sola cosa**: encontrar el original. Luego cita el original.
- Si no existe original: fuera. No lo resumas de memoria.

## Reglas de peso

1. **Una cifra sin unidad, periodicidad y fecha no entra.** "El mercado
   ha crecido" no es un dato. "El número de empresas del sector tecnológico
   en España pasó de A a B entre 2020 y 2024, según INE" sí lo es.
2. **Dos fuentes B o una A para dar algo por firme.** Con una sola fuente B,
   el informe lo dice como afirmación de esa fuente, no como hecho.
3. **Una cifra oficial antigua no es una cifra actual.** Los informes anuales
   se citan con su año: "el balance 2025 publicado en febrero de 2026", no "el
   balance de este año".
4. **La metodología es parte de la cifra.** Si no se explica cómo se ha
   calculado, se marca `metodologia_desconocida` y el informe lo dice en la
   propia celda, no en una nota al pie.
5. **Un `fecha_futura` no es un dato raro: es un dato falso.** Casi siempre es
   una página de borrador o un número inventado. Se descarta.
6. **Preferir el dato oficial a la cifra de prensa**, incluso si la cifra de
   prensa es más reciente y mejor explicada. Si usas la de prensa, dilo.
7. **Un número sin nombre de la fuente detrás es relleno.** No lo pongas.

## Qué hacer cuando no hay nada

Es la parte que más se olvida y la que más penaliza un informe:

- No hay dato → celda vacía + `sin evidencia regional` en la nota.
- No hay dato y la vertical es estructuralmente delgada (`riesgo_espana:
  alto`) → se dice **en el resumen ejecutivo**, no escondido en una tabla.
- Hay dato global pero no español → la tabla regional queda vacía. El dato
  global va en su propia sección, marcado como benchmark.
- El hueco es el hallazgo, no el fallo. Un informe con tres verticales bien
  documentadas y tres declaradas vacías es **mejor** que uno con seis
  verticales a medio rellenar de prensa global.
