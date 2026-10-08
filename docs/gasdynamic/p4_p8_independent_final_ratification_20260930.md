# Ratificación independiente final P4→P8 — 2026-09-30

**Dictamen: `INDEPENDENT_REVIEW_BLOCKED`.** Se reauditaron los gates finales y las mutaciones originales R4-001 ahora son rechazadas. Sin embargo, una mutación coordinada del estado terminal PRIMARY y su restart, con digests y referencias regenerados, sigue produciendo `closure_ok=true` sin concordar con la historia gasdinámica primaria. Es un **BLOCKER** para ratificar P8 y el conjunto P4→P8. No corregí el defecto, no modifiqué código productivo ni la evidencia original, y no ejecuté P9.

## Baseline y preservación

HEAD revisado: `722691dfee48a163198ce81b04e0b21a77bf2646`, rama `main`, igual a `origin/main`; árbol limpio. `git diff --check` pasó. Los dos commits R4 posteriores forman parte del HEAD. El reporte y receipt históricos R4 (`INDEPENDENT_REVIEW_BLOCKED`, R4-001) permanecen intactos. La campaña R4 superseded se excluyó de la decisión.

## Resultado de las mutaciones R4-001

En copias temporales de la campaña final ensayé `fresh_mass_delivered_kg`, `fresh_short_circuit_mass_kg` y `replay_terminal_digests.first`: consolidado solamente, individual solamente y ambas copias concordantes. También probé los tres valores juntos en ambas copias. **Las diez variantes dieron `closure_ok=false` y `primary_audit_ok=false`; `csv_equal=true`**, demostrando que el CSV no es la autoridad del gate.

## BLOCKER FINAL-001 — terminal PRIMARY no ligado a la historia bruta

Reproducción exacta en otra copia temporal de `results/p8-wide-rpm-auditable-r4-final-20260930/`, para el anchor de 2500 rpm:

1. En ambos artifacts PRIMARY cambié `terminal.conservative_state[0][0]` en `+0.25` y apliqué el mismo cambio a `restart.terminal_state.conservative_state[0][0]`.
2. Recalculé el digest SHA-256 de cada preimage terminal, actualicé `producer_terminal_digest`, referencias SHA-256/tamaño, y los digests de las copias consolidada e individual.
3. Dejé intacto `terminal.gas_history[-1].stage_states[-1][0][0]`. Su valor permaneció `0.00032609255306421015 kg`, mientras el estado terminal declarado pasó a `0.2503260925530642 kg`.
4. `_audit_p8` aceptó la campaña: `closure_ok=true`, `primary_audit_ok=true`, `anchor_files_equal=true` y `csv_equal=true`.

El auditor compara dos terminales PRIMARY concordantes, restart y digest, pero no compara el estado conservativo terminal con el último estado aceptado del historial bruto. Por tanto, una terminal alterada puede presentarse como replay válido aunque la trayectoria guardada termine en otro estado. Este defecto invalida directamente el gate contractual de replay y es un **BLOCKER**. No añadí una firma criptográfica: el hallazgo es una incoherencia interna verificable entre campos ya persistidos.

## Gates restantes

La auditoría primaria sin mutaciones devolvió `P8_PRIMARY_EVIDENCE_REAUDIT_PASS`. Los cinco anchors dieron PASS y se verificaron en los estados de todas las etapas finitud, positividad de masa/energía, fracciones de especie admisibles y la igualdad exacta de geometría 900°→180°. Los valores reconstruidos fueron:

| RPM | Trabajo (J) | Potencia (W) | Residuo masa (kg) | Residuo energía (J) | Máx. residuo ledger especie (kg) |
|---:|---:|---:|---:|---:|---:|
| 2500 | 4.36006443176 | 181.669351323 | 1.99e-17 | -7.36e-12 | 4.45e-18 |
| 5000 | 2.05624923628 | 171.354103023 | 1.49e-17 | -2.86e-13 | 6.55e-18 |
| 8000 | 0.669119496785 | 89.2159329046 | 1e-17 | -4.22e-13 | 7.27e-18 |
| 11000 | 0.137153296973 | 25.1447711118 | 5.64e-18 | 3.24e-12 | 2.97e-18 |
| 15000 | -0.098111847969 | -24.5279619922 | 1.34e-17 | -2.93e-14 | 7.66e-18 |

En cada anclaje el replay directo, digest, fresh delivery, short circuit, estado de especies, restart, CFL y ledgers pasan para la evidencia intacta. Se mantiene la semántica `BOUNDED_TRANSIENT_INDICATED`; no se afirma periodicidad, predicción ni validación experimental.

**G2/R3-001:** reauditoría offline `E13_G2_V2_PASS`, período 2, stop contractual en ciclo 50, A=15/B=3. La conservación se recalculó desde ledgers primarios; ciclos 31, 40 y 50 dieron residuo global máximo `1.66e-14`, `1.36e-14` y `1.37e-14`, respectivamente. CFL y admisibilidad pasaron. No se repitieron integraciones ni ciclos posteriores a 50.

**R2:** `dt=false` produjo `INCONCLUSIVE / MALFORMED_CFL_DT`, nunca PASS; 11 pruebas focales aprobaron.

**C3:** no se repitió la adquisición. Los siete hashes runtime-binding de C3-R5 coinciden. En el primer sample de retorno contractual (índice 694, `t=0.002654656914619853 s`) A, B0, B1 en etapas A/B y B2 dieron PASS. El ledger primario del paso conservó exactamente masa, energía y especie; la adquisición reporta `completed` hasta `0.003 s`. C3 conserva su status histórico `P4_SCI_C3_PASS`, con esta revisión limitada a muestras suficientes según la orden.

**P4:** la evidencia técnica, C3 y G2 está aprobada; la matriz marca `P4_PASS_TECHNICAL_ONLY`. No otorgo la aceptación independiente porque el blocker P8 impide ratificar el conjunto. P5 conserva PASS de fixtures de intake/transfer, backflow, topología, ledgers, restart y determinismo. P6 conserva PASS de cuatro especies, donantes directos/inversos, ledgers, scavenging/short circuit, restart y determinismo. P7 conserva PASS de evento no vacuo, admisibilidad de fuente, consistencia calor/masa quemada, ledger energético, restart y replay. La provenance de revalidación P5–P8 y las 113 pruebas ejecutadas soportan estos estados; no hubo cambios de código productivo P4–P7 en la remediación. P5–P7 siguen `CONDITIONAL_ON_P4`; esta revisión bloqueada no elimina esa dependencia.

## Pruebas y estado

- P8 audit/mutation/replay: 20 PASS; prueba de campaña física excluida y campaña final reauditorada por separado.
- P5–P7: 113 PASS.
- P4/E13/G2 focal: 76 PASS, una prueba de adquisición excluida; R2 `dt=false`: 11 PASS.
- OpenSpec estricto: P4, P5/P6, P7 y P8 PASS; `git diff --check` y Git LFS fsck PASS.

**Estado final:** `INDEPENDENT_REVIEW_BLOCKED`, BLOCKER `FINAL-001`. P4 sigue `P4_PASS_TECHNICAL_ONLY` con aceptación `NOT_GRANTED`; P5–P8 no quedan ratificados. Validación experimental `NOT_PERFORMED`; P9 `STOPPED_NOT_AUTHORIZED`. El receipt detallado es `results/p4-p8-independent-final-ratification-20260930/review.json`.
