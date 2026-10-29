# E2 at 176 cells — scaling and E1.3 decision

## Execution decision

**No new solver comparison was run.** The E2 authorization is capped at ten
benchmarks. The frozen replication addendum explicitly assigned its two
A44/B44 runs to the final two slots; both have now been consumed. This leaves
no authorized bisection/Brent pair for a 176-cell run. No E1.3 time was
consumed.

The existing 176-cell artifacts are present and preserved:

- Configuration: `C:\Users\ageribon.MIDES\Dino-artifacts\predictive-reliability-v1\candidate-periodic-gci-v1\window-176-02\configuration.json`, SHA-256 `4e8c01987424c0dae3b12a3af456dcbb951e43a992b2278f539bafdedf56ad73`.
- Cycle-37 checkpoint: `...\window-176-02\checkpoint-absolute-037.json`, SHA-256 `5a7ae79230c251d5b277238ef79e5e3ee050d59304c186e4d913c6f9a744085a`; it records cycle 37 at 13320 degrees.
- Its detector has lag-1 streak 0 and period-2 branch streaks A=0, B=0. The run is `TRANSIENT_AT_BUDGET`, not periodic.

The existing 176 runner's `prepare()` starts from the cycle-30 E2B checkpoint
and remaps to 176 cells; it does not restore the cycle-37 checkpoint above.
Using cycle 37 as requested would require a separate, source-bound continuation
comparison path. That change and its paired benchmark are outside the exhausted
E2 budget.

## Measured cost and bounded projection

The preserved seven-cycle 176 run recorded 849.6025 solver seconds and
850.8215 wall seconds: **121.3718 solver s/cycle and 121.5459 wall s/cycle**.
The 1.2189-second wall-minus-solver difference covers the timed loop's
per-cycle observation, checkpoint/frame/recipe writes and other loop overhead.
The timer starts only after `prepare()`, directory creation, configuration and
initial-checkpoint writes, so it excludes input loading, checkpoint restoration,
remapping/engine setup and initial writes. Those costs were not timed and remain
unknown.

At the observed bisection rate, the minimum three future cycles needed for a
period-1 candidate cost 364.1154 solver seconds or about 364.6378 loop-wall
seconds. Applying a 20% margin gives **437.5653 seconds, plus unmeasured
preparation/restoration/setup**. Only 230.1685 seconds remained in the existing
176 per-grid budget. This path does not fit.

For scale context only, applying the A44/B44 Brent speedups (2.2183–2.2901x)
to the 176 bisection rate would project three cycles at 159.5–164.7 seconds of
loop wall time, or **191.4–197.6 seconds with 20% margin**, before the omitted
preparation/restoration/setup. This is not a 176 measurement or accepted
projection. It leaves only 32.6–38.7 seconds against the 230.1685-second cap;
the omitted setup would have to fit inside roughly 27.1–32.3 seconds before
margin. Its cost is unknown. A period-2 candidate would require six future
cycles and would exceed the remaining cap even under the same unverified
speedup extrapolation.

## Decision

**E1.3 cannot be resumed within the currently demonstrated limits. Additional
authorization is required for a two-run E2 176-cell comparison.** That
comparison must restore both solvers from the same preserved cycle-37 state,
include setup/restore/write time, and preserve the bisection and Brent outputs.
Only if its measured end-to-end projection fits the existing 230.1685-second
176 allowance with margin could the owner consider resuming E1.3; no E1.3 run
is authorized by this report.

Even a periodic 176 result alone would not produce valid GCI. The 88-cell
branch remains transient/unresolved and 44/88/176 periodic values on a matched
identity are still required. No periodicity, GCI or predictive claim is made.

## Runner reliability

The E2 candidate runner's result-saving and comparison steps succeeded, but a
relative `--out` path caused a Windows `Path.relative_to` exception while
printing the final summary. A subsequent invocation could misread that as a
failed run and attempt an unsafe duplicate. Path display now normalizes paths
and safely formats both repository-relative and external absolute paths. This
is a reporting-only fix; solver source, checkpoints and all previous hashes
remain unchanged. Focused path/root tests pass.
