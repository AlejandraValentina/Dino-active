## Why
T05 tiene ramas incompatibles al combinar presión acústica fija y selección
de entropía de reservorio. La usuaria autoriza una revisión conceptual previa.
## What Changes
Separar explícitamente pressure-release, no reflectiva y reservorio; si la
revisión aprueba, adoptarR3 y verificar T05/NR01 antes de reanudarP2A.
## Capabilities
### New Capabilities
- `p1-r3-fronteras`: semántica y verificación acotada de fronteras acústicas.
### Modified Capabilities
Sin nuevas capacidades públicas.
## Impact
Contrato nuevo conservando v1/R2, BCideal específica, tests/evidencia y gates.
Sin cambios en Euler/HLLC/HLLE/EOS/CFL/source/T02/T06/0D ni P3.
