## Why
Dino2T es el producto 2T aceptado y el 4T 0D completo vive solamente en el
MotorSim legacy. La usuaria quiere un simulador que sirva para motores 2T y 4T,
sin compararlos entre sí ni unificar sus proyectos. Integrar el 4T 0D como modo
de referencia permite usar Dino para ambos ciclos sin tocar el contrato V3 del
2T aceptado.

## What Changes
- Nuevo documento `MOTORSIM_4T_REFERENCE_PROJECT_V1`, con geometría, válvulas,
  conductos 4T, régimen opcional y procedencia; sin campos 2T.
- Modo 4T en Dino: crear/abrir/guardar, workspace de geometría, válvulas,
  conductos, simulación y resultados.
- Ejecución con el worker 4T existente (`reference_run` / `MotorSimWorker.exe`),
  manifiesto 4T v4 y lectura estricta con `reference_results`.
- Etiqueta visible `SYNTHETIC_REFERENCE_0D` / `NOT_VALIDATED`; sin claim
  predictivo ni validación experimental.
- El proyecto V3, `engine_configuration`, el solver 2T y los resultados
  históricos quedan intactos. No hay comparación cross-cycle.

## Capabilities
### New Capabilities
- `four-stroke-0d-in-dino2t-v1`: modo 4T 0D de referencia dentro de Dino.

### Modified Capabilities
Ninguna especificación consolidada.

## Impact
Python estándar y PySide6; sin dependencias nuevas. Se agregan
`motorsim/four_stroke_project.py`, módulos de desktop 4T y tests. No se modifica
`engine_project.py`, `engine_configuration.py`, el solver 2T ni el paquete rc7.
El editor legacy `MotorSim.exe` conserva R-02/R-03; este change no los hereda
porque el documento 4T nuevo no serializa campos 2T.
