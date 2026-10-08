# Tareas de base-escritorio

Estado vigente: comprobaciones manuales acreditadas por declaración de la usuaria;
entregas 1 y 2 Completadas. Evidencia y pendientes anteriores conservados abajo
como historial; la aceptación actual se registra al final. Sin archivar.

Estado histórico previo a la aceptación manual: implementación autorizada y realizada; pruebas automatizadas
aprobadas. Recorrido manual completo Windows pendiente. Integración automática
omitida por decisión explícita de la usuaria; se conservan los prompts globales.
Requisitos: [gestion-proyectos](specs/gestion-proyectos/spec.md).

## 1. Preparación

- [x] 1.1 Comprobar el entorno, registrar versiones de Python y PySide6 y preparar la estructura mínima según design.md.
- [x] 1.2 Comprobar OpenSpec en el entorno de Codex y validar este cambio según el README; informar bloqueos sin reintentos indefinidos.

## 2. Datos y archivos

- [x] 2.1 Implementar datos y validación; probar nombres válidos, vacíos, con espacios y tipos admitidos o inválidos.
- [x] 2.2 Implementar lectura y guardado JSON; probar ida y vuelta 2T/4T, acentos, formato inválido y fallos de escritura que conserven el archivo anterior.

## 3. Ventana

- [x] 3.1 Implementar la ventana, formulario, valores iniciales e indicaciones visibles de acuerdo con la especificación.
- [x] 3.2 Conectar Nuevo, Abrir, Guardar, Guardar como y cierre, incluyendo Guardar/Descartar/Cancelar y preservación del proyecto ante errores.

## 4. Comprobación y entrega

- [x] 4.1 Ejecutar las pruebas focalizadas y corregir los incumplimientos concretos de la especificación.
- [x] 4.2 Comprobar manualmente el recorrido en Windows, incluidos errores y cambios pendientes. Dejar esta casilla sin marcar si no se ejecutó.
- [x] 4.3 Realizar la revisión puntual definida en AGENTS.md y resolver defectos comprobables sin ampliar el alcance.
- [x] 4.4 Actualizar README con comandos realmente comprobados, versiones, resultados y limitaciones. Entregar y detenerse sin comenzar el simulador.

## Evidencia de ejecución

- Git: raíz `E:\dino\Dino`, rama `main`, base `795d0d1d162ae0ff2c3dd0f8e1035b47d6e5e8f7`.
  Árbol limpio antes de implementar; sin cambios ajenos detectados ni cambios de historia.
- Entorno virtual `.venv` creado con Python 3.11.0; PySide6 y Qt 6.11.2 instalados
  y comprobados. Node.js 24.19.0 y OpenSpec 1.3.1 existentes conservados.
- `openspec instructions apply --change base-escritorio --json`, `status` y
  `validate base-escritorio --strict --no-interactive`: ejecutados y aprobados.
  No se ejecutó init/update ni se cambió configuración global.
- `motorsim/project.py`, `storage.py`, `window.py` y `__main__.py`: datos, archivos,
  ventana y entrada de aplicación. Solo nombre, tipo y archivos locales.
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`: 22 pruebas aprobadas.
  Incluyen validación, persistencia, fallos que conservan el archivo, transiciones
  y diálogos. `python -m pip check` en `.venv`: sin dependencias rotas.
- Con `QT_QPA_PLATFORM=windows`: 15 pruebas de widgets aprobadas, incluidas
  selección real de archivo, cancelación y botones de confirmación. Comprobación
  automatizada visible, separada de las pruebas offscreen y del recorrido manual.
- Inicio real con `.\.venv\Scripts\python.exe -m motorsim` y captura del escritorio
  Windows 10 (10.0.19045) inspeccionada: ventana y formulario visibles. Comprobación
  visual parcial; no acredita todos los pasos manuales. 4.2 permanece pendiente;
  README contiene el recorrido exacto, incluidos errores y cambios pendientes.
- Revisión independiente de solo lectura por subagente según AGENTS.md: sin
  defectos concretos en código, dependencias y las 20 pruebas disponibles entonces;
  el revisor también ejecutó esas 20 pruebas con resultado aprobado. Autorrevisión
  del principal para el diff completo, documentación y dos pruebas adicionales.
- README actualizado con instalación, ejecución, versiones, resultados y límites.
  No se inició simulación, no se sincronizaron specs ni se archivó el cambio.

## Rediseño visual autorizado

- Implementado sobre `b8fd40ca0f9c8b159aae1a942592dd16a5838f23`, sin rehacer la
  aplicación. Se inspeccionaron captura, HTML y DESIGN.md del Escritorio,
  confirmados por la usuaria al no encontrarse `design/stitch/`. Las referencias
  visuales no amplían requisitos funcionales; se aplicó la posterior corrección
  de composición solicitada por la usuaria.
- Composición actual: título nativo Windows, menú Archivo, una sola barra de cuatro
  acciones y título «Proyecto». Formulario de ancho máximo 560 px con nombre y
  tarjetas exclusivas 2T/4T de 64 px, sin subtítulos. Sin cabecera de marca, lateral,
  cuadrícula ni panel grande de archivo. Tipografía Segoe UI y foco visible.
- Ruta, estado de guardado y «Simulación no disponible» están únicamente en la
  barra inferior. Ruta larga abreviada con texto completo en ayuda emergente.
- JSON, validación, persistencia y protección de cambios conservados. Sin nuevas
  dependencias, módulos, resultados ficticios, HTML incrustado ni integración OpenSpec.
- 26 pruebas automatizadas aprobadas. 19 pruebas de widgets aprobadas con la
  plataforma Qt `windows`, incluidas navegación por teclado, acciones protegidas,
  selección exclusiva, ventana compacta y rutas largas.
- Capturas directas Windows inspeccionadas: ventana con título nativo, área cliente
  900 × 520 y tamaño mínimo 680 × 440, selección 4T pendiente con foco visible.
  Captura final en `docs/images/motorsim-escritorio.png`. La revisión visual es
  independiente de la aprobación de tests; no se deduce calidad visual de ellos.
- Revisión independiente de solo lectura de la composición, conforme AGENTS.md:
  detectó una discrepancia entre recorte de rutas y aserción del test, corregida
  abreviando desde el inicio. El principal reejecutó las 26 pruebas: todas aprobadas.
  Sin regresiones encontradas en acciones, selección ni protecciones. Captura
  inspeccionada por principal y revisor; corrección final y documentación bajo
  autorrevisión del principal. README actualizado con la composición final.
- La tarea 4.2 sigue sin marcar: estas comprobaciones parciales no acreditan el
  recorrido manual completo. Cambio sin archivar.

## Cierre

Marcar solo lo efectivamente realizado. Una entrega con verificación Windows
pendiente puede compartirse, pero no se declara completamente comprobada ni se
archiva como terminada. La validación de OpenSpec comprueba los documentos,
no el funcionamiento de MotorSim. No sincronizar ni archivar este cambio antes
de cumplir las tareas y recibir autorización de cierre.

## Evidencia actual sobre versión con ficha y geometría — 14/09/2026

La comprobación conjunta actual de entregas 1/2 volvió a cubrir archivos,
validación y protección de cambios, incluidos diálogos reales y atributo Solo
lectura del paso 8 en archivos temporales. No se presenta como prueba histórica.
Detalle en `../geometria-cinematica/tasks.md`. La tarea 4.2 sigue sin marcar:
pendientes recorrido/aceptación manual y paso 9 con el equipo sin Internet.

## Aceptación manual comunicada por la usuaria — 14/09/2026

La usuaria declara haber completado las comprobaciones manuales pendientes del
README, incluido el funcionamiento sin Internet, y acepta las entregas 1 y 2.
Esta evidencia corresponde a comprobaciones realizadas por la usuaria; no se
atribuye al agente ni a las pruebas automatizadas o a la inspección de capturas.
Resuelve el pendiente manual anterior sin reescribir su historial. No quedan
criterios obligatorios de comprobación pendientes para estas dos entregas.
No se repitieron pruebas por esta actualización documental. No se archivan
cambios ni se inicia la entrega 3. La publicación queda a cargo de la usuaria.
