# Dino Commercial - notas de release

## CP2 - operación comercial (2026-11-11)

- Licencia perpetua offline con firma Ed25519 y clave pública embebida; la
  clave privada queda en custodia del emisor y no se distribuye.
- Activación por archivo firmado, sin red ni telemetría.
- Modo TRIAL configurable; por defecto 30 días de ingeniería.
- Reinstalación/recuperación por reimportación del mismo archivo de licencia.
- Estado visible en barra, Ayuda → Licencia y Acerca de Dino.
- Actualización manual/opt-in por manifiesto local; sin auto-update.
- Un error de licencia no bloquea proyectos, resultados ni exportaciones.
- Candidato Windows CP2 empaquetado PASS.
- Políticas pendientes: duración comercial definitiva del TRIAL y alcance de
  actualizaciones incluidas.

## CP1 - workflow completeness (2026-11-11)

- Undo/redo acotado en 2T, 4T 0D y 4T nativo.
- Bundles portables con proyecto, resultados, trazas, hashes y política legacy.
- Informes PDF además de HTML/CSV.
- Guía de inicio, plantillas sintéticas y verificación de primeros pasos.
- Cola 4T 0D con presupuesto, cancelación, reanudación y persistencia.
- Guía de comparación exacta y aviso explícito de importación legacy.
- Aceptación de fuente y Windows empaquetado PASS.

## CP0 - hardening comercial (2026-11-10)

- About/producto, diagnóstico ZIP, recientes por familia, autosave/recovery,
  cierre seguro y política de release.
- Candidato Windows rc12 aceptado para el alcance CP0.

## Límites

- Calibración: `NOT_PERFORMED`.
- Validación experimental: `NOT_PERFORMED`.
- Capacidad predictiva: `NOT_CLAIMED`.
- La regresión general permanece `NOT_GREEN` por deuda heredada; no se
  presenta como suite verde ni como validación científica.
- CP2 sigue pendiente de licenciamiento/activación elegido por el dueño.
