# DINO_DESKTOP_V3_1_VISUAL_PARITY

## ADDED Requirements

### Requirement: Edición de escape por tramo
El editor MUST mostrar perfil dimensionado y tabla editable por tramo con largo y diámetro de salida. El diámetro de entrada MUST derivarse de la estación compartida anterior. El usuario MUST ver diferencias respecto de baseline sin recorrer una tabla separada para la edición común.

#### Scenario: Editar un tramo desde su fila
- **WHEN** el usuario cambia largo o diámetro de salida en la fila de un tramo
- **THEN** el perfil, la estación compartida siguiente, semiángulo, volumen y diferencias se actualizan y la configuración existente valida sin ejecutar el solver

### Requirement: Cilindro y distribución integrados
Una vista MUST presentar esquema de cilindro, geometría editable, magnitudes derivadas, dimensiones y eventos de lumbreras y gráfica área–ángulo usando las APIs existentes. La admisión que cruza PMS MUST mantener sus eventos derivados desde transiciones reales del área.

#### Scenario: Revisar geometría y distribución juntas
- **WHEN** el usuario abre Cilindro y distribución
- **THEN** ve esquema, parámetros, dimensiones de lumbreras, apertura, cierre, duración y área efectiva frente al ángulo
- **AND** el evento de admisión se deriva de transiciones de área al cruzar PMS

### Requirement: Preparación desde barra de ejecución
La preparación MUST abrirse desde la barra de ejecución. RPM, horizonte y presupuesto MUST tener una sola fuente de estado. Progreso y cancelación MUST seguir visibles en la barra; no habrá una segunda página de ejecución con controles duplicados.

#### Scenario: Preparar desde la barra
- **WHEN** el usuario abre Preparar desde la barra inferior
- **THEN** encuentra un panel de preparación y corridas existentes
- **AND** los valores resumidos en la barra corresponden a los mismos controles del panel

### Requirement: Análisis prioriza señales
El análisis MUST dar espacio primario a presión y mapas de ondas disponibles, conservar clasificaciones y explicar métricas indefinidas. No MUST fabricar potencia, torque, datos interpolados ni resultados faltantes.

#### Scenario: Analizar una corrida no periódica
- **WHEN** se carga una corrida EXPLORATORY con presión disponible y sin periodicidad aceptada
- **THEN** las señales disponibles se presentan antes de tablas secundarias
- **AND** potencia, torque y BMEP permanecen sin valor con su razón

### Requirement: Comparación de ingeniería
La comparación MUST mostrar deltas de geometría y métricas disponibles con unidades y estado. Debe preferir corridas comparables a RPM e identidad física iguales cuando existan y advertir diferencias cuando no.

#### Scenario: Comparar corridas vinculadas
- **WHEN** existen corridas base y variante a la misma RPM
- **THEN** el panel muestra diferencias geométricas y deltas de métricas definidas con unidades
- **AND** advierte condiciones o identidad física no coincidentes o no reportadas
- **AND** omite pares que requieran interpolación

### Requirement: Vista compacta
En ventanas compactas, navegación y edición MUST conservar acceso a controles principales sin depender de una columna vertical recortada. Los inspectores secundarios pueden plegarse.

#### Scenario: Navegación compacta
- **WHEN** la ventana tiene 1120 píxeles lógicos de ancho o menos
- **THEN** la navegación de componentes cambia a pestañas horizontales y el editor conserva acceso a perfil y tabla

### Requirement: Seguridad y provenance
La aplicación MUST rechazar fail-closed cualquier artifact root dentro del repositorio al crear nuevos resultados. El ZIP TRIAL MUST contener los cambios V3.1 y conservar los hashes del ejecutable MotorSim.exe.

#### Scenario: Raíz insegura
- **WHEN** la raíz de artifacts está dentro de cualquier repositorio Git
- **THEN** la aplicación deshabilita nuevas ejecuciones y reanudaciones que escriban en esa raíz
- **AND** la comprobación de inicio la rechaza antes de crear un directorio de corrida

### Requirement: Evidencia visual y alcance científico
La aceptación MUST incluir comparación antes/después M1–M6 en el EXE real. No se ejecutarán simulaciones ni campañas. Los gate y artifacts científicos históricos permanecerán inalterados.

#### Scenario: Aceptación empaquetada
- **WHEN** se evalúa el cambio V3.1
- **THEN** se registran capturas antes/después de M1–M6 generadas desde el ejecutable real
- **AND** el paquete contiene los cambios del código fuente verificado
- **AND** no se ha iniciado una simulación o campaña
