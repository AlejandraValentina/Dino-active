# Tareas de caracteristicas-motor

Estado vigente: comprobaciones manuales acreditadas por declaración de la usuaria;
entregas 1 y 2 Completadas. Evidencia y pendientes anteriores conservados abajo
como historial; la aceptación actual se registra al final. Sin archivar.

- [x] 1. Registrar el alcance autorizado y validar el único cambio OpenSpec.
- [x] 2. Implementar datos opcionales, parseo y validación, JSON v2 y lectura v1.
- [x] 3. Implementar ficha adaptable, geometría calculada y estado pendiente completo.
- [x] 4. Ejecutar pruebas de datos, compatibilidad, cálculos y regresiones de archivos.
- [x] 5. Inspeccionar ventana real Windows, escalado y captura con datos de prueba.
- [x] 6. Hacer revisión puntual, actualizar README y entregar resultados y pendientes.

No modifica ni completa el recorrido manual pendiente de base-escritorio.
No se archiva automáticamente ni se comienza simulación física.

Evidencia: validación OpenSpec estricta aprobada; 36 tests automáticos y 23 de
widgets con plataforma Windows aprobados; pip check correcto. Captura visible
`docs/images/motorsim-motor.png` inspeccionada, datos de prueba identificados.
También se inspeccionó ventana apilada al 150 % (escalado del proceso Qt), con
foco, campos y barra inferior accesibles mediante desplazamiento vertical.
Revisión independiente de solo lectura: un caso de precisión de enteros corregido
y cubierto por regresión; autorrevisión del principal de corrección y documentación.
No equivale al recorrido manual completo histórico de base-escritorio.

## Retoma según la hoja de ruta

- [x] 7. Vincular el seguimiento persistente a la hoja de ruta y declarar geometría común.
- [x] 8. Comprobar cierre/reapertura de ficha completa en otra ventana y lectura v1 desde el editor; ejecutar regresiones y revisar la ventana Windows.
- [x] 9. Realizar autorrevisión puntual del ajuste y actualizar README y estado resumido.
- [x] 10. Acreditar el recorrido manual Windows heredado antes del cierre completo; referencia única de pasos: README y tarea 4.2 de base-escritorio.

Evidencia de la retoma (14/09/2026): estado local contrastado en main, HEAD
7301848; cambios previos preservados. Reutilizada la implementación existente.
AGENTS y hoja de ruta enlazados; hipótesis de geometría común declarada en ficha
y especificación. Suite completa: 38 aprobadas; plataforma Windows: 25 aprobadas;
pip check sin fallos y validación estricta OpenSpec aprobada. Se probaron cierre y
reapertura de todos los campos en otra ventana y lectura v1 desde el editor sin
reescritura automática. Captura Windows actualizada e inspeccionada; comprobada
vista apilada al 150 % con foco y sin desplazamiento horizontal. Autorrevisión
puntual de código, pruebas, documentos y captura, sin nueva revisión independiente.
La tarea 10 sigue pendiente: automatización visible e inspección de capturas no
acreditan el recorrido manual completo. Estado resumido: Por verificar.

## Comprobación actual conjunta — 14/09/2026

Implementación sin cambios sobre 7ef0628, publicado. Se comprobaron ahora ficha,
archivos v1/v2, cambios pendientes y geometría con 47 tests automáticos, 27 de
widgets Windows y recorrido adicional con diálogos reales, incluido error real
Solo lectura en 2T/4T. Evidencia conjunta detallada en
[geometria-cinematica/tasks.md](../geometria-cinematica/tasks.md#comprobación-conjunta-actual--14092026).
Captura actual: `docs/images/motorsim-ficha-verificacion.png`.
La tarea 10 permanece pendiente: automatización visible e inspección actual no
son aceptación manual; falta además el paso 9 con desconexión real de Internet.

## Aceptación manual comunicada por la usuaria — 14/09/2026

La usuaria declara haber completado las comprobaciones manuales pendientes del
README, incluido el funcionamiento sin Internet, y acepta las entregas 1 y 2.
Esta evidencia corresponde a comprobaciones realizadas por la usuaria; no se
atribuye al agente ni a las pruebas automatizadas o a la inspección de capturas.
Resuelve el pendiente manual anterior sin reescribir su historial. No quedan
criterios obligatorios de comprobación pendientes para estas dos entregas.
No se repitieron pruebas por esta actualización documental. No se archivan
cambios ni se inicia la entrega 3. La publicación queda a cargo de la usuaria.
