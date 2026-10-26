# Bounded integrated endpoint V2 check — before calculation

Prerequisites: limited endpoint prototype passes positivity/simplex, smooth
boundary-order reference, unchanged Sod/contact limits, both-stage conservation,
signed donor tests, same-model restart, cross-model rejection and explicit
frozen-reader rejection. Static legacy/V1 physical states/ledgers match the
pre-boundary source bit for bit on the control fixture. No physical equation
change. Dynamic reed moving-wall work still uses the original cell pressure;
no second-order claim for that mechanical/geometry coupling.

One A9000, 44-cell, independently initialized diagnostic only, using
`MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2` and the existing equivalent-nozzle
V2. Original geometry, numerical criteria, h/T, species, combustion, RPM and two
revolutions. Same maximum 0.5-degree step, event schedule and original admissibility
retries. No warm start, full RPM campaign, new mesh or periodic claim. This is a
check of a specifically measured truncation correction, not continuation of the
earlier mesh refinement budget.

Per execution: max 240 seconds, 10000 accepted steps, 100 MiB estimate with
original storage preflight/reserve. Preserve full stage stream, initial/native
360/720 checkpoints, hashes, conservation and actual restart equality. Compare
with `spatial-muscl-coarse` descriptively; do not demand increased work or power.
Acceptance retains normalized mass/species <=1e-9 and energy <=1e-8, original
admissibility, full 720-degree phase and restart equality.

Then replay/audit the second revolution from its actual native checkpoint with
the unchanged producer/source guard and exact recorded accepted dt, original
rejection reproduction and 240-second bound. No new trajectory or source/hash
rebinding. This provides critical numerical evidence, not measured validation.
If the candidate fails, preserve state/logs and diagnose it before any subsequent
engine execution. No automatic budget extension.

P4–P8 regressions must pass before numerical closure. Candidate remains opt-in;
baseline rc7/default/previous spatial version and historical evidence persist.
Engine mesh independence, periodicity and real-port losses are separate gates;
a successful two-revolution correction check does not establish any of them.
