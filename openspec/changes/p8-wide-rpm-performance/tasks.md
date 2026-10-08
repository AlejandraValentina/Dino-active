# Tasks

- [x] Record supervisor authorization and the bounded P8-only scope; keep P4
      blocked, experimental validation not performed, independent review
      pending, and P9 stopped.
- [x] Preserve the approved S2T-0D-01 mechanics and frozen P5-C/P6/P7 fixture;
      use exactly two fixed preparation cycles, with no periodic convergence,
      warm start, or steady-state claim.
- [x] Implement two deterministic unmeasured preparation cycles 180->900 with
      P7 disabled, CFL 0.4, repeated mechanical event cuts, clean accounting
      reset, and exact geometry-only rebase 900->180.
- [x] Use one repeated authoritative event-cut builder for preparation,
      measured execution, and restart continuation; include the exact 350/390
      P7 boundaries and 370 restart cut only where P7 is enabled.
- [x] Correct P5-C stored-topology external accounting to intake minus exhaust;
      reconcile accepted P7 heat to the gas ledger without changing burn law;
      retain mass/energy residual terms and tests.
- [x] Add P7 post-event zero-hook, geometry/rebase, preparation-state,
      deterministic replay, restart, species, admissibility, CFL and accounting
      tests without tolerance relaxation.
- [x] Execute the five-anchor campaign and regenerate consolidated JSON, CSV and
      all `anchor-*.json` from that campaign.
- [x] Execute required P8/P7/P6/P5-C/P5-B/P5-A/P3 and focal P4
      coupling/exhaust regressions: 9 passed, 1 deselected for the P8 contract;
      40 passed for P7/P6/P5-C; 92 passed and 7 subtests passed for lower
      regressions.
- [x] Retry OpenSpec strict with a repo-local npm cache; exact command and
      outcome are recorded below.
- [ ] Independent review remains pending; do not claim it without evidence.
- [x] Verify conditional closure with all five anchor gates true and no failures.

## Current evidence

The final campaign status is `P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL`.
All five anchors have heat > 0 and all measured gates are true; `failures=[]`.
The result is conditional on P4 remaining blocked/not granted and does not
claim periodic convergence, steady state, or experimental validation.

The durable evidence records two preparation cycles, zero preparation heat, the
900->180 geometry proof, repeated event cuts, accepted P7 heat, gas/ledger heat
residual, mass and energy ledger terms, exact restart state and CFL. The P5-C
external ledger is intake into the stored topology minus exhaust outflow;
internal interfaces cancel. No residual is hidden or relaxed.

## Validation record

- Campaign: `P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL`; `failures=[]`;
  five anchors have `heat>0` and all gates are true.
- Regression command: `.\\.venv\\Scripts\\python.exe -m pytest -q
  tests/test_p8_performance.py -k "not campaign" tests/test_p7_prescribed.py
  tests/test_p7_full_topology.py tests/test_p6_species.py
  tests/test_p5c_integrated.py tests/test_p5b_integrated_coupling.py
  tests/test_p5b14_complete_fixture.py tests/test_p5_intake_transfer_foundation.py
  tests/test_coupling_adapter.py tests/test_coupling_preflight.py
  tests/test_coupling_riemann.py tests/test_exhaust_port.py tests/test_hybrid_exhaust.py
  tests/test_p4_sci_04a.py tests/test_p4_sci_04b.py tests/test_p4_r1e.py`
  -> P8 contract `9 passed, 1 deselected`; P7/P6/P5-C `40 passed`;
  lower regressions `92 passed, 7 subtests passed`.
- OpenSpec strict: valid with the repo-local writable npm cache.
- `git diff --check`: no errors.
- Independent review: pending.
- P4: `BLOCKED / NOT_GRANTED`; P9: `STOPPED`.

No P4 acceptance, independent review, publication, archive, commit, push or P9
work is claimed.

## Remediación FINAL-001 — enlace trajectory → terminal

- [x] Preservar sin cambios el dictamen y receipt independientes bloqueados del 2026-09-30; el bloqueo histórico sigue identificado como `INDEPENDENT_REVIEW_BLOCKED`.
- [x] Confirmar insuficiencia de la campaña R4 para comparar estado de especies y ledgers acumulados con cada endpoint aceptado; conservarla intacta.
- [x] Persistir en cada endpoint medido el estado acoplado aceptado después de SSPRK2/P6/P7: conservativo, cuatro especies, externos, ledgers, evento/fuente P7, contadores frescos, ciclo, tiempo y ángulo.
- [x] Cambiar el esquema de evidencia primaria a V2 y hacer que la auditoría valide history → terminal antes de digest → restart/replay.
- [x] Agregar mutaciones coherentes de masa, momento, energía, especies, ledgers, fresh delivery, short circuit, tiempo/ciclo/ángulo, restart y terminal/digest/hash/resúmenes; conservar control positivo.
- [x] Reejecutar únicamente los cinco anchors P8 bajo la configuración congelada y reauditar la campaña V2: `results/p8-wide-rpm-trajectory-bound-20260930/`; los cinco anchors aprobaron, `failures=[]`.
- [x] Ejecutar regresiones P8/R4-001 (23 passed; campaña excluida porque se ejecutó por separado), P5–P7 (113 passed), P4/E13 (76 passed, 1 deselected), OpenSpec strict y verificar que los siete hashes runtime-binding C3 siguen iguales.
- [x] Confirmar exacto rechazo del ataque terminal/restart/digest/hash/summary sobre evidencia P8 real de 2500 rpm: `trajectory_terminal_mismatch: conservative_state`; control positivo y los cinco anchors pasan.
- [x] Registrar `READY_FOR_FINAL_INDEPENDENT_RATIFICATION` sin otorgar `INDEPENDENT_REVIEW_PASS`, sin cambiar P4, y sin iniciar P9.

### Resultado de FINAL-001 — 2026-09-30

El registro PRIMARY que fija el endpoint es `gas_history[-1].p8_accepted_state`, capturado al regresar de `P6IntegratedSystem.step`: después de que SSPRK2 instala el candidato `q_n` y terminan transporte de especies y fuente P7, antes del siguiente paso. El `q_n` guardado dentro del diagnóstico de etapa puede diferir del estado reconstruido post-install por un ULP en cámaras; se conserva íntegro y no se agrega tolerancia. La comparación contractual se hace entre las copias exactas del endpoint post-install y el terminal. Se comprueban todos los endpoints para identidad/orden, `dt`, CFL, ángulo y tiempo aceptado; el último además se compara campo por campo con estado conservativo, cuatro especies, estado externo, ledgers gas/P7, fuente, fresh delivery, short circuit y ciclo/tiempo/ángulo. El digest sólo se recalcula después de ese gate; el restart directo y el segundo recorrido se comparan después.

La campaña anterior `p8-wide-rpm-auditable-r4-final-20260930` y los receipts/reports `INDEPENDENT_REVIEW_BLOCKED` no se modificaron. La nueva auditoría V2 fue `P8_PRIMARY_EVIDENCE_REAUDIT_PASS` en 2500/5000/8000/11000/15000 rpm. El resultado conserva `BOUNDED_TRANSIENT_INDICATED`, `CONDITIONAL_ON_P4`, P4 `BLOCKED / NOT_GRANTED`, validación experimental `NOT_PERFORMED` y P9 `STOPPED`. La revisión independiente final sigue pendiente.

## Revalidación sobre P4 cerrado — 2026-09-29
- [x] P8 revalidado sobre `P4_PASS` mediante provenance y auditoría focal; cinco anchors y todos los gates vigentes PASS.
- [x] Outputs conservan semántica `BOUNDED_TRANSIENT_INDICATED`; no se declara periodicidad ni validación experimental.
- [ ] Revisión independiente permanece pendiente; P9 sigue detenido.

## Revalidación tras recuperación G2-v2 — 2026-09-29

- [x] P8 conserva los cinco anchors y todos los gates históricos; `p8_performance.py` y runtime asociado sin cambios, 141 pruebas focales PASS y 1 campaña completa excluida por no haber cambiado P8.
- [x] Recibo nuevo `results/p5-p8-revalidation-g2-v2-recovery-20260929/receipt.json`; semántica `BOUNDED_TRANSIENT_INDICATED`, sin validación experimental.
- [ ] Nueva revisión independiente P4–P8 pendiente; P9 no autorizado.

## Remediación R4-001 — evidencia primaria durable y reauditoría

- [x] Preservar sin modificaciones el reporte/receipt R4 `INDEPENDENT_REVIEW_BLOCKED` y la campaña R3 que reprodujo el MAJOR.
- [x] Confirmar que la campaña R3 no persiste los flujos resueltos/preimage completos necesarios; por tanto, una campaña nueva de los mismos cinco anchors es necesaria y está autorizada.
- [x] Añadir persistencia por replay de terminal state, historial gasdinámico, trazas de donantes/flujo, ledgers, configuración, checkpoint dentro de P7 y terminal de restart.
- [x] Implementar auditor offline independiente de los resúmenes: integra fresh delivery/short-circuit desde flujos primarios; deriva trabajo/potencia/torque/presión y balances; reconstruye el preimage y el SHA-256; compara directamente replay y restart.
- [x] Especificar canonicalización del digest y clases PRIMARY/DERIVED/SUMMARY/DIAGNOSTIC en `docs/gasdynamic/p8_primary_evidence_r4.md`.
- [x] Agregar regresiones de mutación R4-001 para los dos valores frescos, copias consolidadas/individuales/concordantes, digest y evidencia primaria alterada.
- [x] Ejecutar y auditar campaña nueva de 2500/5000/8000/11000/15000 rpm sin modificar configuración física; los cinco anchors aprobaron la reauditoría primaria y el replay.
- [x] Ejecutar suites P8 y auditoría mutacional R4-001, regresiones P5–P7 y P4/E13, OpenSpec estricto, `git diff --check` y Git LFS fsck.
- [x] Actualizar ruta del evaluador durable y registrar `READY_FOR_FINAL_INDEPENDENT_RATIFICATION` tras la reauditoría primaria de los cinco anchors. Mantener P9 no autorizado y la validación experimental `NOT_PERFORMED`.

### Evidencia R4-001 — campaña final 2026-09-30

- Resultado primario: `results/p8-wide-rpm-auditable-r4-final-20260930/primary-audit.json`, clasificación `P8_PRIMARY_EVIDENCE_REAUDIT_PASS`; cinco RPM aprobados, replay directo y copias de anchors coincidentes.
- Pruebas automatizadas: P8 focal 20 PASS; P5–P7 113 PASS; P4/E13 19 PASS. OpenSpec estricto válido; `git diff --check` y `git lfs fsck` PASS.
- Mutaciones del auditor durable sobre una copia temporal de la campaña final: fresh consolidado/individual/ambos, short-circuit consolidado/individual/ambos, digest consolidado/ambos, ataque combinado y estado primario con referencias SHA/tamaño actualizadas: todos `closure_ok=false`.
- Impacto: solo `motorsim/p8_performance.py` recibió instrumentación de captura P8; no cambiaron solver/física, archivos productivos P4–P7, C3 ni G2. R4 original y su receipt permanecen intactos. Estado P4 `BLOCKED / NOT_GRANTED`; P9 `STOPPED`; revisión independiente pendiente.
- El primer intento de campaña R4 queda preservado con `SUPERSEDED_NOT_USED_FOR_DECISION`; no aporta al resultado final. La campaña final es la única evidencia usada por el evaluador durable.
