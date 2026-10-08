# ENGINE_PHYSICS_V1 phase review

## Scope and independence

This is a durable adversarial self-review of the new engineering phase. It is
not an independent external review and makes no experimental claim. The frozen
R2 baseline is `1a58b2a5c23447f81308609acc37ab74a8bd5de5`; no R2 campaign,
KT100 campaign or R3 was reopened.

## Preregistration and execution

- Preregistration: `results/engine-physics-v1/preregistration.json`, v1.1,
  SHA-256 `9f613ae3de44913611beb3266de0905bf4eccbc5f9ac2bac44fda1e72f067310`.
- Producer: `scripts/engine_physics_v1_campaign.py`, SHA-256
  `67fe013b9bd6d5ae82edfc2e57c3caa96faae8be3dc7b5f3ddc4b8888249942d`.
- Campaign receipt: `results/engine-physics-v1/campaign-run/engine-physics-v1-four-point-r3.summary.json`, exit 0, duration 1469.171 s.
- Final result: `results/engine-physics-v1/campaign-evidence-r3/result.json`,
  SHA-256 `90d71e20f9c174a4ab105644d384176c38337e459a1885ad59ff16372ea802b`.
- Derived-output refresh was offline from accepted primaries only; no solver
  step was rerun. Its producer is
  `scripts/refresh_engine_physics_v1_outputs.py`.

## Point results

All four points completed 12 cycles, passed primary audit, passed checkpoint /
restart verification, and passed `ENGINE_PLAUSIBILITY_GATES_V1` hard gates.
The real `PeriodicDetectorV2` classified all four as
`NO_CONVERGENCE_WITHIN_HORIZON`; this is an engineering-horizon result and is
not promoted to periodic convergence or substituted for the historical R2
closure result.

| Point | RPM | Periodicity | Hard gate | Warnings |
|---|---:|---|---|---|
| ENGINE_A_3000 | 3000 | NO_CONVERGENCE_WITHIN_HORIZON | PASS | nonpositive synthetic brake/net piston work |
| ENGINE_A_4000 | 4000 | NO_CONVERGENCE_WITHIN_HORIZON | PASS | nonpositive synthetic brake/net piston work |
| ENGINE_B_3000 | 3000 | NO_CONVERGENCE_WITHIN_HORIZON | PASS | none |
| ENGINE_B_4000 | 4000 | NO_CONVERGENCE_WITHIN_HORIZON | PASS | none |

Warnings are recorded as plausibility warnings, not hidden or converted to
zeroes. Undefined scavenging ratios remain explicitly undefined when gross
crossing semantics leave their bounded domain. Fuel burned, AFR, phi, IMEP,
FMEP, BMEP, torque, power, SFC, heat transfer, pressures, temperatures,
species and conservation are serialized in each engineering output.

## Provenance review

Every point binds solver, detector, auditor, producer, configuration, fixture,
fuel and thresholds. The phase fuel is the frozen synthetic surrogate
`SYNTHETIC_GASOLINE_V1` with SHA-256
`b8c385ce4d6ae0cf6078969f22698a4cb4881974d95097085b609c487a691792`.
The new physics module is `motorsim/engine_physics_v1.py`, SHA-256
`3fbed2fe1e04b008405e68c6ec7db0aa2ea595e86c96ede451a91f915e86ec81`.

## Review verdict

The engineering capability is implemented and its four-point synthetic run is
complete with all hard physical gates passing. The evidence supports a
conditional phase classification only: periodic convergence was not reached
within the preregistered engineering horizon, and A-point performance carries
explicit plausibility warnings. No commercial, experimental, or full-RPM
claim is supported.

