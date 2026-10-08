# P9 v1.0 — Experimental validation of fixed 2T indicated performance

Contrato congelado para una configuración fija 2T. El PASS queda limitado al
hardware y dominio medidos; no es validación universal ni predictiva para otros
motores. Potencia de freno/eje no equivale a potencia indicada y nunca es el
gate principal. P9 v1.0 es `VALIDATION_ONLY`; prohíbe ajustar parámetros contra
el dataset P9.

## ADDED Requirements

### Requirement: dataset and fixed configuration

P9 MUST identify one physical 2T configuration and show matching relevant
hardware between test and simulation. Bore, stroke, rod, displacement,
compression, ports/timing, exhaust/intake/crankcase geometry, ignition, fuel,
mixture, throttle/load, and exhaust configuration MUST be recorded where
applicable. Relevant unknown conditions MUST be `UNKNOWN`, with their impact
assessed; values MUST NOT be invented. A known material configuration mismatch
invalidates that operating point.

The dataset MUST contain at least five RPM operating points spanning a
significant fraction of its measured operating range, including low,
low-medium, medium, high-medium, and high regimes when the data permit. Every
valid point in the preregistered domain MUST
be included; points MUST NOT be selected based on agreement. Raw files MUST be
preserved. A frozen manifest MUST bind filenames, SHA-256, sizes, operating
points, channels, units, metadata, and exclusions before final comparison.

#### Scenario: dataset is frozen before comparison

- **WHEN** P9 prepares the confirmatory dataset
- **THEN** it records provenance, hashes, sizes, channels, units, metadata,
  operating points, and exclusions before inspecting simulation agreement
- **AND** it preserves raw files and stores transformations separately
- **AND** it does not replace an experimental point silently

#### Scenario: insufficient or mismatched dataset

- **WHEN** fewer than five valid operating points exist or a material known
  configuration mismatch invalidates a point
- **THEN** the missing or invalid point cannot be silently omitted to claim P9
  PASS and the dataset sufficiency decision is recorded

### Requirement: experiment provenance, uncertainty, and cycles

Each test MUST record available RPM, ambient pressure/temperature, intake
temperature, relevant exhaust conditions, fuel, mixture/AFR, ignition, throttle,
load, and engine/coolant/head temperature. Missing relevant values MUST be
recorded `UNKNOWN`, not fabricated. Data provenance MUST include source, origin
or date when available, engine configuration, conditions, units, channels,
uncertainty, transformations, exclusions, missing data, outliers, and
RPM/angular/time alignment.

When cycle-resolved data exists, at least 50 consecutive fired cycles MUST be
used per point unless a dataset limitation is documented. Mean, standard
deviation, count, excluded cycles, and the exclusion criterion MUST be saved.
Cycles MUST NOT be hand-selected for agreement. Available uncertainty and its
confidence definition MUST be preserved. If unavailable, record
`EXPERIMENTAL_UNCERTAINTY_UNKNOWN`; this alone need not prevent execution.

#### Scenario: cycle-resolved measurements

- **WHEN** cycle-by-cycle traces are available
- **THEN** P9 records the consecutive-cycle sample and summary statistics
- **AND** any documented limitation or exclusion criterion is retained

### Requirement: indicated work and power observables

The primary experimental observable MUST be indicated work per cycle and its
equivalent indicated power, using the same definition for simulation and
experiment. Prefer cylinder pressure versus crank angle with sufficient
geometry to compute instantaneous volume, and calculate indicated work as
`W_i = ∮ p dV`. Also accept a processed pressure trace only with its processing
documented, or indicated work/IMEP only with methodology and provenance
sufficient to reproduce the observable. Indicated power MUST use the 2T
cycle/rpm relation for the same measured RPM.

Brake power or shaft torque MUST NOT be compared directly against indicated
power. It may be retained as secondary information only. No post-hoc mechanical
efficiency factor is allowed.

#### Scenario: pressure-volume trace is available

- **WHEN** pressure-angle data and matching geometry are valid
- **THEN** the frozen processing derives instantaneous volume and `∮ p dV`
- **AND** the primary evidence retains the inputs and enough processing detail
  to recalculate work and indicated power offline

### Requirement: frozen simulation and P9-A periodic qualification

Before revealing the confirmatory comparison, P9 MUST persist the MotorSim
commit SHA, configuration SHA, geometry SHA, runtime binding, solver
configuration, physical constants, and operating-point definitions. No P9
dataset parameter may be tuned. Port/discharge, heat-transfer, combustion,
ignition, friction, scavenging, boundary, geometry, or numerical thresholds
MUST NOT be adjusted to improve agreement.

Every operating point MUST pass the existing MotorSim periodic convergence
contract before comparison, reusing E13 semantics if applicable. Period-1 and
period-2 are accepted; max cycles is 400 and MUST NOT be increased after seeing
a failure. Period-2 MUST preserve branches A and B. A scalar multicycle
experimental work/power may compare against `mean(branch_A, branch_B)`, while
both branch outputs remain stored; cycle-resolved data MUST retain the
corresponding cycle-level comparison.

Each point MUST pass all of: periodic-state qualification, finite state,
geometry, admissibility, species, CFL, mass conservation, energy conservation,
species conservation, non-vacuous P7 combustion event, P7 source admissibility,
restart, and deterministic replay.

#### Scenario: point fails P9-A

- **WHEN** a point does not qualify period 1 or 2 within 400 cycles or fails
  any required P9-A gate
- **THEN** that point cannot support an experimental validation claim
- **AND** the cycle cap and thresholds remain unchanged

#### Scenario: period-2 point

- **WHEN** E13 qualifies period 2
- **THEN** the evidence preserves branches A and B separately
- **AND** a scalar multicycle comparison uses their mean only when appropriate
- **AND** no period-1 result is fabricated

### Requirement: operating-point alignment

An experimental and simulated point MUST match only when
`abs(RPM_sim - RPM_exp) / RPM_exp <= 1%`. If an exact simulation RPM is
available, it MUST be used instead of interpolation. RPM MUST NOT be shifted to
improve agreement. Experimental TDC MUST derive from an encoder, documented
experimental procedure, or correction independently established before seeing
the MotorSim match. Phase shift MUST NOT be optimized against simulation.

#### Scenario: RPM and angular alignment

- **WHEN** a measured point is paired with simulation
- **THEN** the match obeys the 1% RPM rule, uses exact RPM when available, and
  records the independent TDC/alignment source
- **AND** no post-hoc RPM or phase adjustment is used

### Requirement: per-point and global performance gates

For each point P9 MUST define `relative_error_i = abs(P_sim_i - P_exp_i) /
abs(P_exp_i)`, using indicated power or indicated work under identical
definitions. Every point MUST have relative error at most 15%; at least 80% of
points MUST have relative error at most 10% (four of five when exactly five
points exist). MAPE MUST be the arithmetic mean of per-point relative errors
and MUST be at most 10%. Simulated and experimental indicated-work/power signs
MUST agree at every point. A sign mismatch is `P9_FAIL` for the performance
gate.

If the sampled experiment identifies an unambiguous interior maximum, the
simulated maximum RPM MUST be within one experimental RPM interval. This
secondary shape gate does not apply if the maximum is ambiguous and MUST NOT
extrapolate outside the measured range. Pressure peak, its crank angle,
pressure-trace RMSE, and integrated work MAY be recorded as diagnostics when
pressure data is sufficiently reliable; they are not gates in P9 v1.0.

#### Scenario: all primary performance criteria pass

- **WHEN** all points pass P9-A, pointwise error/sign criteria, MAPE, and any
  applicable shape gate
- **THEN** the performance gates pass without any threshold relaxation

#### Scenario: error criterion fails

- **WHEN** valid complete evidence violates any mandatory per-point, global,
  sign, or applicable shape criterion
- **THEN** the frozen model version receives `P9_FAIL`
- **AND** thresholds and results remain unchanged

### Requirement: primary evidence and offline auditor

P9 MUST retain raw experimental inputs, simulation primary evidence, work,
indicated power, experimental mean and uncertainty when available, relative
errors, MAPE, and gate decisions. An offline auditor MUST reconstruct
raw-data/primary-simulation evidence → aligned operating points → work/power →
errors → global metrics → decision. Stored PASS, MAPE, relative-error metrics,
or summary-vs-summary equality MUST NOT be authoritative. Original data MUST
remain unchanged; each transformation MUST be a separately hashed artifact.

The auditor MUST reject at least: NaN, infinity, booleans used as numbers, unit
mismatch, dataset hash mismatch, missing or duplicated operating points, RPM
mismatch over 1%, missing primary simulation evidence, changed experimental
values with unchanged manifest, modified summaries, modified derived metrics,
and incomplete periodic qualification.

#### Scenario: evidence is independently recomputed

- **WHEN** an auditor evaluates a P9 campaign
- **THEN** it verifies raw hashes and reconstructs every primary metric and
  decision from raw/primary evidence
- **AND** adulterated summaries or derived metrics cannot produce PASS

### Requirement: preregistration and classifications

P9 v1.0 MUST be versioned and frozen in OpenSpec with commit SHA and date
before the decision dataset is incorporated or inspected. After preregistration,
metrics, thresholds, alignment, minimum points, and PASS/FAIL criteria cannot
change; a change requires a new contract version and invalidates the prior
attempt for confirmatory decision-making.

Classifications are:

- `P9_PASS`: valid dataset, all points pass P9-A, all per-point errors ≤15%, at
  least 80% ≤10%, MAPE ≤10%, signs agree, and all other applicable gates pass.
- `P9_FAIL`: complete valid experimental evidence demonstrates a preregistered
  scientific gate failure.
- `P9_INCONCLUSIVE`: present evidence cannot support a valid decision, such as
  critical metadata, point, insufficient uncertainty/measurement, or simulation
  evidence problems. `EXPERIMENTAL_UNCERTAINTY_UNKNOWN` alone is a limitation,
  not necessarily an execution blocker.
- `P9_EXPERIMENTAL_DATA_REQUIRED`: no authorized dataset sufficient to execute
  the contract exists. This is not scientific FAIL.
- Before suitable data exists after preregistration, state is
  `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`.

After PASS, the only permitted claim is equivalent to
`EXPERIMENTALLY_VALIDATED_FOR_THE_TESTED_2T_CONFIGURATION_AND_OPERATING_DOMAIN`.
Universal and arbitrary-engine predictive validation claims are prohibited.
After FAIL, preserve the complete result; calibration requires a separate phase
and a distinct independent validation dataset. A future modified model version
MUST execute a new validation process; it cannot reuse the previous version's
P9 decision as its own validation.

After preregistration, P4 remains `P4_PASS`; P5–P8 remain
`REVALIDATED_ON_P4_PASS`; P8 remains `BOUNDED_TRANSIENT_INDICATED`;
experimental validation stays `NOT_PERFORMED` until a valid comparison is
completed; predictive validation remains `NOT_CLAIMED`.

#### Scenario: no suitable experimental dataset

- **WHEN** no authorized dataset sufficient for the frozen requirements exists
- **THEN** P9 remains `P9_EXPERIMENTAL_DATA_REQUIRED` or
  `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`, as applicable
- **AND** experimental validation remains `NOT_PERFORMED`
- **AND** the result is not represented as scientific FAIL

#### Scenario: bounded P8 output is proposed as measurement

- **WHEN** a P8 bounded-transient synthetic anchor is offered as experimental
  input or periodic state
- **THEN** P9 rejects that interpretation because P8 is synthetic and does not
  establish periodic convergence or experimental provenance
