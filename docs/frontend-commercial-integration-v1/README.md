# Integración controlada F0/F1 + CP0–CP2

Rama: `integration/dino-frontend-commercial-v1`.
Worktree nuevo: `dino-frontend-commercial-v1`, en E:.
Base: main `f97469b`; frontend aceptado en fuente `9b7392e`.

## Conflicto operativo

Único conflicto textual: `program-status.json`. El análisis a tres bandas contra
`d44305c` encontró cuatro claves divergentes: cola, progreso, objetivo y gate.
No hubo tareas compartidas con cambios semánticos contradictorios en ambos padres.
Se preservaron 577 tareas heredadas mediante unión por ID y cambios descendientes;
se conservaron los registros distintos de progreso y ambos objetivos/gates padre.
Se registró un objetivo nuevo de integración con ocho tareas. Los doce blockers
científicos heredados siguen fuera del alcance; el frontend no aporta sus datos
faltantes ni autoriza campañas postergadas.

Evidencia: `results/frontend-commercial-integration-v1/state-consolidation.json`.
Los padres del merge conservan los archivos originales completos. No se eligió
automáticamente una de las dos colas ni se reescribieron estados científicos.

## Estrategia de verificación

Regresión focal de frontend + CP0–CP2, contratos protegidos y reproducción
diferencial de fallos generales heredados. No se presenta un conjunto focal como
una suite general verde. Recorridos reales independientes de las tres familias
en fuente y en candidato empaquetado. Licencias de prueba usan secretos efímeros
en memoria y claves públicas inyectadas sólo en la aceptación; no son licencias
comerciales emitidas ni cambian las claves del producto.

Los recibos finales distinguirán fuente, ejecutable, regresión general, UAT humano
y validación científica. La integración y el candidato no se publican ni se
fusionan a main durante esta tarea.

## Compatibilidad funcional revisada

La fusión de `app.py` no produjo conflicto textual, pero la revisión y los
recorridos encontraron tres defectos de aplicación que requerían corrección:

| Problema | Corrección | Evidencia |
|---|---|---|
| El menú Licencia pasaba dos argumentos posicionales a un diálogo que admite un padre | Un único padre; prueba del callback real del shell | Tests nuevos y captura de licencia del candidato |
| Undo/redo podía cambiar el documento nativo o fallar en referencia mientras existía un worker | Acciones deshabilitadas y guardas del comando; notificaciones de ejecución actualizan su disponibilidad | Negativos con slot activo y recorrido de corrida real |
| Barrido nativo enviaba `progress` a una API que admite `on_progress` | Corregir exclusivamente el nombre del argumento en el adaptador | Regresión de firma estricta y corrida/cancelación reales |

El tercer defecto apareció en la repetición sobre fuente limpia: la primera
cancelación había ganado la carrera antes de llegar a la llamada defectuosa.
La aceptación limpia rechazó el resultado PARTIAL con dos TypeError; se conservó
ese incidente y se repitió el recorrido tras corregirlo. El nuevo CANCELLED
conserva un punto NOT_CONVERGED con WALL_LIMIT, sin promoverlo a curva periódica.
No hubo modificación del solver, sus opciones, tolerancias o contrato público.

Se agregó una ruta de aceptación de mantenedor que usa los mismos comandos y
widgets en fuente y en el ejecutable: `--verify-frontend-commercial`. La receta
normal de inicio y el comportamiento de las licencias comerciales se conservan.
Las interacciones automáticas, selectores de archivos sustituidos por rutas
aisladas y claves públicas efímeras de test se declaran en los recibos. El PDF
se genera desde el comando del producto; se suprime sólo el visor externo durante
la aceptación para no abrir otra aplicación del usuario.

## Verificación final de fuente

- Conjunto conjunto inicial: **95 PASS** de frontend y CP0–CP2.
- Tras corregir el callback nativo: **23 PASS** del contrato de transporte y
  regresiones relacionadas. Hay solapamiento entre conjuntos; no se suman como
  pruebas únicas.
- Contratos protegidos: **301 PASS, 3 SKIP**, con avisos NumPy heredados.
- Qt Windows sobre fuente limpia `8712f29`: **47 comprobaciones PASS** y 25
  capturas. Incluye un ciclo 2T real no convergido, punto nativo con diámetro
  aplicado de 87 mm, cancelación nativa, cola y punto de referencia 0D reales,
  guardado fallido/recuperación, transporte con origen inaccesible y reapertura.
- La comparación elegible usa endpoints sintéticos de presentación declarados;
  su función es comprobar el contrato y la interfaz, no una diferencia física
  nueva ni validación experimental.

`GENERAL_REGRESSION_NOT_GREEN` permanece vigente. Se reprodujeron cuatro fallos
de preregistro de preflight con los mismos mensajes en main `f97469b` y en esta
integración; los otros dos casos del subconjunto pasaron en ambos. La suite
general completa no se reejecutó como campaña: su informe histórico conserva
fallos adicionales. La ausencia de regresiones nuevas se limita a los conjuntos
relevantes ejecutados y al subconjunto diferencial documentado.

## Candidato Windows

Versión **0.1.0-rc13**, clasificación **INTERNAL_ENGINEERING_CANDIDATE**.
Commit de fuente/build limpio: `8712f290ff7c1485cd0417101426aa4e80fc5205`.
Los commits posteriores de evidencia no cambian los bytes de aplicación de ese
commit. El build usa Python 3.11.0 y las versiones fijadas en
`packaging/requirements-build.txt`, con distribución, caché y temporales propios
en E:. Las dependencias existentes se leyeron mediante un junction local
`.venv-build`; no se instalaron ni actualizaron paquetes del entorno compartido.

El manifiesto enumera 290 entradas de repositorio y entradas explícitas de
licencias/dependencias con hashes. Se comprobó el SHA-256 del manifiesto, del ZIP,
de los tres ejecutables y la igualdad de once módulos críticos empaquetados con
la fuente, incluidos formularios F0/F1, portabilidad, callback nativo, CP2 y
launcher. El candidato no contiene archivos de licencia emitida ni claves
privadas de los tests. Las claves públicas del proveedor no se modificaron.

La receta permite reproducir la construcción a partir de fuente y dependencias
identificadas. No se promete un ZIP idéntico bit por bit al reconstruir: la
receta existente incorpora marcas de tiempo de build. El hash publicado en el
recibo identifica este candidato concreto.

No se reutilizó el rc12 anterior. El binario rc13 se ejecutó fuera del worktree:
47 comprobaciones Qt PASS, incluida ejecución real con MotorSimWorker.exe,
sin usar Python externo como worker. Las aceptaciones empaquetadas CP1 y CP2
también pasaron. Un supervisor registra PID e instante de creación de los hijos
propios y comprueba su salida, sin finalizar procesos de otras sesiones.

El recibo final y las rutas del ejecutable/ZIP están en
`results/frontend-commercial-integration-v1/acceptance.json` y `candidate.json`.
Los proyectos, corridas, PDFs y logs completos permanecen en la raíz externa de
artefactos. No se borraron paquetes ni resultados históricos.

## Gate del candidato

Estado: **WINDOWS_ACCEPTED**, con fuente **SOURCE_ACCEPTED**. El recibo comprueba
31 condiciones de procedencia, ejecución, persistencia y cierre. Permanecen
**GENERAL_REGRESSION_NOT_GREEN**, **PENDING_UAT** y
**SCIENTIFIC_VALIDATION_NOT_PERFORMED**.

La aceptación externa estable de recuperación usa UI Automation Invoke, sin
teclado global: **12 comprobaciones PASS** en las tres familias. Cada borrador
se aceptó en su diálogo real, abrió Guardar como, conservó el SHA-256 del archivo
original y cerró con exit 0. También se verificaron los recientes de las tres
familias en el INI escrito por el propio candidato durante sus recorridos.

El recorrido externo monolítico por teclado **no se acepta como gate**: sus
intentos fallidos quedan conservados. Inicialmente se observaron Acerca de y
diagnóstico en las tres familias antes de que fallara el selector de archivos;
los diagnósticos posteriores identificaron Value.SetValue sin efecto, selección
del desplegable en vez del botón y restricciones SetForegroundWindow/
AttachThreadInput. La verificación estable de recuperación no depende de esos
mecanismos. No se presenta ese recorrido fallido como PASS ni como una regresión
nueva del producto.

Un diagnóstico nuevo de un intento del helper quedó en la ruta predeterminada
del perfil. Se identificó por su creación dentro de la vida del proceso y por el
build embebido, y se trasladó a E: con SHA-256 idéntico. Se conserva
`diagnostic-relocation.json`. No era un proyecto original. Los intentos siguientes
usaron un perfil propio en E: y comprobaron la ruta antes de aceptar.

El supervisor confirmó el cierre de los árboles propios, incluidos los intentos
fallidos. Un probe de accesibilidad cuyo bloque de limpieza falló dejó una GUI
temporal; se identificó por PID, creación y cwd de su directorio aislado y se cerró.
El recibo final vuelve a comprobar que esas identidades de procesos no siguen
activas. No se finalizaron procesos de tareas concurrentes.

Reproducir la construcción: checkout limpio del commit fuente indicado, entorno
`.venv-build` con las versiones fijadas, preflight de espacio y
`python packaging/build_windows.py --output-root <salida-nueva> --work-root <temporal-propio>`.
Los comandos concretos de pruebas y aceptación están en los resúmenes versionados.
La aceptación funcional se ejecuta con `Dino2T.exe --verify-frontend-commercial
--output <carpeta-nueva> --fixtures <fixtures-sintéticos-de-presentación>`;
`verify_recovery_windows.py` comprueba externamente las copias recuperadas.

## Alcance y riesgos restantes

El gate de fuente se mantiene separado del gate del candidato Windows. Los
recorridos automáticos no equivalen a UAT humana: accesibilidad, lector de
pantalla, alto contraste, escalados y validación con usuarios siguen PENDING_UAT.
Las mejoras F2/F3 del frontend conservan su hoja de ruta; no se declara que los
23 hallazgos originales estén completamente cerrados. Tampoco se resuelven en
esta integración las políticas comerciales pendientes de duración definitiva
del trial o derechos de actualización.

La referencia 4T 0D sigue siendo sintética. La integridad de archivos, el fin de
ejecución y la periodicidad se presentan por separado. La validación científica
permanece SCIENTIFIC_VALIDATION_NOT_PERFORMED y no se reclama capacidad predictiva.

Recomendación de integración posterior: revisar y fusionar esta rama completa
conservando su merge y evidencia, en una operación separada. Mantener los estados
de regresión general, UAT y validación científica; resolver en sus propios
objetivos los fallos heredados y CP3/CP4. Esta tarea no hace merge a main ni push.
