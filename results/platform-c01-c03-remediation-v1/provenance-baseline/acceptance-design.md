# C03 provenance remediation — acceptance fixed before implementation

Scope: F08, F09 and F13 only. Baseline source is `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1`.
This work changes provenance and packaging assurance, not physics, solver equations,
numerical configuration, historical expected values, artifacts or scientific claims.

## Falsification before implementation

1. A native 4T example consumed by `MotorSim.spec` must be present in the input
   manifest. The baseline omits `configs/dino4t/example_single_cylinder_500cc.json`.
2. In a temporary committed repository, modifying only that config must make the
   clean-input guard reject the build. The baseline excludes its directory.
3. In a temporary committed source tree, modifying only shared
   `motorsim/kinematics.py` must make native 4T provenance dirty. The baseline
   runner scopes status to `motorsim/dino4t` and reports clean.
4. The build's native 4T metadata must declare `DINO4T_FOUNDATION_V1`, its native
   API and its component model identifiers; legacy four-CV/reference model
   identifiers must be explicitly separated.

## Acceptance

- A single declaration describes repository source roots, required build inputs,
  PyInstaller data selections and external dynamic data selections. The spec,
  clean guard and manifest consume that declaration rather than parallel lists.
- Every declared spec data source is in the raw-byte input manifest. The 4T
  example is mandatory; deleting it fails before a build. Newly declared dynamic
  inputs affect the manifest, are copied only from an enumerated snapshot, and
  are checked again after consumption. Unknown dirty/missing/untracked inputs
  cannot be represented as clean.
- Initial and final guards cover all declared repository inputs, including
  newly added/deleted files under declared roots. External inputs are identified
  as external byte preimages, never falsely bound to a Git commit.
- Source identity conservatively includes all `motorsim` Python/config sources,
  including shared imported numerical dependencies. Every entry records raw
  SHA-256/byte size plus explicit canonical code hashing (UTF-8 source, CRLF/CR
  normalized to LF). The full inventory preimage is exported with its digest.
- Required 4T and shared numerical source files must exist. Missing Git, an
  unverifiable Git boundary, missing required source or unreadable input yields
  incomplete identity and never `dirty=False`. No inference from a commit alone.
- Dirty scope includes tracked and untracked source inputs; unrelated local
  evidence files remain distinguishable. Exact executable bytes are not inferred
  from canonical source hashes.
- Tests cover config mutation/deletion, shared-source mutation, untracked source,
  missing Git/dependency, raw-vs-canonical EOL sensitivity, dynamic consumed files,
  before/after snapshots, registry/spec coverage and legacy/native metadata.
- Existing packaging tests remain compatible where they exercise an intentionally
  minimal tree; newly required data applies explicitly to real declared bundles.
- No Windows build or solver campaign is required or authorized by these tests.

Implementation ownership: `/root/contract_review` acts as implementation writer,
not independent reviewer. Root owns runner wiring and final integration. Reviewers
must review the completed change independently before any closure claim.
