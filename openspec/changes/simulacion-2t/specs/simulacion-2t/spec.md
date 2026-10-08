## ADDED Requirements

Ampliación autorizada del 15/09/2026: los siguientes requisitos de proyecto
extienden el tramo fijo, sin modificar retrospectivamente sus pruebas/criterios.

### Requirement: Ejecutar geometría del proyecto bajo condiciones de referencia
MUST conservar el modo S2T-0D-01 y añadir proyecto actual a 3000 rpm, perfil B,
banda exterior 100 Pa y restantes condiciones fijas del escenario. MUST copiar
edición válida sin guardar, sin sustituirla por disco ni modificar el proyecto.
MUST validar conjuntamente en GUI y nuevamente en proceso: 2T monocilíndrico,
geometría completa/compatible, cárter PMI, admisión por falda efectiva, exactamente
un escape y dos transferencias completos/efectivos, conductos completos/continuos,
cilindro cerrado en todo 350–390° mediante eventos, incluido 360°. MUST bloquear
texto inválido, distinguir guardable de ejecutable y asignar enlaces por función
independientemente del orden/nombre de filas. MUST recalcular inventarios con
volúmenes propios y p/T/Y fijos, sin cambiar ecuaciones o rellenar datos ausentes.

#### Scenario: Copia válida con cambios pendientes
- **WHEN** se ejecuta un motor admitido modificado sin guardar
- **THEN** la copia alimenta el hijo y resultado, conserva dirty/archivo y no cambia aunque se edite o abra otro motor durante el cálculo.

#### Scenario: Configuración incompatible
- **WHEN** faltan datos, existe texto inválido o no se cumple el dominio
- **THEN** se muestran juntos campos/incompatibilidades y no se inicia el cálculo ni se recurre al caso fijo.

### Requirement: Resultados de proyecto trazables y compatibles
MUST conservar JSON v5 de proyectos y lectura de resultados fijos antiguos.
MUST registrar origen, identidad/ruta/dirty al ejecutar, copia, correspondencia
de lumbreras, escenario, parámetros efectivos, versión/perfil/variante y resultados.
MUST distinguir identidad del motor de S2T-0D-01, sin atribuir procedencia medida
o sintética desconocida. MUST validar coherencia de entradas/modelo/unidades/
muestras/resumen/estado al abrir sin necesitar el archivo original del proyecto.
MUST reutilizar un solo proceso, cancelación, protección de cierre, estados reales,
gráficos y reapertura. Condiciones de referencia MUST identificarse como supuestos,
no mediciones/calibración; conductos representan almacenamiento/restricciones, no ondas.

#### Scenario: Edición posterior a la ejecución
- **WHEN** cambian las entradas utilizadas o se abre otro proyecto
- **THEN** se conserva la evidencia y se indica «El resultado corresponde a una configuración anterior», sin reasignar, borrar o recalcular automáticamente.

### Requirement: Comprobación y cierre acotado del editor
MUST probar adaptación, datos inválidos/ausentes, orden, propagación de dimensiones,
eventos/inventarios, conservación, reapertura y regresiones antes de tres cálculos
completos: A geometría de referencia vía editor B/100; B solo compresión 8→8,2 vía
editor B/100; C misma modificación, consola C/100. MUST usar límites previos,
60 s/30 ciclos por cálculo y hasta 180 s total, sin otras series/bandas.
MUST comparar referencia/A y soluciones B/C convergidas con umbrales existentes,
sin atribuir tendencia de tres perfiles o validez general. MUST comprobar Windows
con captura real, revisión puntual y registro en tareas/README/hoja; commit propio
sin publicación, archivo ni entrega 6.

#### Scenario: Cierre del tramo implementado
- **WHEN** editar, comprobar, ejecutar, consultar, guardar y reabrir con procedencia quedan acreditados
- **THEN** entrega 5 se registra implementada para el alcance acotado, con aceptación manual separada y sin añadir ondas/condiciones editables como requisitos nuevos.

Actualización posterior: la orden de integración gráfica autoriza el caso fijo
S2T-0D-01 B/100 Pa mediante ejecución individual separada, sin motores del editor.
Las exclusiones de Qt y autorizaciones de push de etapas anteriores conservadas
abajo son históricas; este tramo permite Qt y commit propio, sin publicación.

### Requirement: Ejecutar y consultar el caso de referencia desde Qt
La pestaña Simulación 2T MUST ejecutar únicamente S2T-0D-01 a 3000 rpm, banda
exterior 100 Pa y perfil B mediante QProcess asíncrono, reutilizando el núcleo sin
Qt y sus presupuestos/criterios. MUST mostrar caso sintético, parámetros de solo
lectura y separación del proyecto. MUST NOT modificar JSON v5 ni usar el editor.

#### Scenario: Proyecto independiente
- **WHEN** se ejecuta o reabre el caso y después cambia el proyecto o su tipo
- **THEN** el proyecto conserva sus datos/estado de cambios y el resultado sigue identificado como caso de referencia.

### Requirement: Cancelación y estados fiables
MUST admitir un único proceso, progreso real y cancelación cooperativa Windows.
Cerrar MUST conservar protección del editor y cancelar sin esperar indefinidamente
ni dejar hijos huérfanos. MUST distinguir convergencia, cancelación, no convergencia
y error; código cero solo no acredita éxito. Nuevo cálculo MUST retirar datos previos.

#### Scenario: Cancelar cálculo activo
- **WHEN** se solicita Cancelar o se autoriza cerrar durante el cálculo
- **THEN** el proceso se detiene con estado Cancelado, con parada forzada acotada si no responde, sin éxito atribuido.

### Requirement: Visualizar y recuperar resultados del caso fijo
MUST mostrar presión absoluta/ángulo continuo con PMS/PMI, P-V en orden temporal,
trabajos C/K calculados, máximo, ciclos/tiempo, balances y parada. MUST validar
resultados guardados separados, entradas, unidades, correspondencia y valores
antes de mostrarlos. MUST identificar parciales como diagnóstico no aceptado,
sin inventar curvas, sensibilidad nueva, validación experimental o soporte general.

#### Scenario: Resultado ilegible
- **WHEN** Abrir resultado recibe estructura, unidades o archivos incompatibles
- **THEN** informa el error sin cerrar la aplicación ni sustituir el resultado válido anterior por datos incoherentes.

Actualización de autorización, 15/09/2026: la usuaria aprobó explícitamente modelo,
caso, aproximaciones y protocolo y autorizó implementación/ejecución del prototipo.
Las restricciones de la tarea documental original conservadas abajo describen
esa etapa histórica; los requisitos condicionales del prototipo pasan a estar
activos sin modificar sus criterios. La orden actual permite un commit propio
y un push normal; ante fallo de autenticación no se reintenta. Permanecen excluidos
Qt, formato de proyectos, ondas, barridos, archivo del cambio y entrega 6.

### Requirement: Definición documental y límite de autorización
Esta tarea MUST entregar un solo modelo recomendado, caso sintético y experimento
acotado en design.md, diferenciando datos, parámetros, derivados y aproximaciones.
MUST NOT implementar solver, interfaz, formato JSON, dependencias ni ejecutar
simulaciones. MUST preservar entrega 4 y evidencias previas sin repetir sus pruebas.
La entrega 5 MUST figurar En curso: definición del primer caso, no implementada.
Los requisitos de prototipo siguientes son criterios propuestos para una fase
posterior, condicionados a aprobación física y autorización explícita de código.

#### Scenario: Preparación válida
- **WHEN** OpenSpec aprueba la estructura documental
- **THEN** se registra únicamente validación de documentos; solver, evidencia numérica y resultados físicos siguen pendientes y no autorizados.

### Requirement: Un modelo abierto con límites explícitos
El diseño MUST definir balances de masa, energía y carga fresca/residual, cierre
del gas, estados/contornos, flujo reversible con área efectiva declarada, aporte
energético, calor/pérdidas, volumen variable del cárter y circuito fijo. MUST citar
fuentes primarias y diferenciar decisiones propias de afirmaciones sustentadas.
MUST explicar el papel efectivo de longitudes/diámetros y la conexión de
transferencias; no deducir almacenamiento completo de las ventanas existentes.
La propuesta 0D sin inercia/ondas MUST identificarse como reducción de capacidad
pendiente de aprobación, sin sintonía ni etiqueta 1D.

#### Scenario: Evaluación del alcance del escape
- **WHEN** se revisa el modelo antes de autorizar el núcleo
- **THEN** se conoce que solo representa volumen agregado y restricción concentrada, no propagación/reflexión ni efecto del orden de conos a igual volumen/área limitante; diferir ondas requiere aprobación expresa.

### Requirement: Caso reproducible y referencias independientes
El diseño MUST fijar un único monocilíndrico 2T atmosférico de chispa y falda,
geometría completa, régimen/condición, p absolutas/T, estados iniciales,
coeficientes y parámetros energéticos. MUST identificar valores como sintéticos,
sin motor real ni mediciones, indicar claves v5 reutilizadas y entradas adicionales
sin cambiar archivos/proyectos. MUST definir controles analíticos independientes,
resoluciones, balances, convergencia y presupuestos antes de ejecutar.

#### Scenario: Datos adicionales ausentes del editor
- **WHEN** se entrega esta definición
- **THEN** estados, contornos, Cd y energía quedan documentados en el caso, sin agregarlos a JSON ni precargar proyectos de la usuaria.

### Requirement: Observación del futuro prototipo condicionado a aprobación
Después de autorización independiente, el prototipo MUST evaluar el circuito
abierto completo; MUST informar p_C(theta), P-V, W indicado por ciclo y estados,
flujos/retornos y balances definidos en el diseño, con caso/resolución identificados.
Un cierre geométrico MUST bloquear flujo; invertir presión MUST invertir donante,
entalpía y fracción fresca. MUST NOT ocultar estados no físicos, recortarlos para
continuar ni presentar ausencia de convergencia como resultado aceptado.
El calor prescrito y la mezcla ideal MUST distinguirse de combustión/barrido
predictivos. MUST NOT inferir potencia al eje, consumo, emisiones o detonación.

#### Scenario: Cálculo elemental cerrado
- **WHEN** una prueba adiabática cerrada o de calor a volumen fijo aprueba
- **THEN** acredita solo ese balance elemental, no el ciclo 2T con intercambio de gases ni el coste del sistema completo.

### Requirement: Viabilidad futura acotada y trazable
La futura prueba MUST aplicar el protocolo de design.md con tolerancias previas,
control de estados/balances, comparación de resolución y evolución entre ciclos.
MUST medir tiempo/memoria del proceso completo, informar progreso y terminar por
cancelación, fallo, ciclos/tiempo/memoria o falta de convergencia sin reintentos
indefinidos. MUST NOT relajar umbrales después de un fallo para declarar éxito.
El objetivo temporal de la hoja MUST seguir siendo una meta hasta medirlo.

#### Scenario: Presupuesto agotado
- **WHEN** se alcanza cualquiera de los límites previamente fijados sin cumplir criterios
- **THEN** la futura ejecución termina con causa y evidencia parcial marcada no aceptada, sin afirmar viabilidad ni iniciar campañas adicionales.

### Requirement: Registro documental y parada
MUST usar proposal/design/spec/tasks del único cambio, con referencias mínimas
de estado en documentos existentes. MUST separar tareas documentales realizadas
de aprobación y prototipo no autorizados, validar OpenSpec y crear commit propio.
MUST NOT reintentar la autenticación bloqueada, cambiar configuración global,
archivar cambios o iniciar entrega 6. La entrega MUST identificar decisiones
pendientes antes del núcleo y no pedir aceptación de una implementación inexistente.

#### Scenario: Fin de esta tarea
- **WHEN** se registran documentos y commit
- **THEN** se entrega modelo/caso/viabilidad propuesta y aprobaciones pendientes, conservando la entrega 5 en definición y deteniendo el trabajo antes del solver.
