# Glosario

Terminos con mas de un significado en este repo. Cuando dos personas usan la
misma palabra pensando en cosas distintas, el fallo aparece tres semanas
despues y en otra tabla.

## Cobrable, comparable, benchmark

**Benchmark** es el dato de referencia de otro mercado (UE, media global, otro
pais). **Comparable** es un benchmark con la misma definicion y la misma
periodicidad. **Cobrable** es comparable mas la fuente accesible.

| Si solo hay... | Se puede escribir... | Porque... |
|---|---|---|
| dato de otro pais | benchmark | No es comparable: la definicion puede ser otra |
| benchmark + nota metodologica | comparable, con la nota al lado | El lector puede entender la diferencia |
| benchmark + fuente abierta | cobrable | Se puede auditar el numero |

Un informe que pone "benchmark" en la columna "comparacion" esta mintiendo por
omision. G11 existe por esto.

## Regional

Se refiere a **Espana como ambito**, no al idioma ni al dominio. Una nota de
Reuters en ingles sobre una startup espanola es regional; una nota de El Pais
sobre una empresa Damien con datos que no aparecen en Espana es global.

El caso limite que se repite: programas de la UE, CERN, organismos
iberoamericanos. Si el dato no es atribuible a una empresa o institucion
espanola concreta, es benchmark, y se marca como tal.

## Vacio, cero y ausente

Tres cosas distintas que en una tabla se ven igual:

- **Cero**: se busco, se encontro cero. Afirmacion fuerte. Requiere busqueda
  exhaustiva.
- **Ausente**: no se ha buscado todavia. No dice nada.
- **Vacio declarado**: se ha buscado y no hay evidencia publica. Es
  informacion: se escribe como tal.

Escribir 0 cuando es "ausente" es el fallo mas caro del informe, porque es el
unico que no se puede detectar leyendo la tabla: parece un dato.

## Peso de fuente

De A (dato oficial) a E (mencion en prensa general). La escala esta en
`config/verticales.json` y en `.opencode/skills/recolectar/CRITERIOS.md`.

Regla que no se negocia: **una cifra autodeclarada no es un hecho**. Va
marcada como tal aunque el dato sea exacto, porque lo que se esta midiendo no es
la cifra sino quien la publico.

## Cita resoluble

Una cita `[E01]` que resuelve a una URL que existe en `evidencia.json`. No
comprueba que la URL siga viva ni que la cifra este en la pagina: comprueba que
la cadena se cierra. Es una metrica de integridad del informe, no de verdad.

## Correccion temporal

Todo informe tiene `fecha_corte`. Un dato anterior a la fecha de corte es
valido; un dato posterior, no. La fecha de corte es lo que hace comparables dos
corridas, y por eso el golden set la exige: sin ella, comparar metricas de
enero con las de junio no significa nada.

## Tesis

Una lectura que va mas alla de lo que dicen los datos. Lleva marcador propio
(**Tesis n.**) y va en su seccion, no mezclada con los hechos.

Regla: una tesis sostenida por una sola fuente tipo D es admisible como
*hipotesis*, nunca como conclusion (G09).
