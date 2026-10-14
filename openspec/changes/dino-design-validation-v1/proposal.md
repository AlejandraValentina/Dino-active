# DINO_DESIGN_VALIDATION_V1

## Why

Verify that supported motor and exhaust edits made in Dino Desktop alter the IntegratedEngine2T solver inputs and produce reproducible, auditable physical responses. Keep synthetic exploratory evidence distinct from experimental validation and campaign evidence.

## Scope

Audit project → motor/variant → native IntegratedEngine2T configuration → solver → primary evidence → results comparison. Exercise two exhaust geometries at short diagnostic operating points under bounded runtime. Record geometry/mapping, wave/pressure/flow response, numerical variability, conservation, audit status, time and convergence. Do not treat transient power as a performance result.

Check the existing versioned powervalve endpoint resolution and its boundary tests without altering historical 27 PERIOD_1 / 3 NUMERICAL_INVALID classifications. Correct software binding defects in a versioned change with tests; do not silently change equations or physical gates.

Prepare an experimental dataset import contract for RPM, torque, power, test conditions, uncertainty and provenance. Keep measurements separate from synthetic output and define error metrics without claiming validation.

## Non-goals

- Full RPM campaign, KT100, calibration, or experimental-validity claim.
- Changing equations, CFL limits, periodicity criteria, hard gates or historic classifications without a separately versioned and justified contract.
- Interpolating missing/invalid comparison values.
