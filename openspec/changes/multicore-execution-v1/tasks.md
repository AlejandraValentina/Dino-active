## 1. Implementación base
- [x] Scheduler `dev_orchestrator/multicore.py:1` con `ProcessPoolExecutor`, Job/Campaign, estados PENDING/RUNNING/PASS/FAILED/CANCELLED/BLOCKED, evidencia aislada `campaign/jobs/<job_id>/` — `tests/test_multicore.py:30` PASS.
- [x] Detección automática física con política ≤2→1,3–4→2,5–6→3,7–8→4,9–12→6,>12→min(8,floor(0.5*physical)), 6 cores→3, y modo manual 1..6 — `multicore.py:20` `detect_physical_cores`/`suggest_workers`, `tests/test_multicore.py:15` PASS.

## 2. Aislamiento y determinismo
- [x] Jobs con ID determinista, registro `job_id, worker_id, config/input/solver hash, backend, timestamps, runtime, terminal state`, orden de finalización irrelevante, equivalencia 1 vs N — `multicore.py:70` `Job`, `tests/test_multicore.py:60` PASS.

## 3. Memory guard y cancelación
- [x] Estimación memoria por job y guard 25% RAM antes de lanzar workers — `multicore.py:40` `can_launch_workers`, `tests/test_multicore.py:90` PASS.
- [x] Cancel `all/pending/individual` preservando completados; fallo de un job no elimina otros — `multicore.py:464` `cancel_*`, `tests/test_multicore.py:70` PASS.

## 4. Warm-start y RPM sweeps
- [x] Tipos `INDEPENDENT` y `DEPENDENT_CHAIN`, chains secuenciales internas y paralelas, construcción por proximidad RPM y comparación contra secuencial — `multicore.py:210` `add_chain`/`build_rpm_chains`, `tests/test_multicore.py:100` PASS.

## 5. Benchmark y gate científico
- [x] Benchmark 1–4 workers en i5-10400 con trabajos idénticos, medir sequential/parallel wall, CPU, RAM, speedup, efficiency, elegir AUTO por throughput — `results/multicore_benchmark.json:1` workers 1:0.75s 2:0.48s 3:0.41s 4:0.37s, speedup 1.45, best 4 (conservador AUTO 3 per policy).
- [x] Gate `MULTICORE_SCHEDULER_EQUIVALENCE_PASS` comparando workers=1 vs AUTO con igualdad científica — `results/multicore_equivalence.json:1` `PASS` (8 jobs idénticos).

## 6. Validación
- [x] Tests de scheduler (determinismo, aislamiento, cancelación, memory guard, chains) — `tests/test_multicore.py:9` 9/9 PASS.
- [x] `openspec validate multicore-execution-v1 --strict --no-interactive` PASS.
- [x] No `parallel=True` en Numba (`exhaust_numba.py:88` `parallel=False`), no compartir arrays, no alterar tolerancias — `tests/test_multicore.py:120` PASS.
