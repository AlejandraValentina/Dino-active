# Tareas de conductos-admision-escape

- [x] 1. Comprobar continuidad y documentar único cambio, autorización y convenciones.
- [x] 2. Implementar datos opcionales, JSON v5 y lectura v1–v4 conservando protecciones.
- [x] 3. Calcular áreas, volúmenes, totales y compatibilidad por dependencias.
- [x] 4. Integrar editor único, orden, perfil real y conservación de borradores en 4T.
- [x] 5. Probar casos independientes, incompletos/inválidos, orden, archivos y regresiones.
- [x] 6. Revisión puntual y Windows disponible, captura real y escalado 150 %.
- [x] 7. Ejecutar suite completa final tras la última corrección; registrar resultado.
- [x] 8. Actualizar evidencia/hoja y preparar commit propio y publicación normal disponible.

## Continuidad — 15/09/2026
main b6dc169, árbol limpio y origin/main coincidente. Se preservan implementación,
pruebas, inspección visual y aceptación manual previa sin reinterpretarlas.
Autorizada únicamente entrega 4 geométrica; sin integración global ni entrega 5.

## Evidencia de cierre técnico — 15/09/2026

- Editor único de recorridos independientes, añadir/editar/eliminar/subir/bajar,
  tipo derivado, referencias y dimensiones opcionales. Borradores inválidos
  conservados incluso al cambiar fila, recorrido y 2T/4T; bloquean guardar.
  Selecciones de vista/fila no marcan pendiente. Se mantienen protecciones existentes.
- Áreas/volúmenes por pieza, totales por dependencias sin sumas parciales, uniones
  continuas/discontinuas/sin verificar; sin ajustes automáticos. Perfil de posiciones
  axiales acumuladas y radios interiores, escala uniforme, piezas y selección reales.
  Invalidez/ausencia retiran perfil. No se suma al cárter ni se multiplica por N.
- JSON v5 guarda orden/nombres/dimensiones/referencia, no derivados. Lectura v1–v4
  conserva todos los datos y deja recorridos vacíos sin escribir hasta guardar.
  Archivos de pruebas y captura en directorios temporales, fuera de .venv; sin
  destinos de la usuaria modificados ni ejemplos persistentes precargados.
- Caso independiente: L100/D20/20 y L100/D20/40, volúmenes 10π y 70π/3, total 100π/3
  cm³, longitud 200 mm y unión 20 mm. Expansión, contracción, discontinuidad, ausentes,
  inválidos, límites finitos, reordenación, borrado, persistencia de ambos recorridos,
  cierre/reapertura, v1–v4, cambio 2T/4T, guardado/errores/cancelaciones cubiertos.
- Durante implementación: 8 pruebas numéricas y 39 pruebas de widgets sin pantalla
  aprobadas. Revisión independiente de solo lectura: sin hallazgos reproducibles;
  también ejecutó 8 pruebas numéricas. Autorrevisión del principal e inspección
  visual detectaron eje oculto por relleno: orden de dibujo corregido antes del final.
- **Suite completa FINAL: 85 pruebas, 22,311 s, OK**, una ejecución después de la
  última corrección con QT_QPA_PLATFORM=windows. Incluye 39 pruebas de widgets y
  diálogos reales automatizados más regresiones de ficha, cinemática, lumbreras,
  admisión y archivos. Comando: .\.venv\Scripts\python.exe -m unittest discover -s tests -v.
- Windows disponible: captura real docs/images/motorsim-conductos.png, 1350×988 px,
  escala efectiva 125 %, caso sintético identificado. Perfil continuo, discontinuidad
  sin adaptador y perfil retirado tras edición inválida inspeccionados. También
  editor/perfil apilados al 150 % en 700×480 unidades lógicas; Tab/foco y sin
  desplazamiento horizontal. Escala Qt solo del proceso; no configuración global.
- Automatización visible e inspección del agente no equivalen a aceptación manual
  de la usuaria. Evidencias y aceptaciones anteriores conservadas. Entrega 4 Completada
  técnicamente, sin pendientes obligatorios de comprobación ni afirmaciones físicas.
- Validación OpenSpec estricta aprobada; único cambio nuevo. Archivos propios
  preparados para commit separado y push normal si autenticación lo permite.
  Sin credenciales/configuración global modificadas, archivo de cambios ni entrega 5.
