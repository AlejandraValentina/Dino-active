# P4 final closure

## BASELINE / HISTORICAL BLOCKERS

P4A, P4B, E12, E14, E15, performance, G1 E13 and the foundational B1/C1
benchmarks are passing. G2 remains nonconvergent under E13-R1 at both N≈251
and N=375 within max30. No threshold, detector rule or physical model was
changed.

## SCI-04B AUDIT

B2 finite-amplitude boundary and C2 finite-chamber transient are verified by
the existing artifacts: conservation, admissibility, extended-domain
comparison and temporal refinement pass. The suite reports 44/44 tests.

## C3

The related C2 setup has a rigid termination, but the repository does not
contain the dedicated C3 return-arrival, reversal, interface and momentum
report required by SCI-03. C3 is therefore `P4_SCI_C3_INCONCLUSIVE`; no new
solver campaign is started in this closure order.

## ISOLATED MECHANISMS / ROOT CAUSE

B1, B2, C1 and C2 provide no concrete localized defect. Existing audits found
no parity, detector, conservation or admissibility defect. The complete G2
interaction remains unresolved and exhibits one-branch-close/one-branch-open
behavior under the contractual E13 horizon.

## G2 FINAL VERIFICATION

G1 converges period 2 at cycle 60. G2 does not converge period 1 or period 2
by cycle 30 at either tested resolution. No further G2 run is authorized.

## P4 GATE MATRIX

The machine-readable matrix is in `results/p4-final-closure-20260923/`.
E13-G2 and C3 are the blocking entries; all other listed gates pass or are
historically supported.

## LIMITATIONS / FINAL DECISION

This is numerical verification only, not experimental or predictive
validation. Independent review remains pending. Final classification:
`P4_FINAL_BLOCKED_C3_INCONCLUSIVE` (with G2 E13 nonconvergence also recorded).
P4 is not ready for human acceptance and P5 has not started.
