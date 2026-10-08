# P2 — SCIENTIFIC_CHANGE_REQUIRED

P2A no aprobado; P2B no implementado. Contrato P1 y baseline intactos.
Gate técnico original FAILED_INFRASTRUCTURE por interrupción explícita tras diagnóstico científico; se conserva evidence.json sin alteraciones.

| Caso | Estado | Tiempo solver s | Pasos | Peor ledger |
|---|---|---:|---:|---:|
| T01_moving | PASS | 0.485 | 300 | 1.57671576e-16 |
| T01_rest | PASS | 0.453 | 250 | 3.73399228e-17 |
| T02_sod | FAIL | 2.610 | 435 | 2.38700775e-16 |
| T03 | PASS | 13.594 | 901 | 1.49627995e-16 |
| T04 | PASS | 52.203 | 3450 | 2.74973397e-16 |
| T05 | FAIL | 0.235 | 17 | 1.49358907e-16 |
| T06_contact | PASS | 22.375 | 3000 | 1.74252973e-15 |
| T07_closed | PASS | 0.891 | 251 | 1.49358907e-16 |
| T07_open | PASS | 0.891 | 300 | 1.82312786e-16 |
| T07_periodic | PASS | 1.031 | 300 | 1.24466409e-16 |
| T08_constant_rest_100 | PASS | 0.406 | 250 | 3.73399228e-17 |
| T08_constant_rest_200 | PASS | 1.594 | 500 | 3.73399228e-17 |

Matriz T01–T12:

| Test | Estado |
|---|---|
| T01 | PASS |
| T02 | FAIL |
| T03 | PASS |
| T04 | PASS |
| T05 | FAIL |
| T06 | PASS |
| T07 | PASS |
| T08 | PARTIAL_NOT_VERIFIED |
| T09 | NOT_EXECUTED |
| T10 | NOT_EXECUTED |
| T11 | NOT_EXECUTED |
| T12 | NOT_EXECUTED |

T02: contacto0.6925 vs exacto0.685490524, error0.007009476 >0.005. Sin cambio de métrica/umbral.
T05: No consistent open-boundary branch, cerca de reposo; defecto de robustez pendiente.
Contadores HLLC sin certificar; los doce registros muestran cero HLLE fallback, no se ensayó T12 adverso completo.
No atribuir a T08 los tests unitarios cortos de equilibrio: su campaña variable/nozzle quedó sin completar.
11 unit tests PASS. Regresiones P0: siete comparaciones exactas offline PASS, hashes intactos, sin integrar 0D.
Revisión independiente BLOCKED/scientific_change_required=true. Cero reparaciones posteriores; STOP impide seguir implementando.
No UI/JSON/paquete/P3. Gráficos SVG/PNG son resultados numéricos, no inspección Windows ni validación experimental.
