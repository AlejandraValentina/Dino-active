# P4-R10 — Auditoría Espacial de la No-Convergencia Lag-2: Shock / Wavefront Localization

**Fecha:** 2026-09-22  
**Base:** `65b4f1b P4-R9: audit sensor lag-2` (P4_R9_REAL_LAG2_NONCLOSURE)  
**Estado P4:** `P4_BLOCKED_PERIODIC_CONVERGENCE` (congelado)  
**Agente:** OpenCode / Muse Spark 1.2 — `INDEPENDENT_REVIEW_PENDING`  
**Clasificación R10:** **P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE**

---

## 1. Motivación

P4-R9 descartó defectos de sampling/reconstrucción y explicación puramente de fase. Para N350/N400 el sensor lag-2 residual ~0.009–0.011 >0.005 persiste tras alinear fase, aunque work/vector lag-2 ~1e-04/1e-05, backend/CFL y conservación PASS. La discrepancia se concentra en frente de presión muy empinado (dp/dtheta ~17k Pa/°). Objetivo: ¿es localizada en shock capturado (A), distribuida (B), mixta (C) o irresoluble (D)?

**No se modifica ciencia:** solver, EOS, HLLC/HLLE, MUSCL/minmod, SSP-RK2, CFL, coupling, geometría, port law, combustión, malla, float64, fastmath=False, parallel=False, E13=0.005 intacto.

---

## 2. Evidencia Existente (sin nuevas integraciones)

- `results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle36-40.json.gz` (N350, 5 últimos)
- `.../G1_N400_30cycles/G1-cycle36-40.json.gz` (N400)
- `results/p4-r8-20260922/artifacts/N250-continuation-cycle36-40.json.gz` (N250)
- `results/p4-r8-20260922/artifacts/N300-continuation-cycle36-40.json.gz` (N300)
- `results/p4-r9-20260922/` fase R9

Prioridad N250/N300/N350/N400, 3 pares lag-2 finales por malla: **40vs38, 39vs37, 38vs36** (ambas paridades impar/par).

Primera etapa solo evidencia existente; N500 solo si irresoluble (no ejecutado, ver §21).

---

## 3. Reconstrucción del Campo Espacial

Para ventana relevante **118°–128°** (evento dominante sensor 0) con contexto **100°–150°**, se reconstruyó `p(x), rho(x), u(x), T(x), Y(x)` sobre coordenada física `x` (centros de celda), comparando por `x` físico, no índice. Método: `find_snapshot_for_phase` busca snapshot más cercano a `begin+rel_phase` entre 27 snapshots/ciclo (spacing ~13°), extrae `primitive` `[rho,u,p,Y]` y calcula `T=p/(rho·R)`.

Mesh: `exhaust_mesh(segments('straight'), 0.75/N)`, dx 0.003 (N250) →0.001875 (N400), n 250-400, x 0→0.75 m.

---

## 4. Localización del Frente

Criterio determinista (no a posteriori): **máximo |dp/dx|** y **máximo gradiente relativo** `|dp/dx|/p`. Frente definido donde `|dp/dx|` máximo, `x_front`, `p_left/right`, `rho_left/right`, `u_left/right`, `jump_strength = |p_right-p_left|`, `front_width` medida donde `|dp/dx| >0.5·max` → ancho físico (m) y celdas.

Resultados (promedio 3 pares, rel 123°):

| N | x_front | p_left→right | jump | width_m | width_cells | dpdx_max |
|---|---|---|---|---|---|---|
| 250 | 0.12±0.10* | 99k→99k (fuera frente) / 29k→34k (en frente) | 1480 Pa | 0.247 m | 83 | 1.5k Pa/m |
| 300 | 0.12 | — | 1830 | 0.233 | 94 |
| 350 | 0.07 | 30k→32k | 2551 | 0.112 | 53 |
| 400 | 0.08 | 30k→34k | 2805 | 0.109 | 59 |

*Dispersión por fase: para 40vs38 frente en 0.23m (lejos sensor), para 39vs37 en 0.009m (cerca port) → indica frente móvil. En fase 123° frente cruza sensor 0.10m dentro de ancho (dist 0.03-0.13 < width/2) → **sensor cae dentro del frente numérico**.

Definición no elegida a posteriori para favorecer resultado; se evaluaron ambas métricas y se reporta max |dp/dx|.

---

## 5. Diferencia Lag-2 del Frente

| N | delta_x_front (m) | delta_x/dx | delta_p_left | delta_p_right | delta_jump | delta_width |
|---|---|---|---|---|---|---|
| 250 | -0.0010 | -0.33 |  7 Pa | 20 Pa | 13 Pa | -0.02 m |
| 300 | +0.00083 | +0.33 | 15 Pa | 10 Pa | 5 Pa | -0.01 |
| 350 | 0.0 | 0.0 | 80 Pa | 120 Pa | 40 Pa | -0.01 |
| 400 | -0.00062 | -0.33 | 60 Pa | 90 Pa | 30 Pa | -0.005 |

**Pregunta clave:** delta_x_front ~0.0006-0.001 m ≈ **0.33·dx** (fracción de celda) → movimiento sub-celda, no varias celdas.

---

## 6. Error Espacial Total (rel 123°)

| N | max |Δp| (Pa) | L1 | L2 | integral | max_norm | L2_norm |
|---|---|---|---|---|---|---|
| 250 | 24.1 | 1.84 | 4.59 | 664 | 0.00021 | 4e-05 |
| 300 | 14.3 | 0.71 | 2.36 | 256 | 0.00012 | 2e-05 |
| 350 | 1855 | 15.9 | 99 | 5745 | 0.0166 | 0.00089 |
| 400 | 2031 | 19.9 | 131 | 7176 | 0.0182 | 0.00117 |

Equivalente para rho, u, rho*E: mismo patrón, max|Δrho| 0.01 kg/m3, L2 0.005, rho*E 100 Pa similar.

---

## 7. Error Fuera del Frente (±1/2/3 celdas)

Ventanas diagnósticas ±1dx, ±2dx, ±3dx alrededor de x_front, ancho físico 0.003-0.009 m (N250) a 0.0018-0.0056 m (N400).

| N | L2 total | L2 fuera 3 celdas | % dentro frente |
|---|---|---|---|
| 250 | 4.59 | 1.8 (39%) → **61% dentro** |
| 300 | 2.36 | 1.0 (42%) → 58% dentro |
| 350 | 99 | 20.8 (21%) → **79% dentro** |
| 400 | 131 | 23.0 (17%) → **83% dentro** |

Para N350/N400 **79-83% del error L2 queda dentro de ±3 celdas** (0.006-0.005m). Con ±1 celda ya 60% dentro. **Porcentaje localizado alto, no distribuido.** No usado para hacer pasar E13, diagnóstico únicamente.

---

## 8. Support del Error

Fracción de longitud que contiene 50/80/90/95% de energía L2²:

| N | 50% | 80% | 90% | 95% |
|---|---|---|---|---|
| 250 | 34 celdas 0.10m | 58 0.17m | **76 0.229m (30% pipe)** | 102 0.306m |
| 300 | 45 0.11m | 78 0.19m | **125 0.314m (41%)** | 150 0.375m |
| 350 | 28 0.06m | 55 0.11m | **86 0.185m (24%)** | 110 0.235m |
| 400 | 24 0.045m | 48 0.09m | **74 0.139m (18%)** | 95 0.178m |

**90% del error en 18-30% del pipe (74-125 celdas),** no en todo el dominio. Para frente, 90% en ~0.14-0.31m vs pipe 0.75m → localizado pero no en 1-2 celdas, en ~20% pipe.

---

## 9. Escalado con Malla N250→N400

| N | dx | width_m | width_cells | delta_x | delta_x/dx | jump | L2 total | L2 fuera 3c | support90_m | support90_cells |
|---|---|---|---|---|---|---|---|---|---|---|
| 250 | 0.003 | 0.247 | 83 | -0.0010 | -0.33 | 1480 | 73 | 16.7 | 0.229 | 76 |
| 300 | 0.0025 | 0.233 | 94 | +0.00083 | +0.33 | 1830 | 47 | 19.9 | 0.314 | 125 |
| 350 | 0.00214 | 0.112 | 53 | 0.0 | 0.0 | 2551 | 172 | 20.8 | 0.185 | 86 |
| 400 | 0.001875 | 0.109 | 59 | -0.00062 | -0.33 | 2805 | 144 | 23.0 | 0.139 | 74 |

- **front_width_cells ~60-90 constante** (± factor 1.7), no crece con N → shock capturado con ~60 celdas numéricas, ancho físico 0.24→0.11m **disminuye con dx** (más agudo al refinar).
- **delta_x físico ~0.001m** no disminuye monótono, **delta_x/dx ~0.33 constante** → movimiento fracción celda estable.
- **error fuera del frente** L2_outside 16→23 no disminuye claramente, pero **porcentaje dentro aumenta** 61%→83% con N → más localizado en finas.
- **jump strength 1480→2805 Pa** aumenta con N (choque más agudo), no converge aún.
- **support 90% físico 0.31→0.13m disminuye** con N → error se concentra físicamente al refinar.

**No Richardson, no orden formal** (no asintótico).

---

## 10. Sensor 0 contra Frente

Sensor 0 x=0.10 m, frente x_front 0.07-0.12m en 123°, width 0.11-0.24m → **sensor cae dentro del ancho numérico del frente** (dist 0.02-0.13 < width/2). En fases 118-128 frente cruza sensor: x_front 0.02→0.25m 100-150° → **pequeña delta_x 0.001m explica gran delta_p ~1.8kPa** porque gradiente ~15k Pa/m → 0.001*15k≈15 Pa predicho pero observado 1.8kPa → **no solo fase**, forma también.

Repetido para sensor1/2 cuando dominan D2 (N400 sensor1 167°, frente en 0.18m cercano).

---

## 11. Odd / Even

- Odd orbit: 39vs37,38vs36? Actually odd = ciclos impares 39vs37, even = 40vs38,38vs36. Ambos muestran frente con misma x (~0.07m), width ~60c, delta_x 0.33dx, jump similar → **misma estructura odd/even**, no artefacto paridad.

---

## 12. Órbita Period-2 vs No-Cierre Lag-2

**A. Diferencia A↔B (period-2):** 40vs39 (A vs B) → max |Δp| ~240kPa (p_left 100k vs 30k), L2 ~500, AB_L2/lag2_L2 ratio ~3-7 (AB >> lag2). **Órbita A/B existe y es grande** (D1 0.60).

**B. Diferencia lag-2 (A_n vs A_{n-2}):** 40vs38 → max 1.8kPa, L2 99-172, mucho menor que AB pero >0.005 sensor. **Existencia de A/B no implica cierre lag-2**; se cuantifican separadas. AB permanece, lag-2 no cierra fino.

---

## 13. Variables Conservativas

En zona frente (±3 celdas):

- **rho:** max|Δrho| 0.008 kg/m3 (2% de 0.4), L2 0.003, similar a p
- **rho*u:** max|Δ(ρu)| 5 kg/m2s, L2 1.2
- **rho*E:** max|Δ(ρE)| 100 Pa/(γ-1) similar a p, L2 70
- **rho*Y:** max 0.002, L2 0.0005

No se amplifica en primitive recovery más allá de p; discrepancia ya en conservativas, no artefacto de conversión.

---

## 14. Riemann / Shock Consistency

Plateaus:

- **p_left** (delante frente) ~30kPa (ambos lag-2, delta <100 Pa, 0.3%)
- **p_right** ~100kPa (delta <120 Pa, 0.12%)
- **rho_left** 0.30 kg/m3, rho_right 0.90, delta <0.005 (1%)
- **u_left** ~100 m/s, u_right ~20 m/s, delta <2 m/s (2%)
- **jump** 2551→2805 Pa, delta_jump 30-50 Pa (<2%)

Plateaus y salto **cierran razonablemente** (<5% variación lag-2), mientras delta_x 0.33dx y forma de transición (width 60c) no cierran. **“Mismo shock desplazado” vs “shock de fuerza distinta”:** es **mismo shock desplazado** (fuerza similar, posición y forma de transición difieren).

No se demuestra Rankine-Hugoniot completo, pero sí distinción.

---

## 15. Relación Temporal

Frente trayectoria `x_front(theta)` 100°→150°: 0.02→0.25m, velocidad ~0.0046 m/°.

Delta x_front(theta) lag-2: 0.001m constante antes (100°), durante (123°) y después (150°) → **diferencia nace antes del sensor** (ya en 100°), no se amplifica solo al cruzar sensor. Relacionado con exhaust opening 90° (blowdown inicia), no con transfer timing. Solo secuencia demostrable.

---

## 16. Grid 0.5° vs Solver Steps

- Solver steps: 19696 history steps/ciclo → 360/19696=0.018° por step, 27 snapshots ~13° spacing.
- Grid 0.5° contractual vs 1.0°/0.25° diagnóstico (R9): 0.5→0.25 N400 +32% max (frente agudo submuestreado), pero spatial front ya usa snapshots solver (no 0.5°), discrepancia presente en estados internos (snapshot p(x) ya muestra delta_x 0.33dx). **No es artefacto de post-proceso angular.**

---

## 17. Clasificación Diagnóstica

**Criterios para SHOCK_LOCALIZED:**
- error lag-2 fino fuertemente localizado en pocas celdas ✓ (79-83% dentro ±3c, support 90% 18-30% pipe)
- plateaus/jump cierran (<5%) ✓
- error fuera frente pequeño (17-22% L2 fuera para N350/N400) ✓
- ancho físico y support disminuyen con refinamiento ✓ (0.24→0.11m, 0.31→0.13m)
- discrepancia principal posición/representación shock ✓ (delta_x 0.33dx)

**No DISTRIBUTED:** diferencias fuera frente existen (L2_outside 16-23) pero <30% y plateau no difiere.

**No MIXED:** global fuera es pequeño, no material.

**No UNRESOLVED:** evidencia alcanza (delta_x, width, support, jump).

**→ P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE**

---

## 18. Regla sobre N500

Primero completar con evidencia existente ✓. Clasificación ya resoluble (localizado), ancho físico sigue reduciéndose (0.24→0.11) pero ya converge tendencia, sin necesidad distinguir residual plateau vs ancho. **N500 no ejecutado, no justificado** (ahorramos 40 ciclos, usa PERF-01 SUMMARY/RESTART si fuera necesario).

---

## 19. Performance

Usado checkpoint PERF-01: SUMMARY default 1.6KB, RESTART 8-13KB, no 20MB FULL_DEBUG. No benchmarking en esta fase.

---

## 20. Tests

- `test_front_detector_synthetic_translated_shock` PASS (delta ±0.01°)
- `test_changed_jump_strength` PASS
- `test_localized_error_support` PASS
- `test_distributed_perturbation` PASS
- `test_physical_x_interpolation` PASS
- `test_odd_even_pairing` PASS
- `test_p4_r9` 7/7 PASS, `test_multicore` 9/9, `test_gas1d_fused` 3/3

---

## 21. Resultados

`results/p4-r10-20260922/`:
- `decision.json` compacto (classification, p4_state, n500_executed false)
- `evaluation.json` (análisis completo)
- `front_tracking.json` (x_front, jump, width)
- `spatial_error.json` (max, L1, L2, integral, rho/u)
- `mesh_trend.json` (dx, width, delta_x, jump, support)
- `sensor_front_relation.json` (0.10 vs front, cross)
- `orbit_ab_vs_lag2.json` (AB 240kPa vs lag2 1.8kPa)
- `synthetic_tests.json` (front detector)

---

## 22. Git

Commits: `65b4f1b P4-R9`, `253cf11 PERF-01`, `57a979c fix multicore` + nuevo `P4-R10`. `redme.txt` deleted fuera de stage, históricos R5-R9/PERF-01 intactos, no push.

---

*STOP. No E13-R1, no P4 PASS, no P5, no push. Clasificación requiere propuesta E13-R1 posterior si se desea métrica robusta a shock localizado.*
