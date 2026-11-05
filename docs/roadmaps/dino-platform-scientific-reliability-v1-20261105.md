# Dino 2T+4T — scientific reliability plan v1

Date: 2026-11-05. Basis: frozen audit commit
`1db6408dd03e7302cc84332cd329c6b8ca0b21a8`, including three independent reviews,
nineteen findings and retained verification logs. Machine-readable stages:
`results/platform-scientific-reliability-v1/plan.json`.

## Objective and authority

Dino is one simulation platform with shared application infrastructure and
**independent native 2T and 4T scientific cores**. Its objective is trustworthy
engineering analysis within a stated model/operating domain, followed by
calibration, blind measured validation and only then bounded predictive claims.
Software maturity, numerical maturity and predictive maturity are separate.

This plan prospectively supersedes the **platform execution ordering** of the
2T-only unified roadmap and the earlier staged core plan. It does not erase or
close their scientific obligations, rewrite a frozen criterion, change a prior
PASS/FAIL or allocate an old budget to a different task. The prior roadmap and
operational control snapshot are retained in the state history. The unversioned
staged-plan input has an exact audit snapshot; later owner decisions and the
durable queue prevail over its outdated entries.

The owner authorized this audit and replanning. **Implementation and numerical
campaign activation are not granted by publishing this plan.** Every future
stage is `NOT_ACTIVATED` until its recorded scope, source identity, criteria,
resource projection and budget are established. The current operational gate
closes delivery of audit/replan only; it is not a platform scientific PASS.

Official `main` remains `5e4ba4d`; strict 4T A/B and cooperative cancellation
remain on `work/dino4t-ab-engineering-v1` at `8b371e2`. Audit and planning are on
their own branch. A later controlled merge must preserve the full histories;
no plan entry silently incorporates branch-only capabilities into main.

## Current maturity and inherited obligations

| Dimension | 2T | Native 4T |
|---|---|---|
| Application | Existing internal TRIAL workflows; shared integration defects need closure | Main native workspace; A/B branch adds strict comparison/exports/cancellation; P1 defects open |
| Numerical | Frozen P4–P8 scoped evidence and periodic 44-cell exploratory A/B; periodic multi-mesh unresolved | Component/reference checks, synthetic baseline GCI, coherent six-cycle A/B; input/detector contracts need correction; integrated two-zone oracle unresolved |
| Physical model | Idealized port law and closures do not identify real losses, scavenging or combustion | Prescribed burn, synthetic losses/Cd and scoped boundary assumptions; unsupported domain fails explicitly |
| Calibration | No complete adopted matched measured-engine package | NOT_PERFORMED |
| Experimental validation | NOT_PERFORMED | NOT_PERFORMED |
| Predictivity | NOT_CLAIMED | NOT_CLAIMED |

The 2T 360°/RPM÷60 convention and 4T 720°/RPM÷120 convention remain native.
Common indicator names need explicit definitions and units: gross versus net
work, mechanical efficiency and scavenging/delivery quantities are not
interchangeable. Cross-family descriptive views must not fabricate a scientific
design comparison. Within-family A/B requires compatible models, operating
conditions, criteria and provenance; a shared UI cannot relax these conditions.

### Preserved 2T obligations

- P0–P9 contracts, frozen expected values and evidence remain unchanged. P9
  canonical SHA-256 stays
  `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`.
- Port-law E1.0/reference verification and historical diagnostics are closed.
  Reuse their results. Do not reopen gradient extrema, angular regions or old
  campaigns without a demonstrated new need and recorded activation.
- 2T V2 and MUSCL remain experimental. A native 4T model also named V2/MUSCL is
  a different implementation and does not adopt or validate the 2T candidate.
- Existing periodic 44-cell A/B evidence does not close 88/176-cell periodicity
  or GCI. **E1.3 stays blocked and is not restarted.** The measured 176-cell
  Brent result did not reach the 2× target. No extension, transfer of budget or
  new performance backend is authorized here.
- Preserve the distinction between pressure-wave changes, numerically
  distinguishable design effects, identifiable scavenging, evidence-led
  closures and measured validation. Do not tune any closure to desired power.
- Cahoon MK.1 remains the selected primary partial dataset, with MT110S as a
  complementary exhaust-change reference. Extraction/reference selection are
  closed. Missing crankcase/geometry/test records remain missing.
- rc7, rc9, rc12 and every historical package/checkpoint/receipt remain intact;
  cleanup is a separate decision.

### Explicit 4T obligations

- Preserve `DINO4T_API_V1`, native config/results and model identity separately
  from legacy `motorsim.four_stroke` and the 2T engineering workflow.
- Fix invalid-input and false-periodicity classification before broader
  studies; do not change scientific tolerances to make a run pass. Any changed
  detector definition or physical default requires its own version and scope.
- Refuse unsafe mid-cycle continuation or represent all required phase/model
  context. Fresh transient seeds, project reopening and exact numerical
  restart are distinct claims. No serializable checkpoint capability exists
  merely because the project can reopen.
- Retain Stage-2 component/GCI evidence at its actual case/model/discretization
  scope. Preserve dirty-source study qualifications and the unresolved
  independent integrated two-zone trajectory reference.
- Keep prescribed combustion and uncertain Cd/heat/friction assumptions
  visible. Extending the fail-closed inflow domain requires independent
  reference evidence, not relaxed guards.
- Create a separate measured dataset, calibration/holdout protocol and
  uncertainty budget. No 2T P9 status or validation tolerance transfers to 4T.

## Priority and dependency sequence

The machine plan contains acceptance text for each stage. VAL2/VAL4 and
PRED2/PRED4 are new plan-local gate IDs; they do not rename a native V2 model
or any frozen P0–P9 contract. The table is a
scheduling graph, not a commercial feature list or blanket execution permit.

| Stage | Depends on | Purpose and observable closure |
|---|---|---|
| C01 — trustworthy native contracts | Frozen audit | Close F01/F02/F04: reject malformed inputs/detector domains; bind result semantics to config; meaningful structured errors/default discovery; valid history preserved |
| C02 — input/display integrity | C01 | Close F05/F07/F14: exact untouched-input identity, edited-field-only changes, atomic stale-result invalidation, correct pressure axes |
| C03 — provenance/build completeness | Frozen audit | Close F06/F08/F09/F12/F13: original trace/config/summary binding, transitive source closure, all consumed bundle inputs, portable paths/bytes and accurate native metadata |
| C04 — lifecycle/assurance | C01 | Close F03/F10/F15/F16: safe state contract, actual task lifetime, explicit historical artifact recipe and terminal receipt ordering |
| C05 — trusted common development base | C01–C04 | Resolve relevant P1 findings, review changed scopes, preserve branch histories and perform controlled main integration; retain exact package/source attribution |
| D2 — matched 2T data | Independent, in parallel | Complete the selected engine/experiment package and uncertainty; preserve targeted archive-request status |
| D4 — matched 4T data | Independent, in parallel | Measured geometry, valve profiles/Cd/area convention and operating/pressure/torque/flow records, with uncertainty and provenance |
| N2 — 2T numerical evidence map | Frozen audit | Independent read-only evidence scoping and preserved unresolved gates; no new E1.3 or historical diagnostic execution |
| N4R — independent 4T trajectory reference | Frozen audit | Isolated oracle against an identified frozen model/config and explicit source hashes; does not wait for Desktop fixes or main integration |
| N4S — 4T study assurance | C01/C03/C04 | Per-endpoint eligibility, continuation and provenance through the corrected relevant contracts; old S4 is not rerun by inertia |
| N4 — scoped 4T numerical assurance | N4R/N4S | Aggregate only the reference and study scope actually demonstrated; no family-wide numerical PASS |
| U2 / U4 — design-effect uncertainty | N2 / N4 | Separate temporal/spatial/model effects and numerical noise for an explicitly selected pair; report unresolved rather than force GCI |
| K2 / K4 — identifiable closures | Respective N and D | Calibrate only with discriminating component evidence; conserve native invariants; one justified component change at a time |
| VAL2 / VAL4 — blind measured validation | C05 + respective D/U/K | Separate preregistered domains/metrics, calibration and holdout; measured and modeled uncertainty; independent review |
| PRED2 / PRED4 — bounded predictive claims | Respective VAL | Complete uncertainty of absolute and design-difference outputs, including correlations; no extrapolation or claim transfer |

Data preparation can proceed while P1 software work is blocked; missing external
measurements do not prevent source contract/provenance fixes. Conversely,
working editors do not make measured validation ready. No stage waits for a
scientific gate of the other family unless a genuinely shared dependency is
identified. A 2T GCI budget block does not automatically block an independent
4T algebraic-reference task.

## Gates and evidence requirements

**Common assurance gate C:** all confirmed P1 behaviors have failing-before /
passing-after regression evidence on the fixed source; no silent input edits,
stale scientific values, unbound primary curves or incomplete clean-build
claims. Protected regressions have explicit verified artifact contexts;
initial missing-context failures and remaining skips remain visible. The
historical 115 list is compared by node/cause, never used as a numeric waiver.
Review and source-level tests precede any separately activated package check.
A historical Windows PASS cannot accept changes made after its source commit.

**Numerical gates N/U, per family:** analytical or independently implemented
references, admissibility/conservation, versioned periodicity and scoped
temporal/spatial error. Preserve each original criterion. New decisive criteria
are justified and committed before runs. Richardson/GCI requires its
assumptions; otherwise report sensitivity or a defensible bound, not a forced
order. An uncertainty measured on the base case is not automatically the
uncertainty of its design delta. L0/L1 labels do not become L2/L3 through a new
report or a larger test count.

**Physical identification gate K, per family/component:** data discriminate
parameters and model alternatives; document nonidentifiability and validity
domain. A power curve alone cannot identify scavenging, burn law, heat transfer
and friction simultaneously. Complexity is not a substitute for evidence.
Relevant numerical error must be bounded and small against the calibration
residual and measured uncertainty, so fitted closures cannot absorb
discretization error. Component/reference bounds can satisfy this requirement;
it does not require a full design-pair uncertainty stage or create a circular
dependency. U2/U4 initially establish the numerical contribution and explicitly
unresolved components; total U95 requires the later data/identification evidence.

**Experimental gates V, separate protocols:** complete engine/condition/measurement
package and unit/phase/reference conventions; holdout frozen before predicted
results; calibration subset explicitly excluded from validation. Include
numerical, measurement, parameter and model-form uncertainty. Existing 2T
5%/U95 engineering targets retain their original domain and prospective
preregistration requirements; they are neither current accuracy nor automatic
4T thresholds. 4T limits remain undefined until a justified own protocol exists.

**Predictive gates P:** distinguish a validated absolute operating point/curve
from a validated design difference. Include covariance between variants and
between measured outputs derived from the same observation. Preserve the 2T
adenda's total-uncertainty obligation; define a separate 4T criterion before
looking at reserved results. Power and torque related algebraically are not
independent validation observations. A synthetic sensitivity PASS cannot close
V or P.

## Resources, activation and stopping

Every stage is initially `NOT_ACTIVATED` with
`budget_authorization=NONE_GRANTED_BY_THIS_PLAN`. The prior 720-second A/B pair
is closed and not repeated. Prior E2/E1.3 budgets are not replenished. There is
no numerical cost estimate disguised as a granted allowance.

For future activation, record source/config identity, needed evidence, criteria,
fixture/domain, cost based on an existing measurement, memory/storage estimate
and margin, accumulated budget and checkpoint policy where applicable. Run
storage preflight with the existing 2 GiB reserve. Use logged bounded runs.
Isolated falsification/reference checks precede expensive integration. Existing
general diagnostic limits are ceilings, not permission to launch a campaign.
No automatic cleanup, build series or budget extension.

Stop a dependent scientific stage on invalid states, failed conservation or
identity, unsupported model domain, unresolved uncertainty, missing measured
data, or exhausted authorized resources. Preserve the failed/partial evidence;
do independent work that does not depend on it. Do not create angular, mesh or
benchmark diagnostics merely to keep a queue active.

External requests retain their exact original recipient/content/authorization
and actual sent/unsent state. This audit sends none. Do not duplicate the Cahoon
request or invent a new engine search to compensate for missing documents.

## Decisions that still require evidence

| Decision | Evidence required before acceptance | Current disposition |
|---|---|---|
| Integrate A/B/fixes into official main | Scoped P1 fixes, regression/context records, independent review and preserved history | Proposed controlled integration; no merge performed here |
| Claim safe 4T continuation | Complete state/phase/model identity and interruption/replay test, or explicit cycle-boundary-only rejection policy | Exact restart not claimed |
| Adopt 2T V2/MUSCL as physical defaults | Own domain/evidence/adoption decision; measured discriminating data as needed | Remain experimental |
| Extend 4T boundary domain | Independent reference for unsupported regime and versioned model decision | Keep fail-closed |
| Accept 4T trajectory/numerical-error scope | Independent trajectory oracle and applicable discretization controls | Targeted future verification, not a global PASS |
| Accept measured validation or design superiority | Separate per-engine preregistration, complete data, holdout and full uncertainty | Both NOT_PERFORMED / NOT_CLAIMED |

Routine contract/serialization/test fixes do not require a new scientific
policy decision. A materially different physical model, model promotion,
unfunded campaign, or new external communication needs the corresponding scope
and authorization. No such choice is made by this plan.

Closure is stage- and family-specific. The platform has no single blanket
scientific PASS that can hide an unvalidated family or extend a case-specific
result outside its domain.
