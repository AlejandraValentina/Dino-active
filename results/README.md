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

## Explicit test-fixture exceptions

Two bounded raw fixtures are intentionally tracked because current automated tests consume them directly:

- `results/2t-v1-closure-20261006/restart-replay-c11/fixture_a_prime/continuous-cycle-1.json.gz`
- `results/engine-physics-v1/campaign-evidence-r3/engine_a_3000/cycle-012.json.gz`

Adding any further raw fixture should be deliberate, minimal, and justified by an automated test or reproducibility requirement.

The historical cutover anchor is documented in `docs/history/repository_cutover_20261008.md`.
