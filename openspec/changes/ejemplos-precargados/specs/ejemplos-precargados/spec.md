## ADDED Requirements
### Requirement: Archivos físicos de demostración
La continuación SHALL versionar cuatro JSON v6 en examples/projects con nombres
EJEMPLO_SINTETICO_2T_REFERENCIA.json, EJEMPLO_SINTETICO_2T_COMPRESION_8_2.json,
EJEMPLO_SINTETICO_4T_REFERENCIA.json y EJEMPLO_SINTETICO_4T_COMPRESION_8_2.json.
SHALL derivarlos de S2T-0D-01 y S4T-0D-01 mediante el modelo real, con nombre
“EJEMPLO SINTÉTICO 2T — REFERENCIA” o “EJEMPLO SINTÉTICO 4T — REFERENCIA” y
observaciones explícitas NO MEDIDO/sin validación experimental. Cada variante
SHALL diferir únicamente en compression_ratio, incluso en sus metadatos.
El generador SHALL validar todos los proyectos y su ejecutabilidad antes de
sobrescribir únicamente esos cuatro destinos, sin solver. La próxima candidata
SHALL incluirlos bajo Ejemplos, idénticos al repositorio y sin dependencia runtime
del repositorio. El menú previo mantiene su identificación y carga protegida.
#### Scenario: Apertura y copia de un archivo físico
- **WHEN** se abre cualquiera desde Archivo → Abrir y se guarda una copia
- **THEN** conserva todos los campos y no modifica el original.
### Requirement: Ejemplos canónicos identificados
El sistema SHALL ofrecer 2T referencia, 2T compresión8.2, 4T referencia y 4T
compresión8.2, derivados de las referencias canónicas. SHALL identificar nombre
y observaciones con “EJEMPLO SINTÉTICO — NO MEDIDO”. La única diferencia física
de cada variante SHALL ser compresión8.0 a8.2, sin modificar referencias.
#### Scenario: Seleccionar variante
- **WHEN** se carga una variante8.2
- **THEN** conserva todos los otros datos de su referencia y no incluye resultados.
### Requirement: Carga protegida y editable
Archivo → Cargar ejemplo SHALL reutilizar Guardar/Descartar/Cancelar ante cambios
pendientes. La carga confirmada SHALL crear proyecto editable dirty=True, path=None;
Guardar SHALL solicitar destino nuevo. SHALL preparar simulación del proyecto real
y navegación del ciclo cargado, sin sobrescribir archivos incluidos.
#### Scenario: Cancelar transición
- **WHEN** se cancela la confirmación o el guardado previo
- **THEN** conserva proyecto, ruta, cambios y selección actuales.
### Requirement: Distribución autónoma
Los ejemplos SHALL generarse determinísticamente sin red, repositorio ni cwd.
rc4 SHALL conservar rc3 y acreditar pruebas, revisión y recorrido Windows,
sin campañas físicas ni aceptación manual atribuida.
#### Scenario: EXE extraído
- **WHEN** se carga un ejemplo desde la aplicación distribuida
- **THEN** permite editar/guardar y consultar resultados existentes independientemente del repositorio.
