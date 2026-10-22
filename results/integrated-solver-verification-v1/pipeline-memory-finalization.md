# Solver memory architecture finalization

**PIPELINE_MEMORY_IMPROVED_WITH_LIMITATIONS.** The full-state trajectory is no
longer materialized by the new production evidence path. Derived engineering
series and rejection/scalar metadata still grow with samples; neither absolute
constant memory nor representative T1-B/C readiness is claimed.

## Root cause and solution

The previous integration spool removed retained stage trees during stepping,
but `snapshot()` expanded them again. Primary construction deep-copied them;
independent replay retained a second full history; gzip persistence and reload
allocated full JSON buffers and parsed trees. Those simultaneous representations
dominated the previous pipeline peak, rather than the active finite-volume state.

The production exploratory path now uses:

1. **Sealed snapshot views:** a fixed-length view of fsynced, checksummed spool
   records. Later appends cannot change its extent. Leases keep the file alive
   until consumers finish, even after cycle compaction. A failed later append
   cannot invalidate the earlier sealed prefix.
2. **Primary views:** slicing and first/last-record access use the small offset
   index, not a copied trajectory. Explicit legacy deepcopy still materializes
   ordinary containers when a caller requests an editable copy.
3. **Independent streaming audit:** every accepted/rejected SSPRK step is still
   recomputed by the solver. Replay history uses a private spool. Full primary
   reconstruction and equality iterate the sealed records; no producer-trust
   shortcut, observable subset or changed tolerance was introduced.
4. **Canonical streaming persistence:** sorted JSON keys and complete records
   feed SHA-256 and deterministic gzip incrementally. The conventional newline,
   JSON schema, record order and numeric values remain unchanged.
5. **Streaming reload:** the ordinary gzip/JSON is parsed record by record into
   another private spool. Both its raw decompressed digest and canonical digest
   must match; then the independent auditor recomputes it again. The result-import
   route uses the same reader, isolating mutable analysis metadata while sharing
   the sealed trajectory instead of roundtripping the whole primary twice.
6. **Unchanged conventional restart:** the production workflow compacts only
   after persisting a cycle and writes the same complete compact checkpoint and
   atomic manifest. No temporary spool is a restart authority.

Only first/last stage records, geometry-event endpoints and ordered traversal
are needed by these consumers; none needs every full state as a Python object
simultaneously. The index costs eight bytes per record and supplies existing
random-access interfaces. Read-only views are internal to the explicit streaming
snapshot path. Default eager snapshot APIs remain available for compatibility.

## Measurements on increasing work

These are **13-cell synthetic engine fixtures, not T1-A/B/C**. Each pair uses
the same engine/fuel, one complete cycle, RPM, CFL, nominal stepping and loss
model. Diagnostic CFL 0.4/0.2/0.1 scales the number of records; no preregistered
configuration was modified. Legacy mode selects the old list/materialization
path under the same current physical code and source bindings. This isolates
representation effects; it is not a rerun of a historical A3b executable.

Each run includes integration, snapshot, primary, independent audit, actual gzip
write, engineering output, actual gzip read, a second independent audit and a
conventional compact checkpoint. Run_logged enforced 180 s per fixture. Worker
RSS was sampled every 10 ms; very short phases may have no peak sample. Other
tests ran on the host during some timings; these are paired engineering
observations, not statistical campaign throughput claims.

| Accepted steps | Pipeline peak MiB, old/new | Wall seconds, old/new | Artifact MiB |
|---:|---:|---:|---:|
| 1242 | 410.16 / 62.23 | 34.49 / 35.17 | 4.09 |
| 2019 | 630.18 / 78.35 | 57.48 / 58.66 | 6.36 |
| 4330 | 1344.59 / 127.05 | 129.25 / 131.77 | 13.05 |

Final end-to-end overhead is about **2%**, with 85–91% less peak RSS on these
fixtures. At the largest scale CPU was 129.14/131.48 s. Compressed artifact
bytes, not only decompressed canonical hashes, are identical in every pair.
Temporary-spool disk space is additional and is not included in artifact sizes;
the measured wall time does include spool I/O. Disk-full errors remain explicit.
Table times cover the pipeline body. Including process startup/configuration,
the launcher measured 35.31/35.89, 58.39/59.42 and 130.63/132.73 s; those complete
invocation measurements are also preserved in the receipt.

| Phase RSS at 4330 steps, MiB | Old | Streaming |
|---|---:|---:|
| Integration | 219.25 | 38.05 |
| End snapshot | 384.57 | 38.58 |
| Primary generation | 689.58 | 42.52 |
| Independent audit | 1041.30 | 47.30 |
| Gzip persistence | 701.60 | 48.59 |
| Engineering series | 669.17 | 127.05 |
| Gzip reload | 929.53 | 112.41 |
| Independent reaudit | 1344.59 | 112.12 |

Reload/reaudit peaks include engineering vectors still held by the caller; they
are not independent additive allocations. The new audit peaks across the three
scales are 42.06/43.09/47.30 MiB, while engineering peaks are
62.23/78.35/127.05 MiB. This identifies the remaining dominant structure.

At 4330 steps gzip write took 4.30/4.95 s and reload 2.37/6.20 s. The added
decode/spool cost is real, but full-primary construction improved from
16.65 to 14.69 s and audit remained 42.06/42.77 s. The diagnostic checkpoint
timer covers compact snapshot construction; its small JSON file write is also
inside total wall time. Production atomic checkpoint/manifest persistence is
covered by the workflow tests, not substituted by the benchmark writer.

The integration RSS slope between first and last progress samples was:

| Steps | Old RSS bytes/step | New RSS bytes/step |
|---:|---:|---:|
| 1242 | 44936 | 4 |
| 2019 | 45406 | 378 |
| 4330 | 45449 | 650 |

RSS slopes include allocator effects and rejection logs; they are not Python
object sizes. A separate real small-engine partial fixture at 20/60/120 steps
measured retained Python allocation growth with tracemalloc: **31458.24 versus
1114.56 bytes/step**, with identical final canonical snapshots. Neither result
establishes constant memory indefinitely. Active state/RHS and bounded row/
compression buffers are now the principal full-state allocations; rejection
logs, index and scalar/output vectors remain proportional to samples.

## Integrity and robustness

All three pairs have exactly equal accepted/rejected counts, primary and compact
checkpoint digests, engineering-output digests and conservation values. All
12 benchmark audits/reaudits returned PASS with `recomputed=True`. Every recorded
solver dependency hash matches the final current core implementation. These
fixtures do not demonstrate periodicity, steady-state convergence or predictive
HP/torque.

The focal verification includes canonical and exact gzip equivalence, record
corruption/truncation, noncanonical JSON, wrong hashes, buffer limits, fsync and
restore-write failures, preserved sealed prefixes, lease cleanup, full physical
replay, checkpoint restore and real Windows spawn interruption. A killed gzip
writer leaves its prior valid target untouched; incomplete temporaries from a
dead owner are preserved in quarantine. Live or unverifiable owners fail closed.
An unmanifested complete primary still blocks automatic resume as before.

Development exposed two corrected cases: a test mislabeled already-canonical
JSON as invalid, and the native tuple view needed exact tuple/list-normalized
geometry comparison during restore. No numerical tolerance was changed.
An initial pipeline prototype had 33% overhead; eliminating repeated row
normalization reduced the final paired overhead to about 2%. Prototype evidence
is preserved externally and is not mixed with the final-source measurements.

There are **65 unique focal tests passing**: the 64-case final base suite and
the subsequent 33-case import regression including one extra isolation test.
Exact commands/timings and checks are recorded in the adjacent receipt. Historical
frozen-suite identity failures are not hidden: the optimized code intentionally
fails V4 preflight on the changed `engine_configuration.py` dependency. No frozen
hash or historical test was edited to accept it.

The history-import caller still returns dense derived traces for all selected
cycles. Those requested output collections can grow with both samples and cycle
count, even though primary loading and reaudit no longer reconstruct all stage
trees. No interface or result-selection policy was changed.

## Remaining limitation and real-engine viability

`make_integrated_engineering_output` and its builder return dense angle/channel
arrays, and temporarily retain the derived sample dictionaries. Those O(samples
times channels) representations now dominate the largest peak. They contain
requested engineering information, not redundant full SSPRK history. Their
materialization is a limitation of the current derived-output API, not a physical
necessity. Columnar/lazy derived series could reduce it, but this intervention
does not claim that further change was implemented. Legacy eager snapshot/load
callers also remain proportional to history. The streaming reader bounds an
individual metadata/record value; it does not make arbitrarily large manifests
or rejection logs constant-memory objects.

Therefore strict bounded memory of the **whole** pipeline is not demonstrated.
The measured correction removes the original full-state multiplication across
snapshot/primary/audit/persistence, while exposing a smaller, explicit next limit.
No claim is made that it is impossible to remove that limit.

T1-B/C have 48 cells and different dynamics, step counts and channels. No valid
linear extrapolation from this 13-cell fixture gives their RSS or inclusive
runtime. The evidence supports requesting one representative diagnostic, not
authorizing it automatically. The minimum next test is one separately authorized
48-cell cycle at CFL 0.2, with the selected streaming implementation/source hashes,
complete independent audit, checkpoint and phase telemetry. Reserve at most
600 s, 3072 MiB worker and 4096 MiB aggregate; actual cost is unmeasured. State
explicitly how its charge and identity relate to A3b before launching it.

A3b remains **783.376/4320 s consumed, 3536.624 s left**. The old B–E projection
was 3560.282 s, already larger than the balance. The toy timing does not establish
that B–E now fit; no counter, cap or budget was reset or increased.

## Versions and files

Implementation: `integrated_2t.py`, `_trajectory_store.py`, new `_evidence_io.py`,
`exploratory_workflow.py`, and `engine_configuration.py`. Both helpers are now
bound by the full workflow/build-manifest identity as well as cycle solver
dependency hashes. Tests/benchmark and the necessary status/receipts accompany
the code. No desktop changes, new A3b protocol, campaign or push.

Seventeen historical source evidence files and four V4 evidence files are
verified unchanged, including T1-A and its ledger. Frozen V2/V3/V4 and atol are
preserved. Scientific equivalence on these fixtures is not authorization to
combine identities or reuse historical artifacts. Exact new hashes, external
artifact digests and the final verification outcome are in
`pipeline-memory-finalization-receipt.json`.
