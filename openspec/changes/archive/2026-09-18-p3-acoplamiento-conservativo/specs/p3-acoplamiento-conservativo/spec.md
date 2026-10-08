## ADDED Requirements
### Requirement: Aceptación y núcleo congelado
P3 SHALL registrar P2_HUMAN_ACCEPTED y preservar hashes del núcleo y contratos.
#### Scenario: Cambio del núcleo
- **WHEN** una incompatibilidad exige modificar una frontera verificada
- **THEN** detiene SCIENTIFIC_CHANGE_REQUIRED sin cambiarla silenciosamente.
### Requirement: Flujo compartido y energía compatible
La interfaz FINITE_WELL_MIXED_0D_COUPLING SHALL resolver un único Riemann
con W0D=(rho,0,p,Y) y el estado de cara1D por stage y aplicar signos opuestos
a masa, energía total Euler y especie. SHALL registrar impulso sin momentum0D.
#### Scenario: Backflow
- **WHEN** cambia el signo del flujo
- **THEN** la dirección emerge del Riemann sin selección previa; conserva el
  vector completo HLLC/HLLE de energía y especie, sin reemplazo manual de donor,
  deadband ni clipping. La mezcla0D incorpora toda la energía entrante a U.
### Requirement: Gates internos y cierre
P3 SHALL ejecutar el gate R1 C00/C00B y revisión independiente antes de volumen
finito (sustituye P3A reservoir bloqueado), y volumen fijo antes de variable,
con C01–C12, regresionesP0/P2 y revisión independiente.
#### Scenario: Bloqueo científico
- **WHEN** no existe rama consistente bajo el contrato congelado
- **THEN** conserva evidencia, marca gates dependientes pendientes y no iniciaP4.
