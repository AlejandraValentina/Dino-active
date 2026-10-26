# Tasks

The authoritative queue is `results/2t-commercial-core-20261002/program-status.json`.

- [x] PERFV3-SOURCE-FORENSICS — receipt/checkpoint/manifest hashes and compatible phase-zero state verified.
- [x] PERFV3-TRANSFER-DESIGN — conservative state mapping and distinct-run/reset semantics frozen.
- [x] PERFV3-TRANSFER-IMPLEMENT — hash-bound initializer added; commit `9c60db2`, binding fix `ff32967`.
- [x] PERFV3-TRANSFER-TESTS — 4 current focused tests PASS; incompatibilities fail closed.
- [x] PERFV3-PILOT-PREFLIGHT — one-shot contract and storage preflight PASS.
- [x] PERFV3-A10000-PILOT — one run, 15 cycles, 61.59 s, period-1 accepted; hard caps respected.
- [x] PERFV3-DECISION — 102/413 cross-run observables fail; significant speed gain but equivalence not demonstrated; coordinator integration rejected for this result.

No further cycles or campaigns are authorized by this change.
