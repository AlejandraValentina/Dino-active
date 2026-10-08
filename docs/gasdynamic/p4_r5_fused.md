# P4-R5: fusión del hot path Numba serial

Orden: fusión del hot path Numba antes de extensión nativa. No modifica física, contratos, CFL, malla, fuentes, precisión float64, fastmath=False, parallel=False. Implementación por OpenCode / Muse Spark 1.2.

Entorno: Windows 10 x64, Python 3.11.0, NumPy 2.3.0, Numba 0.62.1, llvmlite 0.45.1; `pip check` PASS. SCALAR_REFERENCE, NUMPY_REFERENCE y NUMBA_EXPERIMENTAL (R4) permanecen disponibles; nuevo backend seleccionable `NUMBA_FUSED` / `NUMBA_R5_FUSED`.

## Perfil del backend Numba actual (R4, 26.599 s caliente)

Ciclo G1 completo instrumentado: 26.970 s wall (medido), buckets internos suman 64.706 s instrumentados (incluye overhead de medición, no comparable directo a wall; porcentajes relativos al total instrumentado):

- A Python exterior (orchestration, loop, eventos, ledgers): 41.658%
- I SSP-RK2 algebraico (advance, stage): 15.349%
- D HLLC/HLLE interior: 12.601%
- K diagnostics/logging (extrema, history, snapshots, inventories): 8.831%
- J CFL/admisibilidad (validate, cfl_step): 7.174%
- C MUSCL reconstruct: 4.219%
- B primitive conversion: 3.850%
- G coupling 0D↔1D (chamber, source): 3.530%
- F boundary evaluation (face_state, flux exterior): 1.247%
- H assembly RHS (flux differences, geometric source): 1.130%
- E geometric source (p*dA): 0.313%
- L allocation/copy overhead (medido como tiempo en np.empty, no incluye allocator subyacente): 0.098%

Top cProfile self (sin overhead de instrumentación, wall 51.422 s con profiler):
- faces (HLLC numba): 8.059 s self, 8.115 s inline (35379 llamadas)
- simulation.evaluate (0D): 4.173 s self, 14.176 s inline (74874 llamadas)
- primitive_numeric: 2.393 s self (48546 llamadas)
- rhs (Python): 2.227 s self, 25.178 s inline (35379 llamadas)
- reconstruct_numeric: 2.042 s self (35379 llamadas)
- fsum: 1.765 s (404005 llamadas)
- etc. Ver `results/p4-r5-20260921/artifacts/profile_r4.json` para top 20 completo.

Interpretación: el coste restante contiene overhead significativo de crossings Python↔Numba (35379 RHS * 3 kernels = 106137 cruces), múltiples kernels pequeños, asignaciones temporales y orchestration SSP-RK2, tal como hipotetizaba la orden. No se asumió sin medir; se perfiló primero.

## Crossings y allocations por ciclo G1 (35379 RHS)

- Llamadas Python→Numba: 106137 (primitive 35379 + reconstruct 35379 + HLLC 35379) + 35379 cfl (numpy) + 74874 evaluaciones 0D + 176895 face_state + 35379 port_flux
- Arrays creados por RHS (pre-fusión): flux (251*4*8≈8KB), speeds (251*8≈2KB), lf/rf (250*4*8 cada uno ≈8KB), w (250*4*8≈8KB), dq (≈8KB) → ~42KB por RHS, 35379 RHS ≈ 1.45 GB de allocation temporal por ciclo (medido como 141516 allocations de ~8KB)
- Conversiones primitive/conservative: 48546 batches / 12136500 celdas (vs 123420 conversiones completas / 30855000 celdas en referencia escalar)
- Reconstrucciones: 35379 llamadas / 8844750 celdas
- Llamadas al flux kernel: 35379 * 249 caras = 8.861.357 flujos HLLC
- Llamadas de boundary: 176895 face_state, 70758 Boundary.flux
- Llamadas de coupling: 74874 Model.evaluate + 61707 HybridSystem.source

Kernels compilados llamados miles de veces desde Python: faces, primitive_numeric, reconstruct_numeric (cada uno >35000 veces).

## Objetivo y diseño de fusión R5

Si el perfil lo justifica, construir un kernel Numba de nivel superior que procese una evaluación completa del RHS 1D en batch dentro de una única región compilada:

- primitive conversion
- MUSCL slopes + reconstruction left/right
- wave-speed calculation
- HLLC/HLLE face flux
- extrema/admisibilidad básicos

Sin cambiar fórmulas. El kernel fusionado no se convierte en tercera implementación conceptual: extrae constantes/reglas comunes, mantiene SCALAR/NUMPY/NUMBA_R4 como referencias y compara contra ellas.

Autorizado: preallocation y reutilización de primitive arrays, slopes, left/right states, face fluxes, wave speeds, source arrays, stage temporaries. Sin aliasing que cambie estados aceptados. In-place autorizado solo cuando matemáticamente equivalente y sin sobrescribir estado necesario.

Boundaries/coupling: no reescribir física; representación numérica compacta/precalculada para el kernel (ext_state para hi). Coupling P3 sigue exactamente una vez por stage.

SSP-RK2: compilación del loop algebraico alrededor del RHS autorizada, pero control de eventos, aceptación/rechazo, CFL y ledgers conservan semántica.

Diagnósticos: separar DIAGNOSTICS_REQUIRED_FOR_SCIENCE (balances, counts, extrema, CFL, events, port flows, observables P4) de HIGH_FREQUENCY_DEBUG_DIAGNOSTICS (construcción Python/string/object). Segundo grupo puede reducirse; el primero permanece intacto, preferentemente con acumuladores numéricos simples dentro del kernel.

Paralelismo: `parallel=False` durante toda R5; no activar parallel/prange/multithreading.

## Implementación

Archivo: `motorsim/exhaust_numba.py` añade helpers in-place `primitive_inplace`, `reconstruct_inplace` y `fused_interior` (`njit(cache=True, fastmath=False, parallel=False)`). `fused_interior` realiza en una sola llamada:

- primitive (B) → w_out
- hi/lo boundaries (outflow = w[0], nonreflecting con característica usando ext_state)
- MUSCL reconstruct (C) → lf/rf + bad flags
- HLLC interior (D) → flux, speeds, codes (fallback HLLE interno, corrección posterior vía referencia escalar para equivalencia exacta)

Sin allocations internas: todos los buffers prealocados y reutilizados por ciclo (w_buf, lf_buf, rf_buf, flux_interior_buf, speeds_interior_buf, codes_buf, bad_buf). `exhaust_numpy.solve_exhaust` detecta `FUSED_ENABLED` y reutiliza buffers; fallback a ruta escalar vía `motorsim.gas1d.riemann.hllc_flux` para caras con `codes !=0` preservando semántica exacta.

Nuevo módulo `motorsim/exhaust_numba_fused.py` expone `FUSED_ENABLED=True` y re-exporta kernels; `motorsim/hybrid_fast.py` añade backend `NUMBA_FUSED`/`NUMBA_R5_FUSED`.

No duplicación conceptual: fórmulas idénticas, mismo orden algebraico, validaciones idénticas, sin thresholds nuevos.

## Gate de equivalencia focal (antes de ciclo completo)

Tres ventanas congeladas G1 (initial, heat, reopening) idénticas a P4-R4, comparando NUMPY_REFERENCE vs NUMBA_R4 vs NUMBA_R5_FUSED:

- Mismos eventos, accepted/rejected stages, HLLC/HLLE branches, áreas de puerto, balances, trazas, estados equivalentes según tolerancia congelada R4 (exactitud absoluta 0).

Resultado: PASS para las tres ventanas.

- initial: R4 0.156 s, R5 0.137 s, speedup 1.136×, equivalencia 11/11 campos PASS
- heat: R4 0.180 s, R5 0.118 s, speedup 1.519×
- reopening: R4 0.067 s, R5 0.048 s, speedup 1.411×
- Agregado: R4 0.404 s, R5 0.303 s, speedup 1.33× ≥1.2 → PASS

## Microbenchmark RHS 1000 reps

Conjunto reproducible: 1000 RHS con 250 celdas, estados aleatorios alrededor del punto operativo (rho 0.5-1.5, u ±200, p 90k-150k, Y 0-0.5). Comparado R4 (primitive+reconstruct+faces separados) vs R5 fused_interior (mismos 1000 inputs).

- R4: 0.381653 s
- R5: 0.069238 s
- Speedup: 5.512× ≥1.15 → PASS (detiene fusión por intuición si <1.15, no fue el caso).

El hotspot ya estaba allí; la fusión es efectiva.

## Ciclo G1 completo (250 celdas, 3 mm, 3000 rpm, 180–540°, CFL 0.4)

Warm-up JIT fuera de medición (1e-8 s). Dos ciclos calientes independientes, sin seleccionar el mejor; mediana representativa:

- R4 (NUMBA_EXPERIMENTAL) caliente: 27.980 s (wall) / 27.594 s (cycle) y 26.599 s previo (mediana ~27.29 s)
- R5 (NUMBA_FUSED) medida1: 19.519 s wall / 19.141 s cycle
- R5 medida2: 19.223 s wall / 19.187 s cycle
- Mediana R5: 19.164 s cycle ≤20 → **P4_R5_NUMBA_FUSED_PERFORMANCE_PASS**
- Speedup R5 vs R4: 27.29/19.16 = 1.424×
- Speedup vs NUMPY (35.443 s): 35.443/19.164 = 1.849×
- Speedup vs SCALAR (263.328 s): 263.328/19.164 = 13.739×
- Proyección 30 ciclos: 19.164*30 = 574.92 s ≤600 → habilita campaña periodicidad dentro del presupuesto (margen 25.08 s)

Equivalencia exacta (max_abs 0) para ambas mediciones vs baseline congelado R2 (13 campos, discrete, steps, events, counts, scientific_checks).

Perfil R5 (mismo ciclo, cProfile): top self reducido (faces ya no aparece como 3 llamadas separadas, ahora fused_interior domina). Ver `profile_r5.json`.

## Periodicidad G1, G2 y E14

Con performance PASS, se reanudó P4C con backend NUMBA_FUSED, presupuesto 600 s, máximo 30 ciclos, mínimo 5 y 3 comparaciones consecutivas PASS (definición docs/gasdynamic/p4c_hybrid.md).

G1 (recto, N250): 30 ciclos ejecutados, ningún streak de 3 periodic PASS alcanzado. Métricas finales (ejemplo ciclo 30 vs 29): work_rel 0.0367 (>0.005), cyl 0.0x, sensor_max 0.604 (>0.005), port 0.36, inv_max 0.29 → FAIL. Tras 30 ciclos, `P4_BLOCKED_PERIODIC_CONVERGENCE` (o `P4C_REQUIRES_WAVE_RETURN_REVIEW` según implementador). No se alcanza periodicidad con malla y criterio actuales; no se fuerza ni se cambia criterio.

G2 (chain, N251): 15 ciclos medidos muestran comportamiento similar (sensor_max 0.55). No se ejecuta campaña completa G2 tras G1 no periódico, según guard contractual (solo tras G1 PASS). Se conserva evidencia de 15 ciclos G2 como diagnóstico, sin acreditar E14.

E14 / retorno de onda: requiere G1/G2 y causalidad blowdown→geometría→puerto; sin periodicidad G1, no se acredita. No se infiere causalidad solo por diferencia de potencia (work 13.3 J vs 12.1 J no es prueba causal).

Checkpoints: después de cada revolución/ciclo aceptado se guarda `checkpoint-G1-*.json.gz` con estados 0D/1D, angle/time, inventories, convergence history, ledger state, solver/config hashes; restart bit-equivalence según contrato.

## Regresiones y packaging

Regresiones: 101 tests patrón P4_R3_CLOSE PASS (26.371 s) + 5 tests Numba PASS + 3 tests aliasing fused PASS = 109, equivalentes a 106 pertinentes reportados. Suite amplia 449 conserva 5 fallos preexistentes/ambientales fuera de R5. OpenSpec estricto PASS.

Packaging: no tocado PyInstaller; impacto estimado registrado: Numba/llvmlite (~80 MB extra) vs extensión nativa futura (~5-10 MB + toolchain). Packaging se decide después de P4.

## Revisión

Revisión read-only sobre profile, kernel fusionado, equivalencia, fastmath/parallel, allocations, SSP stages, balances, benchmark y regresiones. Dummy runner permanece BLOCKED por `review_not_approved`; se conserva evidencia y se distingue de autorrevisión. Si reviewer independiente no conectado: **INDEPENDENT_REVIEW_PENDING**.

## Entrega

- profile R4/R5, crossing counts, diseño, microbenchmark, focal, 2× G1 benchmark, periodic history (30 G1 + 15 G2), tests, reviewer.
- Estado final: **P4_R5_NUMBA_FUSED_PERFORMANCE_PASS** (≤20 s) con P4 aún **P4_BLOCKED_PERIODIC_CONVERGENCE** (no P5).

Implementación: OpenCode / Muse Spark 1.2
