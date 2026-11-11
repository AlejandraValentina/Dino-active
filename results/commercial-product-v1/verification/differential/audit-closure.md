# CP1 differential audit closure

- Decision: **CLOSED_NO_CP1_REGRESSION**.
- Main: `48b3afe` → `613dfd5` (fast-forward).
- Post-merge source smoke: 71 PASS.
- Post-merge packaged Windows acceptance: PASS.
- Differential: 146 baseline failures, 146 CP1 failures, 0 CP1-only, identical causes for 137 isolated common failures.
- General regression: **NOT_GREEN** (inherited).
- External view: **OPEN_INDEPENDENT**.

## Open follow-ups
- `DINO-INC-EXTVIEW-001`: external_view access violation.
- `DINO-DEF-DESKTOP-001`: desktop execution Page IndexError candidate.
- `DINO-INC-BASELINE-TEARDOWN-001`: baseline 0xC0000409 after JUnit.

Evidence: `differential-report.json`, `main-post-cp1-smoke.summary.json`, `windows-cp1-main/acceptance.json`.
