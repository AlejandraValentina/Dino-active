# P5-A-R1 verification

## FOUNDATION
La foundation existente se verificó con fixtures de interfaces y geometría sin rediseñar el solver.

## FIXTURES
Intake y transfer pasan en flujo directo e inverso. El puerto cerrado produce flujo nulo y el puerto parcial escala continuamente con el área.

## BACKFLOW
Los signos se invierten mediante Riemann, sin clamps ni válvulas implícitas.

## WAVES
Se verificó el contrato de propagación y tiempo de viaje sobre las mallas compartidas para intake y transfer, reutilizando el core existente. No se ejecutó campaña de motor.

## SYMMETRY / ASYMMETRY
Dos transferencias idénticas evolucionan con estados equivalentes; una perturbación aislada no contamina la otra entidad.

## CONSERVATION
El fixture cerrado conserva masa, energía y scalar dentro del contrato analítico; admisibilidad se valida sin clipping.

## DEPENDENCIES
Estos resultados son `INDEPENDENT_OF_P4`. Periodicidad y operación integrada siguen `CONDITIONAL_ON_P4`.

## DECISION
`P5_A_FOUNDATION_VERIFIED_CONDITIONAL`. No iniciar P5-B automáticamente; P4 permanece unresolved.
