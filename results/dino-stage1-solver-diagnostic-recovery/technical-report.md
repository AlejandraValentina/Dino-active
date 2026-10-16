# Informe técnico — Diagnóstico y recuperación del solver científico

**Resultado:** `DINO_2T_SOLVER_DIAGNOSTIC_RECOVERY_PARTIAL`. Se corrigió la salida CP1252 del lanzador, se perfiló un fixture y se cerraron diagnósticos de periodicidad, malla e identidad. La viabilidad de la campaña y la independencia científica de malla no están demostradas. No se ejecutaron campañas, RPM de producción ni reanudaciones del focal agotado.

## Rendimiento y memoria

El punto focal histórico (`Escape original`, 3000 RPM, malla de 48 celdas) completó cuatro ciclos en 682.829 s (promedio aritmético 170.707 s/ciclo; no extrapolable). Superó el presupuesto de 600 s en 89.359 s. RSS final: 2,051,182,592 bytes; pico de working set muestreado: 2,151,251,968 bytes, aproximadamente 4 MiB por encima del límite configurado de 2048 MiB. El control RSS es cooperativo en fronteras de paso; no constituye una barrera de memoria del sistema operativo.

Profiling sintético, fuera del punto productivo: test de dos ciclos, 13 celdas/5 conductos, 6088 llamadas a `IntegratedEngine2T.step` en el test de motor. Corrida normal: 52.568 s, pico 1,127,280,640 bytes, proceso alrededor de 99.0% de un núcleo; se observaron 12 núcleos lógicos. La versión con cProfile tomó 203.367 s (3.87× de instrumentación) y 1,132,093,440 bytes.

Una prueba EXPLORATORY sintética de cancelación/checkpoint/resume/auditoría/importación tomó 115.437 s sin profiling y 359.579 s con cProfile (3.11×). En el perfil instrumentado, las cinco llamadas a `audit_integrated_cycle_primary` sumaron 235.693 s inclusivos; `run_exploratory` sumó 248.107 s, `make_integrated_cycle_primary` 142.860 s, importación con reauditoría 107.548 s, 14,615 llamadas a `step` 104.482 s, `_jsonify` 88.520 s y `deepcopy` 62.022 s. Estas cifras se solapan por llamadas anidadas y el caso incluye reauditorías deliberadas; no sumarlas ni extrapolarlas. `gzip.compress` tomó 1.271 s y `_atomic_write` 0.108 s dentro de ese perfil.

**Lectura:** la mayor oportunidad observada está en reconstrucción/replay de primarias y conversiones/copias del pipeline de evidencia, además del avance físico. Las escrituras comprimidas y atómicas no fueron un hotspot en este fixture. El focal de producción sólo conserva tiempo total: no permite separar sus pasos físicos, auditoría y persistencia. No eliminé copias ni reduje auditoría: el perfil disponible no demuestra una equivalencia end-to-end de producción antes/después y esos cambios podrían debilitar la independencia o invalidar hashes. No se afirma una mejora de rendimiento.

## Periodicidad

El detector `REFERENCE_PERIODIC_CONVERGENCE_V2` sí se ejecutó. En el focal, el ciclo 1 no tenía comparación; ciclos 2–4 guardaron cada uno 449 métricas lag-1 con estado `FAIL`; los ciclos 3–4 también guardaron comparación lag-2 `FAIL`. Las rachas permanecieron en cero; ningún período fue aceptado. El timeout cortó la corrida tras 4 de 8 ciclos. El campo final `NOT_EVALUATED` resulta de mapear `classification is None` a ese string, por lo que mezcla “comparaciones ejecutadas sin período aceptado aún” y “detector no ejecutado”. Se conserva intacto el resultado v1 y se documenta el diagnóstico como **sin período aceptado antes del timeout**, no como `NOT_PERIODIC` ni periodicidad aceptada. Métricas cíclicas dependientes siguen indefinidas.

## Malla espacial

La evidencia histórica `EXHAUST_NUMERICAL_CONVERGENCE_V2_PARTIAL` / `FAIL_TERMINAL` mantiene `NOT_ESTABLISHED`: 1/2/4 y 1/2/4/8 no demuestran independencia/asintótico suficiente para separar la respuesta A/B del error espacial. No se repitieron estudios. [mesh-protocol.md](../../openspec/changes/dino-solver-diagnostic-recovery-v1/mesh-protocol.md) propone casos analíticos, niveles 1/2/4/8, control temporal separado, observables completos y tolerancias justificadas antes de preregistro. El estudio queda sin ejecutar por presupuesto y autorización.

## Identidad IMPL2

La identidad congelada registra `integrated_2t.py` = `e3d1e449240478bd6ca955c032ec835fce65479965a5d305d48288a3ef3e29b3`; el archivo actual normalizado es `38d9896e8bf4405945cdc53aea091eb895d7e00a3ec52df0f0263115e971af17`. Los otros 23/24 hashes del inventario coincidían. La diferencia llegó con `3fdc38c` (2026-10-14): (1) `IntegratedEngine2T._geometry` consulta el mapa de válvula de escape con RPM de referencia exacta, mientras mantiene RPM reconstruida para la cinemática; puede cambiar el área calculada cerca de interpolaciones/extremos y evita el fallo ULP en endpoints, por lo que es un cambio de ruta numérica, no sólo metadata; (2) `audit_integrated_cycle_primary(..., preserve_precycle_p7_baseline=True)` cambia replay/baseline de ledger, no el avance físico. Se verificó el test de endpoints y el replay de ciclo. El delta de una corrida de producción no se midió.

Se conservó el preregistro histórico `e26c0599325a9e6296291178ffd2e36457838052f1d9b59de7b6dc0f282d59e3`. La identidad candidata completa está en [impl2-derivative-identity-candidate.json](identity/impl2-derivative-identity-candidate.json) (hash canónico declarado dentro del recibo); no constituye preregistro, autorización, aceptación ni reutilización de checkpoints. La campaña debe permanecer fail-closed hasta un preregistro/versionado y revisión/decisión apropiados.

## Robustez y pruebas

`run_logged.py` fija `PYTHONIOENCODING=utf-8:backslashreplace` para el proceso hijo y configura salida parent con `backslashreplace`: captura y resumen no fallan bajo cp1252, conserva el log UTF-8 y propaga el exit code. Test de CLI real: 2 PASS. Suite focal (periodicidad, Stage 1 preflight sin solver, cancel/checkpoint/resume con auditoría, timeout y memory-failure clasificación): 15 PASS. El preflight rechazo de hash/incompatibilidad permanece fail-closed. El timeout y memory classification nuevo se prueban con `_advance_cycle` simulado; no falsean una falla física.

Verificaciones: OpenSpec strict PASS; `program_status.py check` PASS. Los artifacts pesados de profiling quedaron bajo `${DINO_ARTIFACT_ROOT}/dino-stage1-solver-diagnostic-recovery/v1`; los receipts compactos están en este change.

## Decisión y pendientes

- No se cambió solver, ecuaciones, CFL, esquema, tolerancias, umbrales ni artifacts históricos.
- No se aplicó optimización de solver/evidencia: faltó un before/after end-to-end de configuración productiva con auditoría canónica completa.
- No hay base para completar el horizonte focal bajo el presupuesto existente ni para afirmar viabilidad de 30 RPM. No aumentar el presupuesto automáticamente.
- No declarar independencia de malla ni resultados periódicos. Mantener métricas dependientes de periodicidad indefinidas.
- No ejecutar campaña IMPL2 con el hash histórico incompatible; utilizar una nueva identidad preregistrada sólo tras sus propios preflight y decisión.
- El bug de encoding está resuelto en la ruta operativa documentada (`run_logged.py`); artifacts y solver permanecen iguales.
