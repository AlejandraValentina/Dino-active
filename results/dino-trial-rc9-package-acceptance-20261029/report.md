# Dino Desktop rc9 Windows TRIAL acceptance

**Decision: READY_TRIAL.** The localized frozen Windows spawn defect is corrected in the only rc9 build and passes the packaged-executable acceptance. This does not promote rc9 to stable or support a predictive claim.

## Package

- Version: `0.1.0-rc9` TRIAL.
- Folder: `C:\Users\ageribon.MIDES\Dino-artifacts\Windows\MotorSim-0.1.0-rc9-windows-x64-9ef35834-trial-20261029T113419Z\MotorSim`
- ZIP: `C:\Users\ageribon.MIDES\Dino-artifacts\Windows\MotorSim-0.1.0-rc9-windows-x64-9ef35834-trial-20261029T113419Z.zip`
- SHA-256: `3ca5caa395ee943783abfd876f7b852b8f3041190fc4a2989ddc1595ae180841`
- ZIP integrity: 325 entries, `testzip=None`.
- Source commit: `9ef35834f62a5482a5d302c053c03045ba2769d6`; build manifest marks `source_dirty=True` because unrelated workspace changes were preserved. The runtime code change was committed separately as `9ef3583`; source fix is `4794b78`.
- Exactly one build was generated. rc7 and failed rc8 archive hashes were checked and remain unchanged.

## Packaged executable results

- `multiprocessing.freeze_support()` executes in `packaging/dino_desktop_entry.py` before importing `motorsim.dino_desktop`/PySide6. The PyInstaller spec points the GUI executable at that entrypoint. Focused ordering and distribution tests passed.
- The main process opened one Dino window. Three packaged spawn children appeared during the A/B dispatch as `Dino2T.exe --multiprocessing-fork`, with no windows; they exited at terminal completion. The dispatch configured two pool workers plus the coordinator's Manager process.
- A/B synthetic run `592d2201a474445fa1f1defb7a8e89b4` completed all four points (base and `RC9 synthetic exhaust B`, 4500/5000 RPM) in 14.703 s with two pool workers. Each result has a checkpoint and result hash. Each is labeled `MAX_CYCLES_NONCONVERGED / INSUFFICIENT_CYCLES`; no one-cycle result was presented as periodic.
- Parallel cancellation run `4de8c735665841c0989e784b36b3cf74` reached terminal `PARTIAL` in 4.031 s. All four points became `INTERRUPTED_CHECKPOINTED / CANCELLED_CHECKPOINTED` at zero complete cycles. All workers exited; no orphan remained.
- Serial checkpoint test `a7e171c6993340ebac7906f87618e33b` was cancelled after a valid cycle-1 checkpoint, then resumed through Desktop history and completed cycle 2. The run record has two invocations; final classification is `MAX_CYCLES_NONCONVERGED / NOT_CONVERGED`. Serial execution remained functional.
- Run `8c061528e4fc4a29876498fdc6363695` was cancelled at zero cycles with no `checkpoint.json`. Desktop history disabled **Reanudar checkpoint…** for that row. Screenshot: [desktop-no-checkpoint-resume-disabled.png](desktop-no-checkpoint-resume-disabled.png).
- The runs are `EXPLORATORY`, `SYNTHETIC_UNVALIDATED`, and `NOT_CLAIMED` scientifically. Existing synthetic `GAS_EXCHANGE_V2` geometry schema remains explicit; the separate experimental ideal-nozzle port-connection V2 candidate and MUSCL reconstruction were not selected. The run artifacts show no spatial method selector or MUSCL reconstruction source hashes. No experimental model was silently enabled by the package.

## Pre-build and focused tests

- Storage preflight: PASS for 1.5 GiB artifact plus 1 GiB build work, preserving a 2 GiB reserve; estimated headroom after those estimates was 15,280,058,368 bytes.
- Environment: Windows 10 x64, Python 3.11.0, PyInstaller 6.22.3, PySide6 6.11.2.
- Distribution/entrypoint focused tests: 4 passed.
- Desktop dispatch/checkpoint/cancel focused tests: 4 passed.
- Packaged ZIP integrity: PASS; post-run C: free space was 17,752,457,216 bytes.

## Scientific status and next step

Windows dispatch integration is closed. rc7 remains the functional baseline. Experimental validation is still blocked by incomplete matched-engine geometry and independent measured outputs; periodic GCI remains blocked by its approved remaining budget. Return to the unified predictive-reliability roadmap for the next authorized, unblocked task; do not reopen packaging investigation without a reproduced defect.

Full manifest paths, hashes, process evidence, build provenance, and state details are in [receipt.json](receipt.json).
