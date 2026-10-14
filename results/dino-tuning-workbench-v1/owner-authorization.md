# DINO-ACTIVE — DINO_TUNING_WORKBENCH_V1

## Autorización del propietario

Autorizo desarrollar `DINO_TUNING_WORKBENCH_V1`, tomando como autoridad de diseño la propuesta de Claude Opus:

`DINO_COMMERCIAL_UX_BENCHMARK_PROPOSAL`

Repositorio: `E:\dino\Dino-active`

HEAD de referencia: `3f5ce5b173f8620d96593f921fe6e19f10eb584c`

Utilizar el HEAD local vigente. No descartar commits posteriores.

El objetivo es que Dino funcione como un banco de puesta a punto de motores 2T, inspirado en los flujos de EngMod2T, MOTA y WaveDyno, sin copiar literalmente sus interfaces.

Leer AGENTS.md y realizar únicamente las transiciones administrativas permitidas.

No modificar física, solver, malla, periodicidad, hard gates ni resultados científicos históricos.

## F0 — Preservar la auditoría y corregir defectos

Localizar y preservar antes de trabajar:

`%TEMP%\dino_bench\DINO_COMMERCIAL_UX_BENCHMARK_PROPOSAL.md`

Conservar las 15 capturas reales y las referencias comerciales en documentación durable. Registrar hashes.

Si la carpeta temporal ya no existe, utilizar el informe proporcionado por el propietario y no inventar evidencia.

Corregir los siete defectos identificados por Opus:

D1. Actualización de la lista de superposición al abrir otro proyecto.

D2. Resaltado real de los tramos geométricos modificados.

D3. Inconsistencia entre horizonte solicitado y presupuesto temporal. No elevar presupuestos automáticamente; advertir, estimar y permitir una decisión explícita dentro de los límites autorizados.

D4. Autoescala correcta de presión, sin forzar indebidamente el eje Y a cero. Mostrar unidades y distinguir presión absoluta de relativa cuando corresponda.

D5. Impedir que el artifact root predeterminado apunte al repositorio. Preservar los artifacts existentes y ofrecer una corrección de ubicación sin moverlos ni borrarlos silenciosamente.

D6. Aislar completamente la configuración Windows durante tests. No escribir claves de prueba en la configuración real del usuario.

D7. Unificar la identidad y el nombre visible de cada variante en todas las pantallas.

Investigar además el mensaje `Error calling Python override of QWidget::metric()`. Corregirlo si se reproduce y registrar su causa.

## F1 — Presentar el motor como una herramienta de ingeniería

Implementar una pantalla de construcción del motor orientada a componentes reales.

Priorizar cilindro, distribución, lumbreras, escape y combustión según las capacidades existentes.

Mostrar cilindrada y parámetros derivados mediante cálculos respaldados por el backend.

Visualizar la distribución en grados y sus dimensiones físicas. No crear conversiones inversas no verificadas.

Reorganizar el escape en una tabla única de tramos y estaciones, con perfil longitudinal a escala, longitudes, diámetros, ángulos y volúmenes calculados cuando los modelos existentes los soporten.

Toda modificación debe mostrar visualmente qué tramo cambió.

No permitir que una geometría puramente editable se presente como científicamente validada.

## F2 — Implementar la arquitectura B+

Crear una ventana principal con cuatro regiones coordinadas.

**Superior:** proyecto activo, variante activa, baseline seleccionada y estado de guardado.

**Izquierda:** construcción del motor, con Motor, Lumbreras, Escape y Combustión. Mostrar el estado de cada componente: válido, modificado, incompleto o erróneo.

**Derecha:** resultados siempre accesibles, con presión, flujo, ondas, métricas disponibles y diferencias respecto de la baseline.

**Inferior:** barra de simulación con RPM, horizonte, presupuesto, preflight, progreso y acciones permitidas.

Incluir un panel avanzado de Evidencia para hashes, provenance, conservación, auditorías, checkpoints y artifact root.

Conservar los controles científicos y fail-closed existentes, pero evitar que dominen el flujo habitual de uso.

La baseline debe poder seleccionarse explícitamente y permanecer visible.

No propagar automáticamente los cambios del motor base hacia las variantes.

No hacer depender la comparación de navegar manualmente entre archivos JSON.

## F3 — Unificar edición, simulación y resultados

El usuario debe poder modificar un escape, revisar las diferencias, preparar una simulación y consultar sus resultados sin recorrer múltiples pantallas independientes.

Al seleccionar una variante, actualizar coherentemente editor, geometría, simulación y resultados.

Mostrar el historial de corridas correspondiente a esa variante.

El usuario debe poder seleccionar una corrida existente y compararla contra la baseline sin abandonar el banco de trabajo.

Si las corridas tienen RPM, resolución de malla, combustible u otras condiciones diferentes, advertir que la comparación no aísla únicamente la modificación de escape.

Distinguir claramente:

- Resultado transitorio.
- Periodicidad no evaluada.
- Periodicidad identificada.
- Auditoría independiente.
- Conservación.
- Hard gates.
- Validación experimental inexistente.

No presentar potencia, torque ni BMEP cuando estén indefinidos.

Para horizontes insuficientes, mostrar anticipadamente qué resultados es razonable esperar, sin garantizar convergencia.

Política vigente: cada simulación requiere confirmación individual. No introducir colas automáticas ni seudobarridos RPM.

## F4 — Resultados comparativos de ingeniería

La zona principal de resultados debe funcionar incluso cuando todavía no haya curvas periódicas.

Priorizar inicialmente:

Presión de cilindro y escape, flujos, ondas y diferencias entre configuraciones.

Incorporar el mapa posición × ángulo utilizando únicamente observables reales. No inventar datos ni interpolar comparaciones temporales que exijan correspondencia exacta.

Mantener la curva de potencia y torque como una vista disponible cuando existan puntos admisibles, con marcadores para puntos inválidos, ausentes o no convergidos.

Agregar unidades, escalas apropiadas, leyendas y referencias visibles.

Evitar pantallas vacías: cuando un resultado no exista, explicar por qué y cuál sería el siguiente paso para obtenerlo.

No convertir resultados exploratorios en resultados VERIFIED.

## Políticas del propietario

No habilitar confirmación masiva de corridas.

No implementar seudobarridos RPM en este objetivo.

No introducir recomendaciones empíricas de puesta a punto como si fueran resultados del modelo físico.

Mostrar distribución en grados, conservando la edición geométrica validada.

Preservar `MotorSim.exe` y sus hashes.

Mantener separadas la UX de uso cotidiano y la evidencia científica obligatoria.

## Aceptación funcional

Evaluar el escenario de referencia utilizado por Opus:

Crear o abrir motor de ejemplo, seleccionar escape original, duplicarlo, cambiar la cámara de 180 a 200 mm, preparar una simulación, abrir resultados existentes, comparar con baseline y guardar.

Objetivo UX: realizar el recorrido aplicable en 12 acciones principales o menos y reducir los seis cambios de vista actuales, sin eliminar confirmaciones de seguridad ni ocultar pasos necesarios.

Verificar que el cambio geométrico sea visible, que la variante activa resulte inequívoca y que no se pierda el contexto entre edición y resultados.

Probar tanto código fuente como `Dino2T.exe` empaquetado.

Verificar 1360×900 y 980×680. Comprobar escalado 125 % y 150 % cuando el entorno real lo permita, diferenciándolo de simulaciones Qt.

Agregar tests de las correcciones D1–D7, persistencia, identidad, selección de baseline, comparación, límites de ejecución, configuración Windows aislada y errores de Qt.

No realizar campañas ni simulaciones costosas.

## Entrega

Implementar, probar y corregir el alcance completo de F0–F4.

Entregar la aplicación, capturas reales, recorrido comparativo antes/después, tests, documentación, paquete Windows TRIAL y límites pendientes.

Ejecutar OpenSpec strict y program_status check.

Preservar todos los artifacts históricos, la física y los gates científicos.

Respetar AGENTS.md y la prohibición de push. Mantener Ostacky fuera de los commits.

Clasificación final:

`DINO_TUNING_WORKBENCH_V1_READY`

o

`DINO_TUNING_WORKBENCH_V1_PARTIAL`

con blockers concretos.

No declarar READY solamente porque la aplicación abre: el recorrido de ingeniería debe haberse probado de extremo a extremo.