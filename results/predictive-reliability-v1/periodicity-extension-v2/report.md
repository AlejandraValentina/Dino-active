# Extension cycle17->23 — 2026-10-27

**Improvement overall, recent localized stagnation; no accepted period1/2.**
Completed exactly6additionalcycles18–23, frozen configuration/source/detector.
Stop atcycle23; no automatic further extension or periodic mesh study.
No product solver, physics, CFL, numerical tolerance or rc7 change. SELF_REVIEW,
L1 checkpoint observations; no regenerated primary trajectory audit.

|Cycle|max error/threshold|p90|median|failed/413|workJ|IMEPbar|
|---|---:|---:|---:|---:|---:|---:|
|17|15.092|4.101|.405|151|128.070|10.2761|
|18|7.024|2.924|.353|113|128.617|10.3200|
|19|3.790|1.589|.210|76|129.226|10.3689|
|20|3.625|.873|.147|38|129.794|10.4145|
|21|3.560|.852|.141|32|130.256|10.4515|
|22|3.556|1.333|.119|51|130.618|10.4806|
|23|3.635|1.215|.119|47|130.872|10.5010|

The maximum plateau and rising tail aftercycle21 preclude saying every error
continues to decay. Last lag2 maximum7.063,p90 2.434,91fail versus lag1
3.635,1.215,47fail. No required detector streak, no detected period. Lag2
being worse does not support period2 here; it is not a proof excluding it later.

## Previously worsening30

29have lower normalized error than at17;28now pass. Only fresh-air fraction in
exhaustcell16 worsened overall: ratio1.431->1.604. Global fresh-air inventory
improved1.425->1.027 but still fails. assessment.json records individual metric
histories and all-observable recent trends, not just the failed count.

Near outletcell30, residual fraction .022792 at17->.000639 at23, while burned
fraction .608000->.624578 at20->.612418 at23 and fresh-air fraction
.329956->.345955. The dominant new discrepancy is now fresh/burned replacement,
up to .00727 absolute fraction per cycle in exhaustcells20–23, not simply the
last residual gas. The former residual purge and the new fresh/burned evolution
must not be treated as one scalar error with a guaranteed exponential decay.

An unaligned, local translation-only least-squares diagnostic oncells13–24
explains only about55% of squared fresh/burned change at22->23. It is a local
linearization on cell means, not a measured front speed or proof of causality;
no acceptance states were shifted. The relatively flat tail also changes its
composition. Thus evidence supports both transport/relaxation and changing
amplitude/composition; it does not justify calling all30 changes harmless front
motion. Full same-phase profiles and signed differences remain in assessment.

## Physical balances and drift

At23 total mass.0028196682kg, energy1490.0829J. Changes22->23 are
+3.09705e-6kg,+.818309J; storage is still changing and correctly balanced by
external exchange, work and combustion. Global species budgets per cycle are
in species-budgets.csv. Maximum total conservation residuals: mass9.18e-18kg,
energy3.30e-12J, species7.81e-18kg. No conservation defect is indicated.
Equal-phase cylinder pressure rises5.7516->5.8342MPa over18–23 while work
rises128.617->130.872J. These trends have decreasing increments but are not
stationary. Equal-phase pressure is not an in-cycle pressure maximum or curve.
A single fixed-grid trajectory cannot isolate physical transient from truncation
error or establish a long-term attractor. No localized unbounded divergence has
been demonstrated, but tail-composition stagnation warrants diagnosis.

## Cost, restart and traceability

Numerical extension process84.985s, solver83.714s=13.952s/cycle versus previous
13.452s/cycle, about3.7% difference without a speed-regression claim. Serialization
.219s, detector .023s, constructor/prefix restore .236s. No primary audit ran.
All new native checkpoints restore and detector snapshot replays. Prior checkpoint17
and detector verified by hashes, source dependency identity unchanged. No historical
complete cycles recomputed. Initial launcher stopped before physical execution on
Windows manifest-path separator lookup; reader normalization fixed in this diagnostic
only. Original failure log and successful retry are both retained.

The strict150s ceiling was respected using145s admission/120s solver limits and
checkpoint per cycle. Storage preflight passed. Four focused restart/trend/hash
checks PASS. All new artifacts and runner source hashed in the manifest.

## Decision

Do not extend again automatically. The completed extension shows substantial
relaxation but a new composition plateau. Next read-only work: correlate delivered
fresh charge, combustion species source, outlet inflow/outflow composition and
exhaust residence over the affected cycles, using existing checkpoints/recipes;
then define one bounded trajectory diagnostic if these terminal records cannot
identify the mechanism. No solver change or revised threshold is justified now.
No spatial-periodic study is admitted until a period meets existing criteria
and the required primary replay. rc7 and historical evidence remain preserved.
