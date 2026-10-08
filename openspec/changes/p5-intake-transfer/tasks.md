# Tasks

- [x] Implement isolated geometry, port laws and network data model.
- [x] Compose existing mesh and coupling primitives.
- [x] Add focused geometry/closed-port/topology/state tests.
- [ ] Add full wave, conservation and backflow fixture campaign in the next P5 increment.
- [ ] Human acceptance remains conditional on P4.
- [x] P5-B coordinator skeleton and stage/port traces implemented.
- [ ] Conservative chamber/duct updates, p·dV ledger and integrated global conservation remain before P5-B verification.
- [x] P5-B-R1: aplicación conservativa de fluxes a inventarios de cámaras y validación por stage.
- [x] P5-B-R1: término contractual de trabajo `-p·dV/dt` validado con expansión, compresión y rechazo de entradas no finitas.
- [x] P5B-06: auditoría de fuente única de flux por interfaz; cada interfaz se resuelve una vez desde su propio ducto y se reutiliza para trazas y actualizaciones.
- [x] P5B-07: ledger global de masa; el residuo `ΔM - M_ext` se comprueba con entradas externas, transferencias internas y puertos cerrados.
- [x] P5B-08: ledger global de especie pasiva; el residuo `ΔS - S_ext` se comprueba con entradas externas, transferencias internas y puertos cerrados.
- [x] P5B-09: ledger global de energía; `ΔE = E_ext + W_cc + W_cyl`, con flujo externo y cada trabajo `-p·dV/dt` auditables por separado y sin doble conteo de interfaces internas.
- [x] P5B-10: fixture de volumen cerrado; puertos cerrados, inventarios constantes, trabajo contractual de compresión/expansión y admisibilidad auditados ([evidencia](../../../results/p5b-10-closed-volume-work-20260924/evidence.json)).
- [x] P5B-11: fixture finito single 0D↔1D con pared rígida Euler contractual, validación dimensional de cámara mediante `ChamberState`, conservación global y admisibilidad verificadas; 27 P5B y 40 pruebas relevantes PASS ([evidencia](../../../results/p5b-11-single-0d1d-fixture-20260924/evidence.json)).
- [ ] Integrar inventarios/celdas de ductos, término -p dV/dt y ledgers globales antes del cierre P5-B.
- [x] P5B-12: one-transfer closed subsystem implemented; two interfaces are solved once per SSPRK2 stage, opposite-sign duct/chamber updates, global mass/species conservation, applied energy/work gate, exact closed-port zero flux, interior evolution and admissibility verified ([evidence](../../../results/p5b-12-one-transfer-fixture-20260924/evidence.json)). Final stored-state energy roundoff is reported and bounded separately from the strict stage-quadrature gate.
- [x] P5B-13: two-transfer fixture implemented with two independent finite transfer paths; four interfaces are solved once per SSPRK2 stage, aggregate chamber RHSs reuse opposite-sign fluxes, symmetric/asymmetric independence, global ledgers, closed ports, interior evolution, stage consistency and admissibility verified ([evidence](../../../results/p5b-13-two-transfer-fixture-20260924/evidence.json)). Applied SSPRK2 energy is the strict gate and stored-state roundoff is independently bounded.
- [x] P5B-14: complete atmosphere/intake/crankcase/two-transfer/cylinder finite topology implemented as one conservative global SSPRK2 update; five physical interfaces and all duct interior faces are reevaluated per stage, the atmospheric boundary is the only external ledger input, and applied-vs-stored roundoff gates are evidenced ([evidence](../../../results/p5b-14-complete-fixture-20260924/evidence.json)).
- [ ] P5-C: bounded conditional exhaust integration implemented; 43 focused P5B/P5C tests PASS, with closed-port, exhaust and restart/replay evidence in `results/p5c-conditional-20260924/evidence.json`. Full fixture-bank closure remains pending (backflow, causal delay, complete ledgers).
- [ ] P5-C stage-coherent shared cylinder RHS: blocker found in current adapter; exhaust is applied after P5-B core step.
- [x] Relevant P5-A/P5-B/P3 coupling/P4 exhaust focal regressions: 59 passed.
- [x] P5-C resolved causal front: dominant positive dp/dt, predeclared windows, CFL 0.2/0.4 ordering PASS; precursor retained diagnostically.
- [x] P5-C conditional closure evidence recorded in `results/p5c-conditional-20260924/causal-front-20260924.json`.
- [x] P6 four-species conservative transport and scavenging accounting.
- [x] P6-A four-species state, donor semantics, legacy mapping and scavenging metrics.
- [x] P6-B stage companion integrated with P5-C traces; authoritative species state and derived legacy fresh view.
- [x] P6-C full topology species fixture bank and independent ledgers.
- [x] P6-D restart/determinism and regressions.
- [x] P6 conditional closure: F05-F09 PASS, four species ledgers and local/global species-mass gates PASS; evidence in `results/p6-species-20260925/final-campaign.json` and `evidence.json`; OpenSpec 1.3.1 strict PASS. Classification `P6_SPECIES_SCAVENGING_VERIFIED_CONDITIONAL`, dependency `CONDITIONAL_ON_P4`; P4 remains `BLOCKED / NOT_GRANTED`.

## Revalidación sobre P4 cerrado — 2026-09-29
- [x] Suite focal P5-A/P5-B/P5-C y backflow/ledgers/restart: PASS; receipt `results/p5-p8-revalidation-20260929/revalidation.json`.
- [x] P5 revalidado sobre `P4_PASS`; clasificación condicional histórica conservada y evidencia P5-C parcial no borrada.
- [x] P6 revalidado sobre `P4_PASS`; cuatro especies, scavenging, ledgers, restart y determinismo PASS.

## Revalidación tras recuperación G2-v2 — 2026-09-29

- [x] P5/P6: hashes de producto y runtime sin cambio; 141 pruebas P5–P8/acoplamiento PASS; recibo `results/p5-p8-revalidation-g2-v2-recovery-20260929/receipt.json`.
- [x] Se conservan las clasificaciones condicionales y la evidencia histórica; no se repitió campaña física P8.
- [ ] Nueva revisión independiente P4–P8 pendiente; estado `READY_FOR_NEW_INDEPENDENT_REVIEW`.
