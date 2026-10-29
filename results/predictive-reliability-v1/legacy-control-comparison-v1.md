# E1.4 — legacy control comparison

**Classification: PASS for reproducible control and subsystem attribution.** This is a documentary comparison of existing receipts only. No simulation was rerun, historical result was edited, or physical-equality criterion applied. Results remain transient engineering diagnostics, not periodic power or experimental validation.

## Control identity and reproducibility

- `results/predictive-reliability-v1/baseline.json` confirms the rc7 package SHA-256 `2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a` and records `legacy_results_modified: false`.
- The completed legacy control receipt `integrated-legacy-observer-fixed/receipt.json` and both nozzle receipts share configuration SHA-256 `b7d48c08b56886d803aa4b200eafb589ebec088c22a8e0e5919263305e22e061` for legacy and source-configuration SHA-256 `743a00de51aa4ca214afb5c84b790c1d642c92a4887fa0074bad3d76aa2c1a9c`. The comparison helper verifies configurations differ only by the selected connection model.
- The legacy control completed 720° with 1444 accepted steps, `numerical_gate: true`, and exact checkpoint/restore/next-step replay. It conserves mass to `4.10e-19 kg` and energy to `5.13e-13 J`.
- The earlier `integrated-legacy/receipt.json` remains preserved and records a stopped one-cycle attempt whose checkpoint observer reported a state/ledger mismatch. The later observer-fixed run uses the same configuration identity and provides the completed control; the earlier failure is not erased or treated as a physics result.
- `integrated-spatial-comparison-v1.json` explicitly records `disabled_reconstruction_is_bit_identical: true`, supporting that the inactive spatial reconstruction preserves the first-order reference path.

## Differences by subsystem

The existing `integrated-port-v2-comparison.json` keeps three independently initialized, two-cycle cases at the same crank phase and verifies the same mesh/time boundary. It records `numerical_gate: true`, `temporal_gate: true` and maximum normalized coarse-to-refined time difference `5.9114e-4`.

| Observable | Legacy | Nozzle V2 coarse | Attribution |
|---|---:|---:|---|
| Cylinder work out | 14.6516 J | 31.8770 J | Changed port-connection subsystem; altered boundary mass/energy exchange |
| Crankcase work out | -3.0005 J | -5.7992 J | Changed transfer/intake exchange through selected connection model |
| Fuel-combustion heat | 136.0990 J | 159.5476 J | Integrated consequence of changed cylinder filling and combustion state |
| Peak cylinder pressure | 5.981 MPa | 5.019 MPa | Cylinder state response to changed gas exchange |
| Peak exhaust pressure | 125.85 kPa | 147.93 kPa | Exhaust boundary-wave response to changed port exchange |

For the nozzle cases, coarse-to-refined spatial differences are separately
reported in the same receipt: net indicated work changes from `26.0778 J` to
`26.1371 J`; the largest normalized terminal-state difference is
`5.9114e-4`. The separate spatial comparison attributes the first-order to
MUSCL change and reports its own coarse/refined comparison. Neither comparison
establishes periodicity; the receipt explicitly labels the state
`TRANSIENT_NOT_PERIODIC_POWER`.

These changes are subsystem attribution, not a ranking of physical accuracy.
No model is promoted and no power curve is claimed.

## Evidence references

- `results/predictive-reliability-v1/baseline.json`
- `results/predictive-reliability-v1/integrated-legacy/receipt.json`
- `results/predictive-reliability-v1/integrated-legacy-observer-fixed/receipt.json`
- `results/predictive-reliability-v1/integrated-port-v2-comparison.json`
- `results/predictive-reliability-v1/integrated-spatial-comparison-v1.json`

The comparison's receipt hashes are recorded in `integrated-port-v2-comparison.json`; the historical files remain unchanged.
