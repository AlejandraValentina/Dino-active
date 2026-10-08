# Reference engine hybrid harness

## ADDED Requirements

### Requirement: isolated configurable harness

The system MUST provide `REFERENCE_ENGINE_HYBRID_HARNESS_V1` as orchestration,
configuration, convergence, evidence and audit around existing product physics.
It MUST accept arbitrary valid geometry within the existing single-cylinder 2T
P5-C topology, RPM, CFL, finite meshes, compatible boundary
states, four-species initial states, cycle-relative P7 timing, maximum cycles,
checkpoint cadence and replay configuration. It MUST NOT depend on P8 campaign
anchors, fixed P8 mechanics/windows or historical P7 absolute campaign gates.
It MUST NOT modify P4–P9 scientific contracts or introduce physical equations.
It MUST reject non-product atmospheric boundaries and configurable discharge
coefficients because the existing P5-C/P4 interfaces do not expose them; it
MUST NOT accept and silently ignore those inputs.
The physical event phase MUST be in [30°,350°] for the fixed 40° product event
inside the preregistered [30°,390°] cycle. The scheduler offset MUST also be
applied to cycle boundaries and checkpoints, while its inverse is applied to
physical geometry callbacks.

#### Scenario: configurable reference case

- **WHEN** a validated configuration supplies a compatible geometry, mesh,
  operating point, states and event phase
- **THEN** the harness constructs the existing P5-C/P6/P7 topology and records
  exact component-source hashes in the run manifest
- **AND** missing or invalid configuration is rejected before integration

### Requirement: preregistered reference periodic convergence

The harness MUST implement the separately named
`REFERENCE_PERIODIC_CONVERGENCE_V1` exactly as frozen in its preregistration.
It MUST evaluate exactly the listed physical terminal observables and thresholds,
including only P7 `burned_produced` and heat increments from the P7 ledger
(remaining ledger fields are audit-only), apply period-1
precedence, maintain independent period-2 branch streaks, require three
consecutive passing comparisons, distinguish INVALID from FAIL, and stop at the
fixed 400-cycle maximum. It MUST NOT claim that these observables or thresholds
are historical E13.

#### Scenario: period-1 and period-2 classification

- **WHEN** complete compatible cycle records are evaluated
- **THEN** lag-1 PASS streak may classify period-1 before period-2
- **AND** period-2 requires three PASS comparisons in each anchor-relative
  branch independently
- **AND** FAIL/INVALID resets only the affected streak

### Requirement: primary evidence and independent audit

Every run MUST persist accepted trajectory endpoints, complete cycle terminal
states, conservative and four-species inventories, P7 and boundary ledgers,
delivery/short-circuit, work, CFL, admissibility, cycle identity, checkpoints,
restart and independent replay. The offline auditor MUST recompute conservation,
convergence and performance from PRIMARY evidence and MUST reject malformed
numeric values, corrupted hashes, absent fields, summary mismatches and
trajectory-terminal mismatches.

#### Scenario: summary cannot override primary evidence

- **WHEN** a summary claims PASS but its primary trajectory, terminal state,
  ledger or recomputed convergence differs
- **THEN** the auditor rejects the run
- **AND** no stored digest or PASS flag substitutes for direct state comparison

### Requirement: KT100 V2 remains synthetic and separate

The first client MUST derive only its documented facts from V1, mark each
additional required parameter as `SYNTHETIC_ASSUMPTION`, retain the five
exploratory RPM points, and label all computed values as model outputs.
Comparison against V1 MUST be `MODEL_FORM_DIFFERENCE`. It MUST NOT claim
experimental/predictive validation or alter P9 status, contract or hash.

#### Scenario: no Yamaha performance claim

- **WHEN** the KT100 hybrid campaign produces output
- **THEN** outputs remain a synthetic reference fixture
- **AND** P9 stays `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`
