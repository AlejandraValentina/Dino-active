# Revisión independiente — fix contractual/evidence B1–B3 de MOTORSIM_2T_V1_CLOSURE_R2 (`0c1008b..497e67f`)

- **Tipo:** `INDEPENDENT_REVIEW` (agente distinto de la sesión Codex que produjo
  el fix; solo lectura).
- **Revisor:** Claude (Claude Code, modelo Opus 5.5), sesión separada de Codex.
- **Fecha:** 2026-10-07.
- **Base:** `0c1008b` (revisión independiente previa persistida).
- **HEAD auditado:** `497e67f` ("Clarify durable regression command receipt").
- **Rango revisado:** `0c1008b..497e67f` (`bc17ad6`, `08c97b1`, `1e33aea`,
  `497e67f`).
- **Veredicto:** **`B1_B3_FIX_REVIEW_PASS`**.

## 1. Alcance

- Esta revisión cubre específicamente el fix contractual y de evidencia de los
  findings B1–B3 de la revisión previa. Pregunta única: si el diff
  `0c1008b..497e67f` resuelve correctamente B1–B3 y deja
  `MOTORSIM_2T_V1_CLOSURE_R2` en condiciones legítimas de pasar de `REVIEW` a
  `PASS`.
- **No se volvió a revisar la física de R2.** Tampoco se volvieron a analizar
  A′/B′ ni `PeriodicDetectorV2` desde cero, ni se abrieron findings nuevos de
  producto o roadmap. La evidencia computacional de R2 queda cubierta por la
  revisión previa.
- La revisión previa,
  `docs/gasdynamic/v1_closure_r2_independent_review_53f66c6.md` (SHA-256
  `4185c01cbfd3df4cbce3ac22d78a2edcca0d42ee29836308e74295d8131cddc9`), cubría
  sólo hasta `53f66c6`. Esta revisión cubre el fix posterior y no reemplaza a
  aquella.

## 2. Independencia y conflicto declarado

- Revisión en solo lectura, hecha por un agente distinto de Codex. El working
  tree quedó intacto durante la revisión.
- Es un único revisor; no equivale a una revisión científica completa.
- **Conflicto declarado:** el mismo revisor redactó los findings B1–B3, y en la
  revisión focal del FAIL R1 había recomendado un R2 con horizonte más largo.
  Ese conflicto, declarado en la revisión de `53f66c6`, se mantiene acá.

## 3. B1 — PASS

- **v1.0 se conserva como `FAIL_TERMINAL`** en `program-status.json →
  objectives`, con la clasificación
  `MOTORSIM_2T_V1_CLOSURE_V1_0_FAIL_TERMINAL`.
- **El change histórico no se reescribió:** el `spec.md` y el `proposal.md` de
  `openspec/changes/two-stroke-v1-closure/` no cambian en el diff. En su
  `tasks.md` sólo cambian C14, C15, C17 y C18, y lo hacen para registrar el FAIL
  de v1.0, no para convertirlo en PASS.
- **El change nuevo `openspec/changes/two-stroke-v1-closure-r2/` declara que se
  escribió después de observar R2.** Basa su legitimidad en:
  - la decisión del dueño `OWNER_DECISION_C14_C15_R2`;
  - el preregistro inicial `9b73a1e` / `37e0e685…`;
  - la regla `ceil(4τ)+3`, que da horizontes de 111/47.
- **La procedencia está completa:**
  - la enmienda `dddf243` / `7a712f78…`;
  - el cambio de `restart_cycle` de 56/24 a 10/10;
  - el cambio de producer;
  - los dos intentos de A′, con observables idénticos bit a bit en los 56
    ciclos comunes;
  - la diferencia de producer de B′.
- **No hay afirmaciones falsas sobre el preregistro:** el spec R2 prohíbe
  afirmar que nunca cambió, y esa afirmación no aparece en ningún lado.
- **Estados consistentes:** `program-status.json`, `AGENTS.md` §1, los dos
  `tasks.md` y OpenSpec coinciden en v1.0 `FAIL_TERMINAL` y R2 `REVIEW`.

## 4. B2 — PASS

- **La evidencia completa está en el repo:**
  `results/2t-v1-closure-20261006/p4-p8-regression-b2-complete/` contiene
  manifest, log y summary.
  - Resultado: 304 passed y 4 warnings (`DeprecationWarning` de NumPy), con
    exit 0, sobre HEAD `53f66c6`.
  - Los SHA-256 del log y del summary coinciden con los registrados en el
    manifest.
- **La selección no se manipuló:** son 26 módulos explícitos, el mismo conjunto
  que la corrida por glob del revisor, que también dio 304.
- **El resultado parcial no se usa como final:** `p4-p8-regression-b2/` (301
  tests, sin `test_two_stroke_ports_p5c.py`) queda marcado como selección
  incompleta.
- **C17 apunta a la corrida completa.**

## 5. B3 — PASS

- **La revisión previa no se modificó:**
  `docs/gasdynamic/v1_closure_r2_independent_review_53f66c6.md` mantiene el
  SHA-256 `4185c01cbfd3df4cbce3ac22d78a2edcca0d42ee29836308e74295d8131cddc9` en
  `497e67f`.
- **Su alcance sigue limitado:** está ligada al gate R2 y cubre sólo hasta
  `53f66c6`. En ningún lado se la presenta como revisión del fix.
- **El fix se etiqueta sólo como `SELF_REVIEW`:**
  `docs/gasdynamic/v1_closure_r2_contractual_fix_self_review_0c1008b.md`
  (SHA-256 `cc07111437724ff0a7629f987ad405775862f65825d29aabe306a7a0bbaab99f`),
  que dice explícitamente que no es una revisión independiente.
- **R2-EXTERNAL-REVIEW queda en `REVIEW`**, como corresponde.

## 6. Integridad — PASS

- `openspec validate --all --strict --no-interactive`: 34/34, incluidos
  `two-stroke-v1-closure` y `two-stroke-v1-closure-r2`.
- Hash P9 `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`:
  coincide.
- `git lfs fsck`: OK.
- **Sin cambios de física ni de evidencia entre `0c1008b` y `497e67f`.** No
  cambian:
  - `motorsim/` y `tests/`;
  - el runner de campaña;
  - los preregistros;
  - los specs P4–P9;
  - los resultados de campaña existentes.

  En `results/`, el único archivo modificado es `program-status.json`; el resto
  son archivos añadidos.
- La evidencia P4–P8 es consistente por hash.
- El único cambio de código es `GATE_STATES` en
  `scripts/agents/program_status.py`, que agrega `REVIEW`.
- Herramientas de la cola: `program_status.py check` da OK, `stop-status` da
  `CONTINUE`, y `tests/test_agent_program_status.py` da 27 passed.

## 7. Findings no bloqueantes (backlog)

Ninguno impide el cierre.

1. La evidencia de la tarea R2-B2 en la cola dice que el comando incluye
   `-p no:cacheprovider`. El manifest no lo incluye, porque se corrigió el
   manifest pero no el texto de la cola.
2. El C17 del `tasks.md` de v1.0 todavía dice "Both corrected R2 fixture results
   are PERIOD_1…". Mezcla contexto de R2 en el change histórico, pero no es
   falso.
3. El spec R2 no define criterios de aceptación propios más allá de exigir la
   revisión.
4. `git diff --check` marca una línea en blanco de más al final de 5 archivos
   nuevos. Es sólo espacio en blanco.
5. `program_status.py check` avisa que hay 2 tareas `READY`, menos de las 3
   mínimas.

## 8. Veredicto

**`B1_B3_FIX_REVIEW_PASS`**

- **Queda autorizado el cambio administrativo
  `MOTORSIM_2T_V1_CLOSURE_R2: REVIEW → PASS`.** Este artefacto durable de
  revisión del fix es la evidencia que cierra R2-EXTERNAL-REVIEW.
- **Queda justificado declarar `GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED`**,
  sólo con estos calificadores:
  - sintético;
  - `CONDITIONAL_ON_P4`;
  - sin validación experimental: experimental `NOT_PERFORMED`, predictiva
    `NOT_CLAIMED`;
  - ligado al gate superseding `MOTORSIM_2T_V1_CLOSURE_R2`.
- **El gate histórico `MOTORSIM_2T_V1_CLOSURE_V1_0` permanece `FAIL_TERMINAL`.**
  Nunca se reescribe como PASS, y la declaración anterior no se le atribuye.
- **`MOTORSIM_2T_V1_DEVELOPMENT_FREEZE_CANDIDATE` queda justificado como
  etiqueta de candidato.** No está definido en ningún contrato del repo, así que
  declararlo es una decisión administrativa del dueño, no una clasificación de
  gate. La evidencia revisada no lo impide.
- Esta revisión no reclasifica el gate; la reclasificación se hace en un commit
  aparte.
