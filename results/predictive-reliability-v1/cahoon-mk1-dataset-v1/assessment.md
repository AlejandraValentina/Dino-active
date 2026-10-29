# Cahoon 1971 — MK.1 extraction and Dino readiness

Date: 2026-10-29. Review: SELF_REVIEW. **Result: verified partial experimental
reference; not ready for a Dino prediction or quantitative validation.**

## Source and extraction

The legitimate Queen's University Belfast thesis endpoint was newly reached via
the repository's administrative file route. The original PDF is retained
outside Git under `DINO_ARTIFACT_ROOT/predictive-reliability-v1-cahoon-20261029/cahoon-1971-verified-full.pdf`.
SHA-256: `292ce05bf386df7b6f4980c1232e46e5ed74ae798d01992d9fd473ed76c11963`;
23,498,890 bytes; 264 PDF pages. The failed/truncated transfer is retained
separately. The institutional bibliographic record states that pressure-time
histories were measured in inlet, transfer and exhaust pipes and at two
cylinder positions, and that induced airflow was measured; it describes three
engine versions. This establishes what the thesis reports, not uncertainty or
availability of raw sensor files. [QUB thesis record and PDF](https://pure.qub.ac.uk/en/studentTheses/unsteady-gas-flow-through-a-naturally-aspirated-two-stroke-intern/).

Pages below are PDF page numbers unless identified as printed. The engine-details
table, printed p.11 (PDF p.19), was rendered and visually checked. MK.1 entries:
bore 82 mm; stroke 72 mm; rod centres 139.7 mm; trapped compression ratio
6.57; crankcase compression ratio 1.6; exhaust opens 96° ATDC; inlet opens
76° BTDC; transfer opens 115° ATDC; total effective exhaust/inlet/transfer
port widths 58/46/64 mm; inlet and transfer pipe lengths 7/4 in; carburettor
flow diameter 32 mm; exhaust equivalent-pipe lengths L1/L9/L2/L3/L4/L5 are
17/22/32/32/41/56 in and diameters D1/D9/D2/D3/D4/D5 are
1.94/2.92/3.75/3.75/1.625/1.625 in. These are published engine details,
not independently measured as-built dimensions with tolerances.

Table 4.1, PDF p.79, is titled “MK.1 Engine Test Data”. Ten legible rows are
preserved in `performance.csv`; obscured rows at 6250–6750 rpm were omitted.
Chapter 4, PDF pp.77–78, says performance characteristics were calculated
from test-bed measurements and corrected to SAE standard atmospheric
conditions. It does not provide the raw values or correction factors there.
No measurement uncertainty or repeatability is stated with the table. Do not
label its values raw, uncorrected, or full-throttle absent further evidence.

Figure 4.13, PDF p.91, is visually labelled cylinder, MK.1, RPM=6000 and plots
pressure ratio against crank angle. It is retained as a future pressure-trace
candidate, not digitized: the plotted measured/calculated line identity,
absolute reference/calibration, numeric samples and digitization uncertainty
have not been separated. Chapter 4 states that both experimental traces and
THROUGH FLOW predictions appear across Figs. 4.10–4.150.

## Derived check

Using the published bore and stroke as a circular cylinder gives
`Vd = π B² S / 4 = 380.233 cm³` (derived, not a separate measured
displacement). For the ten clear table rows, brake torque is derived from
reported bhp as `T[lb·ft] = bhp × 5252.113 / rpm`; BMEP is recomputed with the
two-stroke identity `bmep[psi] = bhp × 396000 / (rpm × Vd[in³])`. Recomputed
BMEP differs from the printed rounded values by at most 0.064% (Table 1
rounding). This is an internal dimensional/rounding consistency check, **not**
an independent validation of Dino and not an independent second measurement:
torque and BMEP are derived from the same brake-power identity.

The resulting torque and BMEP columns are explicitly marked derived in the
CSV. No uncertainty has been invented; uncertainty propagation is therefore
not claimed.

## Remaining blockers for a defensible Dino comparison

1. The MK.1 details table and the THROUGH FLOW input sheet, Appendix 2,
   Fig. A2.2 (PDF pp.253–255), do not identify one coherent as-tested exhaust
   revision. The sheet is explicitly an MK.1 calculation input at 4400 rpm;
   its D1/D9/D2/D3 are 1.95/2.94/3.625/3.625 in, versus
   1.94/2.92/3.75/3.75 in in the engine-details table, and its K9 is 23 in versus L9 22 in.
   The sheet's port widths agree with the engine-details table. The mismatch must not be
   resolved by choosing one or averaging them.
2. Absolute crankcase clearance/free volume, measurement angle and included
   cavities are not established by the ratio 1.6. The exact definition and
   effective swept volume behind the trapped-compression ratio are also not
   confirmed for Dino input.
3. Port profiles/area-versus-angle laws, complete duct and junction geometry,
   exact sensor positions, matching test settings (fuel, ignition, ambient and
   thermal state), raw test data, SAE correction details, and measurement /
   repeatability uncertainty remain unverified.
4. Appendix 2 labels additional data “assumed for design purposes, unless known
   for analysis.” The sheet lists 1320 R exhaust-wall, 560 R transfer-gas and
   520 R inlet-gas temperatures; they are not established here as measured test
   conditions. It lists 4.6 atm at exhaust opening, while the sheet legend also
   says this pressure is otherwise assumed as BMEP/20. Chapter 4 says the
   THROUGH FLOW input takes this quantity from experimental diagrams when
   available. Its provenance for this particular sheet is therefore unclear.
   That calculation is not an independent blind prediction of the measured
   pressure trace.

These gaps preclude constructing a traceable, non-mixed MK.1 Dino configuration
and make a run misleading. No solver run, calibration, curve digitization,
model change, or use of synthetic substitute parameters was performed. The
partial gain is a source-verified measured brake curve and a measured pressure
trace candidate with a reproducible consistency check.

## Concrete acquisition path

A prior draft to QUB's library/archive route is retained at
`results/experimental-data-readiness-v1/cahoon-archive-request.md`; it was not
sent. It already asks the correct MK.1 questions and identifies verified QUB
archive contacts. Update that request only if it is sent under separate
authorization. The exact need is an erratum/record tying the MK.1 engine-details
table or Appendix 2 dimensions to the measured build, plus crankcase-volume convention,
port profiles, raw/corrected test records and uncertainty/repeatability. No
communication has been sent.

Validation remains `NOT_PERFORMED`; predictive accuracy remains `NOT_CLAIMED`;
rc7 is unchanged and V2/MUSCL remain experimental.
