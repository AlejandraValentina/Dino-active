# Independent contract and regression review

Reviewer: `/root/contract_review`  
Review mode: `INDEPENDENT_REVIEW`, read-only  
Reviewed source: `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`  
Official main reference: `5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`  
Pre-4T regression baseline: `e95db4c`

No source, tests, expected values, thresholds, contracts, Git references, status records or original scientific artifacts were modified. All review-generated files are outside the repository. The reviewed worktree remained clean.

## Technical conclusion

No new 2T physical or numerical regression was demonstrated in this review. The 2T physical kernels, protected P4–P8 tests, associated OpenSpec contracts and historical orchestration code are unchanged between the pre-4T baseline and `main`. The A/B branch adds no changes to those 2T physical kernels or tests.

The clean-checkout regression invocation is nevertheless **not green**: it produced **5 failed, 296 passed, 3 skipped**, with four warnings. All five failing node IDs appear in the recorded historical set of 115 failures. Their failure mechanisms were missing or unconfigured historical artifacts, not differing numerical assertions. Focused rechecks resolved all five when the exact existing artifact context was explicitly provided.

This supports “no newly demonstrated 2T regression in the reviewed scope.” It does not support a self-contained clean-checkout PASS, a repository-wide PASS, or experimental validation.

## Executed verification

The required 26-file P4–P8 suite was run at the frozen A/B revision using:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$testFiles = Get-ChildItem `
  tests/test_p4_*.py,tests/test_p5*.py,tests/test_p6*.py,`
  tests/test_p7*.py,tests/test_p8*.py,tests/test_two_stroke_ports_p5c.py |
  Sort-Object FullName -Unique |
  ForEach-Object { $_.FullName }

python scripts/agents/run_logged.py `
  --name p4-p8-independent-audit `
  --out <external-review-root>/p4-p8 `
  --timeout 600 -- `
  python -m pytest @testFiles -q -p no:cacheprovider
```

Results and diagnostic rechecks:

| Invocation | Result | Logged duration |
|---|---|---:|
| Clean pinned worktree, no external artifact root configured | 5 failed, 296 passed, 3 skipped, 4 warnings | 119.172 s |
| Only the three initially failing G2 tests, with verified `DINO_ARTIFACT_ROOT=E:/Dino-artifacts` | 2 passed, 1 failed because an additional historical path was relative to the checkout | 90.656 s |
| Only the two initially failing R13A tests, frozen test paths with preserved original checkout as read-only artifact cwd | 2 passed | 0.859 s |
| Only the remaining historical G2 comparison, explicitly pinned frozen runtime and original read-only artifact cwd | 1 passed | 11.375 s |

These are **301 distinct passing tests and three remaining conditional skips across explicitly different artifact contexts**, not a single clean-checkout execution with 301 passes. The initial failure records were preserved.

The external G2 artifact resolver verified all **56 registered artifacts** by registered byte size and SHA-256. The final historical G2 recheck logged the SHA-256 of its 20 original checkpoints and compared their state and cell arrays exactly with the hash-bound reacquisition.

The source modules were explicitly pinned in the final historical-context invocation, which asserts that both `motorsim.artifact_store` and `dev_orchestrator.p4_g2_v2_offline_audit` load from the frozen `8b371e2` worktree. No solver campaign was started.

### Exact initially failing nodes

All are present in `results/dino4t-stage2-v1/audit/preexisting_failures_at_e95db4c.txt`:

```text
tests/test_p4_g2_v2_recovery.py::test_new_durable_acquisition_reaudits_without_producer_pass
tests/test_p4_g2_v2_recovery.py::test_reacquired_terminal_states_match_historical_run_exactly
tests/test_p4_g2_v2_recovery.py::test_r2_real_closing_checkpoint_false_dt_cannot_pass_after_hash_update
tests/test_p4_r13a.py::R13ATests::test_cycle56_is_compared_against_replayed_cycle54
tests/test_p4_r13a.py::R13ATests::test_replay_gate_and_cycle56_result
```

The historical inventory contains **115 entries: 83 FAILED and 32 ERROR**. No initially failing node from this review is outside that inventory. The entire current general suite was not rerun, so equality of the complete current failure set with the historical set is not independently asserted.

### Conditional skips

The three clean-worktree skips follow existing test code and missing optional historical artifacts:

- `P4R10ATests::test_cycle_labels`
- `P4R10ATests::test_plateau_vs_adjacent`

  Both require `results/p4-r10a-20260922/front_tracking_corrected.json`; see `tests/test_p4_r10a.py:127` and `tests/test_p4_r10a.py:139`.

- `P4R9SyntheticTests::test_original_metric_reconstruction`

  Requires `results/p4-r9-20260922/sensor_tables.json`; see `tests/test_p4_r9.py:81`.

These skips remain disclosed. Their historical expected values were not changed or reconstructed.

## Findings

### CR-01 — P1 operational assurance: the protected regression closure depends on two artifact access conventions

**Confirmed.**

The clean frozen worktree cannot reproduce the complete protected regression result with the ordinary documented pytest invocation.

Three tests initially stop because `motorsim/artifact_store.py:60` requires an explicit `DINO_ARTIFACT_ROOT`, and the clean invocation has none. Setting the existing, verified external root resolves the durable-acquisition audit and the adversarial false-time-step rejection.

The third G2 test also directly reads historical checkpoints through a checkout-relative path at `tests/test_p4_g2_v2_recovery.py:466`. That path bypasses the external artifact resolver. The two R13A tests likewise directly read checkout-relative JSONs at `tests/test_p4_r13a.py:12` and `tests/test_p4_r13a.py:17`.

**Scientific impact:** no differing physical or numerical result was observed. In fact, the durable audit and adversarial mutation rejection passed with the original registered artifacts.

**Operational impact:** a clean checkout cannot independently reproduce the aggregate protected assurance without knowledge of the original checkout and external storage layout. This is a reproducibility barrier for a clean-source release gate.

**Residual requirement:** a future clean-source assurance process must make these existing artifacts and access conventions explicit and reproducible, while preserving historical bytes and protected tests. The contextual rechecks in this audit must not erase the initial failures.

### CR-02 — P2 assurance coverage: the historical “115 failures” inventory is a scoped baseline, not a waiver for subsequent platform changes

**Confirmed limitation.**

`docs/dino4t/stage2_assessment.md:273` describes a full-suite comparison against `e95db4c`, with 115 identical failures and no new failures from the foundation work. Its stored inventory lists node IDs. The main consolidation report explicitly states that the full suite was not rerun, instead reporting focused integration and Stage 2 suites; see `results/dino-platform-consolidation-v1/verification/consolidation-report.md:21`.

Since `e95db4c`, `main` contains additional Desktop, design-study, project and routing changes. The historical list therefore cannot establish the absence of all current integration regressions. It can identify known failures, as it did for the five nodes examined here.

**Residual requirement:** future changes must classify failures by exact node ID and cause against an appropriate pinned base. Unrelated historical failures must remain visible, and newly failing nodes cannot be exempted merely by citing the number 115.

This review did not rerun the full general suite or reproduce the previously documented Qt access violation in `tests/test_external_data.py`.

### CR-03 — P2 scientific provenance: some 4T sensitivity studies are not exactly reproducible by commit

**Confirmed and already disclosed by the project.**

`results/dino4t-stage2-v1/PROVENANCE.md:18`–`24` explicitly records that S2/S3/S4 were produced from an uncommitted working tree, some studies omit `code_dirty`, and exact commit reproduction is not guaranteed. The same document distinguishes the clean regenerated examples from these study outputs.

This is not evidence that the study numbers are wrong. It limits the assurance that can be assigned to those studies and their suitability as decisive fixtures for future scientific gates.

**Residual requirement:** preserve these studies with their existing qualification. Do not upgrade them into exact-source reproducible gate evidence without additional source identity or a separately authorized versioned verification.

### CR-04 — P2 interpretation of test counts: legacy regression assertions are not equivalent to independent physical verification

**Confirmed limitation.**

For example, `tests/test_p4_r13a.py:5`–`18` contains structural assertions and checks of stored `exact`, `passed` and sensor-summary values. Passing these tests confirms consistency with the historical contract, not an independent reconstruction of the physical trajectory.

The stronger G2 durable audit at `tests/test_p4_g2_v2_recovery.py:456` and adversarial mutation test at `tests/test_p4_g2_v2_recovery.py:481` provide materially different evidence and passed in the configured original artifact context.

Counts of historical regression tests must therefore remain separate from counts of numerical verification cases, physical model validation cases and blind experimental comparisons.

## Confirmed safeguards

### Frozen P9 content is preserved

Both the `main` and `8b371e2` Git blobs of:

```text
openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md
```

have SHA-256:

```text
79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d
```

The Windows working file has CRLF line endings. Its raw byte hash is:

```text
b72efd6734cdaa076ff7027f3158d100a60337cead7ed44b580abaf7cbe80d08
```

Normalizing CRLF to LF reproduces the frozen hash exactly. This is the canonicalization explicitly implemented in `scripts/agents/program_status.py:216`; it is not evidence corruption.

### Integration has not rewritten the protected 2T physical kernels

Git comparisons between `e95db4c` and `main` showed no changes in the selected 26 P4–P8 test files, protected P0–P9 OpenSpec paths, `dev_orchestrator`, or `docs/gasdynamic`.

For `motorsim`, the integration additions outside the independent `dino4t` package are in Desktop, project/platform infrastructure and design-study components. Excluding those application areas leaves no changed 2T physical runtime files. The A/B branch similarly does not alter those 2T kernels or protected tests.

This establishes source preservation through the integration scope. It does not prove every historical scientific result under every new environment.

### Scientific claims remain appropriately limited

The historical P8 evidence is explicitly described as `BOUNDED_TRANSIENT_INDICATED`, with `steady_state=false`, periodic convergence not granted by P4, and no experimental validation; see `docs/gasdynamic/p9_readiness_contract_reconstruction_20261001.md:35`.

The 4T provenance document labels its data numerical verification and engineering studies with synthetic parameters, not validation or prediction. Older foundation results using the defective V1 boundary are explicitly historical and unsuitable for use; see `results/dino4t-stage2-v1/PROVENANCE.md:3`.

The 2T P9 obligations cannot be inherited by the 4T model, and functional Desktop acceptance cannot establish either model’s predictive validity.

## Reproducible review artifacts

External review root:

```text
C:/Users/ageribon.MIDES/Dino-artifacts/dino-platform-audit-v1/contract-review/
```

Machine-readable integrity receipt:

```text
contract-integrity.json
SHA-256:
654b828e8b00a36f91637982b1b0a1a12ce734e3eebefa4d55bdfb458dd905b7
```

It records source pins, P9 raw/canonical hashes, selected test modules, exact historical-failure mapping, context qualifications and hashes of the logs.

The `p4-p8/` subdirectory contains these four complete log/summary pairs:

```text
p4-p8-independent-audit
p4-g2-failed-context-restored
p4-r13a-failed-historical-context
p4-g2-historical-context-final
```

Initial full-suite log SHA-256:

```text
077a3d9d5eb1ff6593e5776570ada9d55b07197e70297c29b57df8d52458a941
```

Initial full-suite summary SHA-256:

```text
95f979217b11349aff7540fec39fb07eb52ef75b86e157f47e5de884d7018a44
```

The initial failures and subsequent contextual successes are separate retained observations. No historical gate is retroactively reinterpreted by this review.
