# Memory and execution recovery — 2026-10-21

Classification: **MEMORY_OPTIMIZATION_VERIFIED**, limited to the measured small
engineering fixture. **T1-B/C viability remains unverified.** No A3b execution,
new protocol, increased cap or scientific gate promotion.

## Cause and correction

`IntegratedEngine2T.trace` deliberately retains every accepted SSPRK stage,
including chamber/duct/species states, geometry and fluxes. It grows with
accepted steps and cells per stage; this is required evidence, not proof of a
leak. Smaller CFL can increase steps and therefore retained evidence. Snapshot
normalization, primary `deepcopy(trajectory)`, independent replay and rebuilt
primary coexist with this trace. Those representations remain intact.

Two avoidable temporary allocations were removed in `motorsim/integrated_2t.py`:

* `_evidence_sha256`: encode/hash a top-level trajectory one record at a time,
  with the same canonical JSON separators, key sorting and finite-value guard.
  This retains the C encoder and bounds the string/UTF-8 temporary to one row.
* `_json_evidence_equal`: compare lists/tuples and dictionaries recursively,
  without allocating two entire JSON-shaped trees. Used for accepted replay
  rows and the final complete reconstructed primary comparison. Every stage,
  field and species is still checked; this does not replace the independent
  solver replay or compare a reduced observable set.

No physical operation, buffer, flux, CFL, geometry, event timing, species,
primary variable, checkpoint schema, tolerance or audit was removed. No cache
or `gc.collect()` was introduced. Tests verify immediate release of input
references after both helpers return.

The historical T1-B progress log has 73 samples, rising from 39.67 MiB to
672.80 MiB by 359.617 degrees. The supervisor subsequently sampled 3073.07 MiB
and terminated the worker. This localizes a large later peak to cycle closure,
but does not identify the precise allocation phase in that failed process.
The small fixture below directly identifies an audit peak. Neither observation
proves an unbounded leak. NumPy temporary buffers were not established as a
cause; the large retained structures inspected here are Python stage trees.

## Measured comparison

`scripts/diagnostics/integrated_evidence_memory_benchmark.py` runs the existing
small synthetic integrated-engine fixture with fuel combustion and open-end
plenum, two cycles (1242 and 1442 accepted steps). Legacy mode restores only the
old allocation algorithms in its own process. Both modes execute and bind the
same current physical implementation. This is not the historical A3b executable
and not a 48-cell T1-B/C benchmark. Raw records are external in the current
user's `Dino-artifacts/evidence-memory-recovery` directory.

| Measurement | Legacy allocations | Optimized |
|---|---:|---:|
| Sampled peak worker RSS, MiB | 584.70 | 514.03 |
| Wall time, seconds | 50.31 | 47.19 |
| Worker CPU time, seconds | 50.22 | 47.20 |
| Cycle 1 audit, seconds | 12.69 | 11.01 |
| Cycle 2 audit, seconds | 14.27 | 13.26 |
| Cycle 1 accepted steps/s | 345.90 | 360.44 |
| Cycle 2 accepted steps/s | 344.37 | 334.99 |
| Cycle 1 RSS growth, bytes/step | 44601 | 44492 |
| Cycle 2 RSS growth, bytes/step | 45428 | 45491 |
| Final private USS, MiB | 189.43 | 178.70 |

RSS reduction: 12.09%; observed wall ratio: 1.066x. A preceding paired run gave
586.10 to 513.98 MiB. These are two small paired observations, not a statistical
campaign speedup claim. Other regression tests ran on the host during portions
of the measurements; timing is indicative. The 10 ms RSS sampler can miss
shorter peaks. Final USS is measured separately; no reliable Windows shared
memory breakdown or peak private measurement was obtained. Launcher/parent
memory is excluded from this worker measurement, not confused with RSS.
The fixture times integration, snapshots, primary construction, independent
audit and canonical digest measurement; it does not gzip-persist a campaign
primary or checkpoint. Its wall time is therefore not a full campaign pipeline
benchmark. Checkpoint correctness is covered by the existing regression tests.

In the instrumented pair, cycle-1 audit peaks were 381.02/320.58 MiB and
cycle-2 peaks 584.70/514.03 MiB. End-of-cycle-2 snapshot and primary construction
remained around 298/395 MiB: these costs were not removed. The fixture retains
full two-cycle history intentionally; its cross-cycle growth must not be
mistaken for a leak in the campaign, which compacts trace after persisted cycles.

A separate synthetic-container allocation probe (400 unique records) measured:

| Operation | Legacy traced peak bytes | Optimized traced peak bytes |
|---|---:|---:|
| Canonical hash | 2261464 | 6528 |
| Complete structural comparison | 2656696 | 2904 |

Under tracemalloc these kernels became slightly slower (hash 0.058/0.062 s,
comparison 0.092/0.120 s). Those kernel timings are not engine throughput.

## Scientific equivalence and compatibility

The two-cycle canonical primary hashes are identical between allocation modes:

* Cycle 1: `0d29870356e67c318a2f90fbeb80fa641841aa60e0f3292b7267c4eea22fba33`
* Cycle 2: `4ef7ae7f80f7be6031e70015239025c5a038d977b4d6ee1d90eda19a9ba74b31`

All four audits returned PASS with `recomputed=True`. Conservation is exactly
equal between modes; maximum absolute residuals across the two cycles are
1.156e-18 kg mass, 1.361e-13 J energy, and 4.310e-19 kg species. No periodicity,
steady performance or predictive power/torque claim follows from these fixtures.

Changing `integrated_2t.py` changes its dependency SHA and therefore engine
identities. The frozen V4 driver correctly returns FAIL_CLOSED:
`repository dependency changed: motorsim/integrated_2t.py`. Frozen V2/V3/V4,
T1-A, its ledger, checkpoint, primaries and atol were not changed. Historical
evidence remains bound to its historical implementation; new code cannot reuse
those artifacts by pretending its identity is unchanged. A later authorized
scientific continuation requires an explicit identity/equivalence decision;
no such migration or new A3b version was made here.

## Tests, budget and remaining limitation

Eight new focal allocation/equality/release tests pass. All 83 existing
`test_integrated_2t.py` cases passed before the combined invocation reached a
historical identity assertion. These include independent primary audit,
mass/energy/species, tamper rejection, checkpoint restore, cycle compaction and
fuel-ledger continuity.

On the changed working tree, the 52 frozen A3b tests produce 32 passes,
3 failures and 17 setup errors: all nonpasses require the frozen historical
dependency identities. They are preserved and reported, not edited or relabeled
as passing. An extracted historical Git bundle is tested separately using the
original bytes verified against the frozen repository-input hashes (including
the original Windows line endings). Its result is recorded in the JSON receipt.
The existing Windows subprocess timeout, memory termination and restart tests
remain the verification mechanism; no massive new suite was created.

A3b accounting remains 783.376/4320 s, with **3536.624 s remaining**. This work
ran only separately authorized diagnostics/tests, not A3b invocations, and did
not write or reset its ledger. Diagnostic times are reported separately.

The remaining blocker is representative peak memory and inclusive cycle cost
for T1-B and especially T1-C under the changed identity. Smaller CFL increases
trace volume; snapshots/primary duplication remain, so C is at higher risk.
No numeric cap proposal is justified from this reduced fixture. The 3072/4096
MiB guards stay frozen; 3584 MiB is not adopted. Another expensive run requires
specific authorization. This intervention ends with a measured, limited
optimization, not a claim that A3b can now complete.
