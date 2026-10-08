# P4 G2 — auditoría de causa raíz de la rama B

Fecha: 2026-09-29. Base: `52a15a7`.

## Evidencia revisada

Se revisaron R6, R7, R10/R10A, R11, R12, R13, R13A, la implementación E13-R1 y la continuación G2 1–30. La continuación reutilizó el estado del ciclo 15, mantuvo `NUMBA_FUSED`, CFL 0,4, float64, un worker, conservación y admisibilidad PASS en todos los ciclos 16–30.

El emparejamiento contractual fue `n` contra `n-2`, con A/B relativas al ancla 1. No hay mezcla de ramas ni conversión de INVALID a FAIL. Lag-1 permaneció separado y no cerró, como corresponde a la órbita de período 2.

## Resultado de rama

La rama A alcanzó streak 5. La rama B acumuló 14 comparaciones, todas FAIL; su `sensor_max` descendió de aproximadamente `0,13–0,15` a `0,0290580` en el ciclo 30, pero no alcanzó `0,005`. Las demás comprobaciones físicas registradas permanecieron válidas.

La secuencia es compatible con una respuesta geométrica/numérica persistente específica de B, pero los artefactos no aíslan una corrección técnica concreta. No se encontró defecto reproducible de checkpoint, continuación, selección de rama, métrica, ledger, CFL, backend o malla que pueda corregirse sin cambiar la ciencia.

## Límite contractual

`docs/gasdynamic/p4c_hybrid.md` fija `max_cycles = 30` para P4C y establece que sin resultado periódico E13 no pasa. La propuesta E13-R1 también conserva explícitamente ese límite como política de presupuesto. Ejecutar ciclo 31+ o relajar el umbral requeriría modificar el contrato científico; no se hace automáticamente.

## Clasificación

Con evidencia completa y fallos físicos/contractuales observables, G2 queda `E13_G2_FAIL` bajo el horizonte vigente, materializado históricamente como `P4_G2_MAX30_WITHOUT_E13_CONVERGENCE`. No es `INCONCLUSIVE`: no faltan comparaciones ni hay corrupción de identidad.

P4 permanece `BLOCKED / NOT_GRANTED`. El único siguiente paso para intentar cerrar G2 sería una decisión humana explícita sobre el contrato (por ejemplo, autorizar un horizonte mayor manteniendo thresholds), seguida de una nueva preregistración. No se inicia P5, P9 ni validación experimental.
