# Hotpath analysis — Performance V2

## Current baseline

The current integrated solver was profiled on the existing A/B 9000 RPM configurations, 48-cell exhaust mesh, unchanged hashes `743a00de...2c1a9c` and `72e2ded3...602524`. Each instrumented run completed three bounded cycles and was classified `MAX_CYCLES_NONCONVERGED`; this is a diagnostic, not a periodic result.

Raw cProfile and runner artifacts are under `${DINO_ARTIFACT_ROOT}/integrated-performance-v2/` (`runs/A`, `runs/B`, and `logs/`). Unprofiled current baseline: A 12.409 s process / 12.399 s runner; B 12.264 s / 12.253 s. CPU was 12.25 s and 11.969 s. Peak RSS was 101.5 and 102.3 MiB.

## Exclusive CPU profile (instrumented)

| Function / group | A self s | B self s | Calls | Interpretation |
|---|---:|---:|---:|---|
| P6 `validate_species` | 3.421 | 3.314 | ~914k | repeated four-species checks/conversions |
| `_assemble` | 3.127 | 3.007 | 4,326 | orchestration exclusive time; child work below is separate |
| Python `all` | 3.011 | 2.937 | ~2.96m | generator-based admissibility checks |
| `math.isfinite` | 2.924 | 2.868 | ~25.44m | finite-state checks; profile attribution overlaps call trees |
| HLLC `hllc_flux` | 2.288 | 2.241 | ~190k | internal duct faces |
| EOS generator / `validate` | 2.028 / 1.891 | 2.008 / 1.846 | ~7.35m / 1.47m | repeated primitive/conservative admissibility |
| `deepcopy` | 1.374 | 1.349 | ~1.14m | predictor, checkpoint/diagnostic object copying |
| EOS `primitive` | 1.254 | 1.216 | ~822k | conservative-to-primitive conversion |
| thermal validation | 0.731 | 0.704 | ~303k | already reduced by Performance V1 |

The profiles total about 50 seconds while matching unprofiled executions take about 12.3 seconds: instrumentation materially inflates this workload. Use profile only for ranking; do not derive speedup from it. Cumulative HLLC, EOS and assembly costs overlap and must not be added. Combustion, geometry/ports and persistence are below these dominant rows; the unprofiled runner reports about 0.69 s postprocessing, with no dominant disk wait indicated.

## First candidate

`_face_species_flux` currently normalizes and validates both left and right species states on every face even though the signed HLLC mass flux selects exactly one donor. `IntegratedEngine2T.step` validates the complete SSPRK stage state before each `_assemble`; boundary species are validated when configured. Reuse only the selected donor's normalized state, retaining the public `donor_species` guard and leaving zero-flow validation unchanged. This removes repeated validation/allocation work without changing the selected donor, normalization arithmetic, HLLC flux, SSPRK2, or species ledger. End-to-end benefit must be measured before accepting it.
