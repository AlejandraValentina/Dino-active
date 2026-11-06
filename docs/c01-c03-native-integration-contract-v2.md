# C01/C03 native integration contract — version 2

This application-layer contract is additive to `DINO4T_API_V1`. It does not
change either engine's physical equations, integration steps, tolerances or
historical evidence. It is not the B1.2 implementation or an OpenSpec update.

## Native configuration and results

Discover `config_validation_contract=DINO4T_CONFIG_VALIDATION_V2` and
`result_validation_contract=DINO4T_RESULT_VALIDATION_V2` through capabilities.
`validate` rejects typed/domain/finite/unknown-key errors with structured issues.
A typo is invalid even if `allow_unknown_keys=True` was supplied by legacy code.
Valid configurations keep the same canonical identity and numerical values.

`combustion.model=WIEBE_SINGLE_ZONE_V1` is the retained V1 compatibility label
for the prescribed Wiebe burn family. It is not the zone selector. Actual
selection is `combustion.zone_model` and `enabled`; `result.models` records the
resolved cylinder/burn/heat/duct/boundary choices. Unknown family labels are
rejected. Omitted selectors are reported using the actual constructor defaults,
not the bundled example's explicit settings. Legacy and native 4T model metadata
are separate in build receipts.

`check_summary(summary, config=resolved_config)` checks cycle/history/detector
consistency and recomputes convergence from finite metrics, not stored flags.
It binds exact RPM, configuration, model selections, provenance and evaluated
loss/indicator identities. Three complete cycles and the positive recorded
streak remain necessary. Signed finite friction coefficients remain legal;
negative evaluated FMEP is ineligible and is never clipped or calibrated away.
The versioned roundoff assurance profile is an admission policy, not a new
universal physical theorem or a relaxed convergence detector.

API `ok` requires periodic completion and admissible result semantics.
`RESULT_INVALID` preserves raw summary/state/artifacts with explicit validation
issues. Cancelled/limited/nonperiodic output must not be promoted into validated
performance. A 4T continuation state is still not an exact phase-safe restart:
F03/C02 remain outside this remediation.

## Original-byte references

Use `motorsim.dino4t.artifacts` as the versioned application artifact interface:
`publish_primary`, `verify_primary`, strict JSON/byte helpers and canonical safe
relative paths. `artifacts.json` is written last as commit marker and binds raw
summary/config/trace bytes plus canonical configuration identity. New outputs
are UTF-8/LF. Trace values retain the original ten-significant-digit policy;
JSON numeric payloads retain their original precision. No existing output is
overwritten.

Desktop `publish_desktop_run` anchors the producer's manifest SHA in immutable
`DINO4T_DESKTOP_RUN_V2` metadata, itself anchored by a
`DINO4T_RUN_REFERENCE_V2` outer reference. Save this reference in the project.
`reference.json` is the portable outer record. Call `assess_run_reference` or
`require_verified_run` before using data. Plot only the returned immutable raw
snapshot; do not reopen a mutable trace after verification. Reverify original
references immediately before comparison/export. An adjacent manifest whose
hash is freshly computed by the importer is not original authority.

Old project reference shapes are still accepted. Unbound historical files are
`LEGACY_UNVERIFIED` or explicitly incompatible, retained with original values,
and cannot supply trusted pressure curves/performance comparisons. Explicit
`reconstruct_from_ab_receipt` needs an independently supplied original receipt
SHA. Summary/trace raw-byte authority and config canonical-JSON authority are
distinguished. `GIT_TEXT_RECORDED_EOL_V1` recovery is explicit and must reproduce
the originally expected raw SHA; it never edits the historical file.

Use `import_reference_bundle` with the supplied original V2 outer reference;
use `export_project_bundle` to preserve exact metadata, manifests and primary
bytes using relative paths. Project/variant switching cannot change a run's
source config or immutable identity. These digests prove integrity relative to
the supplied reference, not digital authorship or experimental truth.

## A/B and parallel B1.2 adoption

`DINO4T_AB_COMPARISON_V2` re-verifies both outer references, resolved config,
exact operating/numerical context, models, thermochemical sources and source
identity. The default `STRICT_SOURCE_V1` additionally requires complete clean
original source snapshots and matching recorded runtime environments. Historical
`code_dirty=False` alone is insufficient. `LEGACY_RECEIPT_DESCRIPTIVE_V1` is an
explicit API-only descriptive policy for original receipt reconstructions,
labelled `LEGACY_SOURCE_UNVERIFIED_MODEL_SENSITIVITY`. It is never automatically
selected by Desktop and never means validated improvement. The new comparison
identity incorporates qualifications and lineage; it does not impersonate V1.
JSON/HTML and CSV differences preserve endpoint anchors and origin metadata.

B1.2 must adopt the V2 outer references, assessment classifications, immutable
snapshot plots, actual-model discovery and comparison policy explicitly. Do not
pass in-memory caller-created summary dictionaries as trusted endpoints. Do not
reinterpret source-qualified historical results as newly reproduced results.
Existing V1 report rendering remains available with legacy qualification.

## Source and packaging boundary

`DINO_SOURCE_IDENTITY_V1` records application/shared runtime source and data
preimages, Git policy, commit, dirty/unknown state and capture stability. Missing
Git or shipped preimages cannot establish clean source. Packaged execution needs
the complete embedded source snapshot and matching shipped preimages, not old
receipt booleans. Source preimages are application files, not an embedded copy
of their contents in each result.

`packaging/bundle_inputs.py` is the common explicit source/static/optional-data
inventory for spec, input manifest and clean guard. Optional external projects,
referenced data and build-environment license files have raw preimages and are
not falsely Git-bound. Dirty, untracked, deleted or changed consumed inputs fail
closed. Native example JSON is mandatory. Automatic third-party imports are
identified by the pinned build environment and runtime versions; this change
does not establish byte-identical third-party binary or Windows EXE reproduction.
No candidate was built or distributed in this remediation. Package-content
verification and acceptance remain necessary for a future authorized candidate.
