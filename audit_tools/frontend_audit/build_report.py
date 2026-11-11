"""Build the revision-bound UX diagnosis/backlog and archive live evidence."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/frontend-audit-v1'
OUT=ROOT/'results/frontend-audit-v1'


def finding(number, priority, category, title, observation, impact, cause,
            evidence, components, layer, outcome, acceptance, verification,
            dependencies=(), kind='OBSERVADO'):
    return dict(id=f'UX-{number:03d}',priority=priority,category=category,title=title,
        evidence_type=kind,observation=observation,impact=impact,probable_cause=cause,
        evidence=evidence,components=components,layer=layer,expected_outcome=outcome,
        dependencies=list(dependencies),acceptance=acceptance,verification=verification,
        implementation_state='PROPOSED_NOT_ACTIVATED')


F=[
finding(1,'P0','Defecto funcional','Una edición nativa sin aplicar puede perderse y ejecutarse el modelo anterior',
 'Se escribió 87 mm en el diámetro nativo, se confirmó la celda y se pasó a SIMULAR. La tabla mostraba 87, pero el contexto y la solicitud real del worker conservaron 86. No hubo advertencia de edición pendiente. Tras publicar el resultado, el editor volvió a mostrar 86.',
 'El usuario puede atribuir un resultado a una geometría que nunca se ejecutó y perder su edición.',
 'Las celdas son un borrador sin estado propio. FourStrokeSimulation lee context.engine(); la notificación changed del resultado refresca el editor y reemplaza ese borrador.',
 ['p26-native4t-unapplied-edit','p27-native4t-unapplied-to-simulate','p28-native4t-run-with-unapplied-edit','p52-native4t-draft-after-run'],
 ['motorsim/desktop/four_stroke_desktop.py','motorsim/desktop/native_four_stroke_workspace.py','motorsim/desktop/context.py'],
 'FRONTEND+BACKEND_APLICACION','Toda ejecución y guardado identifican la revisión aplicada y resuelven explícitamente las ediciones pendientes.',
 ['Editar 86→87 y cambiar de pantalla conserva el borrador y muestra su estado.',
  'Ejecutar obliga a aplicar, descartar explícitamente o cancelar; nunca usa 86 mientras se presenta 87 como actual.',
  'Un evento de resultados no destruye un borrador; aplicar sin cambios mantiene los valores exactos de origen.'],
 'Repetir la secuencia Qt y contrastar el valor visible con config_resolved.json real, incluyendo guardado, llegada de resultados y rechazo de una entrada inválida.'),
finding(2,'P0','Defecto funcional','El bundle nativo no transporta la cadena completa de resultados',
 'El bundle nativo contenía project.json, manifest.json, README y dos resúmenes/dos run.json. Tras importarlo por la interfaz, las dos corridas antes verificables quedaron UNAVAILABLE: faltaba artifacts/artifacts/artifacts.json. El diálogo de importación había anunciado proyecto y artifacts verificados.',
 'La función portable no permite recuperar los resultados existentes en el destino y el mensaje de éxito oculta esa pérdida de disponibilidad.',
 'project_bundles copia referencias directas y cambia su ubicación, pero no preserva ni resuelve el grafo transitivo anclado en cada run.json.',
 ['p53-native4t-bundle-export','p54-native4t-bundle-import-notice','p55-native4t-bundle-import-results'],
 ['motorsim/desktop/project_bundles.py','motorsim/desktop/four_stroke_artifacts.py','motorsim/desktop/app.py'],
 'BACKEND_APLICACION+FRONTEND','Exportación/importación portables con cierre transitivo y evaluación semántica de disponibilidad antes de declarar éxito.',
 ['Incluir manifiesto primario, configuración, resumen y traza cuando exista, preservando sus bytes y hashes originales.',
  'Importar en otra raíz sin acceso a la raíz original conserva las clasificaciones e integridad de cada corrida.',
  'Una dependencia faltante se explica por corrida; no se anuncia éxito íntegro ni se promueve evidencia legacy.'],
 'Roundtrip de bundles nativos completos, incompletos y legacy en un entorno que sólo permite leer la extracción; verificar todos los hashes y abrir las trazas. Usar versión nueva del contrato de bundle si cambia.',
 dependencies=()),
finding(3,'P0','Defecto funcional','Guardar un proyecto nativo importado falla sin aviso visible',
 'Después de importar el bundle, context.path era str. Pulsar Guardar produjo AttributeError: str object has no attribute suffix en app.py. La interfaz tenía tres referencias y el archivo seguía con dos; dirty permaneció true. No apareció un diálogo de error.',
 'El usuario no puede persistir las modificaciones mediante Guardar y puede cerrar creyendo que la operación se completó.',
 '_save_native_project usa context.path como Path antes del try. import_bundle devuelve project_path como str y replace_project conserva ese tipo.',
 ['p55-native4t-bundle-import-results','p66-native4t-save-after-bundle-import'],
 ['motorsim/desktop/app.py','motorsim/desktop/context.py','motorsim/desktop/project_bundles.py'],
 'BACKEND_APLICACION+FRONTEND','Guardar funciona después de todas las rutas de apertura/importación y sus fallos tienen respuesta visible.',
 ['Normalizar rutas en una frontera de aplicación sin cambiar el esquema científico.',
  'Guardar después de importar escribe el proyecto esperado y limpia dirty sólo tras éxito.',
  'Un fallo de permisos o I/O mantiene el borrador y ofrece Guardar como/diagnóstico.'],
 'Abrir/importar con str y Path, editar y pulsar Guardar; reabrir y verificar contenido. Repetir con escritura denegada y comprobar aviso visible.'),
finding(4,'P1','Inconsistencia entre módulos','El contexto activo desaparece en los espacios nativos de ejecución y resultados',
 '2T conserva proyecto, variante y estado en la cabecera. En nativo, la lista de variantes sólo se ve en MODELO y desaparece al simular o analizar. La barra de título del sistema conserva parte del proyecto, pero el cuerpo de la aplicación no mantiene ese contexto.',
 'Es más difícil saber qué variante se ejecuta o qué resultado corresponde al modelo actual.',
 'La cabecera ContextBar es exclusiva de 2T; los adaptadores 4T usan banners distintos.',
 ['p02-2t-cylinder','p14-native4t-variant-context','p16-native4t-running','p20-native4t-results-timeout'],
 ['motorsim/desktop/app.py','motorsim/desktop/widgets/context_bar.py','motorsim/desktop/native_four_stroke_workspace.py'],
 'FRONTEND','Cabecera persistente con proyecto, tipo de modelo, variante, revisión aplicada y estado de guardado.',
 ['La misma estructura permanece en Modelo, Simular, Corridas, Resultados y Comparar.',
  'Seleccionar un resultado histórico muestra su revisión junto al modelo actual y señala diferencias.',
  'El 4T de referencia nunca se presenta como el mismo núcleo que el nativo.'],
 'Recorrido de las tres modalidades, dos variantes y un resultado anterior; capturas con identidades largas en 980×680 y 1360×860.',dependencies=('UX-001',)),
finding(5,'P1','Inconsistencia entre módulos','4T 0D duplica navegación y acciones de proyecto',
 'En 4T 0D coexisten MODELO/SIMULAR/RESULTADOS con Diseño 4T/Resultados 4T/Curva RPM 4T, además de Volver a 2T y Nuevo/Abrir/Guardar 4T dentro del módulo. Ejecutar sigue visible en Resultados.',
 'El usuario debe aprender qué sistema de navegación controla cada área y qué botón opera sobre cada proyecto.',
 'El shell de referencia anterior se incrustó dentro del shell común conservando sus controles.',
 ['p09-reference4t-model','p10-reference4t-simulation','p11-reference4t-results-empty','p57-reference4t-converged-result'],
 ['motorsim/desktop/app.py','motorsim/desktop/four_stroke_workspace.py','motorsim/desktop/four_stroke_curve.py'],
 'FRONTEND','Un recorrido común con capacidades explícitas por modelo y herramientas de referencia en un espacio identificado.',
 ['Una sola navegación principal y una sola acción de proyecto por operación.',
  'Abrir un proyecto 0D conserva su contrato y lo identifica como referencia sintética.',
  'Los accesos existentes tienen equivalentes localizables y conservan atajos adecuados.'],
 'Comparar mapas de navegación y completar los mismos objetivos en 2T, nativo y referencia, sin convertir archivos entre modelos.',dependencies=('UX-004',)),
finding(6,'P1','Confusión o dificultad de uso','El editor nativo expone el esquema como formulario principal',
 'El modelo nativo se presenta como pestañas de tablas con rutas de parámetros, procedencia repetida y valores de texto libre. La creación 4T solicita nombres y deriva el resto a una plantilla sintética; el usuario debe descubrir después cómo completar el motor.',
 'Configurar un motor real requiere interpretar estructura de datos y dependencias que el frontend debería explicar.',
 'FourStrokeConfigEditor genera filas recorriendo escalares del documento y usa su esquema como organización de pantalla.',
 ['p05-native4t-model','p12-native4t-compact','p30-new-project-native4t'],
 ['motorsim/desktop/four_stroke_desktop.py','motorsim/desktop/new_engine_dialog.py','motorsim/desktop/native_four_stroke_workspace.py'],
 'FRONTEND','Editores por componente con magnitudes, unidades, selección tipada y procedencia contextual; el esquema queda en una vista avanzada.',
 ['Geometría, válvulas, conductos y operación tienen controles adecuados y ayuda de convenciones.',
  'Los datos ausentes no se presentan como mediciones y la plantilla sintética permanece identificada.',
  'Los valores no editados preservan exactamente su representación científica de origen.'],
 'Introducir un motor desde una ficha de medidas y revisar no-op Apply, precisión, unidades, claves opcionales y errores de dependencias.',dependencies=('UX-001','UX-004')),
finding(7,'P1','Confusión o dificultad de uso','La validación nativa devuelve errores de conversión sin ubicación útil',
 'Una entrada numérica incompleta produjo could not convert string to float: en un mensaje de advertencia. La configuración aplicada se conservó, pero el aviso no identificó la sección/celda ni indicó cómo corregirla. El rechazo geométrico 2T sí explicó la relación biela/carrera.',
 'La protección funciona, pero la recuperación del error exige buscar la celda y comprender una excepción de Python.',
 'El editor muestra str(exc) en un QMessageBox; no mantiene un resumen navegable de errores por campo.',
 ['p13-native4t-invalid-input','p32-2t-invalid-geometry'],
 ['motorsim/desktop/four_stroke_desktop.py','motorsim/desktop/engine_page.py'],
 'FRONTEND','Errores locales en español, con campo, unidad, motivo y acción; detalle técnico desplegable.',
 ['El foco vuelve a la celda inválida y el valor no se aplica.',
  'Un resumen enlaza todos los errores de la transacción sin ocultar otros campos.',
  'Se preservan los criterios de validación existentes.'],
 'Ingresar texto incompleto, NaN, negativos y una dependencia inválida; comprobar foco, mensaje y configuración aplicada intacta.',dependencies=('UX-006',)),
finding(8,'P1','Problema de visualización','La guía inicial tiene texto claro sobre fondo blanco',
 'La guía y la tabla de primeros pasos se renderizaron con fondo blanco y texto muy claro en la aplicación real con Qt 6.11.2, dificultando su lectura.',
 'La ayuda destinada a resolver la primera experiencia es difícil de leer justo cuando más se necesita.',
 'La regla global QWidget aplica texto claro, pero QTextBrowser conserva un fondo de documento blanco.',
 ['p56-onboarding-native-context'],
 ['motorsim/desktop/theme.py','motorsim/desktop/onboarding.py','motorsim/desktop/product.py'],
 'FRONTEND','Paleta coherente de documentos y controles de ayuda con contraste suficiente.',
 ['Guía y verificaciones se leen en temas/os soportados; texto normal objetivo ≥4,5:1.',
  'Tablas HTML, vínculos, selección y foco conservan contraste.',
  'La corrección cubre About y otros QTextBrowser sin cambiar el contenido científico.'],
 'Renderizar con el Qt fijado, medir colores reales de texto/fondo y revisar capturas de guía, About y diagnósticos.'),
finding(9,'P1','Defecto funcional','Primeros pasos mezcla el proyecto 2T con el contexto nativo',
 'Con el proyecto nativo activo, la tabla de la guía informó identidad audit-2t, familia 4T y resultado listo. Los resultados 2T cargados pueden satisfacer la verificación aunque los nativos importados estén no disponibles.',
 'La guía puede orientar al usuario sobre el proyecto equivocado y afirmar disponibilidad que no corresponde al contexto activo.',
 'first_steps_status toma project desde window.context y calcula result_ready acumulando resultados de varias modalidades.',
 ['p55-native4t-bundle-import-results','p56-onboarding-native-context'],
 ['motorsim/desktop/onboarding.py','motorsim/desktop/app.py'],
 'FRONTEND','La verificación usa exclusivamente el contexto y la selección activos.',
 ['Nombre, familia y disponibilidad pertenecen al mismo proyecto/revisión.',
  'Un resultado de otra familia no activa el paso de resultados.',
  'No disponible, legacy, parcial y periódico se describen sin equivalencia científica.'],
 'Alternar tres proyectos con disponibilidad distinta y abrir la guía en cada uno; comprobar identidad y estado.',dependencies=('UX-004',)),
finding(10,'P1','Funcionalidad poco visible','La corrida 2T terminada no conduce directamente a su resultado',
 'Tras completar un ciclo, la barra mostró terminación y checkpoint. RESULTADOS siguió sin corrida seleccionada. Fue necesario abrir Variantes y corridas, seleccionar el historial y abrir la corrida para cargar los datos.',
 'El usuario puede concluir que no se generaron resultados o buscar archivos del repositorio para encontrarlos.',
 'La finalización, el historial y el conjunto de resultados seleccionados son estados distintos sin una acción contextual directa.',
 ['p38-2t-terminal','p39-2t-results','p40-2t-history-discovery','p42-2t-loaded-nonconverged'],
 ['motorsim/desktop/execution_page.py','motorsim/desktop/app.py','motorsim/desktop/widgets/run_history.py','motorsim/desktop/results_page.py'],
 'FRONTEND','Toda corrida terminal ofrece Ver resultado, inspeccionar motivo y acciones siguientes.',
 ['Ver resultado abre la corrida exacta aun si no convergió.',
  'La carga asíncrona tiene estado visible y un error recuperable.',
  'La curva sigue excluyendo valores no periódicos y explica ese filtro.'],
 'Terminar, cancelar y agotar presupuesto en un punto 2T; abrir cada resultado desde su tarjeta sin buscar rutas.',dependencies=('UX-004',)),
finding(11,'P1','Flujo incompleto','El bundle 2T puede omitir el resultado que está en pantalla sin anticiparlo',
 'Después de abrir el resultado real de un ciclo, el proyecto tenía cero result_references. Exportar bundle produjo sólo proyecto, manifiesto y README: cero archivos de resultados. El diálogo anunció artifacts referenciados sin mostrar qué quedó fuera.',
 'Compartir el proyecto puede dejar fuera el trabajo recién realizado; el usuario no ve la diferencia entre cargado y vinculado.',
 'La selección de resultados no implica su asociación al proyecto y la exportación no presenta una previsualización de contenido.',
 ['p42-2t-loaded-nonconverged','p44-2t-bundle-export-notice'],
 ['motorsim/desktop/project_bundles.py','motorsim/desktop/context.py','motorsim/desktop/results_page.py','motorsim/desktop/app.py'],
 'FRONTEND+BACKEND_APLICACION','Asociación explícita de corridas al proyecto y resumen del contenido portable antes de exportar.',
 ['El usuario distingue resultado seleccionado, vinculado y externo.',
  'La exportación lista cantidades, tamaño, dependencias faltantes y resultados excluidos.',
  'Vincular no cambia configuración, hashes ni nivel de evidencia del resultado.'],
 'Ejecutar→abrir→vincular→guardar→exportar→importar un punto 2T; contrastar selección, manifiesto y disponibilidad.',dependencies=('UX-002','UX-004','UX-010')),
finding(12,'P1','Confusión o dificultad de uso','Las curvas RPM se preparan de tres formas y el coste agregado no siempre es visible',
 '2T usa un diálogo con presupuestos por punto y total; nativo usa una pestaña con tiempo/punto y sin total visible; referencia tiene su propia pestaña y límites. El formulario nativo inicial proponía 1000–13000, paso 500 y 120 s/punto: 25 puntos y hasta 3000 s presupuestados, sin incluir overhead; esto no es una predicción de duración.',
 'Es difícil comparar alcances, anticipar costes o entender dónde configurar una curva según el modelo.',
 'Cada familia dispone de un preparador independiente sin un resumen común de plan/capacidades.',
 ['p04-2t-simulation','p07-native4t-curve','p45-2t-curve-setup','p46-reference4t-curve-setup'],
 ['motorsim/desktop/execution_page.py','motorsim/desktop/native_four_stroke_curve.py','motorsim/desktop/four_stroke_curve.py'],
 'FRONTEND+BACKEND_APLICACION','Preparador común de punto/curva con plan explícito y controles adaptados a capacidades existentes.',
 ['Mostrar lista/cantidad de RPM, ciclos, presupuesto por punto, total y estimación si existe evidencia comparable.',
  'Distinguir presupuesto máximo, tiempo transcurrido y estimación desconocida.',
  'Mantener dominios, CFL, tolerancias y políticas de reanudación de cada núcleo.'],
 'Preparar rangos válidos e inválidos en cada modelo, verificar la lista exacta y cancelar antes de ejecutar; probar un barrido breve autorizado.',dependencies=('UX-004','UX-005')),
finding(13,'P1','Funcionalidad faltante','La cola de trabajos disponible sólo cubre curvas de referencia 4T 0D',
 'La cola CP1 se localiza dentro de Curva RPM 4T 0D y permite agregar curvas de esa referencia. No equivale a una cola general de trabajos 2T y nativos. Se probó agregar un ítem; no se ejecutó la cola.',
 'Una tarea habitual de preparación necesita organizar variantes/puntos en varios flujos, sin cambiar de aplicación o lanzar manualmente cada uno.',
 'FourStrokeBatchQueue está ligada al contexto 0D y no existe un registro de trabajos común con adaptadores por capacidad.',
 ['p48-reference4t-queue-empty','p49-reference4t-queue-added','p07-native4t-curve','p45-2t-curve-setup'],
 ['motorsim/desktop/batch_queue.py','motorsim/desktop/execution_page.py','motorsim/desktop/native_four_stroke_curve.py'],
 'BACKEND_APLICACION+FRONTEND','Cola común de trabajos con identidad de modelo y capacidades explícitas; extensión propuesta, no incumplimiento del alcance CP1 0D.',
 ['Los trabajos fijan configuración/revisión antes de salir de pendiente.',
  'Cancelar, reintentar pendientes y reanudar checkpoint son acciones distintas.',
  'El nativo no promete reinicio exacto y la cola no altera simultáneamente un proyecto en ejecución.'],
 'Pruebas del scheduler por adaptador y UAT de dos trabajos por modalidad con presupuesto/cancelación; sin mezclar resultados de familias.',dependencies=('UX-001','UX-012'),kind='PROPUESTA_BASADA_EN_ALCANCE_OBSERVADO'),
finding(14,'P1','Flujo incompleto','La comparación requiere descubrir por separado pares, contexto y cambios de diseño',
 '2T y nativo presentan mecanismos distintos. Con una sola corrida nativa, Comparar permite intentar el mismo extremo y después pide elegir dos diferentes. Existe una guía, pero no una preparación de par que explique anticipadamente elegibilidad y diferencia de configuración. La comparación 0D no debe inventarse por uniformidad visual.',
 'El usuario puede perder tiempo buscando pares utilizables o interpretar diferencias sin conocer sus condiciones.',
 'Selección de corridas, diferencias geométricas y contratos de comparación se exponen como controles separados.',
 ['p22-native4t-comparison-ineligible','p59-2t-comparison-state','p67-2t-variant-management'],
 ['motorsim/desktop/results_page.py','motorsim/desktop/four_stroke_desktop.py','motorsim/desktop/four_stroke_comparison.py','motorsim/desktop/legacy_ux.py'],
 'FRONTEND+BACKEND_APLICACION','Constructor de comparación A/B guiado con explicación de elegibilidad y vínculo a cambios de configuración.',
 ['Mostrar familia/núcleo, RPM, configuración, estado e incompatibilidades antes de calcular.',
  'Separar diferencia geométrica, diferencia transitoria y comparación admitida por el contrato.',
  'No habilitar ganancias entre familias ni promover legacy o no convergidos.'],
 'Pares idénticos, incompatibles, legacy, no periódicos y válidos; comprobar que la UI explica el rechazo y mantiene los contratos.',dependencies=('UX-004','UX-010')),
finding(15,'P2','Funcionalidad faltante','Falta una vista de motor coordinada con el editor de componentes',
 '2T ya tiene un esquema de cilindro y un perfil de escape útiles. No forman un mapa de sistema que conecte cilindro, cárter, admisión, transferencias y escape con el componente editado; nativo depende de tablas.',
 'La estructura física y las dependencias son más difíciles de comprender para un usuario nuevo.',
 'Los diagramas existentes son widgets locales sin un modelo de selección compartido.',
 ['p02-2t-cylinder','p03-2t-exhaust','p05-native4t-model'],
 ['motorsim/desktop/model_diagrams.py','motorsim/desktop/engine_page.py','motorsim/desktop/exhaust_page.py','motorsim/desktop/four_stroke_desktop.py'],
 'FRONTEND','Mapa esquemático seleccionable con convenciones físicas y límites del modelo visibles.',
 ['Seleccionar un componente en el árbol o diagrama sincroniza el inspector.',
  'El esquema se identifica como esquemático cuando no representa dimensiones reales.',
  '2T y 4T muestran sus componentes propios; 0D no aparenta resolver una geometría que no modela.'],
 'Evaluación con tareas de localizar y modificar un componente, sin cambiar el documento al seleccionar.',dependencies=('UX-004','UX-006'),kind='PROPUESTA_BASADA_EN_OBSERVACION'),
finding(16,'P2','Funcionalidad faltante','Inspección gráfica avanzada insuficiente para explorar muestras exactas',
 'Las vistas permiten trazas y selección de puntos en algunos gráficos. CurvePlot implementa selección por clic, pero no un sistema común de zoom y cursor enlazado entre tabla, presión y eventos. La propuesta amplía esas interacciones; no declara que todos los gráficos actuales carezcan de selección.',
 'Comparar fase, amplitud y eventos requiere pasar manualmente entre tablas y gráficos.',
 'Hay implementaciones gráficas locales sin un contrato compartido de interacción.',
 ['p58-2t-pressure-traces','p57-reference4t-converged-result','p25-native4t-curve-terminal'],
 ['motorsim/desktop/plot.py','motorsim/desktop/four_stroke_results.py','motorsim/desktop/results_page.py'],
 'FRONTEND','Zoom, restauración de escala y cursor de muestra enlazado, con unidades y puntos ausentes explícitos.',
 ['El cursor muestra la muestra discreta y su índice sin inventar interpolaciones.',
  'Se conservan las convenciones 360°/720° y los períodos del artefacto.',
  'Los gaps de puntos no admitidos no se unen ni se convierten en ceros.'],
 'Comparar valores de cursor con el CSV primario y verificar gaps, escalas y exportación.',dependencies=('UX-014',),kind='PROPUESTA_BASADA_EN_OBSERVACION_Y_CODIGO'),
finding(17,'P2','Confusión o dificultad de uso','Los términos técnicos y los ejes de confianza necesitan una presentación común',
 'La UI combina EXPLORATORY, VERIFIED, NOT_VALIDATED, DINO4T_API_V1, límite de pared, auditoría e integridad. Los resultados 2T sí identifican los transitorios, y los legacy se conservan como no verificados. Esas distinciones correctas aparecen con organización y vocabulario diferentes.',
 'El usuario debe aprender códigos internos para interpretar si terminó el cálculo, convergió, conserva integridad o fue validado físicamente.',
 'Se reutilizan códigos y textos técnicos como contenido principal en varios módulos.',
 ['p04-2t-simulation','p16-native4t-running','p42-2t-loaded-nonconverged','p62-native4t-legacy-results'],
 ['motorsim/desktop/presentation.py','motorsim/desktop/results_page.py','motorsim/desktop/four_stroke_desktop.py','motorsim/desktop/app.py'],
 'FRONTEND','Cuatro indicadores separados: ejecución, periodicidad, integridad y validación científica, con detalle técnico disponible.',
 ['Integridad verificada nunca se rotula como validación experimental.',
  'Se muestran unidades de potencia, presión y par junto a cada valor y cualquier conversión es explícita.',
  'Un resultado incompleto explica qué se puede inspeccionar y qué comparación queda bloqueada.'],
 'Revisar casos vacío, convergido, no convergido, cancelado, incompleto, legacy y no disponible en las tres modalidades.',dependencies=('UX-004',)),
finding(18,'P2','Problema de visualización','Los diseños compactos requieren redistribuir contenido y navegación',
 'En 980×680 el editor nativo dedica una columna amplia a variantes y oculta secciones tras flechas de pestañas. En 2T se comprimen contexto, controles y área de análisis; incluso a 1360 la etiqueta Baseline queda truncada. Las ventanas sí aceptaron el tamaño solicitado.',
 'Los usuarios con portátil tienen menos espacio útil y mayor esfuerzo para descubrir campos y acciones.',
 'Anchuras, pestañas horizontales y barras persistentes compiten sin reglas de prioridad suficientes.',
 ['p12-native4t-compact','p60-2t-results-compact','p02-2t-cylinder'],
 ['motorsim/desktop/app.py','motorsim/desktop/widgets/context_bar.py','motorsim/desktop/native_four_stroke_workspace.py','motorsim/desktop/results_page.py'],
 'FRONTEND','Paneles colapsables y prioridad de acciones con desplazamiento predecible.',
 ['En 980×680 se alcanzan edición, aplicar, ejecutar, cancelar y exportar sin controles fuera de pantalla.',
  'En 1360×860 se mantienen gráfico y contexto legibles.',
  'Verificar 100/125/150% en implementación; esta auditoría no acredita esos tres DPI.'],
 'Matriz de tamaños/DPI, navegación por teclado y captura sin modificar tipografía del sistema para ocultar problemas.',dependencies=('UX-004','UX-005','UX-006')),
finding(19,'P2','Confusión o dificultad de uso','La decisión de recuperación carece de identidad y previsualización',
 'La recuperación como copia funcionó y preservó el archivo original. El aviso preguntó por un borrador de 2T sin mostrar nombre, fecha, ruta original, diferencias o lista de borradores. Se observó además la secuencia de avisos por familia.',
 'Ante varios trabajos, el usuario tiene poca información para decidir qué recuperar o descartar.',
 '_offer_recovery elige la entrada más reciente y presenta una pregunta genérica por familia.',
 ['p65-recovered-2t-copy','p68-recovery-decision'],
 ['motorsim/desktop/app.py','motorsim/desktop/product.py'],
 'FRONTEND','Selector de recuperación con contexto, fecha, origen y opción de posponer.',
 ['Mostrar todos los borradores con familia/núcleo inequívocos y selección explícita.',
  'Recuperar conserva la semántica de copia sin ruta del original.',
  'Descartar requiere identificar qué copia se elimina; posponer no la borra.'],
 'Dos borradores de una familia y uno de otra, recuperación como copia y hash del original intacto.',dependencies=('UX-004',)),
finding(20,'P2','Funcionalidad faltante','Falta una aceptación de accesibilidad de los recorridos completos',
 'Se registró una secuencia real de doce Tab y nombres accesibles de controles. Eso no sustituye una prueba con lector de pantalla, alto contraste o entrada sólo por teclado. El inventario contiene controles sin nombre accesible explícito, lo cual por sí solo no demuestra que Qt no derive una etiqueta.',
 'La accesibilidad de tablas, editores y diálogos no está acreditada para usuarios con otras formas de interacción.',
 'No hay evidencia en esta auditoría de una aceptación asistiva integral por familia.',
 ['p69-keyboard-focus','p56-onboarding-native-context'],
 ['motorsim/desktop/app.py','motorsim/desktop/four_stroke_desktop.py','motorsim/desktop/theme.py'],
 'FRONTEND','Recorridos de teclado y etiquetas semánticas verificadas con tecnología asistiva.',
 ['Crear/editar/ejecutar/cancelar/analizar/exportar son operables sin ratón.',
  'El lector anuncia magnitud, unidad, error y estado activo con foco visible.',
  'La información crítica no depende exclusivamente del color.'],
 'UAT con teclado y lector de pantalla en Windows; documentar derivación de etiquetas Qt y capturas de foco/alto contraste.',dependencies=('UX-008','UX-018'),kind='BRECHA_DE_VERIFICACION_Y_PROPUESTA'),
finding(21,'P2','Inconsistencia entre módulos','Las acciones de variantes no son equivalentes entre 2T y nativo',
 'El panel 2T ofrece crear, duplicar, renombrar, eliminar y comparar con base. El panel nativo muestra base, duplicar y eliminar; el renombrado no tiene un acceso equivalente.',
 'Administrar alternativas de diseño exige aprender dos recorridos y limita la organización del trabajo nativo.',
 'Cada workspace define sus propios botones aunque comparten capacidades de contexto.',
 ['p14-native4t-variant-context','p67-2t-variant-management'],
 ['motorsim/desktop/project_page.py','motorsim/desktop/native_four_stroke_workspace.py','motorsim/desktop/context.py'],
 'FRONTEND+BACKEND_APLICACION','Explorador común de variantes con operaciones y consecuencias explícitas.',
 ['Renombrar preserva o migra de forma trazable las asociaciones de resultados según el contrato existente.',
  'Eliminar no elimina los artifacts históricos y requiere confirmación contextual.',
  'Las operaciones no admitidas por 0D se explican en vez de simular capacidad.'],
 'Renombrar/eliminar una variante con resultados, guardar/reabrir y comprobar asociaciones y hashes.',dependencies=('UX-004',)),
finding(22,'P3','Problema de visualización','Terminología, puntuación y codificación tienen detalles inconsistentes',
 'La cola muestra PENDING/IDLE y un carácter de reemplazo; algunos diálogos usan Close y el botón PDF termina en punto mientras otros usan puntos suspensivos. Estos ejemplos se ven en la captura real, no sólo en la salida de terminal.',
 'Reduce la coherencia y la percepción de acabado del producto.',
 'Literales locales sin catálogo de terminología y un texto con codificación deteriorada en la cola.',
 ['p49-reference4t-queue-added','p56-onboarding-native-context','p43-2t-report-exported'],
 ['motorsim/desktop/batch_queue.py','motorsim/desktop/onboarding.py','motorsim/desktop/results_page.py'],
 'FRONTEND','Vocabulario español consistente con códigos originales disponibles en detalle técnico.',
 ['No hay caracteres de reemplazo visibles en los recorridos aceptados.',
  'Acciones que abren diálogo tienen una convención de puntuación uniforme.',
  'Los códigos persistidos de contratos no se traducen ni cambian.'],
 'Inventario de literales, revisión visual de diálogos y comprobación de serialización idéntica.'),
finding(23,'P3','Problema de visualización','La jerarquía visual dedica demasiado espacio a avisos repetidos',
 'Se repiten banners científicos, procedencia por grupo y textos de arquitectura mientras algunos editores dejan grandes áreas vacías. Los avisos necesarios compiten con el objetivo de la pantalla.',
 'La exploración visual es más lenta y las acciones principales tienen menos protagonismo.',
 'Cada módulo agrega su propia introducción y el tema no define niveles de información progresiva.',
 ['p02-2t-cylinder','p05-native4t-model','p04-2t-simulation'],
 ['motorsim/desktop/theme.py','motorsim/desktop/app.py','motorsim/desktop/four_stroke_desktop.py'],
 'FRONTEND','Jerarquía de objetivo, acción, estado y detalle técnico sin ocultar las limitaciones científicas.',
 ['El estado científico esencial permanece visible en todas las pantallas.',
  'Los detalles repetidos pasan a un inspector accesible, conservando su contenido.',
  'La acción principal y el siguiente paso se identifican sin leer el documento técnico completo.'],
 'Revisión de tareas con usuarios y comparación de capturas, después de cerrar los cambios de arquitectura.',dependencies=('UX-004','UX-005','UX-006','UX-017')),
]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args()
    DOC.mkdir(parents=True,exist_ok=True)
    evidence=OUT/'evidence';evidence.mkdir(parents=True,exist_ok=True)
    for source,target in [('interaction-journal.jsonl','interactions-pinned.jsonl'),
                          ('driver.stderr.log','driver-pinned.stderr.log'),
                          ('runtime-final.json','runtime-final.json')]:
        shutil.copy2(args.artifacts/source,evidence/target)
    counts=dict(Counter(f['priority'] for f in F))
    (OUT/'findings.json').write_text(json.dumps(dict(schema='DINO_FRONTEND_AUDIT_FINDINGS_V1',
        product_revision='d44305c24ec81d9b767305d319a660c0c034e5c9',counts=counts,findings=F),
        ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    intro='''# Diagnóstico UX/UI de Dino

Fecha: 2026-11-11. Producto observado: `d44305c24ec81d9b767305d319a660c0c034e5c9`.
Incluye CP0, CP1 y navegación unificada. Investigación de una sola persona/agente;
revisión final **SELF_REVIEW**, sin validación científica ni aceptación del producto.

## Evaluación

Conviene reorganizar profundamente la experiencia sobre los servicios existentes.
El shell común reúne tres flujos, pero todavía no ofrece un contexto ni un ciclo de
trabajo coherentes. Tres problemas P0 deben preceder a la reorganización: edición
nativa no aplicada, portabilidad de resultados y guardado después de importar.
Una corrección de colores por sí sola dejaría esos problemas intactos.

## Qué ya funciona y debe conservarse

- Crear y guardar un 2T, rechazar geometría inválida y deshacer/rehacer cambios.
- Perfil geométrico de escape 2T y vistas por componentes ya existentes.
- Un punto 2T de un ciclo produjo un resultado no convergido y checkpoint;
  las métricas lo identificaron como transitorio y la curva no lo convirtió en
  una prestación periódica.
- Una curva nativa fue cancelada y conservó su estado parcial; un punto nativo
  agotó el presupuesto con cero ciclos y no se presentó como prestación válida.
- Un punto 4T 0D terminó convergido y se mostró como referencia sintética.
- Un barrido 2T real de dos RPM conservó sus dos puntos no convergidos como
  curva parcial. Una curva 0D real de dos RPM convergió, se vinculó al proyecto
  y se restauró después de guardar/reabrir, siempre como referencia sintética.
- La importación legacy conservó su clasificación y no habilitó comparación verificada.
- La recuperación 2T abrió una copia con diámetro 57 y ruta None; el hash del
  archivo original permaneció intacto.
- El PDF 2T se generó desde un resultado real no convergido. Se comprobó su
  creación y flujo de UI; no se hizo auditoría tipográfica página por página.

Las conclusiones se basan en recorridos reales, inventarios de widgets y código.
Consulte [método y cobertura](metodologia.md), [rediseño](rediseño.md),
[backlog](backlog.md) y [prototipo navegable](wireframes.html).

## Prioridades

'''
    diagnosis=[intro, '| Prioridad | Hallazgos |\n|---|---|\n']
    diagnosis += [f'| {p} | {counts.get(p,0)} |\n' for p in ['P0','P1','P2','P3']]
    diagnosis.append('\n## Hallazgos detallados\n')
    backlog=['''# Backlog ejecutable de frontend y backend de aplicación

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
''']
    for item in F:
        diagnosis += [f"\n### {item['id']} · {item['priority']} · {item['title']}\n\n",
            f"**Categoría:** {item['category']}. **Base:** {item['evidence_type']}.\n\n",
            f"**Ubicación:** {', '.join('`'+x+'`' for x in item['components'])}.\n\n",
            f"**Observación:** {item['observation']}\n\n**Impacto:** {item['impact']}\n\n",
            f"**Causa probable:** {item['probable_cause']}\n\n**Evidencia:** "]
        diagnosis.append(', '.join(f'[{e}](../../results/frontend-audit-v1/captures/{e}.png)' for e in item['evidence'])+'.\n')
        backlog.append(f"| {item['id']} | {item['priority']} | {item['layer']} | {item['expected_outcome']} | {', '.join(item['dependencies']) or '—'} |\n")
    backlog.append('\n## Fichas de implementación\n')
    for item in F:
        backlog += [f"\n### {item['id']} · {item['priority']} · {item['title']}\n\n",
            f"**Problema:** {item['observation']}\n\n**Resultado esperado:** {item['expected_outcome']}\n\n",
            f"**Capa:** {item['layer']}. **Componentes:** {', '.join('`'+x+'`' for x in item['components'])}.\n\n",
            f"**Dependencias:** {', '.join(item['dependencies']) or 'Ninguna otra mejora de este backlog'}.\n\n",
            '**Criterios de aceptación:**\n\n']
        backlog += [f'- {criterion}\n' for criterion in item['acceptance']]
        backlog.append(f"\n**Verificación:** {item['verification']}\n")
    (DOC/'diagnostico.md').write_text(''.join(diagnosis),encoding='utf-8')
    (DOC/'backlog.md').write_text(''.join(backlog),encoding='utf-8')
    captures=[]
    for path in sorted((OUT/'captures').glob('*.png')):
        state=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        captures.append(dict(id=path.stem,path=path.relative_to(ROOT).as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size=state['size'],
            platform=state['platform'],
            qualification='PINNED_QT_6_11_2' if path.stem.startswith('p') else 'PRELIMINARY_QT_6_10_1_NOT_USED_FOR_FINDINGS'))
    (OUT/'evidence-index.json').write_text(json.dumps(dict(captures=captures,
        runtime_journal='results/frontend-audit-v1/evidence/interactions-pinned.jsonl',
        note='Screenshot and JSON inventories are actual source GUI observations. Preliminary captures and harness failures are not product findings.'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(findings=len(F),priorities=counts,captures=len(captures)),ensure_ascii=False))


if __name__=='__main__':main()
