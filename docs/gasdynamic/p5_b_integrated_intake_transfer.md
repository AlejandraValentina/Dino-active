# P5-B integrated intake + transfer coupling

## GOVERNANCE
P4 continúa BLOCKED y no se usa como criterio de aceptación. P5-B es condicional.

## SCOPE / TOPOLOGY
Se creó un coordinador mínimo para atmosphere → intake → crankcase y dos transferencias hacia cylinder. El escape permanece ausente.

## STAGE ORDER
La traza registra ángulo, áreas, estados, interfaces y actualización por stage. Las áreas de puertos respetan intervalos cerrados/abiertos.

## INTAKE / TRANSFER INTEGRATION
Las tres interfaces reutilizan el Riemann existente y conservan entidades independientes. Se verificó apertura dinámica y flujo cero en intervalos cerrados.

## MULTIPLE TRANSFERS / BACKFLOW
La topología y los fluxes por interfaz se registran; no se fuerza una dirección. La campaña integrada no demostró aún backflow natural.

## CONSERVATION / ENERGY ACCOUNTING
El ledger conservativo integrado y el término -p dV/dt aún no están implementados en el coordinador; por eso no se declara verificación global.

## RESTART
Se implementó snapshot/restore y determinismo del fixture corto. La equivalencia terminal conservativa queda pendiente.

## DEPENDENCIES / LIMITATIONS
Los fixtures son independientes de P4. No se ejecutó motor completo, periodicidad, escape ni P6.

## DECISION
`P5_B_BLOCKED_INTEGRATION`: la composición de interfaces está trazada, pero falta actualización conservativa de cámaras/ductos y ledger global.
