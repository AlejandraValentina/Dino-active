# Diagnóstico UX/UI de Dino

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

| Prioridad | Hallazgos |
|---|---|
| P0 | 3 |
| P1 | 11 |
| P2 | 7 |
| P3 | 2 |

## Hallazgos detallados

### UX-001 · P0 · Una edición nativa sin aplicar puede perderse y ejecutarse el modelo anterior

**Categoría:** Defecto funcional. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/native_four_stroke_workspace.py`, `motorsim/desktop/context.py`.

**Observación:** Se escribió 87 mm en el diámetro nativo, se confirmó la celda y se pasó a SIMULAR. La tabla mostraba 87, pero el contexto y la solicitud real del worker conservaron 86. No hubo advertencia de edición pendiente. Tras publicar el resultado, el editor volvió a mostrar 86.

**Impacto:** El usuario puede atribuir un resultado a una geometría que nunca se ejecutó y perder su edición.

**Causa probable:** Las celdas son un borrador sin estado propio. FourStrokeSimulation lee context.engine(); la notificación changed del resultado refresca el editor y reemplaza ese borrador.

**Evidencia:** [p26-native4t-unapplied-edit](../../results/frontend-audit-v1/captures/p26-native4t-unapplied-edit.png), [p27-native4t-unapplied-to-simulate](../../results/frontend-audit-v1/captures/p27-native4t-unapplied-to-simulate.png), [p28-native4t-run-with-unapplied-edit](../../results/frontend-audit-v1/captures/p28-native4t-run-with-unapplied-edit.png), [p52-native4t-draft-after-run](../../results/frontend-audit-v1/captures/p52-native4t-draft-after-run.png).

### UX-002 · P0 · El bundle nativo no transporta la cadena completa de resultados

**Categoría:** Defecto funcional. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/project_bundles.py`, `motorsim/desktop/four_stroke_artifacts.py`, `motorsim/desktop/app.py`.

**Observación:** El bundle nativo contenía project.json, manifest.json, README y dos resúmenes/dos run.json. Tras importarlo por la interfaz, las dos corridas antes verificables quedaron UNAVAILABLE: faltaba artifacts/artifacts/artifacts.json. El diálogo de importación había anunciado proyecto y artifacts verificados.

**Impacto:** La función portable no permite recuperar los resultados existentes en el destino y el mensaje de éxito oculta esa pérdida de disponibilidad.

**Causa probable:** project_bundles copia referencias directas y cambia su ubicación, pero no preserva ni resuelve el grafo transitivo anclado en cada run.json.

**Evidencia:** [p53-native4t-bundle-export](../../results/frontend-audit-v1/captures/p53-native4t-bundle-export.png), [p54-native4t-bundle-import-notice](../../results/frontend-audit-v1/captures/p54-native4t-bundle-import-notice.png), [p55-native4t-bundle-import-results](../../results/frontend-audit-v1/captures/p55-native4t-bundle-import-results.png).

### UX-003 · P0 · Guardar un proyecto nativo importado falla sin aviso visible

**Categoría:** Defecto funcional. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/app.py`, `motorsim/desktop/context.py`, `motorsim/desktop/project_bundles.py`.

**Observación:** Después de importar el bundle, context.path era str. Pulsar Guardar produjo AttributeError: str object has no attribute suffix en app.py. La interfaz tenía tres referencias y el archivo seguía con dos; dirty permaneció true. No apareció un diálogo de error.

**Impacto:** El usuario no puede persistir las modificaciones mediante Guardar y puede cerrar creyendo que la operación se completó.

**Causa probable:** _save_native_project usa context.path como Path antes del try. import_bundle devuelve project_path como str y replace_project conserva ese tipo.

**Evidencia:** [p55-native4t-bundle-import-results](../../results/frontend-audit-v1/captures/p55-native4t-bundle-import-results.png), [p66-native4t-save-after-bundle-import](../../results/frontend-audit-v1/captures/p66-native4t-save-after-bundle-import.png).

### UX-004 · P1 · El contexto activo desaparece en los espacios nativos de ejecución y resultados

**Categoría:** Inconsistencia entre módulos. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/app.py`, `motorsim/desktop/widgets/context_bar.py`, `motorsim/desktop/native_four_stroke_workspace.py`.

**Observación:** 2T conserva proyecto, variante y estado en la cabecera. En nativo, la lista de variantes sólo se ve en MODELO y desaparece al simular o analizar. La barra de título del sistema conserva parte del proyecto, pero el cuerpo de la aplicación no mantiene ese contexto.

**Impacto:** Es más difícil saber qué variante se ejecuta o qué resultado corresponde al modelo actual.

**Causa probable:** La cabecera ContextBar es exclusiva de 2T; los adaptadores 4T usan banners distintos.

**Evidencia:** [p02-2t-cylinder](../../results/frontend-audit-v1/captures/p02-2t-cylinder.png), [p14-native4t-variant-context](../../results/frontend-audit-v1/captures/p14-native4t-variant-context.png), [p16-native4t-running](../../results/frontend-audit-v1/captures/p16-native4t-running.png), [p20-native4t-results-timeout](../../results/frontend-audit-v1/captures/p20-native4t-results-timeout.png).

### UX-005 · P1 · 4T 0D duplica navegación y acciones de proyecto

**Categoría:** Inconsistencia entre módulos. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/app.py`, `motorsim/desktop/four_stroke_workspace.py`, `motorsim/desktop/four_stroke_curve.py`.

**Observación:** En 4T 0D coexisten MODELO/SIMULAR/RESULTADOS con Diseño 4T/Resultados 4T/Curva RPM 4T, además de Volver a 2T y Nuevo/Abrir/Guardar 4T dentro del módulo. Ejecutar sigue visible en Resultados.

**Impacto:** El usuario debe aprender qué sistema de navegación controla cada área y qué botón opera sobre cada proyecto.

**Causa probable:** El shell de referencia anterior se incrustó dentro del shell común conservando sus controles.

**Evidencia:** [p09-reference4t-model](../../results/frontend-audit-v1/captures/p09-reference4t-model.png), [p10-reference4t-simulation](../../results/frontend-audit-v1/captures/p10-reference4t-simulation.png), [p11-reference4t-results-empty](../../results/frontend-audit-v1/captures/p11-reference4t-results-empty.png), [p57-reference4t-converged-result](../../results/frontend-audit-v1/captures/p57-reference4t-converged-result.png).

### UX-006 · P1 · El editor nativo expone el esquema como formulario principal

**Categoría:** Confusión o dificultad de uso. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/new_engine_dialog.py`, `motorsim/desktop/native_four_stroke_workspace.py`.

**Observación:** El modelo nativo se presenta como pestañas de tablas con rutas de parámetros, procedencia repetida y valores de texto libre. La creación 4T solicita nombres y deriva el resto a una plantilla sintética; el usuario debe descubrir después cómo completar el motor.

**Impacto:** Configurar un motor real requiere interpretar estructura de datos y dependencias que el frontend debería explicar.

**Causa probable:** FourStrokeConfigEditor genera filas recorriendo escalares del documento y usa su esquema como organización de pantalla.

**Evidencia:** [p05-native4t-model](../../results/frontend-audit-v1/captures/p05-native4t-model.png), [p12-native4t-compact](../../results/frontend-audit-v1/captures/p12-native4t-compact.png), [p30-new-project-native4t](../../results/frontend-audit-v1/captures/p30-new-project-native4t.png).

### UX-007 · P1 · La validación nativa devuelve errores de conversión sin ubicación útil

**Categoría:** Confusión o dificultad de uso. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/engine_page.py`.

**Observación:** Una entrada numérica incompleta produjo could not convert string to float: en un mensaje de advertencia. La configuración aplicada se conservó, pero el aviso no identificó la sección/celda ni indicó cómo corregirla. El rechazo geométrico 2T sí explicó la relación biela/carrera.

**Impacto:** La protección funciona, pero la recuperación del error exige buscar la celda y comprender una excepción de Python.

**Causa probable:** El editor muestra str(exc) en un QMessageBox; no mantiene un resumen navegable de errores por campo.

**Evidencia:** [p13-native4t-invalid-input](../../results/frontend-audit-v1/captures/p13-native4t-invalid-input.png), [p32-2t-invalid-geometry](../../results/frontend-audit-v1/captures/p32-2t-invalid-geometry.png).

### UX-008 · P1 · La guía inicial tiene texto claro sobre fondo blanco

**Categoría:** Problema de visualización. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/theme.py`, `motorsim/desktop/onboarding.py`, `motorsim/desktop/product.py`.

**Observación:** La guía y la tabla de primeros pasos se renderizaron con fondo blanco y texto muy claro en la aplicación real con Qt 6.11.2, dificultando su lectura.

**Impacto:** La ayuda destinada a resolver la primera experiencia es difícil de leer justo cuando más se necesita.

**Causa probable:** La regla global QWidget aplica texto claro, pero QTextBrowser conserva un fondo de documento blanco.

**Evidencia:** [p56-onboarding-native-context](../../results/frontend-audit-v1/captures/p56-onboarding-native-context.png).

### UX-009 · P1 · Primeros pasos mezcla el proyecto 2T con el contexto nativo

**Categoría:** Defecto funcional. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/onboarding.py`, `motorsim/desktop/app.py`.

**Observación:** Con el proyecto nativo activo, la tabla de la guía informó identidad audit-2t, familia 4T y resultado listo. Los resultados 2T cargados pueden satisfacer la verificación aunque los nativos importados estén no disponibles.

**Impacto:** La guía puede orientar al usuario sobre el proyecto equivocado y afirmar disponibilidad que no corresponde al contexto activo.

**Causa probable:** first_steps_status toma project desde window.context y calcula result_ready acumulando resultados de varias modalidades.

**Evidencia:** [p55-native4t-bundle-import-results](../../results/frontend-audit-v1/captures/p55-native4t-bundle-import-results.png), [p56-onboarding-native-context](../../results/frontend-audit-v1/captures/p56-onboarding-native-context.png).

### UX-010 · P1 · La corrida 2T terminada no conduce directamente a su resultado

**Categoría:** Funcionalidad poco visible. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/execution_page.py`, `motorsim/desktop/app.py`, `motorsim/desktop/widgets/run_history.py`, `motorsim/desktop/results_page.py`.

**Observación:** Tras completar un ciclo, la barra mostró terminación y checkpoint. RESULTADOS siguió sin corrida seleccionada. Fue necesario abrir Variantes y corridas, seleccionar el historial y abrir la corrida para cargar los datos.

**Impacto:** El usuario puede concluir que no se generaron resultados o buscar archivos del repositorio para encontrarlos.

**Causa probable:** La finalización, el historial y el conjunto de resultados seleccionados son estados distintos sin una acción contextual directa.

**Evidencia:** [p38-2t-terminal](../../results/frontend-audit-v1/captures/p38-2t-terminal.png), [p39-2t-results](../../results/frontend-audit-v1/captures/p39-2t-results.png), [p40-2t-history-discovery](../../results/frontend-audit-v1/captures/p40-2t-history-discovery.png), [p42-2t-loaded-nonconverged](../../results/frontend-audit-v1/captures/p42-2t-loaded-nonconverged.png).

### UX-011 · P1 · El bundle 2T puede omitir el resultado que está en pantalla sin anticiparlo

**Categoría:** Flujo incompleto. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/project_bundles.py`, `motorsim/desktop/context.py`, `motorsim/desktop/results_page.py`, `motorsim/desktop/app.py`.

**Observación:** Después de abrir el resultado real de un ciclo, el proyecto tenía cero result_references. Exportar bundle produjo sólo proyecto, manifiesto y README: cero archivos de resultados. El diálogo anunció artifacts referenciados sin mostrar qué quedó fuera.

**Impacto:** Compartir el proyecto puede dejar fuera el trabajo recién realizado; el usuario no ve la diferencia entre cargado y vinculado.

**Causa probable:** La selección de resultados no implica su asociación al proyecto y la exportación no presenta una previsualización de contenido.

**Evidencia:** [p42-2t-loaded-nonconverged](../../results/frontend-audit-v1/captures/p42-2t-loaded-nonconverged.png), [p44-2t-bundle-export-notice](../../results/frontend-audit-v1/captures/p44-2t-bundle-export-notice.png).

### UX-012 · P1 · Las curvas RPM se preparan de tres formas y el coste agregado no siempre es visible

**Categoría:** Confusión o dificultad de uso. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/execution_page.py`, `motorsim/desktop/native_four_stroke_curve.py`, `motorsim/desktop/four_stroke_curve.py`.

**Observación:** 2T usa un diálogo con presupuestos por punto y total; nativo usa una pestaña con tiempo/punto y sin total visible; referencia tiene su propia pestaña y límites. El formulario nativo inicial proponía 1000–13000, paso 500 y 120 s/punto: 25 puntos y hasta 3000 s presupuestados, sin incluir overhead; esto no es una predicción de duración.

**Impacto:** Es difícil comparar alcances, anticipar costes o entender dónde configurar una curva según el modelo.

**Causa probable:** Cada familia dispone de un preparador independiente sin un resumen común de plan/capacidades.

**Evidencia:** [p04-2t-simulation](../../results/frontend-audit-v1/captures/p04-2t-simulation.png), [p07-native4t-curve](../../results/frontend-audit-v1/captures/p07-native4t-curve.png), [p45-2t-curve-setup](../../results/frontend-audit-v1/captures/p45-2t-curve-setup.png), [p46-reference4t-curve-setup](../../results/frontend-audit-v1/captures/p46-reference4t-curve-setup.png).

### UX-013 · P1 · La cola de trabajos disponible sólo cubre curvas de referencia 4T 0D

**Categoría:** Funcionalidad faltante. **Base:** PROPUESTA_BASADA_EN_ALCANCE_OBSERVADO.

**Ubicación:** `motorsim/desktop/batch_queue.py`, `motorsim/desktop/execution_page.py`, `motorsim/desktop/native_four_stroke_curve.py`.

**Observación:** La cola CP1 se localiza dentro de Curva RPM 4T 0D y permite agregar curvas de esa referencia. No equivale a una cola general de trabajos 2T y nativos. Se probó agregar un ítem; no se ejecutó la cola.

**Impacto:** Una tarea habitual de preparación necesita organizar variantes/puntos en varios flujos, sin cambiar de aplicación o lanzar manualmente cada uno.

**Causa probable:** FourStrokeBatchQueue está ligada al contexto 0D y no existe un registro de trabajos común con adaptadores por capacidad.

**Evidencia:** [p48-reference4t-queue-empty](../../results/frontend-audit-v1/captures/p48-reference4t-queue-empty.png), [p49-reference4t-queue-added](../../results/frontend-audit-v1/captures/p49-reference4t-queue-added.png), [p07-native4t-curve](../../results/frontend-audit-v1/captures/p07-native4t-curve.png), [p45-2t-curve-setup](../../results/frontend-audit-v1/captures/p45-2t-curve-setup.png).

### UX-014 · P1 · La comparación requiere descubrir por separado pares, contexto y cambios de diseño

**Categoría:** Flujo incompleto. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/results_page.py`, `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/four_stroke_comparison.py`, `motorsim/desktop/legacy_ux.py`.

**Observación:** 2T y nativo presentan mecanismos distintos. Con una sola corrida nativa, Comparar permite intentar el mismo extremo y después pide elegir dos diferentes. Existe una guía, pero no una preparación de par que explique anticipadamente elegibilidad y diferencia de configuración. La comparación 0D no debe inventarse por uniformidad visual.

**Impacto:** El usuario puede perder tiempo buscando pares utilizables o interpretar diferencias sin conocer sus condiciones.

**Causa probable:** Selección de corridas, diferencias geométricas y contratos de comparación se exponen como controles separados.

**Evidencia:** [p22-native4t-comparison-ineligible](../../results/frontend-audit-v1/captures/p22-native4t-comparison-ineligible.png), [p59-2t-comparison-state](../../results/frontend-audit-v1/captures/p59-2t-comparison-state.png), [p67-2t-variant-management](../../results/frontend-audit-v1/captures/p67-2t-variant-management.png).

### UX-015 · P2 · Falta una vista de motor coordinada con el editor de componentes

**Categoría:** Funcionalidad faltante. **Base:** PROPUESTA_BASADA_EN_OBSERVACION.

**Ubicación:** `motorsim/desktop/model_diagrams.py`, `motorsim/desktop/engine_page.py`, `motorsim/desktop/exhaust_page.py`, `motorsim/desktop/four_stroke_desktop.py`.

**Observación:** 2T ya tiene un esquema de cilindro y un perfil de escape útiles. No forman un mapa de sistema que conecte cilindro, cárter, admisión, transferencias y escape con el componente editado; nativo depende de tablas.

**Impacto:** La estructura física y las dependencias son más difíciles de comprender para un usuario nuevo.

**Causa probable:** Los diagramas existentes son widgets locales sin un modelo de selección compartido.

**Evidencia:** [p02-2t-cylinder](../../results/frontend-audit-v1/captures/p02-2t-cylinder.png), [p03-2t-exhaust](../../results/frontend-audit-v1/captures/p03-2t-exhaust.png), [p05-native4t-model](../../results/frontend-audit-v1/captures/p05-native4t-model.png).

### UX-016 · P2 · Inspección gráfica avanzada insuficiente para explorar muestras exactas

**Categoría:** Funcionalidad faltante. **Base:** PROPUESTA_BASADA_EN_OBSERVACION_Y_CODIGO.

**Ubicación:** `motorsim/desktop/plot.py`, `motorsim/desktop/four_stroke_results.py`, `motorsim/desktop/results_page.py`.

**Observación:** Las vistas permiten trazas y selección de puntos en algunos gráficos. CurvePlot implementa selección por clic, pero no un sistema común de zoom y cursor enlazado entre tabla, presión y eventos. La propuesta amplía esas interacciones; no declara que todos los gráficos actuales carezcan de selección.

**Impacto:** Comparar fase, amplitud y eventos requiere pasar manualmente entre tablas y gráficos.

**Causa probable:** Hay implementaciones gráficas locales sin un contrato compartido de interacción.

**Evidencia:** [p58-2t-pressure-traces](../../results/frontend-audit-v1/captures/p58-2t-pressure-traces.png), [p57-reference4t-converged-result](../../results/frontend-audit-v1/captures/p57-reference4t-converged-result.png), [p25-native4t-curve-terminal](../../results/frontend-audit-v1/captures/p25-native4t-curve-terminal.png).

### UX-017 · P2 · Los términos técnicos y los ejes de confianza necesitan una presentación común

**Categoría:** Confusión o dificultad de uso. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/presentation.py`, `motorsim/desktop/results_page.py`, `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/app.py`.

**Observación:** La UI combina EXPLORATORY, VERIFIED, NOT_VALIDATED, DINO4T_API_V1, límite de pared, auditoría e integridad. Los resultados 2T sí identifican los transitorios, y los legacy se conservan como no verificados. Esas distinciones correctas aparecen con organización y vocabulario diferentes.

**Impacto:** El usuario debe aprender códigos internos para interpretar si terminó el cálculo, convergió, conserva integridad o fue validado físicamente.

**Causa probable:** Se reutilizan códigos y textos técnicos como contenido principal en varios módulos.

**Evidencia:** [p04-2t-simulation](../../results/frontend-audit-v1/captures/p04-2t-simulation.png), [p16-native4t-running](../../results/frontend-audit-v1/captures/p16-native4t-running.png), [p42-2t-loaded-nonconverged](../../results/frontend-audit-v1/captures/p42-2t-loaded-nonconverged.png), [p62-native4t-legacy-results](../../results/frontend-audit-v1/captures/p62-native4t-legacy-results.png).

### UX-018 · P2 · Los diseños compactos requieren redistribuir contenido y navegación

**Categoría:** Problema de visualización. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/app.py`, `motorsim/desktop/widgets/context_bar.py`, `motorsim/desktop/native_four_stroke_workspace.py`, `motorsim/desktop/results_page.py`.

**Observación:** En 980×680 el editor nativo dedica una columna amplia a variantes y oculta secciones tras flechas de pestañas. En 2T se comprimen contexto, controles y área de análisis; incluso a 1360 la etiqueta Baseline queda truncada. Las ventanas sí aceptaron el tamaño solicitado.

**Impacto:** Los usuarios con portátil tienen menos espacio útil y mayor esfuerzo para descubrir campos y acciones.

**Causa probable:** Anchuras, pestañas horizontales y barras persistentes compiten sin reglas de prioridad suficientes.

**Evidencia:** [p12-native4t-compact](../../results/frontend-audit-v1/captures/p12-native4t-compact.png), [p60-2t-results-compact](../../results/frontend-audit-v1/captures/p60-2t-results-compact.png), [p02-2t-cylinder](../../results/frontend-audit-v1/captures/p02-2t-cylinder.png).

### UX-019 · P2 · La decisión de recuperación carece de identidad y previsualización

**Categoría:** Confusión o dificultad de uso. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/app.py`, `motorsim/desktop/product.py`.

**Observación:** La recuperación como copia funcionó y preservó el archivo original. El aviso preguntó por un borrador de 2T sin mostrar nombre, fecha, ruta original, diferencias o lista de borradores. Se observó además la secuencia de avisos por familia.

**Impacto:** Ante varios trabajos, el usuario tiene poca información para decidir qué recuperar o descartar.

**Causa probable:** _offer_recovery elige la entrada más reciente y presenta una pregunta genérica por familia.

**Evidencia:** [p65-recovered-2t-copy](../../results/frontend-audit-v1/captures/p65-recovered-2t-copy.png), [p68-recovery-decision](../../results/frontend-audit-v1/captures/p68-recovery-decision.png).

### UX-020 · P2 · Falta una aceptación de accesibilidad de los recorridos completos

**Categoría:** Funcionalidad faltante. **Base:** BRECHA_DE_VERIFICACION_Y_PROPUESTA.

**Ubicación:** `motorsim/desktop/app.py`, `motorsim/desktop/four_stroke_desktop.py`, `motorsim/desktop/theme.py`.

**Observación:** Se registró una secuencia real de doce Tab y nombres accesibles de controles. Eso no sustituye una prueba con lector de pantalla, alto contraste o entrada sólo por teclado. El inventario contiene controles sin nombre accesible explícito, lo cual por sí solo no demuestra que Qt no derive una etiqueta.

**Impacto:** La accesibilidad de tablas, editores y diálogos no está acreditada para usuarios con otras formas de interacción.

**Causa probable:** No hay evidencia en esta auditoría de una aceptación asistiva integral por familia.

**Evidencia:** [p69-keyboard-focus](../../results/frontend-audit-v1/captures/p69-keyboard-focus.png), [p56-onboarding-native-context](../../results/frontend-audit-v1/captures/p56-onboarding-native-context.png).

### UX-021 · P2 · Las acciones de variantes no son equivalentes entre 2T y nativo

**Categoría:** Inconsistencia entre módulos. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/project_page.py`, `motorsim/desktop/native_four_stroke_workspace.py`, `motorsim/desktop/context.py`.

**Observación:** El panel 2T ofrece crear, duplicar, renombrar, eliminar y comparar con base. El panel nativo muestra base, duplicar y eliminar; el renombrado no tiene un acceso equivalente.

**Impacto:** Administrar alternativas de diseño exige aprender dos recorridos y limita la organización del trabajo nativo.

**Causa probable:** Cada workspace define sus propios botones aunque comparten capacidades de contexto.

**Evidencia:** [p14-native4t-variant-context](../../results/frontend-audit-v1/captures/p14-native4t-variant-context.png), [p67-2t-variant-management](../../results/frontend-audit-v1/captures/p67-2t-variant-management.png).

### UX-022 · P3 · Terminología, puntuación y codificación tienen detalles inconsistentes

**Categoría:** Problema de visualización. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/batch_queue.py`, `motorsim/desktop/onboarding.py`, `motorsim/desktop/results_page.py`.

**Observación:** La cola muestra PENDING/IDLE y un carácter de reemplazo; algunos diálogos usan Close y el botón PDF termina en punto mientras otros usan puntos suspensivos. Estos ejemplos se ven en la captura real, no sólo en la salida de terminal.

**Impacto:** Reduce la coherencia y la percepción de acabado del producto.

**Causa probable:** Literales locales sin catálogo de terminología y un texto con codificación deteriorada en la cola.

**Evidencia:** [p49-reference4t-queue-added](../../results/frontend-audit-v1/captures/p49-reference4t-queue-added.png), [p56-onboarding-native-context](../../results/frontend-audit-v1/captures/p56-onboarding-native-context.png), [p43-2t-report-exported](../../results/frontend-audit-v1/captures/p43-2t-report-exported.png).

### UX-023 · P3 · La jerarquía visual dedica demasiado espacio a avisos repetidos

**Categoría:** Problema de visualización. **Base:** OBSERVADO.

**Ubicación:** `motorsim/desktop/theme.py`, `motorsim/desktop/app.py`, `motorsim/desktop/four_stroke_desktop.py`.

**Observación:** Se repiten banners científicos, procedencia por grupo y textos de arquitectura mientras algunos editores dejan grandes áreas vacías. Los avisos necesarios compiten con el objetivo de la pantalla.

**Impacto:** La exploración visual es más lenta y las acciones principales tienen menos protagonismo.

**Causa probable:** Cada módulo agrega su propia introducción y el tema no define niveles de información progresiva.

**Evidencia:** [p02-2t-cylinder](../../results/frontend-audit-v1/captures/p02-2t-cylinder.png), [p05-native4t-model](../../results/frontend-audit-v1/captures/p05-native4t-model.png), [p04-2t-simulation](../../results/frontend-audit-v1/captures/p04-2t-simulation.png).
