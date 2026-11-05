# Tasks: Dino 4T Desktop A/B engineering workflow v1

The authoritative task states are in
`results/2t-commercial-core-20261002/program-status.json`.

- [x] Strict compatibility and eligibility for A/B performance comparisons.
- [x] Reproducible A/B result, CSV, and technical report exports.
- [x] Bounded execution cancellation and safe-cycle behavior; restartable
      checkpoints are not supported by the current API contract.
- [ ] Execute the fixed two-design API pair once within the preregistered
      720-second combined budget.
- [ ] Build one Windows candidate from a clean, identified source state.
- [ ] Run targeted 2T Desktop/project/result regression tests.
- [ ] Verify the actual packaged Desktop A/B workflow with those API results,
      including exports and cancellation behavior.
