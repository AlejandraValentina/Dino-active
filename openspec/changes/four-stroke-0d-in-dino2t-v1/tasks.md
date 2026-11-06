## B1.1 — modo 4T 0D de referencia en Dino

- [x] B1-PROJECT — Crear `motorsim/four_stroke_project.py` con
  `MOTORSIM_4T_REFERENCE_PROJECT_V1`, validación, round-trip atómico y adaptador
  a `Project`; sin campos 2T en el archivo.
  — verificar: test:python -m unittest discover -s tests -p 'test_four_stroke_project.py'
- [x] B1-CONTEXT — Implementar `FourStrokeContext` de desktop (proyecto, dirty,
  validación, abrir/guardar) sin modificar `DesktopContext`.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_context.py'
- [x] B1-WORKSPACE — Implementar el workspace 4T de Geometría, Válvulas y
  Conductos, con validación local y etiqueta de referencia.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_workspace.py'
- [x] B1-EXECUTION — Implementar el adaptador de ejecución 4T con
  `project_inputs`, `worker_command()`, `--cycle 4T`, progreso y cancelación.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_execution.py'
- [x] B1-RESULTS — Implementar la vista de resultados 4T con
  `reference_results.load_result`, resumen, P-V/p-V y etiqueta
  `SYNTHETIC_REFERENCE_0D · NOT_VALIDATED`.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_results.py'
- [x] B1-SHELL — Integrar en `DinoDesktopWindow` las acciones Nuevo/Abrir/Guardar
  4T, el cambio de workspace y el título/indicador de modo.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_shell.py'
- [x] B1-REGRESSION — Ejecutar la suite completa y comprobar que 2T, V3 y los
  contratos 4T existentes no cambiaron.
  — verificar: test:python -m unittest discover -s tests -p 'test*.py'

## Cierre B1.1
- Regresión focalizada verde: `test_dino_desktop.py` (28), `test_dino_commercial_desktop_v3.py` (12), `test_desktop_four_stroke_*.py` (31), contratos 4T, shell y V3.
- `test_cae_ui.py` conserva fallos preexistentes (`neutral` vs `error`, artifact externo ausente) y no usa `DinoDesktopWindow`; no bloquea B1.1.
