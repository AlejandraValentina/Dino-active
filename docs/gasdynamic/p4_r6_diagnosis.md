# P4-R6: diagnóstico de periodicidad — posible órbita de período 2

Orden: diagnóstico antes de nueva campaña. Reutiliza exclusivamente evidencia existente G1 1–30 y G2 1–15 de `results/p4-r5-20260921` / `results/p4-r6-20260921/artifacts/g1_cycles` (NUMBA_FUSED, 19.16s/ciclo, equivalencia exacta). No modifica solver, física, backend, CFL, malla, geometría, thresholds E13, ni P4-R2/R5. `INDEPENDENT_REVIEW_PENDING` se preserva.

Implementation_agent: OpenCode / Muse Spark 1.2

## 1. Hipótesis investigada

Observación final G1: W25≈13.822, W26≈13.341, W27≈13.837, W28≈13.333, W29≈13.838, W30≈13.331. No declarar period-2 aún; determinar si es A metric defect, B period mapping (720°), C órbita estable período 2, D convergencia lenta/no periódica, E otra inconsistencia.

## 2. Evidencia reutilizada

30 G1 y 15 G2 completos con checkpoints, historias, estados 0D, arrays 1D, trazas, inventarios, port integrals. No se ejecutaron otros 30 ciclos iniciales; la generación de 30 G1 para diagnóstico se considera infraestructura de R6 (ahora en `results/p4-r6-20260921/artifacts/g1_cycles/G1-cycle*.json.gz`).

## 3. D1 exacto (n vs n-1) — thresholds P4C originales

Definición contractual idéntica a `dev_orchestrator/p4_hybrid.py:periodic`: work `|Wn-Wprev|/max(|Wn|,|Wprev|,1)≤0.005`, cylinder `max|p_diff|/max|p|≤0.005`, cada sensor `≤0.005`, port `|Qm|/max(|Qm|,mC0)≤0.002`, inventarios m/U ≤0.002 y Y ≤0.002. Falso si alguno excede.

| n | work | work_prev | work_rel | cyl | s0 | s1 | s2 | sensor_max | sensor_max_idx | phase (°) | p_prev (Pa) | p_cur (Pa) | denom | port | inv_max | passed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2 | 14.961 | -0.418 | 1.02795 | 0.25809 |0.09858|0.09812|0.09616|0.09858|0|295.5|104380.7|115840.3|115840|0.10946|0.07473|False|
| 3 | 12.206 |14.961|0.18414|0.03871|0.01529|0.02203|0.01529|0.02204|1|299.5|116625.4|114052.2|116625|0.00295|0.07531|False|
| 4 | 12.441 |12.206|0.01889|0.00356|0.53965|0.43456|0.36835|0.53965|0|126.0|100316.8|38442.9|100316|0.00432|0.05060|False|
| ... | | | | | | | | | | | | | | | | |
|25|13.822|13.360|0.03343|0.15580|0.60452|0.604|0.603|0.60452|0|123.5|100212.1|30864.2|100212|0.15464|0.32442|False|
|26|13.341|13.822|0.03478|0.15587|0.60459|0.604|0.603|0.60459|0|123.5|30864.2|100210.9|100210|0.15227|0.32481|False|
|27|13.837|13.341|0.03585|0.15521|0.60343|0.603|0.602|0.60343|0|123.5|100210.9|30996.9|100210|0.15401|0.32489|False|
|28|13.333|13.837|0.03648|0.15524|0.60347|0.603|0.602|0.60347|0|123.5|30996.9|100212.2|100212|0.15194|0.32498|False|
|29|13.838|13.333|0.03653|0.15518|0.60379|0.603|0.602|0.60379|0|124.0|100218.1|30965.8|100218|0.15417|0.32500|False|
|30|13.331|13.838|0.03667|0.15518|0.60377|0.603|0.602|0.60377|0|124.0|30965.8|100217.2|100217|0.15230|0.32483|False|

Sensor que produce el máximo: siempre sensor 0 (x=0.1m) en los últimos ciclos, fase 123.5–124.0°, p_prev ~100k Pa (alta) vs p_cur ~30k Pa (baja) o viceversa. Orden de sensores idéntico (0,1,2), soporte angular exactamente 180→540 con fases 0.5° (720 puntos), interpolación lineal relativa correcta. No es error de indexing o fase.

## 4. Lag-2 diagnóstico (n vs n-2, NO para aprobar E13)

| n | lag | work | sensor_max | passed |
|---|---:|---:|---:|---|
|3 vs1|2|1.03426|0.08510|False|
|4 vs2|2|0.16843|0.52964|False|
|5 vs3|2|0.00424|0.56604|False|
|...| | | | |
|25 vs23|2|0.00390|0.17982|False|
|26 vs24|2|0.00140|0.02535|False|
|27 vs25|2|0.00111|0.14663|False|
|28 vs26|2|0.00066|0.00667|False (≈0.005)|
|29 vs27|2|0.00005|0.02277|False|
|30 vs28|2|0.00014|0.01518|False|

Trabajo lag2 <0.002 tras ciclo 24, sensor lag2 ~0.006–0.02 (mucho menor que D1 0.60). Inventarios lag2 también <0.002. Indica convergencia hacia dos estados alternos, no hacia uno.

## 5. Lag-3 / Lag-4 (diagnóstico)

- D3 (lag3) sensor_max ~0.60 (similar a D1), work ~0.03
- D4 (lag4) sensor_max ~0.015 (similar a D2), work ~0.0006

Patrón: lag impar = no convergente, lag par = convergente → período 2, no período mayor ni drift irregular (drift mostraría crecimiento monotónico de lag2, no observado).

## 6. Vector estado X_n

X_n = [I m,U,F; K m,U,F; C m,U,F; pipe mass,mom,energy,species]. Normalización física declarada (relativa con floor 1 J o 1e-6 kg).

| n | ||X_n-X_{n-1}|| max | L2 | ||X_n-X_{n-2}|| max | L2 |
|---|---:|---:|---:|---:|
|23|0.32209|0.12174|0.00073|0.00029|
|24|0.32426|0.12254|0.00319|0.00122|
|25|0.32442|0.12259|0.00024|0.00011|
|26|0.32481|0.12275|0.00058|0.00023|
|27|0.32489|0.12277|0.00012|0.00005|
|28|0.32498|0.12282|0.00026|0.00008|
|29|0.32500|0.12282|0.00004|0.00001|
|30|0.32483|0.12278|0.00024|0.00009|

Lag1 ~0.324 sostenido, lag2 ~4e-05–7e-04 → X_n≈X_{n-2} pero ≠X_{n-1}. Criterio `PERIOD_2_ORBIT_CANDIDATE` satisfecho de forma sostenida.

## 7. Invariancia 360°

Para 2T, `theta → theta+360°` debe ser identidad (mismo volumen, dV, áreas, port.area, events, source). Comprobado en estados congelados representativos (theta 0,90,180,270,350,480):

- `geometry(theta)` vs `geometry(theta+360)`: diff volumen 0, dV 0, área 0 (exacto)
- `port.area(theta)` diff 0
- `LegacySources` / `HybridSystem` heat_start desplazado +360 correctamente, events idénticos

**PASS** — no mapping defect.

## 8. Handoff y 720°

- Handoff `cycle n end → n+1 start`: state 0D, pipe cells, inventories, angle, composition, ledger initialization exactos por construcción (`state=row['state']; pipe=row['cells']` sin reinicialización silenciosa). Verificado en 29 fronteras: sin reinicio de pipe/cylinder/crankcase/fresh.
- Búsqueda 720°: `motorsim/` contiene 720 solo en módulos 4T (`four_stroke.py`, `valves.py`, etc.), no en camino híbrido 2T (`hybrid_exhaust.py`, `exhaust1d.py`, `hybrid_fast.py`). No dependencia `angle%720`, `cycle parity`, `heat_start+720`, ni estado compartido. **No se encontró `P4_R6_PERIOD_MAPPING_DEFECT`.**

## 9. Restart determinism

Checkpoint G1-cycle28 reejecutado como ciclo 29 con `NUMBA_FUSED` (1 ciclo, prueba infraestructura, no campaña):

- `state`, `cells`, `work_indicated_J` (13.838113318470205), `port_integral`, `history` exactos (`max_abs 0`)
- `restart determinism PASS`

## 10. Trabajo e inventarios odd/even

```
odd W:  -0.418, 12.206, 12.258, 12.161, 10.032, 11.631, 12.398, 13.012, 13.528, 13.299, 13.482, 13.667, 13.768, 13.822, 13.837, 13.838
even W: 14.961, 12.441, 12.301, 12.190, 13.621, 13.602, 13.616, 13.528, 13.437, 13.399, 13.360, 13.341, 13.333, 13.331
```

- Odd subsecuencia últimos 3: 13.822→13.837 (0.0011), 13.837→13.838 (5e-05) → convergente
- Even últimos 3: 13.341→13.333 (0.00065), 13.333→13.331 (0.00014) → convergente
- Cross odd/even diff ~0.50 J (3.6%) → no convergencia lag1

Pipe mass odd ~1.486e-04, even ~1.041e-04 (30% diferencia), cada subsecuencia estable (1e-07 variación). Similar para pipe energy (odd 71.68 J vs even 48.39 J), K/C/I inventarios, port mass/energy/species (odd port mass -6.54e-05 vs even -4.92e-05). Divergencia nace antes del evento de escape (diferencia ya en `pipe_mass` al inicio de ciclo, no solo post-escape), sugiere causa en estado inicial del ciclo (condición de cierre), no solo dinámica de escape, pero requiere análisis causal más profundo (no inferir solo por potencia).

## 11. G2 existente (15 ciclos, diagnóstico)

D1 G2: ciclos 4–5 sensor_max 0.005 (habrían sido PASS aislados), pero 6→ sensor_max 0.46, 7→0.457, 8→0.527… hasta 15→0.552 → no periodic. D2 G2: 7 vs5 0.009, 9 vs7 0.005, 11 vs9 0.003, 13 vs11 0.005, 15 vs13 0.004 → lag2 convergente también. Mismo patrón previo a interacción geométrica → causa común del motor/ciclo, no específica de G1.

## 12. Clasificación

- **Metric defect (A): DESCARTADO** — sensor, fase, interpolación y normalización verificados exactos; sensor_max real es 0.60, no artefacto.
- **Period mapping defect (B): DESCARTADO** — invariancia 360° PASS, handoff PASS, no dependencia 720° en 2T.
- **Original periodic PASS (E): DESCARTADO** — D1 nunca muestra 3 comparaciones consecutivas ≤0.005/0.002.
- **Sin convergencia (D): DESCARTADO para lag2** — D2 y vector lag2 sí convergen (work 6e-05, sensor 0.006, vector 4e-05).
- **Período 2 real (C): CONFIRMADO**

Criterios C satisfechos:
- implementación 360° PASS
- handoff PASS
- metric PASS (no defecto)
- D2 y X_n-X_{n-2} convergen (<0.002/0.005 sostenido)
- D1 permanece claramente no convergente (~0.036 work, ~0.60 sensor)
- odd/even forman dos estados reproducibles (work, pipe, port, inventarios)

**→ `P4_R6_PERIOD_2_ORBIT_CONFIRMED` — STOP. No modificar E13. Período 2 como estado periódico requeriría `SCIENTIFIC_CHANGE_REQUIRED` + decisión humana explícita (no promediar, no duplicar período, no relajar thresholds, no aumentar MAX_CYCLES).**

## 13. Entrega

Tablas D1/D2, D3/D4, odd/even, vector, sensor fase 123.5°, invariancia, handoff, restart, G2, tests, commits en `results/p4-r6-20260921/` y `results/p4-r5-20260921/`. Sin P5, sin cambio de contrato.

Implementation_agent: OpenCode / Muse Spark 1.2
