# MotorSim 2T Commercial Core

## Why

MotorSim has verified scientific components, but its current editable geometry
and integrated two-stroke topology do not yet form a configurable general-purpose
2T engine model. This program adds new capabilities without editing the frozen
P4–P9 scientific contracts or claiming experimental validation.

## What Changes

- Evolve the existing reference harness and KT100 synthetic fixture without
  changing P4–P9 historical gates or using KT100 as P9 evidence.
- Add reusable configurable 2T gas-exchange geometry/topology, scavenging
  accounting, intake/exhaust components, thermal and combustion capabilities,
  crankcase and mechanical-loss models, fuel accounting, and engineering outputs.
- Extend experimental-data infrastructure without changing the frozen P9
  confirmation contract, and qualify an independent second reference case when
  reliable provenance exists.
- Track the 16 authorized program phases in one durable task queue. Each new
  scientific metric or acceptance threshold is specified before the campaign
  that uses it.

## Boundaries

- P4–P8 history and P9 contract/hash remain unchanged; no experimental or
  predictive claim is implied.
- New capability schemas and contracts are versioned independently. No solver
  duplication, hidden calibration, or unsupported parameter provenance.

- Blocked phases do not stop independent phases; the program stops only at the
  global hard stops authorized in the user order.
