# P4 — cierre técnico con G2-v2

Fecha: 2026-09-29.

## Resultado

G2-v2 fue preregistrado en `c2e3820` con el único delta contractual `max_cycles=400`. La continuación desde el ciclo 30 fue validada y ejecutó únicamente los ciclos 31–50. El detector E13-R1 cerró período 2 en el ciclo 50: rama A streak 15, rama B streak 3, lag-1 FAIL coherente con dos estados, conservación/admisibilidad/CFL PASS. El `sensor_max` lag-2 de B fue `0.000508629756519752` en el ciclo de cierre. Resultado: **`E13_G2_V2_PASS`**.

El G2 original de 30 ciclos permanece registrado como FAIL y no fue sobrescrito. No se ejecutaron ciclos 51+ ni se cambiaron thresholds.

## Matriz P4

La matriz consolidada está en `results/p4-g2-v2-20260929/p4-final-gate-matrix.json`. P4A, P4B, E12, E13/G1, E14, E15, B1, B2, C1, C2, C3, performance, checkpoint/restart, regresiones y OpenSpec figuran PASS con sus evidencias históricas o nuevas. C3 se acredita con `P4_SCI_C3_PASS`; su runtime binding no fue modificado por la continuación G2-v2.

Clasificación técnica: **`P4_PASS`**. La aceptación independiente sigue separada como `INDEPENDENT_REVIEW_PENDING`; esta ejecución no convierte la autorrevisión en revisión independiente. P5 no se inicia, P9 permanece detenido y la validación experimental no se realizó.

No se modificaron física, solver, geometría, malla, CFL ni thresholds.
