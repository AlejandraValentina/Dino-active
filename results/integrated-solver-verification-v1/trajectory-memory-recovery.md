# Trajectory memory recovery

Result: **MEMORY_GROWTH_REDUCED**. Integration history retention is substantially
reduced on small fixtures; full-pipeline memory is not bounded and T1-B/C are
**NOT_VERIFIED**. No A3b configuration or RPM campaign was executed.

## Cause and implemented change

Each accepted step retained three full SSPRK states (`q0`, `q1`, `qn`), two
sets of face/species fluxes, geometry, external/network exchanges, work and
thermal rates, combustion source/event data, inventories, CFL and exact timing
in `IntegratedEngine2T.trace`. The next integration step needs current state,
active events and cumulative ledgers, not the entire accepted-stage history.
Rejections are logged by the caller and are not removed by this change.

`motorsim/_trajectory_store.py` implements one private process-local temporary
spool. Each complete record is serialized losslessly with marshal (built-in
types, including tuples), zlib level 1, and a length/SHA-256 frame. An in-memory
array holds eight bytes per record offset. There is no retained Python state
graph, complete second RAM buffer, lossy compression or sampling change. One
record is serialized at a time. Writes are buffered, not fsynced each step;
snapshot export flushes/fsyncs before it can reference the records. Serialization,
sequential reconstruction and indexing are linear in the number of records.

`IntegratedEngine2T.enable_trajectory_spooling()` selects this backend without
changing scientific configuration. Snapshot exports the same complete JSON
tree. Restore validates the full old public checkpoint, writes/syncs a new
private spool before committing live state, and only then closes the old file.
Cycle compaction replaces/closes the completed spool. The normal exploratory
production workflow enables the backend; frozen campaign/A3b drivers do not.
Callers using the engine directly may select it explicitly.

This is temporary internal storage, not a new evidence or restart format.
No persistent spool can be imported or selected implicitly. Independent audit
still replays every SSPRK stage using the existing solver and verifies the
same complete primary. The auditor itself continues to retain replay history
in a list; snapshot, primary deepcopy and rebuilt audit representations still
grow with history. Removing those costs safely is outside this delivered
correction. No claim of constant memory for the complete pipeline is made.

## What occupied the historical 3 GiB?

The old T1-B log sampled 39.67 MiB initially and 672.80 MiB at 359.617 degrees;
the later supervisor peak was 3073.07 MiB. Most of that later peak cannot be
attributed to the state required for the next numerical step. A zero-step
construction of the saved 48-cell configuration measured **22128 Python bytes**
for current state plus ledger (unique objects counted once). This excludes
configuration, interpreter, transient RHS work and event objects; it is not a
worker RSS estimate. Three GiB is not a requirement of those 48 current cells.

The historical log lacks phase-specific allocation measurements at termination,
so its exact 3 GiB partition cannot be reconstructed. Inspection and new phase
measurements demonstrate retained trajectories plus simultaneous snapshots,
primary/replay/reconstruction trees as the dominant mechanism. No unbounded
leak or exact allocation at the kill point is claimed. NumPy buffers were not
identified as the cause of these Python trajectory trees.

## Measurements

External artifacts: current user's `Dino-artifacts/trajectory-memory-recovery`.
Two fresh processes use the same current small synthetic engine, identical fuel,
mesh and stepping. Only list versus spool backend changes. The benchmark
inherits the previous canonical-hash/comparison optimizations in both modes;
it is not a comparison against a historical A3b binary. Both cycles retain
full history to expose growth. The workload is 1242 + 1442 accepted steps.

| Two-cycle fixture | List | Spool |
|---|---:|---:|
| Sampled RSS peak, MiB | 513.51 | 481.40 |
| Cycle 1 integration RSS peak, MiB | 86.54 | 34.74 |
| Cycle 2 integration RSS peak, MiB | 198.32 | 109.57 |
| Cycle 1 audit RSS peak, MiB | 321.36 | 293.97 |
| Cycle 2 audit RSS peak, MiB | 513.51 | 481.40 |
| Total fixture wall, s | 47.51 | 48.48 |
| Worker CPU, s | 47.50 | 48.38 |
| Cycle 1 integration time, s | 3.64 | 3.80 |
| Cycle 2 integration time, s | 4.16 | 4.50 |
| Cycle 1 audit time, s | 10.88 | 11.09 |
| Cycle 2 audit time, s | 13.35 | 13.06 |
| Cycle 1 RSS growth per step, bytes | 44670 | 749 |
| Cycle 2 RSS growth per step, bytes | 45385 | 864 |

Overall sampled peak improves only 6.25% because materialized snapshots/audits
remain. Wall time increases 2.05% in this paired observation; integration grows
about 4.6%/8.2%. These are small-run observations, not campaign speedup claims.
Other tests ran on the host during portions of measurement. RSS sampling is
10 ms and may miss short peaks. Parent/launcher memory is excluded; worker
final private USS is in the raw JSON, not confused with peak RSS.

Spool size was 6529842 bytes after cycle 1 and 15434044 after cycle 2;
index size was 9936/21472 bytes. Public JSON primary representation is unchanged.
The benchmark includes compressed spool writes in integration and spool reads
and fsync in snapshot time. It does not gzip-persist full campaign primaries or
checkpoints; this is not a complete campaign I/O benchmark. The waveform,
periodicity detector and engineering output contracts are not changed.

A separate partial-horizon growth fixture measured 20/60/120 accepted steps:

| Metric | List | Spool |
|---|---:|---:|
| Retained traced bytes at 20 steps | 1155365 | 591746 |
| Retained traced bytes at 60 steps | 2565049 | 684534 |
| Retained traced bytes at 120 steps | 4301189 | 703202 |
| Retained growth between 20 and 120, bytes/step | 31458.24 | 1114.56 |
| RSS at 120 steps, MiB | 46.96 | 35.29 |
| Runtime with tracemalloc, s | 2.92 | 2.87 |

This is a 96.46% reduction in measured retained growth, not evidence of constant
memory. The index remains O(steps); events, caller rejection logs and other
small runtime structures were not shown bounded indefinitely. Python released
objects need not make RSS fall. No `gc.collect()` workaround was used.

## Integrity, equivalence and recovery

Two-cycle canonical primary digests match exactly between backends:

* `a86a74d190da9f6a74872018d9ba4278d24caa0ec98bf85a8b268f37a1a188a6`
* `32c44a8d5e3573108d9228740982bb78e9936e57b4c4153442d3fe336b504fa9`

The growth fixture snapshot digest matches exactly too. All four cycle audits
returned PASS/recomputed true, with exactly equal physical/conservation values.
Additional tests compare a full primary after mid-cycle checkpoint restore,
including independent replay. Existing exploratory tests cover detector and
periodicity state, interrupted manifests, orphan-primary rejection and resume.

Eight new storage/recovery tests initially passed, plus one later reference
retention test: nine unique spool tests. With eight previous memory tests and
22 exploratory workflow tests, **39 unique focal tests pass**. The combined
38-test run took 230.95 s; the final eight lightweight storage tests (one full
cycle test deselected because it had already passed) took 2.92 s. Initial test
development had one failure due to a mismatched test fixture schema; it was
corrected to use the same plenum schema, then verify configuration rejection.
No production validation was weakened. OpenSpec strict and program-status pass.

Recovery tests run real Windows spawn workers. They preserve a self-contained
checkpoint, kill the worker during further integration or an incomplete spool
write, verify temporary-file cleanup, restore only the valid checkpoint and
match the uninterrupted snapshot canonically without duplicate accepted steps.
Short writes, truncation, wrong SHA, fsync failure and restore disk failure are
explicit failures. A failed store cannot be exported or advanced. Its partial
tail is never interpreted as audited evidence; an earlier public checkpoint is
the sole recovery source. TemporaryFile's OS close/deletion handles abrupt
worker death on the tested Windows environment. No durable partial spool
recovery is claimed or needed for the unchanged checkpoint contract.

## 48-cell estimates and A3b budget

Measured historical T1-A accepted counts are 5254, 5764 and 5764. Under the
explicit, unverified inverse-CFL assumption, a 48-cell cycle might have:

| CFL | Assumed steps/cycle | Resident spool index only |
|---|---:|---:|
| 0.4 | 5254–5764 (historically measured counts) | 41–45 KiB |
| 0.2 | 10508–11528 (estimated) | 82–90 KiB |
| 0.1 | 21016–23056 (estimated) | 164–180 KiB |

These are index estimates, **not predicted worker RSS peaks**. One-record
marshal/compression/decompression buffers and current RHS state remain in RAM.
Transient buffers scale with cells per record; disk storage scales with total
steps. The historical 48-cell integration near CFL 0.2 reached 672.80 MiB;
an inverse-step-volume model would put list integration around 356/673/1306 MiB
at CFL 0.4/0.2/0.1, respectively. Only the middle number is an observed progress
sample; these are not closure/audit peaks. No valid whole-pipeline RSS estimate
for B or C follows from this model because snapshots and replay remain.

Historical accounting is unchanged: **783.376/4320 s consumed; 3536.624 s left**.
No diagnostic was booked as a new scientific invocation and no ledger reset.
Diagnostic run_logged caps were 180 s per two-cycle fixture and 45 s per growth
fixture, with fixed small horizons; regression tests are separate. No T1-A was
repeated. Seventeen source files and four V4 evidence files retain exact hashes.

The old V4 pending projection was 3560.282 s (B 1037.324, C 2014.648,
D 305.050, E 203.261). Carrying it unchanged now projects 4343.658 s accumulated,
23.658 s beyond the global cap. Applying the small fixture's 1.020465 wall ratio
as a **hypothetical stress scenario only** gives 3633.143 s pending and
4416.519 s accumulated; it is not a measured or validated B–E forecast.
The individual caps sum to 3670 s, also above the remaining global balance.
Actual cost might differ, so mathematical impossibility is not established;
there is currently **no defensible plan shown to fit** the original budget.
Neither the 3072 MiB worker cap nor 4096 MiB aggregate cap is increased.

## Identity and remaining work

Changed bound files: `integrated_2t.py` and `exploratory_workflow.py`. The new
private spool module is included in solver dependency hashes. Exact new hashes
are in the receipt. Frozen V4 zero-step preflight correctly fails closed on
the changed workflow dependency. V2/V3/V4, T1-A, ledgers, atol, primaries and
historical audit receipts are preserved; no hashes were updated to pass.

Backend equivalence is demonstrated on small fixtures. It does not authorize
combining historical and current scientific identities. A later authorized
driver change would minimally select spooling and bind the reviewed new
dependencies with explicit historical-reference provenance; none was made here.

Remaining technical limitation: public snapshot/primary materialization and
auditor replay/reconstruction can still dominate the peak. A safe future
solution would need sequential export/consumption while preserving the exact
public canonical records; it was not implemented speculatively here. Before
authorizing a costly B/C cycle, measure a **partial, at most 60 s** synthetic
48-cell integration under the same 3072/4096 MiB guards and collect phase RSS,
step count, spool bytes and throughput. A full audited B/C cycle needs separate
authorization and a validated budget/identity plan; no peak or fit is promised.
