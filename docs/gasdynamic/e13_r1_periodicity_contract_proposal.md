# E13-R1 — Contrato formal de periodicidad period-1 / period-2 (propuesta)

**Fase:** E13-R1-DESIGN — sólo diseño, no implementación.  
**Fecha:** 2026-09-23  
**Base:** `df1bc38` P4-R13A (R13A: `P4_R13_N400_EVEN_EVENTUAL_CLOSURE`)  
**Estado:** `HUMAN_APPROVED` — `proposal_revision=R1`, `implementation=false`, thresholds intactos, sin P4 PASS, sin P5  
**Agente:** OpenCode / Muse Spark 1.2 — `INDEPENDENT_REVIEW_PENDING`

---

## 1. Problema

El contrato E13 histórico (`docs/gasdynamic/p4c_hybrid.md:45-56`) supone
convergencia period-1:

> tres comparaciones consecutivas `n vs n-1` PASS con  
> `work ≤0.005, cylinder ≤0.005, sensor_max ≤0.005, port ≤0.002, inventories ≤0.002`.

La evidencia P4 demuestra una órbita física/numérica estable de período 2:

```
A → B → A → B → ...
```

con

- `A_n ≈ A_{n-2}`  y `B_n ≈ B_{n-2}`  (lag-2 pequeño, `~0.00005–0.004`),
- `A ≠ B`  (lag-1 grande, `sensor_max ~0.60`, `work 13.65 vs 13.40`).

Bajo el contrato lag-1 nunca se alcanza PASS. Mantener sólo lag-1 obliga
a declarar `MAX_CYCLES_WITHOUT_CONVERGENCE` aunque la órbita sea estable.
Además un *streak global* lag-2 (`PASS, PASS, PASS` en ciclos consecutivos)
mezcla ramas (`A, B, A` o `B, A, B`) y no garantiza que cada subsecuencia
haya cerrado por separado.

E13-R1 debe reconocer correctamente `period-1` y `period-2` sin relajar
thresholds, sin cambiar física/solver/malla/sensores/CFL y sin métricas
post hoc.

Ciencia congelada: Euler quasi-1D, HLLC/HLLE, MUSCL/minmod, SSP-RK2,
CFL 0.4, `NUMBA_FUSED`, `float64`, `fastmath=False`, `parallel=False`,
sensores en `p4_hybrid.periodic()` (malla común `180.5:0.5:540°`,
interpolación lineal, `sensor_max = max_i max_phase |p_prev-p_cur|/max|p|`).

---

## 2. Evidencia histórica que fija el diseño

### R11 — cierre lag-2 global pero con mezcla de ramas (`6d5e242` → `39cae9a`)

* `results/p4-r11-20260922/temporal_metrics_N*.json`, `parity_analysis.json`,
  `decision.json`
* N300 41–46, N350 41–49, N400 41–51.  
  `first_3x` global lag-2: N300 46, N350 49, N400 51.
* D1 siempre FAIL (`~0.60`). D2 media `0.00003–0.004` PASS.
* Problema: `51` es `49→51` (odd) pero el streak global `49,50,51`
  mezcla `odd, even, odd`. `decision.json:even_vs_odd` muestra
  `N400 even_streak 1` (sólo `50 PASS` tras 4 FAIL) y `odd_streak 6`
  (41–51). El `3×` global no equivale a `branch_A ≥3 ∧ branch_B ≥3`.
* Además `parity_analysis.json` registra booleanos como string `"False"`
  (defecto ya corregido en R12: JSON `true`/`false`), pero no altera la
  conclusión científica `P4_R11_PERIOD2_LAG2_CLOSURE_CONFIRMED` bajo su
  contrato original.

### R12 — cierre por ramas independiente (`fe94c28`)

* `2` ciclos nuevos N400 51–54 (`results/p4-r12-20260922/r12_continuation_N400_50_54.json`):
  `52 vs 50 sensor_max 0.00039 PASS`, `53 vs 51 7e-06 PASS`, `54 vs 52 0.00904 FAIL`.
* `N350` 51 FAIL (arranque, D2 inválido), `52 PASS`.
* `parity_closure_N400.json`: `even [true,true,false] max 2`, `odd [true×6] max 6`.
  Clasificación `P4_R12_ONE_BRANCH_NONCLOSURE`.
* Contratos: R11 intacto bajo su definición; R12 aplica condición más fuerte
  por ramas.

### R13 — horizonte fijo 55–60 (`3face8f`)

* Restart durable `cycle54` válido (`NUMBA_FUSED`, CFL 0.4, N400, 14580°),
  continuación física 55–60 sin early stop.
* `58 vs 56 8.96e-05 PASS`, `60 vs 58 0.00033 PASS`; control impar
  `57 vs 55 5.7e-06 PASS`, `59 vs 57 1.15e-05 PASS`.
* Gap explícito `56 vs 54` sin historia angular en R12 → clasificación
  conservadora `P4_R13_INTERMITTENT_NONCLOSURE` (no acredita cierre eventual).

### R13A — cierre del gap 56 vs 54 (`df1bc38`)

* Replay `51–54` desde `restart_cycle50` de R11 (`results/p4-r11-20260922/campaign_stageA/jobs/G1_N400_A/restart_cycle50`),
  `NUMBA_FUSED`, CFL 0.4, `workers=1`, `full_cycle54` bitwise exacto:
  `state/cells/angle/cycle` → `P4_R13A_CYCLE54_REPLAY_EQUIVALENCE_PASS`
  (`results/p4-r13a-20260923/replay/cycle54_replay_equivalence.json`).
* Reutilizado `results/p4-r13-20260923/campaign_N400_54_60/full_cycle56.json.gz`.
  `56 vs 54` PASS con `sensor_max 0.0011905119731371136` (`sensor 0, fase 132.5°,
  p_prev 52407.79, p_cur 52540.40, diff 132.61, denom 111390.14`).
* Secuencia par sin gap: `50 PASS (0.00444), 52 PASS (0.00039), 54 FAIL (0.00904), 56 PASS (0.00119), 58 PASS (8.96e-05), 60 PASS (0.00033)`.
  Clasificación corregida `P4_R13_N400_EVEN_EVENTUAL_CLOSURE` — FAIL 54 queda
  como excursión transitoria visible.

Thresholds originales intactos en todas las fases.

---

## 3. Thresholds — sin cambios

```
work                 ≤ 0.005   |Wn-Wprev|/max(|Wn|,|Wprev|,1J)
cylinder pressure    ≤ 0.005   max|p_cyl,n - p_cyl,n-1| / max|p|
sensor_max           ≤ 0.005   max_i max_phase|p_i,n - p_i,n-1|/max|p|
port mass            ≤ 0.002   |Qm,n - Qm,prev|/max(|Qm|,|Qmprev|, m_C0)
inventories (I/K/C)  ≤ 0.002   m/U relativo, Y absoluto; pipe m/E relativo, F norm m
vector               ≤ implícito en comparador, pero gate exige max(inv) ≤0.002
conservation         ≤ 1e-10   residuo global y por etapa, normalizado
admissibility        PASS      rho>0, p>0, Y∈[0,1], EOS válida
```

No se propone max→L1/L2, no se redefine `sensor_max`, no se sustituye por
phase-alignment, no se relaja post hoc.

---

## 4. Contrato period-1 propuesto (lag-1)

**Definición:** para cada `n ≥ start+1` comparar `n vs n-1` con la función
contractual `periodic()` idéntica a P4C (`dev_orchestrator/p4_hybrid.periodic`).

**Requisito:**

```
lag1_streak ≥ 3   ⇔   tres comparaciones lag-1 consecutivas PASS
                     con TODOS los thresholds de §3
                     + conservation PASS + admissibility PASS
                     en los tres ciclos del streak
```

**Semántica de contador:**

* inicia a `0` tras `start_cycle` (no hay previo);
* `PASS` → `lag1_streak +=1`;
* `FAIL` (comparación válida fuera de threshold, o conservación/admisibilidad fallida) → `lag1_streak =0`;
* `INVALID` (historia ausente/incompleta, NaN/corrupción, identidad o configuración incompatible) → `lag1_streak =0`, pero no es FAIL científico;
* el streak es consecutivo sin huecos; no se “recuerda” un PASS antiguo;
* se evalúa a partir de `cycle ≥ start+5` (mínimo legacy) pero el contador
  puede empezar antes; la convergencia sólo se declara cuando `cycle ≥ min_cycle`
  y `streak ≥3` dentro del horizonte;
* tras `restart` el streak se restaura desde `restart_detector_state` (§13);
  sin ese estado el contador reinicia a `0` y requiere reconstruir `n-1`.

**Resultado:**

```
periodicity_status = CONVERGED
detected_period    = 1
converged_cycle    = ciclo donde se alcanza el tercer PASS (n)
lag1_metrics[n]    = {work,cylinder,sensor_max,sensor_details,port,inv_max,passed}
```

No hay averaging ni relajación; un `FAIL` intermedio resetea completamente.

---

## 5. Contrato period-2 propuesto (lag-2 por ramas)

Definir dos ramas lógicas independientes:

```
branch A : ..., n-4, n-2, n
branch B : ..., n-3, n-1, n+1
```

Cada rama usa comparación `lag-2: n vs n-2` con idéntica función y thresholds.

Cada rama mantiene su propio contador:

```
lag2_branch_a_streak
lag2_branch_b_streak
```

Reglas:

* `PASS` en `A` → `a_streak +=1`, `b_streak` inalterado.
* `FAIL` en `A` → `a_streak =0`, `b_streak` inalterado.
* `INVALID` en `A` → `a_streak =0`, `b_streak` inalterado; rompe la consecutividad sin declarar no convergencia física.
* `PASS` en `B` → `b_streak +=1`, `a_streak` inalterado.
* `FAIL` en `B` → `b_streak =0`, `a_streak` inalterado.
* `INVALID` en `B` → `b_streak =0`, `a_streak` inalterado.
* Nunca mezclar: un `PASS` global no incrementa ambas; un `FAIL` no resetea
  la otra rama.
* La comparación `n vs n-2` sólo es válida si ambos ciclos existen y
  conservación/admisibilidad PASS en `n`; si falta historial, la comparación
  se marca `INVALID`, no cuenta como PASS ni FAIL y reinicia únicamente el
  streak afectado (requiere reconstrucción o replay).

---

## 6. Condición de convergencia period-2

```
PERIOD2_CONVERGED  ⇔
    lag2_branch_a_streak ≥ 3
AND lag2_branch_b_streak ≥ 3
AND NOT PERIOD1_CONVERGED   (precedencia §7)
AND conservation PASS en los ciclos del streak
AND admissibility PASS en los ciclos del streak
```

Los thresholds son exactamente los de E13 (§3) aplicados al lag-2.
No se exige lag-1 PASS para period-2; de hecho `D1 ~0.60 FAIL` es esperado
cuando `A≠B`.

La convergencia se declara en el ciclo donde la **segunda** rama alcanza
su tercer PASS (la primera ya tenía ≥3 y sigue ≥3).

---

## 7. Precedencia period-1 / period-2

Orden determinista:

```
1. evaluar period-1 (lag1_streak)
2. evaluar period-2 (a_streak, b_streak)
3. si lag1_streak ≥3        → detected_period = 1
   else if a_streak≥3 ∧ b_streak≥3 → detected_period = 2
   else                      → NOT_CONVERGED
```

**Justificación:** toda solución period-1 que converge también satisface
lag-2 (`n vs n-2` compara el mismo estado). Sin precedencia se clasificaría
erróneamente como period-2. Con precedencia, `period-1` es el caso estricto
y `period-2` sólo se declara cuando `period-1` no ha cerrado pero ambas
ramas sí.

Caso límite: si tras convergencia period-1 la ejecución continúa,
las comparaciones lag-2 seguirán PASS, pero el estado permanece
`CONVERGED_PERIOD1`.

---

## 8. Caso N400 obligatorio — semántica esperada

Rama par N400 (definida como ciclos pares relativos al origen 40):

```
50 PASS (0.00444)  → a_streak 1
52 PASS (0.00039)  → a_streak 2
54 FAIL (0.00904)  → a_streak 0   (reset)
56 PASS (0.00119)  → a_streak 1
58 PASS (8.96e-05) → a_streak 2
60 PASS (0.00033)  → a_streak 3   ⇒ convergido en 60
```

Rama impar ya cerrada (`41,43,45,47,49,51,53,55,57,59` todos PASS,
streak ≥6 desde 45).

Resultado:

* **No convergido en 52** (`a_streak 2 <3`).
* **No convergido en 54** (`a_streak 0`).
* **Convergido en 60** (`a_streak 3 ∧ b_streak 3`).

El `FAIL` de 54 resetea sólo la rama par, no invalida permanentemente la
simulación y permanece visible en `final_even_sequence.json`.

Este caso es el test de aceptación del diseño.

---

## 9. Caso N350 — reconstrucción contrafactual

Evidencia existente (sin simular):

* R11 41–49: odd `41T 43T 45T 47T 49T` (streak 5, primera 3 en 45),
  even `42F 44F 46F 48T` (streak 1, primera 3 no alcanzada).
* R12 continuación 51F (D2 inválido, arranque), 52T (`52 vs 50 0.00141 PASS`,
  `results/p4-r12-20260922/campaign_N350_45_52/jobs/G1_N350_45_52/r11_result.json`);
  `full_cycle50.json.gz` existe (`parity_closure_N350 even [T,T,T]` sugiere
  `48T 50T 52T`).

Reconstrucción bajo E13-R1:

| ciclo | rama | D2 vs | sensor_max | PASS | a_streak | b_streak |
|------:|------|-------|-----------:|------|--------:|----------:|
| 41 | B | 39 | 0.00100 | T | 0 | 1 |
| 42 | A | 40 | 0.01526 | F | 0 | 1 |
| 43 | B | 41 | 0.00032 | T | 0 | 2 |
| 44 | A | 42 | 0.00986 | F | 0 | 2 |
| 45 | B | 43 | 0.00030 | T | 0 | 3 |
| 46 | A | 44 | 0.00821 | F | 0 | 3 |
| 47 | B | 45 | 3.8e-05 | T | 0 | 4 |
| 48 | A | 46 | 0.00477 | T | 1 | 4 |
| 49 | B | 47 | 2.9e-05 | T | 1 | 5 |
| 51 | B | 49 | 0.604   | F*| 1 | 0 |
| 50 | A | 48 | (no D2 en R11, pero full_cycle50 existe) | T | 2 | 0 |
| 52 | A | 50 | 0.00141 | T | 3 | 0 |

`*` 51F es artefacto de arranque (falta historial `49` completo lag-2); si se
ignora como `INVALID`, B no debería resetear. Con corrección, B mantendría 6.

**Conclusión propuesta (pendiente de verificación `50 vs 48`):**

* odd primera 3 en **45**,
* even primera 3 en **52** (si `48T ∧ 50T ∧ 52T`),
* period-2 convergido en **52** (la segunda rama cierra),
* `detected_period =2`, `period1_converged=false` (D1 ~0.60 FAIL),
* `evidence_complete = PARTIAL` (requiere lectura confirmada de `full_cycle50`
  vs `48` con función contractual; no se simula nuevo ciclo).

Sin confirmar `50 vs 48`, el cierre no es acreditable como `EVIDENCE_COMPLETE`.

---

## 10. Caso N300 — reconstrucción contrafactual

R11 41–46: even `42T 44T 46T` (streak 3 en 46), odd `41F 43F 45T` (streak 1).

| ciclo | rama | sensor_max | PASS | a(even) | b(odd) |
|------:|------|-----------|------|--------:|-------:|
| 41 | B | 0.01544 | F | 0 | 0 |
| 42 | A | 0.00015 | T | 1 | 0 |
| 43 | B | 0.00782 | F | 1 | 0 |
| 44 | A | 0.00017 | T | 2 | 0 |
| 45 | B | 0.00498 | T | 2 | 1 |
| 46 | A | 3.5e-05 | T | 3 | 1 |

* `period1` nunca PASS (D1 ~0.60).
* `branch even` alcanza 3 en 46, `branch odd` sólo 1.
* `PERIOD2_CONVERGED = false` en todo el horizonte 41–46.
* `evidence_complete = false` — la rama odd no llega a 3 por falta de
  horizonte (no por fallo persistente). Se requeriría continuar impar
  `47,49,51` para decidir.

No se infieren datos faltantes. Estado: `MAX_CYCLES_WITHOUT_CONVERGENCE`
bajo E13-R1 si el horizonte terminase en 46.

---

## 11. Streak global — formalización de insuficiencia

`PASS, PASS, PASS` en ciclos consecutivos **no** basta para period-2.

Ejemplo:

```
47 B PASS  → b=1, a=0
48 A PASS  → b=1, a=1
49 B PASS  → b=2, a=1   (global streak 3 pero a=1, b=2)
```

Cumple `global lag2_streak 3` pero `a_streak 1, b_streak 2` → no period-2.

El caso real N400 global `49T,50T,51T` habría sido declarado cierre en R11
( `first_3x 51` ), pero bajo E13-R1 `a=1 (50T), b=6 (41–51)` → faltan 2
even PASS consecutivos. El detector debe ser `branch-aware`.

Implementación exigirá contadores separados; un `vector<int>` global no sirve.

---

## 12. Identidad de rama — no odd/even absoluto

No definir ramas como “par/impar absoluto del número de ciclo” porque el
número absoluto cambia tras `restart`/`import` (ej. R12 empieza en 45 o 50).

**Definición conceptual:**

```
branch A / branch B  (etiquetas lógicas)
```

**Mapeo interno propuesto:**

* `anchor_cycle` = `start_cycle` del job que creó la órbita (ej. 40 en R11,
  54 en R13). Se persiste en `restart_detector_state.anchor_cycle`.
* `branch = (cycle - anchor_cycle) % 2`  
  `0 → A`, `1 → B` (o viceversa, pero consistente).

Alternativa válida: `parity = cycle %2` si y sólo si el `anchor` es par y
no hay rebase; ambas son isomorfas y se documenta la elegida. La clave es
que el mapeo sea **relativo al origen de la órbita**, no absoluto tras
import, y que se **persista**.

Tras `restart` el proceso receptor lee `anchor_cycle` y reconstruye la
identidad sin ambigüedad. Un cambio de `anchor` sin nueva órbita es
`SCIENTIFIC_CHANGE`.

---

## 13. Restart semantics

Qué debe guardar el `restart` para continuar detección sin perder estado
científico:

**Persistir (obligatorio):**

* `lag1_streak` (int)
* `lag2_branch_a_streak`, `lag2_branch_b_streak` (int)
* `lag1_last_cycle`, `lag1_last_passed`, `lag1_metrics` (última comparación)
* `lag2_branch_a_metrics` (última comparación `A n vs n-2`)
* `lag2_branch_b_metrics` (análogo)
* `branch_anchor_cycle` (int)  y `branch_map` (`A_even`/`A_odd`)
* `detected_period` si ya convergió (`0/1/2`)
* `converged_cycle`
* `lag1_history_cycle_ids` (para saber `n-1` existe)
* `lag2_history_cycle_ids` (para saber `n-2` existe)
* `last_full_history_ref` (puntero a `full_cycleXX` necesaria para lag-2
  interpolado; si no persiste el array, al menos su hash y ubicación)

**Reconstruible (no persistir si se puede derivar):**

* `history phase arrays` si se conservan `FULL_DEBUG`/`full_cycleXX`; en caso
  contrario debe persistirse la métrica y el resultado PASS/FAIL, pero no la
  historia completa para re-comparar (tradeoff espacio vs recomputación).

**Política recomendada:** guardar `SUMMARY` cada ciclo (1.6 KB) + `RESTART`
cada 5 (`state.npz` 8–13 KB) + `FULL_DEBUG` para cada ciclo que participe en
una comparación pendiente (16–22 MB). Si `FULL_DEBUG` no se guarda, la
comparación `n vs n-2` futura requiere replay desde `restart` (coste
computacional) — se documenta como `EVIDENCE_GAP` si falta, como en R13.

No se puede “re-inventar” un streak artificial tras datos faltantes;
si falta `n-2`, la comparación es `INVALID`, no `PASS`.

---

## 14. Early stop — comportamiento futuro

* **Period-1:** `stop cuando lag1_streak ≥3` (dentro de `max_cycles` y fuera
  de warm-up `cycle ≥ start+5`). El `stop` se ejecuta inmediatamente tras
  registrar el tercer PASS; no se ejecuta `n+1`.

* **Period-2:** `stop únicamente cuando a_streak ≥3 ∧ b_streak ≥3`.
  No parar en `52` ni `54` para N400; parar en `60` (primera vez que ambas
  ramas cumplen). Si ambas alcanzan 3 en ciclos distintos, el `stop` ocurre
  cuando la segunda lo alcanza.

* **Caso N400:** `52 → a=2` no stop, `54 → a=0` no stop, `60 → a=3 ∧ b≥3` stop.

* **Mixed stop:** si `period-1` alcanza 3 antes que period-2, se detiene como
  `period-1`; period-2 no se evalúa como convergencia posterior.

El `early stop` no sustituye `conservation/admissibility`; un ciclo con
fallo de conservación nunca cuenta para streak aunque el wall-time permita
continuar.

---

## 15. Max cycles — separación de criterio y política

No se cambia `max_cycles =30` (P4C) ni `min 5`. Estados propuestos:

```
CONVERGED_PERIOD1                    (lag1 ≥3)
CONVERGED_PERIOD2                    (a≥3 ∧ b≥3, precedencia period-1)
MAX_CYCLES_WITHOUT_CONVERGENCE       (horizonte agotado sin cierre)
NUMERICAL_FAILURE                    (conservación/admisibilidad/CFL fail)
UNSUPPORTED_PERIODICITY              (evidencia no period-1/2, ver §16)
```

`max_cycles` es política de presupuesto, no criterio de convergencia.
Un `FAIL` transitorio no cambia `max_cycles`; sólo resetea su rama.

---

## 16. Periodicidad >2 — no generalizar en GEN1

GEN1 no construye detector `period-N` genérico (`period-3,4,...`).

Si aparece evidencia incompatible con `period-1` y `period-2`:

* `D1 FAIL`, `D2 FAIL` pero `D3 PASS` sostenido, o divergencia de ramas,
* se declara `UNSUPPORTED_PERIODICITY` / `PERIODICITY_NOT_SUPPORTED`.

No se adapta thresholds ni se inventa `period-3` sin orden científica.
Se requiere nueva campaña diagnóstica y decisión explícita antes de cambiar
el contrato.

---

## 17. Campos propuestos (no implementados en esta fase)

```json
{
  "periodicity_status": "NOT_CONVERGED | CONVERGED_PERIOD1 | CONVERGED_PERIOD2 | MAX_CYCLES_WITHOUT_CONVERGENCE | NUMERICAL_FAILURE | UNSUPPORTED_PERIODICITY",
  "detected_period": 0 | 1 | 2,
  "lag1_streak": 0,
  "lag1_metrics": {"work":0.0,"cylinder":0.0,"sensor_max":0.0,"port":0.0,"inv_max":0.0,"passed":false,"sensor_details":[...]},
  "lag1_last_cycle": 60,
  "lag2_branch_a_streak": 3,
  "lag2_branch_b_streak": 6,
  "lag2_branch_a_metrics": {"work":..., "sensor_max":..., "passed":true},
  "lag2_branch_b_metrics": {"work":..., "sensor_max":..., "passed":true},
  "lag2_branch_a_last_cycle": 60,
  "lag2_branch_b_last_cycle": 59,
  "branch_anchor_cycle": 40,
  "branch_map": {"A":"even","B":"odd"},
  "converged_cycle": 60,
  "conservation_pass": true,
  "admissibility_pass": true,
  "restart_detector_state": {
    "lag1_streak": 0,
    "a_streak": 3,
    "b_streak": 6,
    "anchor_cycle": 40,
    "detected_period": 2
  }
}
```

Todos los campos son serializables JSON con booleanos nativos `true`/`false`
(nunca strings, ver riesgo R11).

---

## 18. Matriz de tests futura (diseño, no implementación)

| Caso | Secuencia | Expectativa E13-R1 |
|------|-----------|--------------------|
| **A — period-1 limpio** | `n vs n-1: PASS,PASS,PASS` | `CONVERGED_PERIOD1` en `n` (lag1 3) |
| **B — period-1 con reset** | `PASS,FAIL,PASS,PASS,PASS` | sólo último 3 converge; `FAIL` resetea |
| **C — period-2 limpio** | `A PASS, B PASS, A PASS, B PASS, A PASS, B PASS` (6 ciclos, cada rama 3) | `CONVERGED_PERIOD2` cuando ambas 3 |
| **D — falso streak global** | `A PASS, B PASS, A FAIL, B PASS, A PASS, B PASS` (global 3 al final `B,A,B` pero `A` 1,2?) | `NOT_CONVERGED` (A streak 2,B streak 2 tras FAIL) |
| **E — caso real N400** | `50T,52T,54F,56T,58T,60T` (par) con `odd≥3` | converge sólo en 60 (tercer nuevo PASS de A) |
| **F — period-1 y lag-2 ambos PASS** | lag-1 `T,T,T` y lag-2 `A T*3, B T*3` | `CONVERGED_PERIOD1` (precedencia) |
| **G — restart** | guardar `streaks,anchor`, reiniciar, continuar `A T, B T...` | resultado idéntico con y sin restart |
| **H — fail en A no resetea B** | `A FAIL, B PASS` intercalado | `b_streak` permanece |
| **I — fail en B no resetea A** | `B FAIL, A PASS` | `a_streak` permanece |
| **J — invalid history** | `n vs n-2` sin `n-2` | `INVALID`, no incrementa ni resetea |
| **K — boolean serialization** | `true`/`false` vs `"True"` | debe rechazar strings |

Cada caso exige `conservation/admissibility PASS` en los ciclos del streak;
un `FAIL` de conservación equivale a `FAIL` de periodicidad.

---

## 19. Contrafactual P4 — qué habría hecho E13-R1

Usando sólo evidencia existente (sin simular):

| N | period1_converged | branch_A_first_3 | branch_B_first_3 | period2_converged_cycle | detected_period | evidence_complete |
|---|-------------------|-----------------|-----------------|-------------------------|-----------------|-------------------|
| **300** | `false` (D1 0.60 FAIL) | **46** (even `42,44,46`) | **no** (odd `41F,43F,45T` max 1) | **none** | `0` | `false` — horizonte impar insuficiente (faltan `47,49,51` impar) |
| **350** | `false` | **52** (even `48T,50T,52T` *si 50T*) | **45** (odd `41T,43T,45T`) | **52** (*si 50T confirmado*) | `2` | `PARTIAL` — requiere verificar `50 vs 48` PASS con `full_cycle50`; 51F es arranque `INVALID` |
| **400** | `false` | **60** (`50,52,56,58,60` con reset 54) | **45** (`41T,43T,45T`) — y `≥6` en 51 | **60** | `2` | `true` — con R13A se completa `56 vs 54 PASS`, historia angular disponible |

* `period1` nunca converge en 41–60 para N300/350/400 (D1 sensor `0.60`).
* N300 no converge period-2 en 46 por rama impar incompleta; R11 global 46
  no sería convergencia bajo E13-R1.
* N350 converge en 52 bajo hipótesis `50T`; sin esa verificación quedaría
  `NOT_CONVERGED` (evidencia parcial).
* N400 converge en 60, no en 51 (R11) ni 52/54; el FAIL 54 es excursión que
  retrasa pero no invalida.

No se infieren ciclos no ejecutados; la tabla es `counterfactual` basada en
archivos existentes.

---

## 20. Retrocompatibilidad

| Fase | Efecto de E13-R1 | Clasificación |
|------|------------------|---------------|
| P4-R5 | `P4_BLOCKED_PERIODIC_CONVERGENCE`, 30 ciclos `D1 ~0.60 FAIL`, `D2 ~0.00005` pero no period-2 aún; ciclo único medido | `DIAGNOSTIC_ONLY` — no cambia; era pre-periodicidad |
| P4-R6 | `PERIOD_2_ORBIT_CANDIDATE` con `D2` y `vector` pero sin separar ramas | `REINTERPRETED_BY_E13_R1` — D2 global no distingue, habría requerido branch-aware |
| P4-R7 | `PERIOD_2_ROBUST_NUMERICAL_ORBIT`, 6 ciclos `D2 0.01–0.05` | `REINTERPRETED` — robustez sigue válida, pero streak 3 no acredita period-2 |
| P4-R8 | `P4_BLOCKED_PERIODIC_CONVERGENCE`, baseline para R11 | `UNCHANGED` |
| P4-R9 | audit sensor lag-2 | `DIAGNOSTIC_ONLY` |
| P4-R10 / R10A | localización shock, no periodicidad | `UNCHANGED` |
| **P4-R11** | `P4_R11_PERIOD2_LAG2_CLOSURE_CONFIRMED` con `first_3x 46/49/51` global | `REINTERPRETED_BY_E13_R1` — bajo E13-R1, `N400` no habría cerrado en 51 sino en ≥60 (incluso no en 51 por `a_streak 1`); `N300` tampoco en 46. La clasificación permanece válida **bajo su contrato** pero no como `E13-R1 CONVERGED` |
| **P4-R12** | `P4_R12_ONE_BRANCH_NONCLOSURE`, even max 2 | `UNCHANGED` — ya es branch-aware parcial; E13-R1 lo formaliza y confirma |
| **P4-R13** | `P4_R13_INTERMITTENT_NONCLOSURE` por gap 56vs54 | `REINTERPRETED_BY_E13_R1` — con R13A pasa a `EVENTUAL_CLOSURE` en 60 |
| **P4-R13A** | `P4_R13_N400_EVEN_EVENTUAL_CLOSURE` | `UNCHANGED` — es exactamente el caso de aceptación de E13-R1 |
| P4-R5→R8 early | perf, no periodicidad | `UNCHANGED` |

No se reescriben commits históricos; se preservan resultados y se añade
`reinterpretación` en documentación.

---

## 21. Riesgos

* **period-1 satisface lag-2:** sin precedencia, una solución period-1 se
  declara period-2. Mitigado por §7.
* **pérdida de branch identity tras restart:** `anchor_cycle` perdido →
  mapeo `A/B` invertido, streaks atribuidos a rama errónea. Mitigado por
  `restart_detector_state.anchor_cycle`.
* **streak artificial tras datos faltantes:** `n-2` inexistente comparado como
  `PASS` por defecto. Mitigado: marcar `INVALID`, no contar.
* **mezcla de configuraciones:** comparar ciclos de `N300` vs `N400` o
  `CFL 0.4` vs `0.2` como si fuesen misma órbita. Mitigado: detector exige
  `config_hash` idéntico (`N, dx, backend, CFL, gas`).
* **reset incorrecto de una rama:** bug `even_streak` resetea `odd`
  (observado en borrador `p4_r12_branch_continuation.py:162` comentado).
  Mitigado por tests H/I y `branch-aware` estricto.
* **early stop prematuro:** parar en `52` (streak global) antes de que ambas
  ramas cierren. Mitigado por §14.
* **persistencia insuficiente:** guardar sólo booleano sin métricas →
  no auditable. Mitigado por §17 y `SUMMARY`/`FULL_DEBUG`.
* **falsas cadenas PASS tras NaN/error:** `NaN ≤0.005` es `false`; debe
  tratarse como FAIL y resetear. Mitigado por comparador `passed = bool(...) ∧ conservation`.
* **boolean serialization:** R11 usó `"False"` string que es truthy en
  Python (`bool("False")==True`). Mitigado: exigir `isinstance(v,bool)` y
  test K; R12 ya corrigió a `true`/`false`.

---

## 22. Decisiones para aprobación humana (no autoaprobadas)

Se separa **derivado de evidencia** vs **propuesta de contrato**.

**Derivado de evidencia (no negociable si se quiere capturar R13A):**

* Existe órbita `A↔B` con `lag-2 ≪ lag-1`.
* `FAIL` transitorio en una rama no debe invalidar permanentemente (R13A).
* `streak global` no garantiza ambas ramas (R11 vs R12).

**Propuesta de contrato (requiere aprobación explícita):**

| ID | Propuesta | Alternativa | Default si no aprueba |
|----|-----------|-------------|----------------------|
| **A** | `streak length =3` | `2` o `4` | mantener 3 (legacy P4C) |
| **B** | `period-1` tiene precedencia | `period-2` primero | `period-1` primero |
| **C** | `branch-independent reset` | reset global | independiente (diseño) |
| **D** | `period-2 requires BOTH branches` | `ANY branch` | BOTH |
| **E** | thresholds idénticos E13 | relajar `sensor_max` | sin cambios |
| **F** | no soportar `period>2` en GEN1 | detector `period-N` genérico | `UNSUPPORTED` |
| **G** | restart conserva `detector_state` | recomputar sólo | persistir estado |

Cada decisión debe ser `HUMAN_APPROVED` antes de implementar E13-R1.
Sin aprobación, **no** se inicia `E13-R1` ni `P4 PASS`.

---

## 23. Referencias

* `docs/gasdynamic/p4c_hybrid.md` — definición original E12/E13/E14/E15
* `docs/gasdynamic/p4_r11_long_horizon_period2.md`
* `docs/gasdynamic/p4_r12_period2_branch_closure.md`
* `docs/gasdynamic/p4_r13_n400_even_persistence.md`
* `docs/gasdynamic/p4_r13a_evidence_gap_closure.md`
* `results/p4-r11-20260922/temporal_metrics_N*.json`
* `results/p4-r12-20260922/r12_continuation_N400_50_54.json`
* `results/p4-r13-20260923/evaluation.json`
* `results/p4-r13a-20260923/evaluation.json`, `cycle56_vs54.json`

---

*Fin de propuesta E13-R1-DESIGN — requiere revisión humana independiente.*

## 24. Revisión R1 — correcciones obligatorias antes de aprobación

Esta revisión no implementa el detector. Fija dos semánticas que sustituyen
las formulaciones ambiguas anteriores:

1. `INVALID` rompe el streak de la comparación afectada, pero no se registra
   como `FAIL` científico. Un `PASS, PASS, INVALID, PASS, PASS, PASS` sólo
   converge en el último PASS; el contador es `1, 2, 0, 1, 2, 3`.
2. El estado del detector sólo puede continuar si coincide la identidad
   científica persistida: `configuration_hash`, `scientific_contract_id`,
   solver/backend, malla, geometría, RPM/operating point y convención de ciclo.
   Cualquier mismatch produce `INVALID` y reinicia los streaks afectados.

El restart debe conservar `anchor_cycle` y `branch_map` A/B. El anchor de la
órbita original no se redefine por el `start_cycle` de una reanudación. Un
restart sin historia suficiente conserva el estado físico, pero inicia el
detector con evidencia insuficiente y no reconstruye streaks por inferencia.

Las decisiones A–J quedan `HUMAN_APPROVED` por la aprobación explícita registrada
el 2026-09-23: A streak 3; B precedencia
period-1; C reset independiente; D ambas ramas; E thresholds sin cambios;
F periodos mayores que 2 no soportados en GEN1; G estado del detector en
restart; H anchor persistente; I INVALID reinicia sólo la rama afectada sin
ser FAIL; J vinculación a identidad de configuración/ciencia.
