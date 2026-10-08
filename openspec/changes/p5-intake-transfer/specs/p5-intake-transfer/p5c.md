## Requirements

### Requirement: conditional integrated topology
P5-C SHALL couple the existing P5-B intake/crankcase/two-transfer/cylinder
topology to the existing time-varying exhaust port and finite exhaust duct in a
bounded horizon. Evidence SHALL be labelled `CONDITIONAL_ON_P4`.

### Requirement: ledgers and admissibility
The integrated update SHALL expose mass, mY and total-energy ledgers, closed-port
zero flux, admissibility, and stage traces. Internal interface exchanges SHALL
cancel and only atmospheric boundaries may change global inventory.

### Requirement: bounded fixtures
The fixture bank SHALL include closed ports, retained P5-B paths, exhaust-only,
full topology, controlled backflow, restart and deterministic replay. It SHALL
not require periodic convergence or alter P4 criteria.

### Requirement: restart and determinism
A checkpoint after a real update SHALL restore all dynamic chamber, duct, angle and
ledger state. Uninterrupted and resumed bounded runs SHALL agree under the existing
deterministic numeric policy.

### Requirement: resolved causal front
The bounded exhaust causality fixture SHALL locate the principal resolved
compression front by the dominant positive `dp/dt` within predeclared direct
arrival windows. The former 1000 Pa first-crossing remains diagnostic only.
Near, middle and far sensors SHALL preserve finite downstream ordering and
physically compatible effective speeds at two permitted CFL values, without
terminal-reflection contamination.

### Requirement: governance
P4 SHALL remain `BLOCKED`/`NOT_GRANTED`; P5-C may close only as
`P5_C_INTEGRATED_GASDYNAMIC_VERIFIED_CONDITIONAL` when all focal fixtures and
regressions pass.
