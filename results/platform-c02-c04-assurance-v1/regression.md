# C02/C04 verification record

- C02/C04 new tests: 4 passed.
- C01/C03 + API/A-B/Desktop focused: 74 passed.
- Stage2: 28 passed.
- C01/C03 artifact/provenance/packaging: 56 passed.
- F10 protected recipe with explicit context:
  `DINO_ARTIFACT_ROOT=E:/Dino-artifacts`,
  `python -u results/platform-c01-c03-remediation-v1/verification/run_protected_regression.py E:/dino/Dino-active`
  → **301 passed, 3 skipped** (4 NumPy deprecation warnings).
- A2-13 source acceptance: PASS (see `a2-13-acceptance.md`).

No build, package, merge, push or scientific campaign was performed.
