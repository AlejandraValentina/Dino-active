# Design

## Baseline and isolation

Baseline is HEAD `2752e2e9e95b1548e0395f15d718d255b632c3a2` (also
`origin/main` when this change was opened). The six untracked
`results/kt100-hybrid-model-fixture-v2-harness-20261002*` directories are
preserved. P9's frozen spec has SHA-256
`79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`.
Changes after the external audit HEAD `46592f5` are committed: fuel-library
CRUD/catalog, the P5 rhoY primitive-view adapter, and dynamic reed integration.
The latter two product areas are not used to satisfy this v1 gate; dynamic reed
and the commercial Fuel Library are post-v1 backlog. The P5 adapter is reviewed
as an existing narrow compatibility behavior, not modified by this change.

No P4–P9 code, contract, artifact, threshold, or evidence is changed. The
one-cell atmospheric boundary and chemical combustion capabilities below are
new versioned contracts; legacy `nonreflecting`, `LEGACY_CHARACTERISTIC_V1`,
P7, and old fixtures retain their historical meaning.

## Mathematical definitions

For the cylinder, positive indicated work is `W_cyl = integral(p_cyl dV_cyl)`
over one accepted 360-degree 2T cycle. Crankcase gas work is separately
`W_cc = integral(p_cc dV_cc)` using crankcase volume and the same pressure-work
sign convention. Net piston gas work is `W_piston,net = W_cyl + W_cc`. It is
the sole gas-work input to mechanical-loss conversion. Mechanical loss work is
the sum of explicit, provenance-bearing loss terms; brake work is net piston
gas work minus losses. Crankcase work must not be counted again as FMEP.

The frozen slider-crank geometry supplies displacement `Vd`; IMEP is
`W_cyl / Vd`, BMEP is `W_brake / Vd`, and cycle frequency is `RPM/60`. A
negative or zero brake result remains a signed result/undefined performance
where the metric requires positive power; no clipping is allowed.

`SYNTHETIC_FUEL_SURROGATE_V1` is a non-real, versioned fuel. It records an
explicit C/H/O mass composition, oxygen mass fraction in the synthetic fresh
air, analytically derived stoichiometric AFR, explicitly assumed LHV and
combustion efficiency, provenance, canonical hash, and frozen run snapshot.
No ANCAP, measured-fuel, or calibrated-fuel claim is allowed. For the initial
surrogate, C/H/O mass fractions are 0.86/0.14/0, oxygen in fresh air is 0.232,
and LHV is 43,000,000 J/kg; each is `SYNTHETIC_ASSUMPTION`. Stoichiometric O2
mass per fuel mass is `m_O2/m_f = (8/3) w_C + 8 w_H`; stoichiometric air/fuel is
that value divided by 0.232. Configuration validation recomputes and checks
this derived value.

The closure uses `FUEL_COUPLED_COMBUSTION_V1` with the immutable surrogate
snapshot defined above. The later additive Fuel Library consumer
`FUEL_COUPLED_COMBUSTION_V2` is outside the v1 gate; the extensible Fuel
Library, commercial fuels, and Uruguay-specific profiles remain
`POST_2T_V1_BACKLOG` and are not used as prime-fixture evidence.

At ignition, only the cylinder's accepted four-species inventory is eligible
for burning. A frozen Wiebe cumulative progress `x(theta)` determines the
requested burned fraction of the ignition-time trapped fuel; it does not set
the available energy. Per stage, requested incremental burn is limited by
unburned trapped fuel and oxygen available in fresh-air pseudo-species at the
stoichiometric demand. Consumed fuel and corresponding fresh-air mass are
converted to `burned` pseudo-species without changing total mass; `residual`
is unchanged. Chemical source is `dQ = dm_fuel_burned * LHV * eta_comb` and
is applied to cylinder total energy within the same SSPRK2 stages. Wiebe only
distributes this bounded total chemical release in angle. Zero fuel or zero
available oxygen gives zero chemical heat. Unburned fuel remains in its
existing species inventory. Historical P7 is not called or changed on this
path.

## Scavenging and performance semantics

The declared v1 approximation is `SINGLE_ZONE_PERFECT_MIXING_SCAVENGING_ASSUMPTION`.
Four-species inventories at exact geometry-derived transfer/exhaust closures
are authoritative for retained mass and composition. Gross P6 crossing
ledgers remain separately labelled. A metric is `UNDEFINED` if its physical
numerator, denominator, closure event, accepted state, or provenance is
unavailable. Trapping efficiency, short-circuit fraction, and all efficiencies
must lie in [0,1]; values outside that domain are rejected as invalid evidence,
never clipped. Delivered, trapped, short-circuited, unburned, and burned fuel
are distinct. Actual AFR uses trapped fresh air / trapped fuel. ISFC/BSFC are
defined only for a periodic accepted cycle, positive respective power,
explicit surrogate provenance, and a complete fuel ledger.

Every versioned engineering output carries status, provenance, definition
version and periodicity dependency. Existing V1–V4 records keep their old
semantics; the new integrated closure output schema is additive.

## Fixture and mesh freeze

`FIXTURE_A_PRIME` is a newly versioned, initially uniform-pressure synthetic
configuration with quasi-static reed, three transfers, physical atmospheric
boundary, expansion chamber, synthetic fuel, chemical combustion, thermal
loss, and mechanical losses. `FIXTURE_B_PRIME` is separately frozen with
piston-port intake and no reed, two transfers, a materially different exhaust
chamber, distinct RPM, atmospheric boundaries, the same versioned fuel,
combustion, thermal, and mechanical-loss capability. Both use exact
`SYNTHETIC_ASSUMPTION` provenance for synthetic parameters. Neither rewrites A,
B, or C.

For these synthetic fixtures, the open inlet reservoir uses the inherited
0.98 fresh-air / 0.02 fuel mass-fraction donor as an explicit
`SYNTHETIC_ASSUMPTION` representing premixed intake charge. It is not claimed to
be ambient-air composition or a measured carburetor setting. The outlet donor
remains fresh-air only. This fixed input avoids adding an injection or
carburetor model to the gate.

Before either campaign, a mesh study is preregistered and completed for at
least three systematically refined transfer and exhaust meshes with fixed
geometry, physics, RPM, and integrator settings. The convergence observables
are complete-cycle mass/energy residual, peak cylinder pressure, retained
fresh mass, trapped fuel, and cylinder indicated work. The sufficient mesh is
the coarsest tested mesh for which each observable differs from the next
refinement by at most 2% and both meshes meet strict admissibility and ledger
closure; campaign meshes must be no coarser. This is a numerical-sufficiency
test, not an experimental-accuracy claim.

For this gate's preregistered refinement comparison, the positive dimensional
observables use the symmetric relative difference
`abs(a-b)/max(abs(a),abs(b))`, with two exact zeros treated as equal and a
single zero compared against the nonzero magnitude. Signed mass/energy ledger
residuals instead use their already-bound primary absolute-term scale: compare
`abs(r_fine/S_fine - r_coarse/S_coarse)` against `0.02`. This is a 2-percentage-
point bound on the change in signed ledger-scale residual, avoids an undefined
relative percentage at roundoff zero, and does not replace the independent
float64 `gamma_n` conservation gate for either mesh.

Each prime fixture has a fixed 20-complete-cycle horizon, no early stopping and
no post-result extension. Campaign preregistration freezes the exact hashes of
geometry, boundaries, mesh, thermal/fuel/combustion/loss configuration,
producer, solver, periodicity detector V2, thresholds, evidence schema, and
restart/replay procedure. Periodicity is PASS only under the pre-existing V2
detector's frozen thresholds and streak rules; otherwise report explicit
`NO_CONVERGENCE_WITHIN_HORIZON`, `INVALID`, or `FAILED` without promotion.

## Evidence and review

The cycle primary stores accepted SSPRK stage states and fluxes, boundary and
network reactions, source terms, species ledgers, work terms, energy ledger,
fuel snapshot/hash, output records, solver/config/fixture/detector hashes, and
restart anchors. Offline audit reconstructs RHS/fluxes and cycle outputs from
primary states; it does not trust summaries alone. Every rejected inadmissible
trial is persisted with angle, attempted step and reason; retry/halving may not
be silent. Restart and independent replay compare physical arrays, species,
ledgers, events and outputs, not only digests.

C12 mesh-level A1 exposed a replay-boundary defect: the auditor reconstructed
the accepted SSPRK angle increment from `angle_end - angle_start`. At large
unwrapped angles, that subtraction can differ by a few ULPs from the exact
nominal/retry step passed to the solver, changing derived RPM and volume rates.
The correction replays the validated nominal proposal or final retry half-step
and checks the stored endpoint within four ULPs. This preserves the scheduler,
retry chain, numerical trajectory, and all scientific thresholds. The initial
C12 run is retained as incomplete/invalid evidence; a separately committed R1
preregistration records the corrected replay source before any repeated mesh
execution.

The corrected R1 study completed and audited all four A′ meshes and B′ meshes
0–2. B′ mesh 3 stopped before primary output because the combustion source
rejected a tiny negative species value that the integrated state validator
already permits within its 1e-14 kg roundoff tolerance. The R2 correction
aligns the combustion input check with that existing validator and keeps
available reactant amounts clamped at zero; it does not clip or burn negative
species. R1 artifacts remain intact and are not mixed into the R2 mesh study.

Internal adversarial review is required before a candidate; it is labelled
self-review unless a separate, actually independent reviewer and durable
receipt exist. A terminal candidate is not experimental validation and makes
no KT100 claim.
