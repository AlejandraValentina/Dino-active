# Dino 4T A/B — Windows candidate acceptance

**Result:** PASS for internal TRIAL. This does not authorize publication or a stable release.

## Candidate identity

- Version: `0.1.0-rc12`
- Source commit: `07849322b8ad0115defb28de2ad5f23b8bfacd55`
- Build: `20261105T152851Z` on `Windows-10-10.0.19045-SP0` (`AMD64`)
- Package ZIP: `C:\Users\ageribon.MIDES\Dino-artifacts\Windows\MotorSim-0.1.0-rc12-windows-x64-07849322-trial-20261105T152851Z.zip`
- ZIP SHA-256: `aa0992b08514c996ca8191e863387260fee964dfcd2aff19d6582a4bdc997e03`
- EXE SHA-256: `89852dd681b0620380114ab8232649f9008a5d11cd1cb34e69d63458bc9e04d2`
- Clean packaged-input manifest SHA-256: `cc2b065d5902f1942376efe00f6734e91a25a86f64dbaf4b1f5d89d85f1fd602` (255 files)

## Verified in the packaged EXE

- Opened the saved 4T project with its two hash-bound result endpoints.
- Reproduced the strict exact-6000-RPM A/B comparison, including periodic qualification and the explicit caveat that computed differences are not experimentally validated.
- Exported JSON, CSV and HTML. The JSON retained the comparison ID; CSV retained full precision and both result hashes; the HTML retained the scientific caveat.
- Reused one actual packaged cancellation record (`cancelled_by_user`, two cycles, `incomplete`, `NOT_CONVERGED`). The process returned from cancellation; no `MotorSimWorker.exe` remained. A fresh packaged process reopened the saved A/B project and compared the periodic endpoints again. No second solver run was started for recovery verification.
- In the same packaged process, opened the existing 2T exhaust-comparison project, routed the 4T project into the 4T workspace, then returned to the 2T project. No solver runs were started in this compatibility check.
- Visual evidence: 4T comparison at 1360×900 and reopened comparison at 980×680; 2T model at 1360×900.

## Source checks

- Focused 4T A/B/Desktop regressions: 38 passed.
- 2T Desktop/project/example regressions: 34 passed, 1 skipped.
- Dino 4T Stage 2 regressions: 28 passed.
- These source tests complement, and do not substitute for, the packaged EXE checks above.

## Scientific status and limits

The two source A/B endpoints are real solver calculations with one preregistered design delta (`intake_valve.lift.max_lift_mm`: 10 → 8), both at 6000 RPM and equivalence ratio 1.0. The inputs are labeled `SYNTHETIC_ASSUMPTION`; the comparison is `PERIODIC_MODEL_SENSITIVITY_ONLY`. Experimental validation was not performed, and Dino's predictive capability is **not claimed**. The packaged cancellation smoke is incomplete and remains nonconverged; it is lifecycle evidence only.

The candidate archive remains at the external path above. It was not published. The sole package build used source commit `07849322b8ad0115defb28de2ad5f23b8bfacd55`; no rebuild was made during acceptance.

See [`candidate-acceptance.json`](candidate-acceptance.json), the two packaged acceptance receipts, and the captured images/exports in this directory for machine-readable evidence.
