## Why
B1.1 agregó el 4T 0D de referencia como modo separado, pero solo permite un
punto RPM. El worker existente ya soporta `--sweep-input` y `sweep.execute_sweep`
es genérico por ciclo; falta exponer una curva RPM 4T sin tocar el solver, el
schema 4T ni el flujo 2T.

## What Changes
- Adaptador de ejecución de barrido 4T con `reference_run --sweep-input`.
- Página “Curva RPM 4T” con inicio/fin/incremento, estado, tabla y gráfico de
  `W_C_J` contra RPM.
- Lectura estricta de `series.json` con `sweep.load_sweep` y manifiestos v4.
- Etiqueta `SYNTHETIC_REFERENCE_0D · NOT_VALIDATED`; sin comparación con 2T.
- Variantes y estudios de diseño 4T quedan fuera de este change.

## Capabilities
### New Capabilities
- `four-stroke-rpm-curve-v1`: curva RPM 4T de referencia dentro de Dino.

### Modified Capabilities
Ninguna especificación consolidada.

## Impact
Python estándar, PySide6 y el worker existente; sin dependencias ni solver
nuevo. Se agregan un adaptador y una página de desktop 4T, más tests. No se
modifican `MOTORSIM_4T_REFERENCE_PROJECT_V1`, el proyecto V3, el solver 2T ni
los resultados históricos.
