# Equivalence plan — Performance V2

- Freeze A/B native configuration SHA-256 and source identity for every run; three cycles per run, same 0.5 degree grid, 9000 RPM, standard-v1 loss, 512 MiB limit and existing periodicity settings.
- Exact equality required for engine state, species state/ledgers, per-cycle work, heat, peak pressure, accepted/rejected step counts, checkpoint payload (excluding source identity where producer identity is intentionally different), and timing-independent diagnostic arrays when the selected donor path is unchanged.
- Existing fail-closed state/species validators remain active at SSPRK stage boundaries. Public `donor_species` validation remains in the hot path. Zero mass flux continues to validate both sides and return the existing zero vector.
- Compare wall and process CPU on three-cycle unprofiled A/B runs. Report RSS from runner summaries. cProfile is attribution only and is excluded from speedup.
- Run focused species, integrated solver, and restart/replay tests; verify conservation ledgers and physical outputs. No CFL, tolerance, geometry, coefficients, combustion law, or periodicity threshold changes.
- If implementation changes operation order or exceeds exact output equality, define and justify field-specific tolerances from existing contracts before acceptance; do not claim bitwise identity.
