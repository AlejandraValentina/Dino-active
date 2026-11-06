## Etapa 1 — incompatibilidades P1

- [x] P1-PRODUCER — Publicar runs/referencias A/B V2 sin reescribir V1.
  — verificar: test:python -m pytest tests/test_platform_p1_incompatibilities.py::test_ab_producer_publishes_v2_run_and_reference_without_solver -q
- [x] P1-AUDIT — Reproducir el script read-only y comparar manifiesto por campos registrados.
  — verificar: test:python -m pytest tests/test_platform_p1_incompatibilities.py::test_documented_audit_script_is_reproducible -q
- [x] P1-VALIDATION — Cerrar F02: cycle_history, thermo_sources, evidence_level, warm_start, config_identifier y models exactos.
  — verificar: test:python -m pytest tests/test_platform_p1_incompatibilities.py -q
- [x] P1-SOURCE — Cerrar F09: identidad incompleta explícita y propagación a studies/CLI.
  — verificar: test:python -m pytest tests/test_platform_p1_incompatibilities.py -q
- [x] P1-REGRESSION — Ejecutar suites C01/C03, A/B/API/Desktop, compatibilidad y packaging.
  — verificar: test:python -m pytest tests/test_c01_c03_native_contracts.py tests/test_c01_c03_artifact_binding.py tests/test_c01_c03_provenance_boundary.py tests/test_c03_source_and_bundle_integrity.py tests/test_dino4t_api.py tests/test_dino4t_ab_comparison.py tests/test_dino4t_desktop_integration.py -q

## Cierre Etapa 1
- Tests focalizados: 84 C01/C03 + 39 A/B/API/Desktop + 47 compatibilidad + 28 Stage2 + 10 P1 + 3 packaging.
- Auditoria read-only: exit 0; P9 coincide; diferencias reales del arbol actual reportadas sin falso 255/255.
- CLI: publica source_identity, runtime_environment y contract_issues.
