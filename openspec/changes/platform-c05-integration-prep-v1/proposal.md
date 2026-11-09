## Why
La auditoría congelada dejó F03, F15, F16 y A2-03 como bordes de aseguramiento
del 4T 0D. Sin cerrarlos, la integración controlada de C05 no puede distinguir
una continuación segura de un reinicio exacto, ni demostrar que una aceptación
no publica PASS antes de cerrar procesos, ni conservar la identidad entre
proyecto, configuración, curva y resultados.

## What Changes
- F03: contexto de continuación versionado con fase, modelo, configuración y
  topología; se distingue `continuation`, `warm_start` y `cold_start`; el
  reinicio exacto no se declara.
- F15: ciclo de vida determinista de `QRunnable`/`QProcess`, reserva de
  ejecución, cancelación y cierre durante la corrida sin huérfanos.
- F16: receipt terminal sólo después de `wait`, exit code 0 y verificación de
  workers/hilos; error, timeout y cierre incompleto no publican PASS.
- A2-03: la curva RPM 4T 0D se vincula al proyecto por identidad, persiste
  junto al proyecto, se reabre y distingue serie completa, parcial, obsoleta,
  corrupta o no disponible. El 4T 0D sigue separado del 4T nativo.
- C05: se documenta la secuencia de integración fast-forward y se registran los
  criterios verificables y los pendientes de aceptación Windows.

## Capabilities
### New Capabilities
- `platform-c05-integration-prep-v1`: preparación de fuente y evidencia para la
  base común confiable de C05.

### Modified Capabilities
Ninguna especificación consolidada. P0–P9, ecuaciones, tolerancias y evidencia
histórica no cambian.

## Impact
Cambios de contrato, ciclo de vida Qt, aceptación y persistencia 4T 0D, con
tests propios. No hay merge a `main`, push, build de distribución ni campaña
científica. La aceptación Windows empaquetada de C05 queda pendiente.
