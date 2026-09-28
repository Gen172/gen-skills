# El ciclo completo

Mapa de una linea. Detalle por debajo. Términos según `GLOSSARY.md`.

```
config/ ----.
             \
red ----------+--> /recolectar --> datos/<corrida>/{evidencia.json,resumen.md}
                                     |
                                     |  frontera dura: analizar NO busca
                                     v
                                  /analizar --> informes/<...>.md
                                     |
                                     v
                           scripts/evaluar.py --> metricas.json
                                     |
                        +------------+------------+
                     falla                      pasa
                        |                         |
             corrige el INFORME          golden/rubrica.md
             (nunca el script)           (parte 1 + parte 2)
                        |                         |
                        +------------+------------+
                                     |
                          fallo humano --> caso nuevo en
                          golden/casos.json --> ajusta prompt
                                     |
                                     '--> otra vez /analizar
```

---

## 1. Qué es una skill (mecánica)

Skill = carpeta con `SKILL.md`. Nada más. Sin codigo, sin runtime.

```
.opencode/
  skills/recolectar/   SKILL.md + CRITERIOS.md + REGIONAL.md
  skills/analizar/     SKILL.md + INFORME.md  + REDACCION.md
  commands/            recolectar.md, analizar.md  →  /recolectar  /analizar
```

**Carga progresiva.** El agente lee solo el frontmatter de las N skills
disponibles (~50 tokens cada una). Solo abre el cuerpo de la que su
`description` dice que aplica. Por eso:

- `description` = cuando usarla. Es lo mas importante del fichero. Va primero,
  en tercera persona, con la condicion de NO usarla.
- cuerpo = como. Se lee solo si aplica.
- ficheros hermanos = detalle. Se leen cuando el cuerpo lo dice ("lee
  `CRITERIOS.md` antes de seguir"). Nadie los carga por accidente.

**Skill vs comando.** Mismo `.md`, distinto disparo:

| | Command | Skill |
|---|---|---|
| disparo | tú: `/recolectar es fintech full` | agente, por `description` |
| quien decide argumentos | usuario | el agente |
| para que | atajo reproducible, args explícitos | descubrir capacidad sin conocerla |

Comandos = alias de skills. La skill es la fuente; el comando solo empaqueta
argumentos. Si divergen, gana la skill.

**Por que 2 skills y no 1 agente (ADR-001).** Frontera dura = permiso, no
consejo. El contexto que permite a un modelo "recordar" un dato de una fase
anterior es justo el que lo hace rellenar huecos de memoria. Separan el
proceso en dos rails: recolectar no tiene contexto del informe, analizar no
tiene red. Sin esa amnesia, `citas_resolubles` no significa nada.

**Frontera, en tabla:**

| recolectar | | analizar | |
|---|---|---|---|
| buscar | si | buscar | NO |
| descargar | si | descargar | NO |
| extraer metadatos | si | comparar/redactar | si |
| deduplicar | si | completar hueco de memoria | NO |
| marcar calidad/region | si | citar URL fuera de evidencia | NO |
| declarar vacios | si | rellenar vacios | NO |

Frase que marca el limite en fase 1: *"por tanto, esto significa que…"* →
territorio de `analizar`. Se para ahi.

---

## 2. Fase 1 — `/recolectar`

```
/recolectar <region: es|global> <vertical: id|todas> <modo: quick|full>
```

Ficheros de apoyo: `config/verticales.json` (6 verticales × 4 campos), `config/semilla-espana.json` (47 verificados + 8 no encontrados + 2 candidatos).

| # | Paso | Comando / regla |
|---|---|---|
| 0 | mirar cache | `fetch.py --dump-cache` — no repedir lo cacheado |
| 1 | cargar y verificar semilla | `verificado: false` es **veto**, no aviso. Verificar = abrir URL + actor existe y opera + poner `verificado: true` + `verificado_el`. **Se modifica el fichero, no la memoria** |
| 2 | descargar | recurrente → `--feed`; puntual → `--url` (tras `websearch`) |
| 3 | filtrar | `riesgo_espana: alto` → 2 fuentes independientes. Hoy solo `semiconductores` |
| 4 | marcar dudoso | `notas`: `no_verificado`, `autodeclarado`, `metodologia_desconocida`, `sin_fecha`, `fuera_de_ventana`, `no_español`. `flag_fecha` lo pone el script |
| 5 | parar | ver tabla |

**Rutas de descarga:**

| Tipo | Comando | Por que ese |
|---|---|---|
| feed / recurrente | `fetch.py --feed "<RSS>"` | la fecha del feed es mas fiable que la extraida del HTML; coste de razonamiento ~0 |
| puntual | `fetch.py --url "<URL>"` | llegas desde `websearch`, no desde RSS |
| atajo (prohibido como fin) | `webfetch`, luego `metadatos.py` por stdin | `webfetch` salta metadatos; nunca pegues texto crudo en contexto |

Regla: `websearch` descubre, `fetch.py` trae. Fuente caida → se registra su
`error` y se sigue. Nunca se sustituye por recuerdo.

**Criterio de parada** (no por sensacion):

| Modo | Para cuando |
|---|---|
| `full` | ≥10 fuentes utilizables para la vertical pedida **o** 3 rondas completas sin novedad |
| `quick` | ≥4 fuentes utilizables para **una** vertical **o** 2 rondas sin novedad |

"Utilizable" = fecha + medio + texto no vacio + no duplicado por hash. Si no
llegas al minimo: **no tires mas fuentes, dilo**. Vacio declarado = informacion.
Vacio rellenado = mentira.

**Salida:**

| Fichero | Quien lo escribe | Nota |
|---|---|---|
| `datos/<corrida>/evidencia.json` | `fetch.py` | nunca reescribir a mano |
| `datos/<corrida>/resumen.md` | agente | 1 parrafo, formato exacto |

Formato exacto de `resumen.md` (la linea 3 es la que gobierna la fase 2):

```
Corrida: <region> / <vertical(es)> / <modo>
Fuentes unicas: N (con fecha: N, con error: N, desde cache: N)
Nodos de semilla verificados en esta corrida: <nombres> | ninguno
Verticales sin evidencia regional: <ids> | ninguna
Senaladas: <etiquetas con conteo>
Limitaciones: <lo que no se pudo cubrir y por que>
```

En el dominio `laboral` el resumen usa otro formato, porque los huecos no son
por vertical sino por familia, y el umbral de utilidad es por oferta:

```
Corrida: <region> / <familia(s)> / <modo>
Ofertas unicas: N (con fecha: N, con error: N, desde cache: N)
Ofertas con salario publicado: N (suficientes para media: si/no)
Fuentes locales: <archivo:nombre (#filas)> | ninguna
Familias sin oferta verificable: <ids> | ninguna
Senaladas: <etiquetas con conteo>
Limitaciones: <lo que no se pudo cubrir y por que>
```

---

## 3. Frontera: el contrato

`datos/<corrida>/evidencia.json` = unico contrato entre fases. Formato por
registro:

| Campo | Para que |
|---|---|
| `url`, `hash`, `dominio` | identidad + dedupe (hash de URL canonica: mismo articulo con distinto tracking = mismo hash) |
| `titulo`, `medio`, `fecha`, `autor` | citabilidad |
| `texto`, `descripcion` | contenido |
| `flag_fecha` | `fecha_futura` / `antigua` / `sin_fecha` — lo pone el script |
| `notas` | el porque de dudoso, por registro |

Frontera dura: `analizar` no tiene permiso de buscar. Si necesita un dato que
no esta en `evidencia.json`, para y lo pide. Es la unica forma de que
`citas_resolubles` signifique algo.

---

## 4. Fase 2 — `/analizar`

```
/analizar datos/<corrida>
```

Si `$ARGUMENTS` vacio → `resumen.md` mas reciente. Si hay dos con la misma
fecha → preguntar, no elegir.

**Antes de redactar** (los 3 comandos van literalmente en la skill):

| # | Qué comprueba | Si falla |
|---|---|---|
| 1 | numero de registros, fechas, medios | — |
| 2 | existe `resumen.md` | **para**. Sin el no sabes qué parte se calla a proposito y que parte se te olvido. No se arregla despues |
| 3 | registros con `flag_fecha` | `fecha_futura` = el registro no existe. Se descarta y se anota en el informe |

**6 reglas de construccion:**

| # | Regla | Mal → Bien |
|---|---|---|
| 1 | toda celda con dato lleva `[E07]` | sin clave, celda sin respaldo. Lo cuenta `evaluar.py` |
| 2 | toda cifra lleva unidad + periodicidad + fecha | "ha crecido mucho" → `3.200 empresas en España en 2024 (INE, publ. 2026-03)` |
| 3 | la celda dice **de donde** viene, no solo cuanto | `autodeclarado`, `metodologia desconocida`, `(fuente de prensa)`, `sin evidencia regional`. En la celda, no en nota al pie |
| 4 | vacios declarados en 2 sitios | en la tabla (`sin evidencia regional`) + en el resumen ejecutivo (con el motivo) |
| 5 | no compares sin citar los 2 lados | solo global = benchmark, marcado como tal |
| 6 | no uses lo que sabes | si sabes algo que no esta en evidencia → `resumen.md` como "pendiente de verificar". En ningun otro sitio |

**Estructura** (plantilla literal en `INFORME.md`; frontmatter con `region`,
`verticales`, `modo`, `fecha_corte`, `fecha_elaboracion`, `fuentes_totales`,
`fuentes_citadas`, `fuentes_descartadas`, `motivo_descartes`):

1. Resumen ejecutivo — 5-8 lineas, incluye vacios
2. Panorama por vertical — 1 tabla/vertical × 4 campos (Empresas, Financiacion, Talento, Regulacion)
3. Benchmarks globales — tabla separada, nunca mezclada
4. Tesis y tension — marcador **Tesis n.**, seccion propia, separada del hecho
5. Riesgos y limites — sesgos, fuentes de pago, huecos
6. Registro de evidencia — `[E01]...` con URL, medio, fecha, idioma, peso A-E

---

## 5. Evaluar

```bash
python3 scripts/evaluar.py --informe informes/<f>.md --evidencia datos/<corrida>/evidencia.json \
                           --json datos/<corrida>/metricas.json --golden golden/casos.json
```

Salida 1 si alguna metrica no llega al umbral.

| Metrica | Mide | Umbral |
|---|---|---|
| `citas_resolubles` | % claves citadas cuya URL existe en evidencia | **1.00** |
| `fechas_correctas` | % entradas del registro cuya fecha cuadra con la evidencia | **1.00** |
| `celdas_sin_fuente` | celdas con dato y sin `[Enn]` | **0** |
| `estructura_completa` | secciones + campos de frontmatter | **1.00** |
| `registro_sin_citar` | entradas del registro nunca citadas | **0** |
| `vacios_declarados` | el informe declara sus huecos | **1.00** |

Binarias a proposito. `citas_resolubles: 0.95` no es "casi bueno": hay una cita
inventada, y eso invalida el resto porque demuestra que el modelo rellena
cuando no sabe.

**Leer el fallo:** `--json` → `detalle` (linea + clave) antes que el
porcentaje. El porcentaje dice que algo va mal; el detalle dice que.
`urls_muertas` necesita `--red`.

**Regla:** si falla, se corrige el INFORME. Nunca se ajusta el script ni el
umbral.

**Lo que las metricas NO miden:** si la tesis es correcta. Un informe puede
tener las 6 a 1.0 y su tesis ser falsa. Eso lo juzga quien lee → parte 2.

---

## 6. Rúbrica y golden set — el bucle que lo justifica

`rubrica.md` parte 1 = lo que calcula el script. Parte 2 = 7 criterios, 0-3,
valoran humana, pesa mas:

| # | Criterio |
|---|---|
| 1 | Frontera regional/global (incl. casos limite: CERN, programas UE) |
| 2 | Declaracion de vacios: los explica y justifica por que son estructurales |
| 3 | Calidad de las cifras: completas + metodologia al lado |
| 4 | Uso de lo que sabe: ni completa ni especula |
| 5 | Utilidad: dice que se puede y que no se puede hacer con estos datos |
| 6 | Estructura: plantilla + registro completo |
| 7 | Tesis: dice tambien lo que la evidencia NO permite afirmar |

Si un informe "no cuadra" pero las metricas pasan → la parte 2 esta mal, no el
informe.

**Los 12 casos** (`golden/casos.json`): G01 ciudadanía de region en fuente
internacional · G02 semiconductores sin evidencia · G03 cifra autodeclarada ·
G04 cifra oficial antigua como actual · G05 nodo sin verificar · G06 cifra sin
unidad/periodicidad · G07 fuente duplicada · G08 fecha en el futuro · G09
tesis con una sola fuente D · G10 idioma de la cita global · G11 comparacion
sin los dos lados · G12 informe sin seccion de limites.

Cada caso lleva fecha de corte: sin ella, comparar metricas de enero con las
de junio no significa nada.

**Bucle de iteracion:**

```
escribir caso → correr → medir → ajustar prompt → repetir
```

Tres reglas para que el historico signifique algo:

1. **Un cambio de prompt, una entrada en golden.** Cambias dos cosas, no sabes cual arreglo el fallo.
2. **Anadir casos, nunca editarlos.** Obsoleto → `obsoleto: true` + caso nuevo. Editar invalida todas las metricas anteriores sin dejar rastro.
3. **Guardar informe + metricas de cada iteracion** en `informes/<caso>-iter<N>/`. El "¿que mejoro?" se responde con `git log`, no de memoria.

Prioridad de caso nuevo: cuando `evaluar.py` marca un fallo que **no sabemos
detectar**. El linter es solo la parte que sabemos automatizar.

---

## 7. Las tres gorras (mantenimiento, no pipeline)

Una persona, tres trabajos por turnos. Cada uno con una regla para no
contaminar a los otros.

| Gorra | Mantiene | Regla |
|---|---|---|
| 1 recolector | `config/semilla-espana.json`, fuentes de `verticales.json` | no ampliar la semilla con lo que "sabes". Con lo que se ha **encontrado y verificado**. Si falta una empresa y no la has buscado → `verificada: false` |
| 2 golden | `golden/casos.json` | escribir primero el fallo, despues el prompt. Al reves, el caso se ajusta a lo que el prompt ya hace y no prueba nada |
| 3 auditor | rubricas, `docs/ADR` | ADR cuando cambia una decision, no cuando se ejecuta. Experimento fallido que exige un parrafo explicando por que se descarta → no era decision |

Revisar semilla cada 4 semanas: que los verificados sigan existiendo, añadir
nuevos.

---

## 8. Reglas que no se negocian

1. Ninguna cifra sin fuente `[E07]`.
2. Ninguna cifra sin unidad, periodicidad y fecha. "Ha crecido" no es un dato.
3. Los vacios se declaran. Esconderlo en la tabla es mentir por omision.
4. Un informe sin seccion de limites no esta terminado (G12).
5. El golden set se escribe **antes** de arreglar el prompt. Sin caso, un cambio de prompt es una opinion.
6. `datos/` no se versiona. Es reproducible; versionarlo mete ruido generado en el historico (ADR-005).

Cero vs ausente vs vacio declarado (GLOSSARY): escribir `0` cuando es
"ausente" es el fallo mas caro del informe, porque es el unico que no se
detecta leyendo la tabla — parece un dato.

---

## 9. Cuando falla

| Sintoma | Causa mas frecuente | Mira |
|---|---|---|
| "el agente va raro" | caracteres corruptos / JSON invalido | `revisar_docs.py` **primero**, siempre |
| metricas fallan | detalle antes que porcentaje | `--json` → `detalle` (linea + clave) |
| cita sin respaldo | cita de memoria, no de evidencia | ¿la URL esta en `evidencia.json`? |
| fuente sin fecha util | RSS primero, no scrape de HTML | `fetch.py --feed` |
| PDF ilegible | `fetch.py` guarda binario como texto | atajo: `boe.es/diario_boe/txt.php?id=...` → HTML limpio |
| fecha extractada mal | script vs pagina | corregir a mano **en la corrida**, conservar `fecha_extraida_por_fetch_py`. Se pierde si no |

---

## 10. Cheat-sheet

```bash
# FASE 1
/recolectar es fintech full
python3 scripts/fetch.py --dump-cache
python3 scripts/fetch.py --feed "<RSS>" --salida datos/c1/evidencia.json
python3 scripts/fetch.py --url  "<URL>"  --salida datos/c1/evidencia.json
echo '{"url":"...","html":"..."}' | python3 scripts/metadatos.py

# FASE 2  (no busca)
/analizar datos/c1-2026-09-28

# EVALUAR  (exit 1 si no llega al umbral)
python3 scripts/evaluar.py --informe informes/f.md --evidencia datos/c1/evidencia.json \
                           --json datos/c1/metricas.json --golden golden/casos.json
python3 scripts/evaluar.py ... --caso G08      # caso suelto
python3 scripts/evaluar.py ... --red            # comprueba URLs muertas

# SIEMPRE antes de commitear
python3 scripts/revisar_docs.py     # caracteres, JSON, frontmatter
python3 scripts/test_pipeline.py    # 31 pruebas offline
python3 scripts/test_evaluar.py     # 15 pruebas, con fallos plantados
```

Ficheros que no se tocan sin motivo: `.gitignore` · `config/verticales.json`
(cambia la rubrica → ADR) · `golden/casos.json` (editar invalida metricas).

---

## 11. Estado real (2026-09-28)

| | |
|---|---|
| skills, scripts, golden, semilla | listos |
| semilla | 47 verificados · 8 no encontrados (con motivo) · 2 candidatos sin URL. `verificado_el` + `metodo_verificacion` en cada nodo |
| fase 1 | ejecutada 1 vez end-to-end con red → `datos/c1-2026-09-28/`, 44 fuentes unicas |
| fase 2 | **sin ejecutar**. No existe `informes/` |
| falta | primera corrida completa de extremo a extremo |

Veto vigente: un nodo solo sirve como evidencia si consta su URL, su fecha y
que sigue existiendo.

### Dominio laboral (2026-09-28, ADR-006 y ADR-007)

| | |
|---|---|
| config | `config/mercado-laboral.json`: 2 familias, 6 campos, 3 regiones, mapa de CSV, 4 tipos de fuente |
| ingesta local | `--csv`, `--pdf`, `--transcript`, `--youtube`. Probadas offline las tres primeras |
| plantilla | `.opencode/skills/analizar/INFORME-LABORAL.md`, con tabla de brecha por familia |
| metricas | `salarios_verificables` y `brecha_declarada`, con umbral 1.00 y codigo de salida 1 |
| golden | G13-G18 anadidos. Los G01-G12 intactos |
| pruebas | `scripts/test_laboral.py`, 35 offline |
| sin probar | `--youtube` con red, y una corrida laboral completa con fuentes reales |
| entrega | `scripts/empaquetar.py` genera `kb-*.zip`, `agente-*.zip`, `docs-*.zip` con indice sha256 |

Fuentes verificadas el 2026-09-28 con peticion HTTP real y validacion de
certificado activa: **12 de 16**. Las 4 que quedan sin verificar son Gartner y World
Economic Forum (403 a robots), OSIMGA (cadena TLS que no valida desde este entorno)
y "charlas de expertos en canales oficiales", que no es una fuente sino una categoria
y por eso no tiene URL que verificar. Ninguna se marco como verificada saltandose
la comprobacion. Se corrigieron
tres nombres que no eran los oficiales, cada uno con su correccion anotada en el
propio fichero, y se anadio el IGE (verificado) al detectar que era el origen de
los datos de empleo de Galicia.

Lo que **no** hay todavia: ninguna corrida laboral con ofertas reales. Los CSV de
ofertas con fecha y salario son el trabajo del recolector el primer dia, y no se
pueden hacer de memoria.

---

## Trampa conocida

Ruta de salida de fase 2 esta escrita de dos formas y **no coinciden**:

| Fuente | Ruta |
|---|---|
| `README.md`, `AGENTS.md` | `informes/<vertical>/<fecha>.md` |
| `.opencode/skills/analizar/SKILL.md` (frontmatter `produce`) | `informes/<fecha>-<region>-<vertical>.md` |

Fijar una y corregir las otras tres, o el `evaluar.py` acaba apuntando a
ficheros que no existen. Requiere ADR si cambia la plantilla (`INFORME.md`).

Segunda trampa, ya abierta: el dominio laboral **no tiene la trampa de la
region**, pero si la del **umbral**. El evaluador mide `celdas_sin_fuente` por
fila de tabla, no por celda, asi que una columna de veredicto o de recomendacion
en la tabla de brecha no hace bajar la metrica mientras la fila tenga una
`[Enn]`. Es intencionado (el veredicto es juicio, no dato), y por eso la rubrica
pide puntuarlo a mano en el criterio 8.
