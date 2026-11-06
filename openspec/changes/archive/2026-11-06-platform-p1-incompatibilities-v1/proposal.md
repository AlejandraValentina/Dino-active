## Why
La auditoría v2 confirmó que C01/C03 corrige causas a nivel fuente, pero el
productor A/B oficial, la reproducción de auditoría y los bordes semánticos
F02/F09 quedaron incompatibles con el contrato endurecido. Etapa 1 cierra esas
incompatibilidades P1 sin cambiar física, tolerancias ni evidencia histórica.

## What Changes
- Productor A/B oficial publica `DINO4T_DESKTOP_RUN_V2` y
  `DINO4T_RUN_REFERENCE_V2` mediante `publish_desktop_run`.
- Script de auditoría read-only vuelve a ejecutar; el manifiesto histórico se
  compara por campos registrados y reporta campos/paths aditivos.
- F02 liga `cycle_history`, fuentes termodinámicas, `evidence_level`,
  `warm_start`, `config_identifier` y el conjunto exacto de modelos.
- F09 admite una identidad de fuente `INCOMPLETE` explícita sin invalidar el
  resultado numérico; los consumidores estrictos siguen exigiendo fuente
  completa. `studies` y CLI propagan identidad y `contract_issues`.
- Sin cambios de ecuaciones, tolerancias, manifiestos históricos ni paquetes.

## Capabilities
### New Capabilities
- `platform-p1-incompatibilities-v1`: compatibilidad P1 C01/C03 ↔ consumidores.

### Modified Capabilities
Ninguna especificación consolidada.

## Impact
Se modifican `scripts/dino4t/run_ab_pair_v1.py`,
`scripts/audits/audit_dino_platform_v1.py`, `packaging/build_provenance.py`,
`motorsim/dino4t/{validation,studies,__main__}.py`,
`motorsim/source_provenance.py` y fixtures/tests focalizados. No se toca el
solver, el manifiesto primario, P0–P9 ni el estado operativo.
