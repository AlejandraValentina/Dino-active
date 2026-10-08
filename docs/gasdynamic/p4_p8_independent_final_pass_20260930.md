# P4→P8 independent final ratification — 2026-09-30

Reviewed implementation baseline: `78615563ad7f8e4f1dde9ee05226119ffc3433a4` (`main`), clean and equal to `origin/main` before this review. The review is read-only with respect to product and solver code. The only new code execution beyond tests was offline evaluation of persisted evidence; no physical acquisition or P9 work was run.

## Decision

`INDEPENDENT_REVIEW_PASS`. No reproducible BLOCKER or MAJOR was found in the specified P4→P8 gates. P4 is ratified as `P4_PASS`; P5, P6, P7, and P8 are `REVALIDATED_ON_P4_PASS`. Historical blocked reviews and their receipts remain unchanged. Experimental validation remains `NOT_PERFORMED`; P8 remains `BOUNDED_TRANSIENT_INDICATED`; P9 is `READY_FOR_P9_HUMAN_AUTHORIZATION`, not started or authorized by this review.

## P8 primary trajectory and terminal audit

`dev_orchestrator/p8_durable_audit.py` validates every saved accepted SSPRK2 step, its step/CFL/time/angle identity, 360-degree measured horizon, and terminal cycle/time/angle before deriving fresh delivery, canonicalizing the terminal preimage, or checking its digest. It binds the last `gas_history[-1].p8_accepted_state` exactly to terminal conservative state, four-species inventories and ledgers, external totals, P7 event/source, fresh delivery, and short-circuit state. It then independently rebuilds counters/digest and compares raw replay, restart, and summary evidence.

In `motorsim/p8_performance.py`, the snapshot is captured immediately after `system.step()` returns and after elapsed time is advanced. The step returns after installing the SSPRK2 endpoint and completing P6/P7 updates; the snapshot is therefore the accepted in-memory state used by the following step. The raw SSPRK2 `q_n` candidate can differ from this installed state by one binary64 ULP after primitive conversion/reconstruction. This is documented in the auditor and primary-evidence design; no tolerance was added, and terminal comparison uses the exact installed endpoint.

I repeated the FINAL-001 coherent-terminal attack in a temporary copy of the 2500-rpm campaign: changed terminal mass, changed the matching restart terminal state, recomputed terminal digests, then updated compressed-artifact hashes, sizes, and both summary copies while leaving the accepted trajectory untouched. The campaign audit rejected it with `trajectory_terminal_mismatch: conservative_state`; the tracked evidence was not modified.

The existing adversarial suite also passed mutations of mass, momentum, energy, species, species/external ledgers, fresh delivery, short circuit, time/cycle/angle, restart-only state, raw flux/counter/digest copies, and summary/hash copies. A recalculated digest cannot bypass the earlier trajectory-terminal binding check. Validation order is trajectory binding → independently rebuilt counters → canonical preimage → digest comparison → replay/restart equality.

## Five P8 anchors

The independent offline audit `audit_campaign()` re-read both compressed primary runs for each anchor, checked their declared SHA-256 and byte size, reconstructed the measured quantities, and matched each individual and consolidated summary. All five passed finite-state, geometry rebase, admissibility, four-species, non-vacuous P7 event/source/heat, CFL, mass/energy/species balance, restart, deterministic replay, fresh-delivery, short-circuit, and terminal-digest checks.

| RPM | Steps | Work (J) | Indicated power (W) | Max pressure (Pa) | Mass residual (kg) | Energy residual (J) | Species residual (kg) | Max CFL |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2500 | 1867 | 4.360064431757779 | 181.6693513232408 | 1,754,839.8989528634 | 1.9949319973733282e-17 | -7.361666831684488e-12 | 3.469446951953614e-18 | 0.4 |
| 5000 | 996 | 2.0562492362787825 | 171.3541030232319 | 1,738,504.6946132828 | 1.485356976305141e-17 | -2.858828625218468e-13 | 6.938893903907228e-18 | 0.4 |
| 8000 | 647 | 0.6691194967847296 | 89.2159329046306 | 1,687,764.6907165232 | 1.0001765041178778e-17 | -4.2216230511371577e-13 | 0.0 | 0.4 |
| 11000 | 478 | 0.1371532969733605 | 25.14477111178276 | 1,685,182.7187811628 | 5.637851296924623e-18 | 3.241407142695607e-12 | 3.469446951953614e-18 | 0.4 |
| 15000 | 358 | -0.09811184796898713 | -24.527961992246784 | 1,716,040.4740701027 | 1.3444106938820255e-17 | -2.930988785010413e-14 | -1.3877787807814457e-17 | 0.4 |

These are bounded transient indicated results, not a periodic power curve or predictive/experimental validation. P8 evidence remains explicitly conditional on the P4 dependency in its campaign provenance; this ratification resolves that dependency for P5–P8 status without changing P8 metric semantics.

## P4 independent evidence

- **G2 / R3-001:** the durable offline auditor recalculated E13 metrics, conservation, CFL, admissibility, branch identity, ancestry, and detector state through cycle 50 from persisted checkpoints and raw conservation ledgers. Result: `E13_G2_V2_PASS`, period 2, A streak 15, B streak 3, convergence at cycle 50. No new acquisition was run.
- **R2:** the exact cycle-50 checkpoint mutation `dt=false`, with closing checkpoint hash updated, returned `E13_G2_V2_INCONCLUSIVE / MALFORMED_CFL_DT`; it did not pass.
- **C3-R5:** all seven runtime-bound source hashes in the persisted acquisition equal the reviewed source bytes. The persisted 777-record acquisition was independently re-evaluated offline from the recorded return history and frozen N=100 geometry derived from the bound C3 setup. Causal return, A, B0, B1 stage A, B1 stage B, and B2 all passed for every record; conservation residual was `6.964551734577821e-16`, solver completed at the target time. No new physical acquisition was run.
- **Remaining P4 matrix:** the committed P4 gate matrix records P4A/P4B, E12, E13-G1/G2, E14/E15, B1/B2/C1/C2/C3, performance, checkpoint/restart, regressions, and OpenSpec as passing, with the original max-30 G2 failure preserved separately. The updated G2-v2 durable evidence and C3-R5 receipt satisfy the previously outstanding review dependencies.

## P5–P8, checks, and findings

The reviewed HEAD changes only the P8 accepted-state capture/auditor, P8 evidence/specification, tests, and roadmap-executor state; no P4–P7 product implementation file changed. P5–P7 coupling regressions passed. P8 was re-audited from the current campaign artifacts, not inferred from older receipts.

Checks run on the reviewed baseline:

- P4/E13: `190 passed` (the four NumPy deprecation warnings in `test_p4_r10a.py` do not affect results).
- R2 exact malformed-`dt` regression: `1 passed`.
- P5–P7 and coupling: `100 passed`.
- P8/R4 tests: `23 passed`; only the physical campaign test was deselected because the current committed five-anchor campaign was audited separately.
- OpenSpec strict validation: P4, P5, P7, and P8 all valid.
- `git diff --check`: passed; `git lfs fsck`: passed.

BLOCKERS: none. MAJORS: none. MINORS: four unrelated NumPy deprecation warnings in the P4 regression suite. No new physical campaign, acquisition, solver change, threshold change, or P9 work was performed.

## Governance state

`P4 = P4_PASS`; independent review is granted. `P5 = P5_REVALIDATED_ON_P4_PASS`, `P6 = P6_REVALIDATED_ON_P4_PASS`, `P7 = P7_REVALIDATED_ON_P4_PASS`, and `P8 = P8_REVALIDATED_ON_P4_PASS`. `P9 = READY_FOR_P9_HUMAN_AUTHORIZATION`; explicit authorization is still required before starting it. Experimental validation remains `NOT_PERFORMED`. Earlier `INDEPENDENT_REVIEW_BLOCKED` reports and receipts remain historical and unaltered.

Receipt: `results/p4-p8-independent-final-pass-20260930/review.json`.
