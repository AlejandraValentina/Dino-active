# integrated-solver-verification-v1

## Why

La curva de potencia del motor 2T Dino depende de `motorsim/integrated_2t.py`,
un solver de volúmenes finitos de **primer orden espacial** (HLLC sin
reconstrucción, sin MUSCL) y **SSPRK2 temporal**, cuya convergencia de malla y
de paso temporal **nunca fue medida** en la ruta integrada. La evidencia
numérica existente (P2/P2B, T01–T12) cubre el solver `gas1d` standalone, no la
ruta integrada con cárter; el cierre R2 fue semántico/offline. Sin un estudio
de convergencia, toda curva de potencia es exploratoria con error no acotado:
no se puede afirmar ni negar validez numérica, y no corresponde introducir
segundo orden (MUSCL) antes de saber cuánto y en qué dirección se desvía el
primer orden.

El dueño aprobó (2026-10-19) una verificación en dos líneas antes de cualquier
campaña nueva:

1. **Precisión numérica**: convergencia espacial (niveles de malla existentes)
   y temporal (CFL) del solver integrado de primer orden, con cuantificación de
   error sobre el fixture sintético existente.
2. **Rendimiento del pipeline**: separar el costo de integración física del
   costo de auditoría/reconstrucción/serialización; en el punto medido a 3000
   RPM la auditoría consume 235.7 s contra 104.5 s de `step` (evidencia:
   `results/dino-2t-scientific-point-v1/performance-profile.json`).

Restricciones del dueño (2026-10-19): sin MUSCL; sin campañas; sin cambios de
modelo físico ni de contratos P0–P9; A3 no se ejecuta sin autorización
explícita de alcance y presupuesto; convergencia numérica = condición necesaria
pero no suficiente para una curva predictiva.

## What Changes

- **A0 — Cierre honesto de `DINO_POWER_CURVE_V1`**: la infraestructura está
  lista (5/5 tareas, UI y comparación verificadas); la curva real no se produjo
  por falta de autorización de corrida y de datos de motor reales. Se archiva
  como objetivo transicionado, sin reescribir evidencia.
- **A1 — Reparación de provenance**: nota de estado vigente en el bloque
  histórico P1-R5E del README (el PASS histórico T01–T12 no es un PASS global
  de P2; P2B terminó `FAILED_INFRASTRUCTURE`/`P2_BLOCKED_SECOND_ORDER`) y
  provenance explícita de la tercera revisión externa R2 (resultado comunicado
  por el dueño, no reproducido por el agente). Sin tocar P0–P9 ni evidencia
  histórica.
- **A2 — Este change**: diseño de verificación con matriz de experimentos,
  observables, criterios de aceptación, presupuestos por tiers, reglas de
  interrupción fail-closed y preregistro del estudio.
- **A3 — Ejecución acotada**: NO se ejecuta en este change. Permanece
  `BLOCKED_LOCAL` en la cola a la espera de autorización explícita del dueño
  (alcance, tier y caps).

## Non-Goals

- No introducir MUSCL, RK de orden superior ni ningún cambio de física,
  ecuaciones o esquema numérico.
- No ejecutar campañas ni pasos de solver dentro de este change (solo
  preflight sin solver).
- No modificar contratos P0–P9, umbrales, expected values, tests congelados ni
  evidencia histórica.
- No implementar optimizaciones de rendimiento: solo medirlas y separarlas.
- No declarar validez predictiva ni aceptación científica; no claim de
  validación experimental.

## Impact

- `openspec/changes/integrated-solver-verification-v1/**` (nuevo).
- `results/2t-commercial-core-20261002/program-status.json` (objetivo, cola,
  gate, provenance R2).
- `README.md` y `AGENTS.md` (provenance y bloque `CURRENT_OBJECTIVE`).
- A3 (cuando se autorice): reutiliza `motorsim/mesh_study_v1.py` y
  `motorsim/exploratory_workflow.py`; escribe solo bajo
  `results/integrated-solver-verification-v1/`.
