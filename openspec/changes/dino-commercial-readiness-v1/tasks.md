# Tasks — DINO Commercial Readiness V1

- [x] CRV1-EMPTY-ENGINE: Start a project without historical run data and create a supported engine from the Desktop UI. Guided form, assumption-labeled starter, provenance choices, intake choice, empty run-reference list, and template packaging are implemented. Focused/UI regression: 26 passed, 1 skipped.
- [x] CRV1-ENGINE-EDITORS: Connected solver-backed geometry, primary-compression/chamber derivation, intake-control selection, per-field provenance, and the existing escape profile/table editor. Tests: `tests/test_dino_commercial_readiness_v1.py`; Windows editor evidence in `results/dino-commercial-readiness-v1/captures/04-new-engine-configured.png` and `07-exhaust-edited.png`.
- [ ] CRV1-SIMULATION-ANALYSIS: Run coordinator integration produced one bounded transient with stored solver outputs. Still open: a changed variant inherits the previous checkpoint/run identity, and packaged periodic example references do not populate analysis history. Resolve both and prove same-RPM comparison.
- [ ] CRV1-WINDOWS-ACCEPTANCE: Partial Windows receipt exists at `results/dino-commercial-readiness-v1/acceptance/report.md`. Create/edit/run/save/reopen were demonstrated. Comparison remains unverified, so this acceptance task and gate remain open.

- [ ] CRV1-RUN-IDENTITY-REPRODUCER: Add a minimal UI-level regression for stale Run ID/checkpoint reuse after switching to a modified exhaust variant.
