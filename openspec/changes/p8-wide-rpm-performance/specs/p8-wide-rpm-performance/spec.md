# P8 wide-RPM indicated performance

## ADDED Requirements

### Requirement: bounded RPM contract

The implementation MUST accept only integer RPM in [2500, 15000], use
`omega_deg_s = 6*rpm`, complete one measured 360-degree window equal to
`60/rpm` seconds, use CFL 0.4, and cut at exact repeated mechanical events.

#### Scenario: domain and timing

Given 2500, 5000, 8000, 11000 and 15000 rpm, each run uses the exact angular
rate and cycle duration; values outside the range or non-integers are rejected.

### Requirement: deterministic preparation and rebase

Each anchor MUST execute exactly two fixed unmeasured preparation cycles 180->900
with P7 disabled and zero heat/burn, then reset measurement accounting while
preserving gas/species state and rebase 900->180 only after proving equal
volumes, volume rates and areas. Preparation MUST use CFL 0.4 and the same
repeated authoritative mechanical event cuts as measurement, with no fixed-angle
stepping. Preparation MUST NOT be described as periodic convergence or steady
state.

#### Scenario: two fixed preparation cycles

Given an anchor RPM, preparation advances exactly from 180 to 900 with P7
disabled and zero preparation heat, then the measured accounting baseline is
reset and the physical state is rebased from 900 to 180 without changing gas/species
state or periodicity claims.

### Requirement: shared authoritative event scheduler

Preparation, uninterrupted measurement and restart continuation MUST use one
builder that repeats every authoritative `Model(case).events` phase by 360*k
across the full absolute interval. Measurement/restart MUST additionally cut at
P7 350/390 and the exact checkpoint probe inside P7. P7 MUST be enabled only
for measurement.

#### Scenario: repeated cuts and restart cut

Given an absolute interval crossing 360 degrees, the preparation and measured
cut lists contain every `Model(case).events + 360*k` phase in that interval;
the measured/restart list also contains 350, 390 and the exact 370 checkpoint
cut, and continuation uses the same list.

### Requirement: authoritative full topology

The campaign MUST reuse the approved S2T-0D-01 mechanics and frozen
atmosphere-intake-crankcase-transfer-cylinder-exhaust-atmosphere P5-C/P6/P7
fixture. It MUST not invent geometry, timing, physical laws or periodic support.

#### Scenario: provenance and topology

Given an existing approved S2T-0D-01 reference, all five anchors record the
same frozen P5-C/P6/P7 topology and synthetic/not-measured provenance; without
that provenance closure is blocked.

### Requirement: measured gates and accounting

The measured cycle MUST contain exactly one P7 event and require captured fresh
mass > 0, burned produced mass > 0, prescribed heat > 0, source/heat
consistency, species conservation, admissibility, CFL <= 0.4, deterministic
replay, and exact restart from a checkpoint inside P7. It MUST report work,
power, torque, pmax, mass residual, energy residual, and all ledger terms.
Global mass and energy residuals MUST use the correct intake-minus-exhaust
external ledger, accepted P7 heat, and both chamber `-p*dV` terms. A lower-phase
conservation defect MUST block closure rather than be masked.

#### Scenario: measured accounting gates

Given a measured anchor, positive captured fresh, burned mass and accepted heat
are required; the evidence also records source/heat consistency, exact restart,
CFL, species, admissibility and mass/energy residual terms. Any failed gate
keeps the campaign numerically blocked.

### Requirement: conditional evidence

Evidence MUST declare `steady_state=false`,
`periodic_convergence=NOT_GRANTED_BY_P4`,
`metric_semantics=BOUNDED_TRANSIENT_INDICATED`, `conditional_on_p4=true`,
`experimental_validation=NOT_PERFORMED`, and
`independent_review=INDEPENDENT_REVIEW_PENDING`. It MUST retain P4 blocked and
P9 stopped. If any anchor fails a measured gate, status MUST remain
`P8_NUMERICAL_GATE_BLOCKED` and conditional closure MUST NOT be claimed.

#### Scenario: conditional closure

Given all five anchors pass all measured gates, closure is
`P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL` and
`P8_READY_FOR_P9_DATA`; this scenario is not satisfied by a blocked anchor.

### Requirement: primary trajectory is authoritative for terminal state

Each durable primary execution MUST persist the fully accepted coupled state
and cumulative accounting at every measured SSPRK2 endpoint, including gas
state, four-species state, external state, P7 ledger/source, fresh delivery,
short circuit, cycle identity, elapsed accepted time and angle. The last
accepted endpoint MUST be compared exactly with the stored terminal before the
terminal digest is rebuilt. The terminal MUST then be compared with the
independent restart terminal and replay execution. A matching digest, restart
pair or pair of summaries MUST NOT compensate for a trajectory mismatch.

#### Scenario: coherently changed terminal is still rejected

Given an intact primary trajectory, change the conservative terminal state,
species state, cumulative ledger, fresh-delivery counter or time/cycle/angle;
then update restart terminal, terminal digest, artifact hashes and summaries
consistently. The audit MUST fail with a trajectory-to-terminal mismatch before
accepting the digest or restart comparison.
