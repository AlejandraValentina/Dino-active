# Revisión independiente — C05 preparation branch

- Fecha de re-revisión: 2026-11-09
- Rama revisada: `fix/dino-platform-c05-prep-v1`
- Base declarada: `fa81e9c` (C02/C04)
- HEAD revisado: `b92b744` (fixes sobre `ffc89b3`); el registro C05 de
  OpenSpec/`program-status`/`AGENTS.md`/resultados sigue sin commitear.
- Rol: revisor independiente, read-only. No se modificó código, tests,
  contratos, tolerancias, evidencia histórica, `program-status` ni OpenSpec.
- Única escritura: este archivo.

## Veredicto

**APPROVE** (a nivel fuente)

Los dos hallazgos Altos de la revisión anterior quedaron corregidos y
reproducidos como resueltos. No quedan hallazgos bloqueantes. Persisten sólo
riesgos residuales Bajos y un pendiente que no es de código: la aceptación
Windows empaquetada. La evidencia durable de regresión ya fue refrescada en el
mismo fuente (`b92b744`).

Historial: revisión inicial sobre `ffc89b3` → **REVISE**; re-revisión de
`b92b744` → **APPROVE**.

## Alcance y evidencia usada

- `git show --stat b92b744`: 8 archivos (validation, runner, studies,
  acceptance_terminal, four_stroke_context y tres suites de tests).
- Lectura del diff completo de `b92b744` y de los archivos resultantes;
  `integration-plan.md` y `design.md` actualizados en el working tree.
- Tests reejecutados por el revisor (`QT_QPA_PLATFORM=offscreen`, `TEMP/TMP` y
  `DINO_ARTIFACT_ROOT` externos), solicitados:
  - `test_platform_c05_resume`, `test_platform_c05_qt_lifecycle`,
    `test_platform_c05_terminal_acceptance`,
    `test_four_stroke_curve_reference`,
    `test_desktop_four_stroke_curve_binding`,
    `test_desktop_four_stroke_curve_page`: **40 passed**.
- Grupos adicionales de verificación:
  - `test_platform_c02_c04_integrity`, `test_dino4t_stage2`,
    `test_platform_p1_incompatibilities`, `test_c01_c03_native_contracts`:
    **72 passed**.
  - `test_cae_ui`, `test_desktop_four_stroke_shell`, `test_four_stroke_project`,
    `test_desktop_four_stroke_curve_execution`: **25 passed, 1 skipped**
    (skip externo transparente).
- Reproducciones directas de los hallazgos anteriores:
  - `api.run` (1 ciclo) + segundo `api.run` con su `state`:
    `warm_start="continuation"`, `result_validation.issues == []`.
  - `studies.sensitivity(cfg, parameters=["intake_runner_length"])`:
    `status="ok"` y `initial_state_discarded` registrado.
  - `api.run` con topología incompatible: sigue devolviendo `OPTION_INVALID`
    antes del solver (el contrato estricto no se relajó).
- Evidencia durable refrescada post-`b92b744`, al mismo fuente:
  `c05-focused-final2` → **249 passed, 1 skipped**, exit 0 (810 s);
  `c05-protected-final` → **301 passed, 3 skipped**, exit 0 (191 s). Ambas
  corridas son posteriores a la revisión APPROVE y sustituyen a las anteriores
  `c05-focused-final` (242/1) y `c05-protected` (301/3), previas al fix.
- Sin cambios en P0–P9, ecuaciones, tolerancias o evidencia histórica. El blob
  P9 conserva el SHA-256 congelado `79fbe9b8…4b88a4d`; la diferencia del hash
  del working tree es sólo normalización CRLF.

## Hallazgos

| Severidad original | Hallazgo | Estado | Verificación | Acción restante |
|---|---|---|---|---|
| **Alta** | `WARM_START_VALUES` no admitía `continuation`/`warm_start_different_config`; `api.run` marcaba una continuación válida como `RESULT_INVALID`. | **RESUELTO** | `motorsim/dino4t/validation.py:21-22`; `test_platform_c05_resume.py` usa `api.run`/`api.check_summary`; reproducción directa con `issues == []`. | Ninguna. |
| **Alta** | `sensitivity`/`sweep` abortaban con `ValueError` cuando una perturbación cambiaba la topología, sin fallback a cold start. | **RESUELTO** | `motorsim/dino4t/runner.py:187-205` (`cold_start` seguro); `studies.py:61-75,91-93,209-224` (`_seed_for`, `initial_state_discarded`); tests `test_seed_helper_treats_topology_mismatch_as_cold_start` y `test_sweep_cold_starts_when_an_override_changes_topology`; reproducción de `sensitivity` con `intake_runner_length` OK. La API sigue rechazando topología incompatible con `OPTION_INVALID`. | Ninguna. |
| **Media** | `default_worker_probe` podía publicar PASS si `tasklist` fallaba con código ≠ 0 o salida vacía sin excepción. | **RESUELTO** | `motorsim/desktop/acceptance_terminal.py:20-33`; test `test_worker_probe_rejects_tasklist_error_and_empty_output`. | Ninguna. |
| **Baja** | Un `acceptance.json` PASS preexistente no se invalidaba en una corrida no-PASS. | **RESUELTO** | `acceptance_terminal.py:36-42` renombra a `acceptance-superseded-*.json`; test `test_previous_pass_is_invalidated_by_a_non_pass_run`. | Ninguna. |
| **Baja** | `FourStrokeContext.save` permitía cambiar la ruta del proyecto durante una ejecución. | **RESUELTO** | `four_stroke_context.py:126-129` bloquea el cambio de ruta; test `test_save_as_is_blocked_during_execution`. | Ninguna. |
| **Baja** | El plan/design no listaban el rango completo de commits C05. | **RESUELTO** | `integration-plan.md:22-35` y `design.md:43-46` listan `668b20b`…`b92b744`. | Sólo precisar el hash del commit de registro cuando exista; hoy el texto “HEAD = commit de registro” es prospectivo. |
| **Baja** | No había guardia de que los scripts Windows usaran el helper terminal. | **RESUELTO** | Test estructural `test_windows_scripts_use_the_terminal_helper` exige `finalize_acceptance` y prohíbe escritura directa de PASS. | Ninguna. |

## Riesgos residuales (no bloqueantes)

- `default_worker_probe` ahora falla ante código ≠ 0 y salida vacía, pero
  cualquier salida no vacía que no contenga el nombre del worker se considera
  limpia. No exige explícitamente el marcador “No tasks are running”; es un
  fail-open residual muy acotado.
- `Guardar como` estando inactivo no migra `curves/` al nuevo directorio: las
  referencias quedan `UNAVAILABLE` (nunca se presentan como completas). El
  bloqueo nuevo cubre sólo cambios de ruta durante ejecución.
- En `FourStrokeCurveExecution._on_finished` la reserva se libera antes de
  `attach_curve_reference`; en el mismo hilo no hay carrera, pero el orden no es
  defensivo y la copia a `curves/<series_id>` no tiene lock entre procesos.
- Las conexiones de `_RunTask` a lambdas sin receptor `QObject` podrían invocar
  un widget destruido fuera de `closeEvent`/`shutdown`; los caminos actuales de
  cierre lo mitigan.

## Estado explícito

- **Aceptado a nivel fuente:** F03 (continuación/warm start/cold start seguro y
  vocabulario semántico), F15, F16 y A2-03, con los fixes de `b92b744` y sus
  tests. Sin hallazgos bloqueantes.
- **Verificado en ejecución local:** 40 tests focalizados solicitados, 72
  adicionales y 25/1 skip auxiliares; más la evidencia durable post-`b92b744`
  (`249 passed, 1 skipped` focalizada; `301 passed, 3 skipped` protegida).
  Procesos/hilos falsos, Qt offscreen, reapertura, clasificación de curvas y
  reproducers de API/estudios. No es validación física.
- **Pendiente:** build y aceptación Windows empaquetada (UIA, cierre de
  `MotorSimWorker.exe` en un candidato nuevo) y el commit de registro C05.
  Nada de esto se declara integrado en `main` por esta revisión.
- **Sin claim científico:** calibración `NOT_PERFORMED`, validación experimental
  `NOT_PERFORMED`, predictiva `NOT_CLAIMED`.
