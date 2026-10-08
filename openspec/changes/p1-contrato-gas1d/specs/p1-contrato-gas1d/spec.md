## ADDED Requirements
### Requirement: Aceptación P0 sin reescritura
El registro SHALL acreditar aceptación humana de P0 separada del baseline
NUMERICALLY_VERIFIED_BASELINE y SHALL preservar hashes y resultados originales.
#### Scenario: Dependencia autorizada
- **WHEN** la usuaria acepta P0 y autoriza P1
- **THEN** la evidencia derivada habilita únicamente P1, con procedencia explícita.
### Requirement: Contrato cerrado y verificable
P1 SHALL definir Q=A[ρ,ρu,ρE,ρY], EOS, fuente geométrica, FV/HLLC, integración,
CFL, malla, BC, especie/positividad, concepto 0D↔1D y decisiones D1–D11.
SHALL especificar T01–T12 con IC, BC, dominio, tiempo, referencia y métricas PASS.
#### Scenario: Decisión sin resolver
- **WHEN** queda una contradicción científica fundamental
- **THEN** termina SCIENTIFIC_CHANGE_REQUIRED sin implementar solver.
### Requirement: Gate contractual con revisión independiente
P1 SHALL ejecutarse mediante dev_orchestrator, sin reparaciones automáticas,
con revisión independiente real y evidencia trazable. SHALL mantener P2–P9
deshabilitadas y producción intacta.
#### Scenario: Contrato aprobado
- **WHEN** documentos, checks y revisión aprueban
- **THEN** registrar P1_PASS_CONTRACT_READY y WAITING_HUMAN_APPROVAL sin iniciar P2.
