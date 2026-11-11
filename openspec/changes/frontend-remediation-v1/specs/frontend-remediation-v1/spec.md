# Dino frontend remediation and coherent workflow v1

Owner authorization: 2026-11-11. Starting revision: audit `696b8fc`, product
`d44305c`. Work in an isolated E: worktree; no push or merge to main, no solver,
equation, tolerance, scientific-contract or historical-evidence changes.

## Integrity invariants

1. Draft, applied, saved and submitted configuration are distinguishable. A
   pending draft cannot be silently discarded, saved as another configuration or
   bypassed by a point/curve command. A result refresh cannot erase a draft.
2. Every execution owns an immutable configuration snapshot and identity. Native
   4T editing/variant changes are disabled while its point or curve is active.
3. Save normalizes paths, catches failures, preserves dirty state on failure and
   clears it only after atomic persistence. Opening/importing never overwrites
   an original project; an import gets a new destination.
4. Portable bundles preserve original artifact bytes and hashes and transport
   the transitive dependency closure. Integrity, execution completeness,
   periodicity and legacy provenance remain independent. Missing/invalid data
   are reported explicitly; copying never upgrades scientific evidence.

## Incremental application evolution

Provide persistent project/model/variant/configuration identity, understandable
physical-component editing, common model/simulation/results navigation and direct
access to a terminal run. Reuse public engine APIs, existing plots/editors and
scientific eligibility checks. Distinguish 2T, native 4T and reference 4T 0D.
Explain RPM grids, aggregate budgets, cancellation/resume limits, comparison
eligibility and bundle contents. Make help readable and active-context aware.
Document subsequent advanced capabilities separately; do not invent scientific
functionality to make UI layouts symmetric.

## Acceptance scenarios

- Edit native bore 86→87 without Apply, then execute/save/switch variant/undo:
  apply, discard or cancel explicitly; invalid drafts cannot proceed.
- A background reference/result update preserves a pending draft unchanged.
- Export/import verified native complete/incomplete and legacy results into a
  new root inaccessible to the original; source bytes/claims stay unchanged.
- Save imported native projects with str/Path destinations; negative I/O leaves
  original and draft intact and displays an actionable error.
- Create/edit/apply/save/reopen; execute and cancel; open real results; export
  and import; compare eligible endpoints; recover from invalid/missing inputs.
- Observe source GUI in Windows at compact and large sizes, plus targeted and
  protected regression with explicit retained contexts. No numerical validation
  claim follows from UI tests.

## Evidence and lifecycle

Track IMPLEMENTED, SOURCE_ACCEPTED, WINDOWS_ACCEPTED and PENDING_UAT separately.
SOURCE_ACCEPTED requires behavioral tests and real source GUI workflow evidence.
WINDOWS_ACCEPTED requires the matching packaged candidate and is not inferred
from source execution. A Windows rebuild is deferred unless justified.
Human representative UAT and unimplemented advanced items remain visible.

The source acceptance gate closes the bounded F0 integrity + F1 coherent workflow
increment, not every scientific obligation or every future UX feature. Changes
use small semantic commits and the operational queue in the same commit.
