# P4 final acceptance audit

This audit uses only existing evidence; no solver campaign was run. P4
demonstrates the 0D cylinder, variable exhaust port, and quasi-1D exhaust
coupling. P4A and P4B remain historical passes under their stated contracts.

The canonical E13-R1 detector reproduces the N400 G1 sequence
`50 PASS, 52 PASS, 54 FAIL, 56 PASS, 58 PASS, 60 PASS`; cycle 56 versus 54
has `sensor_max=0.0011905119731371136`, so G1 reaches period 2 at cycle 60.

The available G2 evidence contains cycles 1–15 only. Replaying those records
with the unchanged thresholds produces no valid PASS comparisons (lag-1 and
both lag-2 branches remain at zero). Therefore G2 cannot satisfy the approved
three-comparison detector contract without cycles 16 or later. No such cycles
were executed. This is classified as `P4_BLOCKED_G2_PERIODIC_EVIDENCE`.

E12 conservation and E15 admissibility are supported by the recorded G1/G2
campaign checks; E14 has historical propagation/reflection evidence, but the
terminal P4 gate remains blocked by G2 periodic evidence. Performance and all
focal regression tests pass, including the 11-test checkpoint suite.

P4 is numerical gas-dynamic verification, not experimental validation. P9
remains the experimental-validation phase. Independent review is still
`INDEPENDENT_REVIEW_PENDING`; this report is not P4 human acceptance.
