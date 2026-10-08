# Post-migration regression comparison — 2026-10-08

Scope: compare the active checkout at migration baseline `93a03f4cff1be266ae2538c80da651d2904da864` with read-only historical anchor `a3d518e2d736de84d82595f674789d4547baac4e`. This audit restores missing migration evidence and tests; it does not reopen or change a scientific gate.

## Collection and imports

Same Python 3.11 environment and pytest command, with bytecode/cache writes disabled:

| Checkout / command | Result |
|---|---|
| Historical, `python -m pytest --collect-only -q -p no:cacheprovider`, no `PYTHONPATH` | 1129 tests collected, 8 collection errors (`ModuleNotFoundError` for test-to-test imports such as `test_reference_results`) |
| Historical, same command with `PYTHONPATH=tests` | 1205 tests collected |
| Active, same command with no `PYTHONPATH` | 1210 tests collected, including 5 artifact-store tests |

The active checkout adds `pytest.ini` with `pythonpath = tests`; it fixes the inherited test-import issue through standard test configuration and does not alter product imports.

## Windows UI failure

`tests/test_external_data.py::ExternalWindowTests::test_import_confirm_roundtrip_unknown_conditions_and_previous_preserved` was run in both checkouts under the same Windows/Python/Qt environment. Both terminate with the same fatal Windows access violation in `motorsim/external_view.py:88`, through `ExternalDialog.import_csv` (`external_view.py:231`) at `tests/test_external_data.py:230`. The test exercises the offscreen Qt UI. Classification: `PREEXISTING_NON_MIGRATION_TEST_BLOCKER`; no UI redesign or migration-specific fix was made.

## Existing failures compared against history

Each listed failure was run by node ID in both checkouts and reproduced in the historical checkout with the same underlying reason:

| Test / behavior | Historical result | Classification |
|---|---|---|
| P8 committed-evidence consistency | `closure_ok=False` | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| P0 only-enabled configuration | Other phase flags already enabled | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| P1 dependency acceptance | P2 is enabled in the historical phase config | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| P1-R4 frozen implementation | `implementation_contracts_frozen=False`; other three checks true | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| P1-R5 offline/review | Recorded source hashes differ from current solver hashes | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| P2B resume reuse | Stale source hashes in historical checkpoint; 3 affected cases | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| Roadmap supervisor `test_status` | Returns `ROADMAP_NO_ACTIVE_TASKS`, so expected `P5_B` is absent | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| CAE invalid-RPM draft preservation | Existing UI state assertion fails identically | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |
| `RegularizationTests.test_local_discharge_and_physical_fill` in broad order | Fails at the same point in both broad runs; the module passes 5/5 in isolation in active | `PREEXISTING_TEST_INFRASTRUCTURE_DEFECT` |

Together with the fatal UI case, these 20 node IDs were excluded from the broad migration-regression run after their historical failures were confirmed. The broad run also skips two tests marked skip by the suite itself.

## Migration regressions found and repaired

The broad run uncovered evidence present at the historical anchor but absent from the active checkout. Compact receipts, summaries, P8/P9/P1 evidence and test fixtures were restored byte-for-byte where they are small. Large inputs were placed in `E:\\Dino-artifacts` and registered by relative path, size and SHA-256. The affected direct consumers now resolve and verify the registered artifacts instead of reading from the historical repository. This included the four R2 primaries, P0/low-RPM references, GUI point-02 and performance samples, the two AUD-15 Fixture D cycle dumps, P2B resume cases, and the 50-cycle G2-v2 recovery checkpoint set. Missing P4-R10, P4-R12, P4-R13A, P4-SCI-04A/04B and P2B summaries/receipts were restored from the historical checkout.

The affected modules were rerun after repair: AUD-15 2/2, E13-R1 6/6, P1-R4 gate 7/7 (with the single historical frozen-hash case excluded), P4-G2-v2 recovery 58/58, P4-R10 7/7, P4-R12 4/4, P4-R13A 5/5, P4-SCI-04A 8/8, P4-SCI-04B 8/8, artifact-store tests 5/5, and focused consumers of R2/low-RPM/GUI external artifacts 3/3. The P2B changed-input signature test passes after restoring its historical fixture; the three stale-checkpoint tests remain historical failures.

The final broad active run reached 1003 passes, 4 skips and the same order-dependent regularization failure seen in the historical run (1002 passes, 4 skips). The test module passes 5/5 in isolation in active. The remaining segment from `test_scavenging_partition_v1.py` onward passed 162/162, and focused R2, low-RPM, GUI, and artifact-store consumers passed with `DINO_ARTIFACT_ROOT` configured. Earlier broad runs stopped at missing historical fixtures; each was restored or moved behind the verified artifact store and its affected module rerun. No active-only failure remained after the historical fixture gaps were repaired. The broad command stops on the shared order-dependent regularization failure, so the downstream segment was run separately.

## Conclusion

No remaining observed difference is an active-only regression. The active checkout collects without a manual `PYTHONPATH`, has the expected external-artifact boundary for R2, and reproduces the compared historical test failures. Remaining limitations are the explicitly listed pre-existing Windows/UI and stale-contract test failures.
