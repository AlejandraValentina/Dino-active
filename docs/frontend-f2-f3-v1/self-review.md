# SELF_REVIEW · F2/F3

Revisión secuencial por el mismo agente, no INDEPENDENT_REVIEW. Candidato revisado `b00a5653`, fuente funcional aceptada `e9a817c`; árboles motorsim/ y packaging/ idénticos. Los commits posteriores contienen registros, verificador y documentación; el verificador vuelve a comprobar bytes y diferencias de producto.

## Hallazgos resueltos durante la integración

- Cambio programático de familia no notificaba al mapa: señal explícita de familia, prueba directa y recorrido real.
- Selector de muestra podía coincidir por nombre duplicado: selección por instancia/índice y regresión con series homónimas.
- Importaciones asíncronas podían reemplazar una selección más nueva: generación por solicitud y rechazo de callbacks antiguos. La aceptación espera la carga completa.
- El fixture de tests filtraba DINO_RECOVERY_ROOT hacia CP2: aislamiento/restauración de entorno, sin relajar recuperación ni contratos.
- Paneles de gráficos pequeños: ventana ampliada del mismo renderer, cursor/viewport sobre una instantánea real; detalle del componente con scroll y etiquetas legibles.
- Recuperación manual protegía el contexto equivocado: valida primero y guarda/cancela sobre el destino, incluso inactivo. Cancelar conserva el proyecto y la familia previa.
- La captura final reveló el fallback proyecto en referencias dataclass: identidad pública, nombre legacy visible y clave de archivoV2 con digest, incluidos nombres que colisionan al sanitizar. Se retuvo el primer candidato y se reconstruyó la corrección antes de cerrar.

## Evidencia de aceptación

Fuente47+78 y Windows47+78, CP1/CP2 y recuperación externaUIA pasan. El caso añadido crea dos referencias distintas mediante el contexto real, autoguarda ambas y comprueba rutas y nombres retenidos. Las pruebas focalizadas cubren colisión por sanitización y limpieza de un borrador sin afectar al otro. Los originales recuperados mantienen SHA y SaveAs cancelado no los sobrescribe.

La cola conserva bytes canónicos de entrada, límites, estado durable, errores y calificación original del resultado. Un lock evita otro escritor. Al reiniciar no se ejecuta nada automáticamente y RUNNING se convierte en INTERRUPTED. Cerrar espera el límite de ciclo y puede rechazar el cierre mientras exista trabajo activo. No hay promesa de checkpoint nativo ni cola universal de barridos.

## Límites que siguen abiertos

El backlog conserva10 parciales y1 UAT pendiente, sin convertir labels o UIA en aceptación integral de accesibilidad. La regresión general completa no se declara verde. CP3/CP4, datos experimentales, exactitud predictiva y elección/calibración de modelos no forman parte de este cierre. El renderer conserva ausencias y flags de conexión; no agrega interpolación científica. Las fixtures A/B conservan origen sintético en metadatos y cursor.

P9, solvers, tests protegidos, licenciamiento y ZIPrc13 se verifican sin cambios. Procesos sólo propios, por PID+creation time; no se detienen procesos de otras sesiones. Los artefactos previos se preservan. Sin push, publicación ni integraciónF2/F3 en main.
