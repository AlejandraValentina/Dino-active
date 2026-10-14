# Design

- Reuse desktop APIs and existing audited result importers. All implementation stays in `motorsim/desktop/`; tests are isolated and never mutate real Windows QSettings.
- Keep engine configurations and historical runs immutable unless the user explicitly edits/saves an existing editable project or creates a named variant through the current validated context. A baseline preference is keyed by project in QSettings; edits never propagate from base to variants.
- Build an integrated shell: context and baseline at top; component tabs at left; results at right; a guarded single-point execution strip at bottom; provenance and audit details in a collapsible evidence drawer. At 980x680, Build and Results stack vertically and critical execution controls stay reachable.
- Preserve exact channel/angle/cell identity. Wave maps are discrete and contain exactly one band per actual cell. Deltas are computed only at identical angle coordinates; no interpolation is introduced.
- Show a cycle-time estimate from the most recent comparable run with equal finite-volume-cell count; use 30 seconds if no matching sample exists. An insufficient budget warning never changes the budget. A separate user action may set the displayed suggestion, capped by the existing 600-second ceiling; if the cap cannot fit the horizon, say so.
- A default artifact root must resolve outside a Git worktree. Existing unsafe preferences and artifacts are preserved and displayed with an explicit correction action; do not silently relocate or delete artifacts. Tests redirect QSettings to temporary INI storage before constructing the application.
- Package validation remains TRIAL when built from a dirty tree. Do not change or overwrite existing `MotorSim.exe` distributions.
