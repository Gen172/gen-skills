# Formato del informe de mercado laboral

Plantilla del dominio `laboral`. Se copia tal cual, igual que `INFORME.md`: un
formato variable hace imposible automatizar la evaluacion. La unica diferencia
con el informe de sector son las secciones 3 y 4, que aqui son el objeto del
trabajo y alli eran un anexo.

```markdown
---
dominio: laboral
region: galicia
familias: [dam, asir]
modo: quick
fecha_corte: 2026-09-28
fecha_elaboracion: 2026-09-28
ofertas_totales: 12
ofertas_con_fecha: 10
ofertas_con_salario: 4
n_salario: 4
fuentes_totales: 8
fuentes_citadas: 6
fuentes_descartadas: 2
motivo_descartes: sin_fecha, pdf_texto_binario
---

# Informe: mercado laboral DAM/ASIR en Galicia — 2026-09-28

## 1. Resumen ejecutivo

<!-- 5-8 lineas. Los vacios van aqui, no en la ultima seccion. -->

- **Lectura principal.** <una frase>
- **Segunda lectura.** <una frase>
- **Vacios declarados.** <que no se ha podido cubrir y por que>
- **Riesgo del propio informe.** <que sesgo de muestra no se ha corregido>

## 2. Demanda actual por familia

<!-- Una tabla por familia. Las 6 filas salen de config/mercado-laboral.json:
     Vacantes | Perfil demandado | Stack | Salario | Experiencia | Modalidad -->

### 2.1 DAM

| Campo | Dato | Calidad |
|---|---|---|
| Vacantes | 6 ofertas con fecha entre 2026-08-20 y 2026-09-12 en el Portal Emprego, vista desde Galicia [E01] [E02] | D. Recuento de un portal, no del mercado |
| Perfil demandado | Desarrollador/a de aplicaciones multiplataforma, 4 de 6 ofertas [E01] [E02] [E03] [E04] | D |
| Stack | Flutter y Dart en 3 de 6; SQL en 2 [E01] [E02] [E03] | D |
| Salario | 30.000-45.000 EUR brutos anuales, rango observado, n=4, ofertas de 2026-09 [E01] [E02] [E05] [E06] | D. Muestra de 4: no da media. El rango es del conjunto, no del mercado |
| Experiencia | 3 anos en 2 ofertas, 0-1 en 1 [E01] [E02] | D |
| Modalidad | Hibrido en 3 de 6, presencial en 2, remoto en 1 [E01] [E02] [E03] | D |

### 2.2 ASIR

| Campo | Dato | Calidad |
|---|---|---|
| Vacantes | <sin ofertas verificables en la ventana> | — |
| Salario | <las ofertas no publican salario> | — |

## 3. Senales de horizonte 2-3 anos

<!-- Solo aqui entra lo que proyecta. Cada fila dice que proyecta y con que
     metodologia. Una senal de horizonte no rellena la seccion 2. -->

| Senal | Que proyecta y hasta donde | Fuente | Tipo de dato |
|---|---|---|---|
| Lenguajes con mayor crecimiento | Uso en repos publicos, no contratacion [E07] | Octoverse 2026 | B. Encuesta de uso |
| Brecha de ciberseguridad | Proyeccion de empleo a 3 anos, con metodologia del organismo [E08] | WEF Future of Jobs | B. Proyeccion |

## 4. Brecha de habilidades

<!-- El apartado que la practica pide. Por familia, una fila por competencia.
     Con un solo lado no hay brecha: hay benchmark, y se dice. -->

### 4.1 DAM

| Competencia | Se pide hoy | Se anuncia para 2-3 anos | Veredicto | Que haria falta en el plan |
|---|---|---|---|---|
| Contenedores | 1 de 6 ofertas [E03] | Kubernetes entre las tecnologias mas anunciadas [E07] | Senal debil: un lado es una oferta suelta | Subir contenedores de optativa a troncal |
| <competencia> | <sin evidencia> | <senal de horizonte> | No comparable | <o se declara el hueco> |

### 4.2 ASIR

| Competencia | Se pide hoy | Se anuncia para 2-3 anos | Veredicto | Que haria falta en el plan |
|---|---|---|---|---|
| <competencia> | <...> | <...> | <...> | <...> |

## 5. Riesgos y limites

- **Muestra.** <cuantas ofertas, de cuantos portales, y por que no es el mercado>
- **Salario.** <n, si es suficiente para un rango, y por que no se publica media>
- **Sesgo de fuente.** <cuantas ofertas son D, cuantas B, cuantas A>
- **Horizonte.** <que parte de la seccion 3 es proyeccion de terceros y no medida>
- **Fuentes de pago.** <cuales, o ninguna>
- **Huecos.** <que celdas quedan vacias y por que>

## 6. Registro de evidencia

| Clave | URL o clave local | Medio | Fecha | Idioma | Peso |
|---|---|---|---|---|---|
| E01 | https://empleo.galicia.es/oferta/1234 | Portal Emprego | 2026-09-12 | es | D |
| E02 | archivo:ofertas.csv#3 | Portal Emprego | 2026-09-01 | es | D |
| E07 | https://octoverse.github.blog/2026 | Octoverse | 2026-01-15 | en | B |
```

## Reglas de este formato

1. **El `dominio: laboral` del frontmatter no es opcional.** Sin el, `evaluar.py`
   busca las secciones del informe de sector y da por incompleto un informe
   laboral que este completo.
2. **La clave local `archivo:<fichero>#<n>` es una cita valida** si y solo si esa
   fila existe en el fichero de la base de conocimiento. `evaluar.py` la
   comprueba contra `evidencia.json` igual que una URL. Se usa cuando el portal
   no da URL propia para la oferta.
3. **La celda de Salario lleva siempre `n=`.** Con menos de 5 ofertas con salario
   se publica el rango observado y se dice que la muestra no da media. Con 20
   ofertas comparables se puede publicar una media, y su metodologia al lado.
   Los limites estan en `config/mercado-laboral.json` (`umbrales.salario`).
4. **La seccion 4 tiene una subseccion por familia pedida.** Sin subseccion, la
   brecha esta declarada a medias, que es como se pierde.
5. **Un recuento de ofertas lleva su ambito.** "12 ofertas" no es un dato;
   "12 ofertas en el Portal Emprego, vista desde Galicia" si.
6. **La seccion 5 no es opcional aunque no haya riesgos.** Se escribe "sin
   riesgos identificados en esta ventana" y ya. Un informe sin seccion de
   limites afirma que no tiene ninguno, y eso nunca es cierto (G12).

## Marca de peso

Hereda de `recolectar/CRITERIOS.md`, con una consequence propia del dominio
laboral: **una oferta de empleo es siempre tipo D**, porque la publica quien
quiere contratar. Que el dato sea exacto no lo convierte en un hecho de
mercado: lo que se esta midiendo es lo que una empresa decide mostrar. Un
informe con el 90% de fuentes D no es un informe preciso, es un retrato de lo
que se publica, y esa distinction va en la seccion 5.
