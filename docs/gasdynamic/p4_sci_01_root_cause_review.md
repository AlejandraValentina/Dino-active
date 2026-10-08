# P4-SCI-01 — G2 nonclosure root-cause review

## FACTS

G1 and G2 use the same engine, RPM, port, heat law, EOS, solver, CFL,
backend, boundary reservoir and initial state. G1 is straight (0.75 m,
20 mm, N250); G2 is the five-segment chain (0.20/0.15/0.05/0.15/0.20 m,
20→40→20 mm, N251). G2 cycles 1–30 conserve and remain admissible. Branch A
closes under lag-2; branch B does not. Sensor 0 is at 0.10 m, before the first
0.20 m transition, and no parity or angle-wrap defect was found by code audit.

## CODE AUDIT

The mesh builder creates shared faces, exact frustum volumes and volume
centroids. Segment joins require continuous diameters. The quasi-1D area source
is the signed finite-volume term `p_i*(A[i+1]-A[i])`; the same expression is
used through the stage solver and no double counting was found. G1/G2 use the
same nonreflecting exterior reservoir and the same 0D↔1D interface path.
Conservation passing does not prove that coupling or boundary behavior is
free of phase error, but no concrete defect is identified.

## G1 VS G2

The material differences are geometry, mesh topology/cell distribution, area
variation and the resulting expansion/reflection/contraction wave train. These
are confounders only in the sense that they are the intended physical change;
no accidental backend or branch difference was found.

## HYPOTHESES

Resolution is **UNTESTED** for G2 specifically. Area-source sensitivity is
**PARTIALLY_SUPPORTED** as a plausible mechanism because G2 has abrupt area
joins, but no defect is demonstrated. Exterior-boundary and port-coupling
hypotheses are **UNRESOLVED**. A complex higher-period orbit is
**INCONCLUSIVE**; lag-4 supplies no diagnostic signal and is not an E13 gate.
No claim of chaos, instability or insufficient resolution is made.

## DISCRIMINATING EXPERIMENTS

The minimum information-gaining experiment is one bounded G2 refinement with
only `dx` changed. A resolution hypothesis predicts a material reduction in
branch-B lag-2 sensor error; persistence falsifies that hypothesis. If needed,
an isolated boundary-return test and an isolated coupling-return test follow.
No experiment is authorized by this review.

## RISKS

The repository lacks a quantitative variable-area source benchmark at these
abrupt joins and an isolated G2 boundary/coupling return-wave benchmark.
Those are explicit reference gaps. A combined mesh+source+BC change would make
causal attribution impossible and is rejected.

## DECISION TREE

No parity or angle bug is confirmed; no concrete geometry, boundary or
coupling defect is confirmed. If a human authorizes further work, start with a
single-variable resolution study. Otherwise the remaining issue is a model
fidelity review.

## RECOMMENDED NEXT ACTION

`P4_SCI_TARGETED_EXPERIMENT_JUSTIFIED`: consider E1 only after human approval,
with a bounded cost and predeclared falsification criterion. P4 remains
blocked, E13-R1 is unchanged, and P5 has not started.
