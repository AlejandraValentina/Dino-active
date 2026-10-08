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

The historical cutover anchor is documented in `docs/history/repository_cutover_20261008.md`.
