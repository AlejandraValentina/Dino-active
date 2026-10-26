## Purpose

Reduce practical time to periodic integrated 2T power and torque curves while preserving the existing physical equations, boundary conditions, spatial/angular meshes, CFL, periodicity tolerances, conservation checks, result semantics, and checkpoint safety.

## Scope

- Profile current IntegratedEngine2T execution on two existing representative A/B configurations using short reproducible runs.
- Attribute CPU cost to duct/HLLC fluxes, ports and interfaces, species, combustion/thermal terms, chamber updates, SSPRK2, allocations/conversions, diagnostics, checkpoints and persistence/presentation.
- Separate profiled solver CPU from processing, persistence, UI and startup.
- Implement one measured high-impact, low-risk optimization, then compare numerical states, conservation, memory, cycle/step time and restart behavior.
- Keep full-curve runtime as a qualified projection unless existing historical data supports that projection; do not repeat six periodic points.

## Explicit exclusions

No physical-model or geometry changes, combustion/sweep changes, CFL/tolerance changes, Desktop features, broad architecture rewrite, C++ migration, full RPM campaign, X30 work, or historical cleanup. Optional compilation backends require demonstrated compatibility and measured likely benefit before adoption.

## Acceptance

1. Two short representative configurations have reproducible before/after CPU profiles and unprofiled timing.
2. The optimization targets the largest measured worthwhile residual hotspot and does not degrade peak memory or stability materially.
3. State, species, conservation ledgers, combustion/work/power outputs, accepted/rejected step sequence, and same-source checkpoint restart meet justified existing equivalence contracts.
4. Any speedup/projection is explicitly limited to measured workloads; no periodic or scientific claims are inferred from transient short runs.
