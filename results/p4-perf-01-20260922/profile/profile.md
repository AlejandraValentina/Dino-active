# P4-PERF-01 Profile BEFORE (A-O)

## N250
- wall 41.71s solver 35.31s total_with_io 46.11s
- top5:
  - C_hllc_hlle: 11.47s (24.9%)
  - D_fused_interior: 7.51s (16.3%)
  - I_diagnostics: 6.40s (13.9%)
  - F_coupling: 5.84s (12.7%)
  - B_reconstruction: 4.59s (10.0%)

## N400
- wall 72.89s solver 62.92s total_with_io 79.85s
- top5:
  - C_hllc_hlle: 20.05s (25.1%)
  - D_fused_interior: 13.12s (16.4%)
  - F_coupling: 10.21s (12.8%)
  - I_diagnostics: 9.97s (12.5%)
  - B_reconstruction: 8.02s (10.0%)
