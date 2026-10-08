# E13/G2 contract audit after C3-R5

Fecha: 2026-09-28. Base: `211f249`.

## Resultado contractual

La propuesta aprobada `docs/gasdynamic/e13_r1_periodicity_contract_proposal.md` y su implementación canónica `docs/gasdynamic/e13_r1_implementation.md` definen dos contratos: período 1 por `lag1_streak >= 3`, con precedencia, y período 2 por dos ramas lag-2 independientes (`branch_A_streak >= 3` y `branch_B_streak >= 3`). Mantienen los thresholds E13 sin relajación y no mezclan ramas.

Clasificación de la auditoría: **`E13_CONTRACT_ALREADY_SUPPORTS_PERIOD2`**.

## Historia revisada

- R6/R7 establecieron una órbita período 2 robusta frente a backend, CFL y malla.
- R10/R10A localizaron el desacuerdo en el frente de choque y conservaron E13 sin cambios.
- R11 confirmó cierre lag-2 bajo el contrato histórico global, pero no convirtió E13 en PASS.
- R12 mostró no cierre de una rama en la continuación N400.
- R13/R13A conservaron la excursión de ciclo 54 y cerraron la brecha 56 vs 54 (`sensor_max=0.0011905119731371136`), sin declarar P4.
- La continuación G2 1–30 (`docs/gasdynamic/p4_g2_periodic_completion.md`) dejó rama A con streak 5, rama B en 0 y lag-1 en 0: no se satisfacen los dos contratos E13-R1 dentro del horizonte.

## Estado y límites

C3-R5 quedó `P4_SCI_C3_PASS` mediante exactamente una adquisición focal, con recibo en `results/p4-c3-r5-20260928/c3-closure-receipt.json`. La revisión independiente conectada permanece `INDEPENDENT_REVIEW_PENDING`; la autorrevisión de este registro no la sustituye.

E13/G2 no se vuelve a ejecutar en esta auditoría. Con la evidencia durable disponible, el resultado de G2 permanece `P4_G2_MAX30_WITHOUT_E13_CONVERGENCE`; no es PASS ni habilita el cierre global de P4. P4 continúa `BLOCKED / NOT_GRANTED`, P5 no se inicia y P9 permanece detenido.
