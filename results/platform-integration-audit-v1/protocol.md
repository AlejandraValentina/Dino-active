# Unified Dino 2T/4T audit protocol v1 — 2026-11-05

## Scope fixed before synthesis

Owner requests audit first, scientific replanning second. Frozen product revisions: `main=5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`, A/B branch `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`, packaged A/B source `07849322b8ad0115defb28de2ad5f23b8bfacd55`. The audit branch descends from A/B only to retain its operational/evidence history; it does not merge A/B into main. Original dirty checkout, other branches and worktrees are read-only. No solver, UI, configurations, historical evidence, frozen expectations, promotion or executable changes.

## Evidence and criteria

Audit each claim against its own revision, contract, source and artifact. Distinguish implemented software, tested software, numerical verification/convergence, physical consistency, calibration and predictive validation. Tests and conservation do not establish model fidelity. A/B deltas need exact compatible operating conditions, both endpoint identities and explicit uncertainty limits; periodicity does not establish mesh convergence or measured validity.

Classify findings: P0 = confirmed loss/corruption or unsafe scientific misrepresentation with immediate broad consequence; P1 = reproducible incorrect contract, comparison, provenance or numerical acceptance behavior materially affecting engineering decisions; P2 = scoped recoverability, coverage, architecture or documentation risk; P3 = minor usability/debt. Record confirmed / unverified / design limitation, affected revisions, source anchors, reproduction, impact, and evidence required for closure. Do not infer defect absence from a test count, or attribute the historical 115 failures to a new revision without matching identities and conditions.

Use static history/diffs, hash verification and bounded adversarial probes before running tests. No new engine campaigns, benchmark campaigns, GCI or Windows rebuild. Reuse genuine paired results and the candidate; verify stored evidence integrity rather than repeating its accepted GUI workflow. Scientific numerical claims remain bounded to their original protocol. Relevant tests: API/Desktop/project contracts and P4–P8; per diagnostic <=600 seconds, external logged output, no tolerance or expected-value changes. If a test needs missing external evidence, report it; do not fabricate that evidence.

Independent agents review scientific and integration scopes read-only; reports are attributed and persisted verbatim. The orchestrator implemented earlier A/B work, so its own work is SELF_REVIEW. Independent review is a process property, not an assertion that every finding is correct; reconcile contradictory evidence explicitly.

## Audit-before-plan boundary

Commit the completed audit report, findings, independent reports and checksums before writing the successor scientific plan. Future plan priorities must cite audit findings and preserve 2T obligations, component-specific 4T obligations, model/version separation, uncertainty and held-out measured validation. Old criteria/evidence remain frozen. Any supersession is prospective and explicit; no prior PASS/FAIL is erased. Scope activation and numerical budget authorization are distinct from documenting a future task.

The operational objective is delivery of this audit and replan. Its PASS means those documents and verifications are complete even if the product verdict has open P1 findings. It cannot be cited as a solver/core/release/predictive PASS. Future remediation/campaigns are outside this request and require their own recorded activation. Blocker reassessment is in `inputs/blocker-reassessment.json`; missing measurements and owner-deferred numerical campaigns are not unlocked by 4T or Desktop functionality.
