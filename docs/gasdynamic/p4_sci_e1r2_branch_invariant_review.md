# P4-SCI-E1-R2 — branch-invariant reinterpretation

## PROBLEM

E1-R1 compared branch B at N=375 with branch B at N≈251. E13 A/B labels are
valid within each run, but they are relative to each run's anchor and are not
automatically cross-mesh physical identities.

## BASELINE / N375

Baseline closes A and leaves B open. N375 closes B and leaves A open. The
terminal values are preserved in the accompanying artifacts.

## LABELED COMPARISON

The original B→B comparison shows a large reduction and was the basis of the
original `SUPPORTED` interpretation. That comparison is label-dependent.

## BRANCH-INVARIANT COMPARISON

Using closed/nonclosed roles, baseline nonclosed is B and refined nonclosed is
A. The ratios refined/baseline for the terminal triplet are approximately
`0.740, 0.935, 0.809` (mean 0.828, median 0.809). Thus the nonclosed branch
improves moderately, while the orbit still has one open branch and does not
meet E13 period-2.

Worst-branch values remain material in both meshes; best-branch values show
that each mesh has one branch that closes. This separates “one branch improved”
from “the complete orbit converged.”

## STATE MATCHING

Full equivalent state/work/cylinder/port arrays are not retained for all
terminal pairs, so A↔A versus A↔B mapping cannot be selected by state
similarity. The cross-mesh physical mapping remains unresolved.

## PHASE-SWAP ASSESSMENT

`H_PHASE_SWAP` is supported at the role level: the closed role changes A→B
and the nonclosed role changes B→A. Global physical equivalence is not proven.

## RESOLUTION HYPOTHESIS

Resolution clearly changes the solution (H1 supported). The stronger claim that
resolution alone caused the E13 failure (H2) is unproven, because one branch
remains nonclosed after relabeling and E13 requires both branches.

## NEXT EXPERIMENT DECISION

`THIRD_RESOLUTION_NOT_YET_JUSTIFIED`. Before another mesh, resolve state-based
cross-mesh identity and fix the known checkpoint write-order defect. If a third
mesh is later approved, pre-register `worst_branch_lag2_sensor_max` plus the
both-branch E13 outcome; do not use branch B alone.

P4 remains blocked; E13-R1 and physics are unchanged.
