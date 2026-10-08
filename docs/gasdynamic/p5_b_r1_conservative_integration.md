# P5-B-R1 conservative integration

## STATE UPDATE
El coordinator ahora aplica fluxes de interfaz a los inventarios conservativos de cámara y valida admisibilidad después del stage. Cada solve se reutiliza para ambos lados.

## STAGE CONTRACT / INTERFACE ACCOUNTING
Se conserva el orden de cálculo de ángulo, áreas, estados, Riemann y actualización. Los signos de intake y transfer están auditados.

## VOLUME WORK
El término `-p dV/dt` y la ley de volumen variable aún no están conectados al coordinator; no se inventó una fórmula alternativa.

## LEDGERS
Los ledgers globales de masa, energía y especie requieren inventarios conservativos de ductos y actualización por el core 1D. Permanecen inconclusos.

## FIXTURES / RESTART
Puertos cerrados y admisibilidad pasan en el fixture corto. Snapshot/restore y determinismo básico pasan, pero la equivalencia terminal física queda pendiente.

## LIMITATIONS
No se ejecutó escape, periodicidad, P5-C, P6 ni campaña de motor.

## DECISION
`P5_B_BLOCKED_INTEGRATION`: la actualización de cámaras está implementada, pero falta la evolución conservativa real de ductos, `-p dV/dt` y los ledgers globales.
