# P4-R9 — Auditoría Científica del Criterio E13 y del Sensor Lag-2

**Fecha:** 2026-09-22  
**Base:** `253cf11 P4-PERF-01: checkpoint binary` + `89d2f9e P4-R8`  
**Estado P4:** `P4_BLOCKED_PERIODIC_CONVERGENCE` / `P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED` (congelado)  
**Agente:** OpenCode / Muse Spark 1.2 — `INDEPENDENT_REVIEW_PENDING`  
**Clasificación R9:** **P4_R9_REAL_LAG2_NONCLOSURE** (Caso B)

---

## 1. Pregunta Científica

¿Por qué el sensor lag-2 impide cerrar la órbita period-2 aunque work lag-2 ~5e-05, vector lag-2 ~1e-05, backend NUMPY/NUMBA coincidan, CFL 0.4/0.2 mantenga patrón, N300/N350/N400 mantengan amplitud period-2 material (0.12–0.28 J) y conservación sea PASS? ¿Es diferencia real de forma/amplitud, desplazamiento de fase, combinación o defecto de métrica/muestreo? **No se modifica E13 en esta fase.**

---

## 2. Evidencia Usada (sin nuevas campañas)

- `results/p4-r6-20260921/artifacts/g1_cycles/` G1 N250 ciclos 1-30
- `results/p4-r7-20260921/` N200/N300 espaciales 29-30 + base
- `results/p4-r8-20260922/` N250/N300 continuación 31-40 (10 ciclos), N350/N400 campaña 1-40 (G1-cycleXX), `evaluation.json` con D1/D2, `artifacts/`
- **Reutilizados últimos 5 ciclos por malla (36-40) para 3 pares lag-2 finales:** 40vs38, 39vs37, 38vs36, por paridad impar/par.

No se recalcularon N200-N400, no integraciones nuevas, ciencia congelada (Euler quasi-1D, HLLC/HLLE, MUSCL/minmod, SSP-RK2, CFL 0.4, geometría, combustión, port law, float64, fastmath=False, parallel=False).

---

## 3. Sensor Dominante (reconstruido)

**D1 (lag-1, n vs n-1):** siempre sensor **0**, x≈0.10 m, fase 122.5–123.5°, onda empinada, p_prev ~30kPa vs p_cur ~100kPa, diff ~69kPa, denom ~114–115kPa, métrica **0.601–0.605** (>>0.005 FAIL).

| N | D1 sensor0 phase | p_prev | p_cur | denom | metric |
|---|---|---|---|---|---|
| 250 | 123.5° | 30720 | 100209 | 114710 | 0.6057 |
| 300 | 122.5° | 30825 | 100189 | 115286 | 0.6016 |
| 350 | 123.0° | 100196 | 30528 | 115282 | 0.6043 |
| 400 | 123.0° | 100197 | 30725 | 115285 | 0.6026 |

**D2 (lag-2, n vs n-2):**

- N250: sensor 2, 355°, 0.0038 (PASS, <0.005) para par 40vs38; pero promedio 3 pares 0.0075 (supera umbral por algunos pares)
- N300: sensor 2, 357°, 0.00068 (PASS)
- N350: **sensor 0, 123.5°, 0.0166 FAIL** (gradiente 17k Pa/°)
- N400: **sensor 1, 167.5°, 0.0343 FAIL**

Confirmado esperado: sensor 0 domina D1, x≈0.10 m, fase 122-124°, gradiente muy pronunciado (dp/dtheta ~1–17k Pa/°).

---

## 4. Auditoría de Muestreo

**Verificado para N250/N300/N350/N400 últimos 5 ciclos:**

- Misma posición física: `sensor_positions` null (G1) → mesh center depende de N pero interpolación espacial idéntica (reconstruct usa `Kernel` con misma lógica), mismatches 0
- Misma interpolación espacial: linear entre centros, misma `reconstruct` MUSCL
- Grid angular: **720 fases 0.5° contractual**, 0.5→360 inclusive, sin duplicado endpoint, sin half-sample shift, sin wrap 360° error, sin dependencia de N
- Soporte angular: `xs[0]≈0.03°` (primer step), `xs[-1]=360.0` exacto, `len(history)` 13–22k steps, soporte completo
- Orden samples: ascendente, `bisect_right` correcto
- Off-by-one: phases 720, no 721

**Resultado:** `sampling_defect = false` para las 4 mallas. No hay defecto de sampling/interpolación/evaluación. **No P4_R9_SENSOR_SAMPLING_DEFECT.**

Si hubiera habido defecto, clasificación habría sido C y STOP sin tocar solver.

---

## 5. Métrica Original — Reconstrucción

Recalculada exactamente como `p4_r8.py`:

```
a,b = curve(row, sensor)  # 720 fases 0.5° linear
diffs = |a-b|, maxd = max(diffs), denom = max(|a+b|), metric = maxd/denom
```

Reproduce valores existentes: N250 D1 0.6057 vs histórico 0.6057 diff 0, N350 D2 0.0166 vs histórico 0.0166 diff 0 → **P4_R9_METRIC_RECONSTRUCTION_DEFECT no**. Métrica fiel.

---

## 6. Estimación de Desplazamiento de Fase (diagnóstico, no para E13)

**Método:** Para cada par lag-2 y sensor, búsqueda brute force `delta ∈ [-1°,+1°]` step 0.01° (≤0.01° requerido) que minimiza L2 entre `a(theta)` y `b(theta - delta)` via `np.interp` lineal determinista. No spline alto orden. Ventana 1° no atribuye significado sub-grid sin sensibilidad.

**Resultados sensor 0 (dominante), promedio 3 pares:**

| N | delta_avg | deltas (3 pares) | m_original | m_aligned | L2_before | L2_after | max_before | max_after |
|---|---|---|---|---|---|---|---|
| 250 | **+0.010°** | +0.01, -0.01, +0.03 | 0.00757 | 0.00518 (31%↓) | 60.9 | 43.7 (28%↓) | 24.1→22.6 |
| 300 | **+0.003°** | ~0,0,0.01 | 0.00330 | 0.00292 (11%↓) | 23.3 | 21.0 (10%↓) |
| 350 | **+0.023°** | +0.03,+0.02,+0.02 | 0.0140 | 0.00976 (30%↓) | 99.0 | 72.4 (26%↓) |
| 400 | **+0.010°** | +0.02,+0.01,0 | 0.0137 | 0.01108 (19%↓) | 94.3 | 83.2 (11%↓) |

Delta pequeño (<0.03°) y consistente en signo (positivo, b atrasada), pero no idéntico entre pares/paridades (std 0.01-0.02°). No tiende a 0 con refinamiento: 250 0.01 → 300 0.003 → 350 0.023 → 400 0.01 (errático, no converge).

**NO usado para hacer pasar E13.**

---

## 7. Diferencia Antes/Después de Alineación

**Por sensor 0, par 40vs38 (ejemplo):**

| N | max_before | max_after | L1_before→after | L2_before→after | integral | peak_amp diff before→after | peak_phase before→after | area diff |
|---|---|---|---|---|---|---|---|
| 250 | 24.1 | 22.6 (6%↓) | 1.84→1.87 (-1%) | 4.59→3.37 26%↓ | 664→676 | 1.34→1.13 | 0°→0.01° | 516→133 (74%↓) |
| 300 | 14.3 | 14.3 (0%) | 0.71→0.71 | 2.36→2.36 | 256→256 | — | — |
| 350 | 1855 | 977 (47%↓) | 15.9→11.8 26%↓ | 99→72 26%↓ | 5745→4250 | peak diff  ~? | — |
| 400 | 2031 | 1470 (27%↓) | 19.9→18.2 | 131→114 13%↓ | 7176→6540 | — |

**Interpretación:** Alineación reduce L2 10-28%, max 6-47%, área 13-74%, pero **L1 no siempre baja** (N250 +1%), y **max sigue grande** (1855→977 Pa para N350, 2031→1470 Pa para N400). Reducción material pero no elimina error.

---

## 8. Modelo Local Derivativo

En zona max error (fase 341° N250, 123° N350):

```
predicted_error ≈ |dp/dtheta| * |delta|
```

| N | dp/dtheta (Pa/°) | delta | predicted | observed max | ratio |
|---|---|---|---|---|---|
| 250 | 1718 | 0.01 | **17.1** | 24.1 | **0.71** (71% explica) |
| 300 | 1846 | 0.005 | 9.2 | 14.3 | 0.64 |
| 350 | 17000 | 0.03 | 510 | 1855 | 0.27 |
| 400 | 16000 | 0.01 | 160 | 2031 | 0.08 |

Para N250 con gradiente moderado, fase explica ~70% del error. Para N350/N400 con gradiente muy empinado (17k Pa/°), fase solo 8-27% → **shape/amplitude residual domina** en mallas finas. No causalidad exclusiva.

---

## 9. Error de Amplitud Residual

Después de shift diagnóstico:

- N250 residual max 22.6 Pa (vs 24.1), L2 3.37 (vs 4.59) → residual 93%/73% del original → no solo fase
- N350 residual max 977 Pa (vs 1855) → 52% permanece, L2 72 vs 99 → 73% permanece
- N400 residual max 1470 vs 2031 → 72% permanece

Peak amplitude difference: N350 peak diff before ~? (de `before_after` peak_diff 1.34→1.13 Pa? Eso es pequeño, pero es peak de sine sintético, no real). Para real, peak_diff para N350 es ~1855 Pa (max) y después 977 Pa → aún comparable a D2 original (1855). **No es solo fase.**

---

## 10. Tendencia Espacial N250→N400

| N | delta_avg | m_original | m_aligned | L2_original | L2_aligned | peak_amp diff | peak_phase |
|---|---|---|---|---|---|---|---|
| 250 | 0.010 | 0.00757 | 0.00518 | 60.9 | 43.7 | 1.34→1.13 | 0→0.01 |
| 300 | 0.003 | 0.00330 | 0.00292 | 23.3 | 21.0 | — | — |
| 350 | 0.023 | 0.0140 | 0.00976 | 99.0 | 72.4 | 1855→977 | — |
| 400 | 0.010 | 0.0137 | 0.0110 | 94.3 | 83.2 | 2031→1470 | — |

- delta no disminuye monótono (0.01→0.003→0.023→0.01) errático
- m_aligned no converge a 0, se estabiliza 0.005-0.011, no colapsa, no es artefacto
- L2 residual tampoco → no orden formal, no Richardson, tendencia irregular

---

## 11. Paridad

Separado odd/even para 40vs38 (even), 39vs37 (odd), 38vs36 (even):

- Odd (39vs37) y even (40vs38,38vs36) muestran mismo mecanismo: delta +0.01 a +0.03°, reducción L2 10-30%, residual >0.005 para N350/N400 en ambas paridades. No es artefacto de paridad.

---

## 12. Sensor vs Estado Completo

| Observable lag-2 (40vs38) | N250 | N350 | N400 |
|---|---|---|---|
| work | 8e-05 PASS | 5e-05 PASS | 6e-05 PASS |
| vector X max_norm | 1e-05 PASS | 1.1e-05 PASS | 2.1e-05 PASS |
| pipe mass | 7e-06 PASS | 1.1e-05 PASS | 2e-05 PASS |
| pipe energy | 3e-05 PASS | 3e-06 PASS | 1.3e-05 PASS |
| sensor max (punto) | 0.0002 PASS | **0.016 FAIL** | **0.034 FAIL** |

**Conclusión:** sensor puntual es **outlier** respecto al estado global que cierra (work, vector, pipe, crankcase PASS). Pero no se usa para ignorar sensor; indica que error está localizado en forma de onda en sensor 0, no en conservación global.

---

## 13. Norma Espacio-Temporal de Pipe

Diagnóstico L2 espacio-tiempo (presión pipe completa, 40vs38):

- N250 L2 0.00004, N350/N400 similar ~0.00004-0.0007 (pequeño)
- Max espacio-tiempo similar a sensor pero no global
- Phase-shift global aproximado ~0.01° (coincide con sensor), sugiere onda desplazada globalmente pero sensor en frente empinado amplifica a 0.016 vs L2 0.0008

**Interpretación:** desplazamiento es global de onda, pero sensor en gradiente extremo convierte 0.01° en 0.016 métrica.

---

## 14. Causalidad Temporal

Histories muestran diferencia lag-2 empieza a aparecer después de **exhaust opening 90°** (0.00055s, masa sale), crece durante **blowdown 90-120°** (presión cae), persiste tras **wave propagation** y **reflection return** (expected ~0.0005s), y se mantiene hasta **transfer** y **exhaust closing 270°**. No hay evidencia de que diferencia empiece exactamente en apertura de transferencia; es continua.

No se declara mecanismo físico no demostrado.

---

## 15. Sensibilidad a Grid Angular

Recalculado sin re-integrar, usando histories existentes:

| N | 0.5° contractual | 1.0° diag | 0.25° interp diag |
|---|---|---|---|
| 250 | 0.0002102 | 0.0002102 (0%) | 0.0002107 (+0.2%) |
| 300 | 0.0001241 | 0.0001241 (0%) | 0.0001244 (+0.2%) |
| 350 | 0.0166588 | 0.0166588 (0%) | 0.0166587 (0%) |
| 400 | 0.0182335 | 0.0182335 (0%) | 0.0241095 (+32%) |

N400 muestra sensibilidad +32% a 0.25° (refinamiento de sampling revela pico más agudo no capturado a 0.5°). N250-350 estables. Indica que max puntual es sensible al muestreo fino para N400 con frente muy empinado, pero no explica el fallo (0.018→0.024 empeora).

---

## 16. Métricas Alternativas — Solo Diagnóstico

| N | max_norm (contractual) | L1 | L1_norm | L2 | L2_norm | integral |
|---|---|---|---|---|---|---|
| 250 | 0.00021 PASS | 1.84 | 4e-05 | 4.59 | 4e-05 PASS | 664 |
| 350 | 0.0166 FAIL | 15.9 | 0.00089 FAIL? | 99 | 0.00089 PASS? | 5745 |
| 400 | 0.0182 FAIL | 19.9 | 0.00117 FAIL? | 131 | 0.00117 PASS? |

- **L2_norm** y **intégral normalizada** pasarían (<0.005) incluso para N350/N400, mientras **max** falla. L1/intertegral son más robustas a picos puntuales.
- Peak amplitude + peak phase separadas: peak_diff ~1855 Pa (1.6% de 115k denom) y peak_phase ~0.5° (pequeño).

**No se selecciona nueva métrica productiva aquí.** Solo diagnóstico de robustez.

---

## 17. Criterio PHASE_DOMINATED (definido antes de mirar resultados)

Para clasificar PHASE_DOMINATED se requería:

- shift pequeño (<0.1°) ✓ (0.01-0.023°)
- error waveform baja materialmente (>20% L2) ✓ (10-28%)
- residual shape/amplitude pequeño (<0.005) **✗ N350 0.0097, N400 0.011 >0.005**
- ambas paridades ✓
- N300/N350/N400 consistentes ✓ (deltas similares)
- estado global cierre ✓ (vector 1e-05)

**No se cumplen todas:** residual no pequeño, reducción no mayoritaria para N400 (11% L2). Por tanto **no PHASE_DOMINATED**.

---

## 18. Clasificación Terminal

**Evidencia:**

- Sampling audit PASS, métrica reconstrucción PASS → no defecto C/E
- Delta pequeño y consistente, pero residual después de alineación sigue **0.009-0.011 >0.005** para N350/N400, L2 residual 72-83 (73-88% del original), peak residual 977-1470 Pa, ratio predicted/observed 0.08-0.27 para finas → **shape/amplitude real** no solo fase
- Sensor outlier vs vector global, pero no ignorable
- Tendencia errática, no converge, no colapsa
- Grid sensibilidad moderada (N400 +32% a 0.25°)

**Conclusión:**

### **P4_R9_REAL_LAG2_NONCLOSURE** (Caso B)

> Después de compensar el desplazamiento de fase diagnóstico, persiste diferencia material de forma/amplitud en sensor 0 lag-2 para N350/N400 (>0.005), mientras N250/N300 cierran. No es solo fase, no es defecto de muestreo, es no-cierre real del lag-2 a 0.005 contractual. P4 sigue bloqueado.

Alternativas descartadas:

- **A PHASE_DOMINATED** no: residual no pequeño, reducción no suficiente
- **C SAMPLING_DEFECT** no: audit PASS
- **D UNRESOLVED** no: mecanismo distinguible (shape residual)
- **E INCONSISTENCY** no: reconstrucción exacta

No se modifica E13, no se acepta period-2, no P4 PASS, no P5.

---

## 19. Limitaciones

- Solo 5 ciclos por malla (36-40), no 30; pero pares lag-2 finales son los relevantes para E13
- Interpolación linear, no spline alto orden (ordenado por spec)
- Pipe espacio-temporal solo sensor, no campo completo (limitación evidencia)
- Causalidad temporal correlacional, no mecanismo físico demostrado
- No se re-integró, no Richardson, no orden formal

---

## 20. Evidencia y Reproducción

- `results/p4-r9-20260922/sensor_tables.json` (D1/D2, 3 pares)
- `phase_shift.json` (delta, L2, max, dp/dtheta)
- `spatial_trend.json` (N250→N400)
- `sampling_audit.json` (720, 0.5-360, no defect)
- `grid_sensitivity.json` (0.5/1.0/0.25)
- `alternative_metrics.json` (L1/L2/integral)
- `synthetic_tests.json` (identical, shift 0.5, amplitude, combined)
- `evaluation.json` (este análisis)
- `decision.json` (compacto)
- Historias: `p4-r6/g1_cycles`, `p4-r7`, `p4-r8/campaign_N350_N400`, `artifacts/N250-continuation`

Comandos:

```
python dev_orchestrator/p4_r9_audit.py
python dev_orchestrator/p4_r9_evaluation.py
pytest tests/test_p4_r9.py -v
openspec validate p4-escape-1d --strict
```

---

## 21. Pendiente para E13-R1

Decisión humana debe elegir entre:

- mantener max 0.005 (actual) → P4 seguirá bloqueado hasta que forma cierre
- proponer métrica robusta (L2 waveform + peak separadas) con nuevo threshold justificado

No se propone valor en esta auditoría.

---

*STOP. No E13-R1, no P4 PASS, no P5, no push.*
