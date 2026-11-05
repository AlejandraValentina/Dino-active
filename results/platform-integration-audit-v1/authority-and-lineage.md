# Authority, revision and blocker assessment

Audit source is frozen at `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`; official
`main` remains `5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`. The latter is the
ancestor, with seven A/B commits ahead. The audit branch adds audit documents,
operational records and read-only verification infrastructure only. It does
not integrate A/B into main or move another branch.

## Revision-specific capabilities

| Revision | Evidence that belongs to it | Limit |
|---|---|---|
| `dino4t-stage2-v1` / `8d853fb` | Native 4T API, isolated/reference numerical tests and example records | Its original review is SELF_REVIEW; no experimental calibration/validation |
| `552c60e` | First integrated Windows candidate's source | Historical package acceptance does not test later changes |
| `e29f314` | Integration acceptance receipt | Evidence closure, not the packaged source revision |
| `main=5e4ba4d` | Preserved foundation/history, routed 2T/4T Desktop, consolidation verification | Does not contain strict 4T A/B/cancellation additions |
| `cb8f356` | Actual preregistered A/B API calculations | Synthetic-input model sensitivity at one point |
| `07849322` | Sole A/B Windows candidate source | Package input completeness needs correction; no observed bad example content |
| `8b371e2` | A/B evidence/acceptance closure and external UI verifiers | Does not mean those additions are already on main |

`main..8b371e2` product changes are confined to six files: native 4T
API/runner/engine cancellation, 4T Desktop/comparison, and technical reports.
The protected 2T runtime and frozen P4–P9 contracts are not changed by that delta.
The registry in `engine_platform` exposes native 4T. 2T uses its existing
engineering workflow. Common project routing and indicator names therefore
do not imply a symmetric shared execution contract or common physics.

## Planning authority

1. The latest owner request activates **audit followed by replanning only**.
2. `program-status.json` is the repository's operational authority, scoped to
   its revision. Main and A/B carry different current-objective/gate snapshots.
3. The committed unified 2T roadmap explicitly replaces the execution ordering
   of earlier staged/core and product plans. It requires recorded stage
   activation and does not authorize every listed budget automatically.
4. The owner-referenced `docs/planning/predictive-core-staged-plan-v1.md` is
   absent from main and A/B Git trees. It is an untracked file in the preserved
   original checkout. Its exact input snapshot has SHA-256
   `75eee5929e9d9b026e86cdd37a383d68c5fcc50c05a317503df2a6b4b2c2ef20`.
   Its scientific obligations and amendments are relevant antecedents; it
   cannot overrule later owner decisions, committed ordering or the queue.
5. Frozen scientific specs, prior preregistrations and gate results remain
   authoritative for the claims they originally decided. A prospective plan
   may change scheduling, never retrospectively redefine their success.

The staged plan includes an obsolete 0.5 s/cycle target, then the explicit
owner amendment to 2–4×. Later recorded 176-cell Brent scaling is 1.317× for
the only clean paired cycle, not the accepted 2× target. This audit does not
reopen E1.3, transfer budgets or authorize any extra numerical work.

## All BLOCKED_LOCAL entries reevaluated

The twelve-entry machine-readable assessment is
`inputs/blocker-reassessment.json`. No blocker has been made obsolete by the
Desktop or 4T integration:

- Full-RPM, old SPV1 continuation and reed-sensitivity work retain owner scope
  restrictions. No old campaign is reactivated to fill the queue.
- X30 requests/input/configuration/run/result stages lack the recorded
  necessary measured crankcase volume and matching test data. Front-end
  capability does not supply those measurements.
- Cahoon validation still lacks an internally consistent full geometry/test
  package. Reference selection and extraction are closed; the targeted QUB
  request remains recorded as prepared/unsent. This audit sends no messages.
- The periodic multi-mesh/GCI stage retains the measured performance/budget
  block. Existing periodic 44-cell examples do not close it.
- Gradient-extrema/angular-region continuations remain explicitly deferred by
  the owner. No new diagnostic is created to revive them.

Synthetic assumptions may support software or isolated numerical verification.
They cannot unblock measured validation by being relabeled as measured inputs.

## Preserved checkout and evidence bytes

`checks/git-baseline.json` records the original checkout HEAD/branch, change
counts, status and tracked-diff digests. It is left in place. No stash, reset,
rebase, deletion, push or build is part of this audit.

The original A/B Windows worktree verifies all 16 raw evidence hashes. Thirteen
text Git blobs differ from their raw CRLF receipts; the three PNGs do not.
Also, a fresh clean Windows checkout has a different byte manifest for the
new `four_stroke_comparison.py` due solely to LF/CRLF. Its Git source blob and
LF-normalized contents equal the recorded build input. This is an EOL/preimage
reproduction requirement, not evidence of changed physical code or a bad ZIP.
Only the **new audit evidence tree** receives byte-preserving Git attributes;
historical receipts, source attributes and hashes are not rewritten.
