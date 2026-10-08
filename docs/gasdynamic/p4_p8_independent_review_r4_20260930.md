# Revisión independiente final R4 de P4→P8 — 2026-09-30

**Dictamen: `INDEPENDENT_REVIEW_BLOCKED`.** Se reproduce el MAJOR `R4-001`: la auditoría durable de P8 acepta cambios en valores contractuales y digests de replay si se modifican de forma concordante en los dos JSON del anchor. Por ello no ratifico P4–P8 como conjunto ni concedo `INDEPENDENT_REVIEW_PASS`. No ejecuté P9. No se modificó código productivo ni la evidencia original.

## Baseline, integridad y método

Revisión sobre `main`, HEAD `3ae81d0d6197a39198297bb579178c2eaaa04c1a`, igual a `origin/main`; el árbol estaba limpio. Los commits examinados incluyen `2451da3`, `5a807d2`, `9c1fabf` y `3ae81d0`; `git diff --check` y Git LFS fsck pasaron. Los receipts R1/R2/R3 permanecen intactos. Se probaron copias temporales de evidencia para ataques de mutación, sin cambiar los artifacts de campaña.

## Hallazgo R4-001 — MAJOR: la auditoría durable P8 no verifica el contenido replay

En `dev_orchestrator/roadmap_executor.py`, `_audit_p8` exige que cada JSON individual sea igual al anchor consolidado, que el CSV coincida en sus columnas seleccionadas y que varios booleanos guardados indiquen PASS. No vuelve a calcular el replay a partir de un estado terminal/ledger primario ni comprueba el digest contra un preimage persistido. La igualdad entre dos copias del mismo dato no acredita que el dato corresponda a la ejecución; las métricas fresh-delivery y short-circuit mutadas tampoco forman parte de la comparación CSV.

Reproducción en una copia temporal de `results/p8-wide-rpm-replay-r3-20260929-r3/`: para el anchor de 2500 rpm cambié `fresh_mass_delivered_kg` a `123.0` tanto en `p8-wide-rpm.json` como en `anchor-2500.json`; repetí con `fresh_short_circuit_mass_kg=456.0`; y, desde otra copia limpia, reemplacé `replay_terminal_digests.first` por 64 ceros en ambos JSON. En los tres casos `_audit_p8(temp_repo)` devolvió:

```text
closure_ok=True, replay_ok=True, csv_equal=True, anchor_files_equal=True
```

El directorio de campaña original no se modificó. Esta prueba falsifica la afirmación de que la auditoría durable por sí misma impide mutar fresh delivery, short-circuit y digest de replay. El runtime de `run_anchor` sí compara valores entre dos recorridos independientes; el hallazgo está en la verificación durable de artifacts, que no reconstruye esos valores ni verifica su preimage. La campaña física R3 puede conservar sus resultados registrados, pero no pasa el gate de integridad adversarial solicitado para la ratificación.

**Fase e impacto:** P8, y por dependencia la decisión agregada final P4→P8. Evita ratificar el gate durable de replay/contabilidad a partir de artifacts que pueden alterarse sin que el evaluador lo detecte. No demuestra que la física de la campaña sea incorrecta.

**Condición de cierre:** agregar una verificación offline que derive los campos contractuales y los digests desde estado/ledger terminal primario persistido, o vincularlos criptográficamente a un preimage persistido e inmutable cuya integridad se verifique. Incluir regresiones de mutación para ambos campos y el digest. Esto queda fuera de esta revisión: no se corrigió código.

## R3-001: G2 y ledger primario de conservación

**Cerrado técnicamente y reexaminado.** El auditor offline `recompute_conservation` deriva balances desde inventarios inicial/final, intercambios externos por etapa, términos de fuente, intervalos, control de volumen y continuidad de segmentos, y los contrasta con diagnósticos guardados sin usarlos como autoridad. En copias adversariales rechazó inventario inicial/final, intercambio externo, fuente, término faltante, `dt=inf`, volumen de control incorrecto e intervalo incompatible. La igualdad de replay 31–50 es igualdad exacta de objetos numéricos tras descompresión, parseo JSON y comparación; no se afirma identidad bitwise de gzip.

Resultado G2 reauditable: `E13_G2_V2_PASS`, ciclo 50, período 2, A=15/B=3. El seed y las métricas se recalcularon desde la historia; configuración declarada: horizonte máximo 400, umbral 0.005, malla 251, `NUMBA_FUSED`, CFL 0.4, float64, `fastmath=false`, `parallel=false`, un worker. La adquisición se detuvo en ciclo 50 por el gate contractual; no hubo horizonte alternativo. Las pruebas focales de conservación/dt fueron **7 PASS**, y la prueba durable de reauditoría sin PASS del productor fue **1 PASS**.

## R3-002 y replay/restart

La corrección de runtime compara estado conservativo, especies, inventarios iniciales/externos, ledgers de gas y especies, eventos P7, trabajo, entrega fresca y cortocircuito; el digest canónico cubre datos del recorrido. La restauración P6 preserva el inventario inicial de especies en tipo canónico. La suite focal de P8 fue **12 PASS, 1 excluida** (campaña); la campaña de cinco anchors se ejecutó por separado. Sin embargo, R4-001 muestra que el verificador durable permite alterar los JSON posteriores sin recalcular ni verificar su preimage. Por eso la remediación de R3-002 no basta para pasar el gate R4.

## C3-R5 y runtime binding

No se repitió la adquisición C3. Se verificó el receipt existente: una adquisición focal, N=100, CFL=0.4, `t_final=0.003`, backend `NUMBA_FUSED`, float64, sin fastmath/paralelismo y un worker; la clasificación guardada es `P4_SCI_C3_PASS`, aún con revisión independiente pendiente. Los siete hashes runtime-binding guardados coinciden con los fuentes actuales. Se revisaron preregistración, decisión, auditor C3 y método de retorno causal/observables B0–B2. No realicé una nueva lectura y recálculo integral de los 366 MB de historia C3 en esta R4; el dictamen global queda bloqueado por R4-001 y C3 conserva su estatus previo, sin ratificación nueva.

## Suites, contratos y alcance por fase

- P4/E13: **188 PASS, 2 excluidas**; además se ejecutaron individualmente las dos pruebas excluidas por el filtro inicial (**2 PASS**). Eran una prueba de ausencia de entrypoint de campaña C3-R4 y la reauditoría durable G2 sin PASS del productor; ninguna ejecutaba una campaña física.
- P5/P6/P7 y acoplamiento: **90 PASS**.
- P8 replay: **12 PASS, 1 excluida**; la excluida es la prueba de campaña, cubierta por la adquisición R3 de cinco anchors.
- P6 snapshot: **16 PASS**.
- R3-001 conservación y regresión R2 `dt=false` con hash actualizado: **7 PASS** en el comando focal; `dt=false` quedó `MALFORMED_CFL_DT`, nunca PASS.
- OpenSpec estricto: PASS para `p4-escape-1d`, `p5-intake-transfer`, `p7-prescribed-heat-burn` y `p8-wide-rpm-performance`. P6 está cubierto por el cambio P5.
- `git diff --check`: PASS. Git LFS fsck: PASS.

Los conteos son ejecuciones separadas y no se suman como una suite única. No se repitieron adquisiciones G2/C3 ni campañas P8 en R4; no se ejecutaron ciclos G2 posteriores a 50.

## Estado P4–P8 y evidencia de campaña

- **P4:** conserva la clasificación científica de governance `P4_FINAL_BLOCKED_C3_INCONCLUSIVE` y aceptación `NOT_GRANTED`. El `P4_PASS` técnico de la matriz previa no queda ratificado por esta revisión.
- **P5:** implementación verificada condicional según artifacts existentes; no se ratifica aquí porque P4 continúa no aceptado.
- **P6:** transporte de especies/scavenging verificado condicional según artifacts y pruebas existentes; sin química ni cambios físicos en R4.
- **P7:** combustión prescrita verificada condicional según artifacts y pruebas existentes; sin cambios ni nuevas integraciones en R4.
- **P8:** estado de campaña `P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL`, cinco anchors completos, semántica estricta `BOUNDED_TRANSIENT_INDICATED`, condicional a P4. R4 no concede la ratificación independiente debido a R4-001.

La campaña R3 guarda anchors para 2500, 5000, 8000, 11000 y 15000 rpm; los gates registrados de finite, geometría, admisibilidad, especies, evento P7 no vacuo, fuente/calor, CFL, masa/energía, restart y replay son verdaderos. Se contrastaron artifacts individuales, JSON consolidado y CSV, pero la mutación concordante muestra que estas copias no sustituyen una rederivación de valores primarios. Frente al histórico P8, trabajo y potencia coinciden exactamente en cuatro anchors; en 2500 rpm difieren solo por redondeo: trabajo `9.77e-14 J`, potencia `4.06e-12 W` (torque `1.55e-14`, presión pico `-2.33e-9 Pa`). No se interpreta como validación periódica, experimental ni predictiva.

La evidencia histórica incluye balances globales de masa/energía, especies, flujos externos y fuentes; los checks de conservación G2 se recalcularon desde el ledger primario. R4-001 está limitado al enlace durable de los campos P8 enumerados y no demuestra un error físico ni invalida por sí solo los balances recalculados G2.

## Estado final y P9

Clasificación final: **`INDEPENDENT_REVIEW_BLOCKED`**, MAJOR reproducible `R4-001`. Findings R1/R2/R3 permanecen como historia y no se reinterpretan como PASS; R3-001 y la regresión MAJOR R2 `dt=false` quedaron cerrados por evidencia posterior; R3-002 está remediado en runtime, pero la auditoría durable falla el ataque R4 descrito.

`experimental_validation = NOT_PERFORMED`. P9 permanece `STOPPED_NOT_AUTHORIZED`; no está lista una autorización P9 derivada de esta revisión. No se hizo push ni se ejecutó P9.
