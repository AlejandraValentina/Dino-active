# Dino Desktop rc8 Windows TRIAL candidate acceptance

**Classification: FAIL.** The candidate ZIP is intact and its serial Desktop path works, but the packaged Windows parallel A/B dispatcher does not start its point workers. This candidate is not READY_TRIAL.

## Package

- Version: `0.1.0-rc8` TRIAL, source commit `08ce73da`.
- ZIP SHA-256: `1c183663c5ba4178732e65dbf64ddcc9a75fdabe7823e5d71eb21f7577da218d`.
- ZIP integrity: 325 entries, `testzip=None`.
- Exactly one package build was performed. rc7 remains the accepted baseline and was not modified.

## What passed in the packaged application

The actual `Dino2T.exe` launched. Desktop created and edited a synthetic engine, saved and reopened its project, and duplicated a variant with a 4 mm exhaust-length change. A serial 4500/5000 RPM sweep completed one cycle per point; results were shown as `MAX_CYCLES_NONCONVERGED / INSUFFICIENT_CYCLES`. A two-cycle engineering run was shown as `MAX_CYCLES_NONCONVERGED / NOT_CONVERGED`. A cancelled serial curve retained its partial manifest. Experimental V2/MUSCL identifiers were absent from the tested synthetic project and run artifacts.

## Blocking defect

The A/B parallel preflight passed for three workers and four points. Windows multiprocessing spawned the packaged `Dino2T.exe --multiprocessing-fork`, which opened a second default GUI instead of entering the process worker. The dispatch manifest stayed `RUNNING` with all four points `NOT_STARTED`; no A/B results were produced. A resume attempt from a zero-cycle cancellation failed closed; that interruption had no complete cycle checkpoint, so recovery was not proven.

The source fix calls `multiprocessing.freeze_support()` before importing the Desktop GUI. It is committed in the repository, but this acceptance used the single allowed build; the candidate ZIP therefore remains failed and does not contain the fix. No rebuild was performed.

The synthetic execution is only a packaging/integration check. Experimental validation and predictive claims remain unavailable; V2 and MUSCL remain experimental.

Full hashes and test details: `receipt.json`.
