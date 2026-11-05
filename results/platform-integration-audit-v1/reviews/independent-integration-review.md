# Independent integration review — Dino 2T/4T

Reviewer: `/root/integration_review`, read-only independent agent.  
Reviewed revisions: `main=5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`; A/B branch `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`.  
Classification: `INDEPENDENT_REVIEW`, limited to Desktop integration, artifact integrity, packaging and assurance evidence.

No product files, history or historical evidence were modified. All fixture writes occurred in external temporary directories. Git status remained clean in the reviewed worktree. No solver campaign or Windows build was executed.

## Verdict

The available evidence supports a functioning integrated Desktop and an implemented, exercised 4T A/B workflow on the A/B branch. It does **not** support an unqualified claim of scientific data integrity or reproducibility across the complete workflow.

Five P1 defects were confirmed with bounded probes or directly falsifiable source/manifest checks. They concern silent modification of engineering inputs, unbound pressure traces, stale scientific displays, incomplete package input accounting and incomplete source dirty detection. None requires a change to physical equations to resolve.

No P0 data loss or numerical solver corruption was demonstrated. The historical successful GUI runs remain evidence of the particular paths exercised; they do not cover the negative cases below.

## Revision attribution

`main` is the ancestor of the A/B branch. The strict comparison implementation, comparison exports, actual two-design A/B evidence and cooperative cancellation changes are branch-only additions. They must not be attributed to current `main`.

The A/B evidence has three distinct source identities:

- Actual A/B source simulations: `cb8f356aa616ebaa2e5ebb110a89e6edd40c0ff3`.
- Packaged candidate source: `07849322b8ad0115defb28de2ad5f23b8bfacd55`.
- Evidence/acceptance closure: `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`.

This distinction is legitimate and recorded, but should remain explicit in any consolidated assurance claim.

## Confirmed findings

### INT-01 — P1: applying the 4T editor silently rounds untouched input values

Anchors:

- `motorsim/desktop/four_stroke_desktop.py:202`: floating values rendered with `.12g`.
- `motorsim/desktop/four_stroke_desktop.py:207`.
- `motorsim/desktop/four_stroke_desktop.py:211`: Apply parses and rewrites every displayed value, including untouched cells.

A valid configuration with `geometry.rod_mm=180.12345678912345` was opened in `FourStrokeConfigEditor`, then Apply was invoked without editing any cell.

Observed:

```text
NOOP_EDITOR {
  "before": 180.12345678912345,
  "after": 180.123456789,
  "identity_changed": true
}
```

This changes the actual solver configuration, not merely presentation precision. It is present in both `main` and the A/B branch. Existing export precision tests do not cover this input round trip.

Required assurance: an untouched editor Apply must preserve the original configuration and identity exactly; only explicitly modified cells may alter inputs.

### INT-02 — P1: pressure traces are not bound to their original result provenance

Anchors:

- `motorsim/desktop/four_stroke_desktop.py:348`: `_read`.
- `motorsim/desktop/four_stroke_desktop.py:349`: summary hash verification.
- `motorsim/desktop/four_stroke_desktop.py:355`: resolved configuration validation.
- `motorsim/desktop/four_stroke_desktop.py:416`: pressure trace read from mutable metadata path.
- `motorsim/desktop/four_stroke_desktop.py:467`: comparison computes the current trace hash, without checking an original expected trace hash.

The reader verifies summary bytes and canonical configuration identity. It does not verify an original trace digest, or bind mutable `run.json` trace/config/summary paths and identity metadata to the project reference.

A genuine accepted A summary and resolved configuration were copied to a temporary artifact directory. Their hashes were preserved. The copied trace was replaced by an explicitly artificial constant 42-bar cylinder trace. The reader accepted it as a verified periodic run and plotted it.

Observed:

```text
TRACE_TAMPER {
  "loaded": 1,
  "history": "6000 rpm · Periódico · Motor base",
  "plotted_cylinder_bar": 42.0,
  "summary_digest_preserved": true
}
```

This is not a speculative malicious-input concern: accidentally replacing or redirecting a trace can silently associate the wrong scientific curve with a verified summary. `curve_binding_sha256` is likewise consumed from mutable metadata rather than recalculated by `_read`.

Present in `main` and the A/B branch.

Required assurance: preserve original artifact hashes and validate the summary/configuration/trace/metadata relationship before plotting or exporting a “verified” endpoint.

### INT-03 — P1: an unverifiable history selection leaves previous scientific data visible

Anchors:

- `motorsim/desktop/four_stroke_desktop.py:360`: `refresh`.
- `motorsim/desktop/four_stroke_desktop.py:361`: clears history and loaded endpoints.
- `motorsim/desktop/four_stroke_desktop.py:391`.
- `motorsim/desktop/four_stroke_desktop.py:392`: early return for an index absent from `loaded`.

Probe:

1. Loaded the actual accepted two-run A/B project.
2. Changed the in-memory summary-reference paths to a nonexistent external file.
3. Called `refresh`, without altering any historical artifact.

Observed:

```text
BEFORE {
  "loaded": 2,
  "summary_rows": 44,
  "pressure_series": 3
}

AFTER {
  "loaded": 0,
  "selected_history": "Fuente no verificable · ... No such file or directory ...",
  "summary_rows": 44,
  "pressure_series": 3,
  "first_metric": "Trabajo neto por ciclo",
  "first_value": "592.544"
}
```

The selected history row correctly reports the broken source, but the metric table and pressure graph still show the previous result. A user can therefore associate stale scientific data with an unverified selection.

Present in `main` and the A/B branch.

Required assurance: source failure, empty selection and project/history refresh must clear or explicitly invalidate all result details and traces.

### INT-04 — P1: a consumed 4T package input is absent from the clean-input manifest and guard

Anchors:

- `packaging/MotorSim.spec:27`: bundles `configs/dino4t/example_single_cylinder_500cc.json`.
- `packaging/build_provenance.py:10`: packaged input enumeration.
- `packaging/build_provenance.py:13`.
- `packaging/build_provenance.py:15`.
- `packaging/build_provenance.py:59`: clean-input Git scope excludes `configs/dino4t`.
- `packaging/build_provenance.py:75`: same omission in the “unrelated dirty” classification.

Observed on the actual reviewed checkout:

```text
MANIFEST_OMISSION {
  "consumed_by_spec": true,
  "present_in_manifest": false,
  "manifest_sha256":
    "cc2b065d5902f1942376efe00f6734e91a25a86f64dbaf4b1f5d89d85f1fd602",
  "count": 255
}
```

A minimal external Git fixture was committed, then only its identically named 4T example configuration was modified. The actual guard accepted it:

```text
PACKAGING_DIRTY_SCOPE {
  "root_status": "M configs/dino4t/example_single_cylinder_500cc.json",
  "ensure_packaged_inputs_clean": "accepted",
  "fingerprint": {
    "source_dirty": true,
    "unrelated_dirty_entry_count": 1
  }
}
```

Therefore a TRIAL build can consume changed 4T example/validator input while claiming all packaged inputs match the named commit. A before/after manifest comparison will not detect a change to this omitted input.

This flaw exists in `main` and the A/B branch.

Important qualification: I inspected the actual accepted A/B ZIP. Its example configuration is semantically identical to the configuration in commit `07849322`. The byte difference versus the Git blob is CRLF/LF only. This finding does **not** demonstrate contaminated content in that existing candidate; it demonstrates that the build guard’s completeness claim is false.

### INT-05 — P1: source `code_dirty=False` can exclude modified shared numerical dependencies

Anchors:

- `motorsim/dino4t/runner.py:48`.
- `motorsim/dino4t/runner.py:58`: Git status is scoped to `"."` with working directory `motorsim/dino4t`.
- `motorsim/dino4t/kinematics.py:12`: imports `motorsim.kinematics`.
- `motorsim/dino4t/duct.py:29`: imports `motorsim.gas1d.mesh`.

An external miniature Git fixture was committed with a `motorsim/dino4t` subtree and a shared `motorsim/kinematics.py`. The shared dependency was modified. With the runner’s `__file__` pointed to the fixture’s equivalent directory, the actual `_git_dirty` function reported:

```text
SOURCE_DIRTY_SCOPE {
  "root_status": "M motorsim/kinematics.py",
  "reported_4t_code_dirty": false
}
```

A clean commit therefore does not always identify all source code influencing a source-run result, despite `code_dirty=False`.

This is a foundation/main issue, not introduced by the A/B branch. The A/B pair was run from an otherwise clean isolated checkout, so this probe does not demonstrate that the stored pair was produced from modified shared code.

Required assurance: dirty/provenance accounting must include the actual transitive numerical dependencies or a complete protected source manifest.

## Additional defects and assurance limits

### INT-06 — P2: A/B evidence is tied to one filesystem location and EOL policy

Anchors:

- `results/dino4t-ab-engineering-v1/runs/dino4t-synthetic-ab-v1.dino.json:221`, `:230`: absolute source-worktree paths.
- Each `runs/.../run.json:11–13`: absolute summary/configuration/trace paths.
- `motorsim/engine_project.py:141–143`: only explicit `./` project references are rebased; internal metadata paths are not.
- `.gitattributes`: no byte-preservation/EOL rule for the new A/B evidence subtree.

The accepted packaged A/B test loads data from the original source worktree. Copying the study/project tree to another machine or location is insufficient without a documented rebinding procedure; even rebasing the outer project reference leaves absolute configuration and trace metadata.

All 16 Windows evidence hashes currently pass in both the original worktree and the newly created audit worktree under `core.autocrlf=true`. However, only the three PNG Git blobs match the recorded raw hashes. The thirteen textual Git blobs use LF whereas the recorded original bytes use CRLF. A checkout with `core.autocrlf=false` will not match those raw-byte receipts.

This is not corruption of the current Windows evidence. It is an unresolved portability/preimage requirement. Preserve the original receipts and document any reconstruction; do not silently rewrite historical hashes.

### INT-07 — P2: build metadata advertises a legacy 4T model identifier

Anchors:

- `packaging/build_windows.py:79`: takes `FOUR_MODEL_VERSION` from the legacy `reference_results`.
- `results/dino4t-ab-engineering-v1/windows/build.json:28`:

```text
three-cv-0d-prescribed-heat-720-v1-external-regularized-rk4-v1
```

- `motorsim/dino4t/__init__.py:9`: native API model is `DINO4T_FOUNDATION_V1`.
- Native result `models` identify the actual two-zone/SSPRK2/quasi-1D formulation.

This does not demonstrate the wrong solver was executed. It makes the package’s `models.four_stroke` field scientifically misleading and inconsistent with native runtime results. The legacy and native implementations must be named separately if both remain in the bundle.

### INT-08 — P2: pressure traces inherit the “RPM” horizontal-axis label

Anchors:

- `motorsim/desktop/four_stroke_desktop.py:424`: pressure series specify `x_key="theta"` but no `x_label`.
- `motorsim/desktop/plot.py:80`: defaults `x_label` to `"RPM"`.

The data are crank-angle samples, while the common plot labels the horizontal axis RPM. This is present on both revisions. The existing screenshot acceptance focused on comparison tables, so it does not falsify this issue.

Required assurance: pressure plots must explicitly identify crank angle and its unit, independently of performance-curve defaults.

### INT-09 — P2: cancellation/recovery evidence has a narrower meaning than “worker cleanup and resume”

Anchors:

- `motorsim/desktop/four_stroke_desktop.py:231`: `_RunTask(QRunnable)`.
- `motorsim/desktop/four_stroke_desktop.py:266`: runs through the GUI process’s `QThreadPool`.
- `docs/dino4t/integration_contract.md`, execution section: recommends one point per separate process; concurrent use in threads is unverified.
- `tests/verify_dino4t_ab_windows.py:214–216`: checks absence of `MotorSimWorker.exe`.

4T execution does not use `MotorSimWorker.exe`; checking its absence does not establish cleanup of the actual 4T task. The observed complete-cycle return and eventual EXE termination remain useful lifecycle evidence.

The resumed acceptance path opens a fresh process and reloads already saved periodic A/B endpoints. It does not resume the cancelled numerical state or reload the cancelled history from the same artifact root. Documentation appropriately states that no serializable 4T checkpoint exists. Keep this qualification in planning and acceptance language.

The thread/process contract difference is an architectural risk, not a demonstrated concurrency numerical failure. No concurrency campaign was performed.

### INT-10 — P2: acceptance receipts can be written PASS before shutdown verification finishes

Anchors:

- `tests/verify_dino4t_ab_windows.py:242`: writes PASS receipt.
- `tests/verify_dino4t_ab_windows.py:249`: only then closes/waits for the EXE.
- `tests/verify_dino_2t_4t_route_windows.py:135–136`: same ordering; the routing test does not subsequently check a nonzero return code.

A shutdown timeout or crash can leave an already-written PASS receipt alongside `failure.txt`. The supplied successful attempts returned successfully, so no false historical PASS was demonstrated. Future evidence collection should make successful receipt emission contingent on all final checks, and distinguish interim progress from terminal acceptance.

## Architecture assessment

The native scientific boundary is meaningfully separated:

- Desktop routes native 4T validation/run/result checks through `engine_platform` and `DINO4T_API_V1`.
- Native 4T projects have a separate schema and retain native configuration/result semantics.
- The 2T workflow is not coerced into the 4T result contract.
- A/B comparison checks exact RPM/context, native model selection, numerical context, code identity and claim labels; it preserves full-precision metrics in exports.
- Nonperiodic performance results are excluded from the 4T performance plot and A/B deltas.

The common platform remains partial rather than a fully symmetric adapter architecture: registry discovery exposes 4T; 2T still uses its existing execution path. This is an explicit compatibility choice, not automatically a defect.

Other maintenance risks:

- GUI model/label lists are hardcoded rather than discovered from `api.capabilities`, contrary to the integration contract’s stated guidance.
- `docs/dino4t/integration_contract.md` still says no GUI/adapter exists and contains obsolete descriptions of `engine_platform`.
- `docs/dino4t/desktop-integration.md` retains an old “no cancellation” limitation alongside the later cancellation section.
- The summary-less error branch at `four_stroke_desktop.py:285` hashes `self.context.engine()` rather than the immutable task input. Editing the model during an asynchronous failing run can therefore misidentify the failed input. This was identified statically; no solver failure campaign was used to reproduce it.

## Package facts independently checked

For the A/B candidate:

- ZIP SHA-256 matches `aa0992b08514c996ca8191e863387260fee964dfcd2aff19d6582a4bdc997e03`.
- The omitted example input exists inside the ZIP at `MotorSim/_internal/configs/dino4t/example_single_cylinder_500cc.json`.
- Its parsed JSON equals the source configuration at commit `07849322`; its raw bytes match the Windows checkout, with CRLF versus LF explaining the Git-blob byte difference.
- The 255-file recorded manifest indeed omits that consumed input.
- Existing screenshots and successful packaged receipts were inspected as historical evidence; graphical interactions were not rerun by this reviewer.

## Reproduction methods and evidence limits

All confirmed Desktop probes used the frozen source with the pinned `.venv-build` Python, `PYTHONDONTWRITEBYTECODE=1` and `QT_QPA_PLATFORM=offscreen`. They instantiate the real Qt widget classes and call the same editor/history/plot methods used by the GUI. They are software falsification probes, not physical simulations or independent repetitions of the historical graphical acceptance.

Minimal probe recipes:

1. **No-op editor:** `project_from_example` → set valid high-precision rod length → update base identity → `DesktopContext` → `FourStrokeConfigEditor` → `apply()` without cell edits → compare input and identity.
2. **Trace binding:** copy genuine accepted A summary/configuration to a temporary artifact tree → preserve summary digest → write a different trace → make equivalent native run/project references → `FourStrokeResults` → inspect loaded endpoint and `pressure_plot.series`.
3. **Stale detail:** load genuine accepted A/B project → redirect only in-memory summary-reference paths to a nonexistent temporary file → `refresh()` → inspect loaded/history/table/pressure state.
4. **Dirty source scope:** create and commit a miniature external Git dependency tree → modify shared `motorsim/kinematics.py` → invoke actual `_git_dirty` with the runner’s fixture `__file__`.
5. **Package input scope:** create and commit an external Git fixture containing the omitted configuration path → modify only that file → invoke actual `ensure_packaged_inputs_clean` and `unrelated_dirty_fingerprint`.
6. **EOL and path evidence:** compare each recorded evidence digest against current bytes, fresh Windows-worktree bytes and `git show 8b371e2:<path>` bytes; inspect native references and metadata paths.

The audit did not modify physical contracts or tests to improve results. It did not demonstrate experimental calibration, physical-model adequacy across an engine operating domain, mesh/time-step convergence, or predictive validation. Those claims remain outside the evidence reviewed here.
