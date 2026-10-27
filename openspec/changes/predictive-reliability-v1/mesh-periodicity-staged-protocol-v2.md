# Staged spatial/periodicity protocol V2, 2026-10-27

Prerequisites: inspect common-phase probe, verify its output-time-cut perturbation
against original terminal states, preserve all controls. No physical change
until an isolated defect is demonstrated. This document does not launch runs.

1. If phase-cut perturbation is smaller than spatial differences, localize
separate pressure/density/velocity/species maxima versus crank phase. Diagnose
wave-front motion and limiter activation separately. Do not turn maximum state
error into a power error. Analytic fixed-reservoir tests establish smooth
boundary order; shocks/extrema may correctly trigger first-order limiting.
2. A third 176-cell cold two-cycle V2 diagnostic can test trends, max240s,
10000 accepted steps,5MiB,2GiB reserve. Exact frustum splitting/conservation
and same phases required. Two grids alone establish neither observed order
nor asymptotic GCI. Temporal contribution changes with CFL mesh spacing.
3. If work/fields do not approach an asymptotic regime, stop refinement after
that third level. Compare local/segment refinement versus uniform refinement
cost and verification requirements before any architecture/scope change.
4. Only after spatial uncertainty is quantified: same-run periodicity pilot,
max10 additional cycles,240s wall,150s numerical budget,16MiB,per-cycle native
checkpoint and unchanged detector/all-observable criteria. No RPM warm start.
Report TRANSIENT_AT_BUDGET if exhausted. No automatic extension.
5. Quantitative mesh-independence of periodic work requires periodic states
on multiple grids, not two-cycle cold transients. Estimate that cost from the
pilot before preregistering such a campaign; retain L1/L2 distinction and cost
of full recipe replay. Experimental validation remains separately blocked.
