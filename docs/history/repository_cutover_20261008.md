# Active repository cutover — 2026-10-08

This repository is a clean active-development continuation of the historical Dino repository.

## Historical anchor

- Historical remote: https://github.com/AlejandraValentina/Dino.git
- Historical source HEAD: `a3d518e2d736de84d82595f674789d4547baac4e`
- Historical local clone at cutover: `E:\dino\Dino`
- Cutover date: 2026-10-08

The historical repository was **not rewritten**. Existing commit hashes and scientific provenance remain valid there.

## Why the cutover was made

The historical clone had grown to approximately:

- 8.52 GiB in `.git`
- 6.82 GiB of regular packed Git objects
- 1.69 GiB of local Git LFS objects
- 9.51 GiB under the working-tree `results/`

A diagnostic found 231 historical Git blobs of at least 10 MiB, totaling about 4.20 GiB logically. Large cycle dumps, checkpoints, primaries, and campaign traces were the dominant source.

## What this active repository retains

The active repository starts from the exact tracked source tree at the historical HEAD above and retains:

- solver/source code
- tests
- scripts/tools
- configs/examples
- OpenSpec
- documentation and reviews
- compact result manifests, summaries, preregistrations, decisions, receipts, audits, and fixture configs

Heavy raw simulation artifacts are intentionally not imported into the new Git history.

## Raw evidence

Raw historical cycle data, checkpoints, primaries, and large campaign traces remain available in the historical repository/local artifact store. Compact evidence in this repository should continue to carry hashes/provenance that bind back to those artifacts where applicable.

This cutover changes repository storage/history only. It does not reinterpret any historical scientific gate, result, or claim.
