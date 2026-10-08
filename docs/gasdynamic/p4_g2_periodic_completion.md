# P4 G2 periodic completion

The historical G2 chain (cycles 1–15) was replayed with the canonical E13-R1
detector and reproduced the prior audit: lag-1, branch A, and branch B streaks
were all zero. The frozen state from cycle 15 was then continued sequentially
through cycle 30 with NUMBA_FUSED, CFL 0.4, float64, one worker, and the
unchanged solver configuration.

All cycles 16–30 passed conservation and admissibility. The lag-2 A branch
reached a streak of 5, while the B branch remained at 0; lag-1 remained 0.
Neither approved convergence contract (period-1 or both period-2 branches)
was met by cycle 30. No cycle 31 or later was run.

Terminal classification: `P4_G2_MAX30_WITHOUT_E13_CONVERGENCE`, while the P4
acceptance audit remains `P4_BLOCKED_G2_PERIODIC_EVIDENCE`. This is a numerical
evidence result, not experimental validation, and does not start P5.
