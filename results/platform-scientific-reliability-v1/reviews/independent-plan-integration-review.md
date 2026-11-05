# Independent successor-plan integration review

Reviewer: `/root/integration_review`, read-only independent agent.
Decision: **PASS — scoped plan coherence**.
Scope: the prospective roadmap, machine-readable successor plan and OpenSpec successor requirements as read after frozen audit commit `1db6408dd03e7302cc84332cd329c6b8ca0b21a8`. This is a planning-content review, not product/scientific acceptance and not authorization to execute a stage. No tests, solver runs, package builds or repository writes were performed by this review.

## Coverage of the independent integration findings

| Original review finding | Frozen audit finding | Successor closure |
|---|---|---|
| INT-01 no-op input rounding | F05 | C02: preserve exact untouched identity; change edited fields only |
| INT-02 unbound pressure trace | F06 | C03: bind summary/config/trace/metadata and original identities |
| INT-03 stale metrics and pressure | F07 | C02: atomic unavailable-source/selection invalidation |
| INT-04 consumed input omitted from package inventory | F08 | C03: complete input inventory and dirty omitted-input negative test |
| INT-05 dirty source excludes shared dependencies | F09 | C03: transitive source closure and source preimages |
| INT-06 absolute paths and EOL-dependent receipts | F12 | C03: portable byte/path replay without rewriting original hashes |
| INT-07 legacy/native model metadata conflict | F13 | C03: accurate native model metadata |
| INT-08 theta pressure axis labeled RPM | F14 | C02: explicit crank-angle units |
| INT-09 actual task/reopen/restart evidence limits | F15 | C04: observe actual task lifetime and distinguish lifecycle claims |
| INT-10 terminal PASS before final shutdown checks | F16 | C04: terminal receipt ordering after final verification |

The additional static async-failure identity concern is retained under F19/C05 as an issue to reproduce before declaring a confirmed defect. The plan does not silently promote that static concern into demonstrated numerical failure.

## Coherence conclusions

- Main/branch attribution is correct: official `main=5e4ba4d`; strict 4T A/B and cooperative cancellation remain branch-only at `8b371e2`. C05 proposes a later controlled integration; no review language implies a merge already occurred.
- Shared infrastructure is distinguished from the independent native physical cores. Native configuration/result identity, 2T/4T cycle conventions and per-family scientific maturity are preserved. A shared label or UI is not a cross-family comparison criterion.
- C01-C05 prioritize demonstrated contract/input/provenance/lifecycle defects before broader evidence claims. C03 can proceed independently of native contract fixes. The stages are sufficiently scoped to split into implementation tasks after activation without requiring a new architecture by assumption.
- The roadmap and machine plan both declare every successor stage `NOT_ACTIVATED`; publication grants no build, simulation, model promotion, merge or budget extension. Old 720-second A/B and E2/E1.3 budgets are not replenished or transferred.
- The prospective ordering supersedes historical scheduling only. Frozen PASS/FAIL decisions, P9 hash, preregistrations, package/checkpoint receipts and source evidence are retained. The audit findings require new failing-before/passing-after evidence rather than reinterpretation of earlier screenshots as tests of fixes.
- The independent 2T/4T D/N/U/K/V/P paths distinguish software maturity, numerical uncertainty, physical identification, calibration, blind measured validation and predictive claims. In particular, baseline GCI does not certify arbitrary A/B deltas and synthetic periodicity does not close V/P.
- D2/D4 allow useful measured-data preparation independently of software work; missing real measurements cannot be replaced by synthetic geometry. Existing closed reference extraction and deferred numerical investigations are respected.
- The OpenSpec scenarios agree with the roadmap and JSON: preserve native semantics, map the frozen audit, retain historical criteria, require separate measured validation and require explicit activation.

No blocking inconsistency was found within these three plan documents.

## Operational publication check

At the time of this review, the in-progress `program-status.json` still had the old 2T `roadmap_control.roadmap` value and `next_objective=None`. The parent is still completing operational publication. Before claiming the *integrated replanning deliverable* closed, the authoritative state should reference the successor plan and preserve the previous control snapshot/supersession relationship. This must not activate the planned implementation/campaign stages. This scoped PASS does not certify unfinished operational wiring.

## Reviewed content identities

- `docs/roadmaps/dino-platform-scientific-reliability-v1-20261105.md` — SHA-256 `0341db8c50d34079816223ff6c51a3908d5e88bb64279ccd14b89a0e81067fcc`
- `results/platform-scientific-reliability-v1/plan.json` — SHA-256 `e47006277cc24b051e9236185241c0d56ae9b48008f9376b7d6440c20fdeb531`
- `openspec/changes/platform-scientific-reliability-v1/specs/platform-scientific-reliability-v1/spec.md` — SHA-256 `ec9852bd78ff8fd3e5a257296a497394fa664e9b639c1b725c9b5a211acf9670`
