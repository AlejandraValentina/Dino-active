# platform-p1-incompatibilities-v1 Specification

## Purpose
Definir la compatibilidad P1 entre los contratos nativos endurecidos C01/C03 y
sus consumidores: productor A/B V2, auditoría read-only reproducible, binding
semántico F02 e identidad de fuente incompleta explícita F09, sin cambiar
física, tolerancias ni evidencia histórica.
## Requirements
### Requirement: Productor A/B compatible con V2
El sistema SHALL publicar cada endpoint A/B con `DINO4T_DESKTOP_RUN_V2` y
`DINO4T_RUN_REFERENCE_V2` mediante el productor canónico, conservando el
protocolo/condiciones del par y sin reescribir runs V1 históricos.

#### Scenario: Endpoint nuevo
- **WHEN** el productor completa un endpoint
- **THEN** `run.json` y `reference.json` son V2 y `assess_run_reference`
  encuentra un vínculo original verificable.

### Requirement: Auditoría read-only reproducible
El script de auditoría SHALL cargar sus dependencias de packaging sin depender
del `sys.path` del invocador y SHALL comparar el manifiesto histórico por los
campos registrados, reportando aparte campos/paths aditivos.

#### Scenario: Reproducir auditoría
- **WHEN** se ejecuta `audit_dino_platform_v1.py --out ...`
- **THEN** termina con código 0, P9 coincide y no reporta falsos 255/255 por
  `role`; las diferencias reales del árbol actual quedan visibles.

### Requirement: Binding semántico del resultado nativo
El sistema SHALL validar `cycle_history`, fuentes termodinámicas,
`evidence_level`, `warm_start`, `config_identifier` y el conjunto exacto de
modelos contra el resultado y la configuración resuelta. SHALL rechazar
mutaciones que contradigan esos campos sin reescribir el resumen.

#### Scenario: Campo científico alterado
- **WHEN** se altera una métrica de `cycle_history`, una fuente, un nivel de
  evidencia, `warm_start`, el identificador o una clave de modelos
- **THEN** `check_summary` devuelve un issue y el resultado no es elegible.

### Requirement: Identidad de fuente incompleta explícita
El sistema SHALL distinguir identidad de fuente incompleta de invalidez
numérica: una identidad `INCOMPLETE` SHALL conservarse y calificarse, sin
invalidar automáticamente un resultado periódico. La comparación A/B estricta
SHALL seguir exigiendo fuente completa y limpia. `studies` y CLI SHALL propagar
identidad, entorno y `contract_issues`.

#### Scenario: Sin Git
- **WHEN** no hay identidad Git completa
- **THEN** el resultado puede publicarse con `source_identity.status=INCOMPLETE`
  y `DIRTY_OR_UNKNOWN_SOURCE`, pero no es elegible para A/B estricto.

### Requirement: No regresión
El sistema SHALL conservar contratos P0–P9, manifiestos históricos, ecuaciones,
tolerancias y evidencia previa. La verificación SHALL incluir C01/C03, A/B/API/
Desktop, compatibilidad y packaging, sin reclamar release ni validación
científica.

#### Scenario: Cierre de Etapa 1
- **WHEN** se ejecutan las suites focalizadas
- **THEN** pasan y los runs V1 siguen calificados como legacy, sin promoción
  retroactiva.

