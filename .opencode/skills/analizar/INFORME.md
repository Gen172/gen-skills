# Formato del informe

Plantilla. Se copia tal cual: un formato variable hace imposible automatizar la
evaluación.

```markdown
---
region: es
verticales: [ia-aplicada, ciberseguridad]
modo: full
fecha_corte: 2026-09-28
fecha_elaboracion: 2026-09-28
fuentes_totales: 20
fuentes_citadas: 14
fuentes_descartadas: 6
motivo_descartes: fecha_futura, duplicados
---

# Informe: sector tecnológico en España — fecha_corte

## 1. Resumen ejecutivo

<!-- 5-8 lineas. Va aqui, no en un ultimo apartado. -->

- **Lectura principal.** <una frase>
- **Segunda lectura.** <una frase>
- **Vacíos declarados.** <verticales sin evidencia regional y por que>
- **Riesgo del propio informe.** <que sesgo no se ha podido corregir>

## 2. Panorama por vertical

<!-- Una tabla por vertical. Las 4 columnas vienen de config/verticales.json:
     Empresas | Financiación | Talento | Regulación -->

### 2.1 IA aplicada

| Campo | Dato | Calidad |
|---|---|---|
| Empresas | Telefonica Tech (Madrid), cloud e IA corporativa [E01] | tipo A |
| Empresas | Signalyst B, IA para clinica [E04] | tipo D, autodeclarado |
| Financiación | <sin evidencia regional> | — |
| Talento | 2.400 profesionales del sector TIC en 2024 [E09] | tipo A, INE |
| Regulación | sin novedades en la ventana | sin evidencia regional |

## 3. Benchmarks globales

<!-- Separado del regional a proposito. Cada fila dice su equivalente
     espanol o dice que no lo tiene. -->

| Referencia global | Dato | Equivalente en España |
|---|---|---|
| Ronda media Serie A, UE [E12] | 6,2 M€ | <sin equivalente publico> |
| <algo> [E15] | <dato> | Telefonica Tech [E01] |

## 4. Tesis y tension

<!-- Aqui si se interpreta. Marcado como lectura, nunca como hecho. -->

**Tesis 1.** <...> — lectura, no hecho. Apoyada en [E01], [E07].

**Tension 1.** <lo que no encaja entre las verticales>.

## 5. Riesgos y limites

- **Sesgo vertical.** <lo que dice sesgo_conocido en verticales.json>
- **Sesgo de fuente.** Cuantas fuentes son tipo D (comunicación de empresa).
- **Fuentes de pago.** <cuáles, o ninguna>
- **Huecos.** <verticales vacías y el motivo>
- **Antigüedad.** <cuántas fuentes tienen más de X meses>

## 6. Registro de evidencia

| Clave | URL | Medio | Fecha | Idioma | Peso |
|---|---|---|---|---|---|
| E01 | https://... | Expansion | 2026-09-25 | es | A |
| E07 | https://... | Reuters | 2026-09-27 | en | B |
```

## Puntos fijos

- El frontmatter existe para que `evaluar.py` pueda leerlo. Sin él, el script
  no sabe qué verticals se pidieron.
- El **Registro de evidencia** es lo que hace auditable el informe. Si una
  fuente se cita en el cuerpo y no está en la tabla, es una cita inventada.
- Las claves `[E01]` van en orden de aparición, no alfabético.
- La sección 5 no es opcional aunque no haya riesgos: se escribe "sin riesgos
  identificados en esta ventana" y ya. Un informe sin sección de límites
  afirma que no tiene ninguno, y eso nunca es cierto.

## Marca de peso

Hereda de `recolectar/CRITERIOS.md`:

| Peso | Significado |
|---|---|
| A | Dato primario: regulador, organismo oficial, la empresa con responsabilidad legal |
| B | Medio especializado con continuidad editorial |
| C | Medio generalista |
| D | Comunicación de la propia empresa (siempre `autodeclarado`) |
| E | Segunda mano, solo para encontrar el original. No se cita. |

El peso va en la columna del registro **y** en la celda cuando condiciona el
uso. Un dato tipo D que sostiene la tesis principal del informe es un problema
de la tesis, no un detalle de forma.
