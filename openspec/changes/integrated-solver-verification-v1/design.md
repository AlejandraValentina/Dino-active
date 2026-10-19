# Design — integrated-solver-verification-v1

Verificación de precisión numérica y costo computacional de la ruta integrada
2T de primer orden. Este documento es el diseño (A2) con la revisión
2026-10-19; la ejecución plena (A3b) queda bloqueada hasta autorización
explícita del dueño (A3a tiene autorización limitada; su corrida requiere
confirmación del dueño con el preregistro a la vista).

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
  99.039 s, `jsonify` serialización; RSS pico 51,585,024 B en los segmentos
  acotados del perfil (la corrida completa histórica llegó a ~2 GiB, cap
  3072 MiB).
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

## Fases de ejecución (revisión 2026-10-19)

- **A3a — Perfil de una corrida (autorizada con límites)**: UNA corrida de
  solver instrumentada a 3000 RPM sobre la identidad base ya caracterizada
  (variante "Escape original", malla 48 celdas, `max_cfl` 0.4), un solo
  proceso, cap duro global 1200 s (`run_logged --timeout 1200`) con deadline
  interno de stepping a t0+1080 s, `max_cycles` 8, memoria ≤3072 MiB, sin
  reintentos, sin resume, sin extensiones. Objetivo: perfil computacional,
  separación de costos por buckets exclusivos, tiempo por ciclo, RSS,
  periodicidad y conservación observadas. NO decide convergencia: alimenta la
  estimación revisada de costo y la propuesta de A3b.
- **A3b — Estudio de convergencia (NO autorizada)**: matriz revisada de la
  Línea 1, con preregistro propio y nueva autorización explícita del dueño.
  Nada de A3b inicia con este change.

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
| Espacial | malla ∈ {1, 2, 4, 8} celdas/sección vía `RESOLUTIONS` | `max_cfl` = 0.2 (un nivel por debajo del base) | 4 |
| Control de contaminación | `max_cfl` ∈ {0.2, 0.1} | malla más gruesa del brazo espacial (1 celda/sección) | 1 nueva |

- Regla de atribución: **ningún delta se computa entre configuraciones que
  difieran en más de un eje** (malla, CFL o índice de ciclo).
- No se extiende `RESOLUTIONS` ni `_ALLOWED`: malla 16 o CFL < 0.1 serían
  capability nueva versionada.

### Acoplamiento espacial/temporal declarado

- No existe knob de `dt` fijo en `integrated_2t` (solo `max_cfl`; el paso es
  adaptativo con rechazos CFL). Refinar la malla a CFL constante también
  reduce `dt` (dt ∝ Δx), de modo que los deltas espaciales contienen una
  componente temporal decreciente, y en las mallas gruesas `dt` crece y la
  componente temporal puede dominar. **No se asume aislamiento.**
- El brazo temporal (malla fija) cuantifica la componente temporal en la malla
  base; el brazo espacial corre a `max_cfl` 0.2 (no 0.4) para reducir esa
  componente en todos los niveles; el control de contaminación mide la
  sensibilidad temporal en la malla más gruesa, donde la contaminación es
  máxima. Si el delta temporal allí supera la tolerancia, el par grueso se
  excluye de los juicios de convergencia espacial y la exclusión se reporta
  explícitamente (nunca en silencio).
- El dominio declarable es la "par malla/CFL estudiada" con contaminación
  cuantificada; NUNCA independencia conjunta plena.

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
- Tolerancia mixta preregistrada (se congela POR OBSERVABLE en el preregistro
  de A3b; sin preregistro no hay veredicto): `|Δ| ≤ max(0.05·|x_fino|, atol_obs)`.
  - `Δ` = diferencia entre los dos niveles más finos comparados en el MISMO
    índice de ciclo; el denominador es `|x_fino|`, nunca el nivel grueso.
  - `atol_obs` = banda absoluta por observable, congelada ANTES de comparar y
    derivada de la configuración base congelada (malla 48 / CFL 0.4):
    `atol_obs = max(0.05·|x_base|, resolución numérica declarada del
    observable)`; para trabajos, la resolución declarada es ≥ la tolerancia de
    replay del contrato (5e-12 J); para masas, ≥ el ruido de conservación
    declarado por el contrato.
  - Cercanía a cero: si `|x_fino| ≤ atol_obs`, el criterio relativo no aplica
    y rige SOLO la banda absoluta. Cruce de signo entre niveles con alguna
    magnitud > `atol_obs` → `NOT_CONVERGED` (un cruce nunca es PASS por sí
    solo). `crankcase_gas_work_J` es el caso testigo (cruza cero en el barrido
    de referencia).
- Orden observado `p`: SOLO diagnóstico de consistencia. `p ∈ [0.5, 1.5]` es
  una etiqueta ("consistente con primer orden"), jamás un criterio de
  aceptación: la aceptación es la tolerancia. `p` no se calcula con pares no
  monótonos ni ratio ≠ 2. Sin extrapolación de Richardson como resultado,
  cota de error ni insumo de aceptación.

## Línea 2 — Rendimiento del pipeline

Buckets de tiempo EXCLUSIVO, medidos con timers in-process durante la corrida
(sin cProfile ni tracemalloc dentro de la corrida; el replay perfilado de un
primary almacenado queda como análisis posterior, fuera del presupuesto):

1. `INTEGRATION_PHYSICAL`: tiempo dentro de `IntegratedEngine2T.step`
   (incluye `_assemble` y copias de etapa internas).
2. `AUDIT_RECONSTRUCTION`: `make_integrated_cycle_primary` y
   `audit_integrated_cycle_primary` por ciclo como sub-timers separados; la
   reconstrucción interna que ejecuta el audit queda dentro del sub-timer de
   audit y no se suma a ningún otro bucket.
3. `SERIALIZATION_IO`: `_json_bytes`/`jsonify` del primary, gzip y escrituras
   `_atomic_write` (artefacto de ciclo, checkpoint, manifiesto) más lecturas
   de verificación.
4. `STATE_SNAPSHOT_ORCHESTRATION`: `engine.snapshot()`/`restore`/
   `compact_cycle_trace` por ciclo (copias de estado del orquestador).

Regla de exclusividad: cada bucket acumula tiempo en el punto de entrada de su
componente; los solapamientos se restan o se reportan como subcomponente;
prohibido sumar dos timers inclusivos. El residuo (`_advance_cycle` menos
`step`) se reporta como `DISPATCH_OVERHEAD`.

Métricas por configuración: s/ciclo, s/paso aceptado, s/(celda·ciclo), RSS
pico (sampler + `_rss_bytes`), bytes de artefacto por ciclo y share % por
bucket. A3a es una corrida única por autorización: sus shares se declaran
"single-sample" (estimación, no reproducibilidad); repetir la corrida requiere
autorización nueva.

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
- Artefactos: los recibos durables (preregistro, resultado, informes) van bajo
  `results/integrated-solver-verification-v1/`; los artefactos crudos de
  corrida (primaries, checkpoints, manifiestos, logs) van bajo el artifact
  root externo `DINO_ARTIFACT_ROOT`, nunca dentro del repo (precedente SPV1).
- A3a usa un driver de diagnóstico versionado
  (`scripts/diagnostics/integrated_solver_verification_a3a.py`) que NO modifica
  `motorsim/`: replica el loop de ciclos del exploratory workflow con los
  MISMOS primitivos importados (`_advance_cycle`,
  `make_integrated_cycle_primary`, `audit_integrated_cycle_primary`,
  `PeriodicDetectorV2`, `_atomic_write`, clasificación de periodicidad),
  porque el contrato por invocación del workflow es ≤600 s y A3a tiene cap
  autorizado de 1200 s. Divergencias declaradas: deadline de stepping
  t0+1080 s, cap externo 1200 s, `max_cycles` 8, timers/sampler de
  instrumentación, esquema propio de artefactos y `runner_sha256` = hash del
  driver. `--execute` exige el SHA-256 exacto del preregistro.

## Presupuestos e interrupciones

Modelo de costo: `costo ≈ ciclos × (celdas/48) × (0.4/CFL) × 200 s`, con tasa
base medida ≈170–230 s/ciclo a 48 celdas (primer orden limitado por CFL).
Estimaciones seriales preliminares (se recalculan con los costos medidos por
A3a antes de proponer A3b): CFL 0.4 → 600 s; CFL 0.2 → 1,200 s; CFL 0.1 →
2,400 s; malla 24 → 300 s; malla 12 → 150 s (3 ciclos).

- **A3a (autorizada 2026-10-19)**: una corrida, 3000 RPM, malla 48 / CFL 0.4,
  cap global 1200 s (deadline de stepping t0+1080 s + margen de finalización de
  120 s), `max_cycles` 8, memoria ≤3072 MiB, sin reintentos ni extensiones.

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

0. A3a (perfil, autorizada con límites): éxito = evidencia completa — ≥2
   ciclos con timers completos, auditoría por ciclo `recomputed`/`admissible`,
   periodicidad y conservación registradas o ausencia declarada
   (`NOT_EVALUATED`), recibo L1 con hashes, y estimación revisada de costo con
   banda de incertidumbre. A3a NO decide convergencia; cap agotado →
   `PARTIAL`/`INTERRUPTED_CHECKPOINTED` con evidencia exacta y sin extensiones.
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

## Estado de decisiones del dueño (revisión 2026-10-19)

- A3a: AUTORIZADA con límites: variante A, 3000 RPM, configuración base, UNA
  corrida, 1200 s, sin reintentos ni extensiones, sin MUSCL/física, P0–P9
  intactos. Ejecución pendiente de: preregistro commiteado + identidad
  reproducible validada + confirmación explícita del dueño con el preregistro
  a la vista.
- A3b: NO autorizada — tier (T0/T1/T2) sobre la matriz revisada y preregistro
  propio; sin autorización no inicia.
- Identidad: variante "Escape original" y RPM 3000 fijadas.
- Tolerancia: política mixta preregistrada definida en este diseño; los
  valores `atol_obs` por observable se congelan en el preregistro de A3b.

## Alternatives

| Opción | Costo | Riesgo | Complejidad | Evidencia |
|---|---|---|---|---|
| **A. Verificación primero (elegida)** | Medio: ≈3,600–7,200 s de estudio acotado | Bajo y útil: puede concluir "no convergente", evitando invertir en campañas sobre error no acotado | Baja: reutiliza `mesh_study_v1` + `exploratory_workflow` | Solver integrado de primer orden sin estudio de convergencia; perfil 3000 RPM dominado por auditoría (235.7 s vs 104.5 s); aprobación del dueño 2026-10-19 |
| B. MUSCL / segundo orden primero | Alto: cambio numérico versionado + re-verificación completa | Alto: mezcla el error de primer orden, reabre contratos y difiere la respuesta sobre el esquema actual | Alta: nueva capability numérica con gates P4–P8 | Rechazado explícitamente por el dueño: "no MUSCL todavía" (2026-10-19) |
| C. Sweep / campaña directa | Medio: campaña de 30 puntos (precedente IMPL2: 13,436 s) | Alto: curva no defendible con error no acotado, AFR 49 y sin convergencia | Media: infraestructura ya existe | IMPL2: 3/30 puntos `NUMERICAL_INVALID`; `full_rpm_sweep_execution_authorized=false`; rechazado por el dueño |

La opción A es la única que responde la pregunta pendiente (¿cuánto se desvía
el esquema actual?) sin comprometer evidencia histórica ni invertir en
campañas prematuras. Recomendación: A, con el tier T1 de presupuesto.
