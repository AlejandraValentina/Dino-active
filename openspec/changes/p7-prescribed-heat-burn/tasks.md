# Tasks

- [x] Contract and strict OpenSpec validation.
- [x] Event capture, source, boundary split, SSPRK2 primitive and restart.
- [x] Integrate source into authoritative P6/P5-C full-topology SSPRK2 stages.
- [x] F01-F08 bounded verification plus integrated F06/restart/replay evidence.
- [x] P6/P5-C focused regressions: 117 passed plus 7 subtests.
- [x] Strict OpenSpec 1.3.1 validation: `npx --yes --cache C:\\dino\\.npm-cache-openspec @fission-ai/openspec@1.3.1 validate p7-prescribed-heat-burn --strict --no-interactive`.
- [x] Final source/admissibility result: conservative source closure; species remain admissible, residual/processed mass is unchanged, and closed-port full-topology integration is conditional on P4.
- [ ] Independent review pending; P4 remains blocked.

## Closure state

- Classification: `P7_READY_FOR_P8_REVIEW`.
- P4: `P4_BLOCKED` / `NOT_GRANTED`.
- Dependency: `CONDITIONAL_ON_P4`.
- Experimental validation: `NOT_PERFORMED`.
- Independent review: `INDEPENDENT_REVIEW_PENDING`.
- Measured residuals remain those recorded in `results/p7-prescribed-heat-burn-20260927/evidence.json`; no new values are introduced here.

## Revalidación sobre P4 cerrado — 2026-09-29
- [x] P7 revalidado: evento no vacuo, source admissibility, heat consistency, conservación, restart y determinismo PASS en la suite focal.
- [ ] Revisión independiente permanece pendiente; no se inicia P9.

## Revalidación tras recuperación G2-v2 — 2026-09-29

- [x] P7 mantiene evento no vacuo, fuente admisible, calor/ledger, restart y replay: suite P5–P8/acoplamiento 141 PASS y hash de producto intacto.
- [ ] Nueva revisión independiente pendiente; P9 detenido.
