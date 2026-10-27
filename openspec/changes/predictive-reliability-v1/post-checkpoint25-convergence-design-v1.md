# Follow-up design after one-cycle sensitivity, not execution

No claim of periodicity or mesh independence from a single-cycle mapped-state
comparison. No promotion of remapped diagnostics into production histories.

Spatial investigation before costly periodic campaign:
- Three resolutions44/88/176, same physical phase and matched actual step cap,
  conservative physical initialization with explicit source provenance.
- Separate remap representation by validating one conservative limited-linear
  initialization alongside P0 for the steep upstream front; no solver limiter,
  Riemann or boundary modification. Preserve means, energy and each component.
- Fixed physical-duration checks before periodic work. At most120s per44/88case,
  240s per176case,16MiB each; no automatic enlargement. Require initial norm,
  inventory and source guards before execution. Do not infer GCI from two grids
  or from a nonasymptotic one-cycle inherited coarse solution.
- Compare common-volume L1/L2 fields, fronts and cumulative bidirectional fluxes,
  spatial phase effects and work separately. Use actual accepted-step histories
  for temporal control; a requested cap alone may collapse under CFL.
- Only if spatial sensitivity plus initialization uncertainty is bounded for
  the requested observables, preregister a short original-grid continuation
  from native25 with unchanged detector and source (max4cycles/90s, checkpoint
  every cycle, stop at budget/stagnation). That continuation is prepared here,
  not launched; fine diagnostic states must not replace the original native25.

Quantitative thresholds for a future periodic mesh claim remain those of the
owner staged plan and frozen detector. This design does not relax them.
