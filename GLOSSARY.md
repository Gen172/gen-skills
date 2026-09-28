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

---

# Glosario del dominio laboral

Estas palabras solo aparecen en el dominio `laboral` (`config/mercado-laboral.json`).
Varias tienen equivalente en ingles con un significado distinto, y esa confusion
es la que produce informes que parecen buenos.

## Oferta, vaga, vacante

Una **oferta** es un puesto publicado con fecha. Una **vaga** es el puesto vacante
que ofrece una empresa. Un **vacante** es una plaza mas un contrato: en un
informe de empleo, un vacante es un hecho economico y una oferta es un anuncio.

Se cuentan ofertas, no vacantes: el vacante no se publica, se infiere, y para
inferir hay que saber cuantas plazas abre cada oferta. `config/mercado-laboral.json`
no infiere nada.

## Familia: DAM y ASIR

**DAM** (Desarrollo de Aplicaciones Multiplataforma) y **ASIR** (Administracion
de Sistemas y Redes) son familias de perfiles, no de empresas ni de sectores.
Comparten casi todo el vocabulario tecnologico, y por eso el riesgo de que un
informe de dos familias sea en realidad de una: se cruzan sin que se note. El
caso G17 existe para eso.

Familia no es sinonimo de "`familia` en una tabla de contenido". Cada familia
pedida tiene su subseccion, tenga o no tenga ofertas.

## Salario publicado, rango y media

- **Salario publicado**: la cifra que la oferta escribe. Lo mas frecuente es que
  no exista, y su ausencia es informacion.
- **Rango observado**: minimo y maximo de las ofertas con salario, con `n=`. Es
  un hecho con letra pequeña.
- **Media**: solo con `salario_media_n` ofertas comparables (config: 20). Por
  debajo de ese numero, la media no se publica: se publica el rango y se dice
  que no hay media.

Un rango con `n=2` no es un dato de mercado. Es una muestra, y se escribe como
muestra (G13, G14).

`n=` no es decoracion: es lo que separa un dato de una impresion. Sin el, la
cifra es cierta y la conclusion falsa, que es peor.

## Bruto, neto y "sin especificar"

`28.000 EUR/mes` sin decir bruto ni neto son dos lecturas que se separan en
cerca de un 20%. Si la mitad de la muestra no lo dice, el dato se marca
`bruto declarado` y se explica en la celda. No se promedia mezclando unas y
otras.

## Señal de horizonte

Un dato que dice hacia donde va algo, no lo que hay hoy. Una charla que dice
"Kubernetes es lo que mas se pide" es una **senal de horizonte**, aunque venga
de una persona que sabe. En el informe va en la seccion 3, con su tipo de dato
al lado, y **nunca** sostiene una celda de salario.

La confusion entre senal y oferta es el fallo mas caro del dominio: las dos
vienen con numero, las dos se pueden citar, y solo una es un contrato (G15).

## Clave local: `archivo:<fichero>#<fila>`

Un CSV o un PDF que te han entregado no tiene URL. Se cita con
`archivo:ofertas.csv#12` y con `#` para la fila cuando hay varias. No se le
inventa una URL "de donde vino": esa URL no abre ninguna oferta concreta y no
se puede comprobar (G18). `evaluar.py` acepta estas claves con la misma
mecanica que `[E01]`.

## Mercado

En `sector`, `mercado` significa el ambito de un sector. En `laboral` significa
el ambito geografico de una familia: `galicia` es el ambito del encargo, `espana`
y `global` son benchmark. `config/mercado-laboral.json` tiene las tres regiones
con su peso, y el informe tiene que comparar con `espana` y `global` marcados
como benchmark, no como equivalente.
