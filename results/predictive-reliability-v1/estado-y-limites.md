# Dino2T — estado de la intervención física

2026-10-26. Estado científico: **PARTIAL**. Candidatos numéricos verificados;
precisión predictiva no demostrada. Revisión **SELF_REVIEW**, sin claim de release.

## Actualización tras la continuación autorizada

Se añadió únicamente un diagnóstico de 176 celdas, dos revoluciones independientes,
184.42 s de cálculo. La secuencia de trabajo transitorio 44/88/176 es
28.5676/29.4581/30.2026 J: convergencia lenta, todavía no independencia de malla.
Conservación normalizada <1.33e-15 y checkpoints PASS. Los estados de ciclos 1/2
no cumplen periodicidad en ninguna malla con el comparador existente, sin nuevos
pasos para esa comprobación. No se amplió automáticamente el presupuesto.

Nuevas comprobaciones de diagnósticos: 41 PASS. Nueva regresión P4–P8:
301 PASS, 3 SKIP. No se repitió la suite general ni se presenta como aprobada.

El inventario público complementario reconoce los 20 puntos X30 ya digitalizados
y conserva sus faltantes. Encontró una referencia parcial de oscilaciones de
admisión con volumen de cárter documentado; no se adoptó un nuevo motor completo.
Detalles y fuentes primarias en `public-dataset-survey-v2/report.md`; resultados
numéricos en `mesh-three-level-note-v1.md`. El plan y la validación siguen abiertos.

## Implementado y comprobado

1. **Acoplamiento seleccionable**, conservando el camino anterior. La formulación
   V2 trata estrangulamiento, compatibilidad característica, ramas supersónicas
   causales y choque normal bajo la hipótesis explícita de tobera ideal
   equivalente. Rechaza estados no admisibles sin recortar ni forzar caudal.
   Resuelve 1008/1008 casos de la matriz declarada, incluidos los 37 sin solución
   del cierre subsónico V1. **No es el mismo cierre físico:** no demuestra que
   una lumbrera real tenga la expansión/pérdidas de esa tobera equivalente.
2. **Históricos inspeccionados:** 48 estados terminales, 24 conexiones abiertas,
   sin el fallo V1. Todos son de fase 0 grados; los registros antiguos no permiten
   excluirlo durante blowdown. No se atribuye a esa inspección una cobertura que
   no tiene.
3. **MUSCL seleccionable**, conservando el primer orden por defecto. En pruebas
   suaves aisladas los órdenes observados superan 2.12; choques, admisibilidad,
   especies, conservación y restart verificados. Celdas de frontera siguen
   siendo de primer orden. No se modificó HLLC/HLLE ni SSPRK2 congelados.
4. **Diagnósticos integrados acotados:** dos revoluciones independientes, no
   curvas periódicas. Diferencia temporal máxima de estados MUSCL 0.0893%.
   Conservación y replay primario con el productor correspondiente pasan.
5. **Sensibilidad espacial:** 44→88 celdas, 66.51 s de cálculo, residuos
   normalizados menores que 1e-15. Trabajo indicado transitorio +3.12%; diferencias
   locales del escape mayores. No se demostró independencia de malla.
6. **Defecto térmico corregido:** en la celda móvil se usa el volumen real de
   cada etapa al aplicar Q/V. Error de conservación de ~1e-7 J reducido a
   ~5e-15 J en el caso breve, sin alterar h, Twall ni criterios numéricos.

## Pruebas y límites de la regresión

- 391 pruebas conjuntas de los candidatos/corrección aprobadas.
- 15 pruebas integradas de calor y láminas dinámicas aprobadas.
- P4–P8 final: **301 PASS, 3 SKIP**, cuatro avisos NumPy preexistentes,
  178.55 s, con los 26 archivos explícitos de la regresión histórica.
- Una selección errónea inició la suite general y agotó 300 s: **no fue PASS**.
  Sus siete fallos iniciales se reprodujeron aisladamente y se conservan. Incluyen
  expectativas de dos entrypoints frente a tres en el packaging existente,
  evidencia primaria P8 histórica sin la referencia/schema esperada, cuatro
  preflights históricos que rechazan correctamente hashes de fuente/identidad
  distintos y un contrato de presentación RPM que espera `error` y recibe
  `neutral`. No se modificaron contratos ni se reescribieron hashes para
  hacerlos pasar. Packaging, UI y auditor legacy están sin cambios respecto de
  e3be7e2; no se proclama que toda la suite del repositorio esté aprobada.

## Bloqueo para una predicción confiable

El inventario inspecciona nueve manifiestos vinculados por hash y 14 candidatos
numéricos locales. No establece un paquete completo de **geometría, condiciones
y medición trazable del mismo motor**. El caso funcional conserva supuestos no
identificados de barrido, descarga, láminas, calor, combustión y pérdidas.
La selección experimental X30 anterior y su bloqueo se conservan; no se abrió
su ejecución ni se rellenó el cárter mediante supuestos.

Antes de calibración o validación hacen falta datos independientes de componentes
y entradas/salidas medidas compatibles, además de resolver la incertidumbre de
malla del caso que se quiera predecir. Una potencia transitoria parecida no
cumple esos requisitos. No se sustituye la medición por un fixture sintético.

## Referencias preservadas

CRV1 rc7: commit fc27542155840cdadbcc2b591ae5cd8e99031899;
ZIP SHA-256 2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a.
Referencia de desarrollo previa: e3be7e2. Sin builds, campañas RPM, limpieza,
cambios de Desktop ni push. Los modelos nuevos siguen siendo opt-in.
Espacio libre al cierre técnico: aproximadamente 6.27 GiB en E: y 21.02 GiB
en C:, por encima del preflight/reserva de 2 GiB.

Los checkpoints nativos vinculan configuración, no toda la fuente; el auditor
primario sí vincula fuente. Históricos y sus identidades se conservan. Una
continuación con la corrección térmica constituye evidencia nueva, no un replay
idéntico de una trayectoria calculada con el defecto.

Detalle: `connection-v2-engineering-note.md`, `spatial-engineering-note-v1.md`,
`mesh-engineering-note-v1.md`, `moving-cell-heat-note-v1.md` y
`measured-data-inventory.json`, en este directorio.
