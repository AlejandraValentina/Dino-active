## ADDED Requirements
### Requirement: Identidad y soporte del producto
El sistema SHALL exponer versión, build/commit, esquemas de proyecto,
estado científico, licencias de terceros y contacto de soporte desde la
aplicación. SHALL distinguir TRIAL/engineering de validación experimental o
predictiva.

#### Scenario: About en 2T y 4T
- **WHEN** el usuario abre “Acerca de Dino”
- **THEN** ve la identidad del candidato, los límites científicos y las
  licencias, sin depender de documentación externa.

### Requirement: Diagnóstico exportable
El sistema SHALL exportar un ZIP de diagnóstico con identidad de build,
entorno, configuración no sensible, logs y proyecto opcional. SHALL NOT incluir
credenciales ni enviar telemetría automáticamente.

#### Scenario: Soporte sin secretos
- **WHEN** el usuario exporta un diagnóstico
- **THEN** el ZIP se crea fuera del repositorio y no modifica el proyecto ni
  incluye secretos.

### Requirement: Recuperación de proyectos
El sistema SHALL autoguardar borradores de proyectos sucios fuera del
repositorio y SHALL ofrecer recuperarlos al iniciar. SHALL NOT sobrescribir el
archivo original sin confirmación.

#### Scenario: Cierre inesperado
- **WHEN** existe un borrador de recuperación y el usuario inicia la aplicación
- **THEN** puede abrirlo como copia, guardarlo o descartarlo.

### Requirement: Recientes por familia
El sistema SHALL mantener una lista acotada de proyectos recientes separada por
familia 2T/4T y SHALL podar rutas inexistentes.

#### Scenario: Proyecto movido
- **WHEN** un proyecto reciente ya no existe
- **THEN** se elimina de la lista sin afectar otros proyectos.

### Requirement: Cierre seguro
El sistema SHALL cancelar y esperar tareas/procesos activos antes de cerrar y
SHALL NOT dejar workers huérfanos ni destruir widgets con callbacks pendientes.

#### Scenario: Cierre durante ejecución
- **WHEN** el usuario cierra con una corrida activa
- **THEN** se cancela, se espera el cierre y no quedan procesos huérfanos.

### Requirement: Límites científicos
El sistema SHALL declarar calibración, validación experimental y capacidad
predictiva como estados separados. SHALL NOT presentar CP0–CP2 como validación
ni usar supuestos sintéticos para cerrar CP3.
