# C03 final independent source review

Reviewer: `/root/integration_review`, independent read-only architecture reviewer.
Decision: **PASS — scoped C03 source/infrastructure review**.

Frozen audit baseline: `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1`. Review HEAD: `18a10549df914cea4864870123d434c4c30c6f3d` with in-progress uncommitted remediation bytes; the exact reviewed source hashes are recorded below. This is not an assertion that those uncommitted bytes are already represented by HEAD. Final publication must identify the implementation commit and reconcile any later source changes with these hashes.

The review covers F06/F08/F09/F12/F13 and the six C03 mid-review corrections. It does not close C01 scientific acceptance, the enlarged regression run still in progress, Windows acceptance, B1.2 integration or all other audit findings. The reviewer made no product, operational-state, OpenSpec, workspace or test_cae edits. No solver integration, numerical campaign or Windows build was executed by this review.

## Mid-review issues resolved

| Mid-review issue | Reviewed resolution |
|---|---|
| MID-01 undefined finish metadata | Successful completion emits the persisted `ref`; direct `_finished` regression is present. |
| MID-02 raw config falsely called original receipt bytes | Preserved imports use `PRESERVED_IMPORT_PREIMAGES_V1`; per-role authority explicitly distinguishes original raw summary/trace digests from original canonical config identity plus the currently preserved raw config preimage. |
| MID-03 top-level JSON array AttributeError | `parse_json` requires an object; a known-digest `[]` manifest produces controlled ValueError/classification. |
| MID-04 exported reconstruction/source lineage lost | Endpoints and comparison output retain artifact origin/byte policy, source qualification, source identity, runtime environment and original manifest anchors. Strict comparison rejects legacy source identity; the explicit descriptive policy has its own qualified classification. |
| MID-05 adjacent current checksum used as import anchor | Import requires a supplied versioned outer reference. It follows the outer metadata digest and original producer-manifest digest; an adjacent manifest alone is not admitted. |
| MID-06 host-dependent path aliases | Canonical POSIX path form is checked, traversal/absolute ambiguity is rejected, and logical role paths use host-independent casefold collision checks. |

## Root-cause assessment

### Original artifact binding and coherent reads

The new chain is anchored in the versioned outer reference: expected run-metadata digest -> expected primary-manifest digest -> exact primary role bytes. A replacement trace plus recomputed inner manifest cannot satisfy the unchanged outer metadata anchor. The code no longer blesses a trace by computing only its current digest during comparison.

The helper parses the same bytes it verifies and retains a complete byte snapshot for plot selection. Comparison reconstructs its endpoint from a newly verified reference rather than trusting caller-supplied summary/config dictionaries. CSV and JSON/HTML comparison exports carry the source/artifact lineage and new schema. Export readiness checks re-verify original references before exporting cached result/comparison data. These are meaningful fixes to the original mixing of cached summary, current configuration and current unbound trace.

The manifest is published after the primary role files; existing artifact output is refused rather than overwritten. Metadata avoids a digest cycle: it anchors the primary manifest, while the outer reference anchors the metadata. Role availability is explicit for zero-cycle versus completed-cycle outcomes. Native semantic acceptance remains separate from byte integrity.

### Historical compatibility and portable data

Old records lacking the original outer/trace binding remain legacy-unverified or incompatible, not automatically promoted. A preserved original comparison receipt can explicitly reconstruct summary/trace raw preimages, with declared EOL-only recovery to a pre-existing expected hash. Configuration authority is accurately limited to its canonical original identity if no original raw-config receipt exists. Reconstruction records its origin and any byte-restoration operation without rewriting the old receipts or source data.

Strict new A/B refuses `SOURCE_IDENTITY_UNVERIFIED_LEGACY`. An explicit `LEGACY_RECEIPT_DESCRIPTIVE_V1` path preserves the historical model-sensitivity values with `LEGACY_SOURCE_UNVERIFIED_MODEL_SENSITIVITY`, a new comparison identity and retained original evidence references. It does not silently upgrade the old directory-scoped clean-code claim.

Portable export copies verified snapshots and preserves manifest identities. The independently exercised export/reopen succeeded after the original bundle roots were made unavailable. Supplied outer-reference import preserved the metadata digest. Neither path needed the original source-worktree absolute paths as operational locators.

### Source dependency closure and packaging inputs

The source-identity design conservatively inventories the application package, native 4T configuration data and relevant Git policy preimages. Shared kinematics and mesh inputs are included; missing, modified, ignored/untracked or unstable source does not qualify as false clean. Raw byte identity and canonical Python-code identity are distinguished. Historical source-record validation checks the recorded inventory, not whichever files happen to be present today. Packaged source identity checks actual shipped preimages against the embedded source snapshot; a sparse old clean flag is not enough.

The packaging spec, manifest and clean-input guard use the shared bundle-input declaration. The native example is included. Optional periodic-example projects and every copied associated file, as well as external license inputs, have explicit raw-byte inventories and are not falsely attributed to Git HEAD. Copied outputs and the consumed input snapshot are checked again before ZIP creation. Generated metadata has a separate digest instead of a self-hash cycle.

Native 4T model identity is now distinguished from the retained legacy reference-model string. Example component selections are identified as examples and the native result remains the authority for the models selected in a particular run. This does not promote similarly named experimental 2T models.

I reviewed the source/dependency and packaging regression cases and performed a cheap actual-repository declaration call successfully. This review did not reconstruct a package or independently rerun the whole provenance suite. Third-party environment/version identification is not a claim of bit-identical Windows binary reproduction.

## Independently executed evidence

A bounded 2.8-second helper probe used genuine copied historical A/B endpoints, never the solver. It:

- preserved old raw summary/trace while changing config EOL only, and observed accurate per-role canonical-versus-raw provenance;
- confirmed strict comparison rejects the reconstructed legacy source identity;
- reproduced the original four full-precision metrics under the explicitly qualified descriptive policy;
- retained original receipt lineage in the exported comparison;
- copied/exported the project, made original roots unavailable, and reproduced the same new comparison ID after reopening;
- imported a supplied outer reference with the same original metadata digest;
- rejected a changed trace even when its inner manifest hash was recomputed;
- rejected a known-digest top-level array manifest as a controlled object-shape error;
- verified all original historical files read by the probe remained unchanged.

Machine-readable observations: `c03-final-independent-probes.json`, SHA-256 `3dcdb4d0260973d2ca9ae8d661a011640b95c082674514c38a3e5a330cc34d0f`. `solver_integrations=0`.

The parent-produced retained targeted log reports **43 passed** for the new native-contract/artifact-binding suites, exit 0. I inspected that summary rather than rerunning it. Earlier development failures are retained, including the relocation test's earlier attempt to re-read a deliberately renamed original source and the ignored-policy fixture's missing commit; those failed development attempts must not be represented as decisive passes. The enlarged final suite is a separate acceptance dependency for the orchestrator.

## Limits and disposition

No remaining C03 architecture blocker was found at the recorded source hashes. PASS here means the examined provenance/integrity mechanisms address their root causes within the declared trust model, backed by the independent probes above. The trust root is the caller's original reference/receipt; hashes do not authenticate an external measurement or prove that an asserted solver execution occurred.

A clean identified implementation commit, successful relevant enlarged regressions and the owner's acceptance conditions remain required for final delivery. No changed Windows EXE was built or tested here, and earlier rc12 packaged acceptance cannot be reassigned to these source changes. Future B1.2 can reuse the non-Qt validator but is not integrated or accepted by this remediation.

Other audit findings remain outside this scoped PASS, including editor precision work not authorized here, broader lifecycle/continuation assurance and independent physical/experimental validation. Preserve `NOT_PERFORMED`/`NOT_CLAIMED`; neither artifact verification nor legacy descriptive comparison establishes predictivity.

## Reviewed source identities

- `motorsim/dino4t/artifacts.py` SHA-256 `f701109823b150728a8a3f40507fe5c966b2de638318c89dbdccd3e8d94d0f91`
- `motorsim/desktop/four_stroke_artifacts.py` SHA-256 `3db1a492157fe4ac0d3d4da69c371ce1321adea69eaf4fa76f269c3d6f1dbf85`
- `motorsim/desktop/four_stroke_comparison.py` SHA-256 `d99c3e0db1b662d78e34dbafc334737f60879a7c754b0fb1b3a292077cd37bed`
- `motorsim/desktop/four_stroke_project.py` SHA-256 `ad791f254a3450d7bbca7bc68fe7eb3956b0f5f233ebfa764951663fd9ec6e97`
- `motorsim/desktop/four_stroke_desktop.py` SHA-256 `bf82ca68cd27b71f663e985830b6251ef3f9ba02b44faaaa9eac4932267847d2`
- `motorsim/desktop/technical_report.py` SHA-256 `f6166f99fdd64310f7cd1a22f49b802b8f5d950ef92b35428ad9094ee1dbd428`
- `motorsim/engine_project.py` SHA-256 `2692edeb360229339fd18c8b8a3be390aa59f09e07626bf00cd5bc0999834a62`
- `motorsim/source_provenance.py` SHA-256 `a3e8410e04501c92aa79ed11c8d06392bb1fb1a5b51c4278e6c71d5b66c797ed`
- `packaging/bundle_inputs.py` SHA-256 `d2163bec541baf10383dc534c9256ffac3a6e48f70830e1d6cb2f07ac13ee9d4`
- `packaging/build_provenance.py` SHA-256 `faaf0c491bf66c36fc2d7c61a05ae3627bf23fa707b3a555d782f62fcf735e8e`
- `packaging/build_windows.py` SHA-256 `11548b12c19363f270015817d88648f5b590e7bb8d042889ced34cd88cb3acb5`
- `packaging/MotorSim.spec` SHA-256 `ba950a567ab4f0fd9622473388ef3c829d28004078bff6137c9dddc46a4c0b64`
- `tests/test_c01_c03_artifact_binding.py` SHA-256 `0870b6e7d152bdb834077dda45a0133336c064b5d205913cf76c2f403c51b232`
- `tests/test_c01_c03_native_contracts.py` SHA-256 `82495429deae7041ee8f1c4f331941d27d26c3dd7f78c6a0da732497fdd97070`
- `tests/test_c03_source_and_bundle_integrity.py` SHA-256 `cce99ab71059cfca53f7a82d7a9404eb05084a461f6d79f54ba9b9229796a1b0`
