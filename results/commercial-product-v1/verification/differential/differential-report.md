# CP1 differential regression audit

- Baseline: `48b3afe` (fresh worktree, full suite, JUnit).
- CP1: `d44305c` (full-suite log from `c4fe6a2`; clean CP1 worktree subset with JUnit).
- Baseline failures: 146 (89 failures, 57 errors); 3669 passed; 10 skipped.
- CP1 full failures: 145 (89 failures, 56 errors); 3692 passed; 10 skipped.
- CP1-only failures (regressions): **0**.
- Baseline-only outcomes that pass in isolation on CP1: **9** (order/fixture-sensitive).
- Common failure causes are identical for all 137 common failures.

## Verdict
**NO_CP1_REGRESSION_DETECTED; GENERAL_REGRESSION_NOT_GREEN**

## Inherited failure classification

- `inherited_frozen_evidence_or_source_hash_mismatch`: 43
- `inherited_frozen_source_dependency_mismatch`: 17
- `inherited_missing_external_artifact`: 43
- `inherited_missing_local_fixture`: 24
- `inherited_product_defect_candidate`: 1
- `inherited_test_expectation_drift`: 4
- `inherited_test_expectation_or_frozen_message`: 5

## External view incident
- `tests/test_external_data.py::test_import_confirm_roundtrip_unknown_conditions_and_previous_preserved` crashes with Windows access violation at `motorsim/external_view.py:88` on **both** 48b3afe and CP1.
- Retained as an independent inherited incident; not fixed in this audit.

## Reproducible commands
```powershell
# Baseline (main 48b3afe)
python -m pytest tests --ignore=tests/test_external_data.py --tb=line -q -p no:cacheprovider --junitxml=...\main-48b3afe.junit.xml

# CP1 failing-ID subset (clean worktree)
python E:\dino\tmp\run_cp1_failure_subset.py baseline_failures_normalized.json cp1-clean-failures.junit.xml

# External view incident on either commit
python -m pytest tests/test_external_data.py -q -p no:cacheprovider
```
