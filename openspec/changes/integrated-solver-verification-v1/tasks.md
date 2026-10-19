# Tasks — integrated-solver-verification-v1

Estado del change: diseño A2 + revisión de diseño 2026-10-19 (fases A3a/A3b).
A3b no autorizado; A3a autorizada con límites — corrida pendiente de
confirmación del dueño con el preregistro a la vista.

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

## A3a — Revisión de diseño y preregistro (2026-10-19, autorizada con límites)

- [x] ISV1-A3A-DESIGN-REVISION — Revisión del diseño con atribución por un
  solo eje, acoplamiento espacial/temporal declarado, tolerancia mixta con
  banda absoluta en cercanía a cero, orden `p` solo diagnóstico, buckets
  exclusivos de costo y fases A3a/A3b.
  — verificar: file:openspec/changes/integrated-solver-verification-v1/design.md contiene "### Acoplamiento espacial/temporal declarado"
- [x] ISV1-A3A-PREREGISTRATION — Driver de diagnóstico instrumentado
  (`scripts/diagnostics/integrated_solver_verification_a3a.py`, no modifica
  `motorsim/`) + preregistro congelado con identidad, caps, protocolo y
  criterios; dry-run por defecto sin pasos de solver (`preregistration_check`
  PASS, recibo `a3a-preflight-receipt.json`); corrida única solo tras
  confirmación explícita del dueño.
  — verificar: file:results/integrated-solver-verification-v1/a3a-preregistration.json contiene "DINO_ISV1_A3A_PREREGISTRATION_V1"

## A3 — Estudio (NO forma parte de este change; requiere autorización explícita del dueño)

La ejecución A3 completa no es una tarea de este change: A3a quedó autorizada
con límites (una corrida, 1200 s; ver sección A3a) y su corrida requiere
confirmación explícita del dueño tras el preregistro. El estudio A3b (matriz
de convergencia) sigue desbloqueado solo por nueva autorización del dueño
(alcance, tier, caps) y se sigue en la cola durable `program-status.json`
(ISV1-PREREGISTRATION → ISV1-A3-EXECUTION → ISV1-ACCEPTANCE).

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
