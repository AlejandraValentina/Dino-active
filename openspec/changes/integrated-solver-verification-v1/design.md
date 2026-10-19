# Design — integrated-solver-verification-v1

Verificación de precisión numérica y costo computacional de la ruta integrada
2T de primer orden. Este documento es el diseño (A2); la ejecución (A3) queda
bloqueada hasta autorización explícita del dueño.

## Contexto y evidencia disponible

- `motorsim/integrated_2t.py` implementa volúmenes finitos de **primer orden
  espacial** (HLLC sin `reconstruct`) y **SSPRK2 temporal**; `_assemble` aporta
  2 veces por paso y el estado de etapa se copia con deepcopy. `max_cfl` es
  configurable (default 0.4, rango (0, 1]).
- No existe estudio de convergencia de la ruta integrada. El precedente
  reutilizable es `motorsim/mesh_study_v1.py` (`DINO_MESH_STUDY_V1`):
  `RESOLUTIONS=(1, 2, 4, 8)` por sección, `build_refinement_matrix` (setup +
  preflight sin solver) y `compare_resolution_receipts` (deltas crudos, sin
  umbrales; `spatial_independence: NOT_EVALUATED`).
- Costos medidos en el punto 3000 RPM (48 celdas, CFL 0.4):
  baseline 4 ciclos en 682.829 s (`INTERRUPTED_CHECKPOINTED`); recibo 600.125 s
  con 3 ciclos; perfil: `audit_integrated_cycle_primary` 235.693 s,
  `make_integrated_cycle_primary` 142.86 s, `step` 104.482 s, `_assemble`
  99.039 s, `jsonify` serialización; RSS pico 51,585,024 B.
- Fixture: `examples/projects/dino-2t-exhaust-comparison.dino2t.json`
  (sintético, AFR 49 / lambda 3.33, dos variantes de escape). NO existe motor
  Dino real ni datos medidos: este estudio verifica el solver, no el motor.
- Límites operativos existentes: `exploratory_workflow.preflight/run` con
  `budget_seconds` 1–600 s por invocación; el coordinator de sweep admite hasta
  3600 s; el supervisor externo de IMPL2 usó un cap de 21,600 s por precedente.
- Riesgo de no hacerlo (decidido por el dueño): sin convergencia, la curva
  IMPL2 (3/30 puntos `NUMERICAL_INVALID`, AFR 49) no es defendible como base
  predictiva y cada campaña nueva acumula error no acotado.

## Alcance y no-metas

Alcance: líneas 1 (precisión) y 2 (rendimiento). No-metas: sin MUSCL, sin
cambios de física, sin campañas, sin optimizaciones, sin claim predictivo.

## Identidad congelada del experimento (propuesta a fijar en preregistro)

- Fixture `dino-2t-exhaust-comparison` con UNA variante de escape fija
  (recomendación: "Escape original" A, la ya caracterizada; elegir una evita
  confundir convergencia con diferencia de geometría).
- RPM del punto de operación: 3000 (ya caracterizado; no introduce un punto
  nuevo sin decisión del dueño).
- Mínimo 3 ciclos completos por configuración; si el tier no alcanza, 2 ciclos
  y se declara el límite como restricción del estudio.
- Documentos de motor generados por `build_refinement_matrix` sobre la
  identidad del fixture, con hash de configuración por celda de la matriz.

## Línea 1 — Precisión numérica

### Matriz de experimentos

| Eje | Niveles | Fijo | Celdas de matriz |
|---|---|---|---|
| Temporal | `max_cfl` ∈ {0.4, 0.2, 0.1} | malla base (48 celdas) | 3 |
| Espacial | malla ∈ {1, 2, 4, 8} celdas/sección vía `RESOLUTIONS` | `max_cfl` = 0.4 | 4 (2 nuevas + 2 ya caracterizadas) |

- No se extiende `RESOLUTIONS` ni `_ALLOWED`: malla 16 o CFL < 0.1 serían
  capability nueva versionada.
- Límite declarado: convergencia espacial a un solo CFL y temporal a una sola
  malla no prueban independencia conjunta; el dominio que se declare es la
  "par malla/CFL estudiada", no un espacio bidimensional completo.

### Observables y comparación

- Por ciclo, desde la auditoría primaria (solo `DEFINED`):
  `net_piston_gas_work_J`, `cylinder_indicated_work_J`,
  `crankcase_gas_work_J`, pico de presión de cilindro, masa atrapada y
  conservación de partición. IMEP/BMEP/FMEP solo si `DEFINED`; si están
  `UNDEFINED`/`NOT_IDENTIFIABLE` se reporta la ausencia sin sustituir.
- Señal de fase opcional vía `extract_primary_phase_series` + L2 con
  interpolación declarada (el comparador de C12 ya lo hace); los campos
  nativos NO se interpolan.
- Comparación en el MISMO índice de ciclo entre configuraciones (ciclo 2 y el
  último ciclo común). Si el trend del delta no es estable entre índices, el
  observable se clasifica `NOT_CONVERGED` por no estacionariedad: la
  diferencia entre ciclos incluye deriva de periodicity no resuelta, y este
  estudio no la oculta.
- Deltas crudos siempre. Orden observado `p` solo para pares con refino r=2 y
  comportamiento monótono (`p = log2(|Δ12| / |Δ23|)`). Sin extrapolación de
  Richardson a malla infinita como resultado; si se reporta, se etiqueta como
  estimación metodológica, no como valor.

### Clasificación de convergencia (propuesta a fijar en preregistro)

- `CONVERGING_MONOTONE`: |delta| decreciente en ≥2 pares consecutivos.
- `NON_MONOTONE` / `NOT_EVALUATED` / `NOT_CONVERGED` en el resto de los casos.
- Consistencia con primer orden: banda `p ∈ [0.5, 1.5]` (PROPUESTA).
- Tolerancia de convergencia: |delta entre los dos niveles más finos| ≤ 5%
  relativo para métricas clave (trabajos y masas) (PROPUESTA). Ambos valores
  se congelan en el preregistro; sin preregistro no hay veredicto.

## Línea 2 — Rendimiento del pipeline

Buckets por fase usando los hooks de perfil existentes:

1. `INTEGRATION_PHYSICAL`: `step` + `_assemble` + copia de estados de etapa.
2. `AUDIT_RECONSTRUCTION`: `audit_integrated_cycle_primary` +
   `make_integrated_cycle_primary` (+ replay).
3. `SERIALIZATION_IO`: `jsonify` + escritura de primary/manifest.

Métricas por configuración: s/ciclo, s/paso aceptado, s/(celda·ciclo), RSS
pico, bytes de artefacto por ciclo y share % por bucket. Una corrida de control
repetida por configuración del eje temporal estima el ruido; si el tier no la
incluye, el share se declara "single-sample" (estimación, no reproducibilidad).

Criterio de decisión (medición, no ejecución): si
`AUDIT_RECONSTRUCTION + SERIALIZATION_IO` ≥ 50% del total, la próxima
optimización (fuera de este change) apunta primero a auditoría/serialización;
si `INTEGRATION_PHYSICAL` domina, apunta a `_assemble`/deepcopy. No se
implementa ninguna optimización aquí.

## Preregistro, identidad y provenance

- El diseño aprobado, la matriz, las tolerancias y el presupuesto del tier
  autorizado se congelan en un commit de preregistro con SHA-256 por artefacto
  (patrón P3: sin preregistro no hay juicio).
- Cualquier cambio posterior de diseño, matriz o tolerancia invalida el
  preregistro y exige uno nuevo.
- Los resultados se comparan solo contra criterios preregistrados; sin
  análisis post-hoc ni reclasificación retrospectiva.
- Restricción de artefactos: A3 escribe solo bajo
  `results/integrated-solver-verification-v1/` con sufijo de tier.

## Presupuestos e interrupciones

Modelo de costo: `costo ≈ ciclos × (celdas/48) × (0.4/CFL) × 200 s`, con tasa
base medida ≈170–230 s/ciclo a 48 celdas (primer orden limitado por CFL).
Estimaciones seriales: CFL 0.4 → 600 s; CFL 0.2 → 1,200 s; CFL 0.1 → 2,400 s;
malla 24 → 300 s; malla 12 → 150 s (3 ciclos).

| Tier | Contenido | Estimado serial | Cap propuesto |
|---|---|---|---|
| T0 mínimo | temporal {0.4, 0.2} + espacial {24, 48}, 3 ciclos | ≈2,700 s | 3,600 s |
| T1 recomendado | T0 + temporal {0.1} + malla 12 | ≈5,250 s | 7,200 s |
| T2 extendido | T1 + repetición de ruido + 4º ciclo | ≈10,000 s | 10,800 s |

- Con ≤4 workers y RSS agregado ≤4,096 MiB (precedente IMPL2); caps de tier
  aplicados por supervisor externo (mayores que el cap 600 s por invocación de
  `exploratory_workflow`).
- Invocación individual: cap existente 1–600 s; checkpoint y resume ligados a
  identidad y preregistro, nunca a conveniencia.
- Fail-closed: NaN/Inf, >50% de pasos rechazados por CFL, mismatch de
  identidad o de conservación → detener la configuración y clasificar
  `FAIL_CLOSED` con evidencia exacta.
- Prohibido: extender ciclos, CFL o malla post-hoc; relanzar con horizonte
  mayor; cambiar tolerancias. Todo aumento exige nuevo preregistro y
  autorización explícita del dueño (sin extensiones automáticas).

## Criterios de aceptación (de A3, cuando se autorice)

1. Cada configuración de la matriz termina `DONE`/`PARTIAL`/`FAIL_CLOSED` con
   recibo y hash; sin omisiones silenciosas.
2. Reporte de convergencia por observable con deltas crudos en índices de
   ciclo comunes y clasificación explícita (`NOT_CONVERGED` donde corresponda).
3. Declaración de dominio: "precisión numérica soportada a la par malla/CFL
   estudiada" SOLO si la clasificación y tolerancia preregistradas se cumplen;
   si no, "error no acotado — curvas exploratorias, no predictivas".
4. Tabla de separación de costos con shares y ruido (o declaración
   single-sample).
5. Declaración obligatoria: convergencia necesaria pero no suficiente; sin
   validación experimental; sin claim predictivo.
6. P0–P9 y evidencia histórica intactas (verificación por hash).

## Decisiones del dueño pendientes (inputs del preregistro; no bloquean A2)

- Tier de presupuesto a autorizar: T0 / T1 / T2 (recomendación: T1).
- Identidad congelada: variante de escape A (recomendada) y RPM 3000.
- Tolerancia de convergencia (propuesta 5% relativo) y banda de orden
  (propuesta p ∈ [0.5, 1.5]).
- Registro explícito de que A3 no se ejecuta hasta su autorización.

## Alternatives

| Opción | Costo | Riesgo | Complejidad | Evidencia |
|---|---|---|---|---|
| **A. Verificación primero (elegida)** | Medio: ≈3,600–7,200 s de estudio acotado | Bajo y útil: puede concluir "no convergente", evitando invertir en campañas sobre error no acotado | Baja: reutiliza `mesh_study_v1` + `exploratory_workflow` | Solver integrado de primer orden sin estudio de convergencia; perfil 3000 RPM dominado por auditoría (235.7 s vs 104.5 s); aprobación del dueño 2026-10-19 |
| B. MUSCL / segundo orden primero | Alto: cambio numérico versionado + re-verificación completa | Alto: mezcla el error de primer orden, reabre contratos y difiere la respuesta sobre el esquema actual | Alta: nueva capability numérica con gates P4–P8 | Rechazado explícitamente por el dueño: "no MUSCL todavía" (2026-10-19) |
| C. Sweep / campaña directa | Medio: campaña de 30 puntos (precedente IMPL2: 13,436 s) | Alto: curva no defendible con error no acotado, AFR 49 y sin convergencia | Media: infraestructura ya existe | IMPL2: 3/30 puntos `NUMERICAL_INVALID`; `full_rpm_sweep_execution_authorized=false`; rechazado por el dueño |

La opción A es la única que responde la pregunta pendiente (¿cuánto se desvía
el esquema actual?) sin comprometer evidencia histórica ni invertir en
campañas prematuras. Recomendación: A, con el tier T1 de presupuesto.
