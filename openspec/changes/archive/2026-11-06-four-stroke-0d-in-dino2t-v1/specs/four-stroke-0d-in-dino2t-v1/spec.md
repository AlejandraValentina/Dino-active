## ADDED Requirements
### Requirement: Documento 4T de referencia independiente
El sistema SHALL persistir proyectos 4T con el schema
`MOTORSIM_4T_REFERENCE_PROJECT_V1`, incluyendo solo geometría, válvulas,
conductos 4T, régimen opcional y procedencia. SHALL rechazar schema o versión
desconocidos y SHALL conservar proyectos incompletos para corrección sin
presentarlos como calculables. SHALL NOT escribir campos 2T (`ports`, `intake`,
`ducts` 2T, `crankcase_volume_bdc_cm3`, `two_stroke_reference`).

#### Scenario: Guardar y reabrir un proyecto 4T
- **WHEN** se guarda un proyecto 4T válido o incompleto
- **THEN** se reabre con los mismos valores, sin campos 2T y sin defaults
  inventados.

#### Scenario: Archivo ajeno o versión inválida
- **WHEN** se intenta abrir un JSON con otro schema o versión
- **THEN** se rechaza con un error legible y no se modifica el proyecto activo.

### Requirement: Modo 4T separado en Dino
El sistema SHALL ofrecer en `DinoDesktopWindow` creación, apertura y guardado de
proyectos 4T, con un workspace propio de Geometría, Válvulas, Conductos,
Simulación y Resultados. SHALL conservar intactos el proyecto V3, el workspace
2T y `engine_configuration`. SHALL NOT comparar 2T con 4T ni compartir variantes
o estudios de diseño en B1.1.

#### Scenario: Cambio de modo
- **WHEN** se abre o crea un proyecto 4T
- **THEN** Dino muestra el workspace 4T y su etiqueta de referencia; al abrir un
  proyecto 2T vuelve al workspace 2T sin alterar sus datos.

### Requirement: Ejecución 4T con el worker existente
El sistema SHALL ejecutar el 4T 0D mediante `reference_run`/`MotorSimWorker.exe`
con `--cycle 4T`, usando `reference_results.project_inputs` y un RPM entero
2500–3500. SHALL validar `four_stroke.execution_errors` antes de ejecutar,
permitir cancelación y no bloquear la interfaz. SHALL NOT introducir solver,
física, tolerancias ni ejecutable nuevo.

#### Scenario: Proyecto incompleto
- **WHEN** faltan geometría, válvulas o conductos para calcular
- **THEN** la ejecución se rechaza con el motivo concreto y el proyecto sigue
  guardable.

#### Scenario: Cancelación o error del worker
- **WHEN** el usuario cancela o el worker termina con error
- **THEN** se conserva el estado real y no se presenta un resultado parcial como
  convergido.

### Requirement: Resultados 4T estrictos y etiquetados
El sistema SHALL leer el manifiesto 4T v4 con `reference_results.load_result`,
mostrar estado, convergencia, `W_C_J`, `p_max_Pa`, tiempos, memoria y curvas
P-V/p-V, y SHALL mostrar `SYNTHETIC_REFERENCE_0D · NOT_VALIDATED`. SHALL NOT
mostrar `W_K` para 4T ni atribuir validación experimental o predictiva.

#### Scenario: Resultado convergido
- **WHEN** el manifiesto v4 es válido y el estado es `converged`
- **THEN** la vista muestra el resumen y las curvas de las muestras del ciclo.

#### Scenario: Manifiesto alterado
- **WHEN** falta un archivo, cambia un hash o el modelo no corresponde a v4
- **THEN** la vista rechaza el resultado con un error legible.

### Requirement: Verificación y no regresión
El sistema SHALL incluir pruebas de round-trip 4T, validación, adaptador de
ejecución, UI 4T y regresión 2T/V3. La suite completa SHALL pasar sin cambiar
los contratos, hashes ni resultados históricos.

#### Scenario: Cierre del change
- **WHEN** se ejecuta la suite completa
- **THEN** 2T, V3 y los contratos 4T existentes siguen pasando y el modo 4T
  queda cubierto por pruebas propias.
