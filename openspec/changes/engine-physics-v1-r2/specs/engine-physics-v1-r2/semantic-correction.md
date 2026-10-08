# R2 output semantic correction

This is an additive correction to the offline R2 output adapter. It does not
change the solver, the four accepted primary cycles, any physical threshold,
the terminal `ENGINE_PHYSICS_V1 = FAIL_TERMINAL` result, or the administrative
`ENGINE_PHYSICS_V1_R2 = REVIEW` state. The corrected evidence supersedes only
the defective R2 outputs. The primaries and both external review FAIL receipts
are retained.

## Contract sources

- FMEP comes from the `MECHANICAL_LOSS_MODEL_V1` in the matching A-prime or
  B-prime fixture record. The fixture record's fixture ID and engine
  configuration are checked against the primary; the primary configuration
  identity is checked against its bound `fixture_sha256`. The fixture file and
  the model payload each have their own recorded SHA-256. The primary binds its
  configuration identity, while the model record is associated through the
  fixture ID and exact configuration match. The model terms are `1000 Pa` for
  `piston_ring` plus `500 Pa` for `bearing_accessory`; their declared
  provenance remains `SYNTHETIC_ASSUMPTION`.
- Metered AFR is the accepted primary's air-only intake delivery divided by
  fuel delivery, both integrated over the same cycle and the same engine
  intake boundary: `fresh_air_intake_delivery_kg / fuel_delivered_kg`.
  Lambda uses that AFR and the fuel snapshot's elemental stoichiometry; phi is
  its reciprocal. Missing or zero fuel and absent stoichiometry stay undefined.
- Fuel available is the accepted `fuel_available_from_ignition_snapshot_kg`
  ledger. Fuel burned is the primary `fuel_burned_kg` ledger. Fuel unburned is
  their difference with no clipping. This accounting is distinct from the
  exhaust-close unburned snapshot and from gross metered fuel.
- DR remains defined from the valid documented fresh delivery ledger. The
  primaries do not identify which fresh-air species at exhaust close arrived
  during this cycle rather than being carried over from cycle start, so TE,
  CE, and SE are `UNDEFINED` with
  `CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE`. Purity outputs are named
  exhaust-close composition fractions and make no scavenging-efficiency claim.
- Species conservation is independently recomputed by summing initial and
  terminal species inventories in every chamber, duct cell, and network
  volume, then subtracting external exchange, combustion sources, and P7
  sources. The producer's stored species residual is not used as the proof.

The corrected hard checks include fixture loss consistency, metering AFR,
fuel closure and burned availability, scavenging dependency/identity,
independent partition conservation, output provenance, and independent numeric
consistency checks from the primary work ledgers, RPM, displacement, fixture
loss model, fuel ledger, and exact exhaust-close species snapshot. These bind
cylinder work, IMEP, indicated/brake power and torque, BMEP, ISFC, BSFC, and
trapped species quantities to their physical inputs. Changing a published
number while keeping valid metadata must fail its numeric consistency gate.
The versioned output checks use relative tolerance `1e-10`, default absolute
tolerance `1e-12`, BMEP absolute tolerance `1e-9 Pa`, and ISFC/BSFC absolute
tolerance `1e-8 g/kWh`; each point manifest records these values.
An unresolved fixture produces undefined mechanical outputs and a hard
failure; no generic FMEP fallback is permitted.

The offline partition's trapping, charging, and scavenging efficiencies are
`NOT_IDENTIFIABLE` in current R2 outputs because its gross crossing inputs do
not identify current-cycle fresh retention. Superseded numeric values are
retained only in an explicitly historical section. The evidence verifier is
read-only by default; `--write` is required to regenerate the audit receipt.
Before any future `FULL_RPM_SWEEP_V1`, readiness requires
`EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED`: all sweep points must bind an
explicit loss model and fail closed instead of silently using the 85 kPa
standard fallback.

The offline replay uses only the four accepted primaries and starts no
campaign. The evidence manifest records `campaigns_started = 0` and retains
`REVIEW` pending `EP-R2-EXTERNAL-REVIEW`.
