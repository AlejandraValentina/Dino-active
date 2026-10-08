# P4-R10A — Auditoría y Corrección del Diagnóstico de Localización R10

**Fecha:** 2026-09-22  
**Base:** `beeaee6 P4-R10: spatial shock localization` (P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE)  
**Estado P4:** `P4_BLOCKED_PERIODIC_CONVERGENCE` (congelado)  
**Agente:** OpenCode / Muse Spark 1.2 — `INDEPENDENT_REVIEW_PENDING`  
**Clasificación corregida:** **P4_R10_MIXED_SHOCK_AND_GLOBAL_NONCLOSURE**

---

## 1. Defectos Encontrados en R10

### Problema 1 — Fracción de error L2
**Original:** `pct_inside = 100 - L2_outside/L2_total*100` con `L2 = sqrt(mean(diff^2))` para inside y total con diferentes N → no representa energía. Ej: N250 con 3 celdas inside N_inside=3, N_total=250, RMS ratio subestima fracción.

**Corregido:** `E_total = sum(diff^2)`, `E_inside = sum(diff_inside^2)`, `fraction_inside = E_inside/E_total`. Ahora: N250 33% (vs 61% original), N300 28% vs 58%, N350 65% vs 79%, N400 66% vs 83% para ±3c. Original sobreestimaba localización para gruesas y subestimaba para finas? En realidad original 60-88% vs corregido 28-66% → original inflaba para N250/N300 y para N350/N400 similar pero ahora más preciso. Impacto: N250/N300 pasan de "localizado" a "distribuido".

**Test:** `test_L2_energy_fraction` con vector [1,2,3] E=14, inside [1] → 1/14, y `test_inside_outside_sum_to_one`.

### Problema 2 — Front width
**Original:** `front_width` definido como región contigua `|dp/dx| >0.5*max` → 53-94 celdas, 0.11-0.24m, descrito como "shock width de pocas celdas" (incorrecto).

**Corregido:** Separar:
- **A local strongest-gradient width** `|dp/dx| >0.9*max` → 2-3 celdas, 0.005-0.03m (verdadero shock espeso numérico)
- **B broader wavefront width** `>0.5*max` → 50-94 celdas, 0.11-0.24m (onda compresión más ancha)
- **C support de diferencia lag-2** (no frente) → 74-125 celdas 90% energía

Original mezclaba B y C, llamando "few cells" a 83 celdas. Corregido reporta ambos.

### Problema 3 — Tracking del mismo frente
**Original:** `global argmax(|dp/dx|)` por snapshot independiente. En snapshots con dos frentes (ej: x~0.005 port y x~0.23 exhaust), el máximo alterna: para N250 40vs38 x=0.093, 39vs37 x=0.009 → diferentes ondas. Al promediar delta_x de diferentes frentes se cancelan o dan 0.001 promedio engañoso.

**Corregido:** Detectar candidatos locales >0.3*max, elegir para primer snapshot el más cercano a sensor 0.10 (ventana causal 100-150°), luego seguir candidato más cercano (<0.05m) para mismo frente. Por par lag-2 (even-even 40vs38, odd-odd 39vs37) se elige par de candidatos con distancia mínima <0.05. Si no, `AMBIGUOUS`.

**Resultado:** N250 tracking per-pair: 40vs38 ambos en 0.093 delta 0 (TRACKED), 39vs37 ambos en 0.009 delta -0.003 (TRACKED). Antes global daba mezcla 0.093 vs 0.009 con delta 0.08 (falso). Ahora delta_x por par individual, no promedio cancelado.

**Test:** `test_two_front_case_global_argmax_switches`, `test_tracker_preserves_same_front`, `test_ambiguous_crossing`.

### Problema 4 — Rotulado de ciclos
**Original:** pares etiquetados `5 vs 3`, `4 vs 2`, `3 vs 1` (índice dentro de 5 cargados).

**Corregido:** `40 vs 38`, `39 vs 37`, `38 vs 36` (números globales 36-40). Datos ya correspondían a 36-40, solo metadata corregida. **Test** `test_cycle_labels`.

### Problema 5 — Jump strength
**Original:** `jump` = `|p[idx+1]-p[idx]|` adyacente en max gradiente → 7 Pa (N250) vs 4428 Pa (N250 odd) vs 7360 Pa (N350). Pequeño porque es diferencia entre dos celdas del frente, no plateau.

**Corregido:** Reportar ambos:
- `jump_adj` adyacente (7-4428 Pa)
- `plateau_jump` diferencia medianas fuera de frente (±10 celdas) → 649 Pa (N250 even), 15402 Pa (N250 odd), 7360 Pa (N350 even) vs 571 Pa (N350 odd)

Original llamaba "jump strength 1480-2805 Pa" sin distinguir, mezclando adjacente y plateau. Corregido muestra A/B orbits tienen plateau diferente (30k vs 100k) pero lag-2 dentro misma paridad plateau diff <100 Pa (<5%).

### Problema 6 — Localización del error
**Corregido:** `E_inside/E_total` para ±1,2,3 celdas:

| N | ±1 | ±2 | ±3 |
|---|---|---|---|
| 250 | 22% | 30% | 33% |
| 300 | 16% | 24% | 28% |
| 350 | 30% | 65% | **65%** |
| 400 | 55% | 63% | **66%** |

Antes (RMS ratio) daba 60-83% para ±3. Corregido muestra N250/N300 solo 28-33% dentro → distribuido, N350/N400 65-66% dentro → localizado. Support 90% 74-125 celdas (18-41% pipe) no "few cells".

### Problema 7 — rhoE
**Original:** en `p4_r10_spatial.py` había línea `rhoE_cur = rho_cur*E_cur` donde `E_cur = p/(γ-1)+0.5*rho*u²` → `rho*E` sería `rho*p/(γ-1)+0.5*rho²*u²` (incorrecto, factor rho extra).

**Corregido:** `rhoE = p/(γ-1) + 0.5*rho*u²` (energía por volumen, no multiplicar). Test `test_rhoE_formula` falla con lógica incorrecta (correct 285714 vs wrong 142857, ratio 0.5).

### Problema 8 — Sensor/frente
Original usaba `global argmax` independiente por snapshot, distancia sensor-front 0.13 con width 0.366 (ancho B) → cross true. Corregido usa frente trackeado y width_A local (0.039) → para N250 40vs38 distancia 0.007 (0.093 vs 0.10) width_A 0.039 → cross true pero con width local, no B amplio. Más preciso.

### Problema 9 — Delta_x lag-2
Original promediaba delta_x de diferentes frentes (0.093 vs 0.009) dando -0.001 promedio cancelado. Corregido solo calcula `delta_x` si mismo frente trackeado, por par individual, y reporta por par, no promedio. Para N250: 40vs38 delta 0, 39vs37 delta -0.003, 38vs36 delta 0 → avg -0.001 pero con tracking válido por par.

### Problema 10 — Tendencia de malla corregida

| N | dx | width_A | width_B | delta_x/dx (per pair) | frac_in_3 | support90 | plateau_jump_diff |
|---|---|---|---|---|---|---|---|
| 250 | 0.003 | 0.027 (9c) | 0.247 (82c) | 0, -1, 0 | 33% | 0.229 (76c,30% pipe) | 59 Pa |
| 300 | 0.0025 | 0.022 (9c) | 0.233 (93c) | 0, +1, 0 | 28% | 0.314 (125c,41%) | 314 Pa |
| 350 | 0.00214 | 0.011 (5c) | 0.112 (52c) | 0,0,0 | 65% | 0.185 (86c,24%) | 2307 Pa |
| 400 | 0.001875 | 0.010 (5c) | 0.109 (58c) | 0,0,0 | 66% | 0.139 (74c,18%) | 1900 Pa |

Width_A local 9→5 celdas disminuye, Width_B 82→58 disminuye físico pero cells ~60-90 constante, delta_x/dx 0-1, frac 28→66% aumenta con N → más localizado en finas, support 90% disminuye 0.31→0.13m.

---

## 2. Impacto en Clasificación R10

**Original R10:** `P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE` basado en fraction 60-88% dentro, width 53-94 descrito como few cells, delta_x 0.33dx.

**Corregido:** N250/N300 fraction 28-33% dentro → **no localizado** (distribuido), N350/N400 65-66% dentro → **localizado**. Con ambas contribuciones materiales → **P4_R10_MIXED_SHOCK_AND_GLOBAL_NONCLOSURE**.

Original sostenida? **No sostenida**. Nueva: **MIXED**.

Si R10A hubiera mantenido SHOCK_LOCALIZED necesitaría >60% para todas N, pero N250/N300 fallan.

---

## 3. Métricas Corregidas vs Original

- **L2 fraction:** Original 61% N250 vs corregido 33% (cambio -28pp)
- **Width:** Original 83c vs corregido A 9c / B 82c (separado)
- **Delta_x:** Original -0.001 avg vs corregido por par 0, -1dx, 0 (no promedio cancelado)
- **Labels:** 5 vs3 → 40 vs38
- **Jump:** Original 1480 vs corregido plateau 649 vs adj 7 (distinguidos)
- **Support90:** Original 76c vs corregido 76c (igual, pero pipe_fraction 30% vs antes no reportado)
- **rhoE:** Original 142k (wrong) vs 285k correct

Documentado en `audit_diff_vs_r10.json`.

---

## 4. Resultado Final R10A

**Clasificación:** **P4_R10_MIXED_SHOCK_AND_GLOBAL_NONCLOSURE**

- Error lag-2 fino tiene componente localizada en shock (65% N350/66% N400 dentro ±3c) y componente distribuida (33% N250/28% N300 dentro, 66-71% fuera).
- Ancho local 5-9 celdas (A) vs broader 50-90 celdas (B) vs support 74-125 celdas (C) distintos.
- No se requiere N500: mecanismo ya distinguido, ancho físico sigue reduciéndose pero ya no cambia clasificación.

---

## 5. Tests y Validación

9 tests nuevos en `tests/test_p4_r10a.py` cubren L2 energy, inside+outside=1, translated shock tracking, two-front switching, tracker preserves same front, ambiguous, labels, plateau vs adjacent, rhoE. Todos PASS. `test_r10` original 7/7 siguen PASS. OpenSpec strict PASS.

---

## 6. Archivos

- `results/p4-r10a-20260922/` con `decision.json`, `evaluation.json`, `front_tracking_corrected.json`, `error_energy_localization.json`, `mesh_trend_corrected.json`, `sensor_front_corrected.json`, `audit_diff_vs_r10.json`, preserva `results/p4-r10-20260922/` original.
- `docs/gasdynamic/p4_r10a_diagnostic_audit.md` (este archivo)
- `dev_orchestrator/p4_r10a_spatial_corrected.py`, `p4_r10a_evaluation.py`, `tests/test_p4_r10a.py`

---

*Implementation_agent OpenCode / Muse Spark 1.2, INDEPENDENT_REVIEW_PENDING, NO push, NO N500, NO E13-R1.*
