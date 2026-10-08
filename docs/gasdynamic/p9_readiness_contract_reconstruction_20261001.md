# P9 readiness and contract reconstruction — 2026-10-01

## Decision

**Classification: `P9_CONTRACT_UNDEFINED` (contractual hard stop).** The explicit human authorization to start P9 is recorded and supersedes the former authorization gate. It does not supply a scientific acceptance contract. The repository names P9 “Experimental validation”, but has no P9 OpenSpec change, preregistration, measurable requirements, dataset, or execution command. No scientifically valid P9 test can therefore be selected or judged without inventing its scope or gates.

`experimental_validation` remains `NOT_PERFORMED`. This is neither a scientific FAIL nor a P9 PASS. No P9 code, calibration, simulation, or experimental comparison was run. P4–P8 were not reopened or rerun.

## Baseline and authorization

- Repository: `E:\dino\Dino`, branch `main`.
- Starting `HEAD` and `origin/main`: `7c107eb4e59c1ed31684539cc73c51b71752d6aa` (equal; initial worktree clean).
- This task explicitly authorizes P9. The phase's old `human_gate`/“not authorized” language is historical configuration, not the basis of this stop.
- The phase still has `enabled: false`, `allowed_paths: []`, no commands, no tests, and `scientific_changes_authorized: false`. This supervisor entry is declarative and does not define a physical validation protocol. No supervisor or orchestration files were changed.

## Contract inventory

| Source | What it actually establishes | What it does not establish |
| --- | --- | --- |
| `dev_orchestrator/phases/P9.json` | Phase label/objective: future “Experimental validation”; currently no implementation, paths, commands, tests, or evidence requirements. | Experimental object, inputs, campaign, metrics, units, tolerances, uncertainty, comparison/alignment, or decision rules. |
| `dev_orchestrator/roadmap/gasdynamic.json` P9 entry | Title “Experimental validation”, depends on P8, checks only `phase_not_implemented`. | Any scientific contract or acceptance criterion. |
| `dev_orchestrator/README.md` | Explicitly says roadmap phases are declarations, not scientific contracts; commands and allowed paths are empty and phases disabled. | Authority to infer a contract from the phase name. |
| OpenSpec inventory | No P9-named change/specification exists. Existing P1–P8 specs do not define P9 validation gates. | A P9 PASS/FAIL/INCONCLUSIVE classifier or metrics. |
| `docs/HOJA_DE_RUTA_MotorSim.md` and governance notes | Real measurement contrast is a product-roadmap capability; final P4→P8 review keeps experimental validation `NOT_PERFORMED`. | A P9 dataset, protocol, selected engine, or thresholds. |
| P8 contract and final review | P8 is a frozen numerical bounded-transient campaign with explicit synthetic fixture provenance, not measurement. | Permission to interpret P8 indicated outputs as measured, periodic, predictive, or experimentally validated results. |

Consequently the exact P9 scientific contract is **not reconstructible from current durable project materials**. In particular, no P9 metrics or thresholds were inferred from the P8, P0, or UI comparison workflows.

## Existing evidence and provenance

### Reusable P4–P8 evidence

The prior independent final review at `docs/gasdynamic/p4_p8_independent_final_pass_20260930.md` records P4 `P4_PASS`, P5–P8 `REVALIDATED_ON_P4_PASS`, and `INDEPENDENT_REVIEW_PASS`. Its durable receipt is `results/p4-p8-independent-final-pass-20260930/review.json` (SHA-256 `82816e8ff06dc3b30be51bfbef31a2e2949b9e13f8ce096102baffc6ed2f98df`). This receipt and report are reusable as historical dependency evidence; this readiness review did not rerun them.

The P8 result `results/p8-wide-rpm-auditable-r4-final-20260930/p8-wide-rpm.json` has SHA-256 `812f161c39452a8bd7d2ec55a4823bfd65a1f9ab1745129240031113677e2a2b`. It records five anchors (2500, 5000, 8000, 11000, 15000 rpm), `synthetic_not_measured: true`, `metric_semantics: BOUNDED_TRANSIENT_INDICATED`, `steady_state: false`, `periodic_convergence: NOT_GRANTED_BY_P4`, and `experimental_validation: NOT_PERFORMED`. Example primary artifact `primary-15000-first.json.gz` has SHA-256 `980ea760aa2638837a92275f5ed4cb4f463839a7b1c76219a768eeee3de70aef`. These are numerical transient results only.

The prior GUI sweep `results/simulacion-2t/barrido-20260915/gui-sweep/series.json` has SHA-256 `aa1ce958815fa9f927deafadb7d29bc5d2562b6392e7e9cc1229bac194ef2a48`; its embedded project is named `PRUEBA SINTÉTICA`, so it is a model output, not measured engine data. P0 `results/p0-baseline-0d-20260917/artifacts/table.csv` (SHA-256 `9c91361e7fba500011dc64d02281f27e877d63c1bcc1b781e5436dd643418d19`) is likewise solver output, not experiment.

### Candidate data inventory

The repository and visible `E:\dino` workspace were searched for tabular and common instrument-data formats (CSV/TSV, Excel, HDF5, MATLAB, TDMS, Parquet, and JSON candidates). No dataset with experimental provenance for a MotorSim-matching engine was identified.

| Candidate | Classification | SHA-256 |
| --- | --- | --- |
| `examples/EJEMPLO_SINTETICO_contraste.csv` | Explicitly synthetic user-interface/example data; not an experiment. | `96b6e9c4bbd9a6edd86481404968b60bf115912a915e231d9147c68e3051d460` |
| `examples/EJEMPLO_SINTETICO_presion_bar.csv` | Explicitly synthetic example pressure data; no test provenance or uncertainty. | `24f40cd9278671294930f34709c3f88d2fa96b096b2cd435faafb45f3efe8fdf` |
| `examples/EJEMPLO_SINTETICO_trabajo.csv` | Explicitly synthetic example work data. | `5d446031ca1741486d9b40630a3ae8b8220887718baf8e46f41d26fd084ee260` |
| `results/p0-baseline-0d-20260917/artifacts/table.csv` | Simulated numerical campaign table; not measured. | `9c91361e7fba500011dc64d02281f27e877d63c1bcc1b781e5436dd643418d19` |
| `results/simulacion-2t/barrido-20260915/gui-sweep/series.json` | Generated simulation sweep using a project labeled synthetic; not measured. | `aa1ce958815fa9f927deafadb7d29bc5d2562b6392e7e9cc1229bac194ef2a48` |
| `results/p8-wide-rpm-auditable-r4-final-20260930/p8-wide-rpm.json` | P8 generated campaign explicitly `synthetic_not_measured`; not measured. | `812f161c39452a8bd7d2ec55a4823bfd65a1f9ab1745129240031113677e2a2b` |

The sibling `E:\dino\Dino-p4-r5-muse` contains a prior workspace copy of the same synthetic examples and generated numerical outputs; it did not provide an authorized experiment. No data was edited or imported.

## What can and cannot be claimed

Permitted: the existing P4–P8 statuses as recorded by their durable review; P8 numerical results retain bounded-transient semantics; this inventory found no authorized experimental dataset in the searched workspace; P9 has not been evaluated.

Not permitted: P9 PASS/FAIL; experimental validation; predictive validation; a periodic P8 power curve; a measured-vs-simulated error; calibration quality; or any claim that synthetic examples or simulated sweeps validate a physical engine.

## Minimum prerequisites to resume P9

The project needs an approved, versioned P9 contract that identifies the target physical engine/configuration and defines: authorized dataset(s) and train/calibration/validation separation; required channels and units; operating conditions and metadata; treatment of uncertainty, missing values and exclusions; the preregistered RPM/time/crank-angle alignment; contractual comparison metrics and thresholds; whether bounded-transient or accepted periodic states are required; evidence/provenance and independent-audit rules; and explicit PASS/FAIL/INCONCLUSIVE/DATA-REQUIRED outcomes. An authorized dataset must then be supplied with source, hash, units, channel definitions, engine configuration, conditions, date/origin, uncertainty, transformations, exclusions, and alignment metadata. These are unresolved contract prerequisites, not criteria chosen or thresholds proposed by this report.

Until then, the only defensible P9 classification is `P9_CONTRACT_UNDEFINED`; experimental validation remains `NOT_PERFORMED`. No implementation or campaign is legitimate under the current contract.

## Enmienda posterior — preregistro P9 v1.0 (2026-10-01)

La conclusión anterior era válida al commit `f9a308dafc95d61c8d1f86b205bdac0873c708e0`, antes de recibir el contrato adjunto. La usuaria suministró P9 v1.0; su texto original quedó preservado en `docs/gasdynamic/p9_v1_user_contract_20261001.md`. Se transcribió sin cambiar los umbrales a `openspec/changes/p9-experimental-validation/`, y `openspec validate p9-experimental-validation --strict --no-interactive` aprobó.

El contrato congelado está en commit `ba1dff027d66982aba0aeb7ae6f315fa92346a2c` (2026-10-01), antes de inspeccionar cualquier dataset experimental de decisión. El receipt y hashes están en `results/p9-readiness-20261001/preregistration.json`. El estado actual reemplaza la clasificación histórica de arriba: `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`. La auditoría no halló dataset adecuado; experimental validation continúa `NOT_PERFORMED`. No se ejecutó el simulador ni hubo calibración.
