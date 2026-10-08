# Auditoría adversarial R2 P4→P8 — 2026-09-29

**Resultado: revisión bloqueada por un MAJOR reproducible.** No se otorga `INDEPENDENT_REVIEW_PASS`. El `P4_PASS` técnico registrado sigue siendo una afirmación pendiente de ratificación; las reclasificaciones dependientes P5–P8 tampoco quedan ratificadas. La validación experimental continúa `NOT_PERFORMED` y P9 sigue detenido. Esta revisión no modifica código, física, contratos ni los artefactos de las dos adquisiciones.

Baseline revisado: `main` en `e6a5de0a2aee55332dac4e06150fd3069a11914b`, `origin/main` en `d616e2946d84080be44e21867602855d12f7c54a`, árbol inicialmente limpio. Rango de corrección: `d616e29..e6a5de0`; se inspeccionó el diff real y no se hizo fetch, push, reset ni rebase. La primera revisión bloqueada, de `544d2dc`, permanece intacta. Esta pasada comparte hilo con trabajo anterior de implementación y no reclama independencia personal distinta.

## Contraste de los tres hallazgos anteriores

1. **Historias E13:** los 50 nuevos checkpoints contienen historias angulares, estado, celdas, trabajo, puerto, masa de referencia, identidad, datos de gates y snapshots del detector. Verifiqué los SHA-256 de las 30 fuentes históricas contra el manifiesto y recalculé las comparaciones decisivas sin importar el comparador, detector ni auditor del producto. La ausencia de historias señalada en la revisión inicial fue corregida para las métricas E13 observadas. El auditor nuevo, sin embargo, acepta una entrada CFL malformada; hallazgo R2-001 abajo.
2. **Detector/restart:** el replay de los ciclos 1–30 produce lag-1 `0`, rama A `5` y B `0` al ciclo 30. `prepare_seed` los deriva de comparaciones, los serializa y `restore_detector` exige esquema, ciclo, rama, identidad y campos de estado; no hay asignación manual de esos streaks en la continuación nueva. La regresión sintética de evolución continua/reanudada pasó. Comparé además los terminales de los 20 ciclos nuevos con la adquisición anterior: `begin`, `end`, `state` y `cells` son exactamente iguales después de decodificar JSON. Esto acredita igualdad numérica exacta de los valores binarios leídos, no identidad de los archivos comprimidos.
3. **CFL en la parada:** `physical_gate` rechaza explícitamente `CFL=false`, ausente y una cadena en lugar de booleano antes de avanzar el detector. El problema restante está un nivel antes: el auditor puede **derivar `CFL=true` desde un `dt` que no es un número**, y con ello aceptar una evidencia adulterada.

| Comparación lag-2 | Work | Cylinder | Sensor máximo | Port | Inventarios máximo | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 44 vs 42 | 0,0000197492 | 0,00000402248 | **0,0061818000** | 0,00000263797 | 0,0000122807 | FAIL, sensor > 0,005 |
| 48 vs 46 | 0,00000587896 | 0,00000169313 | 0,000505678 | 0,00000245810 | 0,00000455179 | PASS |
| 50 vs 48 | 0,00000344875 | 0,00000122085 | **0,000508629756519752** | 0,00000171550 | 0,00000307131 | PASS |

El recálculo independiente de streaks da A=`15`, B=`3`, lag-1=`0`, primera detección de período 2 en ciclo `50`; el ciclo 44 sigue siendo FAIL de B. El G2 original conserva `P4_G2_MAX30_WITHOUT_E13_CONVERGENCE` y la primera adquisición compacta no se alteró. La adquisición nueva contiene exactamente ciclos nuevos 31–50, ninguno 51+, con máximo contractual 400 y umbral de sensor 0,005. No cambió ningún archivo `motorsim/`, ni los resultados anteriores ni los archivos C3 en el rango revisado.

En los **datos efectivamente persistidos**, comprobé tipos numéricos positivos y finitos de `dt` y límites en 702.617 etapas de los 50 ciclos: cero malformados y cero violaciones CFL. Los balances y residuos persistidos quedan por debajo de `1e-10` (máximo de balances `3,374388913987309e-14`, máximo de residuos de etapa `1,9895217603354292e-14`); las extrema de admisibilidad no muestran violaciones. Esta comprobación verifica los valores de gate persistidos; no reconstruye un ledger físico global a partir de todos los intercambios del solver.

## R2-001 — MAJOR: CFL malformado puede recibir PASS contractual

En `dev_orchestrator/p4_g2_v2_offline_audit.py`, `finite()` (línea 45) acepta cualquier booleano como valor finito, y `gates()` (línea 132) evalúa `stage["dt"] <= min(stage["limits"])` sin exigir números reales positivos y finitos. En Python, `False` se compara como `0`: un `dt` JSON `false` produce `CFL=true`. El auditor coteja luego ese true con la afirmación almacenada y acepta el checkpoint.

Reproducción de solo lectura sobre una copia temporal: enlazar los checkpoints 1–49, copiar manifiesto y seed, copiar el checkpoint 50, cambiar únicamente `inputs.gate_inputs.segments[0].stages[0].dt` de `1.0723312057482394e-06` a `false`, comprimir de nuevo y actualizar `decision.json.closing_checkpoint_sha256` al SHA del archivo modificado. Sin cambiar métricas, checks declarados, detector ni solver, `audit(copia)` devuelve **`E13_G2_V2_PASS`, `CONVERGED_PERIOD2`, ciclo 50**. La copia temporal se eliminó; el repositorio y su evidencia no se tocaron. Las pruebas negativas existentes cambian `dt` a otro número que excede el límite, pero no prueban un tipo malformado que Python acepte como número.

El defecto viola el requisito explícito de que un CFL malformado no pueda producir PASS y la afirmación de que el auditor detecta evidencia adulterada. **No afirmo que el `dt` real de ciclo 50 sea inválido:** es un número finito y pasó el cálculo observado. La gravedad MAJOR corresponde al gate de certificación; requiere corrección y regresión focal antes de otorgar revisión independiente PASS. No se propone aquí cambiar thresholds ni resultados físicos.

## Alcance detenido por el hard stop

La matriz P4 y el receipt P5–P8 se leyeron, pero sus etiquetas PASS no se tomaron como autoridad. Por R2-001 se detuvo la ratificación antes de auditar por completo C3, P4A/P4B/E12/E14/E15, P5 restart, P6 especies/ledger, P7 replay/energía y P8 anchors/restart/determinismo. Su estado de revisión R2 es **no ratificado**, no FAIL físico demostrado. No se repitió la campaña P8 de cinco anchors ni se evaluó todavía si sus hashes/provenance bastan para reutilizarla. Los resultados P8 siguen documentados como `BOUNDED_TRANSIENT_INDICATED`, no validación experimental.

Comprobaciones ejecutadas: 25 pruebas focales P4/E13 PASS; OpenSpec estricto PASS para `p4-escape-1d`, `p5-intake-transfer`, `p7-prescribed-heat-burn` y `p8-wide-rpm-performance`; `git diff --check` PASS; `git lfs fsck` PASS. El archivo C3 LFS disponible tiene SHA-256 `cf51eafd6a8058afb325278bf0dc5a2db241dff49d82c014f83d90a29b7536cb`, igual al hash esperado de la revisión anterior. No se ejecutaron suites P5–P8 ni la campaña física después de encontrar el MAJOR, conforme al hard stop. BLOCKERS: ninguno nuevo demostrado. MAJORS: R2-001. MINORS: ninguno.
