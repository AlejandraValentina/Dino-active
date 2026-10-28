# 88-cell periodicity continuation — bounded addendum v1

Status: frozen for one continuation only, after review of cycles 31–36. This
does not authorize the 176-cell window or any further 88-cell extension.

## Evidence and trigger

Window 31–36 completed in 256.70 s (solver 255.79 s) with status
`TRANSIENT_AT_BUDGET`, exact cycle checkpoints and a restored detector history.
The last three maximum error/tolerance values were 4.3252, 3.0289, 2.6947; p90
values were 1.6231, 0.8965, 0.5332. Both tails fell strictly, while the terminal
maximum remains above 1 and cycle work is still increasing. Periodicity is not
demonstrated. This trend admits one bounded continuation to cycle 40.

## Frozen continuation

- Restore `checkpoint-absolute-036.json` and `detector.json` from window 31–36.
- Verify exact source hashes against the committed continuation preregistration.
- Continue the same 88-cell configuration through absolute cycles 37–40, with
  detector indexes 7–10 and the existing PeriodicDetectorV2 contract.
- Solver budget 180 s; admission limit 205 s; projected solver cost 170.5 s and
  projected cost with 20% margin 204.6 s. This remains within the 600 s total
  88-cell stage allowance.
- Save native checkpoints, detector state, recipes and cycle records after
  every completed cycle. No restart into a later cycle unless its saved state
  and detector are both verified.

Stop at detector classification, any conservation/admissibility failure, or
the registered budget. After cycle 40, review the result before another mesh
or continuation. A period candidate still requires exact primary replay/audit;
this continuation alone cannot yield GCI, mesh independence, or promotion.

All E2B A30 source identity, 9000 RPM, V2/MUSCL V2 experimental status, engine
physics, numerical tolerances, and rc7 remain unchanged.
