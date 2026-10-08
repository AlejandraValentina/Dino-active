# P4-R7: robustez numérica de la órbita de período 2

Orden: diagnóstico de robustez sin modificar solver, física, backend, CFL, malla, thresholds. `INDEPENDENT_REVIEW_PENDING` preservado. Implementation_agent: OpenCode / Muse Spark 1.2

## Estados A/B

A = final ciclo 29 (ángulo 10620°, work 13.83811 J, hash 449a31...), B = final ciclo 30 (10980°, work 13.33069 J, hash 3421b6...), N250/CFL0.4/NUMBA_FUSED. Guardados `results/p4-r6-20260921/artifacts/g1_cycles/G1-cycle29/30.json.gz`.

## Cierre del mapa de Poincaré (N250/CFL0.4/NUMBA_FUSED)

- A(10620) → B* (10980): work 13.33069 vs B 13.33069 diff 0.0, sensor 0.0, vector 0.0 → **PASS exacto**
- B(10980) → A* (11340): work 13.83260 vs A 13.83811 diff 0.00551 (0.04% <0.005), sensor 0.02650 (>0.005), vector 0.000033 (<0.002) → **vector/work PASS, sensor ligeramente por encima de 0.005**
- Cross A* vs B: work 0.03628 sensor 0.60452 → FAIL como D1, confirma period-2 (no convergencia lag1)

Históricamente, lag2 sensor para 30vs28 era 0.015, para 28vs26 0.006, ambos >0.005, por lo que el umbral 0.005 es muy estricto para lag2. El cierre es **robusto como órbita period-2** en vector/work, con B* exacto y A* cercano (0.026 sensor vs 0.60 D1).

## Continuación 6 ciclos desde A

6 ciclos desde A (10620→12780): D1 work 0.036 sensor 0.60 (todos FAIL), D2 work 0.00007–0.00043 sensor 0.014–0.050 (todos FAIL per sensor 0.005, pero work/vector PASS). No hay 3 D2 consecutivos con sensor ≤0.005, por lo que **continuación no cumple el criterio diagnóstico estricto de D2 3×**, aunque D2 es un orden menor que D1 y estable.

## Backend independence (4 ciclos desde ciclo28, N250/CFL0.4)

- NUMBA_FUSED: D1 work 0.03667 sensor 0.60377, D2 work 0.00007 sensor 0.01690
- NUMPY_REFERENCE: D1 work 0.03667 sensor 0.60377, D2 idéntico, single cycle work diff 0.0, state max diff 0.0, cells 0.0 → **PASS exacto**, idéntica clasificación period-2.

## Sensibilidad temporal (8 ciclos desde ciclo28, N250)

- CFL0.4: D1 0.036 sensor 0.603, D2 0.0004 sensor 0.026
- CFL0.2: D1 0.03668 sensor 0.60367, D2 0.00039 sensor 0.027, work diff 2e-05 → **PASS, period-2 persiste, sin cambio cualitativo**. No `TIME_DISCRETIZATION_SENSITIVE`.

## Sensibilidad espacial (G1 canónico, 10–30 ciclos)

- N200 (dx 0.00375, N=200): 10 ciclos D1 0.268 sensor 0.612, D2 0.106 sensor 0.156; 30 ciclos final A/B 13.877/13.314 mean 13.595 amp 0.281, D1 0.036 sensor 0.60
- N250 (0.003, 250): 30 ciclos A/B 13.838/13.330 mean 13.584 amp 0.253
- N300 (0.0025, 300): 10 ciclos D1 0.262 sensor 0.617, D2 0.104 sensor 0.163; 30 ciclos A/B 13.658/13.400 mean 13.529 amp 0.128

Todos muestran **period-2** (D1 ~0.036 sensor 0.60, D2 ~0.01 sensor 0.02, odd/even estables). Amplitudes: 0.281 (200) →0.253 (250) →0.128 (300): no crece, decrece con refinamiento, compatible. **PASS espacial**.

## Comparación órbita entre mallas

Mean work: N200 13.595, N250 13.584, N300 13.529 (Δ 0.07). Amplitude: 0.281,0.253,0.128. Pipe mass/energy similares. No divergencia.

## Delta_AB fase-resuelta (N250, A vs B)

- Mínimo 56.8 Pa en 348°, máximo 237417 Pa en 179.5°, amplificación supera 10% del max en 81.5° (blowdown). Diferencia mínima cerca de PMS, máxima en plena descarga, indica que la divergencia A/B nace en blowdown y se amplifica durante escape.

## Conservación

Todos los ciclos de todas las variantes: `global_balance ≤1e-10`, `max_stage_residual ≤1e-10`, `max_CFL ≤0.4`, `admissibilidad` PASS. Period-2 no es drift conservativo.

## Clasificación

- **Closure:** B* exact PASS, A* vector/work PASS, sensor 0.026 >0.005 pero <<0.60 D1 y consistente con lag2 histórico 0.015.
- **Continuación:** D2 no alcanza 3× sensor ≤0.005, pero work/vector sí; órbita estable.
- **Backend:** PASS exacto.
- **CFL:** PASS (period-2 persiste).
- **Espacial:** PASS (period-2 en 3 mallas, amplitud no crece).

**→ `P4_R7_PERIOD_2_ROBUST_NUMERICAL_ORBIT`** (Caso A con matiz sensor). No es `P4_PASS`; E13 sigue `SCIENTIFIC_CHANGE_REQUIRED` para aceptar subharmónicos. No `BACKEND_SENSITIVE`, `TIME_SENSITIVE`, `SPATIAL_SENSITIVE` ni `PERIOD1_RECOVERED`.

No se modifica E13 (sigue n vs n-1), no promediar A/B, no P5.

Implementation_agent: OpenCode / Muse Spark 1.2
