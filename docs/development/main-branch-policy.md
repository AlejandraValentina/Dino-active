# Dino platform development on `main`

`main` is the official integration base for the unified Dino Desktop platform.
The accepted 2T/4T Desktop integration was consolidated by fast-forward from
`8a140eb90bb31589d697e2b93278343ede73499d` to
`e29f314523b810b88d59727f68ee9ca9f6551dbb`. This retains the integration
branch's commits and its original merge of the independent 4T foundation; no
history was rewritten.

The integration lineage is:

- `dino4t/foundation-v1` at `8d853fbf0816aad9c0c9be7cec8345796d5cf0ea`,
  also identified by tag `dino4t-stage2-v1`;
- merge commit `e7af020` bringing that foundation into the Desktop integration;
- source integration `7a74ee4`, frozen-build correction `552c60e`, and accepted
  Windows Desktop record `e29f314`.

After this consolidation, new work should start from `main`. Specialized 2T
and 4T branches may continue independently, but their changes return through a
reviewed merge into `main`; neither branch replaces the integration base.
Keep each solver, scientific contract, evidence classification, and validation
status independent. Shared Desktop infrastructure may depend on public engine
interfaces, not private numerical implementation details.

Use a separate clean worktree for integration when another checkout contains
local changes. Do not clean, stash, reset, or remove historical worktrees or
artifacts as part of ordinary integration. Release and detached worktrees are
retained as provenance unless their owner explicitly authorizes cleanup.

The Windows acceptance remains the historical candidate built from source
`552c60e` and recorded in
`results/dino4t-desktop-integration-v1/acceptance/windows/receipt.json`. This
consolidation adds no product code, solver changes, scientific evidence, new
Windows package, or public distribution.
