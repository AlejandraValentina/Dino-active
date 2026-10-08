## ADDED Requirements

### Requirement: Cinemática directa de un cilindro
La aplicación MUST calcular posición desde PMS del mecanismo sin descentrado,
con r=S/2 y L>r, y volumen de cámara Vc=Vd/(C-1) y volumen instantáneo
V=Vc+π D² x/4000, con longitudes mm y volúmenes cm³. MUST declarar PMS=0°,
PMI=180° y repetición mecánica cada 360°. MUST mostrar 0–360° para 2T y
0–720° para 4T distinguiendo segunda revolución, sin asignar eventos físicos.
MUST NOT multiplicar volúmenes instantáneos por N ni usar un solver temporal.

#### Scenario: Puntos muertos y periodicidad
- **WHEN** se informa geometría compatible
- **THEN** x(PMS)=0, x(PMI)=S, V(PMS)=Vc, V(PMI)=Vc+Vd, con repetición a 360°.

### Requirement: Dependencias y datos incompletos
Cada resultado MUST validar únicamente sus entradas necesarias. Posición y esquema
requieren S/L compatibles; cámara y extremos D/S/C; curva de volumen D/S/L/C.
Ausencias, errores, incompatibilidad L<=S/2 o límites numéricos MUST retirar el
resultado afectado anterior y explicar su causa. MUST conservar edición y
posibilidad de guardar la ficha bajo sus reglas existentes, sin corregir datos.

#### Scenario: Compresión ausente
- **WHEN** S/L son compatibles pero falta C
- **THEN** esquema y posición permanecen disponibles; volumen se retira con explicación.

#### Scenario: Biela incompatible
- **WHEN** L deja de superar S/2
- **THEN** esquema y curvas cinemáticas se retiran, con explicación; la ficha positiva sigue siendo guardable.

### Requirement: Visualización integrada sin nuevas entradas persistentes
La aplicación MUST conservar el editor y añadir pestaña Geometría con esquema 2D,
curvas de posición y volumen con ángulos/unidades, puntos muertos y valores
derivados. Esquema y curvas MUST usar los mismos cálculos y actualizarse al editar,
abrir o crear proyecto. MUST identificar un cilindro y límite de esquema no CAD.
MUST conservar teclado, escalado, archivos v1/v2, guardado seguro y protecciones.
MUST NOT guardar series ni cambiar versión JSON; MUST NOT añadir 3D, fuerzas,
velocidades, aceleraciones, presión, temperatura, lumbreras, válvulas o simulación.

#### Scenario: Edición y cambio de tipo
- **WHEN** se editan datos o cambia 2T/4T
- **THEN** las curvas y el esquema corresponden a los datos vigentes y al rango angular actual.

### Requirement: Evidencia de entrega
La entrega MUST probar puntos muertos, periodicidad, extremos de volumen,
cilindrada, dependencias, actualización y regresiones de archivos; MUST contrastar
un caso con cálculo independiente. MUST registrar captura real Windows y distinguir
pruebas automáticas, inspección visual y recorrido manual. MUST conservar pendientes
históricos, no archivar cambios ni comenzar entrega 3.

#### Scenario: Registro verificable
- **WHEN** se entrega el cambio
- **THEN** tasks registra evidencia real, README comandos y límites, y la hoja resume estado sin duplicar tareas.
