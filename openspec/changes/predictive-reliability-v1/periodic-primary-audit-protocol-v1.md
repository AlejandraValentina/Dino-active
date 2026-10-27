# Auditoría acotada del candidato periódico30

2026-10-27. No nuevas trayectorias: replay exacto de recetas27–30.
Cuatro primarias permiten verificar las comparaciones28/27,29/28 y30/29
desde etapas completas, no sólo desde ledgers de checkpoints.

- Verificar manifiestos, configuración, fuentes, continuidad de recetas y
  estados27–30 antes de escribir. Reproducir propuestas rechazadas exactas y
  pasos aceptados; terminal físico, reloj, eventos y ledger deben ser idénticos.
- Usar productor/auditor existentes sin cambios; el auditor recomputa SSPRK2,
  RHS, flujos y ledgers. Modo existente preserve_precycle_p7_baseline=True
  conserva el baseline histórico declarado, no cambia física ni tolerancias.
- Usar spool existente y snapshot streaming para limitar RAM (≈2.6GiB libres
  al diseñar); gzip canónico por partes. Primarias externas bajo
  DINO_ARTIFACT_ROOT o ~/Dino-artifacts, sin letras de unidad en código.
- Presupuesto480s global con watchdog; admisión global360s y120s por ciclo.
  Si un ciclo completado supera120s, no iniciar el siguiente. Preflight con
  reserva2GiB:512MiB primarias (máximo128MiB cada una),256MiB temporales y4MiB
  receipts. Sin limpiar históricos. Los spools efímeros propios siguen su ciclo
  de vida existente; las primarias/receipts durables se preservan.
- Parar ante cualquier discrepancia; persistir progreso por ciclo. No corregir
  solver/auditor ni rebajar criterios para conseguir PASS.
- Reconstruir detector original con prefix1–26 y primarias27–30. Exigir
  PERIOD_1/converged_cycle30. Si PASS: periodicidad auditada sólo para este
  caso44. No GCI, validación experimental, promoción o independencia de malla.
  Evidencia L2/SELF_REVIEW; no sustituye revisión independiente de un gate.
