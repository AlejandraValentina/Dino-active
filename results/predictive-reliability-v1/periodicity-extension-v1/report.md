# Same-configuration periodicity extension — 2026-10-27

**Progress toward a repeatable state, but periodicity not demonstrated.** One
bounded extension completed6cycles12–17. Stop at registered limit, no additional
extension or spatial campaign launched. No solver, thresholds, CFL or model change.
L1 checkpoint-derived evidence and SELF_REVIEW, not full L2 trajectory acceptance.

## What the old nine cycles showed

Cycles3–11: maximum error/threshold399.0->112.85, median2.352->1.079,
p90 29.867->24.192, RMS45.888->20.660. Last4cycle trends of the210failed metrics:
67improving,137worsening,6stable using a descriptive5% band (not acceptance).
The worst metrics were residual fractions in exhaustcells18–25. Other ducts
improved markedly; exhaust p90 became worse even as the largest peak declined.
Global species stored inventories were still evolving. This mixed transient
justified one limited extension, without promising a PASS.

## New evidence

|Cycle|Work J|max ratio|p90 ratio|
|---|---:|---:|---:|
|11|133.225|112.846|24.192|
|12|131.251|115.660|21.993|
|13|129.552|105.936|16.349|
|14|128.351|79.654|13.485|
|15|127.765|51.184|7.930|
|16|127.737|29.137|6.067|
|17|128.070|15.092|4.101|

Cycle17:151/413metricsfail, median.4054,p99 14.3508,RMS3.4952.
Among currently failed metrics118improve,30worsen,3stable over last4cycles.
Failure groups:123exhaust,24otherducts,2global species,2chambers/integrals.
Worst residual/burned fractions are now near exhaustcells27–30, consistent with
an evolving compositional field rather than one permanently failing cell. This
is not proof that the entire discrepancy is passive purging or that boundary
coupling error is absent. Signed inventory changes, work/IMEP, equal-phase cylinder
pressure, normalized distributions and all413individual histories are preserved
in CSV/JSON. Equal-phase pressure is not an in-cycle maximum pressure claim.

Lag2 maximum remains44.229 versus lag1 15.092; lag2 p90 9.389 versus4.101.
No detector period1/2 or required streak. Lag2 being worse offers no support for
a period2 attractor at this point; it cannot exclude a later multi-cycle state.
The turning work trajectory alone is not proof of physical multi-periodicity.
Consistent configuration/source and deterministic restart reduce ordinary restart
and identity errors. Conservation distinguishes real inventory storage/external
exchange from numerical balance leakage. It does not separate fixed-grid
truncation from actual model transient evolution. No mesh-independent physical
variation, final power or convergence-cycle count is inferred from this run.

## Restore verification and budgets

Started native checkpoint11 (3960degrees), whose SHA and detector matched the
source manifest. Reconstructed persisted detector history without physically
recalculating cycles1–11. Separate restart test advanced only the80stored steps
of the earlier40degree partial segment; physical state and ledger match exactly.
Six new native checkpoints restore; old/new detector snapshots replay correctly.
Old partialcycle12 remains preserved and is not mislabelled a native checkpoint.

Limit:6cycles,120solver seconds/180wall seconds,16MiB. Stop atcycle17,
TRANSIENT_AT_BUDGET, no error; progress-based early stop was not triggered.
Wall82.66s (process), solver80.711s =13.452s/cycle, serialization approximately
.21s, detector .016s, constructor+prefix restore .338s. Isolated native restore
.0038s;40degree verification replay1.182s. Minor timing fields exclude final
receipt write. No primary audit ran (timing audit0means not performed).
Prior source-bound cycle2 audit cost76.87s, a different state/workload; do not
call this an audited per-cycle overhead measurement of cycles12–17.

Final absolute mass residual8.64e-18kg, energy1.94e-12J (rounded bounds).
Inventory changes are much larger and are physically balanced, not inferred
from residual alone. No demonstrated numerical conservation or admissibility bug.

## Decision and remaining work

No correction is justified. Continued transient relaxation is the most compatible
explanation, dominated by exhaust composition and some coupled chamber/inventory
change, but fixed-grid error and wave/boundary interactions remain unseparated.
Do not increase the budget repeatedly to force acceptance. This extension closes
at its cap. The checkpoint17 supports a future explicitly costed study, not an
automatic new invocation. Periodic spatial convergence preparation is conditional
on a full-observable accepted period and primary replay, not merely steady work.

The numerical solver consumes almost all measured time; optimizing JSON or
restoration would save little. A justified future optimization would profile a
short checkpoint segment, identify a dominant repeated numerical kernel and
compare immutable state/ledger/checkpoint results against the reference before
adoption. Audit trace/replay cost also deserves separate measurement before a
large mesh study. No speculative optimization or physics change was implemented.
No claims of spatial independence, physical experimental validation or rc7 change.
