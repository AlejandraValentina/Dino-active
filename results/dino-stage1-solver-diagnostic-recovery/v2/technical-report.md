# DINO 2T Solver Recovery V2 — informe técnico

**Resultado:** `DINO_2T_SOLVER_RECOVERY_V2_READY` para el alcance de software/reporting acotado. No es una declaración de rendimiento end-to-end, periodicidad del motor, independencia de malla ni readiness de campaña.

## Correcciones y evidencia

- **Periodicidad:** Se separó la identidad del detector V2 del contrato de datos V1 que las primarias conservan intencionalmente. Los checkpoints nuevos enlazan SHA-256 del detector y umbrales; los bindings anteriores no reanudan. Los resultados nuevos guardan estado de evaluación, motivo de terminación, ciclos/comparaciones, período aceptado y un índice hacia residuos completos y umbrales por comparación. El importador reconstruye el detector desde primarias y verifica igualdad. Se preservaron recibos `NOT_EVALUATED` históricos.
- **Geometría:** Se confirmó que la implementación actual aplica la RPM configurada al mapa de válvula y conserva RPM reconstruida para cinemática. La reconstrucción puede caer una ULP fuera del dominio configurado en 1000/5000 RPM. Las pruebas controladas confirman área invariable a `nextafter` en 1000, 3000 y 5000 RPM. El fix ya existía: V2 no modificó `integrated_2t.py` ni las ecuaciones.
- **Rendimiento:** Se quitó una copia de 108,9 MB creada mediante `json.dumps/json.loads` sólo para adjuntar metadata después de persistir la primaria canónica. El benchmark de ese paso aislado midió 6,95 s para la conversión anterior; la nueva ruta adjunta metadata y es exactamente equivalente como objeto. La reauditoría canónica permanece intacta. No se midió la mejora end-to-end de un ciclo completo.
- **Profiling 48 celdas:** Una ejecución de 5,125 grados tardó 1,023 s instrumentada y fue cancelada al límite de observación. La reauditoría de una primaria productiva histórica tardó 249,65 s con cProfile y dio PASS/recomputed=true. Esto localiza costo en el replay, copias/conversión, solver de conductos y transporte de especies, pero no se extrapola a un ciclo ni sustituye la corrida histórica de 682,829 s.
- **Malla:** Se implementó setup 1/2/4/8, extracción de señales nativas, receipts por resolución y comparación cuantitativa. El refinamiento conservó geometría, masa, energía y especies con error relativo máximo medido `5,89e-16`. La comparación sólo registra diferencias; no existen tolerancias preregistradas. Setup hizo cero pasos de solver. `spatial_independence = NOT_EVALUATED`.

## Límites vigentes

El preregistro IMPL2 histórico sigue siendo incompatible: `integrated_2t.py` registrado `e3d1e449…`, actual `38d9896e…`. No se alteró el preregistro, no se reutilizan checkpoints bajo esa identidad, no se creó preregistro nuevo y ninguna campaña fue autorizada. El checkpoint focal V1 agotado permanece intacto; Stage 2 no fue activado.

## Verificación

- Suite focal: 122 passed en 380,38 s (workflow, resume/replay/conservación, periodicidad, geometría, mesh, CP1252).
- Pruebas posteriores del extractor de malla: 4 passed.
- OpenSpec strict: 53 passed, 0 failed.
- `program_status.py check` y `git diff --check`: PASS.

Receipts compactos: [recovery-receipt.json](recovery-receipt.json). Los `.pstats`, perfiles, primarias y logs permanecen en `${DINO_ARTIFACT_ROOT}/dino-stage1-solver-diagnostic-recovery/v2/`.
