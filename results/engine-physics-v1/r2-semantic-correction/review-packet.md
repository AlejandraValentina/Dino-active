# R2 semantic correction review packet

The corrected point outputs and full provenance are in manifest.json. The
field-by-field old/new values in comparison.json use the persisted pre-correction
R2 offline manifest as the old side. Its producer species residual is shown
separately from the historical gross-partition residual. The first and second
external review FAIL receipts remain preserved in
../r2-external-review/first-review.json and
../r2-external-review/second-review.json. This evidence supersedes outputs only.

The replay used the same accepted cycles: A3000@73, A4000@88, B3000@34,
B4000@38. No campaign or solver execution occurred. The four primary hashes
are recorded in the manifest and independently checked against the external
artifact manifest. campaigns_started is 0.

FMEP uses the matching A-prime or B-prime fixture record: 1000 Pa piston ring
plus 500 Pa bearing/accessory, with SYNTHETIC_ASSUMPTION provenance. The
primary configuration binding, fixture ID, fixture file hash, model hash and
fields used are recorded per point. AFR uses air-only intake delivery and fuel
delivery on the same engine intake boundary and cycle. It yields approximately
49. Fuel unburned is available-at-ignition minus primary fuel burned, with no
clipping.

DR remains defined from the accepted delivery ledger. TE, CE and SE are
undefined because current-cycle fresh retention cannot be identified from the
primary state. The same ratios under `scavenging_partition.metrics.ratios`
are `NOT_IDENTIFIABLE` with null values; previous numerics are isolated under
`superseded_outputs` and in the old/new comparison. Purity is reported as an
exhaust-close composition fraction.
Species conservation is independently summed from all chamber, duct-cell and
network inventories plus exchange/source ledgers; the maximum residual is
below 6e-19 kg for these points.

`mutation-audit.json` records per-point mutations: numeric changes retain valid
metadata for IMEP ×3, cylinder work ×2, indicated power/torque ×3, ISFC ×0.5,
BSFC ×0.5 when defined, brake power/torque ×5, trapped air ×2, incorrect FMEP,
incorrect AFR, and corrupt fuel closure. It also corrupts the partition ledger
and injects false fallback metadata. Every applicable case is detected.
Published metrics are checked against primary work ledgers, RPM,
displacement, fixture losses, fuel ledgers, and the exhaust-close species
snapshot. The old/new IMEP mapping reads the old manifest's `IMEP` field.

The evidence verifier is read-only by default. Regenerating
`provenance-audit.json` requires an explicit `--write` flag.

| Point | FMEP Pa | AFR | lambda | phi | Fuel available kg | Burned kg | Unburned kg | DR | TE/CE/SE | IMEP Pa | BMEP Pa | Torque N m | Power W | ISFC g/kWh | BSFC g/kWh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| A3000 | 1500 | 49.000 | 3.34143 | 0.299273 | 2.50034e-7 | 2.49359e-7 | 6.74446e-10 | 0.329309 | UNDEFINED | 16761.5 | 1289.05 | 0.0252653 | 7.93732 | 517.923 | 6734.59 |
| A4000 | 1500 | 49.000 | 3.34143 | 0.299273 | 2.01918e-7 | 2.01480e-7 | 4.37615e-10 | 0.261730 | UNDEFINED | 12845.5 | -478.994 | -0.00938827 | -3.93255 | 528.577 | UNDEFINED: NONPOSITIVE_BRAKE_POWER |
| B3000 | 1500 | 49.000 | 3.34143 | 0.299273 | 7.49535e-7 | 7.47546e-7 | 1.98911e-9 | 0.738893 | UNDEFINED | 67388.7 | 18819.6 | 0.368863 | 115.882 | 555.175 | 1987.96 |
| B4000 | 1500 | 49.000 | 3.34143 | 0.299273 | 6.77241e-7 | 6.75621e-7 | 1.62067e-9 | 0.605217 | UNDEFINED | 61479.1 | 18730.7 | 0.367122 | 153.780 | 493.250 | 1618.97 |

All corrected point hard gates and numeric mutation checks pass. The
administrative R2 state remains REVIEW for another external review.
ENGINE_PHYSICS_V1 remains FAIL_TERMINAL. Future sweep readiness requires
`EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED`; R2 does not change the generic
fallback implementation.
