# Propuesta de reorganización de Dino

## Decisión

Reorganizar la arquitectura de información y la coordinación del estado de la
interfaz, conservando los núcleos, las APIs públicas y los servicios útiles.
Evolución incremental mediante adaptadores, con una experiencia común por tarea.
No conviene una reescritura total del producto: el trabajo ya hecho en ejecución,
procedencia, validación de entrada y preservación de históricos tiene valor.
Tampoco alcanza con cambiar colores manteniendo las tres interfaces incrustadas.

El principal objeto del usuario es **un proyecto de motor**, con variantes,
revisiones, estudios y corridas. Los menús se organizan alrededor de ese objeto,
no alrededor de módulos Python o de las campañas históricas del repositorio.

## Arquitectura de información

```text
Inicio / proyectos
  Crear · Abrir · Recientes · Recuperar borrador · Importar bundle
Proyecto activo [familia y núcleo fijados por su esquema]
  Motor y componentes
    Geometría · Admisión · Escape · Combustión · Pérdidas · Ambiente
    2T: cárter, lumbreras y transferencias
    4T nativo: válvulas, alzadas, distribución y conductos
    4T 0D: únicamente los componentes y límites de la referencia
  Variantes y revisiones
  Preparar simulación
    Punto · Curva RPM · Estudios admitidos por ese modelo
  Corridas y cola
    Pendientes · Activas · Terminadas · Parciales · Históricas
  Resultados
    Prestaciones · Muestras/trazas · Balances · Medidas de referencia
  Comparar
    Elegir par · Elegibilidad · Cambios de configuración · Diferencias
  Compartir e informes
    Bundle · CSV · HTML/PDF · Dependencias y archivos externos
  Datos y procedencia
    Fuentes · Validaciones declaradas · Configuración/artefactos originales
Ayuda y diagnóstico [siempre accesibles]
```

Una cabecera persistente muestra nombre/ruta del proyecto, familia y núcleo,
variante activa, revisión aplicada y estado de guardado. Al inspeccionar una
corrida, se muestra además su revisión: la selección del resultado nunca cambia
silenciosamente el motor activo. Las identidades completas y hashes van al
inspector de procedencia, disponibles para diagnóstico y comparación.

La familia y el núcleo no se cambian con un selector que aparente convertir el
mismo motor. Cambiar de proyecto carga su contrato; crear uno nuevo elige el
tipo correspondiente. El 4T 0D permanece disponible como **referencia sintética**,
con acceso claro desde proyectos/ejemplos y apertura de históricos. Su colocación
en referencia no elimina capacidades existentes ni lo transforma en nativo.

## Pantallas y recorridos propuestos

### 1. Inicio y proyecto

Recientes con nombre, modelo, última apertura y disponibilidad. Crear/abrir son
acciones principales. La primera ejecución ofrece un recorrido corto opcional,
sin convertir avisos de arquitectura en requisitos para trabajar.

Una recuperación presenta todos los borradores, fecha, proyecto y origen antes
de preguntar; abrir recupera una copia sin vincular la ruta original. El usuario
puede posponer sin perder el borrador. Las plantillas se declaran sintéticas y
se explica qué datos debe reemplazar para describir su propio motor.

### 2. Motor y componentes

Árbol compacto de componentes a la izquierda, diagrama coordinado en el centro
e inspector de parámetros a la derecha. Seleccionar una pieza en el diagrama
selecciona el mismo objeto en el árbol. En pantalla pequeña, el inspector se
apila o colapsa; los campos y acciones siguen siendo alcanzables por teclado.

El formulario presenta magnitud, unidad, procedencia y convención. Las válvulas
incluyen alzada/eventos; el escape conserva el perfil y las cotas que ya sirven;
el 2T mantiene cronograma/áreas de lumbreras existentes. No se agrega una vista
3D como condición para comprender dimensiones que un esquema claro resuelve.

Los campos derivados son de lectura y muestran sus dependencias. El detalle de
esquema se mueve a Avanzado, conservando acceso a información que necesita un
usuario experto. Ninguna selección o cambio de unidad reescribe valores de origen.

Hay tres estados de edición separados: **borrador**, **aplicado** y **guardado**.
Un borrador invalida la posibilidad de ejecutar silenciosamente otra revisión.
Aplicar valida transaccionalmente; el rechazo conserva el último modelo válido y
devuelve el foco al campo. Guardar indica qué revisión está persistiendo.
La llegada de resultados no debe reemplazar ediciones en curso.

### 3. Preparar una simulación

Una estructura común para punto/curva/estudio admitido, con adaptador por modelo.
El usuario ve rango, cantidad y lista de RPM, variante/revisión, horizonte,
presupuesto por punto y agregado, memoria y destino. La estimación de duración
se basa en corridas comparables cuando existen; si no, se declara desconocida.
El presupuesto es un límite, no una promesa de duración.

El preflight separa errores que impiden correr de advertencias que informan el
alcance. Cada error enlaza el componente/campo correspondiente. Los límites del
núcleo y los umbrales científicos se consultan desde sus contratos vigentes.
La confirmación no exige interpretar rutas internas, aunque permite desplegarlas.

### 4. Corridas y cola

Todos los trabajos se descubren desde el proyecto. Cada fila muestra variante,
revisión, punto/rango, fase, tiempo transcurrido, periodicidad e integridad.
La fase inicial distingue preparación/inicialización de integración y escritura.
Se muestra progreso real por punto/ciclo cuando el backend lo emite; un progreso
desconocido se declara como tal y no se reemplaza por porcentajes inventados.

Cancelar explica el punto seguro que soporta ese modelo. La UI distingue:

- Cancelar un trabajo y conservar lo disponible.
- Reintentar trabajos pendientes o fallidos como nueva ejecución.
- Reanudar un checkpoint sólo si la capability/estado exactos lo admiten.

El 4T nativo no obtiene reinicio exacto por la mera existencia de una cola o por
poder reabrir un proyecto. Las tareas fijan una copia identificada de entrada al
salir de pendiente. Los trabajos terminados ofrecen **Ver resultado** directamente.

### 5. Resultados

Primero se responde qué se calculó, con qué configuración y qué se puede inferir.
Después se ofrecen curvas, muestras/trazas y balances. Ejecución, periodicidad,
integridad y validación experimental son cuatro ejes independientes. Un resultado
con hashes correctos puede ser transitorio y no validado físicamente.

Los gráficos de prestaciones excluyen por defecto los valores no elegibles,
con una explicación por punto y acceso a muestras transitorias identificadas.
Los gaps no son ceros ni segmentos interpolados. Presiones y eventos respetan
la convención nativa 360°/720° y el período del artefacto. Un cursor inspecciona
muestras discretas, no crea nuevos datos.

La comparación con mediciones permanece disponible en el modelo correspondiente,
declarando procedencia e incertidumbre. Importar una medición no valida el modelo.
El usuario puede desplegar la configuración y los archivos originales de la corrida.

### 6. Comparar variantes

Selección guiada de A y B y matriz de elegibilidad antes de calcular: familia,
núcleo, RPM, condiciones, modelos, discretización, procedencia y periodicidad,
según el contrato actual. La UI explica qué condición bloquea el par y propone
una acción, sin relajar el criterio para habilitar el botón.

Un panel muestra las diferencias de configuración de los dos extremos exactos,
no sólo las diferencias del proyecto actual. Una diferencia geométrica, una
diferencia transitoria y una comparación periódica admitida tienen rótulos
distintos. La incertidumbre no disponible permanece no disponible.

No se presenta una ganancia 2T frente a 4T ni se inventa un contrato científico
para 0D de referencia por querer completar una pantalla común. Las capacidades
no soportadas se explican y el frontend ofrece únicamente vistas descriptivas
compatibles con los contratos que existan.

### 7. Compartir e informar

Previsualización de contenido: proyecto, variantes, corridas vinculadas, medidas,
configuraciones, manifiestos y trazas. Los resultados seleccionados pero externos
se muestran como excluidos, con una acción explícita de asociación si corresponde.
El usuario ve el tamaño estimado y las dependencias faltantes antes de exportar.

El bundle conserva bytes/hashes originales y el cierre transitivo de dependencias.
Una importación comprueba disponibilidad semántica, no sólo hashes de archivos
directos. Su resumen diferencia íntegro, parcial y legacy. Los informes toman un
conjunto/revisión explícitos y conservan unidades, estados y límites científicos.

## Organización de implementación

| Pieza | Responsabilidad | Lo que conserva |
|---|---|---|
| Shell de proyecto | Navegación, cabecera, comando activo y estados vacíos | Proyectos actuales y atajos útiles |
| Adaptador de capacidad | Edición, preparación y visualización por modelo | Núcleos 2T, nativo 4T y referencia separados |
| Sesión de edición | Borrador/aplicado/guardado y undo/redo | Identidad/precisión de entradas no editadas |
| Registro de trabajos | Estado, señales, cancelación y artefactos asociados | Capacidades reales de cada runner |
| Selección de resultados | Dataset explícito, revisión, elegibilidad | Datos primarios y clasificaciones |
| Portabilidad/informes | Dependencias, resolución de rutas, exportación | Bytes, hashes y evidencia histórica |

Los adaptadores deben depender de APIs públicas, no importar internals del solver.
Las vistas de referencia no son un fallback silencioso del motor nativo. La
presentación común no exige fusionar los contratos de datos científicos.

## Migración y riesgos

1. Corregir los tres P0 con pruebas de comportamiento reproducibles.
2. Añadir contexto/selección comunes sin cambiar la serialización del proyecto.
3. Introducir navegación nueva detrás de una opción de transición y adaptar los
   widgets útiles. Mantener accesos a archivos históricos y diagnósticos.
4. Migrar por recorrido vertical: abrir→editar→ejecutar→ver→compartir para cada
   modelo. Evitar una migración de todos los widgets antes de probar un recorrido.
5. Cerrar equivalencia funcional con proyectos reales copiados, negativos,
   cancelación, rutas faltantes, teclado y matriz de resoluciones/DPI.
6. Evaluar con usuarios y sólo entonces retirar navegación duplicada.

Riesgos principales: selección del contexto equivocado, pérdida de borradores,
reclasificación de históricos y reescritura accidental de valores. Se reducen
con pruebas negativas por identidad, importación aislada y límites entre capas.
Las migraciones de contratos de aplicación, si son necesarias, se versionan y
preservan el archivo original; nunca se edita evidencia congelada para adaptarla.

## Evaluación crítica de alternativas

| Alternativa | UX | Mantenibilidad | Riesgo | Recomendación |
|---|---|---|---|---|
| Cambios visuales aislados | Mejora lectura; conserva flujos confusos | Continúa la duplicación | Bajo por cambio, alto de persistir errores | Útil para el contraste urgente, insuficiente como dirección |
| Reorganización incremental con adaptadores | Permite coherencia por tarea | Aísla contrato científico y reutiliza widgets | Moderado y verificable por recorrido | **Elegida** |
| Reescritura total de frontend/backend | Puede perder capacidades y conocimiento acumulado | Alto coste de reconstrucción | Alto riesgo de serialización y regresión | No justificada por la evidencia actual |

## Material visual

- [Prototipo HTML navegable](wireframes.html): seis espacios, variantes de proyecto,
  borrador pendiente, preparación, cancelación e información de exportación.
- [Motor y componentes](wireframes/modelo.svg).
- [Preparación y ejecución](wireframes/simulacion.svg).
- [Resultados y comparación](wireframes/resultados.svg).

Los SVG se renderizaron e inspeccionaron; el HTML no tuvo prueba de navegador
por falta de un navegador conectado. Todo el material visual de esta sección es
**diseño ilustrativo**, no captura del producto ni evidencia científica.
