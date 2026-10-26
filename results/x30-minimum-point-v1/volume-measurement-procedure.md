# X30 crankcase free-volume measurement procedure

## Purpose

Obtain one defensible pre-compression free gas volume for the X30 Senior at a stated crank angle and with a stated boundary, for use only after the external request is answered or the measurement is performed on an identified assembled engine.

This is a measurement procedure, not a measurement. No value is fabricated here.

## Definitions

- **Crank angle θ:** degrees ATDC. Record the minimum-volume condition at TDC (0° ATDC) and, for verification, BDC (180° ATDC).
- **Boundary A — crankcase only:** gas volume from the crankcase cavity up to the transfer-passage inlet plane, sealed at that plane. Use this if the 1D model represents transfer passages separately.
- **Boundary B — crankcase plus transfer passages:** gas volume up to the cylinder transfer-window plane, sealed at the window. Use this only if the model does not add transfer volumes separately.
- **V_cc(θ, boundary):** connected free gas volume at θ under the chosen boundary, excluding oil, coolant-intensive cavities and any volume outside the sealed gas boundary.
- **Reed/valve dead volume:** include only if it is part of the sealed gas boundary; state it explicitly.

Do not mix Boundary A and Boundary B, and do not add transfer volumes twice.

## Method 1 — manufacturer value

Accept a manufacturer value only if it states θ, the boundary definition and the inclusion/exclusion of inlet and transfer volumes. Otherwise treat it as an undefined number and do not use it.

## Method 2 — volumetric measurement

1. Use an assembled, identified X30 Senior with no fuel and no ignition source. Remove the spark plug.
2. Fix the piston at θ with a positive mechanical stop; verify θ independently.
3. Seal the intake and exhaust boundaries. Seal the transfer boundary at A or B, consistently.
4. Install a calibrated burette or syringe with a low-pressure port and a differential pressure gauge. Check for leaks at the working pressure before measurement.
5. Fill with dry air at near-ambient temperature and low pressure. Record absolute pressure, temperature and the burette reading before and after filling.
6. Correct for apparatus dead volume and gas compressibility. Repeat three times; report the mean and the combined uncertainty.
7. Repeat at TDC and BDC. Report `V_cc(θ)`, boundary, method, temperature, pressure, date, operator and uncertainty.
8. Do not use the 40 ml gearbox oil volume as a gas volume. Do not derive the volume by multiplying partial drawing dimensions.

## Uncertainty and acceptance

Report at least: burette resolution, dead-volume correction, temperature, pressure, leak check, reed deflection and repeatability. A value is acceptable only with θ, boundary, method and uncertainty. A value without those is not usable for configuration freeze.

## Deliverable

Create `input-intake.json` with:

```json
{
  "source": "manufacturer | measurement",
  "engine_revision": "identified revision",
  "crank_angle_deg_atdc": 0,
  "boundary": "A | B",
  "includes_inlet": false,
  "includes_transfer": false,
  "precompression_volume_cm3": null,
  "uncertainty_cm3": null,
  "method": "description",
  "date": "YYYY-MM-DD",
  "operator": "name or lab",
  "notes": "sealing plane and exclusions"
}
```

No solver run and no configuration freeze may occur until this file contains a non-null volume with a valid boundary.
