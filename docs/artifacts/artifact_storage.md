# External artifact storage

The active repository is self-contained for source code, tests, OpenSpec,
compact manifests, summaries, receipts, and small fixtures. Large accepted
primaries, cycle dumps, checkpoints, and traces stay outside Git.

The historical `Dino` repository remains an archival provenance source. Active
runtime workflows must not read from that checkout or depend on its local path.

## Configure the artifact root

Set `DINO_ARTIFACT_ROOT` to the root directory of the local artifact store. For
example, in PowerShell:

```powershell
$env:DINO_ARTIFACT_ROOT = 'E:\Dino-artifacts'
```

The value is machine-local configuration. Versioned manifests contain only
logical artifact IDs and paths relative to the root.

## Verify and replay R2 inputs

The R2 artifact identities are in
[`artifacts/engine-physics-v1-r2.json`](../../artifacts/engine-physics-v1-r2.json).
The resolver rejects missing files with `REQUIRED_EXTERNAL_ARTIFACT_NOT_AVAILABLE`
and rejects size or SHA-256 mismatches with `ARTIFACT_INTEGRITY_FAILURE`.
Verification happens before each primary is opened by the replay.

The GUI result-history fixture and performance sweeps, the two AUD-15 Fixture D
cycle dumps, P2B resume cases, and low-RPM regression inputs use the same
resolver through [`artifacts/test-fixtures.json`](../../artifacts/test-fixtures.json)
and [`artifacts/low-rpm-test-evidence.json`](../../artifacts/low-rpm-test-evidence.json),
with P2B cycle records in [`artifacts/p2b-resume-evidence.json`](../../artifacts/p2b-resume-evidence.json).
They keep larger time histories outside the Git repository while preserving
their byte identity and historical relative source paths.

The legacy P1-R4 integrity verifier uses the compact P0 inventory and
[`artifacts/p0-baseline-evidence.json`](../../artifacts/p0-baseline-evidence.json)
for its large result files. It verifies each external file against the
inventory hash; it does not open the historical checkout.

With the root configured, run the offline replay to a scratch directory:

```powershell
python scripts/engine_physics_v1_r2_offline_replay.py --out "$env:TEMP\engine-physics-v1-r2-replay-check"
```

This consumes the four registered primaries and does not start a campaign or
advance the solver. Compare its point outputs and hashes with the committed
`results/engine-physics-v1/r2-offline/manifest.json`.

To independently check one registered file's byte hash on Windows:

```powershell
Get-FileHash "$env:DINO_ARTIFACT_ROOT\engine-physics-v1\r2\A3000\cycle-073.json.gz" -Algorithm SHA256
```

Never add a machine-specific absolute path to the manifest. Register new
artifacts with a stable logical ID, historical relative source path, byte size,
SHA-256, purpose, and root-relative destination.
