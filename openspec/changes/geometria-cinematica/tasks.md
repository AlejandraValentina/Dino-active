# Tareas de geometria-cinematica

Estado vigente: comprobaciones manuales acreditadas por declaración de la usuaria;
entregas 1 y 2 Completadas. Evidencia y pendientes anteriores conservados abajo
como historial; la aceptación actual se registra al final. Sin archivar.

- [x] 1. Comprobar registro/publicación de entrega 1, preservar pendientes y validar este único cambio.
- [x] 2. Implementar cálculos directos y dependencias por resultado; contrastar caso independiente.
- [x] 3. Añadir pestaña, esquema y curvas Qt con actualización y teclado.
- [x] 4. Ejecutar regresiones de datos, archivos y cambios pendientes, y pruebas de geometría.
- [x] 5. Inspeccionar pestaña Windows y escalado, conservar captura real y hacer revisión puntual.
- [x] 6. Actualizar README y estado y preparar archivos revisados para registro/publicación separados. Detenerse sin archivar.

## Evidencia

- Entrega 1 encontrada ya registrada y publicada: 040e789, main y origin/main
  iguales tras fetch, árbol limpio. Sin commit vacío ni reescritura. No hay
  entornos, cachés, credenciales o archivos personales en el conjunto versionado.
- Cálculo directo y Qt Widgets sin dependencias nuevas. JSON v2 y lectura v1
  conservados. 47 pruebas automáticas aprobadas; 27 de widgets con plataforma
  Windows aprobadas. pip check correcto. OpenSpec apply disponible y validación
  estricta aprobada. Contraste independiente mediante triángulo 3-4-5 a 90°.
- Revisión independiente puntual: se corrigió que Vd dependiera de compresión;
  nuevo test confirma independencia con compresión vacía e inválida. Autorrevisión
  del principal para la corrección y documentación, sin campaña adicional.
- Tarea 5 incompleta: escritorio devuelve imagen azul uniforme; LogonUI activo.
  Solo se pudo inspeccionar renderizado Qt Windows normal/150 %, que no equivale
  a captura real. Pasos pendientes concretos en README, sección Geometría.
  La automatización no acredita el recorrido manual histórico de entrega 1.
- Estado: Por verificar. No se archiva ningún cambio ni se comienza entrega 3.

## Comprobación conjunta actual — 14/09/2026

Sobre main `7ef0628`, árbol inicialmente limpio; commit confirmado contenido en
origin/main tras fetch, sin push innecesario ni cambios de remoto o credenciales.
Implementación conservada, sin defectos nuevos reproducidos ni funciones añadidas.
47 pruebas automáticas y 27 de widgets Windows aprobadas. Recorrido adicional
mediante automatización visible y diálogos reales en ambos ciclos: edición de
ficha completa, guardar, cerrar/reabrir, Guardar como (cancelar/reemplazar), JSON
inválido, nombre inválido, protección al cancelar/descartar y lectura v1 sin
reescritura hasta guardar. Archivo temporal Solo lectura: guardar falla, conserva
bytes y edición; cerrar eligiendo Guardar queda bloqueado hasta corregir el permiso.
Sin sustituir los diálogos ni simular el error del sistema de archivos.

Geometría: cambio de carrera actualiza esquema/curvas; compresión ausente retira
solo volumen, biela ausente/incompatible retira cinemática sin impedir guardar
la ficha positiva. Rangos 360°/720°, teclado, pestañas y redimensionado comprobados.
Escritorio desbloqueado: capturas reales inspeccionadas, incluidos ambos rangos,
resultados retirados y escala 150 % del proceso Qt. Se conservan
`docs/images/motorsim-geometria.png` y `docs/images/motorsim-ficha-verificacion.png`.
Los datos están identificados como prueba. Inspección visual separada de tests.

Esto acredita comprobaciones técnicas actuales para ambas entregas, no aceptación
manual ni evidencia histórica. Sigue pendiente realizar y aceptar el recorrido
manual de README, incluido paso 9 con el equipo realmente desconectado de Internet;
no se modificó la conectividad del entorno compartido. No se archiva ni inicia
entrega 3. Estado de cierre conjunto: Por verificar.

## Aceptación manual comunicada por la usuaria — 14/09/2026

La usuaria declara haber completado las comprobaciones manuales pendientes del
README, incluido el funcionamiento sin Internet, y acepta las entregas 1 y 2.
Esta evidencia corresponde a comprobaciones realizadas por la usuaria; no se
atribuye al agente ni a las pruebas automatizadas o a la inspección de capturas.
Resuelve el pendiente manual anterior sin reescribir su historial. No quedan
criterios obligatorios de comprobación pendientes para estas dos entregas.
No se repitieron pruebas por esta actualización documental. No se archivan
cambios ni se inicia la entrega 3. La publicación queda a cargo de la usuaria.
