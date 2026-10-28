# Recorded39 post-opening wave/transport execution — activation v2

This v2 addendum supersedes the runner/output binding from activation v1 after
the first attempt completed exact source replay and the 88-cell extension to
90 degrees, then stopped because a FAST trajectory cannot be serialized with
`engine.snapshot()`. That partial output is preserved under
`DINO_ARTIFACT_ROOT/.../postopen-wave-transport-run-v1`; it is not a completed
case and contributes no accepted physical comparison.

## Corrected binding and remaining budget

- The only code correction is to save common-phase FAST terminals with
  `fast_recipe_terminal_state()`; no solver equation, configuration, timestep,
  CFL, or accepted threshold changes.
- Preserve the same exact source hashes, four P0 cases, 90/120/150 degree
  phases, flux windows, conservation criterion, and per-case cap of 210 s.
- The failed logged invocation used 27.797 s of wall budget. The corrected
  output is a fresh append-only path and has a remaining global admission cap
  of 572.203 s (600 s total activation cap minus that preserved invocation).
- Fresh projection is still 541.002 s with 30% margin. Re-run all four cases
  only if source replay, current hashes, storage preflight and the remaining
  admission cap pass. Run sequentially and re-estimate after every case.
- The first attempt's exact replay is evidence of runner operation only; it
  does not authorize treating the incomplete 88-cell case as a complete
  spatial result. Preserve it intact.

All scope and interpretation limits in activation v1 remain in force.
