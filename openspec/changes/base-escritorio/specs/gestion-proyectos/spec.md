## Purpose

Permitir crear, editar, guardar y recuperar la identificación de un proyecto
local de motor desde una aplicación de escritorio, protegiendo sus datos y sin
presentar cálculos ni una simulación física que todavía no existe.

## ADDED Requirements

### Requirement: Ventana y proyecto activo

La aplicación MUST mostrar una única ventana principal identificada como
MotorSim, con textos en español, un proyecto activo y las acciones Nuevo,
Abrir, Guardar, Guardar como y Salir. MUST indicar el archivo activo o su ausencia,
los cambios pendientes y «Versión básica: simulación no disponible».

#### Scenario: Inicio y nuevo proyecto
- **WHEN** se inicia la aplicación o se confirma Nuevo
- **THEN** se presenta un proyecto sin archivo asociado, con nombre «Sin título»
  y tipo 2T, ambos editables; no se heredan datos del proyecto anterior.

#### Scenario: Edición visible
- **WHEN** el usuario modifica el nombre o el tipo del proyecto
- **THEN** la ventana indica que existen cambios pendientes y permite seguir editando.

### Requirement: Datos y validación

El proyecto MUST tener un nombre y un tipo de motor. Para guardar, el nombre
MUST ser texto no vacío ni compuesto solo por espacios y el tipo MUST ser 2T o 4T.
El selector MUST ofrecer únicamente esas dos opciones. No se añaden parámetros físicos.

#### Scenario: Datos válidos
- **WHEN** hay nombre válido y tipo admitido
- **THEN** los datos son admisibles para guardar, incluidos nombres con acentos.

#### Scenario: Datos incompletos o inválidos
- **WHEN** el nombre está vacío, tiene solo espacios o el tipo no está admitido
- **THEN** no se guarda el proyecto como válido y se informa el problema sin
  perder la edición actual.

### Requirement: Formato local de proyecto

Cada archivo MUST ser JSON UTF-8 con `format_version`, `name` y `cycle`.
`format_version` MUST ser el entero 1, no un booleano; `name` y `cycle` MUST ser
cadenas que cumplan la validación del proyecto. El archivo MUST NOT contener
campos reservados para cálculos futuros. No se requiere un sistema de migraciones.

```json
{
  "format_version": 1,
  "name": "Motor de ejemplo",
  "cycle": "2T"
}
```

#### Scenario: Guardar y recuperar ambos tipos
- **WHEN** se guarda, cierra y vuelve a abrir un proyecto válido 2T o 4T
- **THEN** se recuperan el nombre y el tipo sin cambios, incluidos los acentos.

### Requirement: Apertura sin pérdida de trabajo

Abrir MUST validar formato, versión y datos antes de sustituir el proyecto activo.
Un archivo ilegible, JSON malformado, raíz distinta de objeto, campo obligatorio
ausente, tipo incorrecto o versión no admitida MUST producir un error comprensible
sin cerrar la aplicación ni perder el proyecto actual.

#### Scenario: Archivo rechazado
- **WHEN** se intenta abrir un archivo inválido o ilegible
- **THEN** se conserva el proyecto activo y su edición; el error no se presenta
  como una apertura exitosa.

#### Scenario: Diálogo de apertura cancelado
- **WHEN** se cancela la elección de un archivo
- **THEN** el proyecto, su ruta y sus cambios pendientes permanecen intactos.

### Requirement: Guardado y Guardar como seguros

Guardar MUST solicitar un destino cuando aún no existe archivo asociado.
Guardar como MUST permitir elegir otro destino sin modificar el archivo original
y confirmar antes de sobrescribir un archivo existente. El nombre del proyecto y
el nombre del archivo no tienen que coincidir. Una escritura fallida MUST dejar
intacto un archivo válido anterior y no marcar el proyecto como guardado.

#### Scenario: Guardar como completado
- **WHEN** se guarda una copia en otra ruta nueva
- **THEN** esa copia contiene los datos actuales, pasa a ser el archivo activo,
  el original permanece intacto y no quedan cambios pendientes.

#### Scenario: Guardado cancelado o fallido
- **WHEN** se cancela el destino, se rechaza sobrescribir o falla la escritura
- **THEN** se conserva la edición y la ruta activa previa, no se pierde el
  archivo anterior y un fallo de escritura se informa sin cerrar la aplicación.

### Requirement: Protección de cambios pendientes

Nuevo, Abrir, Salir y cerrar la ventana MUST ofrecer Guardar, Descartar o Cancelar
cuando hay cambios pendientes. La operación solicitada MUST continuar solo si
se confirma Descartar o si Guardar termina correctamente. Descartar al abrir
MUST NOT vaciar el proyecto antes de disponer de un archivo nuevo válido.

#### Scenario: Cancelar la operación
- **WHEN** se elige Cancelar antes de Nuevo, Abrir, Salir o cerrar la ventana
- **THEN** no se realiza la operación y se conserva toda la edición.

#### Scenario: Guardar antes de continuar
- **WHEN** se elige Guardar y el guardado se completa
- **THEN** se continúa con la operación solicitada; si el guardado falla o se
  cancela, no se descarta el proyecto ni se cierra la ventana.

#### Scenario: Descartar y continuar
- **WHEN** se elige Descartar y la operación solicitada puede completarse
- **THEN** se permite Nuevo, la apertura válida o el cierre sin guardar cambios.

### Requirement: Base local sin cálculos ni simulación

La aplicación MUST funcionar con archivos locales sin cuenta, servidor ni
conexión a Internet durante su uso. MUST NOT incluir parámetros físicos,
cálculos geométricos, resultados ficticios, curvas o botones que aparenten
simular. Elegir 2T o 4T solo MUST identificar el proyecto, no ejecutar modelos.

#### Scenario: Uso sin simulador
- **WHEN** se crean y editan proyectos de cualquier tipo admitido
- **THEN** se puede completar el recorrido de archivos sin Internet y la
  interfaz no presenta ningún cálculo o simulación como disponible.

### Requirement: Entrega verificable

La entrega MUST incluir instrucciones reales para instalar en un entorno Python
limpio, iniciar y probar la aplicación; MUST registrar las versiones comprobadas.
MUST incluir pruebas focalizadas de datos, validación y persistencia, y una
comprobación del recorrido de interfaz en Windows. Lo no ejecutado MUST quedar
identificado como pendiente, no como aprobado. No se exige instalador ni una
cantidad de tests o porcentaje de cobertura arbitrarios.

#### Scenario: Comprobación automatizada y manual
- **WHEN** se evalúa la entrega
- **THEN** se registran los comandos y resultados reales de las pruebas y del
  recorrido de interfaz; una ejecución sin pantalla no se declara prueba de Windows.
