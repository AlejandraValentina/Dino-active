# P5-A intake + transfer foundation

## SCOPE
Se implementó la base API para geometría de ductos, mallas compartidas, leyes de puertos e intercambio Riemann bidireccional aislado.

## GOVERNANCE STATUS
P5 es `AUTHORIZED_CONDITIONAL`; P4 continúa `BLOCKED` y no se reinterpretó como PASS.

## P4 DEPENDENCY
La geometría y los fixtures aislados son `INDEPENDENT_OF_P4`. La campaña integrada, periodicidad y resultados del motor son `CONDITIONAL_ON_P4`.

## TOPOLOGY
Intake: exterior → cárter. Transfer: cárter → cilindro. Cada transfer es una entidad independiente.

## GEOMETRY / PORT LAWS
Se reutiliza `segments_mesh` para frustums exactos. Las leyes de área transfer e intake están explícitas; área cero produce interfaz cerrada.

## COUPLING / BACKFLOW
`interface_exchange` compone `coupling.interface_flux`; el signo lo determina Riemann. No se implementó una válvula unidireccional.

## CONSERVATION / FIXTURES
Los campos de flujo y estados son serializables y están listos para fixtures. La suite completa de ondas, backflow, simetría, asimetría y conservación global queda pendiente.

## LIMITATIONS
No se ejecutó campaña de motor, periodicidad, RPM sweep, scavenging P6, combustión ni P4.

## NEXT PHASE
Completar fixtures aislados y su verificación antes de P5-B.
