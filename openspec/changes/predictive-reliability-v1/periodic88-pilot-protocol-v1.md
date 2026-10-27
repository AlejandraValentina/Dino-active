# Primera ventana periódica88, seis ciclos máximo

2026-10-27. Depende de auditoría44 PASS de primarias27–30 y preparación
conservativa/reloj verificada. No campaña RPM, no176, no adopción de modelo.

- Origen30 auditado44, proyección P0 conservativa a88 con identidad nueva.
  Validar hashes, constructor nativo fuente, configuración, dependencia de
  auditoría y eventos. No restaurar el checkpoint44 directamente en88.
- Conservar reloj10800°/historia de combustión. Detector vacío con índices
  relativos1–6, ciclos físicos absolutos31–36 registrados por separado.
  Contrato de datosV1/detectorV2, umbrales originales.
- Misma física/geometría/CFL/receta adaptativa. Máximo6 ciclos,260s solver,
  290s admisión,300s watchdog,16MiB+reserva2GiB. No bajar precisión para cumplirlo.
- Guardar checkpoint/receta/detector por ciclo y estados a fases30° sin cambiar
  pasos para muestrear. Faltan muestras: registrar ERROR, no interpolar estados
  ni alterar la trayectoria. FAST+receta si interrumpe el presupuesto.
- Registrar máximo/p90/mediana/fallidos, lag1/lag2, trabajo/IMEP, inventarios y
  conservación. Primer ciclo no tiene comparación: no inventar un PASS.
- Con tres comparaciones disponibles, detener si en sus dos transiciones el
  máximo no baja5% y p90 no mejora. Es admisión de recursos, no detector nuevo.
- Ante candidato, parar y exigir auditoría posterior; L1 no equivale a período
  auditado. Al completar presupuesto sin candidato, conservar resultado y
  analizar antes de otra ventana. No ampliar automáticamente ni ejecutar176.
