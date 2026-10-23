# Bounded integrated performance comparison

Baseline: fc4603f, raw motorsim source copy and hashes stored externally before code changes. User-authorized optimization only; X30 and its prepared email remain frozen.

Diagnostic budget: one sequential worker,512MiB per invocation,180s per short point;600s maximum per diagnostic and1800s overall profiling/benchmark envelope excluding regression tests. No full RPM curve. Inputs: existing A/B9000 native configurations unchanged,3cycles each, conventional engineering diagnostics and checkpoints. Same0.5degree grid, CFL, physics, conservation guard and V2periodicity. No coefficient/mesh/tolerance changes.

Use cProfile only to attribute CPU, not to calculate speedup. Compare unprofiled paired runs in alternating order when feasible; preserve all raw outputs externally. Scientific equality: exact state/ledger/checkpoint engine snapshot and timing-independent numerical diagnostics; reject/CFL/step sequence and existing periodicity metrics. Performance fields and producer identities are intentionally separate. Report wall, CPU, solver/trace capture, processing, storage and RSS. Curve speedup remains a labeled projection until a full periodic curve is measured; no new full curve authorized here.
