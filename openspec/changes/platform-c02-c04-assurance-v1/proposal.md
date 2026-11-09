## Why
C01/C03 y Etapa 1 dejaron abiertos C02/C04: F05 todavía reescribía valores no editados, F03 aceptaba estados de medio ciclo, F16 escribía PASS antes del cierre y A2-13 no exportaba históricos legacy. Esta etapa cierra esos bordes sin cambiar física ni reabrir evidencia.

## What Changes
- F05: Apply conserva identidad exacta de celdas no editadas y sólo re-tipa cambios.
- F07/F14: refresco invalida atómicamente y eje de presión usa ángulo de cigüeñal.
- F03: sólo se acepta un `DINO4T_STATE_CONTEXT_V1` de ciclo completo; estados crudos/medios se rechazan.
- F16: el receipt PASS se escribe después de `process.wait` y exit code 0.
- F10: receta protegida con contexto externo/relativo explícito verificada.
- A2-13: export CSV/HTML incluye históricos legacy con clasificación explícita y la aceptación los reconoce.

## Capabilities
### New Capabilities
- `platform-c02-c04-assurance-v1`: integridad de editor, estado seguro y aseguramiento terminal.

### Modified Capabilities
Ninguna especificación consolidada.

## Impact
`motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/acceptance_smoke_4t.py`,
`motorsim/dino4t/{runner,api,studies}.py`, `tests/verify_dino4t_ab_windows.py` y
tests focalizados. No se toca el solver, P0–P9, tolerancias ni paquetes.
