# Remediación R3 y recuperación técnica P4→P8

Fecha: 2026-09-29. Base: `17b3652731b16c39cd49b8b6d169499f40a6704b` (`main`).

R3 queda preservada como revisión histórica `BLOCKED`. No se editaron su reporte ni su receipt. Esta nota registra el trabajo posterior y deja el árbol listo para una revisión independiente final; no concede aceptación humana ni revisión independiente.

## R3-001 — conservación G2 reauditable

La causa raíz fue que los checkpoints G2 de ciclos 31–50 guardaban residuos ya calculados, pero no inventarios inicial/final ni los intercambios brutos por etapa necesarios para recomputarlos. La adquisición histórica no contenía otra fuente primaria durable equivalente. Por eso se repitió el tramo mínimo desde el continuation contractual ciclo 30 y se detuvo en la convergencia ciclo 50; no se ejecutó el ciclo 51.

La captura optativa `capture_conservation` persiste por paso los inventarios conservativos de inicio, etapa 1, etapa 2 y estado aceptado, tasas externas de ambas etapas, intervalo temporal, integral externa acumulada y residuos diagnósticos. El auditor offline calcula SSPRK2 y balances globales desde esos términos primarios y solo después contrasta los residuos guardados y las puertas productivas. No usa el flag de conservación ni el residuo persistido como autoridad. Los ciclos nuevos requieren el ledger; la evidencia histórica 1–30 conserva su auditoría existente.

La adquisición está en `results/p4-g2-v2-ledger-recovery-20260929-retry/`; `offline-audit.json` registra `E13_G2_V2_PASS`, período 2 en ciclo 50, rachas A=15/B=3. Las celdas y estados terminales de 31–50 coinciden exactamente con la corrida previa. CFL, admisibilidad y conservación recomputada pasan en los veinte ciclos. El threshold `0.005`, máximo de 400 ciclos, streak, definición de período, malla, CFL, solver y modelo permanecen intactos.

Las pruebas negativas cambian inventario inicial/final, flujo externo, términos obligatorios, datos no finitos o malformados y residuos diagnósticos. El ledger mutado o incompleto no puede producir PASS; el residual diagnóstico mutado tampoco sustituye el cálculo independiente.

## R3-002 — igualdad completa P8

El gate anterior omitía parte del estado acumulado de reanudación. El estado exacto ahora incluye estado conservativo, masas de especie, inventarios iniciales, exchanges externos, ledger de gas, eventos y deltas P7, masa fresca entregada total y por transferencia, masa de cortocircuito, y estado operativo. La reanudación exige igualdad exacta de cada componente; el replay determinista compara un digest SHA-256 de una serialización canónica del estado y los ledgers terminales de ambos recorridos independientes.

El restart de P6 ahora persiste/restaura el inventario inicial de especies, manteniendo la representación de tupla del ledger para igualdad exacta. Las mutaciones de fresh delivery, short-circuit y digest no pasan el gate. La regeneración P8 demostró por qué era necesaria: los anchors históricos no persistían las dos terminales requeridas para reevaluar el gate corregido. Se ejecutaron los cinco anchors vigentes —2500, 5000, 8000, 11000 y 15000 rpm— una vez en `results/p8-wide-rpm-replay-r3-20260929-r3/`. Todos pasan restart, replay determinista, especie, masa, energía, CFL, admisibilidad, geometría y gates P7. Los dos intentos técnicos fallidos anteriores están señalados como `used_for_decision=false` en sus carpetas y no se usan para la decisión.

P8 conserva la semántica `BOUNDED_TRANSIENT_INDICATED`, sigue `CONDITIONAL_ON_P4` y no equivale a validación predictiva o experimental.

## Impacto y provenance

No cambió la actualización física del solver, el modelo, el contrato científico, umbrales, malla ni CFL. Los cambios runtime fueron de captura/auditoría, estado de restart y gate de replay. Blobs Git de las fuentes que separan esos cambios (`17b3652` → árbol actual):

| Archivo | Blob de base | Blob actual | Alcance |
| --- | --- | --- | --- |
| `motorsim/exhaust_numpy.py` | `f2d56160703469e1524c26ed60a97fe253715cd2` | `ebc2a2ec3dc4d1ae47e1d8dc0fcd67465a998fe9` | Captura optativa de términos del balance; no participa en la actualización. |
| `motorsim/hybrid_fast.py` | `2b4663d59808281265a9f8cd49c31f03bb9a0cb5` | `144b3cd4a4c79a63b5e5e468ef20b41fb78fa1cb` | Propaga el flag optativo de captura. |
| `motorsim/p6_species.py` | `588372237e4cc1c7cce531a4a2bd92b8126cf9cf` | `5935a54a86896616108282f1ae1e7620073a28b1` | Completa persistencia del ledger en snapshot/restore. |
| `motorsim/p8_performance.py` | `bd402e73e1ee5416633ef59e65f9b23f9f3f18b1` | `aa26fef3203c3364169896c40e8df612c5014b70` | Gate exacto de estado y replay; no altera el integrador físico. |
| `motorsim/coupling.py` | `98992f5f007db86ee839a420c8ba546f9fc31b4e` | igual | Sin cambios. |
| `motorsim/p5c.py` | `11b6b0f0546e0e08f52f84e97b727a9467a4eb4b` | igual | Sin cambios. |
| `motorsim/p7_prescribed.py` | `a52de638772474329ca18d7b093e5fda683efacf` | igual | Sin cambios. |

El runtime binding histórico C3-R5 mantiene sus siete hashes exactos: `p4_sci_04b.py`, auditor C3-R5, los auditores de Riemann/HLLC y las fuentes `second_order.py`, `riemann.py`, `eos.py`. Todos coinciden con `results/p4-c3-r5-20260928/acquisition-evaluation.json`; no fue necesario repetir C3.

## Revalidación y estados

- P4 recuperado como `P4_PASS` técnico sobre la matriz vigente y G2 auditable. Aceptación: pendiente del revisor independiente final.
- P5, P6 y P7: suites relevantes aprobadas; conservan su clasificación `*_VERIFIED_CONDITIONAL` y dependencia `CONDITIONAL_ON_P4`.
- P8: cinco anchors aprobados bajo gate corregido; conserva condición P4 y semántica transitoria indicada.
- 188 pruebas P4/E13 aprobaron; 2 casos de campaña/adquisición quedaron excluidos porque la evidencia física necesaria se generó y verificó de forma separada. G2 focal: 57 aprobadas, 1 adquisición excluida. P5–P7: 90 aprobadas. P8 replay: 12 aprobadas y campaña verificada separadamente. P6 snapshot/restore: 16 aprobadas.
- OpenSpec estricto aprobado para `p4-escape-1d`, `p5-intake-transfer`, `p7-prescribed-heat-burn` y `p8-wide-rpm-performance`.
- Experimental validation: `NOT_PERFORMED`. P9: `STOPPED_NOT_AUTHORIZED`.

La matriz consolidada está en `results/p4-p8-r3-remediation-20260929/recovery-matrix.json`. Estado final de implementación: `READY_FOR_FINAL_INDEPENDENT_REVIEW`; R3 conserva su clasificación histórica bloqueada hasta que el reviewer evalúe esta evidencia.
