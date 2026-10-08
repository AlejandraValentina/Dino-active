# Tareas de configuracion-2t

- [x] 1. Comprobar continuidad y documentar/validar este único cambio y convenciones.
- [x] 2. Implementar filas/cárter opcionales y JSON v3 compatible con v1/v2.
- [x] 3. Implementar cruce acotado, áreas y dependencias reutilizando cinemática.
- [x] 4. Integrar editor 2T, selección, gráfico, edición pendiente y conservación en 4T.
- [x] 5. Probar caso sintético independiente, límites, actualización, persistencia y regresiones.
- [x] 6. Comprobar Windows cuando esté disponible y hacer revisión puntual; registrar evidencia y captura.
- [x] 7. Actualizar README/hoja, preparar commit separado y publicación sin reintentos de autenticación.
- [x] 8. Definir y autorizar el tramo de admisión: decisión posterior de la usuaria, falda recta y ventana rectangular; sin modalidad por defecto.
- [x] 9. Implementar admisión, dominio, eventos/áreas, editor y JSON v4 compatible.
- [x] 10. Comprobar casos independientes, dependencias, borradores y regresiones.
- [x] 11. Revisar puntualmente y comprobar Windows/captura y escalado 150 %.
- [x] 12. Ejecutar suite completa después de la última corrección y registrar resultado final.
- [x] 13. Actualizar evidencia y resumen; preparar cambios propios para commit separado y push normal con autenticación disponible.

## Evidencia del primer tramo — 14/09/2026

- Inicio en main 5cc7e50, árbol limpio. Aceptación manual de entregas 1/2 y prueba
  sin Internet declaradas por la usuaria conservadas; no se reinterpretan.
- Único cambio configuracion-2t, especificación/diseño y validación estricta
  aprobada. Integración y configuración global intactas; ninguna dependencia nueva.
- Datos incompletos, borradores inválidos, filas individuales, cárter, referencia
  JSON v3 y lectura v1/v2 implementados. Posición del pistón y gráfico reutilizados.
- Suite completa de 58 pruebas aprobada. Revisión independiente de solo lectura:
  detectó subdesbordamiento de área positiva a cero; corregido con error de rango
  que retira áreas conservando eventos. Después, 9 pruebas focalizadas de lumbreras
  (incluida la nueva regresión) y 30 de widgets Windows aprobadas. Colección: 59 tests.
  Autorrevisión del principal de corrección y documentación, sin campaña adicional.
- Caso sintético esperado 90°/270°/180°/200 mm² contrastado con valores dados por
  la usuaria, sin generarlos mediante la función probada. Parcial, nunca abierta,
  ausencia, invalidación, persistencia/eliminación y cambio 2T/4T cubiertos.
- Captura real Windows inspeccionada: docs/images/motorsim-configuracion-2t.png,
  datos identificados como sintéticos, ventana 1080×791. También inspeccionado
  escalado 150 % y disposición apilada, sin desplazamiento horizontal.
  Pruebas automatizadas y captura no constituyen aceptación manual del tramo.
- Pendiente de producto: admisión (tarea 8). Entrega 3 En curso, no completada.
  No se archiva ni se desarrolla entrega 4, conductos o simulador. Archivos propios
  revisados y preparados para commit separado; publicación solo por push normal
  si la autenticación disponible lo permite.

## Evidencia de admisión — 14/09/2026

- Retoma en main 988adb2 con árbol limpio y origin/main coincidente. Se conserva
  el primer tramo y toda la evidencia histórica; el pendiente de decisión de
  aquel momento queda resuelto ahora por autorización explícita de la usuaria.
- Modalidad null/piston_port, cuatro dimensiones opcionales y referencia propia,
  JSON v4 con lectura v1/v2/v3 sin reescritura automática. Borradores inválidos
  conservados y guardado bloqueado aun sin modalidad y en 4T. Sin dependencias nuevas.
- Eventos por cruce acotado compartido; área distinta de escape/transferencia,
  dominio u>=S y d<S, caso nunca abierto y máximo parcial. Cálculos independientes
  de diámetro, compresión, N y cárter. Ancho ausente conserva eventos.
- Caso sintético independiente S56/L100/u64/h10/w20/f42: 270°/90°/180°/200 mm²,
  A0=A360=200 y A90=A180=A270=0. También límites/rango, ausencia e invalidez,
  actualización S/L/u/h/f, persistencia incompleta, cambios de ciclo/modalidad,
  cancelaciones y regresiones de lumbreras y archivos. No es motor experimental.
- En implementación se corrigió conexión de señales del editor; después pasaron
  9 pruebas numéricas y 34 de widgets sin pantalla. Revisión independiente de
  solo lectura, sin defectos de código; señaló ambigüedad documental v3, aclarada.
  Autorrevisión del principal de corrección, integración, documentación y capturas.
- Suite completa FINAL, ejecutada una vez tras la última corrección con
  QT_QPA_PLATFORM=windows: **72 pruebas, 11,647 s, OK**. Incluye 34 pruebas de
  widgets y diálogos reales automatizados. Comando: .\.venv\Scripts\python.exe
  -m unittest discover -s tests -v. No se presenta una ejecución anterior como final.
- Escritorio Windows disponible: captura real inspeccionada
  docs/images/motorsim-admision-2t.png (1080×791); caso sintético identificado
  en ruta de archivo. Curva abierta alrededor de PMS, cerrada alrededor de PMI.
  Inspeccionados también formulario y curva apilados al 150 % en 700×480 unidades
  lógicas; Tab/foco, ayuda desplegable y sin desplazamiento horizontal.
- Automatización visible e inspección del agente no son aceptación manual de la
  usuaria para entrega 3. Las aceptaciones previas 1/2 permanecen intactas.
  Sin comprobaciones técnicas obligatorias pendientes; entrega 3 Completada para
  esta configuración geométrica. No acredita predicción ni elige motor experimental.
- OpenSpec validado estrictamente; sin init/update, configuración global ni prompts
  modificados. No se archiva ni se comienza entrega 4, conductos o simulación.
  Cambios propios preparados para commit separado; publicación únicamente normal,
  informando cualquier fallo de autenticación sin reintentos ni cambios globales.
