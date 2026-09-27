# Frontera regional/global: como se decide que es Espana

El fallo mas caro de este pipeline no es inventar una empresa. Es Colocar una
noticia de Reuters sobre el mundo en la tabla regional, porque esta escrita en
castellano o menciona un actor espanol de pasada. Al principio parece un
detalle; al final significa que el informe de Espana no dice nada de Espana.

## La regla

Una fuente es **regional** si su **sujeto** esta en Espana. No si su idioma,
ni su medio, ni su URL.

| Fuente | Regional | Global | Por que |
|---|---|---|---|
| Reuters: "la startup espanola T levanta 100 M$" | **si** | no | El sujeto es T, en Espana. Procedencia extranjera. |
| Genbeta: "OpenAI abre oficina en Madrid" | **si** | no | El sujeto es la llegada, que ocurre en Espana. |
| Expansion: "la bolsa europea sube" | no | **si** | El sujeto es el mercado europeo. |
| El Pais: "Trump anuncia tariffs sobre la UE" | no | **si** | La mencion de Espana, si la hay, es de contexto. |
| Informe del INE sobre empresas tecnologicas | **si** | no | Dato oficial de Espana. |
| Informe de ENISA (sede Alicante) | **si** | no | Dato de Espana, aunque sea de una agencia de la UE. |
| Comunicado de una empresa que cierra una Serie A en Berlin | no | **si** | El sujeto es la ronda, que no ocurre en Espana. |

El caso que mas se da: **una startup espanola finanziada por un inversor
estadounidense sigue siendo regional.** El dinero es global; la empresa es
espanola. Y al reves: una empresa estadounidense abriendo una filial en
Madrid es regional, porque el hecho ocurre en Espana.

Los dos casos limites, resueltos por criterio explicito:

- **CERN**: Espana es miembro, pero el sujeto (el laboratorio) no es espanol.
  Se trata como global. Es deeptech de benchmark, no regional.
- **Programas europeos con sede en Espana** (EIT Digital, Red.es, ENISA): la
  sede es espana pero la decisión se toma en Bruselas. Para una vertical se
  cuenta como regional solo si hay un dato especifico de Espana, no el agregado
  europeo.

## Metodo: tres capas

De barato a caro. Se aplican en orden y cada una puede parar la busqueda.

### Capa 1 — Prefiltro por procedencia (barato, poco fiable)

Sospecha de regional si: el dominio es `.es` o termina en `.es`, el medio
tiene sede en Espana (esta en la semilla), el titulo contiene una entidad
espanola conocida. Sirve para reducir candidatos, **no para clasificar**.

### Capa 2 — Semilla y snowballing (el nucleo)

La semilla esta en `config/semilla-espana.json`. Se recorre en dos tiempos:

**Tiempo 1, verificar.** Abrir cada nodo, confirmar que existe y opera, poner
`verificado: true` y `verificado_el` con la fecha. Mientras un nodo siga en
`verificado: false` no puede usarse como evidencia: solo genera consultas.

**Tiempo 2, expandirse.** Desde cada nodo verificado se sale por su
`vecindad`. De una empresa: sus proveedores, sus clientes, sus inversores, el
inversor que la respaldó. De un inversor: su portfolio. De un centro: sus
grupos de investigacion. De un regulador: sus expedientes y sanciones. De un
medio: a quien ha entrevistado.

El snowballing es lo que convierte "articulos en espanol" en "el ecosistema
tecnologico espanol". Sin el, la capa 1 se queda en clasificacion por
procedencia, que es exactamente el fallo que estamos intentando evitar.

Cada salto se anota como `origen: <nombre del nodo del que salio>`, para que
el informe pueda decir de donde sale cada actor y no solo citar una pagina.

### Capa 3 — Datos oficiales (para cifras, no para noticias)

Cuando lo que se busca es un numero, se va a la tabla, no a la prensa:

- Poblacion de empresas por sector: INE
- Pagos e inclusion financiera: Banco de Espana
- Regulacion y sanciones: CNMC, CNMV, AEPD
- Incidentes y alertas: INCIBE, CCN-CERT
- Despliegue y digitalizacion: Red.es
- Investigación: CSIC y los centros de la semilla.

La cifra sale de la tabla con su ano de referencia. Si unicamente hay una
cifra de prensa para ese dato, se marca `metodologia_desconocida` y se dice de
que medio es.

## Huecos estructurales

Hay verticales donde la respuesta correcta es "no hay". Escribirlo en
`config/semilla-espana.json` bajo `huecos_conocidos` (hoy: semiconductores y
talento) tiene una consecuencia concreta en el prompt:

> Si la vertical tiene `riesgo_espana: alto` y la busqueda no encuentra
> evidencia regional, **la tabla queda vacia y se declara en el resumen
> ejecutivo**. No se rellena con la version global.

Poner esta regla es lo que evita el modo de fallo mas visible de un informe de
este tipo: seis verticales "cubiertas" cuando cuatro son prensa internacional
reetiquetada.
