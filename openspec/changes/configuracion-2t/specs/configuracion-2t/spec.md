## ADDED Requirements

### Requirement: Editor de lumbreras incompleto y persistente
El editor MUST permitir añadir, editar y eliminar filas individuales con nombre,
función Escape/Transferencia, distancia superior u, altura h y ancho desarrollado w.
MUST explicar origen en borde superior periférico del pistón en PMS, positivo hacia
abajo, no cara del cilindro/cúpula; ancho desarrollado, no cuerda. MUST identificar
rectángulos como aproximación. Datos nuevos incompletos MUST ser guardables con
null para números ausentes; números informados MUST ser positivos finitos con
coma/punto. Entrada inválida MUST conservarse y bloquear guardado sin volverse null.

#### Scenario: Edición y protección
- **WHEN** se añade, edita o elimina una lumbrera
- **THEN** se marca pendiente; guardar/reabrir conserva las filas, eliminar no reaparece y cancelar protege los cambios.

### Requirement: Eventos y área geométrica
La aplicación MUST reutilizar x del mecanismo sin descentrado y calcular
A=w*max(0,min(h,x-u)), entre 0° PMS y 180° PMI en rango 0–360°.
MUST mostrar apertura, cierre, duración, máximo efectivo y curva para la fila
seleccionada. Cruce MUST ser acotado y verificable, no muestra redondeada.
MUST NOT exigir compresión/cárter ni multiplicar por N. Eventos dependen de S/L/u;
área depende además de h/w. Faltantes, inválidos o incompatibles MUST retirar los
resultados afectados explicando su causa. La curva MUST identificarse como área
geométrica sobre pared, no flujo, caudal, barrido ni potencia.

#### Scenario: Caso sintético independiente
- **WHEN** S=56, L=100, u=32, h=10, w=20 mm
- **THEN** apertura=90°, cierre=270°, duración=180° y área máxima=200 mm².

#### Scenario: Parcial o sin apertura
- **WHEN** la carrera no descubre toda la altura o no supera u
- **THEN** el máximo usa la altura efectivamente descubierta; si u>=S se indica No se abre, ángulos ausentes, duración cero y área cero con dimensiones válidas.

### Requirement: Cárter individual
MUST existir volumen libre del cárter con pistón en PMI opcional, cm³ positivo finito,
de cárter individual sin conductos externos, con procedencia en observaciones.
MUST NOT deducirlo, calcular presión o compresión del cárter.

#### Scenario: Cárter no informado
- **WHEN** falta volumen de cárter
- **THEN** la ficha puede guardarse y los cálculos de lumbreras no se bloquean.

### Requirement: Compatibilidad y límites de la sección
MUST añadir pestaña Configuración 2T conservando editor y gráficos Qt actuales.
En 4T MUST NOT calcular ni mostrar resultados 2T, conservando entradas al alternar.
JSON v4 MUST guardar solo entradas y referencias documentadas; MUST leer v1/v2 sin
lumbreras/volumen informados y sin escritura automática. MUST conservar guardado
seguro, sobrescritura y protección de cambios. MUST NOT añadir otras modalidades de admisión, perfiles,
puentes, válvula de escape, conductos o simulación.

#### Scenario: Alternancia y archivos antiguos
- **WHEN** se cambia a 4T y vuelve a 2T o se abre un archivo anterior
- **THEN** alternar conserva los datos; v1/v2 inicializan lista vacía y volumen null, mientras v3 conserva ambos, sin modificar bytes hasta guardar.

### Requirement: Evidencia del primer tramo
MUST registrar pruebas focalizadas, regresiones y comprobación Windows cuando sea
posible, separada de aceptación manual. MUST mantener entrega 3 sin completar si quedan
criterios obligatorios pendientes, sin archivar ni comenzar entrega 4 o simulador.

#### Scenario: Entrega parcial explícita
- **WHEN** se registra este tramo
- **THEN** tasks y README distinguen implementación, pruebas, inspección visual y aceptación manual; commit separado y push normal solo si autenticación disponible.

### Requirement: Admisión opcional por falda recta
La aplicación MUST permitir admisión sin definir o piston_port, en bloque separado
con u/h/w/f opcionales positivos finitos en mm. MUST explicar las referencias del
diseño mediante ayuda contextual o Referencias de medida desplegable, conservar
unidades visibles y mostrar “Área geométrica de admisión; no calcula caudal”.
MUST NOT ofrecer otros mecanismos ni asignar modalidad a proyectos antiguos.
Textos inválidos MUST conservarse y bloquear guardado incluso al cambiar modalidad,
sección o 2T/4T. En 4T MUST retirar resultados conservando datos.

#### Scenario: Sin definir y compatibilidad
- **WHEN** se abre v1, v2 o v3
- **THEN** se conservan sus datos, admisión queda sin informar y no se reescribe hasta guardar explícitamente como v4 con intake y su referencia documentada; no se guardan resultados.

### Requirement: Eventos y área de admisión
MUST reutilizar x con L>S/2 y exigir u>=S. Con d=u+h-f, d<=0 MUST mostrar No se
abre, ángulos ausentes y duración/área cero; d>=S MUST informar ausencia de cierre
finito alrededor de PMI y retirar eventos/áreas. Combinaciones incompatibles
positivas MUST poder guardarse para corregirlas. Para 0<d<S MUST resolver x(beta)=d
mediante cruce acotado, apertura=360-beta, cierre=beta, duración=2beta, intervalo
[apertura,360] unido a [0,cierre]. MUST calcular A=w*max(0,min(h,d-x)), máximo
w*max(0,min(h,d)), y dibujar 0–360° sin apertura ficticia en PMI. Eventos MUST
necesitar solo S/L/u/h/f; área además w. Ausencia, invalidez y rango MUST retirar
solo resultados afectados con causa, sin conservar resultados obsoletos.

#### Scenario: Caso independiente de admisión
- **WHEN** S=56, L=100, u=64, h=10, w=20 y f=42 mm
- **THEN** apertura=270°, cierre=90°, duración=180°, máximo=200 mm²; A0=A360=200 y A90=A180=A270=0, sin valores esperados generados por la función probada.

#### Scenario: Dependencias y límites
- **WHEN** falta ancho o la ventana solo abre parcialmente en PMS
- **THEN** los eventos válidos permanecen sin ancho; el máximo utiliza la altura realmente descubierta; editar dimensiones actualiza o retira cada resultado.

### Requirement: Comprobación final del tramo
MUST probar parcial, nunca abierta, fuera de dominio, incompletos e inválidos,
actualización S/L/ventana/falda, persistencia/compatibilidad, alternancia 2T/4T y
regresiones de lumbreras y archivos. MUST ejecutar una vez la suite completa
vigente después de la última corrección, realizar revisión puntual y comprobar
Windows con captura real si el escritorio está disponible, distinguiendo automatización,
inspección visual y aceptación manual. Un motor real documentado MUST NOT bloquear
el editor; casos sintéticos no acreditan predicción ni eligen motor experimental.

#### Scenario: Registro de cierre
- **WHEN** finalizan implementación y comprobaciones
- **THEN** tasks, README y resumen de hoja reflejan evidencia actual, decisión resuelta y pendientes; commit separado y publicación normal solo con autenticación disponible, sin archivar ni iniciar entrega 4.
