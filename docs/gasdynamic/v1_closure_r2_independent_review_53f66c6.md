# Revisión independiente — cierre MOTORSIM_2T_V1_CLOSURE con R2 (HEAD `53f66c6`)

- **Tipo:** `INDEPENDENT_REVIEW` (agente distinto de la sesión Codex que produjo
  el cierre; solo lectura).
- **Revisor:** Claude (Claude Code, modelo Opus 5.5), sesión separada de Codex.
- **Fecha:** 2026-10-07.
- **HEAD auditado:** `53f66c6ed40cdf8eb81b6d9b2ed2f6cbc6ff7db9`
  ("Close v1 periodicity gate with corrected R2").
- **Rango revisado:** `937719e..53f66c6` (`0e496bc`, `c41ad20`, `9b73a1e`,
  `9e6c0be`, `dddf243`, `5dd7e37`, `53f66c6`).
- **Veredicto:** **FAIL** contra el gate congelado.

## 1. Alcance

Auditoría exclusivamente contra el gate congelado de `MOTORSIM_2T_V1_CLOSURE`
(`openspec/changes/two-stroke-v1-closure/specs/two-stroke-v1-closure/spec.md`,
último commit `92ff28e`, anterior a las campañas): si A′/B′,
`PeriodicDetectorV2`, R2, evidencia, regresiones e integridad justifican
`GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED`. Sin propuestas de features ni
ampliación de alcance; los findings no bloqueantes van a backlog.

## 2. Independencia y su limitación

- Revisión hecha por un agente distinto de Codex, en solo lectura. Scripts de
  análisis fuera del repo (`%TEMP%\c14audit`); el working tree quedó intacto
  (sólo los `results/kt100-hybrid-model-fixture-v2-harness-20261002*` sin
  trackear preexistentes).
- Es un único revisor; no equivale a una revisión científica completa.
- **Conflicto declarado:** el mismo revisor recomendó, en la revisión focal
  previa del FAIL R1 (veredicto `FIX_REQUIRED_BEFORE_RERUN`), la opción de un R2
  con horizonte más largo derivado de R1, y en esa revisión no señaló que el
  spec congelado prohíbe extender el horizonte post hoc. El finding B1 corrige
  esa omisión.
- Esta revisión cubre R2 hasta `53f66c6`. No cubre ningún cambio posterior
  (spec superseding, reclasificación de estado, fix de B1–B3).

## 3. Verificaciones que dieron bien

| Ítem | Resultado |
|---|---|
| `PeriodicDetectorV2` | Recalculado offline desde los primaries: coincide exactamente. **A′ `PERIOD_1` en el ciclo 73 de 111; B′ `PERIOD_1` en el ciclo 38 de 47.** Snapshot del detector idéntico al guardado en `result.json`. Ramas P2 = 0. `motorsim/reference_harness/convergence.py` sin cambios desde `39d4750`. |
| Determinismo | Observables y trayectorias de A′ idénticas entre el R2 abortado (`campaign-a-prime-r2/`) y el corregido (`campaign-a-prime-r2-corrected/`) en los 56 ciclos comunes; sólo difieren `evidence_binding` y, desde el ciclo 11, `checkpoint_binding`. R1 y R2 también idénticos en observables en los ciclos 1–20, para A′ y para B′. Los cambios del runner fueron sólo operativos. |
| Re-auditoría muestral | `audit_integrated_cycle_primary` con `recomputed=True` y `status=PASS` en 11 primaries: A′ ciclos 10, 11, 12, 71, 72, 73; B′ ciclos 24, 25, 36, 37, 38. |
| Hashes ligados frente a HEAD | A′: 8/8 coinciden (solver, detector, auditor, producer, fixture, config, fuel, thresholds). B′: 7/8; el producer difiere porque B′ corrió con el runner `c39a1d6b3806dc2edf63b5f2fe26e7a4bb52492908359832523847e85e999b38`. |
| Física, combustible, malla, RPM, umbrales, racha | Sin cambios en el rango. |
| Integridad P4–P9 | Hash P9 `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d` coincide. Único cambio en `motorsim/` del rango desde `8120ac9`: el auditor en `motorsim/integrated_2t.py` (`937719e`). |
| Regresiones P4–P8 (corrida del revisor) | **304 passed, 4 warnings, 194,38 s**, exit 0, sobre HEAD `53f66c6`. Comando: `python -m pytest tests/test_p4_*.py tests/test_p5*.py tests/test_p6*.py tests/test_p7*.py tests/test_p8*.py tests/test_two_stroke_ports_p5c.py -q -p no:cacheprovider`. Corrida fuera de la infraestructura del repo; el log no se persistió en el repo. |
| Estado convergido | Plausible. A′ ciclo 73: W 2,06 J, Tcyl 1562 K, escape medio 730 K, masa total 1,018 → 0,470 g, especie residual lavada de 243 a 2,1 mg. B′ ciclo 38: W 7,57 J, Tcyl 1700 K, escape medio 688 K. |

### Trayectoria del peor residuo lag-1 (valor/umbral), recalculada offline

- A′: ciclo 5 38,8; 10 33,7; 15 18,9; 20 13,2; 30 11,8; 40 8,5; 50 4,7;
  60 2,5; 70 1,08; 71 0,988; 72 0,899; 73 0,818. Métrica dominante final:
  `ducts.exhaust[4].species.residual`.
- B′: ciclo 5 75,0; 10 30,9; 20 17,9; 25 8,3; 30 3,5; 35 1,24; 36 0,988;
  37 0,784; 38 0,619. Métrica dominante final:
  `ducts.exhaust[6].species.residual`.

## 4. Las dos versiones del preregistro R2

`results/2t-v1-closure-20261006/campaign-preregistration-r2.json`:

| Commit | SHA-256 del archivo | Runner ligado | restart_cycle A′/B′ | Horizonte A′/B′ |
|---|---|---|---|---|
| `c41ad20` (14:04:00 −0300) | `e453e9fe…` | `350ef4d5…` | 56 / 24 | 111 / 47 |
| `9b73a1e` (14:04:33 −0300) | `37e0e6855d7acac7164ddb006d51bf505e10453e417baa78fde351632dd9ab98` | `c39a1d6b…` | 56 / 24 | 111 / 47 |
| `dddf243` (15:39:34 −0300) = HEAD | `7a712f7811ab883a753075b7531f4f8c6ddd404605ef4e68c7767ed13d84c3ee` | `a1515faf835c0e8820052bec89179873582a039732581ea053cf5ace00901f3d` | 10 / 10 | 111 / 47 |

Secuencia temporal (UTC):

- Decisión del dueño `OWNER_DECISION_C14_C15_R2`: 16:35:00.
- Preregistro `9b73a1e`: 17:04:33.
- Arranque de ambas corridas R2: 17:05:04.
- B′ termina: 17:32:40, bajo el preregistro `37e0e685…` y el runner `c39a1d6b…`.
- Primer intento de A′: exit `4294967295` a las 18:35:50, tras 5445,8 s y 56
  ciclos auditados. El camino de restore en el ciclo 56 excedió el
  presupuesto.
- `dddf243` (18:39:34): cambia `restart_cycle` y el producer, y agrega la
  compactación de trace. No cambia el horizonte ni la regla
  `ceil(4 * exhaust_residence_cycles) + 3`.
- A′ corregido: de 18:40:28 a 19:23:10, bajo el preregistro `7a712f78…`, con
  `PERIOD_1` en el ciclo 73.

## 5. Findings bloqueantes contra el gate congelado

**B1. Extensión del horizonte después de observar resultados, prohibida por
el spec.**
- `spec.md:186-196`: *"Each prime campaign MUST run exactly its preregistered
  20-complete-cycle horizon … never be extended post hoc"*. Si no hay periodo
  dentro de los 20 ciclos, el fixture *"fails the v1 gate"*.
- `proposal.md` y el `completion_criterion` repiten *"without extending a
  horizon"*.
- Los horizontes R2 (111/47) se derivaron de tiempos de residencia medidos en
  R1, que es exactamente lo prohibido.
- R1, con V2 evaluado offline, no converge en ninguno de los dos fixtures.
- `OWNER_DECISION_C14_C15_R2` autoriza R2, pero el spec no se modificó: su
  último commit es `92ff28e`, anterior a las campañas. El PASS se apoya en una
  decisión registrada en `program-status.json` que contradice la autoridad de
  requisitos, que es el spec.

**B2. La evidencia de regresiones P4–P8 no está en el repo.**
- C17 y `tasks.md:91` afirman "full relevant P4–P8 regressions".
- La única evidencia es `c17-final-focused-tests`: 88 tests de 3 archivos
  (`test_integrated_2t`, `test_v1_closure_periodicity`,
  `test_reference_harness`).
- La corrida del revisor (304 PASS) muestra que no hay defecto. Lo que falta es
  la evidencia del cierre, y la afirmación tal como está escrita es falsa.

**B3. No hay revisión adversarial interna de R2.**
- El spec (`spec.md:203`) exige "internal adversarial review" para la
  clasificación terminal.
- La única revisión independiente existente es la de R1. No hay ninguna sobre
  la enmienda, R2 ni el cierre.

## 6. Findings no bloqueantes (`POST_2T_V1_BACKLOG` o provenance)

- **N1. Enmienda operacional del preregistro R2.** El preregistro R2 se enmendó
  en `dddf243` después de que B′ ya había terminado y de que se abortara el
  primer intento de A′:
  - el ciclo de restart pasó de 56/24 a 10 y cambió el hash del producer;
  - A′ se ejecutó dos veces bajo "una única R2";
  - B′ queda ligado a un preregistro distinto (`37e0e685…`) y no se reproduce
    con el runner de HEAD sin hacer checkout.

  La identidad bit a bit de observables y trayectorias con el intento abortado
  (56 ciclos) demuestra que no hubo selección ni cambio físico. Es una
  desviación de procedencia, no de sustancia.
- **N2.** En `result.json`, `restart_cycle_next_exact: True` es un literal. Es
  correcto porque sólo se escribe si no hubo excepción, pero no es un valor
  medido.
- **N3.** El hash del auditor cubre sólo
  `inspect.getsource(audit_integrated_cycle_primary)`, no las funciones
  auxiliares que llama.
- **N4.** `detector_projection` etiqueta los registros con `CONTRACT` (V1)
  aunque los consume `PeriodicDetectorV2`. Es inocuo, porque
  `compare_cycles_v2` no lo valida.
- **N5.** El criterio lag-1 declara `PERIOD_1` mientras el peor residuo todavía
  se contrae entre un 9 y un 20 % por ciclo. A′ declara convergencia con 0,82
  veces el umbral y razón ≈ 0,91, lo que deja una cola acumulada de unas 8
  veces el umbral en `exhaust[4].species.residual`. Es la semántica
  preregistrada del detector, no un defecto.
- **N6.** El cortocircuito de fresco es alto: A′ 9,0 de 20,1 mg (≈45 %); B′
  32,6 de 49,3 mg (≈66 %). Es sintético y no es criterio del gate.
- **N7.** `pytest --co` sobre la suite completa da 8 errores de colección por
  rutas de import (`test_examples`, `test_four_stroke_integration`,
  `test_performance_recalculation`, `test_project_simulation`,
  `test_regularization`, `test_simulation_view`, `test_sweep`,
  `test_workspaces`). Están fuera del gate.

## 7. Veredicto

**FAIL** contra el gate congelado. El PASS registrado y la clasificación
`GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED` no están justificados. La parte
computacional de R2 es sólida y fue reproducida; lo que falla es la base
contractual del PASS (B1) y dos piezas de evidencia que faltan (B2, B3).

## 8. Condiciones necesarias para legitimar un nuevo gate

Decisión del dueño, sin ampliar el alcance:

1. **B1:** versionar en un spec, con un commit propio, la enmienda que
   autoriza un único R2 con la regla `ceil(4τ)+3`, citando la decisión del
   dueño. Si no se quiere enmendar el spec, la clasificación correcta vuelve a
   ser `FAIL_TERMINAL` con R1 como evidencia.
2. **B2:** persistir la corrida P4–P8 con `scripts/agents/run_logged.py`, o
   corregir el texto de C17.
3. **B3:** registrar una revisión adversarial de R2 como artefacto durable.
   Esta revisión puede servir para el alcance que cubre, `53f66c6`. Los
   cambios posteriores del fix no quedan cubiertos por ella.

Con esas tres condiciones, la evidencia computacional revisada sostiene la
clasificación, con las etiquetas sintético y `CONDITIONAL_ON_P4`. Sin la
condición 1, el resultado es FAIL.
