# Rubrica de evaluacion

Se puntua sobre un informe producido por el pipeline, no sobre el pipeline.
Dos columnas: la metrica automatica (la calcula `scripts/evaluar.py`) y la
valoracion humana (la que hace una persona del equipo leyendo el informe).

## Parte 1: metricas automaticas

Las calcula el script. No se ajustan a mano: si una metrica no representa lo
que crees, se cambia el script y se vuelve a correr todo el golden set.

| Metrica | Que mide | Umbral para aprobar |
|---|---|---|
| `citas_resolubles` | % de claves citadas cuya URL (o clave `archivo:`) existe en `evidencia.json` | **1.00** |
| `fechas_correctas` | % de entradas del registro cuya fecha coincide con la evidencia | **1.00** |
| `celdas_sin_fuente` | % de celdas con dato y sin clave `[Enn]` | **0.00** |
| `estructura_completa` | Secciones del informe y campos del frontmatter | **1.00** |
| `registro_sin_citar` | Entradas del registro nunca citadas en el cuerpo | **0** |
| `vacios_declarados` | El informe declara sus huecos | **1.00** |

Las tres primeras son binarias a proposito. Un informe con `citas_resolubles`
de 0.95 no es "casi bueno": tiene una cita inventada, y una cita inventada
invalida el resto porque demuestra que el modelo rellena cuando no sabe.

### Metricas que solo existen en el dominio `laboral`

Se calculan cuando el frontmatter del informe lleva `dominio: laboral`, con el
mismo script y los mismos umbrales. Si salen a `null` en un informe laboral, es
que el evaluador no ha detectado el dominio: eso ya es un fallo.

| Metrica | Que mide | Umbral para aprobar |
|---|---|---|
| `salarios_verificables` | % de celdas de la fila `Salario` que se pueden auditar: llevan `EUR`, un año o fecha, `n=` con la muestra, y **al menos una oferta citada que publique un salario** | **1.00** |
| `brecha_declarada` | % de familias pedidas que tienen subseccion en la tabla de brecha **y** dicen que se pide hoy (o que no hay datos) | **1.00** |

`salarios_verificables` no mide si el salario es *correcto*: mide si se puede
auditar. La comprobacion de que exista una oferta citada con salario es la que
mata el fallo de G15, donde la cita resuelve y la cifra no esta. Los motivos que
el script imprime son `sin n= (muestra)`, `sin EUR`, `sin fecha o ano`,
`ninguna de las fuentes citadas publica un salario` y `sin clave de fuente`.

`brecha_declarada` mide la simetria, no la calidad del juicio. Una familia sin
ofertas tiene su subseccion con `<sin evidencia>` y la cumple; una familia que
no aparece, no.

## Parte 2: valoracion humana

Se puntua de 0 a 3 cada punto. Esta parte no la puede hacer un script, y es la
que mas pesa.

| # | Criterio | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|
| 1 | Frontera regional/global | Todo mezclado | Mezclado con aviso al final | Bien, con casos limite dudosos | Todo bien, incluidos los casos limite (CERN, programas UE) |
| 2 | Declaracion de vacios | Huecos escondidos | Huecos en tabla, no en resumen | Resumen los menciona | Los explica y justifica por que son estructurales |
| 3 | Calidad de las cifras | Cifras sin fuente o sin unidad | Cifras con fuente pero sin periodicidad | Cifras completas | Cifras completas y con la metodologia al lado |
| 4 | Uso de lo que sabe | Completa huecos de memoria | Dice "no lo se" y sigue | No completa, pero speculate en la seccion de tesis | No completa ni speculate; separa hecho de lectura sin confundirlos |
| 5 | Utilidad para la decision | No sirve para nada | Describe | Compara | Dice que se puede y que no se puede hacer con estos datos |
| 6 | Estructura del informe | Caotico | Secciones libres | Plantilla seguida | Plantilla seguida y el registro de evidencia completo |
| 7 | Tesis | Ninguna o la tesis es una cifra repetida | Tesis sin evidencia clara | Tesis con evidencia citada | Tesis que dice tambien lo que la evidencia no permite afirmar |

## Como se usa

1. Se produce un informe con `/recolear` y `/analizar`.
2. `python3 scripts/evaluar.py --informe <f> --evidencia <e> --json <m>` y se
   anota la parte 1. Si alguna no llega al umbral, **se corrige el informe** y
   se vuelve a puntuar. No se ajusta el script para que pase.
3. Dos personas del equipo puntuan la parte 1 de forma independiente.
4. Se calcula la media de las dos. Si discrepan en mas de 1 punto en cualquier
   criterio, se discute en la revision: ahi esta casi siempre el hallazgo.
5. `python3 scripts/evaluar.py ... --caso <id>` para los casos del golden set
   aplicables a la corrida. El script marca con `*` los que encajan, y avisa si
   el caso y el informe no son del mismo ambito.

## Sobre la parte 2 en el dominio `laboral`

Los siete criterios de arriba se puntuan igual, pero dos cambian de sentido:

- **Utilidad para la decision** (5): en un informe de empleo, un 3 no es
  "dice que se puede hacer" sino "dice que se puede ajustar el plan, y con que
  margen de error". Si el plan solo puede cambiar de forma cualitativa, esa es
  la conclusion util y hay que escribirla.
- **Calidad de las cifras** (3): una cifra de salario sin `n=` puntua 1, no 2.
  Y un rango con n=2 no es un dato de mercado aunque las dos cifras sean
  ciertas: es una muestra.

Un criterio extra que solo se puntua en `laboral`, de 0 a 2:

| # | Criterio | 0 | 1 | 2 |
|---|---|---|---|---|
| 8 | Separacion oferta / senal de horizonte | Las dos se mezclan en la misma tabla | La tabla 3 existe pero alguna fila mezcla oferta con proyeccion | La tabla 3 dice de que lado sale cada fila y la tabla 4 no usa cifras de charla como si fueran salario |

## Iterar el prompt

El bucle es el del criterio agil de esta practica, y es lo unico que justifica
el golden set:

```
escribir caso  ->  correr  ->  medir  ->  ajustar prompt  ->  repetir
```

Reglas para que el historico signifique algo:

- **Un cambio de prompt, una entrada en el golden set.** Si cambias dos
  cosas, no sabes cual ha arreglado el fallo.
- **Anadir casos, nunca editarlos.** Si un caso ya no representa el
  comportamiento que quieres, se marca `obsoleto: true` y se escribe otro. Editar
  un caso invalida todas las metricas anteriores sin dejar rastro.
- **Guarda el informe y las metricas de cada iteracion** en
  `informes/<caso>-iter<N>/`. El "¿que mejoro?" se responde con git log, no de
  memoria.

## Nota sobre lo que esto no mide

Ninguna de estas metricas dice si la **tesis** es correcta. Solo dicen si está
respaldada. Un informe puede tener las seis metricas a 1.0 y su tesis ser
falsa. Esa parte la juzga quien lee, y por eso la parte 2 no se automatiza.
