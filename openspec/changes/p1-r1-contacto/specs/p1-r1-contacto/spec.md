## ADDED Requirements
### Requirement: Estudio del observable
La etapa SHALL comparar A/B/C/D sobre las mismas soluciones Sod N200/400/800/1600
y contacto puro, conservando física y método; SHALL registrar errores, L1,
conservación, fallback y tiempos. B SHALL localizarse sin conocimiento del exacto.
#### Scenario: Cruce ambiguo
- **WHEN** no existe un único cruce o se pierde monotonía local
- **THEN** B no se adopta ni se elige oportunistamente otro estimador.
### Requirement: Gate científico acotado
La etapa SHALL mantener 2dx en N400 y exigir convergencia, contacto puro y revisión
independiente para proponer 1D_CONTRACT_V1_R1 con único cambio A→B.
#### Scenario: B incumple precisión
- **WHEN** B supera2dx en N400
- **THEN** registra P1_R1_CONTACT_ACCURACY_UNRESOLVED, preserva P1 original y detiene
  sin correcciones P2, T05, P2B ni P3.
