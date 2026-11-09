## ADDED Requirements
### Requirement: Apply sin cambios conserva identidad
El editor 4T SHALL conservar exactamente los valores originales de celdas no
editadas y SHALL re-tipar sólo las celdas cuyo texto difiere de la
representación cargada. SHALL NOT llamar `replace_engine` cuando no hay cambios.

#### Scenario: No-op
- **WHEN** se pulsa Apply sin editar ninguna celda
- **THEN** el valor exacto (incluido un float de 17 dígitos) no cambia y no se
  marca el proyecto como modificado por esa acción.

### Requirement: Refresco y ejes científicos
El refresco de resultados SHALL limpiar métricas, traza y presión stale antes de
releer referencias. Las curvas de presión SHALL usar ángulo de cigüeñal con
unidad explícita, no RPM.

#### Scenario: Fuente no disponible
- **WHEN** una referencia deja de ser legible
- **THEN** no quedan métricas ni curvas de la selección anterior.

### Requirement: Estado de continuación seguro
El sistema SHALL aceptar `initial_state` sólo como un
`DINO4T_STATE_CONTEXT_V1` con `complete_cycle=True`; SHALL rechazar state crudo
o de medio ciclo con `OPTION_INVALID` antes de ejecutar el solver. Los estudios
SHALL propagar el contexto, no el state crudo.

#### Scenario: State de medio ciclo
- **WHEN** se intenta reutilizar un state marcado incompleto
- **THEN** la API devuelve un error estructurado y no llama al solver.

### Requirement: Aceptación terminal y legacy explícito
El driver Windows SHALL escribir el receipt PASS sólo después de que el proceso
haya terminado con exit code 0. Los históricos legacy SHALL poder exportarse
con `integrity_classification=LEGACY_UNVERIFIED` y su calificación de fuente,
sin promocionarlos a V2.

#### Scenario: Cierre del proceso
- **WHEN** el proceso empaquetado no termina correctamente
- **THEN** no existe un receipt PASS terminal.

### Requirement: No regresión
El sistema SHALL conservar P0–P9, ecuaciones, tolerancias, manifiestos y
evidencia histórica. La verificación SHALL incluir C01/C03, API/A-B/Desktop,
Stage2 y la receta protegida; no se declara release ni validación científica.

#### Scenario: Cierre C02/C04
- **WHEN** se ejecutan los tests y la receta protegida
- **THEN** pasan y los históricos legacy siguen calificados.
