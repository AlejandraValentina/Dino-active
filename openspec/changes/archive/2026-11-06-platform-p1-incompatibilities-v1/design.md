## Context
C01/C03 introdujo referencias V2 y un comparador estricto, pero el productor
A/B histórico seguía emitiendo V1. La auditoría v2 también demostró que el
script read-only de reproducción fallaba al cargar `packaging/build_provenance`
y que F02/F09 tenían bordes semánticos no ligados. Etapa 1 corrige esos bordes
sin reabrir física ni invalidar evidencia histórica.

## Decisions
### 1. Productor A/B V2, sin reescribir evidencia V1
`run_ab_pair_v1.py` conserva protocolo/condiciones y usa
`publish_desktop_run` para emitir `run.json` V2 y una referencia V2. Los runs
históricos V1 permanecen intactos y siguen clasificándose `LEGACY_UNVERIFIED`;
no se promocionan retroactivamente.

### 2. Auditoría read-only reproducida
`build_provenance.py` resuelve `bundle_inputs` cuando se carga por ruta y el
script de auditoría añade el root del repo a `sys.path`. La comparación del
manifiesto histórico usa los campos efectivamente registrados; los campos
aditivos (`role`) y paths nuevos se reportan por separado, sin declarar
255/255 falsos positivos.

### 3. F02: binding semántico verificable
`summary_issues` exige:
- `cycle_history` con las seis métricas declaradas, finitas y última entrada
  consistente con `final_cycle`;
- fuentes termodinámicas exactas (`GRI30_SHA256`, `BURCAT_SHA256`, `ACCESSED`);
- `evidence_level` y `warm_start` dentro de los valores nativos admitidos;
- `config_identifier` y conjunto exacto de `models` contra la configuración
  resuelta.

### 4. F09: identidad incompleta no invalida el número
`validate_source_identity(..., require_complete=False)` permite una identidad
`INCOMPLETE` explícita; `summary_issues` la acepta sin convertirla en
`RESULT_INVALID`. La comparación A/B estricta sigue exigiendo
`COMPLETE_CLEAN_SOURCE_SNAPSHOT`. `studies.sweep`, `studies.sensitivity` y el
CLI publican identidad, entorno y `contract_issues`.

## Alternatives considered
- **Reescribir los runs V1 históricos:** rechazado; la evidencia pasada no se
  reinterpreta.
- **Hacer que toda identidad ausente invalide el resultado:** rechazado; mezcla
  confiabilidad de fuente con corrección numérica.
- **Cambiar el comparador para aceptar V1:** rechazado; relaja el contrato de
  procedencia.

## Risks / Trade-offs
- El productor V2 requiere un entorno limpio para ser elegible; un árbol sucio
  seguirá produciendo `DIRTY_OR_UNKNOWN_SOURCE` (correcto).
- El script de auditoría reportará diferencias reales entre el build histórico
  y el árbol actual; no son falsos positivos ni un PASS de paquete.
- La identidad incompleta queda visible y calificada; no se usa para un claim
  de reproducibilidad.

## Verification
- Unit tests: productor V2, auditoría reproducible, seis mutaciones F02,
  identidad incompleta F09, propagación studies.
- Regresión C01/C03 84, A/B/API/Desktop 39, compatibilidad 47, Stage2 28,
  packaging 3; CLI publica identidad/contrato.
