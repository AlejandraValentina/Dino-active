# Auditoría Dino 2T / MotorSim vs EngMod2T — Informe final

| Campo | Valor |
|---|---|
| Fecha de corte | 2026-10-19 |
| Base de inspección | `ea2ff2d13d8dd04bf321bf986d38ed446edc50c6` (HEAD; working tree con cambios ajenos preservados) |
| Alcance | Solver 2T, física, prestaciones, campañas, evidencia, rendimiento, UI, arquitectura y comparación funcional con EngMod2T |
| Método | Inspección read-only de código, tests, contratos, receipts y artefactos; sin campañas nuevas ni cambios de producto |
| Autor | Sesión de auditoría (agente); revisión humana pendiente |

> **Carácter del documento.** Este informe no modifica contratos P0–P9, no reinterpreta evidencia histórica y no declara validación experimental. Separa explícitamente evidencia observada, artefactos, afirmaciones documentales e hipótesis. Las capacidades de EngMod2T provienen de sus páginas oficiales; los detalles de método marcados como "folleto asociado" provienen de documentación EngMod2T de 2004 (Scribd) y no se tratan como especificación oficial vigente.

---

> **Vigencia.** Este documento conserva el corte **2026-10-19** y su base `ea2ff2d`. La **sección I** agrega el delta verificado al **2026-10-26** (HEAD `d048ab4`, cierre de aceptación; EXE `fc275421`) y corrige el estado administrativo; no reescribe A–H ni convierte evidencia exploratoria en validación. Para conteos vivos de cola, ejecutar `python scripts/agents/program_status.py brief`.

---

## A. Diagnóstico ejecutivo

MotorSim es hoy **una plataforma de simulación 2T exploratoria bien instrumentada**: tiene un motor integrado (cilindro + cárter + puertos + escape 1D), contratos versionados, auditoría de conservación, checkpoints, campañas con hashes, una UI Windows funcional y un contrato de curvas de potencia. No es, todavía, **un simulador profesional comparable a EngMod2T**: no hay validación experimental, los resultados centrales son sintéticos, la verificación numérica cubre sobre todo rutas standalone, y no existe una curva de potencia utilizable.

### A.1 Estado administrativo verificado

Fuente: `results/2t-commercial-core-20261002/program-status.json`.

| Elemento | Estado real |
|---|---|
| `current_objective` | `DINO_POWER_CURVE_V1` (UI/infraestructura de curvas), `OPEN`, gate `REVIEW`, 5/5 tasks DONE |
| Gate R2 (`MOTORSIM_2T_V1_CLOSURE_R2`) | `PASS` semántico/offline, `GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED`, `CONDITIONAL_ON_P4`; la "tercera revisión externa" está registrada como comunicada por el dueño, no reproducida por el agente |
| Gate histórico V1 | `FAIL_TERMINAL` (20 ciclos exactos, sin extensión post-hoc) |
| `FULL_RPM_SWEEP_V1` | `PARTIAL`/`REVIEW`: 27 `PERIOD_1`, 3 `NUMERICAL_INVALID`; `execution_authorized:false`; receta FAST `DISABLED` |
| `ready_claim` | `false`; validación experimental `NOT_PERFORMED`; P9 no reclamado |

### A.2 Hallazgos centrales

1. **El gap indicado↔freno está dominado por el trabajo de gas del cárter (~69% de pérdida), no solo por FMEP.** Ejemplos: A@1300 IMEP 31.34 → BMEP 8.08 kPa con ≈−21.76 kPa de cárter; B@1300 IMEP 68.73 → BMEP 19.75 kPa con ≈−47.48 kPa de cárter.
2. **La curva existente es de carga ultrabaja, no una curva de potencia:** AFR 49 (λ 3.33, φ 0.30); A se vuelve negativa desde ~3700 RPM; B alcanza ~0.12 kW de freno a 3100 RPM.
3. **La ruta integrada es numéricamente de primer orden espacial** (FV/HLLC con estados primitivos de cara, sin MUSCL) y SSPRK2 temporal; no reutiliza `gas1d.solver` y no está cubierta por T01–T12/P2/P2B.
4. **El gate R2 es semántico/offline**, no una verificación de precisión ni validación experimental; los primarios conservados declaran periodicidad `NOT_EVALUATED`.
5. **No hay proyecto Dino real ni datos medidos** en los artefactos revisados: `examples/projects/dino-2t-exhaust-comparison.dino2t.json` es "Fixture A — sintético" y `dino-2t-starter.dino2t.json` declara `SYNTHETIC_UNVALIDATED`.
6. **El costo computacional dominante es la auditoría/reconstrucción por ciclo**, no el kernel de flujo: un punto de 3000 RPM no completa 4 ciclos en 600 s, y la UI no puede correr la campaña completa.

**Veredicto en una línea**: MotorSim tiene infraestructura de producto por delante de su madurez física; EngMod2T sigue siendo la referencia funcional, y la distancia crítica no es de "features" sino de **verificación numérica y modelos predictivos**.

---

## B. Matriz comparativa EngMod2T

| Capacidad | EngMod2T (documentado) | MotorSim actual | Brecha | Evidencia |
|---|---|---|---|---|
| Configuraciones de motor | 1–8 cilindros: inline, V, boxer (cárter común/separado), opposed piston, radial, uniflow, boosted, reverse uniflow | Un cilindro + cárter 0D (`CRANKCASE_MODEL_V2`), variantes de escape | Alta: falta multi-cilindro/layouts/turbo | `vannik.co.za/EngMod2TDetails.htm`; `motorsim/crankcase.py` |
| Gasdinámica 1D | Método GPB completo en pipes/ducts/ports/plenums | FV HLLC, **primer orden espacial**, SSPRK2, 48 celdas en el fixture | Alta: segundo orden declarado en contrato (`MUSCL`) pero no ejecutado en la ruta integrada | `motorsim/integrated_2t.py` `_assemble`/`step`; `docs/gasdynamic/1d_contract_v1.json` |
| Scavenging | Modelo basado en Blair (folleto asociado); sin factor empírico para separar zonas | Partición **post-hoc** en snapshots de cierre de puertos; transporte single-zone; etiqueta `TWO_ZONE_PROFILE` sin two-zone real | Alta: no es modelo predictivo | `motorsim/engine_physics_v1.py:125-129`; `motorsim/scavenging.py`; `motorsim/scavenging_partition_v1.py` |
| Combustión | Two-zone típico, Wiebe (folleto asociado); separación quemado/fresco | `FuelCoupledCombustionV1`: 1–2 Wiebe, sin split burned/unburned | Media-alta | `motorsim/fuel_combustion.py:158-185` |
| Admisión/puertos | Reed case/cylinder, reed+piston port, piston port, rotary disc/shaft/drum, poppet; modela Boyesen y floor ports; throttles/boost bottles/air box | Puertos geométricos (`GENERIC_2T_PORTS_V1/V2`), admisión rectangular al cárter, reed estático sintético en el fixture (`dynamic_reed_binding=null`) | Alta | `motorsim/two_stroke_ports.py`; `motorsim/ports.py`; `motorsim/intake.py`; `motorsim/reed.py` |
| Geometría fina / pérdidas de carga | Cd-maps para puertos, extremos y discontinuidades (folleto asociado) | Sin Cd-maps, sin radios/chaflanes; solo área descubierta | Alta | `motorsim/ports.py`; `motorsim/exhaust_mesh_v2.py` |
| Turbocarga / mapas | DigiComp/DigiTurb; mapas de compresor/turbina con flujo superpuesto | Ausente | Alta | `vannik.co.za/EngMod2T.htm` |
| Salidas | RPM (P-av de últimas 3 ciclos, IMEP/BMEP/FMEP, BSFC, Dratio, Purc, Seff/Teff/Ceff, TAF…), trazas por grado, PV, mapas, sound | Series brake power/torque, IMEP/BMEP/FMEP, ISFC/BSFC, clasificación `DEFINED`/gaps, CSV, trazas | Media: base sólida, falta riqueza y validación | `motorsim/power_curve.py`; `motorsim/desktop/performance_curves.py`; `motorsim/engine_results.py` |
| Importación de mediciones | Curvas de dyno y trazas medidas | `measurement_data.py` (pressure_trace/dyno_torque/dyno_power) como **contraste descriptivo**, no calibración | Media: falta pipeline de validación con holdout | `motorsim/measurement_data.py`; `motorsim/external_view.py` |
| Campañas / batch | Batch2T, batch y vehículo | `power_curve_sweep.py`, runner IMPL2, checkpoints, receipts; UI limitada a 600 s/punto y 1800 s total | Media: infra existe; presupuesto/UX no cubre campañas reales | `motorsim/power_curve_sweep.py`; `motorsim/desktop/execution_page.py` |
| QA numérico | Producto maduro, uso comercial | Conservación/auditoría fuertes; verificación de precisión incompleta; R2 semántico | Alta en precisión demostrada | `results/scavenging-partition-conservation-v1`; `results/p2b-gas1d-20260918` |

---

## C. Calidad del solver

### C.1 Ruta integrada

`motorsim/integrated_2t.py` implementa su propio lazo FV/HLLC:

- En `_assemble` usa estados primitivos de cara directamente, **sin `reconstruct` ni MUSCL** (primer orden espacial).
- Avanza con **SSPRK2**; `_assemble` se ejecuta dos veces por paso y `_combine` hace `deepcopy(base)` por paso.
- `dt` equivalente a ≤0.5° de cigüeñal; 48 celdas en el fixture.
- No llama a `gas1d.solver.solve`.

### C.2 Verificación

- El contrato 1D (`docs/gasdynamic/1d_contract_v1.json`) declara baseline primer orden/HLLC/Euler y extensión MUSCL/SSPRK2, pero T01–T12 figuran `SPECIFIED_NOT_EXECUTED`.
- P2B terminó `FAILED_INFRASTRUCTURE` (T04 wall_timeout) y su resume `P2_BLOCKED_SECOND_ORDER` con `P2_PASS_1D_CORE_VERIFIED:false`.
- `README.md:139` todavía afirma `P2_PASS_1D_CORE_VERIFIED` — está desactualizado y contradice los receipts.
- **T01–T12/P2/P2B solo cubren `gas1d`/`coupled` standalone; no verifican el solver integrado.**
- El gate R2 sí evalúa el ciclo integrado, pero como gate **semántico/offline** de outputs y conservación, no de convergencia.

### C.3 Cierres físicos

- Combustible `SYNTHETIC_GASOLINE_V1` (LHV 43 MJ/kg, AFR estequiométrico 14.7126).
- Scavenging post-hoc; reed estático en el fixture; geometría sin Cd-maps.
- Térmica prescrita (`MOTORSIM_THERMAL_V1`); cárter 0D.
- Todo declarado como sintético, pero limita cualquier extrapolación.

### C.4 Malla y periodicidad

- La refinación 1/2/4/8 no demostró independencia espacial en la evidencia histórica.
- Los ciclos primarios R2 conservados declaran `periodicity.status=NOT_EVALUATED`.
- R2 registró A′ `PERIOD_1 @ 73/111` y B′ `PERIOD_1 @ 38/47`, pero se apoya en 4 primarios fijos y una revisión externa no reproducida localmente.

### C.5 Juicio

El solver es **autoconsistente, auditable y adecuado para exploración cualitativa**; no es un solver predictivo verificado. Confundir conservación con exactitud o periodicidad con validación sería el error central a evitar.

---

## D. Rendimiento computacional

| Medición | Valor |
|---|---|
| Campaña IMPL2 (30 puntos) | 13,436.111 s consumidos / 21,600 s de cap; 4 workers; memoria agregada declarada 4,096 MiB |
| Integridad de artefactos | 1,465 hashes verificados, 0 errores, 273.778 s |
| Punto 3000 RPM | preflight con 0 pasos; baseline 4 ciclos en 682.829 s **interrumpido** por presupuesto 600 s; receipt 600.125 s, exit 124, 3 ciclos manifestados |
| Hotspots (perfil) | `audit_integrated_cycle_primary` 235.7 s; `make_integrated_cycle_primary` 142.9 s; `step` 104.5 s; `_assemble` 99.0 s; `jsonify` hotspot |
| Presupuesto UI | 1–600 s por punto, 1–3,600 s total (default 1,800 s) — **no puede correr la campaña completa**; esta se ejecutó con supervisors externos |

**Lectura**: el costo dominante no es el kernel de flujo, sino la **auditoría/reconstrucción/serialización por ciclo**. Un solo punto de 3000 RPM no completa 4 ciclos en 600 s. Con 48 celdas y primer orden, el costo ya es alto; pasar a segundo orden empeora el presupuesto. EngMod2T no publica cifras comparables; **no hay base para afirmar paridad ni ventaja de rendimiento**. `FAST_RECIPE_V1` está `DISABLED`. Cualquier optimización futura debería atacar el pipeline de auditoría/JSON antes que el solver.

---

## E. Arquitectura: KEEP / SALVAGE / REBUILD

### KEEP (ya sirve, no tocar sin motivo)

- Núcleo integrado `integrated_2t.py` como motor exploratorio, con sus límites explícitos.
- Configuración/proyectos/variantes (`MOTORSIM_ENGINE_PROJECT_V1`), editor de puertos/escape.
- Contratos de curvas y campañas: `power_curve.py`, `power_curve_sweep.py`, `full_rpm_sweep_v1*.py`.
- Workflow desktop (`execution_page`, `results_page`, `run_history`, `performance_curves`), UI dual brake, CSV, clasificación `DEFINED`.
- Infraestructura de evidencia: auditoría, conservación, checkpoints/restart, receipts con hashes.
- `gas1d/open_end_plenum_v2.py` como boundary opt-in; `scavenging_partition_v1.py` como auditoría de conservación.
- `measurement_data.py` / `external_view.py` como contraste descriptivo (no venderlo como validación).

### SALVAGE (conceptos/partes, no como ruta de producto actual)

- `gas1d`: HLLC, `reconstruct`/MUSCL y boundaries como **segundo orden versionado** a portar al camino integrado.
- `exhaust_mesh_v2.py`: mecanismo de refinamiento como contrato (sin reclamar convergencia).
- `reed.py`/`reed_coupling.py`: geometría `HingedFlapGeometryV1` como base para reed dinámico futuro.
- `thermal.py`, `duct_network.py`, `coupling.py`: ideas reutilizables con reescritura.
- Backends legacy de escape (`exhaust1d`, `exhaust_batch`, `exhaust_numpy`, `exhaust_numba`, `exhaust_numba_fused`, `exhaust_fast`, `hybrid_exhaust`, `hybrid_fast`): **solo referencia/regresión P4**. Son 6 variantes no integradas; no invertir más en mantenerlas en paralelo.

### REBUILD / GAP real

- Scavenging predictivo estilo Blair (o two-zone con entrainment).
- Combustión two-zone con temperaturas quemado/fresco.
- Geometría con Cd-maps, radios/chaflanes, Boyesen/floor ports.
- Multi-cilindro, layouts, turbo/cárter externo.
- Optimización/calibración con holdout.
- Unificación: hoy conviven dos rutas numéricas (integrada primer orden vs `gas1d` segundo orden) sin una única autoridad de solver.

---

## F. Funcionalidades faltantes (ordenadas por impacto)

1. **Dataset experimental trazable y validación con holdout** — sin esto no hay claim defendible.
2. **Scavenging predictivo** — hoy es partición post-hoc.
3. **Combustión two-zone real** (split quemado/fresco, entrainment).
4. **Reed dinámico en el fixture** (`dynamic_reed_binding=null`; binding sintético existe pero no se usa).
5. **Geometría/ductos con Cd-maps** y puertos no rectangulares.
6. **Multi-cilindro/layouts/turbo** (paridad EngMod2T).
7. **Verificación de convergencia espacial/temporal de la ruta integrada** (MUSCL/RK2, malla).
8. **Batch/paramétrico de producto** (análogo Batch2T) y presupuesto de campaña usable desde UI.
9. **Optimización/calibración** con identificabilidad.
10. Salidas ricas (trazas, PV, mapas, sound) — deseables, no bloqueantes.

---

## G. Ruta en tres etapas

### Etapa 1 — Hacer confiable el solver integrado en un dominio declarado (máximo leverage)

- Objetivo: separar error espacial/temporal en la ruta integrada; portar MUSCL/SSPRK2 como opción versionada; correr casos analíticos y de referencia; demostrar convergencia de malla en el fixture; clasificar periodicidad; fijar dominio soportado (RPM, AFR, supuestos).
- Salida: suite de verificación versionada PASS + límites explícitos + documentación sin contradicciones (README/`continuation_status`).
- Esfuerzo: muy alto. Dependencia de todo lo demás.

### Etapa 2 — Curva de ingeniería por RPM con campaña autorizada

- Objetivo: con el dominio de Etapa 1, preregistrar y ejecutar el sweep de 30 puntos con autorización explícita y presupuesto global; producir HP/torque solo de puntos `DEFINED`, mantener huecos, sin interpolación; etiquetar como predicción de ingeniería bajo supuestos sintéticos.
- Salida: reporte completo con hashes, clasificación y fallos.
- Esfuerzo: medio-alto; la infraestructura ya existe. Requisito ya resuelto según `program-status`: `EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED → RESOLVED`; falta autorización.

### Etapa 3 — Realismo físico y validación

- Objetivo: scavenging predictivo, two-zone, reed dinámico, Cd-maps, multi-cilindro/turbo; luego, adquisición de datos de dinamómetro, partición ajuste/holdout y validación experimental del dominio reclamado.
- Salida: claim validado o etiqueta "predictivo" permanente.
- Esfuerzo: alto; no empezar antes de Etapa 1.

En paralelo y sin bloquear: la UI/desktop y los contratos de comparación ya están listos; mantenerlos.

---

## H. Veredicto — siete preguntas

> Las siete preguntas están reconstruidas del alcance A–H; no se conserva el texto literal del pedido original. Si alguna no coincide, debe corregirse en una revisión de este documento.

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Puede MotorSim producir hoy una curva HP/torque utilizable? | **No.** La infraestructura sí (contrato, UI, sweep, CSV). La curva científica no: los 30 puntos son sintéticos, AFR 49, A negativa desde ~3700 RPM, B ~0.12 kW máx de freno, y el gate está `PARTIAL/REVIEW`. |
| 2 | ¿Cuán lejos está de EngMod2T? | **Lejos en física de producto** (scavenging predictivo, two-zone, reed dinámico, Cd-maps, multi-cilindro, turbo) y **cerca en infraestructura de campañas/UI/auditoría**. No hay comparación de precisión posible sin datos experimentales; no usar métricas de "paridad". |
| 3 | ¿Es confiable el solver? | **Como herramienta exploratoria, sí; como predictor, no.** Conservación/auditoría son fuertes; la verificación de precisión de la ruta integrada está incompleta (primer orden no demostrado como convergente, P2/P2B standalone, R2 semántico). |
| 4 | ¿Dónde está el cuello de botella? | Tres: **(a) científico** (modelos sintéticos/simplificados), **(b) numérico** (primer orden + convergencia no demostrada), **(c) computacional** (auditoría/reconstrucción por ciclo; 600 s no alcanzan para 3 ciclos; la UI no puede correr la campaña). |
| 5 | ¿Qué se conserva? | Núcleo integrado exploratorio, proyectos/configuración, contratos de curva/campaña, workflow desktop, infraestructura de evidencia, boundary V2, import descriptivo. No se conservan los 6 backends legacy de escape como línea de producto. |
| 6 | ¿Qué falta para una curva real? | Dominio verificado (Etapa 1), campaña autorizada con presupuesto (Etapa 2) y, para "real" en sentido estricto, un **dataset experimental con holdout** (Etapa 3) más los modelos predictivos de F. |
| 7 | ¿Cuál es la ruta más corta y la recomendación? | **Etapa 1 → Etapa 2**, sin perseguir paridad de features con EngMod2T antes de arreglar verificación/periodicidad. Recomendación concreta: (i) cerrar la contradicción P2/README y fijar el dominio soportado; (ii) portar MUSCL/RK2 versionado y demostrar convergencia en el fixture; (iii) preregistrar y ejecutar el sweep autorizado con presupuesto global; (iv) recién entonces invertir en scavenging predictivo/two-zone/reed dinámico y en validación experimental. |

**Riesgo principal a comunicar al dueño**: los receipts y el estado administrativo ya no describen con exactitud la evidencia (README P2_PASS desactualizado, `continuation_status` obsoleto, revisión externa no reproducible localmente). Antes de cualquier campaña nueva, conviene corregir esa deuda de provenance: es barata y evita decisiones sobre una imagen falsa del estado.

---

## I. Actualización 2026-10-26 — delta post-auditoría

| Campo | 2026-10-19 (corte original) | 2026-10-26 (este delta) |
|---|---|---|
| HEAD inspeccionado | `ea2ff2d` | `d048ab4` (EXE `fc275421`) |
| `current_objective` | `DINO_POWER_CURVE_V1` | `DINO_COMMERCIAL_READINESS_V1`, gate `PASS` 4/4 (objetivo `OPEN`; sin `next_objective` owner-approved) |
| Gate del objetivo | `REVIEW`, 5/5 tasks | `PASS`, 4/4, `DINO_COMMERCIAL_READINESS_V1_FUNCTIONAL_TRIAL_PASS`, sin `remaining` |
| Estado científico | infraestructura de curva; sin validación | `FUNCTIONAL_TRIAL_ONLY; SYNTHETIC_ASSUMPTIONS_DISCLOSED; EXPERIMENTAL_VALIDATION_NOT_PERFORMED; X30_FROZEN` |

La foto A.1 queda como histórica. El estado vigente no es una curva de potencia comercial: es un **trial funcional de producto cerrado con PASS 4/4** sobre el solver integrado, con supuestos sintéticos declarados y sin validación experimental.

### I.1 Evidencia nueva que cambia el diagnóstico

1. **El solver no diverge; la robustez numérica es verificable.** Los seis puntos A/B a 8000/9000/10000 RPM alcanzaron `PERIOD_1` con tres comparaciones globales consecutivas, 0 rechazos CFL, residuos relativos máximos < 8,85e-15 (masa), 9,94e-15 (energía) y 1,49e-14 (especies), y checkpoints que restauran exactamente. Esto **no** demuestra independencia de malla ni validación experimental (`results/periodic-rpm-curves-v1/report.md`).

2. **La baja potencia se explica dentro del modelo por llenado y dilución, no por un error obvio de integración.** En el punto periódico A@9000: 29,69 mg de aire atrapado, AFR atrapado 7,62, 53,4% de residual quemado, 2,017 mg de combustible quemado, 34,193 J indicados, 10,593 J de FMEP y 22,401 J al eje = **4,506 HP**. El informe separa niveles y no suma pérdidas dos veces. En STANDARD_V1 (otra configuración, 9000 RPM, ciclos 30→50): 25,682 mg, AFR 8,47, 1,745 mg quemados, 29,048 J indicados y 2,589 kW de freno; `MAX_CYCLES_NONCONVERGED`; 20 ciclos extra no recuperaron el llenado (`results/physical-accuracy-v1/report.md`; `results/integrated-solver-verification-v1/standard-v1-controlled-continuation-report.md`).

3. **El costo computacional ya no es el bloqueo histórico, pero la cifra no es universal.** En la verificación empaquetada, 3 ciclos a 9000 RPM: 13,491 s en el EXE final vs 13,382 s en la fuente, con estado y diagnósticos exactos (`results/windows-integrated-delivery-v1/receipt.json`; `program-status.json`, progreso WID1). El punto de 3000 RPM que no completó 4 ciclos en 600 s sigue siendo evidencia histórica de otra ruta/configuración; no se generaliza. La mejora provino de la validación térmica stage-local, no de un cambio de física.

4. **El trial Windows cerró con PASS funcional 4/4.** El EXE empaquetado creó y guardó un diseño, duplicó la variante y editó el escape de 83 a 103 mm; ejecutó dos puntos breves a 3000 RPM (9,620 s y 9,838 s), ambos `MAX_CYCLES_NONCONVERGED`/`INSUFFICIENT_CYCLES` y clasificados `TRANSIENT_ESTIMATE`; comparó el par como `EXPLORATORIO` sin filas ficticias; exportó CSV con hashes e identidades; y reabrió el proyecto tras cerrar/relanzar. Los dos bloqueos previos quedaron corregidos: fresh Run ID (`CRV1-RUN-IDENTITY-REPRODUCER`) y scoping del recipe RPM (`fc27542`), verificado en el EXE del commit `fc275421`; 28 regresiones PASS (`results/dino-commercial-readiness-v1/acceptance/report.md`).

5. **X30 sigue congelado y no es una validación disponible.** La curva pública medida ronda 15,1 ± 0,3 kW a 9000 RPM (lectura gráfica), con máximo cercano a 21,3 kW entre 11500–12000; faltan volumen operativo PMS, volumen libre del cárter, geometría funcional de puertos/ductos y montaje de admisión/escape. No se autoriza una simulación X30 ni se rellenan esos faltantes con STANDARD_V1 (`results/x30-preparation-v1/next-point.md`).

6. **La sensibilidad de láminas propuesta no se ejecutó.** El contraste 1000→500 N/m a 9000 RPM, manteniendo área, AFR, transferencias, combustión y válvula, sigue siendo la prueba acotada de mayor valor para separar si las láminas controlan la carga o si el límite se desplaza a transferencias/barrido. Es **sensibilidad**, no tuning ni una promesa de recuperar potencia; requiere protocolo congelado y autorización explícita (`results/integrated-solver-verification-v1/standard-v1-controlled-continuation-report.md`, §6).

### I.2 Veredicto actualizado

| Pregunta | Respuesta al 2026-10-26 |
|---|---|
| ¿Hay curva HP/torque utilizable? | No comercialmente. Hay seis puntos periódicos A/B exploratorios (`PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED`) y un trial funcional aprobado (PASS 4/4); no hay validación experimental ni independencia de malla. |
| ¿El solver está roto? | No hay evidencia de divergencia ni de error de unidades. Es robusto y auditable; sigue sin ser predictivo. La brecha dominante es física (llenado, barrido, cierres) y de datos de referencia. |
| ¿Dónde está el cuello de botella? | Producto: cerrado (gate PASS 4/4). Ciencia: obtener los datos X30 mínimos. Diagnóstico acotado: A/B de rigidez de láminas. |
| ¿Qué no hacer? | No reconstruir HLLC/SSPRK2 por la potencia baja; no calibrar contra 15,1 kW; no presentar 4–5 HP como error de predicción de un motor real; no abrir X30 sin los tres faltantes. |

### I.3 Plan de tres pasos y su estado en la cola

| Paso | Acción | Tarea(s) de cola | Estado |
|---|---|---|---|
| 1 | Cerrar el loop de producto: EXE corregido, dos corridas al mismo RPM, seis referencias periódicas, CSV y save/reopen | `CRV1-SIMULATION-ANALYSIS`, `CRV1-EXPORT-VERIFY`, `CRV1-PROJECT-RECOVERY-VERIFY`, `CRV1-WINDOWS-ACCEPTANCE` (todas DONE) | **Completado**; gate PASS 4/4 |
| 2 | Congelar el A/B de rigidez de láminas 1000→500 N/m a 9000 RPM; ejecutar sólo con autorización | `CRV1-REED-SENSITIVITY-PROTOCOL` (READY, nueva) | Agregada en la cola; la ejecución queda fuera hasta autorización |
| 3 | Reunir el paquete mínimo X30 (volumen PMS, cárter libre, puertos/ductos y montaje) antes de simular | `X30P-*`/`X30R-*` (DONE, congelado) | Ya cubierto; no reabrir sin datos |

**Orden recomendado:** el paso 1 ya cerró el objetivo comercial (PASS 4/4). Siguen, sin bloquearse entre sí, el paso 3 (adquisición de datos X30) y el paso 2 (protocolo de sensibilidad de láminas). Ninguno de los dos autoriza por sí solo una corrida del solver ni un claim predictivo.

**No-claims:** este delta no declara validación experimental, precisión predictiva, paridad con EngMod2T ni una curva comercial. Las cifras de potencia son estimaciones exploratorias bajo supuestos sintéticos.

---

## Limitaciones de esta auditoría

- Read-only: no se ejecutó la suite completa ni se recomputó periodicidad desde los 4 primarios R2 (no es posible: están seleccionados y declaran `NOT_EVALUATED`).
- La "tercera revisión externa" de R2 y la revisión IMPL2 fueron comunicadas por el usuario; no se reprodujeron.
- Detalles internos de EngMod2T más allá de la página oficial provienen del folleto asociado de 2004; no se tratan como especificación vigente.
- No se encontró un proyecto Dino real con datos medidos: `examples/projects/dino-2t-exhaust-comparison.dino2t.json` es "Fixture A — sintético" y `dino-2t-starter.dino2t.json` declara `SYNTHETIC_UNVALIDATED`.
- Este informe es una evaluación de ingeniería; no reemplaza un preregistro, una campaña autorizada ni una revisión independiente.

## Fuentes principales

### Repositorio

- Código: `motorsim/integrated_2t.py`, `mechanical.py`, `engine_physics_v1.py`, `engine_physics_v1_r2_semantics.py`, `engine_results.py`, `performance.py`, `power_curve.py`, `power_curve_sweep.py`, `scavenging.py`, `scavenging_partition_v1.py`, `fuel_combustion.py`, `measurement_data.py`, `external_view.py`, `desktop/`.
- Evidencia: `results/2t-commercial-core-20261002/program-status.json`, `results/full-rpm-sweep-v1/impl2-extension-final-receipt.json`, `results/dino-2t-scientific-point-v1/*`, `results/p2b-gas1d-20260918/*`, `results/2t-v1-closure-20261006/*`.
- Artefactos externos: `E:\Dino-artifacts\engine-physics-v1\full-rpm-sweep-v1-impl2\...\impl2-full-rpm-sweep-30-points.json|csv`; `E:\Dino-artifacts\engine-physics-v1\r2\*` (4 ciclos primarios).
- Contratos/specs: `docs/gasdynamic/1d_contract_v1.json`, `openspec/changes/two-stroke-v1-closure-r2/.../spec.md`, `openspec/changes/dino-power-curve-v1/.../spec.md`.

### EngMod2T (Vannik Developments)

- `https://vannik.co.za/EngMod2T.htm`
- `https://vannik.co.za/EngMod2TDetails.htm`
- `https://vannik.co.za/EngMod2T%20-%20Outputs.htm`
- `https://vannik.co.za/EngMod2T%20-%20OutputsRPM.htm`
- `https://vannik.co.za/EngMod2T%20-%20OutputsDegree.htm`
- `https://vannik.co.za/EngMod2T%20-%20OutputsDisplacement.htm`
- `https://vannik.co.za/EngMod2T-Customer.htm`
- `https://vannik.co.za/NewsAndStatus.htm`
- Folleto asociado EngMod2T (2004, Scribd) — solo para detalles de método marcados como tales.
