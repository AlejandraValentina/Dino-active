# Deferred scientific work: `GENERALIZED_RESERVOIR_BOUNDARY_V2`

Status: the user's 2026-10-05 scientific decision resolves the AUD-11 model
selection. `OPEN_END_PLENUM_V2` is implemented and its analytical suite passes;
the single preregistered KT100 campaign did not emit cycle primaries because
the evidence writer raised `KeyError('transfer1')`. The mapping is fixed and
tested, but that campaign cannot be rerun under its one-run preregistration.
This note does not amend historical P5 or its evidence.

The KT100 hybrid fixture r5 stopped before its first complete cycle at each
fixed RPM with `No consistent reservoir inflow branch`. The existing
`Boundary('reservoir')` rejected the requested incoming characteristic branch
for the accepted state. The five receipts and their configuration/source
bindings remain frozen in
`results/kt100-hybrid-model-fixture-v2-harness-20261002-r5/`.

This is a local capability blocker for that reservoir/operating-state pairing,
not a blocker for independent component development. It does not establish
that the reservoir equations are generally defective, nor does it establish a
physical failure of the KT100.

Potential future designs to evaluate under a separate scientific contract:

- A sign-aware characteristic boundary that prescribes only incoming
  characteristics for subsonic flow and extrapolates outgoing information.
- Explicit static or stagnation thermodynamic state and donor composition for
  inflow, with a separately specified supersonic inflow contract.
- A pressure outlet/inlet characteristic treatment with documented switching
  rules across flow reversal and strict admissibility handling.

Each option changes boundary semantics and may change mass, energy, species,
and reflection behavior. It therefore requires a declared scientific model,
independent analytical fixtures for subsonic/supersonic inflow/outflow and
reversal, conservation and admissibility tests, and explicit authorization
before implementation. At the time this note was written, no option was
selected. Do not alter historical P5 or reinterpret its receipts.

## Subsequent decision and separate P3-R1 debt

On 2026-10-05 the user resolved AUD-11 as **CASE B — CAPABILITY LIMITATION**
and selected the ideal stationary-plenum model as a new capability. Its exact
equations and pre-campaign gates are preregistered in
`open_end_plenum_v2_preregistration.md`; this decision does not rewrite the
forensic conclusion or modify V1, P3-R1, or historical receipts.

Separately, the external review noted that P3-R1's large-volume behavior has a
finite-volume/infinite-plenum limit that may not be uniform for long-time
responses. This is future scientific debt only: P3-R1 remains historical and
closed, no P3 rerun or reinterpretation is authorized by the AUD-11 decision,
and this observation is not used to select the KT100 boundary based on
convergence.
