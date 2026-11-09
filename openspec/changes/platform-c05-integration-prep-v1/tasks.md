## C05 — preparación de fuente e integración

- [x] C05-F03 — Validar contexto físico, fase, identidad y compatibilidad de
  configuración; distinguir continuación, warm start y reinicio exacto.
  — verificar: test:python -m pytest tests/test_platform_c05_resume.py -q
- [x] C05-F15 — Ciclo de vida de `QRunnable`/`QProcess`, reserva, cancelación
  y cierre durante la ejecución.
  — verificar: test:python -m pytest tests/test_platform_c05_qt_lifecycle.py -q
- [x] C05-F16 — Receipt terminal sólo tras `wait`, exit code y verificación de
  procesos/recursos.
  — verificar: test:python -m pytest tests/test_platform_c05_terminal_acceptance.py -q
- [x] C05-A2-03 — Vincular proyecto, configuración, curva y resultados 4T 0D;
  estados obsoletos, series parciales y reapertura.
  — verificar: test:python -m pytest tests/test_four_stroke_curve_reference.py tests/test_desktop_four_stroke_curve_binding.py tests/test_desktop_four_stroke_curve_page.py -q
- [x] C05-INTEGRATION-PLAN — Documentar secuencia fast-forward, riesgos
  residuales y criterios verificables.
  — verificar: file:results/platform-c05-integration-prep-v1/integration-plan.md
- [x] C05-REGRESSION — Suites focalizadas, C01/C03, C02/C04, P1, API/A-B/
  Desktop, Stage2, packaging y receta protegida con contexto explícito.
  — verificar: test:python -m pytest tests/test_platform_c05_resume.py tests/test_platform_c05_qt_lifecycle.py tests/test_platform_c05_terminal_acceptance.py tests/test_four_stroke_curve_reference.py tests/test_desktop_four_stroke_curve_binding.py tests/test_desktop_four_stroke_curve_page.py tests/test_platform_c02_c04_integrity.py tests/test_c01_c03_native_contracts.py tests/test_platform_p1_incompatibilities.py tests/test_dino4t_api.py tests/test_dino4t_ab_comparison.py tests/test_dino4t_desktop_integration.py -q
- [x] C05-INDEPENDENT-REVIEW — Revisión read-only de los cambios y evidencia.
  — verificar: file:results/platform-c05-integration-prep-v1/reviews/independent-c05-review.md
- [ ] C05-WINDOWS-ACCEPTANCE — Aceptación empaquetada Windows posterior a los
  cambios, requiere build autorizado. No se ejecuta en esta etapa.
  — verificar: pending:authorized Windows build and packaged acceptance
