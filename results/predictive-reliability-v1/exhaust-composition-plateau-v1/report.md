# Focused composition audit at23 and bounded check24–25
2026-10-27, SELF_REVIEW. No product solver/model/criteria change. rc7 preserved.

**Verdict: insufficient evidence to separate remaining physical relaxation from
spatial/numerical transport sensitivity.** A conservative transient is demonstrably
active in the discrete physical model; no species accounting defect was found.
This is not proof of a mesh-independent physical relaxation mode or periodicity.

## Existing evidence before any replay

Inventories at17..23 are in inventories.csv: cylinder, crankcase, intake, primary,
secondary, boost and exhaust separately, total and four composition components.
These are species masses inkg; they sum to total mass. Components are model labels
fresh_air/fuel/residual/burned, not individually conserved chemical elements.
Combustion consumes fresh_air and fuel and produces burned with zero net mass;
residual has no combustion source. Testing each label without its source would
incorrectly diagnose combustion as lost mass.

Global checkpoint ledgers contain external fluxes and reaction sources, but no
gross per-interface reversal integrals. Cycle-local traces are empty. Inferring
interface transport from inventory changes would be circular. A single recorded
cycle23 replay was therefore necessary; it adds no new physical cycles.

## Independent actual interface balance

Restored checkpoint22; replayed recorded accepted steps with original solver,
observing actual two SSPRK2 face fluxes in a diagnostic wrapper. Species integrals
are stage weighted; positive/negative contributions accumulated separately using
the common gas-mass-flux direction. Terminal gas/species/ledger exactly match
original checkpoint23. Wall15.96s, below90s/8MiB budget. Streaming flux evidence
is L1, not a substituted L2/release audit.

Every component in every subsystem closes independently:
Delta species inventory = net interface transport + reaction source.
Maximum absolute residual9.49e-19kg. Same flux cancels at connected endpoints;
all signed/gross sums agree with total gas-mass flux. Four focused hash/restart/
source/flux checks PASS. No clipping or manufactured interface flux was used.

Cycle23 exhaust:
- Fresh inventory change+5.74563mg, burned-2.99462mg, residual-.163297mg,
  fuel+.443765mg; all match measured net face transport, with zero duct source.
- Cylinder->exhaust gross mass225.533mg; reverse exhaust->cylinder43.581mg.
- Exhaust->atmosphere178.920mg; atmosphere->exhaust0 during this cycle.
  Other interfaces do reverse, including intake and each transfer; all gross
  species directions are preserved in interface-audit.json.
- Cylinder fresh reaction-100.438mg and burned reaction+107.265mg are balanced
  by transport and storage. A global-only check would not establish these
  separate subsystem balances; the observed face fluxes do.

The fresh accumulation is concentrated in exhaust storage and is not an error
near a tiny global component. Changing inlet composition, reverse exchange at
the cylinder end and finite residence all participate. This single cycle cannot
establish which dominates the entire multi-cycle relaxation eigenmode.

## The47failed observables

46are in exhaust:31species fractions and15cell masses. One is global fresh-air
inventory. failed47.json/CSV record exact cell/region, physical values22/23,
signed absolute change, metric/tolerance ratio and histories18..23.
The maximum at23 is burned fraction in exhaustcell21: absolute change.0072702,
threshold.002,ratio3.6351. Fresh-air changes are similar and opposite over the
outer duct. Maximum ratios20..23:3.6252,3.5598,3.5561,3.6351. This is a real
plateau in cycle-to-cycle composition change, not a constant cell-count artifact.
The remaining residual gas is decreasing, but fresh/burned distribution is not
stationary. A local translation-only fit explained only about55% of squared
composition change in the inspected region; it cannot replace a transport audit
or prove that these changes are entirely moving-front effects.

## Tolerances near zero

convergence.py compares duct species by absolute fraction change <=.002,
not division by the species fraction. Global species differences normalize by
total cycle-start mass, not by tiny species mass. Failing duct fractions here
are >=.33887 in the two compared states. Thus small residual fractions near zero
are not inflating this plateau. Cell-mass tests are relative to cell mass; their
normalization and physical absolute changes are separately recorded. No threshold,
normalizer, detector or acceptance policy was changed.

## Turnover and time scale

Mean stored exhaust mass / gross outgoing mass at23 =11.185cycles, or.07457s at
9000RPM. This is a gross turnover estimate, not a fitted exponential decay time.
Bidirectional cylinder exchange and nonuniform fields violate a simple perfectly
mixed reservoir assumption. Residual mass nearly halves22->23 while fresh/burned
still change, so one universal purge time cannot be assigned from these balances.
No remaining-cycle count or final power is projected from this estimate.

## Conditional final two-cycle check

Because actual transport/source balances show continuing conservative storage
without a defect, owner condition allowed a brief check24–25. It was preregistered
at2cycles/45s total (40s admission/35s solver), checkpoints each cycle, same source,
configuration and restored detector. Completed in27.86s, solver27.16s; no error.
Both new native checkpoints and final detector snapshot restore. Existing evidence
is unchanged. Native observations remain L1; no primary audit or spatial study.

|Cycle|max ratio|p90|median|failed|
|---|---:|---:|---:|---:|
|23|3.6351|1.2153|.1191|47|
|24|3.6600|1.0580|.1166|42|
|25|3.3475|.8392|.0791|37|

Work24/25=131.0308/131.1111J. Lag2 max at25=7.0075 versus lag1=3.3475;
no period1/2 detected. Progress in distributions continues, but maximum-tail
improvement remains small. **No more automatic extensions.** Fixed-grid evidence
cannot yet distinguish a slow model mode from numerical transport sensitivity.
Next justified work is a controlled temporal/spatial diagnostic of one existing
cycle/state with unchanged physics, not a longer blind continuation. Protocol and
cost must precede any such replay. No correction or periodic predictive claim
is justified by the present audit.
