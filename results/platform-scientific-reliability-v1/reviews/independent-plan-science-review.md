# Independent scientific review of prospective platform plan

**Classification:** `INDEPENDENT_REVIEW`, read-only, scientific scope.

**Disposition:** **REVISE**, limited to unnecessary scheduling prerequisites and an explicit calibration-error acceptance refinement. This disposition concerns plan coherence, not scientific acceptance of Dino or a reinterpretation of historical gates.

The draft reviewed is the prospective plan written after frozen audit commit `1db6408dd03e7302cc84332cd329c6b8ca0b21a8`:

- `docs/roadmaps/dino-platform-scientific-reliability-v1-20261105.md`
- `results/platform-scientific-reliability-v1/plan.json`
- `openspec/changes/platform-scientific-reliability-v1/specs/platform-scientific-reliability-v1/spec.md`

No tests or solver runs were performed in this plan review. The reviewer did not edit the repository, activate tasks, change scientific criteria or authorize expenditure.

## Coherent and appropriately bounded provisions

1. The plan explicitly describes one application platform with native independent 2T and 4T scientific cores. It retains 2T 360-degree/RPM-divided-by-60 and 4T 720-degree/RPM-divided-by-120 semantics, and does not equate gross/net work or scavenging quantities through a shared label.
2. Main revision `5e4ba4d` is distinguished from branch-only strict A/B and cooperative cancellation at `8b371e2`. A future controlled merge is proposed, not silently represented as completed.
3. All scientific review findings have a prospective home: false periodicity, section/numeric validation, summary/config semantics and advertised defaults in C01; source/primary-artifact provenance in C03; unsafe continuation in C04; sensitivity eligibility and the unresolved trajectory oracle in N4. The original A/B evidence is retained at its actual narrow scope.
4. Frozen 2T P0-P9 obligations and the canonical P9 hash remain protected. E1.0 and closed historical diagnostics are not reopened. E1.3 and its multi-mesh/GCI obstruction remain explicit; old budgets are not replenished or transferred. Experimental 2T V2/MUSCL are not promoted by native 4T model names.
5. Stage-2 4T GCI is not generalized to every design or to its A/B difference. The independent integrated two-zone trajectory reference remains open. Prescribed combustion, synthetic Cd/loss inputs and the fail-closed boundary domain remain visible limitations.
6. Numerical, physical-identification, calibration, experimental and predictive maturity are separate. Each family has a distinct measured package, calibration subset, preregistered holdout and validation gate. No 2T P9 state or 5-percent target is inherited by 4T.
7. The uncertainty obligations include numerical/measurement/parameter/model components and correlations for design deltas. Algebraically related power and torque are not treated as independent observations. An uncertainty bound on the baseline does not automatically become a bound on the design difference.
8. External-data acquisition has parallel independent stages. Missing 2T data cannot be replaced by synthetic geometry, and neither family gains measured validation from the other's evidence.
9. `implementation_or_campaign_activation=false`, `NOT_ACTIVATED` task states and `NONE_GRANTED_BY_THIS_PLAN` budgets consistently restrict the current delivery to audit and replanning. Scope, source/config identity, criteria and resources must be recorded before future execution. The old 720-second A/B pair is not repeated automatically.

## Changes required for a coherent dependency graph

### PLAN-SCI-01 — unnecessary common-product barrier on independent scientific preparation

The roadmap and machine plan currently make N2 and N4 depend on C05. C05 itself waits for C01-C04, including editor/display fixes, lifecycle work and controlled main integration.

N2 is a read-only map of preserved scientific evidence; it does not require those product changes. The independent two-zone trajectory reference in N4 can also be prepared and assessed against a frozen, identified solver source with its own scope and budget. Neither needs to wait for completion of every editor/display defect or a main merge.

That dependency conflicts with the plan's correct narrative that independent scientific preparation can proceed while unrelated product work is blocked. It is not a reason to activate the work now.

Recommended correction:

- Remove C05 as the prerequisite for the N2 evidence map; retain its dependence on the frozen audit and explicit future activation.
- Split N4 into an independent reference/oracle item (N4R or equivalent) and a study-eligibility/provenance item (N4S or equivalent).
- Let the reference item use the frozen identified scientific source without requiring C05. Let the study item depend on the relevant contract/provenance/lifecycle corrections, such as C01/C03/C04.
- If useful, keep N4 as an aggregate of both items so U4 still requires complete relevant numerical readiness. Do not make C05 or one family’s scientific gate an automatic prerequisite for unrelated read-only preparation.

### PLAN-SCI-02 — make numerical error in calibration explicit

The overall uncertainty gates are strong, but the individual K2/K4 acceptance text should explicitly require that relevant numerical error be bounded relative to measured uncertainty and the calibration residual. Otherwise a fitted closure could compensate for unresolved discretization error before the later validation gate exposes it.

This need not force K to wait for a full design-pair U stage. Appropriate component/reference numerical bounds from N can be sufficient. The acceptance should prohibit using closure fits to absorb known unresolved numerical error, and should record the bound used. No circular dependency or new campaign is required merely by this clarification.

## Acceptance of the revised plan

Once the machine graph and roadmap remove the unnecessary barriers and make the K-stage numerical-error condition explicit, this reviewer expects a scoped **PASS for prospective scientific-plan coherence**. That PASS would mean the obligations, ordering and limits are coherent; it would not mean any future implementation, scientific campaign, model adoption, measured validation or predictive claim is accepted or activated.
