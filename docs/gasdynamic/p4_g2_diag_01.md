# P4-G2-DIAG-01

## OBSERVATIONS

The analysis reads only G2 cycles 1–30. The lag-2 B branch has 14
comparisons, all FAIL; its sensor-pressure maximum ranges from
0.0268215 to 0.460064 (threshold ratio 5.36–92.0), with sensor 0 the
largest failure in the recorded sequence. Its final three values are
0.0897298, 0.0683317, and 0.0290580. The lag-2 A branch reaches streak 5
and falls to a final sensor maximum of 0.0001577. Lag-1 remains materially
separated, with a final value of 0.53448.

All recorded cycles retain conservation and admissibility. The detector audit
confirms n versus n-2 pairing, the G2-only identity, relative A/B mapping, no
INVALID-to-FAIL conversion, and no cross-branch reset.

## CONTRACTUAL FACTS

E13-R1 supports only period 1 and period 2. B never reaches a PASS in the
30-cycle contractual horizon, so P4 remains blocked. No cycle 31+ was run and
no threshold was changed. Lag-4 is diagnostic only and is classified
`NO_PERIOD4_DIAGNOSTIC_SIGNAL`.

## INTERPRETATIONS

The evidence supports `P4_G2_DIAG_BRANCH_B_PERSISTENT_NONCLOSURE`: B is
consistently above the contractual thresholds while A closes. The broad
sensor disagreement and the compact artifacts do not provide enough retained
phase support to call this a localized wavefront. This is consistent with a
geometry-specific unresolved response, but that interpretation is not a new
gate.

## UNRESOLVED QUESTIONS

The existing records do not establish whether the B discrepancy is caused by
the expansion/constant-section/contraction sequence or by another physical
mechanism. Since the horizon is exhausted and no concrete numerical defect was
found, the recommended route is `NO_JUSTIFIED_NEXT_SIMULATION`.
