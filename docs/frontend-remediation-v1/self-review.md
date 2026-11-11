# Revisión de cierre de F0/F1

Tipo: SELF_REVIEW. No hubo otro agente revisor ni se declara INDEPENDENT_REVIEW.
Fuente de aplicación: `cc5a12d`, sobre correcciones de integridad `4295423` y
registro de alcance `daeb975`. El recibo vincula esta fuente con pruebas y hashes.

| Capa | Cambios de esta fase | Límite |
|---|---|---|
| Frontend | Cabecera, formularios físicos, navegación, presupuestos, mensajes, acceso a corridas y ayuda | No afirma capacidades que no expongan los adaptadores |
| Backend de aplicación | Frontera de borradores, normalización de rutas, vínculo de resultados y transporte transitivo de archivos | Conserva identidades y bytes científicos originales |
| Backend científico | Ningún cambio | Solvers, ecuaciones, tolerancias, contratos y umbrales preservados |

Revisión de integridad: las notificaciones de resultados no descartan borradores;
aplicar/cancelar se resuelve antes de comandos sensibles; guardar fallido conserva
dirty y ruta; importar usa destino nuevo; los metadatos primarios no se reescriben.
Los estados de transporte, ejecución y periodicidad no se promocionan al copiar.
La configuración de la corrida real nativa reabierta contiene el diámetro de
87 mm aplicado en el recorrido, y el resultado conserva su estado incompleto.

Revisión de regresión: el recibo exige conjuntos finales exitosos de frontend,
comercial y contratos protegidos. Los intentos fallidos/abortados permanecen
identificados; no se usan para aceptación. La limpieza del test de shell resuelve
su borrador inválido explícitamente, sin cambiar sus aserciones. El test nuevo
de cierre comprueba que Cancelar conserva ese mismo borrador en producto.

Revisión visual: formularios y cabecera examinados en compacto y grande; ayuda,
diálogos de error, contenido portable y comparación visibles en capturas. Los
recortes/densidad remanentes de resultados compactos están en UX-018; no se
ocultan bajo una afirmación global de diseño adaptable o accesibilidad aprobada.

Revisión de evidencia: comparación elegible con fixture explícitamente sintético
de presentación. Corridas reales 2T/nativa/0D prueban integración de la aplicación;
no son una nueva validación numérica o experimental. El resultado nativo del
recorrido no alcanzó periodicidad; el 2T alcanzó un ciclo sin convergencia.

Revisión operativa: rama y worktree independientes, sin merge ni push. Los
artefactos nuevos se conservaron fuera de la fuente; no se borraron históricos.
P9 conserva su identidad. Main avanzó externamente desde `48b3afe` hasta
`f97469b` durante esta sesión, con trabajo concurrente de CP1/CP2 y licencias:
el recibo conserva su reflog observado y comprueba que el incremento de esta
rama no está integrado en main. Esta tarea no hizo merge ni push. La integración
con ese main más reciente, incluidos posibles conflictos de interfaz, necesita
una fase propia y regresión sobre la combinación. El alcance
de aceptación es F0/F1 en fuente. La cola general, exploración avanzada,
recuperación detallada, accesibilidad y candidato Windows tienen fases separadas
en la hoja de ruta. Un gate fuente cerrado no cierra esas obligaciones futuras.
