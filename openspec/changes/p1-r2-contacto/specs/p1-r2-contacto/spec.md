## ADDED Requirements
### Requirement: Contacto hidrodinámico independiente
El detector SHALL usar solamente rho,p,u y centros/gamma, sin Y, posición exacta,
ventanas ad hoc ni parámetros ajustados después de evaluar.
#### Scenario: Estudio de precisión
- **WHEN** se aplica el algoritmo fijado a Sod y contacto puro N200/400/800/1600
- **THEN** registra detección, errores, L1 y conservación, manteniendo2dx.
### Requirement: Revisión y continuación condicionadas
R2 SHALL adoptar exclusivamente el cambio de observable T02 si independencia,
precisión y revisión aprueban; SHALL conservar P1 original y T06 íntegros.
#### Scenario: Detector falla
- **WHEN** no es independiente o no cumple precisión
- **THEN** registra NOT_INDEPENDENT o ACCURACY_UNRESOLVED y no reanuda P2.
#### Scenario: Detector aprueba
- **WHEN** R2 aprueba
- **THEN** corrige contabilidad HLLC, exterior no reflectivo y rama T05;
  únicamente tras T05 PASS reanuda T01–T12, sin P3.
