# Dino platform main consolidation verification

Date: 2026-11-05

## Git consolidation

- Official branch: `main`.
- Starting main commit: `8a140eb90bb31589d697e2b93278343ede73499d`.
- Accepted integration commit: `e29f314523b810b88d59727f68ee9ca9f6551dbb`.
- Strategy: clean-worktree fast-forward; merge-base was the starting main
  commit. No commits were rewritten, dropped, or pushed.
- 4T foundation: `dino4t/foundation-v1` at
  `8d853fbf0816aad9c0c9be7cec8345796d5cf0ea`, tag `dino4t-stage2-v1`.
- The original 4T merge is `e7af020`; subsequent integration commits are
  `7a74ee4`, `552c60e`, and `e29f314`.
- Other live development branches at consolidation time were the foundation and
  accepted integration branches; both are ancestors of `main` after the
  fast-forward. Historical detached/release worktrees were retained.

## Verification on the consolidated product source

Run from `main` at `e29f314523b810b88d59727f68ee9ca9f6551dbb`:

```text
python -m pytest -q tests/test_dino4t_desktop_integration.py tests/test_dino4t_api.py tests/test_dino_desktop.py tests/test_desktop_technical_report.py
67 passed, 1 skipped in 337.71s

python -m pytest -q tests/test_dino4t_stage2.py
28 passed in 250.65s
```

`python scripts/agents/program_status.py check` returned `CHECK OK`; `promote`
returned `PROMOTED none`. The complete general suite was not rerun: the
repository already records 115 known baseline failures, and the focused tests
exercise the integration scope without rewriting those contracts.

## Packaged Windows acceptance retained as historical evidence

The accepted internal candidate remains the package built from source
`552c60ed9454a9d86ef05707c38d495d109247c3`; it was not rebuilt because this
consolidation contains only branch documentation and operational status.

- Receipt: `results/dino4t-desktop-integration-v1/acceptance/windows/receipt.json`
- Package: `MotorSim-0.1.0-rc12-windows-x64-552c60ed.zip`
- SHA-256: `752e8e8a14819fa42277fc0667f396a3f686e647e6cf70f6b531b8e6eac637d2`
- Executable SHA-256: `7ca0ca86c91152b5e0f1d1de1f2bc6f5d3973703cb03e46dcb3c2dc676c7f048`
- The package archive hash was recomputed from the preserved artifact and
  matched the receipt.

The recorded GUI acceptance covers a historical 2T project and four results,
4T geometry and escape variant edits, save/reopen, bounded execution, CSV and
report export, and the distinction between periodic historical results and a
nonconverged bounded run. It records 4T experimental validation as
`NOT_PERFORMED` and predictive capability as `NOT_CLAIMED`. Known 4T API
limitations (cancellation and serializable checkpoint/restart) remain open.

## Scope and outcome

No solver, physical equation, numerical setting, scientific result, or package
was modified or regenerated. `main` is the integration base; specialized 2T
and 4T work may proceed on separate branches and return through reviewed,
non-destructive merges. No push or public distribution occurred.
