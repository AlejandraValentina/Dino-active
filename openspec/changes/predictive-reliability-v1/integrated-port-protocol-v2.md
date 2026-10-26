# Bounded integrated port V2 diagnostic protocol

Preregistered before these integrated calculations, 2026-10-26.

Input: the existing native configuration of variant A, 9000 RPM, identified by
the hash-bound periodic-rpm-curves-v1 receipt. Construct from its original initial
conditions; do not resume, convert or relabel a historical periodic checkpoint.
Run two revolutions, sufficient to include the first combustion and subsequent
blowdown. They are transient engineering diagnostics, never stationary power.

Cases: original coupling at maximum 0.5 degree; explicit equivalent-nozzle V2 at
0.5 degree and 0.25 degree. The latter is time refinement, not changed CFL.
Retain all existing geometry, EOS, thermal, fuel, combustion, species, boundary,
scavenging, numerical tolerances and max_cfl. Only the versioned port descriptor
differs between the first two cases. No warm start and no campaigns.

Budget per case: 240 s, 10000 accepted steps, 0.1 GiB durable artifacts; reserve
2 GiB according to existing preflight. Stop safely at an accepted-step boundary
on budget or model-domain failure, record the exact error and bound checkpoint.
Only existing CFL/positivity step rejections permit adaptive step subdivision;
a physical domain error must not be hidden by repeated step reductions.

Keep primary stage records in a new gzip stream, with hashes. Compression here
is encoding of newly generated diagnostics; historical artifacts are untouched.
At each complete revolution, record a hash-bound compact checkpoint and verify
its restoration. At the final state, compare the next identical accepted step
on original and restored engines, bit-for-bit, without advancing the scientific
diagnostic's declared terminal state. Keep both stage port endpoint primitives,
species, full face fluxes, selected branches, shock area and causal speeds.

Acceptance: every actual step passes original admissibility and CFL checks;
global mass/species residual <=1e-9 of initial+throughput scale, energy residual
<=1e-8 of initial+source+work scale. No absent domain branch, pressure floor, mass
cap or legacy fallback. Restart/state/ledger exact replay. Report new-model versus
old-model differences in work, mass flows, trapped species, pressure ranges and
final state, without requiring increased power. Report 0.5/0.25-degree differences;
if maximum normalized terminal-state difference exceeds 1%, the time-resolution
gate remains open pending a bounded refinement; do not claim mesh independence.

These are L1/L2 numerical engineering records and SELF_REVIEW, not an independent
review, experiment, predictive validation or a release claim. Passing permits
opt-in candidate development and the dependent spatial verification stage.
