# P7 prescribed heat and synthetic burn progress

## ADDED Requirements

### Requirement: prescribed source law
The implementation MUST use start 350+360k degrees, duration 40 degrees,
q_f 800000 J/kg, the sinusoidal primitive and derivative, with no source outside.

#### Scenario: bounded source
Given a captured event, source is zero before start and after start+40, and its
integral over the window is the captured fresh mass and q_f times it.

### Requirement: captured P6 inventory
The event MUST capture only fresh_air+fuel and fixed proportional fractions;
residual and burned mass MUST not be reheated or converted.

#### Scenario: capture excludes processed mass
Given four P6 masses, only fresh-air and fuel are fixed as event inventory.

### Requirement: stage-coherent conservation
Sources MUST be applied in the same SSPRK2 stage evolution, with zero source
mass, proportional heat, admissible species, and no burned mass above capture.

#### Scenario: conservative stage source
Given valid SSPRK2 stages, source species sum is zero and heat equals q_f times
burned progress within numerical tolerance.

### Requirement: evidence and dependency
The implementation MUST record F01-F08 fixtures, restart, deterministic replay,
two resolutions and ledgers. Closure is conditional on P4; no experimental
validation or independent review is implied.

#### Scenario: conditional closure
Given all bounded fixtures pass, closure remains conditional on P4.
