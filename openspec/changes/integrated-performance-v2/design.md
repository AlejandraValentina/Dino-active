# Design — Integrated Performance V2

1. Reuse the existing A/B 9000 RPM engineering configurations and current solver identity. Run only bounded three-cycle diagnostics; use CPU profiling for attribution and separate unprofiled timing for speedup.
2. Record per-stage and per-subsystem measurements where available. Treat cProfile cumulative times as overlapping; use exclusive CPU attribution for shares. Record allocation counts/peak RSS and persistence timings separately.
3. Rank candidates by measured total contribution and expected safe reduction. First choice is one local algorithmic improvement preserving arithmetic order and operation count semantics where possible. Do not add Numba or another dependency unless the profile supports it and focused equivalence tests establish compatibility.
4. Freeze exact config/input hashes. Compare full states, traces, species ledgers, physical diagnostics and restart results. If operation order changes, define field-specific tolerances from the current numerical contract before accepting the optimization.
5. Stop after one significant stable gain; proceed to another hotspot only when the first gain is material and all equivalence/restart checks pass.
