# Tasks — integrated-solver-verification-v1

Estado del change: diseño A2 (este commit). A3 no autorizado.

## A0/A1 — Cierre y provenance (completado en este change)

- [x] ISV1-PROVENANCE-REPAIR — Cerrar `DINO_POWER_CURVE_V1` como
  infraestructura lista con curva real bloqueada; nota de estado en README
  (bloque P1-R5E); provenance de la tercera revisión externa R2; actualizar
  `continuation_status` y el objetivo en `program-status.json`.
  — verificar: file:results/integrated-solver-verification-v1/provenance-repair-receipt.json contiene README.md

## A2 — Diseño de verificación (completado en este change)

- [x] ISV1-A2-DESIGN — proposal/design/tasks/spec con dos líneas de
  verificación, matriz, tolerancias propuestas, presupuestos por tiers y
  criterios de aceptación; sin tocar solver, física ni contratos.
  — verificar: file:openspec/changes/integrated-solver-verification-v1/design.md contiene "## Alternatives"

## A3 — Estudio (NO forma parte de este change; requiere autorización explícita del dueño)

La ejecución A3 no es una tarea de este change: está desbloqueada por una
autorización del dueño (alcance, tier, caps) y se sigue en la cola durable
`program-status.json` (ISV1-PREREGISTRATION → ISV1-A3-EXECUTION →
ISV1-ACCEPTANCE). Ninguna de estas tareas puede completarse sin esa
autorización.

- ISV1-PREREGISTRATION — Congelar matriz, tolerancias y presupuesto del tier
  autorizado con SHA-256; sin pasos de solver.
- ISV1-A3-EXECUTION — Ejecutar solo el tier autorizado con caps fail-closed,
  checkpoint por identidad y sin extensiones automáticas.
- ISV1-ACCEPTANCE — Reporte contra criterios preregistrados: convergencia o
  `NOT_CONVERGED`, separación de costos, dominio soportado y declaración
  necesaria-no-suficiente.

## Guardrails de ejecución

- Nada de A3 inicia sin autorización registrada en `program-status.json`
  (alcance, tier, caps); el preflight sin solver no requiere autorización.
- Prohibido: MUSCL, cambios de física, campañas, optimizaciones, extensión
  automática de presupuesto, reescritura de P0–P9 o de evidencia histórica.
