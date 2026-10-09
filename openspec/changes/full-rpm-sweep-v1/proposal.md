# FULL_RPM_SWEEP_V1 readiness

## Scope

Prepare a preregistered, no-campaign WOT RPM sweep for the existing integrated
two-stroke engine configurations. The sweep uses only hash-bound A-prime and
B-prime configuration fixtures, resolves a mechanical-loss model explicitly
for each configuration, and fails closed before solver work if any binding or
preflight check fails.

This change does not reopen `ENGINE_PHYSICS_V1` or R2, alter solver/physics,
change accepted thresholds, or execute a sweep. The fixture models and fuel
inputs remain synthetic assumptions conditional on P4; no experimental or
predictive claim is made.

## Readiness outcome

`FULL_RPM_SWEEP_V1_READINESS_PASS` means only that the immutable inputs are
bound, explicit mechanical losses resolve, the existing integrated-engine
configuration validators accept every preregistered RPM point, and focused
tests pass. It is not an execution result. The campaign remains `NOT_STARTED`.
