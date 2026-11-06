# C01 — independent scientific acceptance criteria before remediation

Review type: `INDEPENDENT_REVIEW`, read-only design review.

Frozen source inspected: `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1` in the audit worktree. This note sets prospective acceptance and high-value adversarial checks before the decisive remediation tests. It does not activate other plan stages, modify physics or criteria, or edit operative status/OpenSpec. No solver or test suite was run to produce this note.

## Scientific boundaries

- Valid physical/numerical configurations retain their exact original values and canonical identity. Validation must not insert defaults, round values, cast a fractional valve count to an integer, relabel provenance, or change selected models in the caller's object.
- The native 4T equations, mesh/time stepping, CFL, registered default periodicity tolerances and their inclusive `<=` decisions remain unchanged. The existing two six-cycle A/B endpoints remain a positive compatibility case; their stored bytes and hashes must not be rewritten.
- Invalid historical artifacts remain available as historical evidence with explicit semantic issues and ineligibility/unverified classification. Do not sanitize an old false periodic label into a new scientific result or silently repair an old config/hash.
- Do not introduce arbitrary coefficient signs or numeric conservation cutoffs to make examples pass. Require finiteness and documented domains. A negative fitted polynomial coefficient is not by itself proof of negative modeled friction over its domain. If a stricter physical admissibility policy lacks an existing contract, record that limitation instead of making a new physical choice inside C01.
- C04 exact continuation, C02 editor/display behavior and new scientific campaigns are outside this correction scope. Rejecting an invalid API contract is different from claiming those capabilities are fixed.

## Required acceptance

### Typed configuration and options

1. Validate the type of every section, list, table and consumed scalar before construction. Physical numeric fields are finite numbers excluding booleans. Discrete counts are genuine integers; `1.9`, `True`, numeric strings and truncating casts must not silently select a different design.
2. Cover conditional harmonic/tabulated lift schemas, Cd tables and lengths, segment entries and optional intake-plenum/feed-duct structure. Reject nonfinite table entries and contradictory/malformed table shapes using existing physical domains.
3. Unknown-key recognition is section-aware and recursive, including `lift`, `discharge_coefficient`, `segments`, `periodicity` and nested feed ducts. A legitimate name placed in the wrong section is unknown there. Any compatibility escape such as `allow_unknown_keys` stays explicit and does not grant scientific comparison eligibility.
4. Expected malformed configuration failures return the documented structured issues/error channel with useful paths. Do not catch all exceptions as CONFIG_INVALID and hide programming defects that belong to INTERNAL. Preserve the contract's explicitly documented programming-error boundary.
5. API `max_cycles` and wall-limit options reject bool/noninteger/nonfinite values as applicable before computation. Validate callbacks/events and override shape through documented channels. Advertised default models agree with the actual omitted-key behavior, without changing that behavior or materializing defaults into historical config identities.

### Detector and periodicity meaning

1. Reject invalid detector domains before computation: counts are actual positive integers, and error thresholds are finite with the allowed zero/positive boundary explicitly derived from the existing contract rather than chosen after tests. Unknown detector keys are reported.
2. A periodic status requires the complete detector decision, including minimum complete cycles and a sufficient genuinely passing streak. A property computed solely from `streak >= consecutive` must not certify zero comparisons or ignore minimum cycles.
3. Preserve the default `imep_rel=0.002`, `trapped_mass_rel=0.002`, `pressure_trace_rel=0.005`, `mass_imbalance_rel=0.005`, `consecutive=2` and minimum-cycle behavior for valid inputs. Keep exact-threshold comparisons inclusive.
4. Detect contradictory imported histories by numerical metrics and the recorded tolerances. A stored `passed=true` flag is not authoritative when its metrics fail. Missing or nonfinite metric data cannot establish a passing transition.
5. Preserve valid zero-cycle incomplete/failed results with `final_cycle=None`. Such results can remain historical and informative but cannot become periodic performance endpoints.

### Semantic result/config binding

1. Bind operating conditions (including exact RPM and equivalence ratio), resolved model choices, configured detector criteria, configuration identity and scientific provenance to the resolved configuration, not merely summary-to-summary equality.
2. Validate native schema/type/finite required metrics, run status, termination, complete-cycle count, history length and periodicity consistency. Optional null quantities that are physically undefined remain distinguishable from zero; a legitimate zero-cycle partial is not rejected just for lacking final metrics.
3. Derived expectations should come through the owning 4T API/contract, avoiding new Desktop imports of runner/solver internals. Preserve additive version compatibility with an explicit validation/trust profile where old evidence cannot satisfy new fields; never claim that adding a validator recomputes the old physics.
4. Public comparison and the real import/history loader apply the same semantic eligibility. Two summaries agreeing on an incorrect RPM/model must still fail when their resolved configs disagree. Matching SHA values prove byte binding, not scientific consistency.
5. Arbitrary truthy `validation_evidence` cannot establish experimental or predictive acceptance. Preserve original claim text and evidence bytes but classify unverified claims as unverified/ineligible until a separately defined scientific evidence protocol can verify them. This correction grants no new validation claim.
6. Conservation fields must have coherent structure, finite nonnegative diagnostics and internally consistent maxima where defined. Apply only an existing applicable numerical acceptance criterion; do not invent a universal threshold from the observed pair. Periodicity, conservation, model validity and experimental validation remain separate propositions.

## High-value prospective test matrix

| Area | Falsifying cases | Positive controls |
|---|---|---|
| Scalar/type contract | `count=1.9/True/"2"`; NaN/Inf Cd/friction/geometry; section `None/[]/string`; invalid API option types | Exact original example and both saved A/B resolved configs; deep equality and unchanged hashes before/after validate |
| Recursive schema | `intake_valve.lift.typo_ignored`; `numerics.bore_mm`; typo in Cd/segment/periodicity/plenum feed; mismatched lift/Cd table lengths | Legitimate harmonic and tabulated lift, all documented optional groups/notes/models |
| Detector | `consecutive=0/False/1.5`; no comparisons; one passing transition with `min_cycles=3`; forged passed flag; NaN metric | Recorded actual A/B histories each end with two passing transitions; exact-threshold and immediately-above cases; default decisions unchanged |
| Semantic binding | Both summaries claim 7000 RPM while configs are 6000; both report V1 while configs select V2; summary detector differs from config; cycles zero/history empty with periodic flag | Both authentic stored endpoints and original exact comparison ID remain eligible without rewriting their bytes |
| Status/history | `completed`+wall/cancel termination; periodic+insufficient cycles; mismatched history/cycle count; nonfinite required final metric | Real one-cycle/two-cycle partial/cancelled records remain incomplete/nonperiodic; zero-cycle partial with null final metrics remains representable |
| Scientific claims | `CLAIMED/PERFORMED` plus `validation_evidence=True`, arbitrary object or unauthenticated string | Existing NOT_PERFORMED/NOT_CLAIMED records and their original provenance unchanged |
| Boundary usage | Direct comparator and imported on-disk fixture with self-consistently rebound summary/meta/ref hashes; bypass the shared UI with native API | Same classification and errors regardless of the entry path; unrelated 2T contracts unaffected |
| Error distinction | Bad sections and override structures; deliberately injected internal programmer exception | Expected bad input is CONFIG_INVALID/OPTION_INVALID; unexpected fault remains INTERNAL rather than falsely blamed on input |

Use in-memory monitor/semantic fixtures and isolated temporary file imports first. They are contract tests, not simulated measurements. A full new A/B pair or periodicity campaign is unnecessary. Valid numerical behavior can be supported by unchanged numerical kernels, existing targeted physical regressions, the saved genuine endpoints and any separately justified bounded equivalence check; do not create a numerical budget merely to satisfy this note.

## Review of fixed source

The later independent review should inspect both positive and negative paths, especially bypasses in the native API and direct comparator. A green test count is insufficient if tests normalize fixtures to the new implementation or discard historical invalid records. Any actual result accepted previously but newly found inconsistent must be retained with original evidence and an explicit issue record.
