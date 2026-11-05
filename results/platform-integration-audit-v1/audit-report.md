# Dino 2T/4T — technical and scientific integration audit

Date: 2026-11-05. Protocol: [protocol.md](protocol.md).
Frozen sources: official `main=5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`;
A/B branch `8b371e247498f94255e88ab8d35dbae7b7c2ba6b`.

## Verdict and scope

**Unified software exists and its selected internal workflows have been
exercised. General scientific integrity and predictive reliability are not
demonstrated.** Nineteen findings are recorded: ten P1 and nine P2; no P0
loss/corruption was demonstrated within the inspected scope. Product status is
`CONDITIONAL_INTERNAL_TRIAL_OPEN_P1`, with unqualified scientific/release
acceptance blocked by the P1 findings. No new executable is produced or
accepted by this audit.

The original narrow integration and A/B PASS records remain intact. A passing
workflow using coherent inputs does not falsify the negative cases now
reproduced. Conversely, those negative cases do not establish that the original
coherent A/B numbers are wrong. This report does not retrospectively change
their preregistered success conditions.

The orchestrator participated in the earlier implementation, so synthesis and
its artifact checks are **SELF_REVIEW**. Three separate read-only agents provide
attributed **INDEPENDENT_REVIEW** in `reviews/`: scientific/API, integration and
provenance, and protected contracts/regressions. Their reports are retained
verbatim. Independence is limited to those scopes; this is not a claim that a
separate institution reproduced every scientific reference case.

## What the evidence demonstrates

| Dimension | 2T | Native 4T | Shared platform |
|---|---|---|---|
| Implemented software | Existing projects/variants/execution/results/studies/reporting | Main: native project/config/run/history/results; A/B branch: strict comparisons/exports and safe-cycle cancellation | Single executable and family-aware routing; common presentation/project entry points |
| Verified software | Focused historical and current regression evidence; clean-checkout artifact caveat below | Fresh focused API/A/B/Desktop suite: 38 PASS; historical Windows records remain revision-bound | Package bytes verified, selected negative UI/API cases independently reproduced; no fresh GUI campaign |
| Numerical consistency/convergence | Frozen P4–P8 scope; exploratory periodic 44-cell cases; periodic multi-mesh uncertainty remains open | 31 Stage-2 reported checks include isolated references and one baseline mesh study; actual A/B pair satisfies recorded detector | No cross-family numerical PASS exists |
| Physical consistency | Idealized port/boundary/closure assumptions within declared scope; measured losses/identifiability unresolved | Independent component references, correct cycle conversion and ledger identities; prescribed combustion and uncertain losses/Cd | Native semantics retained; shared names do not make definitions equivalent |
| Calibration | No complete adopted matched measured-engine package | NOT_PERFORMED | Cannot be shared or inferred from software acceptance |
| Predictive validation | NOT_PERFORMED / NOT_CLAIMED | NOT_PERFORMED / NOT_CLAIMED | NOT_CLAIMED |

The two real A/B calculations were made at clean source `cb8f356`; the package
was built from `07849322`; evidence closure is `8b371e2`. Main contains none of
the seven later A/B commits. See [authority-and-lineage.md](authority-and-lineage.md).
The audit branch does not merge them into main.

### Actual A/B endpoint checks

Both recorded endpoints have six complete cycles and two final transitions
passing the four preregistered periodicity tolerances. Summary bytes, canonical
resolved-config identities and raw trace hashes match. Last traces cover 720°
with increasing crank angle (2005/1996 rows). The sole configuration delta is
intake maximum lift 10 → 8 mm at exactly 6000 RPM and equivalence ratio 1.0.

The independent reviewer recomputed work/displacement → IMEP and
`BMEP × displacement × RPM/120` → 4T power, with differences at floating-point
roundoff. Torque also matches. The 2T `RPM/60` convention must remain separate.
Maximum recorded mass/energy/element closures are about 1e-15–4e-14. Those
ledgers are bookkeeping evidence using the same stage fluxes as the state;
they do not independently establish boundary-model fidelity.

These endpoints demonstrate `PERIODIC_MODEL_SENSITIVITY_ONLY`. The geometry,
Cd and other inputs remain labeled synthetic assumptions; prescribed Wiebe
combustion and synthetic friction condition the reported power difference.
The Stage-2 baseline GCI cannot be transferred to the uncertainty of an
arbitrary new design difference. No independent measured-engine claim follows.

## Findings and implications

Every row has detailed anchors, reproductions and future acceptance in
[findings.json](findings.json) and the independent reports. No product fix was
made during evaluation.

| ID | Severity | Confirmed issue | Revision/impact |
|---|---|---|---|
| F01 | P1 | Accepted zero consecutive count produces one-cycle periodic success with no cycle comparison | Main and A/B; classification integrity |
| F02 | P1 | Hash-consistent imported summaries can contradict config RPM/models/cycle history and still compare | Main validator; new A/B exposure |
| F03 | P1 | WALL_LIMIT state omits crank phase and can be reused at the wrong volume | Main and A/B; unsafe API continuation |
| F04 | P1 | Invalid/fractional/bool/nonfinite parameters, section errors and silent unknown-key/default gaps | Main and A/B; input/error contract |
| F05 | P1 | Untouched editor Apply rounds and changes engineering inputs | Main and A/B; configuration identity |
| F06 | P1 | Verified history can plot a replacement pressure trace with no original trace binding | Main and A/B; provenance |
| F07 | P1 | Failed refreshed history retains previous scientific metrics and curves | Main and A/B; stale result association |
| F08 | P1 | Consumed native 4T example omitted from manifest and dirty-input guard | Main and A/B; build assurance |
| F09 | P1 | Source clean flag excludes modified shared numerical dependencies | Main and A/B; source assurance |
| F10 | P1 | Protected clean-source regression closure requires implicit external and relative artifact contexts | Historical/main/A/B; reproducibility |
| F11 | P2 | CLI sensitivity accepts completed nonperiodic perturbations as successful derivatives | Historical/native 4T; not strict Desktop A/B |
| F12 | P2 | Absolute study paths and implicit EOL policy limit portable artifact replay | Native metadata and A/B evidence |
| F13 | P2 | Package labels native 4T with a legacy model identifier | Metadata inconsistency, not wrong solver demonstrated |
| F14 | P2 | Crank-angle pressure data inherit the RPM axis label | Scientific presentation |
| F15 | P2 | Threaded 4T execution and reopen evidence do not prove process-worker cleanup or checkpoint resume | Architecture/evidence scope |
| F16 | P2 | Acceptance can write PASS before final shutdown checks | A/B external assurance scripts |
| F17 | P2 | Historical 115-failure list is not a current-suite waiver | Regression attribution |
| F18 | P2 | Some old 4T studies lack exact committed source preimages | Already disclosed historical limit |
| F19 | P2 | Architecture/capability documentation is stale; discovery and async failure identity need reconciliation | Static risk qualified separately from reproduced bugs |

The F01 diagnostic used a single bounded cycle (11.875 solver seconds) to falsify
a classification hypothesis. It is not a repeat A/B or periodic campaign.
Config-only probes found e.g. valve count 1.9 accepted then truncated, NaN loss
and Cd data accepted, and `geometry=None` escaping as `AttributeError`.
Synthetic contract stubs and temporary copies used for negative tests are
explicitly not genuine engine results; originals were untouched.

## Architecture and scientific boundaries

Native 4T runtime owns its engine, 720° cycle, NASA thermodynamics, equilibrium,
valves, conduct solver and boundary model. Shared cycle-agnostic kinematics and
mesh utility imports do not unify the solvers; the frozen 2T HLLC is a 4T test
oracle, not its operating numerical solver. No changed protected 2T physical
runtime was found in the integration delta.

The common adapter remains asymmetric: `engine_platform.families()` exposes
4T; 2T execution remains its versioned engineering workflow. This is an explicit
compatibility seam, not evidence that the native solvers should be merged.
Semantics such as gross-versus-net mechanical efficiency, trapped mass and
delivery/scavenging efficiency require family-qualified definitions.

Important outstanding scientific obligations are not software defects:

- The integrated two-zone trajectory has no independently resolved trajectory
  oracle. Cantera algebraic states, self-convergence and conservation are
  complementary but do not replace it.
- Numerical error belongs to a specified model, operating condition and
  discretization. 2T periodic multi-mesh remains blocked; neither architecture
  has demonstrated uncertainty for every design effect.
- The native 4T unsupported supersonic-inflow face is rejected explicitly.
  Extending that model domain requires a new justified reference; weakening a
  tolerance is not a remedy.
- L1 summary/last-cycle traces are not a full L2 offline stage-flux replay.
  Current labels should remain L1. The trace CSV itself writes ten significant
  digits; full metric-export precision is a different claim.
- Both families need complete matched measured datasets, distinct calibration
  and blind-validation subsets, measurement uncertainty and model-form
  uncertainty. No input may be invented to fill a measured package.

## Verification record

| Check | Result and qualification |
|---|---|
| Focused API/A/B/Desktop | 38 PASS, 130.49 s; raw log/summary retained |
| Protected P4–P8 clean worktree | 296 PASS, 5 FAIL, 3 SKIP; all five failed nodes are in the historical 115 inventory |
| Only failed protected tests with exact existing contexts | All five PASS after verified external-root/relative-artifact context; 301 distinct passes across contexts, not one green clean run |
| External evidence access | 56 registered G2 files verified by size/hash; 20 original checkpoint hashes retained |
| Frozen P9 | Main and A/B canonical Git blobs match `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d` |
| A/B artifact identities | All summary/config/trace identities match their declared hash semantics |
| A/B Windows evidence | 16/16 raw Windows files match; 13 text Git blobs differ by EOL policy |
| Actual ZIP/EXE | ZIP `aa0992b08514c996ca8191e863387260fee964dfcd2aff19d6582a4bdc997e03`; EXE `89852dd681b0620380114ab8232649f9008a5d11cd1cb34e69d63458bc9e04d2`; ZIP CRC succeeds |
| Omitted package example | Inside ZIP, JSON is semantically identical to source `07849322`; no contaminated example observed |

The known 115 inventory has 83 FAILED and 32 ERROR entries from the historical
comparison to `e95db4c`. This audit traced exact relevant node IDs and causes.
It did not rerun the full general suite, the historical Qt access violation,
all 31 scientific reference cases, the full Stage-2 mesh campaign, Windows GUI
acceptance, or any 2T historical campaign. These omissions are scope limits,
not silent passes. Tests cannot be made green by changing frozen contracts.

### Cancellation/recovery qualification

The packaged record genuinely stopped after two complete cycles and remains
`incomplete`, `cancelled_by_user`, `NOT_CONVERGED`. Reopening the saved periodic
A/B project in a fresh EXE process worked historically. That test used a new
artifact root and did not resume numerical state or recover the cancelled
history. Native 4T uses a GUI-process `QRunnable`; absence of an executable
named `MotorSimWorker` is not evidence about that task's lifetime. No claim of
serializable native 4T checkpoints is justified. 2T checkpoint acceptance is
separate and unchanged.

## Reproduction and audit integrity

Run `python scripts/audits/audit_dino_platform_v1.py --out <new-output.json>`
against this checkout for read-only Git/artifact/ZIP checks. Independent probe
scripts in `reviews/` accept the frozen repo path; scientific runtime probes
require an explicit runtime option and are not needed to consume the retained
observations. Exact protected test commands, artifact contexts and logs are in
`reviews/independent-contract-review.md` and `checks/contract/`.

Only audit infrastructure, operational state and documents change here. New
audit byte-preservation attributes prevent its own receipts from depending on
checkout EOL policy. Historical bytes/hashes, branches, worktrees and the dirty
original checkout are preserved. No push, publication, package rebuild or
physics/configuration change occurred.

**Audit freeze:** this report, attributed reviews, findings and primary check
records are committed before successor planning is written. The later plan
must cite this frozen audit; its delivery gate cannot be mistaken for a
scientific model, predictive or release gate.
