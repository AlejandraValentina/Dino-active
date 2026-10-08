# Two-stroke v1 closure R2 specification

## Scope

This superseding specification evaluates existing synthetic R2 evidence only.
It does not alter the original `two-stroke-v1-closure` requirements or its
terminal result. The original v1.0 gate remains:

`MOTORSIM_2T_V1_CLOSURE_V1_0 = FAIL_TERMINAL`

The separate result under this specification is:

`MOTORSIM_2T_V1_CLOSURE_R2 = REVIEW`

until an external review of this B1–B3 repair is complete.

## ADDED Requirements

### Requirement: Historical v1.0 gate is immutable

The original gate MUST retain its exact 20-complete-cycle requirement and its
prohibition on post-hoc horizon extension. R1 MUST remain evidence of its
failure. Offline V2 results MUST be recorded as P1 streak 0, P2 branches 0,
and detected period None for A′ and B′.

#### Scenario: Original gate remains terminal

- **WHEN** the superseding R2 change is evaluated
- **THEN** the original v1.0 gate remains `FAIL_TERMINAL` with its exact
  20-cycle horizon and is not rewritten as a passing gate.

### Requirement: R2 provenance is explicit

The record MUST distinguish the preregistration used by B′ (`9b73a1e`, SHA
`37e0e6855d7acac7164ddb006d51bf505e10453e417baa78fde351632dd9ab98`) from
the later operational amendment (`dddf243`, SHA
`7a712f7811ab883a753075b7531f4f8c6ddd404605ef4e68c7767ed13d84c3ee`). It MUST
not state that the preregistration never changed. It MUST preserve both A′
attempts and the producer difference for B′.

The amendment MUST be described as operational only: horizons, the residence
rule, solver, physics, fixtures, mesh, fuel, combustion, thermal, mechanical
losses, RPM, `PeriodicDetectorV2`, thresholds, and convergence streak remain
unchanged.

#### Scenario: Provenance versions are distinguishable

- **WHEN** R2 provenance is inspected
- **THEN** the B′ initial preregistration and the later operational amendment
  are both named by commit and SHA, with no claim that the preregistration was
  immutable throughout execution.

### Requirement: Existing R2 results are not rerun

The existing result artifacts MUST be used without new A′/B′ campaigns or R3:
A′ `PERIOD_1 @ cycle 73/111` and B′ `PERIOD_1 @ cycle 38/47`.

#### Scenario: Existing R2 results are reused

- **WHEN** this gate is evaluated
- **THEN** the existing result artifacts are referenced without rerunning A′,
  B′, or creating R3.

### Requirement: Review and regression evidence

The independent review artifact for HEAD `53f66c6` MUST be preserved with its
verified SHA and MUST be identified as covering only that HEAD, not this repair.
The P4–P8 regression MUST have a durable command, HEAD, timestamp, result,
warnings, log, summary, and relevant hashes. Integrated closure tests,
OpenSpec strict validation, diff check, LFS fsck, and the frozen P9 hash MUST
also pass.

#### Scenario: Evidence is durable

- **WHEN** the closure receipt is inspected
- **THEN** the review, regression, integrated tests, and contract checks are
  available as versioned or durable artifacts with their hashes.

### Requirement: Classification

This repair MUST classify N1–N7 as `POST_2T_V1_BACKLOG` or provenance debt,
without changing numerical evidence. The gate may become `PASS` only after an
external review confirms B1–B3. Until then it is `REVIEW`, and no
`GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED` or
`MOTORSIM_2T_V1_DEVELOPMENT_FREEZE_CANDIDATE` claim is permitted.

#### Scenario: Review gates classification

- **WHEN** no new external review of this repair exists
- **THEN** the R2 status remains `REVIEW` and no PASS or freeze candidate is
  declared.
