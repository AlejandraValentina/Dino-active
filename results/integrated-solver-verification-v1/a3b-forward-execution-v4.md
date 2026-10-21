# A3b V4 — final forward execution package

Classification: **IMPLEMENTATION READY — EXECUTION NOT AUTHORIZED**.

## Implemented correction

V4 delegates each scientific cycle to the immutable corrected V2 executor
(SHA-256 `3062ed465f1a8d0e715ef9be07a4ddee4a0a1f11dba7cf4cf7824594e7b8bb42`). The physics, primary construction, independent
auditor, engineering adapter, effective-dt/CFL instrumentation and cycle
checkpoint logic are reused. No V2/V3 file or scientific equation was changed.
Only B/C/D/E may run. V3 T1-A remains the three-cycle reference (`next_cycle=4`).
The exact V3 atol freeze is an input, never regenerated: two evaluable
observables and nine NOT_EVALUATED observables.

The previous 595 s deadline covered stepping, not the subsequent audit and
persistence. V4 supervises the entire child lifetime. It polls at 100 ms,
enforces both 3072 MiB per worker and 4096 MiB aggregate RSS, terminates the
process tree on timeout/cancellation, and keeps ten seconds for closure. A
worker watchdog exits after supervisor death. Parent and worker write the ledger
in separate phases under a single invocation supervisor lock.

B is split into single-cycle invocations. The C invocation limit is proposed
as 750 s, with a 730 s stepping deadline and 740 s supervisor cutoff. Other
invocations retain 600 s, with 580/590 s stepping/supervisor deadlines. These
operational changes require the separate owner authorization below. Production
configuration preflight still uses its supported 600 s preview; it does not
represent the C supervisor limit.

## Budget

The V3 ledger remains **530.469 s**. V4 carries all three original entries
unchanged, including the failed 112.094 s attempt, and separately adds **2.673 s**
of measured historical launcher overhead (1.188 s V2 + 1.485 s V3). The initial
conservative total is **533.142 s**, leaving **3786.858 s** under 4320 s.
The remaining configuration caps sum to 3670 s, leaving 116.858 s beyond those
caps. Supervisor and closure costs count against the applicable configuration
cap and the global cap.

| Config | Cumulative cap s | Cycles per invocation | Invocation cap s | Planned full cost s |
|---|---:|---|---:|---:|
| T1-B | 1050 | [1, 1, 1] | 600 | 1037.324 |
| T1-C | 2100 | [1, 1, 1] | 750 | 2014.648 |
| T1-D | 310 | [3] | 600 | 305.050 |
| T1-E | 210 | [3] | 600 | 203.261 |

Planning uses the measured T1-A cycle-3 cost ratio, the prior linear scaling,
+10% runtime allowance and 20 s per invocation including the charged 10 s
closure reserve. Audit, serialization and complete-cycle checkpoints are in the
measured cycle cost. Total forecast: **4093.424 s**;
margin: **226.576 s**. This is an estimate, not a
new measurement of B–E. A +20% stress can exceed individual caps. The preflight
and each subsequent invocation reject a remaining horizon that no longer fits;
no cap, tolerance, cycle count or CFL is extended automatically.

Run one worker, sequentially. A successful invocation is resumed at the exact
next scheduled cycle, never from zero when a valid checkpoint exists. Completed
results are verified and reused. A timeout or failed invocation is terminal for
this authorization. `recover` never advances the engine: it verifies process
absence, conservatively charges a dead supervisor's full reservation, preserves
all artifacts and leaves execution stopped. If supervisor identity cannot be
established, recovery refuses rather than guessing.

## Frozen identities

- Driver: `3a4c69e820e5d93ad55c32f02c26104fb79590f85ec9babd0305dfd3163b7d79`
- Protocol: `129bc48682026810e35dc999dc8f745b4376706470b2d7daf9c316e5b45f835a`
- Freeze/addendum: `4c18568804cbf2161b068a52f1628e79e0e527ea5c07d1e5a88011cf307b6251`
- Authorization request: `0c6ee428f83c57d9a775d85a7d1412fac1670ad81b84ee1e109855ab0abeb9e1`

The freeze is single-use and immutable. Git attributes preserve the exact
historical delegate and V4 source bytes on Windows.

## Verification and current conditions

52 relevant tests passed (44.27 s). The scientific loop integration fixtures are
synthetic and explicitly labeled; they are not scientific evidence. Windows
subprocess tests verify delayed completion, timeout, worker/aggregate memory,
worker failure and orphan exit after abrupt parent death. A real engine was
constructed and restored without advancing it. Artifact corruption, mismatched
bindings, missing authorization, altered hashes, insufficient budgets and
partial directories fail closed. OpenSpec strict and program-status check pass.

Frozen zero-step preflight: `PASS_STRUCTURAL_ONLY`; all four scientific
configurations and the V3 reference validate. Available RAM at freeze was
2725.7 MiB, below 4096 MiB. Strict launch
preflight refuses in that condition. Structural-only verification cannot bypass
`run-config` authorization or its live memory guard. No scientific output root,
new checkpoint or scientific result was created by this intervention.

## Single execution authorization request

Review `a3b-execution-authorization-request-v4.json`. It is deliberately marked
DRAFT_NOT_AUTHORIZED and execution_authorized=false. Authorization must cite the
final protocol/driver/freeze hashes, approve B's `[1,1,1]` plan and C's 750 s
invocation cap, retain all four configuration caps and the accumulated 4320 s
limit, identify separate source/output roots, and permit only B/C/D/E. Persist
its SHA in program-status before running anything. Do not edit the freeze.

After approval, set DINO_A3B_SOURCE_ROOT to the existing external a3b directory
containing the immutable V2/V3 ledger, and DINO_A3B_V4_ROOT to a separate external
directory. Zero-step command:

```powershell
python scripts/diagnostics/integrated_solver_verification_a3b_v4.py preflight --source-root $env:DINO_A3B_SOURCE_ROOT --artifact-root $env:DINO_A3B_V4_ROOT
```

For each separately authorized invocation use run_logged (620 s outer timeout
for B/D/E, 770 s for C):

```powershell
python scripts/agents/run_logged.py --name a3b-v4-T1-B-inv1 --out $env:DINO_A3B_V4_ROOT --timeout 620 -- python scripts/diagnostics/integrated_solver_verification_a3b_v4.py run-config --source-root $env:DINO_A3B_SOURCE_ROOT --artifact-root $env:DINO_A3B_V4_ROOT --config T1-B --invocation 1 --authorization $env:DINO_A3B_V4_AUTHORIZATION
```

Execute B:1, B:2, B:3, D:1, E:1, C:1, C:2, C:3; inspect each durable outcome and
stop on any terminal condition. Do not execute this sequence without the
independent owner authorization. Analyze only after all four configurations
complete. The analyzer consumes the V3 freeze, produces same-cycle deltas and
classifications, preserves NOT_EVALUATED and explicitly states spatial/temporal
coupling: a fixed-CFL spatial arm does not alone isolate spatial independence.
Three cycles do not demonstrate periodicity, steady state or predictive power.
