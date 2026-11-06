# C03 independent mid-implementation review

Reviewer: `/root/integration_review`; read-only.
Baseline HEAD: `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1`, with in-progress uncommitted C01/C03 implementation.
Disposition: **REVISE before decisive acceptance**. This is an interim review, not final implementation acceptance. No solver run, build, product edit or operational-state edit was performed.

## Correct directions observed

- The new V2 outer reference anchors a raw run-metadata digest, which anchors the producer artifact-manifest digest, which anchors raw summary/config/trace bytes. This fixes the basic adjacent-current-checksum trust failure.
- Validation uses one primary byte snapshot for plotting, rather than reopening a mutable trace after summary verification.
- Missing original bindings remain legacy-unverified and do not enter verified comparison selectors.
- The new comparison schema re-verifies references and uses the resulting original endpoint, instead of trusting caller-supplied summary/config dictionaries alone.
- An isolated receipt-backed reconstruction and portable export/reopen succeeded without solver work; the reopened assessment was VERIFIED and the outer metadata digest was unchanged.

## Issues to close

### MID-01 — blocking integration regression: undefined success payload

`FourStrokeSimulation._finished` removed local metadata construction, but the final `self.runFinished.emit(meta)` remains. A normal non-RESULT_INVALID finish raises NameError after reference persistence. Emit a consistently defined validated metadata/reference payload and add a direct fake-envelope finish regression. No solver is needed for this check.

### MID-02 — original raw config evidence is overstated in historical reconstruction

`reconstruct_from_ab_receipt` checks the original raw summary and trace digests but only the configuration's canonical semantic identity. It then publishes all roles under `byte_policy=ORIGINAL_RECEIPT_BYTES`.

A 2.9-second isolated probe copied genuine A artifacts, changed only config CRLF to LF, and reconstructed from the frozen V1 comparison receipt. The result was VERIFIED with ORIGINAL_RECEIPT_BYTES, although the config raw preimage had changed. This does not alter physical input values, and semantic replay should remain possible. Correct the provenance alias: identify summary/trace as original raw-receipt-bound and config as original canonical identity plus currently preserved raw preimage, or require a separate original raw-config receipt. Do not falsely claim all raw role bytes were anchored by that receipt.

Observed:

```json
{"raw_config_changed":true,"assessment":"VERIFIED","byte_policy":"ORIGINAL_RECEIPT_BYTES","origin":{"kind":"EXPLICIT_LEGACY_RECEIPT_RECONSTRUCTION","evidence_schema":"DINO4T_AB_COMPARISON_V1"}}
```

### MID-03 — artifact JSON shape failures leak as AttributeError

`parse_json` correctly rejects duplicate/nonfinite tokens but accepts arrays/scalars. `verify_primary` and `assess_run_reference` then use `.get` on manifest/metadata/summary without checking object shape. `assess_run_reference` does not catch AttributeError.

Confirmed with an isolated file containing `[]` and its correct expected SHA-256:

```json
{"probe":"top_level_manifest_array","exception":"AttributeError","message":"'list' object has no attribute 'get'"}
```

Validate expected top-level object shapes before accessing fields. The reusable boundary should return controlled incompatibility for expected malformed artifacts rather than exposing a programming exception. Cover manifest, metadata, summary and config roots.

### MID-04 — preserve reconstruction/source qualifications in endpoint exports

`RunAssessment.endpoint` and the comparison output currently omit the producer manifest's origin/byte-policy and do not preserve a distinct source-provenance qualification for old summaries without the new source identity. A receipt-reconstructed old run can therefore appear in exported comparison metadata like a new producer run, with only its old code_dirty/commit claims retained.

Artifact integrity VERIFIED must remain distinct from source preimage provenance. Carry producer versus reconstruction origin, original evidence-receipt digest, per-role raw/canonical proof and source-identity completeness into the endpoint/JSON/HTML. Do not retroactively certify the old directory-scoped clean flag merely because result files now have raw anchors. Define strict A/B eligibility for a legacy source qualification explicitly.

### MID-05 — pending importer must not synthesize its original trust anchor

The parent states new-manifest import is still being implemented. Importing a standalone summary/adjacent artifacts.json and computing the current adjacent digest cannot establish an original producer anchor. Require an externally expected V2 reference/receipt/envelope digest for trusted original import. Otherwise preserve a newly acquired self-consistent snapshot with original provenance unverified. The direct API completion envelope's creation-time manifest digest is a legitimate anchor; discovering an adjacent file is not equivalent.

### MID-06 — portable path checks should not depend on host case semantics

`verify_primary` detects duplicate paths through host Path equality. On Windows case aliases compare equal; a Linux-generated manifest could contain `summary.json` and `SUMMARY.JSON` as distinct roles and then become nonportable on Windows. Compare canonical POSIX/casefold logical names explicitly. Reject noncanonical `foo/./bar` and `foo//bar` rather than letting PurePosixPath silently normalize them; traversal and absolute-path rejection are already present.

## Proof limits

The positive export/reopen probe demonstrates new relative role paths retain the same anchored metadata on relocation. It does not independently authenticate a claimed solver execution, prove numerical convergence, validate physical results, or show a new EXE. The architecture correctly documents integrity relative to the caller's reference trust root; retain that qualification.

The code is actively changing. These notes identify the reviewed intermediate behaviors; final acceptance must bind a fixed source revision and rerun the relevant focused cases after corrections. The earlier predecisive acceptance matrix remains the reference for final C03 review.

## Intermediate source identities

- `motorsim/dino4t/artifacts.py` SHA-256 `70a95bfa4730ca55d21dd5b487bdf3adab8dca249fb4a1f56648c5c3e4d033e3`
- `motorsim/desktop/four_stroke_artifacts.py` SHA-256 `4c05943adc9b69865bd3f5f2227b7831f2b250c71d4953dccc4a1fa1a9e2cfc8`
- `motorsim/desktop/four_stroke_desktop.py` SHA-256 `1bb829529e5931b47f3f054a8a8c0e0d4592ddb340a64a34093110e5e9b666bf`
- `motorsim/desktop/four_stroke_comparison.py` SHA-256 `ea9c9c7033fd4d13639b0ffe030e805aa9362333fe7c9895953f8464607d7cf1`
