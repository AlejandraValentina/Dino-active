# Independent final scientific review of the prospective platform plan

**Classification:** `INDEPENDENT_REVIEW`, read-only scientific-plan review.

**Disposition:** **PASS for prospective scientific-plan coherence only.** This does not accept the product's current scientific reliability, any open audit finding, implementation, numerical campaign, physical-model adoption, measured validation or predictive claim.

The plan was created after frozen audit commit `1db6408dd03e7302cc84332cd329c6b8ca0b21a8`. The exact reviewed inputs are:

| Input | SHA-256 |
|---|---|
| `docs/roadmaps/dino-platform-scientific-reliability-v1-20261105.md` | `5eab83a7926889b7aac2acca57d2a2e995663460de795ebd27fe71ffc850bdc2` |
| `results/platform-scientific-reliability-v1/plan.json` | `9a3336b3ec3ecbbc8784ba397ec7c1fd0643c6c1318d180c87ec935a3855f35a` |
| `openspec/changes/platform-scientific-reliability-v1/specs/platform-scientific-reliability-v1/spec.md` | `ec9852bd78ff8fd3e5a257296a497394fa664e9b639c1b725c9b5a211acf9670` |

## Initial review and resolution

The initial `REVISE` report remains unchanged as `independent-plan-science-review.md`, SHA-256 `cc5d08c49ae87a414e5ce08a885ba8a370c8f4bf7a96a106d48465d9393c0e16`. The final version addresses both requested changes:

1. **Independent numerical preparation no longer waits for unrelated product integration.** N2 has no C05 dependency. N4R can prepare an independent integrated two-zone trajectory oracle against a frozen identified model/configuration, with explicit source/artifact hashes rather than relying on the flawed source dirty flag. N4S depends on the relevant C01/C03/C04 contract, provenance and lifecycle work. N4 aggregates N4R/N4S; U4 still requires their combined scoped assurance. The independent oracle therefore does not wait for editor/display fixes or main integration.
2. **Calibration cannot silently absorb unresolved numerical error.** K2/K4 and the human-readable K gate require relevant numerical error to be bounded and small against measured uncertainty and the calibration residual. Component/reference bounds may satisfy that condition; no circular dependency on the later full design-pair uncertainty stage is introduced.

## Preserved scientific safeguards

- The platform scope is explicitly 2T+4T, with independent native cores, 360-degree/RPM-divided-by-60 versus 720-degree/RPM-divided-by-120 conventions, native units/indicator definitions and separate maturity records.
- Official main and the A/B branch retain distinct source/evidence attribution. A controlled merge is prospective, and historical Windows acceptance cannot verify later changes.
- Frozen P0-P9 evidence, the P9 hash, closed E1.0 work and existing 2T scientific obligations are preserved. E1.3 stays blocked and unactivated; no budget transfer, replenishment, old diagnostic campaign or automatic V2/MUSCL promotion is introduced.
- The new audit findings have prospective corrective acceptance. The coherent original synthetic-input A/B pair remains evidence of computed sensitivity under its declared criteria; it is not retroactively declared invalid by adversarial fixtures.
- The 4T independent trajectory-reference gap, case-specific Stage-2 GCI, prescribed burn, uncertain Cd/loss inputs, dirty-study qualifications and fail-closed unsupported boundary domain remain explicit.
- Numerical evidence does not close physical identification or measured validation. Calibration and blind holdout are separate for each family; complete matched measurements and uncertainty are required. No 2T P9 status, tolerance or predictive maturity transfers to 4T.
- Absolute predictions and design differences require their own applicable uncertainty, including correlations. Power and torque derived from the same observation are not independent validation data, and baseline numerical uncertainty is not automatically design-difference uncertainty.
- Data preparation remains parallel and family-specific. Missing measurements stay missing; synthetic assumptions do not replace them.

## Activation and review limits

The plan retains `implementation_or_campaign_activation=false`, per-task `NOT_ACTIVATED` states and `NONE_GRANTED_BY_THIS_PLAN` budget records. Future scope, source/configuration identity, criteria, cost/resources and authorization must precede execution. The current accepted delivery remains audit and replanning.

No tests, solver runs, model changes, repository edits, merges or external communications were performed during this plan review. No further blocking scientific-plan finding was identified within this review scope. The confirmed product defects and outstanding scientific/data obligations remain open until their own new evidence closes them.
