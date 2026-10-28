# Independent 176-cell periodicity window — addendum v1

Status: frozen for one first window only. It is admitted after review of the
88-cell cycles 31–40 result, which remained nonperiodic and reached the
registered `STOP_NO_SUFFICIENT_PROGRESS` stop. This run is an independent mesh
diagnostic; it cannot complete the 44/88/176 GCI while 88 lacks periodicity.

## Frozen source and initialization

- Reuse audited E2B A cycle 30 (44 cells, 9000 RPM) and the same frozen source
  hashes as the 88-cell protocol. Do not rerun or alter A.
- Initialize 176 cells independently from A30 by the existing conservative P0
  prolongation. Do not transfer any state from 88; start a fresh detector.
- Keep E2B A physics, V2 port law, MUSCL V2, open-end plenum V2, SSPRK2/HLLC,
  CFL 0.4, geometry and all closure parameters unchanged.

## First window

- Run absolute cycles 31–38 at most, recording 30-degree phase frames, accepted
  and rejected step recipes, native checkpoint and detector after each complete
  cycle.
- Solver budget 900 s; admission limit 1080 s; proposed cost is 869.8 s from
  108.73 s/cycle with 20% planning margin (1043.8 s). Study storage remains
  within 1 GiB with the required 2 GiB free-space reserve.
- Stop on detector classification, conservation/admissibility failure, a
  registered no-progress outcome, or budget. Retain any partial recipe and
  terminal state. Review the trend before further cycles.

## Acceptance and limits

Every complete cycle must have global normalized conservation residuals ≤1e-12,
no inadmissible state, and a valid native checkpoint. Periodicity requires the
existing fresh `PeriodicDetectorV2` contract and then an exact primary audit of
the candidate period. This L1 first window is not itself an audit.

No GCI is calculated until all three grids are independently periodic and the
accepted period primaries are replayed/audited. No candidate promotion,
experimental validation, or predictive claim follows from this window. Keep
V2/MUSCL experimental, legacy default and rc7 unchanged.
