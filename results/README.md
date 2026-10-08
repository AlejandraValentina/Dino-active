# Results storage policy

The active repository stores **compact auditable evidence**, not bulk numerical output.

Track here when reasonably small:

- manifests
- summaries
- preregistrations
- decisions/reviews
- conservation receipts
- compact final result records
- fixture/configuration snapshots needed for reproduction

Do not commit here:

- per-cycle raw dumps
- checkpoints
- primary time histories
- large compressed JSON/CSV traces
- profiler dumps
- large logs
- generated campaign scratch data

Those artifacts belong in external artifact storage or the preserved historical repository. A tracked manifest should record their identity, hashes, provenance, and relationship to the producing commit when they are scientifically relevant.

Runtime replay inputs that live outside Git use the explicit `DINO_ARTIFACT_ROOT`
environment variable. Their logical IDs, relative paths, source provenance,
sizes, and SHA-256 values belong in a versioned manifest; consumers verify the
registered size and hash before reading a file. See
[`docs/artifacts/artifact_storage.md`](../docs/artifacts/artifact_storage.md).

## Explicit test-fixture exceptions

Two bounded raw fixtures are intentionally tracked because current automated tests consume them directly:

- `results/2t-v1-closure-20261006/restart-replay-c11/fixture_a_prime/continuous-cycle-1.json.gz`
- `results/engine-physics-v1/campaign-evidence-r3/engine_a_3000/cycle-012.json.gz`
- `results/2t-commercial-core-20261002/aud-15-fixture-d-20261005-v1/cycle-001.json.gz`
- `results/2t-commercial-core-20261002/aud-15-fixture-d-20261005-v1/cycle-002.json.gz`

The AUD-15 pair is consumed by `tests/test_aud15_fixture_d_campaign.py` to
check the preregistered two-cycle replay and P7 geometry. Both files were
restored byte-for-byte from the historical baseline because that automated
test reads the gzip primaries directly. They are 3.85 MB and 5.94 MB; neither
exceeds the 10 MiB per-artifact repository limit.

Adding any further raw fixture should be deliberate, minimal, and justified by an automated test or reproducibility requirement.

Historical low-RPM regression tests retain the compact campaign and diagnostic
receipts under `results/frontera-baja-2t-20260917/`. Their larger observation
and baseline result inputs are externalized in
[`artifacts/low-rpm-test-evidence.json`](../artifacts/low-rpm-test-evidence.json)
and resolved by hash through `DINO_ARTIFACT_ROOT`.

The P0 integrity inventory is retained at
`results/p0-baseline-0d-20260917/artifacts/inventory.json`; its large point
results are externalized in
[`artifacts/p0-baseline-evidence.json`](../artifacts/p0-baseline-evidence.json)
for the legacy P1-R4 verifier. The verifier checks the same registered SHA-256
values without reading from the historical checkout.

The historical cutover anchor is documented in `docs/history/repository_cutover_20261008.md`.
