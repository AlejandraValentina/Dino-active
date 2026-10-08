# G2-v2 — preregistración contractual

Fecha de preregistración: 2026-09-29. Esta revisión deriva del G2 histórico y no borra ni reinterpreta su resultado `P4_G2_MAX30_WITHOUT_E13_CONVERGENCE` / `E13_G2_FAIL`.

## Contrato congelado

- Horizonte máximo nuevo: `max_cycles = 400`; no se ejecutarán ciclos 401+ en esta revisión.
- Único delta respecto de G2 original: el horizonte máximo.
- `sensor_max <= 0.005`; work, cylinder, port e inventories conservan exactamente los límites E13 existentes.
- Período 1 y período 2 permanecen definidos por E13-R1; período 1 tiene precedencia. Para período 2, las ramas A y B conservan streaks lag-2 independientes y ambas deben alcanzar 3.
- Lag-1, lag-2, conservación, admisibilidad, CFL, geometría, malla N251, solver `NUMBA_FUSED`, CFL 0,4, float64, `fastmath=False`, `parallel=False`, un worker, RPM 3000 y convención de ciclo 360° no cambian.
- No se modificarán thresholds, métricas, ecuaciones, fronteras ni selección de rama después de observar resultados.

## Continuation y evidencia

Se usará el estado terminal del ciclo 30 de `results/p4-g2-periodic-completion-20260923/cycle30.json.gz` sólo después de verificar identidad de configuración, geometría/malla, backend, estado terminal, ángulo, ciclo, conservación/admisibilidad y continuidad respecto del ciclo 29. La continuación conservará el ancla 1 y `branch_map={A: odd_relative_to_anchor, B: even_relative_to_anchor}`. Si esa identidad no puede demostrarse, la adquisición será `INCONCLUSIVE` y no se mezclará con la historia anterior.

Cada ciclo nuevo registrará índice, rama, lag-1, lag-2, métricas completas, streaks, conservación, admisibilidad, CFL, inventarios/ledger, estado del detector y provenance. Se guardarán resúmenes ciclo a ciclo y checkpoints de continuación; se retendrán datos completos suficientes para auditar cada comparación.

## Decisión previa y parada

La ejecución se detiene inmediatamente después del primer ciclo que satisfaga inequívocamente el contrato completo: lag-1 para período 1, o ambas ramas A/B para período 2, además de conservación, admisibilidad y CFL. Si llega al ciclo 400 sin converger con evidencia completa, el resultado es `E13_G2_V2_FAIL`. Evidencia incompleta, estado inválido, mismatch de runtime o fallo operacional que impida decidir producen `E13_G2_V2_INCONCLUSIVE`. No se ampliará el horizonte a 800 o más.

La física, el solver y los thresholds no se modifican para obtener PASS. P4 sólo podrá cerrarse si G2-v2 PASS y todos los demás gates obligatorios permanecen PASS; la revisión independiente sigue siendo un estado separado.
