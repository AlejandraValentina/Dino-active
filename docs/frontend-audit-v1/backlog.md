# Backlog ejecutable de frontend y backend de aplicación

Estado de todos los ítems: **PROPUESTO / NO ACTIVADO**. Esta auditoría entrega
investigación y diseño; no autoriza implementación ni cambios científicos.

P0 impide usar correctamente una función existente; P1 afecta comprensión o
productividad; P2 amplía interacción/visualización; P3 refina el acabado.
FRONTEND incluye widgets, presentación y adaptación de comandos. BACKEND_APLICACION
incluye contexto, transacciones, archivos, asociación de artifacts y scheduler;
no significa un servidor web ni cambios de solver.

## Orden sugerido

1. UX-001/002/003: protección de edición, portabilidad y guardado; independientes
   entre sí, con regresiones propias y aceptación en la aplicación fuente.
2. UX-004/005/008/009/010: contexto persistente, navegación, ayuda legible y resultado accesible.
3. UX-006/007/011/012/014: editores, archivos, planificación y comparación.
4. UX-013 y UX-015…021: capacidades de productividad, accesibilidad y compactación.
5. UX-022/023: acabado una vez estabilizada la arquitectura.

Cada fase puede entregarse con adaptadores y una bandera de navegación nueva.
No reconstruir candidatos en esta fase de auditoría. La futura aceptación del
producto debe comprobar el binario de la revisión que realmente se distribuya.

## Resumen

| ID | Prioridad | Capa | Resultado | Dependencias |
|---|---|---|---|---|
| UX-001 | P0 | FRONTEND+BACKEND_APLICACION | Toda ejecución y guardado identifican la revisión aplicada y resuelven explícitamente las ediciones pendientes. | — |
| UX-002 | P0 | BACKEND_APLICACION+FRONTEND | Exportación/importación portables con cierre transitivo y evaluación semántica de disponibilidad antes de declarar éxito. | — |
| UX-003 | P0 | BACKEND_APLICACION+FRONTEND | Guardar funciona después de todas las rutas de apertura/importación y sus fallos tienen respuesta visible. | — |
| UX-004 | P1 | FRONTEND | Cabecera persistente con proyecto, tipo de modelo, variante, revisión aplicada y estado de guardado. | UX-001 |
| UX-005 | P1 | FRONTEND | Un recorrido común con capacidades explícitas por modelo y herramientas de referencia en un espacio identificado. | UX-004 |
| UX-006 | P1 | FRONTEND | Editores por componente con magnitudes, unidades, selección tipada y procedencia contextual; el esquema queda en una vista avanzada. | UX-001, UX-004 |
| UX-007 | P1 | FRONTEND | Errores locales en español, con campo, unidad, motivo y acción; detalle técnico desplegable. | UX-006 |
| UX-008 | P1 | FRONTEND | Paleta coherente de documentos y controles de ayuda con contraste suficiente. | — |
| UX-009 | P1 | FRONTEND | La verificación usa exclusivamente el contexto y la selección activos. | UX-004 |
| UX-010 | P1 | FRONTEND | Toda corrida terminal ofrece Ver resultado, inspeccionar motivo y acciones siguientes. | UX-004 |
| UX-011 | P1 | FRONTEND+BACKEND_APLICACION | Asociación explícita de corridas al proyecto y resumen del contenido portable antes de exportar. | UX-002, UX-004, UX-010 |
| UX-012 | P1 | FRONTEND+BACKEND_APLICACION | Preparador común de punto/curva con plan explícito y controles adaptados a capacidades existentes. | UX-004, UX-005 |
| UX-013 | P1 | BACKEND_APLICACION+FRONTEND | Cola común de trabajos con identidad de modelo y capacidades explícitas; extensión propuesta, no incumplimiento del alcance CP1 0D. | UX-001, UX-012 |
| UX-014 | P1 | FRONTEND+BACKEND_APLICACION | Constructor de comparación A/B guiado con explicación de elegibilidad y vínculo a cambios de configuración. | UX-004, UX-010 |
| UX-015 | P2 | FRONTEND | Mapa esquemático seleccionable con convenciones físicas y límites del modelo visibles. | UX-004, UX-006 |
| UX-016 | P2 | FRONTEND | Zoom, restauración de escala y cursor de muestra enlazado, con unidades y puntos ausentes explícitos. | UX-014 |
| UX-017 | P2 | FRONTEND | Cuatro indicadores separados: ejecución, periodicidad, integridad y validación científica, con detalle técnico disponible. | UX-004 |
| UX-018 | P2 | FRONTEND | Paneles colapsables y prioridad de acciones con desplazamiento predecible. | UX-004, UX-005, UX-006 |
| UX-019 | P2 | FRONTEND | Selector de recuperación con contexto, fecha, origen y opción de posponer. | UX-004 |
| UX-020 | P2 | FRONTEND | Recorridos de teclado y etiquetas semánticas verificadas con tecnología asistiva. | UX-008, UX-018 |
| UX-021 | P2 | FRONTEND+BACKEND_APLICACION | Explorador común de variantes con operaciones y consecuencias explícitas. | UX-004 |
| UX-022 | P3 | FRONTEND | Vocabulario español consistente con códigos originales disponibles en detalle técnico. | — |
| UX-023 | P3 | FRONTEND | Jerarquía de objetivo, acción, estado y detalle técnico sin ocultar las limitaciones científicas. | UX-004, UX-005, UX-006, UX-017 |

## Fichas de implementación

### UX-001 · P0 · Una edición nativa sin aplicar puede perderse y ejecutarse el modelo anterior

**Problema:** Se escribió 87 mm en el diámetro nativo, se confirmó la celda y se pasó a SIMULAR. La tabla mostraba 87, pero el contexto y la solicitud real del worker conservaron 86. No hubo advertencia de edición pendiente. Tras publicar el resultado, el editor volvió a mostrar 86.

**Resultado esperado:** Toda ejecución y guardado identifican la revisión aplicada y resuelven explícitamente las ediciones pendientes.

**Capa:** FRONTEND+BACKEND_APLICACION. **Componentes:** `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/native_four_stroke_workspace.py`, `motorsim/desktop/context.py`.

**Dependencias:** Ninguna otra mejora de este backlog.

**Criterios de aceptación:**

- Editar 86→87 y cambiar de pantalla conserva el borrador y muestra su estado.
- Ejecutar obliga a aplicar, descartar explícitamente o cancelar; nunca usa 86 mientras se presenta 87 como actual.
- Un evento de resultados no destruye un borrador; aplicar sin cambios mantiene los valores exactos de origen.

**Verificación:** Repetir la secuencia Qt y contrastar el valor visible con config_resolved.json real, incluyendo guardado, llegada de resultados y rechazo de una entrada inválida.

### UX-002 · P0 · El bundle nativo no transporta la cadena completa de resultados

**Problema:** El bundle nativo contenía project.json, manifest.json, README y dos resúmenes/dos run.json. Tras importarlo por la interfaz, las dos corridas antes verificables quedaron UNAVAILABLE: faltaba artifacts/artifacts/artifacts.json. El diálogo de importación había anunciado proyecto y artifacts verificados.

**Resultado esperado:** Exportación/importación portables con cierre transitivo y evaluación semántica de disponibilidad antes de declarar éxito.

**Capa:** BACKEND_APLICACION+FRONTEND. **Componentes:** `motorsim/desktop/project_bundles.py`, `motorsim/desktop/four_stroke_artifacts.py`, `motorsim/desktop/app.py`.

**Dependencias:** Ninguna otra mejora de este backlog.

**Criterios de aceptación:**

- Incluir manifiesto primario, configuración, resumen y traza cuando exista, preservando sus bytes y hashes originales.
- Importar en otra raíz sin acceso a la raíz original conserva las clasificaciones e integridad de cada corrida.
- Una dependencia faltante se explica por corrida; no se anuncia éxito íntegro ni se promueve evidencia legacy.

**Verificación:** Roundtrip de bundles nativos completos, incompletos y legacy en un entorno que sólo permite leer la extracción; verificar todos los hashes y abrir las trazas. Usar versión nueva del contrato de bundle si cambia.

### UX-003 · P0 · Guardar un proyecto nativo importado falla sin aviso visible

**Problema:** Después de importar el bundle, context.path era str. Pulsar Guardar produjo AttributeError: str object has no attribute suffix en app.py. La interfaz tenía tres referencias y el archivo seguía con dos; dirty permaneció true. No apareció un diálogo de error.

**Resultado esperado:** Guardar funciona después de todas las rutas de apertura/importación y sus fallos tienen respuesta visible.

**Capa:** BACKEND_APLICACION+FRONTEND. **Componentes:** `motorsim/desktop/app.py`, `motorsim/desktop/context.py`, `motorsim/desktop/project_bundles.py`.

**Dependencias:** Ninguna otra mejora de este backlog.

**Criterios de aceptación:**

- Normalizar rutas en una frontera de aplicación sin cambiar el esquema científico.
- Guardar después de importar escribe el proyecto esperado y limpia dirty sólo tras éxito.
- Un fallo de permisos o I/O mantiene el borrador y ofrece Guardar como/diagnóstico.

**Verificación:** Abrir/importar con str y Path, editar y pulsar Guardar; reabrir y verificar contenido. Repetir con escritura denegada y comprobar aviso visible.

### UX-004 · P1 · El contexto activo desaparece en los espacios nativos de ejecución y resultados

**Problema:** 2T conserva proyecto, variante y estado en la cabecera. En nativo, la lista de variantes sólo se ve en MODELO y desaparece al simular o analizar. La barra de título del sistema conserva parte del proyecto, pero el cuerpo de la aplicación no mantiene ese contexto.

**Resultado esperado:** Cabecera persistente con proyecto, tipo de modelo, variante, revisión aplicada y estado de guardado.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/app.py`, `motorsim/desktop/widgets/context_bar.py`, `motorsim/desktop/native_four_stroke_workspace.py`.

**Dependencias:** UX-001.

**Criterios de aceptación:**

- La misma estructura permanece en Modelo, Simular, Corridas, Resultados y Comparar.
- Seleccionar un resultado histórico muestra su revisión junto al modelo actual y señala diferencias.
- El 4T de referencia nunca se presenta como el mismo núcleo que el nativo.

**Verificación:** Recorrido de las tres modalidades, dos variantes y un resultado anterior; capturas con identidades largas en 980×680 y 1360×860.

### UX-005 · P1 · 4T 0D duplica navegación y acciones de proyecto

**Problema:** En 4T 0D coexisten MODELO/SIMULAR/RESULTADOS con Diseño 4T/Resultados 4T/Curva RPM 4T, además de Volver a 2T y Nuevo/Abrir/Guardar 4T dentro del módulo. Ejecutar sigue visible en Resultados.

**Resultado esperado:** Un recorrido común con capacidades explícitas por modelo y herramientas de referencia en un espacio identificado.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/app.py`, `motorsim/desktop/four_stroke_workspace.py`, `motorsim/desktop/four_stroke_curve.py`.

**Dependencias:** UX-004.

**Criterios de aceptación:**

- Una sola navegación principal y una sola acción de proyecto por operación.
- Abrir un proyecto 0D conserva su contrato y lo identifica como referencia sintética.
- Los accesos existentes tienen equivalentes localizables y conservan atajos adecuados.

**Verificación:** Comparar mapas de navegación y completar los mismos objetivos en 2T, nativo y referencia, sin convertir archivos entre modelos.

### UX-006 · P1 · El editor nativo expone el esquema como formulario principal

**Problema:** El modelo nativo se presenta como pestañas de tablas con rutas de parámetros, procedencia repetida y valores de texto libre. La creación 4T solicita nombres y deriva el resto a una plantilla sintética; el usuario debe descubrir después cómo completar el motor.

**Resultado esperado:** Editores por componente con magnitudes, unidades, selección tipada y procedencia contextual; el esquema queda en una vista avanzada.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/new_engine_dialog.py`, `motorsim/desktop/native_four_stroke_workspace.py`.

**Dependencias:** UX-001, UX-004.

**Criterios de aceptación:**

- Geometría, válvulas, conductos y operación tienen controles adecuados y ayuda de convenciones.
- Los datos ausentes no se presentan como mediciones y la plantilla sintética permanece identificada.
- Los valores no editados preservan exactamente su representación científica de origen.

**Verificación:** Introducir un motor desde una ficha de medidas y revisar no-op Apply, precisión, unidades, claves opcionales y errores de dependencias.

### UX-007 · P1 · La validación nativa devuelve errores de conversión sin ubicación útil

**Problema:** Una entrada numérica incompleta produjo could not convert string to float: en un mensaje de advertencia. La configuración aplicada se conservó, pero el aviso no identificó la sección/celda ni indicó cómo corregirla. El rechazo geométrico 2T sí explicó la relación biela/carrera.

**Resultado esperado:** Errores locales en español, con campo, unidad, motivo y acción; detalle técnico desplegable.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/engine_page.py`.

**Dependencias:** UX-006.

**Criterios de aceptación:**

- El foco vuelve a la celda inválida y el valor no se aplica.
- Un resumen enlaza todos los errores de la transacción sin ocultar otros campos.
- Se preservan los criterios de validación existentes.

**Verificación:** Ingresar texto incompleto, NaN, negativos y una dependencia inválida; comprobar foco, mensaje y configuración aplicada intacta.

### UX-008 · P1 · La guía inicial tiene texto claro sobre fondo blanco

**Problema:** La guía y la tabla de primeros pasos se renderizaron con fondo blanco y texto muy claro en la aplicación real con Qt 6.11.2, dificultando su lectura.

**Resultado esperado:** Paleta coherente de documentos y controles de ayuda con contraste suficiente.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/theme.py`, `motorsim/desktop/onboarding.py`, `motorsim/desktop/product.py`.

**Dependencias:** Ninguna otra mejora de este backlog.

**Criterios de aceptación:**

- Guía y verificaciones se leen en temas/os soportados; texto normal objetivo ≥4,5:1.
- Tablas HTML, vínculos, selección y foco conservan contraste.
- La corrección cubre About y otros QTextBrowser sin cambiar el contenido científico.

**Verificación:** Renderizar con el Qt fijado, medir colores reales de texto/fondo y revisar capturas de guía, About y diagnósticos.

### UX-009 · P1 · Primeros pasos mezcla el proyecto 2T con el contexto nativo

**Problema:** Con el proyecto nativo activo, la tabla de la guía informó identidad audit-2t, familia 4T y resultado listo. Los resultados 2T cargados pueden satisfacer la verificación aunque los nativos importados estén no disponibles.

**Resultado esperado:** La verificación usa exclusivamente el contexto y la selección activos.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/onboarding.py`, `motorsim/desktop/app.py`.

**Dependencias:** UX-004.

**Criterios de aceptación:**

- Nombre, familia y disponibilidad pertenecen al mismo proyecto/revisión.
- Un resultado de otra familia no activa el paso de resultados.
- No disponible, legacy, parcial y periódico se describen sin equivalencia científica.

**Verificación:** Alternar tres proyectos con disponibilidad distinta y abrir la guía en cada uno; comprobar identidad y estado.

### UX-010 · P1 · La corrida 2T terminada no conduce directamente a su resultado

**Problema:** Tras completar un ciclo, la barra mostró terminación y checkpoint. RESULTADOS siguió sin corrida seleccionada. Fue necesario abrir Variantes y corridas, seleccionar el historial y abrir la corrida para cargar los datos.

**Resultado esperado:** Toda corrida terminal ofrece Ver resultado, inspeccionar motivo y acciones siguientes.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/execution_page.py`, `motorsim/desktop/app.py`, `motorsim/desktop/widgets/run_history.py`, `motorsim/desktop/results_page.py`.

**Dependencias:** UX-004.

**Criterios de aceptación:**

- Ver resultado abre la corrida exacta aun si no convergió.
- La carga asíncrona tiene estado visible y un error recuperable.
- La curva sigue excluyendo valores no periódicos y explica ese filtro.

**Verificación:** Terminar, cancelar y agotar presupuesto en un punto 2T; abrir cada resultado desde su tarjeta sin buscar rutas.

### UX-011 · P1 · El bundle 2T puede omitir el resultado que está en pantalla sin anticiparlo

**Problema:** Después de abrir el resultado real de un ciclo, el proyecto tenía cero result_references. Exportar bundle produjo sólo proyecto, manifiesto y README: cero archivos de resultados. El diálogo anunció artifacts referenciados sin mostrar qué quedó fuera.

**Resultado esperado:** Asociación explícita de corridas al proyecto y resumen del contenido portable antes de exportar.

**Capa:** FRONTEND+BACKEND_APLICACION. **Componentes:** `motorsim/desktop/project_bundles.py`, `motorsim/desktop/context.py`, `motorsim/desktop/results_page.py`, `motorsim/desktop/app.py`.

**Dependencias:** UX-002, UX-004, UX-010.

**Criterios de aceptación:**

- El usuario distingue resultado seleccionado, vinculado y externo.
- La exportación lista cantidades, tamaño, dependencias faltantes y resultados excluidos.
- Vincular no cambia configuración, hashes ni nivel de evidencia del resultado.

**Verificación:** Ejecutar→abrir→vincular→guardar→exportar→importar un punto 2T; contrastar selección, manifiesto y disponibilidad.

### UX-012 · P1 · Las curvas RPM se preparan de tres formas y el coste agregado no siempre es visible

**Problema:** 2T usa un diálogo con presupuestos por punto y total; nativo usa una pestaña con tiempo/punto y sin total visible; referencia tiene su propia pestaña y límites. El formulario nativo inicial proponía 1000–13000, paso 500 y 120 s/punto: 25 puntos y hasta 3000 s presupuestados, sin incluir overhead; esto no es una predicción de duración.

**Resultado esperado:** Preparador común de punto/curva con plan explícito y controles adaptados a capacidades existentes.

**Capa:** FRONTEND+BACKEND_APLICACION. **Componentes:** `motorsim/desktop/execution_page.py`, `motorsim/desktop/native_four_stroke_curve.py`, `motorsim/desktop/four_stroke_curve.py`.

**Dependencias:** UX-004, UX-005.

**Criterios de aceptación:**

- Mostrar lista/cantidad de RPM, ciclos, presupuesto por punto, total y estimación si existe evidencia comparable.
- Distinguir presupuesto máximo, tiempo transcurrido y estimación desconocida.
- Mantener dominios, CFL, tolerancias y políticas de reanudación de cada núcleo.

**Verificación:** Preparar rangos válidos e inválidos en cada modelo, verificar la lista exacta y cancelar antes de ejecutar; probar un barrido breve autorizado.

### UX-013 · P1 · La cola de trabajos disponible sólo cubre curvas de referencia 4T 0D

**Problema:** La cola CP1 se localiza dentro de Curva RPM 4T 0D y permite agregar curvas de esa referencia. No equivale a una cola general de trabajos 2T y nativos. Se probó agregar un ítem; no se ejecutó la cola.

**Resultado esperado:** Cola común de trabajos con identidad de modelo y capacidades explícitas; extensión propuesta, no incumplimiento del alcance CP1 0D.

**Capa:** BACKEND_APLICACION+FRONTEND. **Componentes:** `motorsim/desktop/batch_queue.py`, `motorsim/desktop/execution_page.py`, `motorsim/desktop/native_four_stroke_curve.py`.

**Dependencias:** UX-001, UX-012.

**Criterios de aceptación:**

- Los trabajos fijan configuración/revisión antes de salir de pendiente.
- Cancelar, reintentar pendientes y reanudar checkpoint son acciones distintas.
- El nativo no promete reinicio exacto y la cola no altera simultáneamente un proyecto en ejecución.

**Verificación:** Pruebas del scheduler por adaptador y UAT de dos trabajos por modalidad con presupuesto/cancelación; sin mezclar resultados de familias.

### UX-014 · P1 · La comparación requiere descubrir por separado pares, contexto y cambios de diseño

**Problema:** 2T y nativo presentan mecanismos distintos. Con una sola corrida nativa, Comparar permite intentar el mismo extremo y después pide elegir dos diferentes. Existe una guía, pero no una preparación de par que explique anticipadamente elegibilidad y diferencia de configuración. La comparación 0D no debe inventarse por uniformidad visual.

**Resultado esperado:** Constructor de comparación A/B guiado con explicación de elegibilidad y vínculo a cambios de configuración.

**Capa:** FRONTEND+BACKEND_APLICACION. **Componentes:** `motorsim/desktop/results_page.py`, `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/four_stroke_comparison.py`, `motorsim/desktop/legacy_ux.py`.

**Dependencias:** UX-004, UX-010.

**Criterios de aceptación:**

- Mostrar familia/núcleo, RPM, configuración, estado e incompatibilidades antes de calcular.
- Separar diferencia geométrica, diferencia transitoria y comparación admitida por el contrato.
- No habilitar ganancias entre familias ni promover legacy o no convergidos.

**Verificación:** Pares idénticos, incompatibles, legacy, no periódicos y válidos; comprobar que la UI explica el rechazo y mantiene los contratos.

### UX-015 · P2 · Falta una vista de motor coordinada con el editor de componentes

**Problema:** 2T ya tiene un esquema de cilindro y un perfil de escape útiles. No forman un mapa de sistema que conecte cilindro, cárter, admisión, transferencias y escape con el componente editado; nativo depende de tablas.

**Resultado esperado:** Mapa esquemático seleccionable con convenciones físicas y límites del modelo visibles.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/model_diagrams.py`, `motorsim/desktop/engine_page.py`, `motorsim/desktop/exhaust_page.py`, `motorsim/desktop/four_stroke_desktop.py`.

**Dependencias:** UX-004, UX-006.

**Criterios de aceptación:**

- Seleccionar un componente en el árbol o diagrama sincroniza el inspector.
- El esquema se identifica como esquemático cuando no representa dimensiones reales.
- 2T y 4T muestran sus componentes propios; 0D no aparenta resolver una geometría que no modela.

**Verificación:** Evaluación con tareas de localizar y modificar un componente, sin cambiar el documento al seleccionar.

### UX-016 · P2 · Inspección gráfica avanzada insuficiente para explorar muestras exactas

**Problema:** Las vistas permiten trazas y selección de puntos en algunos gráficos. CurvePlot implementa selección por clic, pero no un sistema común de zoom y cursor enlazado entre tabla, presión y eventos. La propuesta amplía esas interacciones; no declara que todos los gráficos actuales carezcan de selección.

**Resultado esperado:** Zoom, restauración de escala y cursor de muestra enlazado, con unidades y puntos ausentes explícitos.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/plot.py`, `motorsim/desktop/four_stroke_results.py`, `motorsim/desktop/results_page.py`.

**Dependencias:** UX-014.

**Criterios de aceptación:**

- El cursor muestra la muestra discreta y su índice sin inventar interpolaciones.
- Se conservan las convenciones 360°/720° y los períodos del artefacto.
- Los gaps de puntos no admitidos no se unen ni se convierten en ceros.

**Verificación:** Comparar valores de cursor con el CSV primario y verificar gaps, escalas y exportación.

### UX-017 · P2 · Los términos técnicos y los ejes de confianza necesitan una presentación común

**Problema:** La UI combina EXPLORATORY, VERIFIED, NOT_VALIDATED, DINO4T_API_V1, límite de pared, auditoría e integridad. Los resultados 2T sí identifican los transitorios, y los legacy se conservan como no verificados. Esas distinciones correctas aparecen con organización y vocabulario diferentes.

**Resultado esperado:** Cuatro indicadores separados: ejecución, periodicidad, integridad y validación científica, con detalle técnico disponible.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/presentation.py`, `motorsim/desktop/results_page.py`, `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/app.py`.

**Dependencias:** UX-004.

**Criterios de aceptación:**

- Integridad verificada nunca se rotula como validación experimental.
- Se muestran unidades de potencia, presión y par junto a cada valor y cualquier conversión es explícita.
- Un resultado incompleto explica qué se puede inspeccionar y qué comparación queda bloqueada.

**Verificación:** Revisar casos vacío, convergido, no convergido, cancelado, incompleto, legacy y no disponible en las tres modalidades.

### UX-018 · P2 · Los diseños compactos requieren redistribuir contenido y navegación

**Problema:** En 980×680 el editor nativo dedica una columna amplia a variantes y oculta secciones tras flechas de pestañas. En 2T se comprimen contexto, controles y área de análisis; incluso a 1360 la etiqueta Baseline queda truncada. Las ventanas sí aceptaron el tamaño solicitado.

**Resultado esperado:** Paneles colapsables y prioridad de acciones con desplazamiento predecible.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/app.py`, `motorsim/desktop/widgets/context_bar.py`, `motorsim/desktop/native_four_stroke_workspace.py`, `motorsim/desktop/results_page.py`.

**Dependencias:** UX-004, UX-005, UX-006.

**Criterios de aceptación:**

- En 980×680 se alcanzan edición, aplicar, ejecutar, cancelar y exportar sin controles fuera de pantalla.
- En 1360×860 se mantienen gráfico y contexto legibles.
- Verificar 100/125/150% en implementación; esta auditoría no acredita esos tres DPI.

**Verificación:** Matriz de tamaños/DPI, navegación por teclado y captura sin modificar tipografía del sistema para ocultar problemas.

### UX-019 · P2 · La decisión de recuperación carece de identidad y previsualización

**Problema:** La recuperación como copia funcionó y preservó el archivo original. El aviso preguntó por un borrador de 2T sin mostrar nombre, fecha, ruta original, diferencias o lista de borradores. Se observó además la secuencia de avisos por familia.

**Resultado esperado:** Selector de recuperación con contexto, fecha, origen y opción de posponer.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/app.py`, `motorsim/desktop/product.py`.

**Dependencias:** UX-004.

**Criterios de aceptación:**

- Mostrar todos los borradores con familia/núcleo inequívocos y selección explícita.
- Recuperar conserva la semántica de copia sin ruta del original.
- Descartar requiere identificar qué copia se elimina; posponer no la borra.

**Verificación:** Dos borradores de una familia y uno de otra, recuperación como copia y hash del original intacto.

### UX-020 · P2 · Falta una aceptación de accesibilidad de los recorridos completos

**Problema:** Se registró una secuencia real de doce Tab y nombres accesibles de controles. Eso no sustituye una prueba con lector de pantalla, alto contraste o entrada sólo por teclado. El inventario contiene controles sin nombre accesible explícito, lo cual por sí solo no demuestra que Qt no derive una etiqueta.

**Resultado esperado:** Recorridos de teclado y etiquetas semánticas verificadas con tecnología asistiva.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/app.py`, `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/theme.py`.

**Dependencias:** UX-008, UX-018.

**Criterios de aceptación:**

- Crear/editar/ejecutar/cancelar/analizar/exportar son operables sin ratón.
- El lector anuncia magnitud, unidad, error y estado activo con foco visible.
- La información crítica no depende exclusivamente del color.

**Verificación:** UAT con teclado y lector de pantalla en Windows; documentar derivación de etiquetas Qt y capturas de foco/alto contraste.

### UX-021 · P2 · Las acciones de variantes no son equivalentes entre 2T y nativo

**Problema:** El panel 2T ofrece crear, duplicar, renombrar, eliminar y comparar con base. El panel nativo muestra base, duplicar y eliminar; el renombrado no tiene un acceso equivalente.

**Resultado esperado:** Explorador común de variantes con operaciones y consecuencias explícitas.

**Capa:** FRONTEND+BACKEND_APLICACION. **Componentes:** `motorsim/desktop/project_page.py`, `motorsim/desktop/native_four_stroke_workspace.py`, `motorsim/desktop/context.py`.

**Dependencias:** UX-004.

**Criterios de aceptación:**

- Renombrar preserva o migra de forma trazable las asociaciones de resultados según el contrato existente.
- Eliminar no elimina los artifacts históricos y requiere confirmación contextual.
- Las operaciones no admitidas por 0D se explican en vez de simular capacidad.

**Verificación:** Renombrar/eliminar una variante con resultados, guardar/reabrir y comprobar asociaciones y hashes.

### UX-022 · P3 · Terminología, puntuación y codificación tienen detalles inconsistentes

**Problema:** La cola muestra PENDING/IDLE y un carácter de reemplazo; algunos diálogos usan Close y el botón PDF termina en punto mientras otros usan puntos suspensivos. Estos ejemplos se ven en la captura real, no sólo en la salida de terminal.

**Resultado esperado:** Vocabulario español consistente con códigos originales disponibles en detalle técnico.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/batch_queue.py`, `motorsim/desktop/onboarding.py`, `motorsim/desktop/results_page.py`.

**Dependencias:** Ninguna otra mejora de este backlog.

**Criterios de aceptación:**

- No hay caracteres de reemplazo visibles en los recorridos aceptados.
- Acciones que abren diálogo tienen una convención de puntuación uniforme.
- Los códigos persistidos de contratos no se traducen ni cambian.

**Verificación:** Inventario de literales, revisión visual de diálogos y comprobación de serialización idéntica.

### UX-023 · P3 · La jerarquía visual dedica demasiado espacio a avisos repetidos

**Problema:** Se repiten banners científicos, procedencia por grupo y textos de arquitectura mientras algunos editores dejan grandes áreas vacías. Los avisos necesarios compiten con el objetivo de la pantalla.

**Resultado esperado:** Jerarquía de objetivo, acción, estado y detalle técnico sin ocultar las limitaciones científicas.

**Capa:** FRONTEND. **Componentes:** `motorsim/desktop/theme.py`, `motorsim/desktop/app.py`, `motorsim/desktop/four_stroke_desktop.py`.

**Dependencias:** UX-004, UX-005, UX-006, UX-017.

**Criterios de aceptación:**

- El estado científico esencial permanece visible en todas las pantallas.
- Los detalles repetidos pasan a un inspector accesible, conservando su contenido.
- La acción principal y el siguiente paso se identifican sin leer el documento técnico completo.

**Verificación:** Revisión de tareas con usuarios y comparación de capturas, después de cerrar los cambios de arquitectura.
