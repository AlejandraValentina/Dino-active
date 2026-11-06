# C03 — independent root-cause design and predecisive acceptance

Reviewer: `/root/integration_review`, read-only architecture reviewer.
Date: 2026-11-06 (America/Montevideo).
Baseline: frozen audit `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1`.
Scope: prospective design/acceptance for F06/F08/F09/F12/F13 within the owner's C01/C03 remediation. No implementation acceptance is claimed. The reviewer does not edit source, operational state, OpenSpec, B1.2/test_cae or historical evidence and executes no solver integration/build.

## Root causes to remove

1. **F06:** only summary bytes and canonical config identity have an external expected digest. Mutable run metadata selects the pressure trace; no original expected trace digest is checked. Hashing that currently selected trace during comparison establishes only its present contents.
2. **F08:** resource enumeration, Git clean scopes and actual PyInstaller/copy inputs are separate lists. The 4T example is consumed but omitted. Optional `--periodic-example` also consumes an external project and copied artifact directories after the repository manifest is created; a complete fix must account for these inputs, not just add the discovered example to two lists.
3. **F09:** source dirty detection is relative to `motorsim/dino4t` and excludes shared kinematics/mesh dependencies and untracked relevant source. A false clean flag cannot identify actual executed source by commit. Build-time clean input status also must not be confused with runtime integrity after unpacking.
4. **F12:** operational paths embedded in project/index metadata are absolute; raw checksums bind CRLF preimages whereas Git text blobs/other checkouts may use LF. Byte identity, canonical JSON identity and source-commit identity are different facts and need separate treatment.
5. **F13:** build metadata takes a legacy 4T reference-model string from `reference_results`, while Desktop uses native `DINO4T_API_V1`/`DINO4T_FOUNDATION_V1`. A package offers model capabilities; each native result records the selected models. These must not be conflated.

## Artifact boundary and trust model

Use one dedicated, versioned, non-Qt artifact-manifest/validator interface, callable by Desktop and later B1.2 without importing Desktop or solver internals. Generic byte/path checking can be common infrastructure; native config/result semantics should delegate to the family's public contract. Avoid duplicating a second summary validator inside Desktop.

The logical flow is:

`producer final bytes -> versioned manifest -> externally anchored manifest digest -> pure validator -> coherent verified snapshot -> Desktop / later B1.2`

The manifest should identify its schema, family/API/model, producer/source identity, outcome, canonical configuration identity, and artifact roles with relative path, raw SHA-256 and byte size. Periodic successful output requires its exact summary/config/trace set; incomplete/error outcomes must declare missing roles explicitly rather than imply an empty path is a verified trace. Config/result/model/operating/periodicity semantics remain subject to C01's native validation.

**An original digest must have an independent anchor.** New project/run references must carry an expected manifest digest (or refer to an equally immutable receipt that does). Locating an adjacent manifest and accepting its newly computed digest is insufficient: replacing the trace and changing that adjacent manifest would still pass. Version the application reference/project contract if necessary; continue reading the old contract explicitly. Do not modify frozen scientific result schemas just to add the application binding.

Bind scientific metadata either as an immutable manifest role, or derive it from the manifest/native summary and treat the mutable application index as a locator/context record with no scientific authority. If keeping `run.json` as a bound role, finalize it before the manifest, put no manifest digest inside that same hashed metadata, and anchor the manifest digest in the outer reference. This avoids a digest cycle. Project/variant display labels must not replace the original configuration snapshot as evidence of which engine ran.

Creation should finish primary writes, validate native semantics, finalize metadata and then atomically publish the manifest; only after successful validation should a bound reference be added to the project. Failure must leave a partial/unverified artifact, never a verified reference. Preserve immutable executed-input identity on failure; do not take the current edited Desktop configuration as the input of an earlier asynchronous task.

## Coherent reads, comparison and export

The validator should read each artifact's bytes once, check the externally expected digest and parse those exact bytes. Return a coherent snapshot with role identities, provenance classification, native validated data and structured diagnostics. Current cached summary + freshly reread config + newly hashed trace is not a coherent snapshot.

For mutation after loading history, define one policy and test it: revalidate before comparison/export and reject changed sources, or retain/export a complete immutable verified snapshot with its original hashes and explicit snapshot identity. Prefer action-time revalidation for the existing path-based Desktop. Never mix source generations or present an already invalidated snapshot as currently source-verified.

Status dimensions must remain separate: artifact integrity, native result semantic validity, periodicity, producer provenance completeness, calibration and experimental/predictive claims. A bundle with correct hashes can contain an invalid result; a periodic native result can have unverified original trace provenance. None of these classifications proves physical validation.

## Historical compatibility and original-byte policy

Old projects/results must remain readable without changing their source bytes, raw receipts or scientific classifications. An old record with no original trace anchor is **LEGACY_UNVERIFIED** (or a more precise legacy-summary/config-verified/trace-unbound classification), not a newly verified run. Creating a manifest from the files present today may protect a newly acquired snapshot, but cannot establish that its trace is the original producer trace.

The legacy classification must propagate to history, pressure availability/warnings, comparison eligibility, CSV/JSON/HTML and traceability. Do not leave a UI label claiming complete verification while a helper knows only the summary is hash-bound. Strict verified A/B must require the chosen verified provenance class. If legacy inspection is supported, its limitations must remain explicit and must not be exported as the new verified class.

Receipt-backed reconstruction is distinct from synthetic promotion. Historical A/B receipts may already supply original expected summary/config/trace digests; use them only with an explicit frozen receipt/source identity. A replay tool can reconstruct original CRLF bytes from a Git LF preimage in an external output if the reconstructed bytes match the pre-existing expected raw hash exactly. Record original blob/hash, transformation and restored raw hash in a new reconstruction receipt. Never rewrite original receipt hashes, silently normalize historical files in place, or select a convenient current digest as the expected one.

For new manifests, choose deterministic UTF-8/canonical JSON bytes and write bytes explicitly so Windows newline translation does not change the manifest digest. Primary artifacts retain their exact producer bytes. New checksum-bound repository fixtures need an explicit byte policy (`-text` or appropriately fixed EOL); historical attributes/evidence must not be rewritten as part of this remediation.

Portable bundles should use manifest-root-relative POSIX role paths, independent of the producing machine. Absolute original acquisition paths may be retained as descriptive provenance, never as operational lookup authority. Reject absolute/drive/UNC paths, traversal, empty/ambiguous role paths, duplicate/case-colliding names and resolved paths outside the bundle root. Symlink/junction handling must fail closed or be explicitly constrained. Do not search by basename outside the bundle as an automatic relocation fallback.

## Complete source and build identity

For F09, use a declared source-identity scope that covers all actual runtime dependencies and relevant untracked source. A conservative `motorsim` source-tree closure may be maintainable if its false-positive policy is documented; an explicit transitive native-source inventory is also legitimate. Include shared `motorsim/kinematics.py` and `motorsim/gas1d/mesh.py`. Record exact source bytes separately from commit/blob identity and EOL-filter semantics. If Git/build provenance is unavailable or incomplete, report unknown/unverified rather than `code_dirty=False`.

For frozen execution, distinguish a build-time declaration that source inputs were clean from any claim that the unpacked source files still match their manifest at execution. If runtime clean verification is claimed, check the relevant actual files against the embedded expected inventory; a static `packaged_inputs_clean=true` is not a runtime integrity test. Dependencies outside the repository need explicit environment/version/byte provenance appropriate to the claim. Pinned versions alone do not prove bit-identical package recreation.

For F08, derive manifest generation and clean-input validation from one consumed-input catalog used by the recipe/spec/copy operations, rather than repairing drift with one more independent hardcoded list. Cover repository resources, source-backed code, recipe, licenses/examples/templates, generated inputs and optional external study inputs in clearly separate categories. Any copied external input must appear with exact bytes and source/receipt identity; it is not claimed to come from the Git commit. A generated `build.json` must not introduce a self-hash cycle. Before/after checks must cover the same complete inventory actually consumed.

For F13, new metadata must identify the native 4T API/model through its public declarations/capabilities, separately from the legacy `motorsim.four_stroke` reference model. Do not present build-wide defaults as the selections of a particular run. Preserve original build receipts; add a new schema or additive explicitly named fields for future metadata. This is not adoption of the experimental 2T models with similar V2/MUSCL names.

## Predecisive acceptance matrix

These checks are scoped infrastructure/contract fixtures, not new physical campaigns. Establish them before judging implementation. Synthetic fixtures are allowed only as explicitly synthetic software-integrity fixtures.

| ID | Falsification or positive case | Required outcome |
|---|---|---|
| ART-01 | New producer bundle + externally anchored manifest + original role bytes | Coherent verified snapshot; identities/status and native semantics agree |
| ART-02 | Change each summary/config/trace/metadata role independently without changing expected reference | Reject with the exact role/cause; no verified pressure/delta/export |
| ART-03 | Change trace and its manifest entry together, but retain the expected outer manifest digest | Reject manifest identity; never trust an adjacent recalculated checksum |
| ART-04 | Swap internally valid files between two real distinct run/config identities | Reject mismatched relationships, not merely parse or hash each file in isolation |
| ART-05 | Change line endings of a raw-bound new artifact | Reject raw-byte mismatch; no silent normalization |
| ART-06 | Copy bundle/project to arbitrary root while original location is unavailable | Same original identities/data through only declared relative bindings; no old absolute-path reads |
| ART-07 | Open unchanged V1 historical project without an original trace receipt | Readable legacy classification, explicitly trace-unbound; never auto-promoted by hashing current files |
| ART-08 | Explicit receipt-backed historical reconstruction into external output | Original expected raw digests met, transformation recorded, originals/receipts unchanged |
| ART-09 | Traversal, absolute/UNC/drive paths, collisions, escape via symlink/junction | Controlled rejection before a source is accepted |
| ART-10 | Source changes after history load but before compare/export | No mixed old-summary/new-config/new-trace endpoint; chosen snapshot policy enforced |
| ART-11 | Interrupt/fail artifact finalization or manifest write | No verified reference published; recoverable partial/error record preserves executed input |
| ART-12 | Hash-valid result whose operating/model/config/status semantics conflict | Native C01 validation rejects; artifact integrity is not semantic acceptance |
| SRC-01 | Modify tracked shared kinematics/mesh and relevant untracked source in isolated Git fixture | Dirty/unverified; changed source closure recorded |
| SRC-02 | Clean checkout with different permitted EOL filters | Commit/blob versus exact raw source identity distinguished; no false byte-equivalence claim |
| SRC-03 | No Git and no usable build receipt | Unknown source identity, never false clean |
| SRC-04 | Modify unpacked scientific source after a clean build | Runtime integrity claim detects it, or metadata explicitly limits clean claim to build time |
| PKG-01 | Modify consumed native 4T example in a TRIAL input fixture | Manifest includes it and clean guard rejects before outputs |
| PKG-02 | Supply optional periodic-example project with copied associated files | Every consumed external byte has an explicit inventory/identity category; no false Git-clean claim |
| PKG-03 | Mutate any consumed recipe/resource/source/license during inventory/copy window | Complete before/after identity check fails closed |
| PKG-04 | Compare new model metadata with public native API and retained legacy identifier | Native/legacy identities named accurately; run-specific selections remain in native results |
| PKG-05 | Inspect packaging changes without constructing an EXE in this scope | No new Windows acceptance claim, build, merge, push or historical package alteration |

Compatibility verification should include unchanged valid 2T projects and 4T V1 projects/results. Schema evolution must not demand a fake trace anchor from legacy data or relabel old scientific evidence. The new reusable validator must be usable without Qt or a solver run; later B1.2 can adopt it, but no B1.2 behavior is silently changed by this scope.

## Review disposition

The versioned manifest + reusable validator direction addresses the root causes if it meets these acceptance conditions. Merely adding a trace checksum field computed at read time, adding the example path to only one list, or replacing the legacy model name with another hardcoded string is insufficient. Implementation still requires an independent read-only review against the fixed source and meaningful failing-before/passing-after regression evidence. No implementation PASS is issued by this design note.
