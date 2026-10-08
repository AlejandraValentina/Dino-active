## ADDED Requirements

### Requirement: Recorridos editables y datos incompletos
La pestaña Conductos MUST ofrecer Admisión y Escape independientes, inicialmente
vacíos, mostrando solo el recorrido seleccionado. MUST permitir añadir, editar,
eliminar y mover arriba/abajo filas con nombre opcional y L/D1/D2 interiores en mm.
Números informados MUST ser positivos finitos, con coma/punto; vacío MUST ser null.
Texto inválido MUST permanecer y bloquear guardado, incluso al cambiar fila,
recorrido o 2T/4T. Tipo MUST derivarse de D1/D2, sin campo contradictorio.
MUST conservar el editor existente, teclado, foco y escalado 150 %.

#### Scenario: Edición y selección
- **WHEN** se añade, edita, elimina o mueve un tramo
- **THEN** se marca pendiente y se conserva el orden; seleccionar fila o Admisión/Escape no marca cambios.

### Requirement: Resultados independientes y uniones
MUST calcular A1=pi*D1²/4 y A2=pi*D2²/4 mm² y V=pi*L*(D1²+D1*D2+D2²)/12000 cm³.
MUST mostrar suma de longitudes y suma de volúmenes, cada resultado con sus propias
dependencias. Faltantes/errores MUST retirar resultados afectados con causa, sin
sumas parciales aparentando totales. Lista vacía MUST indicar Sin tramos.
D2 anterior distinto de D1 siguiente MUST identificar unión discontinua fuera del
modelo continuo; MUST conservar valores sin ajustarlos ni dibujar adaptadores.
Discontinuidad MUST NOT impedir volumen de cada pieza ni suma de volúmenes.

#### Scenario: Contraste independiente
- **WHEN** un tramo L100/D1=20/D2=20 precede a L100/D1=20/D2=40 mm
- **THEN** volúmenes son 10*pi y (70/3)*pi cm³, unión continua20 mm, longitud total200 mm y volumen total(100/3)*pi cm³, con esperados independientes del cálculo probado.

#### Scenario: Datos incompletos y discontinuidad
- **WHEN** falta un diámetro o una unión no coincide
- **THEN** la longitud completa sigue disponible; un diámetro ausente retira volumen total, y una discontinuidad conserva volúmenes calculables con aviso de incompatibilidad.

### Requirement: Perfil geométrico real y alcance 2T
MUST mostrar perfil longitudinal de posiciones axiales acumuladas y contornos ±D/2,
con tramo seleccionado, uniones, unidades y sentido visibles: admisión exterior hacia
ventana al cárter, escape cilindro hacia exterior. MUST indicar cualquier exageración
de ejes y carácter idealizado, no CAD. Faltantes/errores MUST NOT dibujarse como datos
conocidos ni mantener perfiles anteriores. En 4T MUST ocultar resultados/editor 2T
sin borrar datos. MUST NOT inferir diámetros de lumbreras, sumar volúmenes al cárter,
multiplicar por N ni añadir redes, accesorios, cálculos físicos o entrega 5.

#### Scenario: Perfil actualizado
- **WHEN** cambia una dimensión válida, el orden o la selección
- **THEN** el perfil refleja los datos y la selección actuales; una dimensión necesaria inválida retira el perfil y explica la causa.

### Requirement: Persistencia compatible y protección
JSON v5 MUST guardar ambas listas ordenadas, nombres, dimensiones y referencia,
sin derivados. MUST leer v1–v4 conservando todos los datos anteriores e iniciando
ambos recorridos vacíos, sin reescritura automática. MUST conservar guardado seguro,
cancelaciones, sobrescritura y protección de cambios. Pruebas MUST usar archivos
temporales, sin ejemplos que deban conservarse en .venv ni alterar destinos elegidos.

#### Scenario: Recuperación y cambios de ciclo
- **WHEN** se guarda y reabre o alterna 2T/4T
- **THEN** se conservan los dos recorridos y el resto del proyecto; cancelar/errores preservan archivo y edición.

### Requirement: Comprobación y registro
MUST probar cilindro, expansión/contracción, ausentes/inválidos, discontinuidades,
edición/eliminación/orden, actualización, persistencia antigua y regresiones.
MUST ejecutar suite completa una vez después de la última corrección, revisión
puntual y Windows disponible al 150 % con captura real separada de aceptación manual.
MUST actualizar tareas, README/hoja, commit separado y push normal si autenticación
permite, sin reintentos de credenciales, cambios globales, archivo ni entrega 5.

#### Scenario: Entrega verificable
- **WHEN** se entrega el editor
- **THEN** se informan resultados finales, revisión, pendientes, captura, comando de inicio, commit y publicación real sin atribuir aceptación manual.
