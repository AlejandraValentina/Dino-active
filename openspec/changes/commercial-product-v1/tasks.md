## CP0 — hardening comercial

- [x] CP0-PRODUCT-INFO — About/identidad de producto, build, estado científico,
  licencias y soporte en 2T/4T.
  — verificar: test:python -m pytest tests/test_commercial_product.py -q
- [x] CP0-DIAGNOSTICS — ZIP de diagnóstico sin credenciales ni telemetría.
  — verificar: test:python -m pytest tests/test_commercial_product.py -q
- [x] CP0-RECENT-PROJECTS — recientes por familia con poda de inexistentes.
  — verificar: test:python -m pytest tests/test_commercial_product.py -q
- [x] CP0-AUTOSAVE-RECOVERY — autosave fuera del repo y recuperación sin
  sobrescribir el original.
  — verificar: test:python -m pytest tests/test_commercial_product.py -q
- [x] CP0-CLOSE-SAFE — cierre con ejecución activa sin workers huérfanos.
  — verificar: test:python -m pytest tests/test_platform_c05_qt_lifecycle.py -q
- [x] CP0-RELEASE-POLICY — versionado, canal, EULA/licencias, checklist y
  límites científicos documentados.
  — verificar: file:docs/commercial/release_policy.md
- [x] CP0-REGRESSION — suites C01–C05, producto y Windows.
  — verificar: test:python -m pytest tests/test_commercial_product.py tests/test_platform_c05_resume.py tests/test_platform_c05_qt_lifecycle.py tests/test_platform_c05_terminal_acceptance.py -q
- [x] CP0-WINDOWS — candidato Windows subsequent a CP0 y aceptación de about/
  diagnóstico/recuperación.
  — verificar: pending:authorized Windows candidate

## CP1 — completitud de flujo

Orden: (undo/redo, PDF, onboarding) → bundles → (batch, comparación/legacy).

- [x] CP1-UNDO-REDO - historia acotada por contexto (2T, 4T 0D y 4T nativo), limpieza al guardar/cambiar de proyecto y acciones de edición.
  - verificar: test:python -m pytest tests/test_desktop_history.py -q
- [x] CP1-PROJECT-BUNDLES - bundles ZIP 2T/4T nativo/4T 0D con proyecto, resultados/config y trazas, rutas portables, hashes y política legacy `PRESERVE_CLASSIFICATION_NEVER_PROMOTE`.
  - verificar: test:python -m pytest tests/test_desktop_project_bundles.py -q
- [x] CP1-PDF-REPORT - PDF paginado del informe técnico 2T, 4T nativo, A/B y comparación de estudios, con los mismos límites científicos.
  - verificar: test:python -m pytest tests/test_desktop_pdf_report.py tests/test_desktop_technical_report.py tests/test_dino4t_ab_comparison.py -q
- [x] CP1-TEMPLATES-ONBOARDING - guía breve, ejemplos sintéticos 2T/4T nativo/4T 0D y verificación de primeros pasos.
  - verificar: test:python -m pytest tests/test_desktop_onboarding.py -q
- [x] CP1-BATCH-QUEUE - cola 4T 0D acotada (20 curvas/100 puntos), presupuesto, cancelación, reanudación y persistencia JSON; los flujos 2T/nativo conservan sus barridos/estudios acotados existentes.
  - verificar: test:python -m pytest tests/test_desktop_batch_queue.py -q
- [x] CP1-COMPARISON-LEGACY-UX - guía de comparación exacta y aviso explícito de importación legacy con clasificación conservada y sin promoción.
  - verificar: test:python -m pytest tests/test_desktop_legacy_ux.py -q

## CP2 — operación comercial

- [x] CP2-INSTALLER-PORTABLE - ZIP portable con hashes, sin instalador ni registro; desinstalación = borrar carpeta.
  - verificar: file:docs/commercial/portable_release.md
- [x] CP2-UPDATE-CHANNEL - manifiesto local, comprobación manual opt-in y sin auto-update.
  - verificar: test:python -m pytest tests/test_desktop_update_policy.py -q
- [ ] CP2-LICENSING (decisión del dueño) - opciones A/B registradas; pendiente.
- [x] CP2-PRIVACY-TELEMETRY - sin telemetría por defecto; diagnóstico manual.
  - verificar: file:docs/commercial/privacy.md
- [x] CP2-SUPPORT-RELEASE-NOTES - soporte, límites y notas.
  - verificar: file:docs/commercial/support.md; file:docs/commercial/release_notes.md

## CP3 — datos y validación (data-gated)

- [ ] CP3-D2-MEASURED-2T
- [ ] CP3-D4-MEASURED-4T
- [ ] CP3-VAL2-VAL4
- [ ] CP3-PRED2-PRED4

## CP4 — aceptación comercial

- [ ] CP4-UAT
- [ ] CP4-STABILITY-PERFORMANCE
- [ ] CP4-SECURITY-PRIVACY
- [ ] CP4-OWNER-RELEASE-DECISION
