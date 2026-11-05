# Unified scientific replan — delivery record

The [roadmap](../../docs/roadmaps/dino-platform-scientific-reliability-v1-20261105.md)
and [machine plan](plan.json) were written after committed audit freeze
`1db6408dd03e7302cc84332cd329c6b8ca0b21a8`.

The [audit report](../platform-integration-audit-v1/audit-report.md) records
10 P1 and 9 P2 findings, attributed independent reviews, reproducible probes,
artifact checks and all test failures/skips. Product defects remain open;
this delivery implements no product or physical correction.

The plan has 19 unactivated stages. It prioritizes common native contracts,
input/display integrity, provenance/build coverage and execution/assurance,
with separate 2T/4T measured-data preparation in parallel. Independent evidence
scoping and the 4T trajectory reference do not wait for unrelated UI work.
Per-engine numerical, identification, blind-validation and predictive gates
retain their own evidence and criteria. No campaign, build, budget extension,
E1.3 restart or model promotion is activated.

Independent science review initially requested two changes: independent
reference preparation and an explicit numerical-error condition on
calibration. Both are incorporated. The integration review's publication check
was resolved by the new authoritative roadmap pointer, verbatim old-control
archive and explicit planning-only successor. Initial and final reviews remain
in [reviews](reviews); [reconciliation](review-reconciliation.json) records the
changes. Their final PASS applies to planning coherence, not product or science
acceptance.

Reproduce structural/authority checks with:

```text
python scripts/audits/check_dino_platform_plan_v1.py --out NEW_RESULT.json
openspec validate platform-integration-audit-v1 --strict --no-interactive
openspec validate platform-scientific-reliability-v1 --strict --no-interactive
```

The frozen audit byte manifest is verified by the checker. P9, official main,
the A/B branch and product source are checked separately. The original dirty
checkout remains preserved; this branch does not merge A/B into main or publish
an executable.

Operational delivery gate: `DINO_PLATFORM_INTEGRATION_AUDIT_REPLAN_V1`.
Successor: `DINO_PLATFORM_SCIENTIFIC_RELIABILITY_V1`, PLANNED with no execution
activation. This prevents delivery of a plan from being interpreted as a grant
to run every listed stage or reuse historical budgets.
