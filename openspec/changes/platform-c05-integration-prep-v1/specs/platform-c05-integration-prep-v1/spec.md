## ADDED Requirements
### Requirement: Continuación 4T segura
El sistema SHALL aceptar `initial_state` sólo como un
`DINO4T_STATE_CONTEXT_V1` con `complete_cycle=True`, frontera de ciclo 720°,
modelo nativo correcto y topología compatible. SHALL distinguir `continuation`
(misma configuración) de `warm_start` (configuración distinta, topología
idéntica) y SHALL rechazar topologías incompatibles. SHALL NOT declarar
reinicio exacto; el resumen SHALL registrar `exact_restart_claim=NOT_SUPPORTED`.

#### Scenario: Estado de medio ciclo
- **WHEN** se intenta reutilizar un state de fase distinta de la frontera
- **THEN** la API devuelve `OPTION_INVALID` antes de ejecutar el solver.

#### Scenario: Configuración distinta
- **WHEN** se reutiliza un estado de ciclo completo con otra configuración y
  topología idéntica
- **THEN** el resumen lo etiqueta `warm_start` y no afirma equivalencia exacta.

### Requirement: Ciclo de vida de workers Qt
El sistema SHALL reservar un único worker 4T por contexto, SHALL ignorar
señales de corridas anteriores y SHALL cancelar, esperar y liberar el proceso o
tarea al cerrar. SHALL NOT destruir widgets con callbacks pendientes ni dejar
`MotorSimWorker.exe` huérfano.

#### Scenario: Cierre durante la ejecución
- **WHEN** se cierra la ventana mientras un worker 4T sigue activo
- **THEN** se solicita cancelación, se espera la finalización y el cierre no
  deja hilos ni procesos activos.

### Requirement: Aceptación terminal
El sistema SHALL escribir un receipt PASS sólo después de que el proceso haya
terminado, el exit code sea 0 y no existan workers huérfanos ni hilos activos.
Error, timeout y cierre incompleto SHALL conservarse como evidencia de fallo o
incompleta, sin publicar PASS.

#### Scenario: Proceso sin cierre
- **WHEN** el proceso no termina dentro del timeout
- **THEN** se termina, se registra `TIMEOUT` y no existe `acceptance.json` PASS.

### Requirement: Curva 4T 0D vinculada y persistente
El sistema SHALL vincular una curva al proyecto mediante identidad de proyecto,
identidad de serie, hash, estado, modelo y RPM. SHALL copiar la serie junto al
proyecto guardado y SHALL restaurarla al reabrir. SHALL distinguir serie
completa, parcial, obsoleta, en ejecución, no disponible y corrupta. SHALL NOT
presentar una serie parcial, obsoleta o corrupta como curva completa. SHALL
mantener el proyecto 4T 0D separado del proyecto 4T nativo.

#### Scenario: Proyecto editado después del cálculo
- **WHEN** se modifica la geometría después de calcular una curva
- **THEN** la referencia queda `STALE_PROJECT` y no se muestra como vigente.

#### Scenario: Reapertura
- **WHEN** se guarda y reabre un proyecto con una curva fresca
- **THEN** la serie se restaura desde `curves/<series_id>/series.json` y los
  puntos no convergidos conservan su estado sin graficarse como convergidos.

### Requirement: Preparación de integración C05
El sistema SHALL documentar la secuencia de integración entre `main`, la rama
A/B, la auditoría y las correcciones C01–C04, SHALL identificar
incompatibilidades residuales y SHALL establecer criterios verificables. SHALL
NOT ejecutar merge, push ni build como parte de esta preparación.

#### Scenario: Secuencia preservada
- **WHEN** se verifica la ascendencia de la rama de preparación
- **THEN** `main` es ancestro y la integración propuesta es fast-forward con
  historias preservadas.
