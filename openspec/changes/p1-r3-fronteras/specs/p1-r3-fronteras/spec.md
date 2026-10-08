## ADDED Requirements
### Requirement: Revisión conceptual previa
R3 SHALL identificar las BC existentes y derivar sus relaciones características
antes de modificar código. SHALL separar presión acústica y cierre de reservorio.
#### Scenario: Ramas incompatibles
- **WHEN** ninguna rama satisface el signo aun en alta precisión
- **THEN** no impone velocidadcero ni epsilon y documenta el cambio contractual.
### Requirement: Pressure release explícita
T05 SHALL usar ideal_open_pressure_release con presiónp0, velocidad característica
resultante y continuación isentrópica/trazador definida, sin conmutación de ramas.
#### Scenario: Perturbación pequeña
- **WHEN** la velocidad cambia de signo
- **THEN** permanece la misma definición física y el estado debe ser admisible.
### Requirement: Verificación y continuación
T05 SHALL conservar sus parámetros y umbrales; NR01 SHALL medir reflexión aparte
sin inventar un umbral. P2A SHALL reanudarse solo después de gates y revisión.
#### Scenario: Fallo de método
- **WHEN** T08 o T12 exige modificar source/positividad para aprobar
- **THEN** registra SCIENTIFIC_CHANGE_REQUIRED sin inventar well-balancing/limiter.
