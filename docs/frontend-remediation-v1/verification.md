# Verificación de la remediación

## Método y entorno

Aplicación Qt Widgets real con plataforma `windows`, Python 3.11 y PySide6
6.11.2. Las acciones se enviaron mediante QTest (ratón/teclado); los selectores
de archivos devolvieron rutas aisladas para hacer reproducibles exportaciones y
guardados. La inspección del estado y la carga de fixtures se registran aparte
en el journal. No se reemplazó el solver para las corridas reales.

`live_driver.py` es instrumentación local, no una interfaz del producto ni parte
de su empaquetado. Los proyectos/corridas nuevos se conservan fuera del
repositorio. Preflight de espacio PASS antes de ejecutar. No se construyó un
candidato Windows nuevo. El resto de los worktrees y sus procesos se preservaron.

## Recorridos observados

| Recorrido | Evidencia y alcance |
|---|---|
| Borrador nativo | `r03`: 86→87 sin aplicar; cancelar impide enviar el motor anterior |
| Aplicar y ejecutar | `r04–r05`: 87 aplicado/guardado, editor bloqueado; resultado real incompleto por presupuesto, sin promoción de periodicidad |
| Bundle nativo | `r06`, `r25–r27`: cierre original y reubicado verificados, bytes de configuración/resumen/traza/metadatos iguales; exportar/importar/guardar desde el shell |
| Cancelar curva | `r07–r09`: plan de dos puntos, cancelación solicitada y terminal CANCELLED con 0/2 puntos completados |
| Crear y ejecutar 2T | `r10–r14`: creación por asistente, confirmación real, un ciclo; MAX_CYCLES_NONCONVERGED, vínculo al proyecto y botón de último resultado |
| Bundle 2T | `r15`: diez archivos, disponibilidad COMPLETE, resultado idéntico tras reubicación |
| Referencia 0D | `r17–r23`: campo inválido/corrección, aplicación, guardado, ejecución converged y resultado sintético; borrador conservado al cancelar |
| Comparación elegible | `r24`: aplicación real, dos endpoints de fixture SYNTHETIC_PRESENTATION_UI_ONLY; cuatro diferencias calculadas por el contrato existente. No es una corrida física nueva ni validación |
| Error nativo | `r28–r29`: valor no convertible conserva motor aplicado y texto para corregir |
| Error de guardado | `r30–r31`: destino que es directorio; error visible, dirty/ruta original preservados y bytes originales sin cambio; luego se guarda correctamente |
| Contenido portable/corridas | `r32`, `r35`: vista de contenido y centro común de acceso |
| Cerrar/reabrir | `r36–r37`: proceso nuevo y archivo importado; diámetro aplicado y realmente enviado 87 mm, resultado VERIFIED/incomplete/NOT_CONVERGED |

Las capturas incluyen 980×740, 1360×820 y el tamaño inicial disponible de
1440×838. Se inspeccionaron cabecera, formularios, ayuda, resultados y estados de
error. En resultados 2T compactos persisten controles densos y recorte inferior:
UX-018 queda parcial. No se declara aceptación universal de resoluciones,
escalado, lector de pantalla o alto contraste.

`r01–r35` documentan el recorrido durante la implementación incremental. Tras
los últimos ajustes de orden de componentes, mayúsculas de unidades, cabecera
por eventos y cierre 0D protegido, `r36–r37` se tomaron en un proceso nuevo con
el contenido de fuente finalmente fijado en `cc5a12d`. Las 58 pruebas integradas
finales cubren ese contenido. Los hashes de las capturas no significan que todas
se hayan tomado sobre una única revisión intermedia idéntica.

## Regresiones y diagnósticos

Los resúmenes completos, con comandos y resultados, están en
`results/frontend-remediation-v1/verification/`. Los logs completos se conservan
localmente mediante run_logged; los resúmenes versionados bastan para identificar
la corrida y su salida. El recibo final selecciona sólo corridas exitosas sobre
la fuente final.

- Antes de las correcciones P0, seis regresiones reprodujeron los defectos.
- Integridad: borrador preservado ante notificaciones, cancelación sin worker,
  guardado str/Path y PermissionError, cierre transitivo con acceso al origen
  denegado, parcialidad explícita, legacy no promovido y rutas/destinos hostiles.
- Flujo: contexto/ayuda por familia, precisión intacta de campos no editados,
  transacción de referencia, bloqueo de cierre/exportación, modelo de creación,
  preflight A/B, presupuesto RPM, vínculo de resultado y orden/unidades tras abrir.
- La regresión protegida pasó 301 pruebas con 3 omitidas y cuatro avisos de
  deprecación NumPy. Usa los módulos de este worktree y evidencia histórica
  registrada, leída desde su contexto original.
- La regresión comercial/CP1/onboarding final pasó 18 pruebas.
- La regresión integrada final de frontend pasó 58 pruebas sobre la fuente
  entregada. Ver `frm-source-acceptance-final.summary.json`; los otros dos
  conjuntos finales son `frm-commercial-regression-final` y
  `frm-protected-accepted`. No se suman como pruebas únicas: sus alcances se solapan.

Se retienen también los diagnósticos fallidos: intento sin pytest en el entorno
de build, dos errores iniciales en nombres del fixture, nombre de módulo de test
inexistente, una raíz histórica incorrecta y una prueba de callback con registro
mínimo que disparaba el lector de resultados inválidos. Ninguno constituye una
aceptación. La prueba de callback se aisló del lector; el parseo de un resultado
real se comprobó en el recorrido 2T. Un timeout adicional se investigó sin
relajar guardas de borrador ni cambiar pruebas científicas. La limpieza de los
tests antiguos del shell 0D ahora descarta explícitamente su texto inválido antes
de cerrar; limitarse a poner dirty=false ya no equivale a resolver un borrador.
Sus aserciones y las pruebas de los contratos protegidos permanecen intactas.

## Límites de aceptación

IMPLEMENTED describe el código entregado. SOURCE_ACCEPTED exige los checks del
recibo y los recorridos de esta fase. WINDOWS_ACCEPTED sigue falso: no se probó
un paquete construido con estos commits. PENDING_UAT sigue verdadero para
aceptación representativa humana y accesibilidad. La revisión es SELF_REVIEW.
Los hashes de evidencia preservada y del código de aplicación están en el recibo.
P9 conserva tanto el blob Git como su hash canónico LF. No se modificaron solvers,
ecuaciones, tolerancias, contratos, umbrales ni evidencia histórica.

El primer recibo exigía que el puntero global main siguiera en su valor inicial;
ese supuesto no era válido para trabajo concurrente. El reflog muestra avances
externos de CP1/CP2 hasta `f97469b`. Se conserva ese dato y se comprueba en su lugar
el aislamiento de la rama y que su incremento no está integrado en main. No se
restauró ni modificó main para satisfacer el recibo. Integrar las dos líneas de
trabajo queda fuera del gate fuente de esta rama.
