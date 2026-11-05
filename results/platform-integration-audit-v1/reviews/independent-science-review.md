# Independent scientific review — Dino 2T/4T

**Review classification:** `INDEPENDENT_REVIEW` of the scientific/API portions, performed read-only by an agent distinct from the previous implementer.

**Frozen revisions examined:**

- `main`: `5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`
- A/B branch: `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`

No source, project, contract, result or Git state was modified. The reviewed worktree remained clean. Tests below used in-memory copies and did not overwrite historical artifacts. No periodicity campaign, GCI campaign or new A/B pair was run.

## Technical conclusion

The recorded A/B pair supports the narrow claim of **computed sensitivity of one synthetic-input 4T model at one operating point**, using its declared periodicity detector. Inspection and independent artifact checks did not find evidence that the original pair is fabricated, nonperiodic under its registered criteria, or incorrectly converted between work, power and torque.

However, significant input-validation, result-validation and continuation defects prevent treating the platform’s public API and imported results as generally scientifically trustworthy. Several defects are inherited from `main`; the new A/B comparison adds an exposure path for semantically inconsistent results.

The previous narrow software gates should remain historical evidence. They should not be converted into a general scientific acceptance or predictive claim. No experimental validation or predictive capability has been demonstrated.

## Positive evidence independently checked

The existing `results/dino4t-ab-engineering-v1/runs/comparison.json` and its two actual solver endpoints were read directly.

| Check | A | B |
|---|---:|---:|
| Recorded complete cycles | 6 | 6 |
| Consecutive final transitions independently passing the recorded four tolerances | 2 | 2 |
| Required consecutive transitions | 2 | 2 |
| Summary byte hash matches recorded result hash | Yes | Yes |
| Trace byte hash matches recorded trace hash | Yes | Yes |
| Last-cycle trace span | 720° | 720° |
| Strictly increasing trace angles | Yes | Yes |
| Trace rows | 2005 | 1996 |

The only recorded design delta is `intake_valve.lift.max_lift_mm: 10.0 → 8.0`. Both results use 6000 RPM, equivalence ratio 1.0, the same code revision, thermodynamic sources and numerical settings.

Postprocessing identities were recomputed independently:

- `IMEP_net = work_net / displacement`: discrepancy about `5.3e-15 bar`.
- `brake_power = BMEP × displacement × RPM / 120`: discrepancy about `1.1e-14 kW`.
- `brake_torque = brake_power / angular_velocity`: zero discrepancy at stored precision.

Thus the 4T results use the correct **one 720° cycle per two revolutions** conversion. This must remain distinct from the 2T convention, where cycles per second are `RPM/60`. Shared indicator names must not erase that distinction.

Recorded maximum mass/energy/element closure values were:

- A: `6.07e-15 / 7.11e-15 / 3.60e-14`.
- B: `1.55e-15 / 6.15e-15 / 1.99e-14`.

These are internally consistent bookkeeping results. They do not independently establish the correctness of the boundary fluxes or physical model: the state and ledgers intentionally use the same stage fluxes and RK weights.

The runtime separation is deliberate: 4T owns its engine, thermodynamics, boundary conditions and 720° logic. Shared cycle-agnostic geometry kernels do not by themselves conflate the models. The 2T Riemann solver is described as a verification oracle for 4T, rather than its operating solver.

## Confirmed findings

### SCI-01 — P1: invalid periodicity configuration can return false success after one cycle

**Affected revisions:** inherited from `main`; present in `8b371e2`.

**Anchors:**

- `motorsim/dino4t/cycle_analysis.py:156–180`
- `motorsim/dino4t/config.py:45–51`
- `motorsim/dino4t/api.py:187–198`

`PeriodicityMonitor.status` considers only `streak >= consecutive`; it does not require the monitor’s `min_cycles` or the convergence hook’s successful return. Configuration validation does not reject a zero consecutive count.

A bounded negative test used the existing example, `dx_mm=30`, `max_cycles=1`, `wall_limit_s=30`, and `numerics.periodicity.consecutive=0`. It consumed **11.875 solver seconds** and created no output files.

Observed result:

```text
api.validate: valid=True, issues=[], unknown_keys=[]
api.run:
  ok=True
  error=None
  status=completed
  termination=requested_cycles
  periodicity.status=PERIODIC_CONVERGED
  cycles_run=1
  periodicity.history=[None]
```

No cycle-to-cycle comparison existed, yet the public API declared periodic success.

**Impact:** scientific classification and downstream eligibility can be wrong for an accepted configuration. This is not evidence against the original A/B pair, which uses `consecutive=2` and has two passing transitions.

**Required future acceptance:** invalid tolerance/count domains rejected before execution; periodic success requires an actually satisfied, versioned detector; negative tests cover zero/bool/noninteger counts, insufficient cycles and contradictory termination/status combinations. Existing tolerances and historical classifications must be preserved.

### SCI-02 — P1: result validation does not bind scientific metadata to the resolved configuration

**Affected revisions:** weak `api.check_summary` and native loader inherited from `main`; the new A/B comparison in `8b371e2` introduces an additional exposure path.

**Anchors:**

- `motorsim/dino4t/api.py:206–218`
- `motorsim/engine_platform.py:96–112`
- `motorsim/desktop/four_stroke_desktop.py:348–358`
- `motorsim/desktop/four_stroke_comparison.py:76–115`

The loader verifies result bytes and configuration identity. The comparison checks scientific fields **between summaries**, but does not establish that those fields agree with each summary’s resolved configuration. `check_summary` largely verifies required top-level keys, schema, run status and two claim strings.

In-memory adversarial copies of the real A/B endpoints were made, with consistently rebound metadata/result hashes. No historical file changed. The following were all accepted as `PERIODIC_MODEL_SENSITIVITY_ONLY`, and `api.check_summary` returned `[]`:

1. Both summaries had `cycles_run=0`, empty periodicity history, and maximum conservation closure of `1.0` for mass, energy and elements.
2. Both summaries reported **7000 RPM**, while both resolved configurations and their configuration hashes identified **6000 RPM**.
3. Both summaries reported `QUASI_STEADY_RESTRICTION_V1`, while both resolved configurations selected restriction model **V2**.

A related claim-guard probe changed an incomplete result to `experimental_validation="PERFORMED"` and `predictive_capability="CLAIMED"` and added an arbitrary nonempty `validation_evidence` object. `check_summary` again returned `[]`. The strict A/B comparator separately rejects those claims, so that particular bypass is not available through its current claim checks.

**Impact:** matching hashes prove byte identity, not semantic consistency. Malformed or stale imported summaries can be classified or compared as if they matched their actual configuration. This is particularly relevant because earlier 4T stages already had a documented mislabeled-model defect.

**Required future acceptance:** a versioned semantic result validator must bind operating point, model selections and periodicity settings to the resolved configuration; validate status/termination/cycle/history consistency; and treat unverified validation evidence as unverified. Tests should cover malformed imports and graph eligibility. Do not reinterpret the original, coherent A/B pair as failed because of these adversarial probes.

### SCI-03 — P1: wall-limit continuation state omits crank phase and can be reused at the wrong phase

**Affected revisions:** inherited from `main`.

**Anchors:**

- `motorsim/dino4t/runner.py:93–119`
- `motorsim/dino4t/engine.py:450–464`
- `docs/dino4t/integration_contract.md`, error table entry for `WALL_LIMIT`

The runner accepts a warm state based principally on component names and array shapes. The state contains `ducts`, `cyl` and `plen`, but no crank angle. A new `engine.run` always starts at `theta_start`.

A tiny wall-limit probe, using single-zone mode and `dx_mm=30`, observed:

```text
first run:
  status=incomplete
  termination=wall_limit
  complete cycles=0
  returned engine theta=-358.5°
  theta_start=-360°
  state keys=['ducts', 'cyl', 'plen']

same cylinder vector:
  pressure at actual phase = 103922.3829901458 Pa
  pressure when reinterpreted at restart phase = 104153.97459509272 Pa

next runner call using that state:
  warm_start=used
```

This is not an exact continuation. It changes the interpretation of stored cylinder mass and energy through a different cylinder volume before the trajectory resumes. During the two-zone burn, additional model context also lives outside the returned arrays (`twozone.py:32–105`).

**Scope qualification:** Desktop currently does not claim a serializable 4T checkpoint. Its documented restart-from-configuration limitation should remain. Safe cancellation at a complete cycle is a different, narrower mechanism and is not invalidated by this probe.

**Required future acceptance:** restrict reusable warm states to verified complete-cycle boundaries, or introduce a complete versioned continuation state carrying phase and all required model context. Clearly distinguish a fresh transient seed from exact restart. No physics change is required to refuse an unsafe continuation.

### SCI-04 — P1: physically consequential invalid inputs are accepted or silently normalized

**Affected revisions:** inherited from `main`.

**Anchors:**

- `motorsim/dino4t/config.py:45–51,63–67`
- `motorsim/dino4t/valves.py:78–90`
- `motorsim/dino4t/closures.py:14–63`
- `motorsim/dino4t/api.py:97–107`

Configuration-only probes, without simulation, found:

| Input mutation | Result |
|---|---|
| Intake valve count `1.9` | `valid=True`; builder uses `int(...)`, silently producing one valve |
| Intake valve count `True` | `valid=True` |
| Friction coefficient `a_pa=NaN` | `valid=True` |
| Friction coefficient `a_pa=-1e8` | `valid=True` |
| NaN in a forward Cd table | `valid=True` |
| Entire geometry section `None` | uncaught `AttributeError`, rather than structured `CONFIG_INVALID` |

NaN range checks in `FlowCoefficients` do not reject NaN, because the ordinary less-than/greater-than comparisons are false. Friction closures have no effective constructor validation.

**Impact:** silent valve-count changes and invalid loss coefficients can alter effective area or brake metrics. Inputs can also bypass the expected structured-error boundary. The original A/B configurations were not shown to contain these defects.

**Required future acceptance:** finite numeric and strict integer domains, explicit policy for allowable correlation coefficients, section-type validation and expected-error envelopes. Invalid-input tests must exercise the public API and Desktop import/preflight path.

### SCI-05 — P1: source `code_dirty` does not cover shared runtime dependencies

**Affected revisions:** inherited from `main`; packaged behavior follows a separate metadata path.

**Anchor:** `motorsim/dino4t/runner.py:47–62`.

The source dirty check runs:

```text
git status --porcelain --untracked-files=no -- .
```

with its working directory set to `motorsim/dino4t`.

Therefore tracked modifications outside that subtree—such as shared `motorsim/kinematics.py` or `motorsim/gas1d/mesh.py`, which are runtime dependencies—are outside the check. A source result may still report `code_dirty=False` while HEAD does not identify all code that computed it.

**Qualification:** packaged builds use `build.json` and `packaged_inputs_clean`, not that Git-subtree query. This finding does not show the existing clean A/B runs or packaged candidate have incorrect provenance.

**Required future acceptance:** compute source provenance over the actual dependency/build-input closure or an appropriately scoped repository state. Regression tests must mutate a shared dependency in an isolated fixture and ensure reproducibility is not asserted falsely.

### SCI-06 — P2: sensitivity tooling can report successful derivatives from nonperiodic runs

**Affected revisions:** inherited from `main`; this is `dino4t.studies`/CLI behavior, not the new strict Desktop A/B comparator.

**Anchors:** `motorsim/dino4t/studies.py:145–173`.

`sensitivity` requires `status=="completed"` for the base and perturbations. In this API, that status also includes exhaustion of requested cycles without periodicity. Perturbation periodicity is not retained in the resulting derivative records.

A synthetic contract-only stub, explicitly not a solver result, returned `status="completed"` and `periodicity="NOT_CONVERGED"` for every call. `studies.sensitivity` nevertheless returned:

```text
base_periodicity=NOT_CONVERGED
parameters.friction_A.status=ok
parameters.friction_A.imep_net_bar=0.0
```

The stage-2 report already acknowledges that S4 retained periodicity only for the base and that exact commit reproducibility is not guaranteed for several historical studies.

**Impact:** derivative status does not establish periodic eligibility or provide the provenance needed to audit each perturbation. Historical S4 should remain qualified; it cannot be retroactively upgraded.

**Required future acceptance:** retain per-endpoint configuration/result identity, status and periodicity; suppress or explicitly qualify derivatives when either perturbation is ineligible; bound step size and numerical noise. Do not automatically repeat the historical study.

### SCI-07 — P2: unknown-key rejection remains incomplete

**Affected revisions:** inherited from `main`; partially acknowledged in `stage2_assessment.md:176–177`.

**Anchor:** `motorsim/dino4t/api.py:111–131`.

The allowlist gathers key literals globally from the configuration module and skips recursion into `segments`, `lift`, `discharge_coefficient` and `periodicity`.

Accepted configuration-only probes included:

```text
intake_valve.lift.typo_ignored = 42
numerics.bore_mm = 123
```

Both returned `valid=True`, `unknown_keys=[]`.

**Impact:** the declared “unread keys are rejected” policy is broader than the implementation. Some typos or misplaced fields appear accepted while having no effect.

**Required future acceptance:** section-aware schema validation, including nested tables and lists, with tests for misplaced otherwise-valid names. This is a confirmed known limitation, not a newly discovered numerical-model defect.

### SCI-08 — P2: advertised default model disagrees with the accepted omitted-key behavior

**Affected revisions:** inherited from `main`.

**Anchors:**

- `motorsim/dino4t/api.py:70`
- `motorsim/dino4t/config.py:91–93`
- `motorsim/dino4t/runner.py:37–45`

Removing `combustion.zone_model` is accepted. The builder and `resolved_models` select `single_zone`; `api.capabilities()["default_models"]` advertises `TWO_ZONE_EQUILIBRIUM_V1`.

Observed configuration-only probe:

```text
valid=True
advertised default cylinder=TWO_ZONE_EQUILIBRIUM_V1
selected when omitted=SINGLE_ZONE_0D_V1
```

The Desktop rule requiring explicit model keys is valuable, but the API discovery contract itself is inconsistent.

**Required future acceptance:** distinguish reference-example choices from actual omitted-key defaults and verify advertised capabilities against resolved configurations.

## Scientific limits that must remain explicit in the new plan

1. **Periodicity is scoped to the registered observables.** The monitor tests net IMEP, trapped mass, cylinder-pressure trace and system mass imbalance. Passing those conditions is not an independent proof of full-state periodicity in every duct cell or plenum, and it is not experimental validation.
2. **Stage-2 GCI is case- and model-specific.** Its synthetic baseline 20/10/5 mm study cannot establish uncertainty for every new valve geometry, operating point, or A/B difference. The new A/B pair has demonstrated sensitivity at its chosen discretization, not an experimentally validated or universally mesh-resolved design effect. No new campaign is justified merely to restate that limitation.
3. **The integrated two-zone trajectory still lacks an independent trajectory reference.** Stage 2 provides equilibrium and algebraic closure checks against Cantera, temporal self-convergence and conservation. Those do not independently verify the complete evolving two-zone trajectory with heat allocation and prescribed burn. The existing report states this limitation correctly.
4. **Combustion remains prescribed.** Holding Wiebe parameters fixed while modifying valve lift measures sensitivity conditional on that combustion assumption. It does not predict how real combustion duration, phase or stability changes with the design.
5. **Cd, walls and losses remain uncertain engineering inputs.** Flow-bench Cd with its area convention, valve lift/timing, complete geometry, boundary conditions and measured pressure/torque/fuel/air data are prerequisites for meaningful calibration and blind validation. Synthetic parameter labels must not be promoted to measured evidence.
6. **The 4T choking-domain limitation is fail-closed.** The documented explicit rejection of unsupported supersonic inflow is a model-domain boundary, not a defect to remove through tolerances. Extending it requires a justified, independently verified model.
7. **L1 artifacts are not full L2 replay evidence.** Summary closure values and the last-cycle CSV do not contain all stage fluxes needed for independent offline ledger reconstruction. The trace writer also formats numeric values to ten significant digits (`runner.py:160–166`). Existing `L1_ENGINEERING_RUN` labeling is appropriate.
8. **Shared metrics require explicit conventions.** Besides the 360°/720° power factor, `mechanical_efficiency` is explicitly defined here as brake work over **gross** indicated work (`model_reference.md:244–245`, `cycle_analysis.py:105`). It must not be silently equated with a metric using net indicated power in another engine family.

## Recommended ordering of scientific obligations

1. Close false-periodicity, input-domain and semantic result/config validation gaps before expanding studies or making stronger scientific claims.
2. Close source provenance scope and unsafe continuation behavior before using source runs or partial-state reuse as reproducibility evidence.
3. Make sensitivity eligibility and per-perturbation provenance explicit; preserve historical studies with their existing limitations.
4. Define separate 2T and 4T numerical evidence matrices, including model/version/domain/discretization scope. Retain frozen 2T obligations.
5. Prepare an independent two-zone trajectory oracle as a targeted verification deliverable; it does not require experimental geometry or a broad engine campaign.
6. Acquire complete measured datasets separately for each architecture, then preregister calibration and blind validation. Do not transfer the numerical or experimental maturity of one engine family to the other.

The proposed corrections are future work identified by this audit. None was implemented during this read-only review.
