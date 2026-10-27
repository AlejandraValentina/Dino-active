# Única comprobación30 del streak existente

2026-10-27. Dos comparaciones consecutivas28/29 ya cumplen413/413;
máximo error/tolerancia3.3475→.4831, sin defectos y con balances aceptables.
Esta evidencia justifica una sola comprobación nueva, no ampliaciones
indiscriminadas. Se mantiene STREAK=3 y todos los umbrales originales.

- Origen: checkpoint nativo29 y detector29 (streak2); verificar hashes,
  configuración, fuentes y observaciones reproducidas desde28/29, sin pasos
  históricos. Reutilizar el mismo bucle diagnóstico con límites explícitos.
- Ejecutar **sólo ciclo30**, máximo20s solver/23s admisión/25s presupuestados,
 16MiB con reserva2GiB, física y receta adaptativa originales.
- Conservar checkpoint, receta, detector, observables, balances y timing.
  Parar por inadmisibilidad, conservación o tiempo. Si no completa/pasa,
  congelar extensiones y analizar evidencia; no lanzar ciclo31.
- Si aparece clasificación, es **candidato periódico L1 que requiere auditoría**.
  Preparar replay de primarias del período antes de proclamar periodicidad
  auditada. No ejecutar otra malla ni campaña por este protocolo.
- Conservar evidencias previas. Los atributos Git de las referencias de entrada
  fijan sus bytes originales ya registrados, sin cambiar datos, hashes
  científicos ni significado del modelo.
