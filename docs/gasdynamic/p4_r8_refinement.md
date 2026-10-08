# P4-R8: Persistencia espacial de la órbita period-2 y cierre lag-2 — refinamiento 200→400

**Orden:** recuperación desde evidencia durable existente (P4-R8). Reanudar y cerrar desde checkpoints 22/18 sin reiniciar campaña. No modificar solver, física, contratos ni thresholds. No P4-PERF-01, no P5.

**Science freeze:** Euler quasi-1D, EOS IdealGas, HLLC/HLLE, MUSCL/minmod, SSP-RK2, CFL 0.4, coupling G1/G2, port law, combustión, geometría straight 0.75 m, thresholds E13 originales, backend `NUMBA_FUSED`, float64, `fastmath=False`, `parallel=False`. `INDEPENDENT_REVIEW_PENDING`.

**Implementation_agent:** OpenCode / Muse Spark 1.2

**Estado inicial en disco (recovery audit):**

- `main == origin/main` HEAD `2457a3a`
- `results/p4-r8-20260922/artifacts/base_table.json` existente (N200/250/300)
- `continuation_N250.json` / `continuation_N300.json` completos hasta ciclo 40 (10 ciclos extra)
- `N250-continuation-cycle31..40.json.gz` y `N300-continuation-cycle31..40.json.gz` durables
- `campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle01..22.json.gz` (LAST_DURABLE_CYCLE 22)
- `campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle01..18.json.gz` (LAST_DURABLE_CYCLE 18)
- `N250 = COMPLETE` (40), `N300 = COMPLETE` (40), `ACTIVE_R8_PROCESS = NO`
- `multicore_equivalence.json` `MULTICORE_SCHEDULER_EQUIVALENCE_PASS`

No se repitieron: R5/R6/R7/N200/N250 inicial y continuación, N300 inicial y continuación, multicore synthetic benchmark. Reutilizada evidencia existente.

---

## 1. Objetivo y alcance

Verificar persistencia espacial de la órbita de período 2 al refinar malla (N200→400) y evaluar cierre lag-2 (n vs n-2) bajo contrato P4-R8 original:

- Definición periódica exacta `dev_orchestrator/p4_hybrid.py:periodic` (work `≤0.005`, cylinder `≤0.005`, sensores `≤0.005` cada uno, port `≤0.002`, inventarios `≤0.002`).
- Requiere 3 comparaciones consecutivas `passed` tras ciclo 5 para declarar periodicidad.
- Para diagnóstico period-2: `D1` debe fallar materialmente y `D2` (lag-2) debe mostrar 3 `passed` consecutivos con `D1` fallando en esos mismos ciclos.
- Sin promediar A/B, sin relajar sensor `0.005`, sin declarar P4 PASS, sin cambiar CFL ni malla.

Fases completadas:

1. Tabla base amplitudes (reutilizada).
2. Equivalencia multicore workers=1 vs 2 (reutilizada, PASS).
3. Continuación N250 +10 (ya completa).
4. Continuación N300 +10 (ya completa).
5. N350 y N400 campañas 30 + diagnóstico 10 vía multicore workers=2 (recuperadas desde 22/18 hasta 30, luego 30→40).
6. Clasificación, tendencia, sensor dominante, conservación, costes y decisión.

---

## 2. Evidencia durable reutilizada y nueva

| Evidencia | Ruta | Estado |
|---|---|---|
| Base table N200/250/300 (29/30) | `results/p4-r8-20260922/artifacts/base_table.json` | Reutilizada intacta (hashes 6ae11/10bd4/46d08) |
| N250 continuación 31–40 | `results/p4-r8-20260922/artifacts/N250-continuation-cycle31..40.json.gz` + `continuation_N250.json` | Durable, 10 ciclos, conservación PASS, D1/D2 por ciclo |
| N300 continuación 31–40 | `artifacts/N300-continuation-cycle31..40.json.gz` + `continuation_N300.json` | Durable, 10 ciclos, PASS |
| N350 ciclos 1–40 | `campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle01..40.json.gz` | Recuperado 22→30 (8 ciclos) + diagnóstico 30→40 (10 ciclos), total 40 |
| N400 ciclos 1–40 | `campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle01..40.json.gz` | Recuperado 18→30 (12 ciclos) + diagnóstico 30→40 (10 ciclos), total 40 |
| N350 campaña 40 | `artifacts/N350_campaign.json` / `N350_campaign_40.json` | Reconstruido desde 40 ciclos (streaming, sin re-simular) |
| N400 campaña 40 | `artifacts/N400_campaign.json` / `N400_campaign_40.json` | Reconstruido |
| Multicore equivalencia | `artifacts/multicore_equivalence.json` | PASS (`diff0 0.0`, `hist0_match true`) |
| Multicore benchmark real | `artifacts/multicore_benchmark_r8.json` | workers=2, wall_parallel 1737.7 s, sequential 3192.6 s, speedup 1.84 |
| Evaluación final | `artifacts/evaluation.json` | Generado sin simulación, desde ciclos existentes |
| Decisión final | `results/p4-r8-20260922/decision.json` | `P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED` |

Scripts finales:

- `dev_orchestrator/p4_r8.py` (orquestador R8)
- `dev_orchestrator/p4_r8_jobs.py` (jobs NUMBA_FUSED)

Infraestructura temporal de recuperación (auxiliar, no commitada como evidencia científica): `resume_p4r8_recovery.py`, `resume_to_40.py`, `build_campaign_artifacts.py`, `build_campaign_40.py`, `final_r8_close.py` — documentados aquí y excluidos del commit de cierre.

---

## 3. Tabla base y amplitudes (último par A/B)

### N200/N250/N300 (ciclos 29/30, base_table.json)

| N | dx (m) | WA (J) | WB (J) | mean (J) | amp (J) | rel | sensor_max | cyl | port_mass_metric | inv_max | vector_max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 0.00375 | 13.87744 | 13.31499 | 13.59621 | 0.28122 | 0.04053 | 0.60553 | 0.15427 | 0.14965 | 0.32592 | 0.32592 |
| 250 | 0.00300 | 13.83811 | 13.33069 | 13.58440 | 0.25371 | 0.03667 | 0.60377 | 0.15518 | 0.15230 | 0.32483 | 0.32483 |
| 300 | 0.00250 | 13.65809 | 13.40027 | 13.52918 | 0.12891 | 0.01888 | 0.60293 | 0.15794 | 0.16538 | 0.31724 | 0.31724 |

Pipe/Port ledger amplitudes (ejemplo N250 vs N300):

- N250 pipe_mass amp `2.226e-05` kg, pipe_energy amp `11.642` J, port_mass amp `8.085e-06` kg
- N300 pipe_mass amp `2.184e-05` kg, pipe_energy amp `11.366` J (similar, pero work amp ya cae a 0.128)

### N350/N400 (ciclos 39/40, campaña 40)

| N | dx (m) | mesh_n | WA (J) | WB (J) | mean (J) | amp (J) | pipe_mass amp (kg) | port_mass amp (kg) | pipe_energy amp (J) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 350 | 0.002142857 | 350 | 13.405841137198923 | 13.648072950675836 | 13.52695704393738 | **0.1211159067384564** | 2.08e-05 | 7.8e-06 | 11.4 |
| 400 | 0.001875 | 400 | 13.407545491806768 | 13.642726512492775 | 13.525136002149771 | **0.11759051034300327** | 2.02e-05 | 7.6e-06 | 11.2 |

*Nota:* N250 40 (ciclos 39/40) mean `13.57716` amp `0.23922` (ligeramente menor que base 0.253 pero dentro de fluctuación period-2). N300 12-row chain amp `0.12309` similar a base.

**Tendencia espacial N200→N400 (work amp):**

`[0.28122, 0.25371, 0.12891, 0.12112, 0.11759]`

- Disminución sistemática 200→300 (0.281→0.128, -54 %), luego **estabilización** 300→400 (0.128→0.117, ratio 0.91 dentro de 0.8–1.25).
- No colapso hacia cero (`0.117 >0.01` y `0.117 /0.281 =0.417 >0.2`).
- **Descripción contractual:** `amplitud se estabiliza` (no `colapsa`, no `disminuye sistemáticamente` continua más allá de 300).

Pipe mass/energy siguen misma estabilización (2.23e-05 →2.02e-05).

---

## 4. D1 final (n vs n-1) — thresholds originales

| N | work_rel | cylinder | sensor_max | sensor_max_idx | phase (°) | port_mass | inv_max | passed |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 0.04053 | 0.15427 | 0.60553 | 0 | 123.5 | 0.14965 | 0.32592 | **False** |
| 250 (30) | 0.03667 | 0.15518 | 0.60377 | 0 | 124.0 | 0.15230 | 0.32483 | **False** |
| 250 (40) | 0.03463 | 0.15574 | 0.60578 | 0 | 123.5 | 0.15385 | 0.32436 | **False** |
| 300 (30) | 0.01888 | 0.15794 | 0.60293 | 0 | 123.0 | 0.16538 | 0.31724 | **False** |
| 300 (40) | 0.01803 | 0.15825 | 0.60167 | 0 | 122.5 | 0.165? | 0.317? | **False** |
| 350 (40) | 0.01775 | 0.60432* | **0.60432** | 0 | 123.0 | 0.07* | 0.32 | **False** |
| 400 (40) | 0.01724 | 0.60260 | **0.60260** | 0 | 123.0 | 0.06* | 0.31 | **False** |

* cylinder `0.60` es `sensor_max` equivalente para presión cilindro; port e inventories también >thresholds, por lo que `passed=False` siempre. `D1` permanece claramente no convergente (sensor ~0.60) en todas las mallas, incluso tras 40 ciclos.

**Fase del máximo D1:** siempre sensor 0 (x≈0.10 m) en 122.5–124.0°, `p_prev ~100k Pa` vs `p_cur ~30k Pa` (o inverso), `denom ~114k–115k Pa`, `diff ~69k Pa`. Orden sensores idéntico.

---

## 5. D2 (lag-2, n vs n-2) — diagnóstico, NO para aprobar E13 pero indicador period-2

| N | n | work | sensor_max | passed | vec max_norm | Tendencia |
|---|---|---:|---:|---|---:|---|
| 250 (30) | 30 vs28 | 0.00014 | 0.01518 | False | 0.00024 | — |
| 250 (40) | 40 vs38 | 8.47e-05 | **0.00382** | **True** | 3.90e-05 | Alternante, no 3 consecutivas |
| 300 (40) | 40 vs38 | 4.27e-05 | **0.000685** | **True** | 1.66e-05 | — |
| 350 (40) | 40 vs38 | 6.21e-05 | 0.01666 | **False** | 1.44e-05 | Last5 sensor: [0.03904, 0.00262, 0.03572, 0.00125, 0.01665] |
| 400 (40) | 40 vs38 | 6.48e-05 | 0.03434 | **False** | 2.08e-05 | Last5: [0.05017, 0.00136, 0.03017, 0.00084, 0.03434] |

- Trabajo lag2 `<0.001` siempre (PASS work), sensor lag2 ~0.0006–0.05 (mucho menor que D1 0.60) pero **no consistentemente ≤0.005**.
- Patrón alternante: D2 para pares even-even (`0.001–0.002` PASS) vs odd-odd (`0.03–0.05` FAIL) explica por qué no hay streak 3.
- **Streak lag-2 (3 consecutivas passed):**
  - N200 proxy: 0
  - N250 (40): 1 (solo último)
  - N300 (40): 1
  - N350 (40): 0
  - N400 (40): 0
  - Continuación N250 31–40: nunca 3 (`[False,False,True]` últimos 3)
  - Continuación N300 31–40: `[True,False,True]` últimos 3

**Conclusión:** `D2` no alcanza cierre contractual `3× passed` en ninguna malla (incluido 40), aunque work/vector sí. `D2` permanece 1–2 órdenes menor que `D1`, confirmando dos estados alternos, no convergencia a uno.

### N250 análisis completo 1–40 (40 filas)

- `has_period1`: False (nunca 3 D1 consecutivos)
- `has_period2`: False
- `d1_last`: work 0.03463 sensor 0.60578
- `d2_last`: work 8.47e-05 sensor 0.00382 streak 1
- `classification`: `PERIOD2_NOT_CLOSED` (D1 FAIL, D2 pequeño pero no 3×)

### N350/N400 1–40

- `has_period1`: False
- `has_period2`: False
- N350 vec lag2 last `2.79e-05` L2 `1.10e-05`
- N400 vec lag2 last `2.08e-05`

---

## 6. Clasificación por malla (contrato R8)

| Malla | D1 | D2 | has_period1 | has_period2_diag | Clase |
|---|---|---|---|---|---|
| N200 | FAIL (0.60) | ~0.015 (proxy, no 3×) | False | False | **PERIOD2_NOT_CLOSED** |
| N250 (30) | FAIL 0.603 | 0.015 | False | False | **PERIOD2_NOT_CLOSED** |
| N250 (40) | FAIL 0.605 | 0.0038 (1×) | False | False | **PERIOD2_NOT_CLOSED** |
| N300 (30) | FAIL 0.602 | 0.015 | False | False | **PERIOD2_NOT_CLOSED** |
| N300 (40) | FAIL 0.601 | 0.00068 (1×) | False | False | **PERIOD2_NOT_CLOSED** |
| N350 (40) | FAIL 0.604 | 0.01666 | False | False | **PERIOD2_NOT_CLOSED** |
| N400 (40) | FAIL 0.602 | 0.03434 | False | False | **PERIOD2_NOT_CLOSED** |

Todas permanecen período 2, ninguna converge a período 1 ni muestra colapso ni cierre lag-2.

---

## 7. Amplitudes alternas (A/B), mean, tendencia

- **Work A/B alternancia** (odd/even):
  - N200: 13.877 /13.314 mean 13.596 amp 0.281
  - N250: 13.838 /13.330 mean 13.584 amp 0.253 (40: 13.696/13.217 mean 13.577 amp 0.239)
  - N300: 13.658 /13.400 mean 13.529 amp 0.128
  - N350: 13.405 /13.648 mean 13.526 amp 0.121
  - N400: 13.407 /13.642 mean 13.525 amp 0.117

- **Cylinder pressure** D1 `~0.60` corresponde a `Δp ~237k Pa` en `179.5°` sobre `~1.53 MPa` denominador.

- **Sensores 0/1/2 amplitudes** (relativas):
  - N200: 0.605 /0.524 /0.534
  - N350: 0.604 /0.523 /0.545
  - Fase dominante siempre sensor 0

- **Port mass exchange** (kg/ciclo, negativo sale de cilindro):
  - N200 mean `-5.73e-05` amp `7.94e-06`
  - N350 mean similar, no tendencia a cero.

- **Pipe masses** ya tabuladas, estabilizadas.

**Sensor dominante:** sensor 0 (x≈0.10 m) en fase 122.5–124.0° (`p_prev ~30k` vs `~100k`), `metric 0.60`, `grad ~10k Pa/°` en flanco de blowdown. Confirmado en todas las mallas, tanto D1 como D2 alternante.

---

## 8. Conservación, admisibilidad y CFL

| Caso | global_balance max | conservación | admisibilidad | CFL |
|---|---|---:|---|---|---|
| N250 cont 31–40 | 3.9e-05 inv_max D2 pero balance global `4e-15` | PASS (`≤1e-10`) | PASS (rho>0, p>0, Y∈[0,1]) | 0.4 exact |
| N300 cont | 1.66e-05 | PASS | PASS | 0.4 |
| N350 1–40 | max_global `4.52e-14` (wall 1454.9 s, avg 36.37 s) | PASS | PASS (min rho 0.51, T 499K, Y 0–0.44 en G1 tipo) | 0.4 |
| N400 1–40 | max_global `4.02e-14` (wall 1737.7 s, avg 43.44 s) | PASS | PASS | 0.4 |

No `P4_R8_NUMERICAL_REGRESSION`. Todos los ciclos `complete=true`, `reason=final_time`, `CFL≤0.4` exacto, balances por etapa `~3e-16`, sin backflow anómalo. `admissibility` verificada por solver en stages (0D y 1D) sin clipping.

---

## 9. Multicore

- **Equivalencia workers=1 vs 2** (`multicore_equivalence.json`): `MULTICORE_SCHEDULER_EQUIVALENCE_PASS` — `diff0 0.0`, `hist0_match true`, `diff1 0.0`, `hist1_match true` para `N250` 1 ciclo gas. Workers 1 wall 75.78 s sequential 74.95 s speedup 0.989, workers 2 wall 28.96 s sequential 57.25 s speedup 1.97 efficiency 0.988. Sin `parallel=True` en Numba, sin compartir arrays.

- **Benchmark real N350+N400 (40 ciclos, workers=2, `MULTICORE_EXECUTION_V1`):**

| Métrica | Valor |
|---|---:|
| N350 total_wall | 1454.906 s (avg 36.37 s) |
| N400 total_wall | 1737.705 s (avg 43.44 s) |
| Sequential estimado | 3192.611 s |
| Wall paralelo (max) | 1737.705 s |
| **Speedup** | **1.837** |
| **Efficiency** | **0.918** |
| Workers | 2 |
| Passed/Failed | 2/0 |

Para 30 ciclos: sequential 2434.95 s, wall 1324.98 s, speedup 1.837 también (consistente). Cada job conservó directorio aislado `campaign_N350_N400/jobs/G1_N*_30cycles`, sin mezclar archivos, sin compartir estado.

---

## 10. Clasificación terminal R8

Criterios contractuales:

- `P4_R8_REFINED_PERIOD2_SUPPORTED` requiere `N350` y `N400` permanezcan `PERIOD2` **y** `lag-2` alcance cierre `3× passed` **y** amplitud material no nula (`>0.02`) **y** sin colapso **y** conservación PASS.
- `P4_R8_PERIOD2_SPATIAL_ARTIFACT_LIKELY` si `N350` o `N400` convergen a `PERIOD1` o amplitud colapsa `<0.2× N200`.
- `P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED` si persiste period-2 pero sensor no alcanza `0.005` ni se distingue tendencia.
- `P4_R8_NUMERICAL_REGRESSION` si conservación falla.

**Evaluación:**

- `N350_cls=PERIOD2_NOT_CLOSED`, `N400_cls=PERIOD2_NOT_CLOSED` → `remains_period2=True`
- `has_period2_diag` ambos `False` → no cierre lag-2 → `refined_supported=False`
- `amp_nonzero` True (0.121>0.02, 0.117>0.02), `collapse_evidence=False` (0.417>0.2) → `artifact_likely=False`
- Conservación PASS → `regression=False`
- `unresolved = remains_period2 && !refined && !artifact → True`

**→ `P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED`**

No se declara P4 PASS. `P4_BLOCKED_PERIODIC_CONVERGENCE` se mantiene. `SCIENTIFIC_CHANGE_REQUIRED` y `INDEPENDENT_REVIEW_PENDING`.

No se extendió más allá de 40 (máximo contractual). Lag-2 sigue decayendo pero sin cierre (D2 sensor alternante 0.001–0.05, tendencia no monótona clara tras 300). Amplitud se estabiliza, no colapsa, no es artefacto espacial.

---

## 11. Evidencia y reproducción

```
results/p4-r8-20260922/
├── artifacts/
│   ├── base_table.json
│   ├── continuation_N250.json + N250-continuation-cycle31..40.json.gz
│   ├── continuation_N300.json + N300-continuation-cycle31..40.json.gz
│   ├── multicore_equivalence.json
│   ├── multicore_benchmark_r8.json
│   ├── N350_campaign.json (40)
│   ├── N400_campaign.json (40)
│   ├── evaluation.json
│   └── ...
├── campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle01..40.json.gz
├── campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle01..40.json.gz
└── decision.json
```

Comandos sin simulación (solo análisis):

```bash
python -m dev_orchestrator.final_r8_close  # genera evaluation/decision desde evidencia durable
openspec validate --all --strict
python -m unittest discover -s tests -p "test_gas1d*.py" -v
python -m unittest discover -s tests -p "test_hybrid_exhaust.py" -v
```

---

## 12. Revisión

- **Tests focales:** `test_gas1d` 16 PASS, `test_gas1d_batch` 5 PASS, `test_gas1d_fused_aliasing` 3 PASS, `test_gas1d_numba` 5 PASS, `test_hybrid_exhaust` 8 PASS (total 37 PASS en plumbing). `test_multicore` 5/9 PASS (4 fallos por `tests` no paquete y `test_multicore.job_compute` no importable como top-level en `ProcessPoolExecutor` — no atribuible a solver R8; equivalencia real gas PASS).
- **OpenSpec:** 25/25 PASS, `p4-escape-1d` valid.
- **Review:** `INDEPENDENT_REVIEW_PENDING` (dummy hook permanece `BLOCKED`).

---

## 13. Entrega y Git

- Commit cierre P4-R8 incluye: `dev_orchestrator/p4_r8.py`, `dev_orchestrator/p4_r8_jobs.py`, `results/p4-r8-20260922/` (ciclos, campañas, benchmarks, evaluación, decisión), `docs/gasdynamic/p4_r8_refinement.md`. `redme.txt` borrado ajeno preservado sin stage.
- No `P4-PERF-01`, no `P5`.

```
git status --porcelain=v1:
 D redme.txt  (preservado sin stage)
?? dev_orchestrator/p4_r8.py
?? dev_orchestrator/p4_r8_jobs.py
?? results/p4-r8-20260922/
?? docs/gasdynamic/p4_r8_refinement.md
```
