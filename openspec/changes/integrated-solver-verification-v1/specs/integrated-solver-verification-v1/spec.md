# INTEGRATED_SOLVER_VERIFICATION_V1 Specification

## ADDED Requirements

### Requirement: verification targets the first-order integrated path

The study MUST evaluate the current `integrated_2t` implementation (first-order
HLLC without spatial reconstruction + SSPRK2 temporal) and MUST NOT introduce
MUSCL or any higher-order scheme in this change.

#### Scenario: second-order attempt

- **WHEN** a proposal introduces MUSCL or a higher-order time integrator inside
  this change
- **THEN** it MUST be rejected and deferred to a versioned numeric capability
  with its own change, preregistration and gates

#### Scenario: physics or contract change

- **WHEN** an edit touches equations, physics, `gas1d.solver`, P0-P9 contracts,
  thresholds or historical evidence
- **THEN** the edit MUST be rejected as out of scope

### Requirement: spatial convergence with existing mesh levels

The study MUST use the already allowed mesh levels (1/2/4/8 cells per section)
through a reproducible setup (`build_refinement_matrix`), MUST compare the same
cycle index across levels, and MUST report raw deltas per observable without
claiming spatial independence beyond the preregistration.

#### Scenario: non-decreasing delta

- **WHEN** the delta between the two finest levels does not decrease relative
  to the previous pair
- **THEN** the observable MUST be classified `NOT_CONVERGED` or `NON_MONOTONE`
  with the raw evidence attached

#### Scenario: signal interpolation

- **WHEN** phase signals are compared
- **THEN** the interpolation MUST be declared explicitly; native fields MUST
  NOT be interpolated

#### Scenario: temporal contamination in the spatial arm

- **WHEN** spatial-arm deltas are computed
- **THEN** the temporal contribution MUST be bounded from the temporal-arm
  data and the coarsest-level contamination control; if the temporal delta at
  the coarsest level exceeds the preregistered tolerance, that level MUST be
  excluded from spatial convergence judgments and the exclusion MUST be
  reported explicitly

#### Scenario: multi-axis delta

- **WHEN** two configurations differ in more than one axis (mesh, CFL or cycle
  index)
- **THEN** their delta MUST NOT be used for any convergence judgment

### Requirement: temporal convergence (CFL)

The study MUST evaluate at least two `max_cfl` values inside the allowed range,
on the same mesh and the same cycle index, recording accepted/rejected steps
and minimum/maximum dt.

#### Scenario: horizon extension

- **WHEN** a configuration is incomplete after its budget is exhausted
- **THEN** the horizon MUST NOT be extended and CFL MUST NOT be relaxed; the
  result MUST be classified `PARTIAL` and any retry requires a new
  preregistration

### Requirement: error quantification and supported domain

The report MUST quantify the relative error per observable for the studied
mesh/CFL pair, MUST declare `NOT_CONVERGED` when no estimate is possible, and
MUST declare the supported resolution domain or its absence.

#### Scenario: missing estimate

- **WHEN** the data do not allow estimating order or error
- **THEN** the absence MUST be reported without inventing an estimate

#### Scenario: necessary not sufficient

- **WHEN** convergence is declared satisfied
- **THEN** the report MUST state that it is a necessary but not sufficient
  condition for a predictive curve; without experimental validation the
  predictive claim remains prohibited

### Requirement: preregistered mixed tolerance and order as diagnostic

The study MUST judge convergence with a preregistered per-observable mixed
tolerance `|delta| <= max(0.05*|x_fine|, atol_obs)` where `atol_obs` is frozen
before comparison; it MUST apply an absolute band when the observable is near
zero, and it MUST report the observed order only as a consistency diagnostic,
never as an acceptance criterion or error bound.

#### Scenario: near-zero observable

- **WHEN** `|x_fine| <= atol_obs`, including a sign crossing between levels
- **THEN** the relative criterion MUST NOT apply and only the absolute band
  MUST govern; a sign crossing with magnitude beyond `atol_obs` MUST be
  classified `NOT_CONVERGED`

#### Scenario: order estimate

- **WHEN** an observed order `p` is computed from monotone pairs with
  refinement ratio 2
- **THEN** it MUST be reported as a diagnostic label only; no Richardson
  extrapolation MUST be presented as a result, bound or acceptance input

### Requirement: pipeline cost separation

The study MUST measure and report separately: physical integration
(`step`/`_assemble`/stage copies), audit/reconstruction
(`audit_integrated_cycle_primary`/`make_integrated_cycle_primary`/replay) and
serialization/IO (`jsonify`/artifact writes), with seconds per cycle, per
accepted step, peak RSS and share per bucket.

#### Scenario: measurement noise

- **WHEN** shares are reported without a repeated control run
- **THEN** they MUST be declared "single-sample" and the share as an estimate;
  it MUST NOT be presented as verified reproducibility

### Requirement: strict budgets and no automatic extensions

Every execution MUST respect per-configuration and per-invocation caps and the
global cap of the authorized tier; it MUST stop fail-closed when exhausted and
MUST NOT auto-extend or resume outside its identity and preregistration.

#### Scenario: exhausted cap

- **WHEN** a configuration cap or the global cap is exhausted
- **THEN** the configuration MUST be classified `PARTIAL`/`FAIL_CLOSED` with
  exact evidence and the execution MUST stop

#### Scenario: budget increase

- **WHEN** more budget than authorized is needed
- **THEN** a new preregistration and explicit owner authorization MUST be
  required; automatic increase is prohibited

### Requirement: explicit execution authorization

No solver step of the study MUST start without explicit owner authorization
recorded in `program-status.json` (scope, tier and caps); preflight without
solver is allowed without authorization.

#### Scenario: attempt without authorization

- **WHEN** A3 is started without recorded authorization
- **THEN** the attempt MUST be rejected and the task MUST remain
  `BLOCKED_LOCAL`

### Requirement: evidence and historical protection

Every result MUST carry hashes and a classification; partial results MUST NOT
be presented as PASS; P0-P9, thresholds and historical evidence MUST NOT be
modified.

#### Scenario: partial result

- **WHEN** the study does not complete the authorized matrix
- **THEN** acceptance MUST declare `PARTIAL` with the exact limits
