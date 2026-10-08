## ADDED Requirements

### Requirement: Ficha editable e incompleta
El editor MUST conservar nombre válido y tipo 2T/4T, y añadir fabricante, modelo
y observaciones como textos opcionales. MUST admitir sin informar (null) número
de cilindros, diámetro, carrera, longitud de biela entre centros y compresión.
Informados, cilindros MUST ser entero positivo; las tres longitudes en mm MUST
ser positivas y finitas; compresión MUST ser finita y mayor que 1, presentada x:1.
MUST aceptar coma o punto decimal sin separadores de miles. MUST distinguir vacío
de entrada inválida y no convertir errores en null. MUST conservar precisión de
entrada al guardar y todos los campos al cambiar 2T/4T.

#### Scenario: Registro parcial
- **WHEN** se guarda una ficha con nombre y tipo válidos y números nuevos vacíos
- **THEN** se guarda correctamente con esos números null y textos opcionales vacíos.

#### Scenario: Validación sin pérdida de edición
- **WHEN** se informa un número inválido, no finito, no positivo o compresión <= 1
- **THEN** se indica el error y se impide guardar, conservando el texto editado.

#### Scenario: Cambio de tipo
- **WHEN** se alterna entre 2T y 4T
- **THEN** los datos comunes permanecen intactos y se indica el cambio pendiente.

### Requirement: Cilindrada geométrica vigente
La ficha MUST mostrar solo lectura cilindrada por cilindro = pi * D**2 * S / 4000
y total = N * cilindrada por cilindro, en cm³ con dos decimales. La ficha
MUST declarar la hipótesis de geometría común a todos los cilindros; esto no
representa simulación multicilíndrica. Cada resultado
MUST calcularse solo con sus entradas disponibles y válidas; de otro modo MUST
mostrar «—» inmediatamente. Biela y compresión MUST NOT generar simulación,
animación o rendimiento.

#### Scenario: Edición y dependencias
- **WHEN** diámetro o carrera dejan de ser válidos
- **THEN** ambos resultados pasan a «—»; si solo N es inválido o vacío, únicamente
  el total pasa a «—», conservando la cilindrada por cilindro válida.

### Requirement: JSON versión 2 compatible con versión 1
El guardado MUST usar JSON UTF-8 versión 2 documentado en design.md: textos como
cadenas, números informados como números y ausentes como null. MUST validar
estructura, versión (entero, no booleano), tipos y datos antes de activar un archivo.
MUST leer versión 1 conservando nombre y tipo y dejando los campos nuevos sin
informar. Abrir un archivo MUST NOT reescribirlo; conversión solo al guardar.
Todos los campos MUST participar en el estado pendiente y recuperarse al reabrir.
MUST conservar Nuevo, Abrir, Guardar, Guardar como, Salir, confirmación de
sobrescritura, escritura segura y Guardar/Descartar/Cancelar antes de perder cambios.

#### Scenario: Apertura de archivo anterior
- **WHEN** se abre un archivo válido versión 1
- **THEN** sus bytes no cambian; se recuperan name/cycle y se inicializa la ficha
  vacía; un guardado explícito posterior escribe versión 2.

#### Scenario: Cancelación o error
- **WHEN** se cancela una operación o falla lectura, validación o escritura
- **THEN** se conserva el trabajo y la ruta previa; un fallo de escritura conserva
  el archivo anterior y no marca el proyecto como guardado.

### Requirement: Editor Windows verificable
La pantalla MUST conservar título nativo, menú Archivo y barra compacta; MUST
tener un encabezado «Motor» y grupos Datos generales y Geometría adaptables al
ancho, selector compacto 2T/4T, unidades junto a campos, foco y navegación de teclado.
MUST usar fondo oscuro liso y una sola barra inferior para ruta, estado y aviso
de simulación no disponible, sin laterales, cuadrícula, HTML ni botones falsos.
La entrega MUST registrar pruebas, versiones, comandos y captura real Windows con
datos de prueba identificados, distinguiendo inspección visual de automatización.
MUST mantener pendientes históricos sin inventar evidencia y MUST NOT agregar
simulación, lumbreras, válvulas, conductos, combustión, potencia, par ni gráficas.

#### Scenario: Ventana estrecha y escalado
- **WHEN** se reduce el ancho o se utiliza escalado Windows
- **THEN** los controles siguen utilizables mediante distribución adaptable y
  desplazamiento, sin ocultar la barra inferior ni perder navegación de teclado.
