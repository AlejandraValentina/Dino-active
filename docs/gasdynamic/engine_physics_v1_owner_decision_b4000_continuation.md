# Owner-authorized B′4000 operational continuation

Decision recorded after `9e5c6c9`, before execution.

## Authorization

`OWNER_AUTHORIZED_OPERATIONAL_CONTINUATION`

The owner selected alternative B solely to complete the already-authorized
B′4000 operating point. This is an operational continuation caused by the
120-minute wall-clock timeout, not a new scientific campaign and not R3. The
prior no-second-campaign prohibition remains historical and is exceptionally
overridden only for this continuation; no further extension is authorized.

The previous execution completed three of four points:

- A′3000: `PERIOD_1 @ cycle 73`
- A′4000: `PERIOD_1 @ cycle 88`
- B′3000: `PERIOD_1 @ cycle 34`
- B′4000: externally interrupted at cycle 9 of the preregistered 47-cycle horizon

The timeout is not a physical classification of B′4000.

## Restart mode

No durable valid checkpoint exists for the exact end of B′4000 cycle 9. The
persisted files contain primary/engineering outputs but no restorable solver
snapshot satisfying the checkpoint contract. Therefore the authorized mode is:

`B4000_OPERATIONAL_RESTART_AFTER_TIMEOUT`

Restart is from the original contractual initial condition. The continuation
must reproduce the persisted cycles 1–9 under the deterministic guarantee before
accepting cycles 10–47. Any mismatch is a hard stop; no invented checkpoint or
trajectory splice is permitted.

## Immutable contract

Fixture, RPM, geometry, initial-condition contract, physics, fuel, combustion,
scavenging, thermal, mechanical losses, mesh, solver, PeriodicDetectorV2,
thresholds, convergence streak, output definitions, plausibility gates and the
47-cycle maximum are unchanged. A′3000, A′4000 and B′3000 are not rerun.

Permitted terminal outcomes are the real detector classification, including
`PERIOD_1`, `PERIOD_2`, `NO_CONVERGENCE_WITHIN_HORIZON @ cycle 47`, or a valid
physical/numerical failure. No additional extension is permitted.
