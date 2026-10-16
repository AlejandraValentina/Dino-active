# Stage 1 focal diagnostic protocol v1

**State:** frozen before solver execution. **Scope:** one bounded diagnostic at the existing baseline point; this protocol is not a campaign authorization.

## Question and limits

This invocation measures whether the fixed baseline configuration at 3000 RPM and eight axial cells per named exhaust section reaches a period-1 or period-2 state under the existing `REFERENCE_PERIODIC_CONVERGENCE_V2` detector. It does not establish spatial independence, rank the two exhaust variants, validate the physical model, or authorize any RPM sweep.

The existing 1/2/4 and 1/2/4/8 engine matrices remain classified `SPATIAL_NOT_ESTABLISHED`: their refinement changes are material/non-monotonic and exceed the observed A/B response. A periodicity result at one mesh cannot change that classification. One cycle is insufficient for periodicity; this focal point is the only new solver work preregistered here.

## Frozen configuration

- Project: `examples/projects/dino-2t-exhaust-comparison.dino2t.json`.
- Variant: `Escape original`, 3000 RPM, WOT and boundaries from the unchanged project configuration.
- Exhaust mesh: `EXHAUST_MESH_V2`, eight cells in each of six sections, 48 cells total.
- Fuel and mechanical loss model are explicit and bound by their preregistered hashes. The configured friction MEP is 1500 Pa from the selected model's 1000 Pa piston-ring and 500 Pa bearing/accessory terms; it is configuration provenance, not a universal constant.
- Configuration, engine identity, fuel, loss model, project, runner and solver source hashes are frozen in `results/dino-stage1-scientific-readiness/preregistration/stage1-diagnostic-protocol-v1.json`.

## Detector and observables

Use the existing V2 thresholds and streaks without edits. Compare all existing chamber and duct state, global species inventory, work and P7 integral observables. Stop on `PERIOD_1`, `PERIOD_2`, eight complete cycles, or the cumulative 600-second wall budget. The remaining cycle and periodicity classifications are kept distinct: `NO_CONVERGENCE_WITHIN_HORIZON`, `BUDGET_LIMITED_CHECKPOINTED`, `NUMERICAL_INVALID`, and `AUDIT_FAIL`.

Every completed cycle must pass the existing independently recomputed primary audit and mass, four-species and energy conservation checks. Conservation does not establish physical accuracy. Performance outputs are available only if periodicity is accepted and the existing metric contract supplies valid inputs; otherwise IMEP/FMEP/BMEP, torque and power retain explicit undefined states and reasons.

## Resources, checkpoint and artifact policy

One worker; 2048 MiB configured memory limit; 600 seconds cumulative wall time for preflight plus execution across any resume. The diagnostic runner's own deadline controls the solver; `run_logged.py` captures the full output without an external kill timeout. Checkpoints are per-point and after complete cycles. Resume requires the matching prior report, checkpoint and all preregistered hashes. The runner fails closed if the artifact root is inside a Git repository.

Artifacts go under `${DINO_ARTIFACT_ROOT}/dino-stage1-scientific-readiness/v1`. No files are written to historical evidence roots or the repository by solver execution.

## Preflight result

The real preflight passed with zero solver steps, 48 finite-volume cells, explicit fuel/loss hashes and the V2 periodicity contract. The frozen configuration SHA-256 is `5baa4cbdfe00963fe0a48fed01fe6da783d6d48a3ead769c4858ed247a73b203`; engine identity SHA-256 is `5808faa3abe90a50648afde445e501f8af86fcc50a831674f3c12455626d5503`. Full preflight output: `results/dino-stage1-scientific-readiness/preregistration/preflight-20261016.json`.

Preregistration SHA-256 (canonical LF): `5c1f3699ab6411c5e1f5c26c74801179e40319b04e216dc1d4c95463527420c6`.
