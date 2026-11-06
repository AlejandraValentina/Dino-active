## B1.2 — curva RPM 4T de referencia

- [x] B2-ADAPTER — Implementar `FourStrokeCurveExecution` con
  `project_inputs`, `--sweep-input`, progreso, cancelación y `load_sweep`.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_curve_execution.py'
- [x] B2-PAGE — Implementar `FourStrokeCurvePage` con inicio/fin/incremento,
  tabla, gráfico `W_C_J` vs RPM y banner de referencia.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_curve_page.py'
- [x] B2-SHELL — Integrar la pestaña “Curva RPM 4T” y aplicar Geometría,
  Válvulas y Conductos antes de calcular.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_shell.py'
- [x] B2-SMOKE — Ejecutar un barrido real 4T de 2500/3000/3500 rpm y verificar
  `series.json`, manifiestos v4, estados y puntos de la curva.
  — verificar: test:python -m unittest discover -s tests -p 'test_desktop_four_stroke_curve_smoke.py'
- [x] B2-REGRESSION — Ejecutar las suites 4T/V3 y el test CAE corregido.
  — verificar: test:python -m unittest discover -s tests -p 'test*.py'

## Cierre B1.2
- Smoke real 2500/3000/3500: serie de 3 puntos cargada con `load_sweep` en 49.273 s.
- Variantes y estudios de diseño 4T quedan fuera de este change por persistencia y contrato.
