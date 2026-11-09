## C02/C04 — integridad y aseguramiento

- [x] C02-EDITOR — F05: Apply sin cambios no reescribe valores y sólo re-tipa celdas editadas.
  — verificar: test:python -m pytest tests/test_platform_c02_c04_integrity.py::test_noop_editor_apply_preserves_exact_source_identity -q
- [x] C02-DISPLAY — F07/F14: refresco limpia valores stale y eje de presión en ángulo.
  — verificar: test:python -m pytest tests/test_platform_c02_c04_integrity.py::test_verified_pressure_uses_crank_angle_and_refresh_clears_stale -q
- [x] C04-STATE — F03: contexto de estado de ciclo completo; rechazar state crudo/medio.
  — verificar: test:python -m pytest tests/test_platform_c02_c04_integrity.py::test_raw_or_midcycle_state_is_rejected_without_solver -q
- [x] C04-RECEIPT — F16: receipt PASS después de process.wait y exit code.
  — verificar: test:python -m pytest tests/test_platform_c02_c04_integrity.py::test_terminal_acceptance_receipt_is_written_after_process_wait -q
- [x] C04-ARTIFACT — F10: receta protegida con contexto explícito.
  — verificar: file:results/platform-c01-c03-remediation-v1/verification/run_protected_regression.py contiene PINNED_SOURCE_ROOT
- [x] A2-13-EXPORT — históricos legacy exportables con clasificación explícita.
  — verificar: test:python -m pytest tests/test_platform_c02_c04_integrity.py -q
- [x] C02-C04-REGRESSION — C01/C03, API/A-B/Desktop, Stage2 y receta protegida.
  — verificar: test:python -m pytest tests/test_platform_c02_c04_integrity.py tests/test_c01_c03_native_contracts.py tests/test_dino4t_api.py tests/test_dino4t_ab_comparison.py tests/test_dino4t_desktop_integration.py -q


## Cierre C02/C04
- F05/F03/F16/F07/F14/A2-13 verificados; receta F10 301 PASS, 3 SKIP.
- Regresion focalizada: 74 C01/C03+API/A-B/Desktop, 28 Stage2, 56 artefactos/packaging, 4 C02/C04.
