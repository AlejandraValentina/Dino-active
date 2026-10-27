# Tramo único25→29 tras el diagnóstico espacial

2026-10-27. La contracción de presión/composición en352, los balances cerrados
y los controles de representación/tiempo justifican probar la repetibilidad
del motor grueso sin confundirla con independencia de malla. No hay defecto
que justifique cambiar formulaciones. Referencia: informe352 y diseño costeado.

- Restaurar exclusivamente checkpoint25 original44 y detector25. Verificar
  hash de24/25/detector/receipt/ciclos, configuración y fuentes. Reproducir
  observaciones25 desde24/25 sin reintegrar históricos; roundtrip nativo exacto.
- Una invocación, máximo cuatro ciclos26–29,75s solver/85s admisión y90s
  presupuestados totales;16MiB estimados y reserva2GiB. Misma receta adaptativa
  original, física, modelo, CFL, detector y tolerancias. No usar estados
  refinados del diagnóstico ni cambiar cap para acelerar esta continuación.
- Persistir checkpoint/receta/detector por ciclo; FAST+receta si presupuesto
  interrumpe. Conservar snapshots, balances y observables por ciclo; timing
  separado solver/detector/restauración/auditoría/serialización.
- Detener por conservación normalizada>1e-12, inadmisibilidad, límite de tiempo
  o candidato periódico. Este último requiere auditoría posterior, no es PASS.
- Después de tres ciclos nuevos, detener por progreso insuficiente si la
  mediana de máximo error/tolerancia no baja5% frente a la ventana anterior
  y tampoco baja el p90. Es criterio de admisión de recursos; no modifica el
  detector ni la aceptación. Publicar también resultados no favorables.
- Analizar lag1/lag2, distribuciones, variables fallidas, trabajo/IMEP,
  inventarios/composición y persistencia de tendencias. No ampliar ciclos ni
  lanzar otra malla automáticamente. L1/SELF_REVIEW, validación no realizada.
