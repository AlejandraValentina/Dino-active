# Revalidación P5 → P8 sobre P4 cerrado

Fecha: 2026-09-29. Base P4: `5642533f73ebcc79bbd38c7dcb2374702863d8a3`.

## Resultado

La suite focal P5-A/P5-B/P5-C, P6, P7, P8 y acoplamiento ejecutó **141 PASS** y 1 caso de campaña explícitamente excluido. OpenSpec estricto pasó para `p5-intake-transfer`, `p7-prescribed-heat-burn` y `p8-wide-rpm-performance`; los hashes de runtime quedan en `results/p5-p8-revalidation-20260929/revalidation.json`. No se modificó código de producto ni se ejecutaron nuevas campañas físicas: la verificación usa tests, provenance y evidencia histórica vigente.

- **P5:** `REVALIDATED_ON_P4_PASS`, clasificación conservada `P5_IMPLEMENTATION_VERIFIED_CONDITIONAL`. Las fixtures de geometría, transfers, backflow, topología completa, ledgers, restart y determinismo pasan en la suite; la evidencia histórica parcial de P5-C se conserva y no se presenta como una campaña periódica.
- **P6:** `REVALIDATED_ON_P4_PASS`, `P6_SPECIES_SCAVENGING_VERIFIED_CONDITIONAL`. Las cuatro especies, donantes forward/reverse, ledgers independientes, scavenging, restart y determinismo pasan; evidencia durable en `results/p6-species-20260925/`.
- **P7:** `REVALIDATED_ON_P4_PASS`, `P7_PRESCRIBED_COMBUSTION_VERIFIED_CONDITIONAL`. El evento es no vacuo, la fuente es admisible, el calor coincide con masa quemada y el ledger conserva energía; restart y replay pasan.
- **P8:** `REVALIDATED_ON_P4_PASS`, `P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL`. Los cinco anchors 2500/5000/8000/11000/15000 tienen todos los gates true, incluyendo finite, geometry, species, evento P7 no vacuo, source/heat consistency, CFL, masa/energía global, restart y replay determinista.

## Semántica de resultados P8

Los outputs son **bounded-transient indicated**: potencia aproximada 181,7 / 171,4 / 89,2 / 25,1 / −24,5 W para los cinco anchors. No se interpretan como curva periódica ni estado estacionario. La validación es numérica; no hay validación experimental.

La revisión independiente permanece `INDEPENDENT_REVIEW_PENDING`. P9 sigue `STOPPED / NOT_AUTHORIZED`.
