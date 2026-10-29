# Evaluación funcional Desktop — recorrido y mejoras de producto

## Actualización tras desbloquear Windows (2026-10-29)

Esta sección sustituye el estado inicial de las secciones inferiores, conservadas como registro de la primera pasada. Se utilizó mouse/teclado Windows sobre rc9 y después sobre Desktop de desarrollo. No se modificó rc9 ni se generó un build. Las correcciones de desarrollo aún no tienen aceptación de distribución.

### Recorrido observado

| Escenario | Evidencia real y resultado | Límite |
|---|---|---|
| Crear motor | rc9: `synthetic-product-review`, nombre `SYNTHETIC 125`, datos supuestos explícitos | No representa un motor medido |
| Cilindro/cárter/distribución | Desarrollo: diámetro 56,5 mm, cárter en PMI 360 cm³, altura de transferencia primaria 12,4 mm; aplicar y guardar; eventos y cilindrada actualizados | Captura 36; no cambio de leyes físicas |
| Admisión/láminas/transferencias | rc9 ocultaba el editor. Desarrollo corregido: admisión 85 mm, transferencia primaria 52 mm, rigidez reed-1 1100 N/m; guardado y reapertura gráfica conservan valores (34) | Láminas cuasiestáticas; aviso explícito de parámetros dinámicos no utilizados |
| Escape | rc9: duplicación `escape-plus20`, primer tramo 83 → 103 mm, guardar en variante; base conservada (07–11) | Cambio geométrico sintético, sin predicción de ganancia |
| Persistencia y duplicación | Guardar por diálogo nativo, abrir nuevamente el proyecto y verificar variante/escape. Proyecto `synthetic-user.dino2t.json`. Desarrollo reiniciado y proyecto `development-inputs.dino2t.json` reabierto (34) | La reapertura de proyecto en rc9 y el reinicio de aplicación en desarrollo se distinguen |
| Ejecutar/progreso | rc9: base y variante, 3000 RPM, un ciclo cada una, 44 celdas, presupuesto 60 s, 1 worker; 9,31 y 9,20 s declarados por resultados (14–17) | MAX_CYCLES_NONCONVERGED; sin campaña periódica |
| Cancelar/recuperar | rc9: tercera ejecución con horizonte de 3 ciclos, cancelada y conservada con 2 ciclos completos; CANCELLED_CHECKPOINTED. Reanudar desde historial y completar ciclo 3 (20,22,23,25) | Checkpoint válido; resultado final sigue NOT_CONVERGED |
| A/B y trazas | rc9: seleccionar las dos corridas de un ciclo en historial y comparar; presión de escape y mapa celda/ángulo disponibles (25–29) | Conservación interna, sin auditoría independiente; no se presenta como ganancia confirmada |
| Potencia/torque/RPM | rc9: opción explícita de mostrar transitorios, marcadores huecos y rechazo de curva definitiva. Desarrollo: histórico compatible de 30 puntos, curvas A/B HP y torque y RPM comunes (40–41) | Histórico sintético; PERIOD_1 es clasificación histórica declarada, no validación ni revalidación científica |
| Exportar/reutilizar | rc9: CSV de curva transitoria. Desarrollo: exportación histórica real por diálogo nativo, CSV + JSON; reapertura por servicio conserva exactamente los 30 puntos, 3 inválidos, unidades e identidades | Reapertura gráfica del CSV pendiente: Windows volvió a rechazar entrada con `no active desktop`; no se sustituye con el test |

Corridas rc9 bajo la raíz de artifacts configurada de Desktop, carpeta relativa `exploratory-workflow-v1/synthetic-product-review/`: `216eb4171cb741d2920a4987a19f2b15`, `2fdede26df6a40df9ecb92377fa1cd1b`, `f76e2ef44b1f41609258bc0e73480341`. Se conservaron todos los artifacts. No hubo búsqueda de periodicidad ni cambios de CFL, tolerancias o modelos. V2/MUSCL/Brent no fueron promovidos por estas correcciones.

Histórico original reutilizado, sin recalcular: raíz de artifacts existente, `engine-physics-v1/full-rpm-sweep-v1-impl2/authorized-extension-26-v1/reports/impl2-full-rpm-sweep-30-points.json`. `historical-preservation.json` registra su hash y la comprobación exacta de conservación al exportar. Sus valores no se interpretan como prestaciones reales.

### Matriz revisada por uso real

La comparación documental oficial de abajo sigue vigente. La evidencia práctica actual cambia las clasificaciones Dino de esta forma:

| Capacidad | Clasificación tras uso real |
|---|---|
| Crear, escape, guardar/reabrir/duplicar, ejecución acotada, cancelación y recuperación | U: recorrido gráfico observado |
| Cilindro/cárter/distribución | U con fricción de altura/scroll e identificadores técnicos; edición gráfica en desarrollo |
| Admisión/láminas/transferencias | C en navegación rc9 → U en desarrollo corregido; enlace al solver cubierto por prueba focalizada |
| Superposición A/B, presión y mapa celda/ángulo | U exploratorio, con estados y límites visibles |
| Potencia HP/kW/CV y torque | U: HP/torque y kW observados; conversión CV no recorrida gráficamente en esta pasada |
| Lectura precisa por RPM | U tabular; histórico muestra huecos inválidos y rechaza deltas incompatibles |
| Exportación histórica | D rc9 → U por servicio en desarrollo, exportación GUI comprobada; reapertura GUI pendiente |
| Variables de llenado/barrido y PV | C/NV; no se amplía el alcance físico ni se deduce usabilidad de una clase |
| Medición de banco | NV en este recorrido; no equivale a ausencia ni a validación |
| Disco rotativo, multicilindro y automatización de optimización comercial | F: no implementarlos para completar esta entrega |

### Defectos observados y conjunto implementado

| ID | Prioridad | Reproducción/esperado | Corrección y evidencia |
|---|---|---|---|
| INPUT-NAV-01 | P1 | Abrir rc9: no existe entrada visible a conductos/transferencias/láminas pese a existir el editor interno | Añadir entrada a navegación principal reutilizando editor; prueba de clic de pestaña y GUI 30–34 |
| RECOVERY-01 | P2 | Introducir texto en área de lámina, aplicar (rechazo correcto), descartar: valores vuelven pero navegación conserva cruces de error | Emitir cambio de estado al refrescar; regresión y GUI 35 muestran valores y marcas válidas restaurados |
| MESH-01 | P2 | Opciones avanzadas desmarcadas mantienen tabla deshabilitada ocupando espacio; encabezado dice 1/2/4 aunque hay 3/5/6 | Contraer realmente y corregir encabezado, preservando discretización; GUI 38–39 y prueba de counts |
| EXPORT-01/02/03 | P1/P2 | Exportación histórica no podía reutilizarse con su propio importador | Corrección ya comprometida en ac0df82, ahora exportada por GUI con histórico real; preservación exacta comprobada |
| LABEL-01 | P2 | Roles/IDs ingleses y procedencias extensas dificultan lectura | Pendiente; no impide completar el recorrido |
| LAYOUT-01 | P2 | Mucho scroll y campos parcialmente visibles; historia reduce espacio de análisis; etiquetas de tramos cortos se solapan | Pendiente; ocultar historial permite trabajar, sin reconstrucción de interfaz |
| POLISH-01 | P3 | Etiquetas de largo/diámetro en el perfil se solapan en tramos breves | Pendiente refinamiento de dibujo |

No se demostró un P0. El rechazo de deltas del histórico por identidades incompletas y la ausencia de curvas definitivas para ejecuciones no periódicas son protecciones correctas.

### Verificación y aceptación

Pruebas focalizadas: `navigation-tests.txt` (3 PASS: navegación/recuperación, malla, roundtrip histórico), `followup-tests.txt` (3 PASS) y `solver-binding-test.txt` (1 PASS: admisión/transferencias/láminas persisten y llegan al solver). El test de exportación verifica estados, unidades, identidades, protección de JSON existente y rechazo de CSV alterado. Son pruebas funcionales de código fuente, separadas de las capturas de uso real.

Regresión completa de Desktop: `desktop-regression.txt`, **24 PASS, 1 SKIP, 228,42 s**. El omitido requiere la raíz histórica externa configurada en el entorno aislado de tests; el reporte real sí fue utilizado en la GUI y comprobado aparte. Revisión: SELF_REVIEW, no revisión independiente.

Aceptación: mejoras de fuente verificadas focalizadamente, por regresión completa y por interacción gráfica para entrada/recuperación/malla; distribución protegida intacta. Evaluación gráfica sustancial completada; queda únicamente cerrar reapertura gráfica del CSV exportado. No se declara nueva versión READY_TRIAL ni validación predictiva. Siguiente acción concreta: reabrir `historical-gui-export.csv` desde «Abrir datos» con Windows activo y comprobar aviso histórico/30 puntos; después consolidar la aceptación de fuente antes de proponer cualquier paquete.

## Registro de la primera pasada (anterior al desbloqueo)

## Alcance y aceptación

Estado: PARCIAL. rc9 protegido se abrió e interactuó gráficamente mediante mouse y teclado Windows. La sesión se bloqueó durante el diálogo de guardado. No se afirma haber completado los diez escenarios por GUI. No se lanzó simulación ni build. La corrección de exportación se verifica en código fuente mediante prueba funcional de Desktop, no en rc9.

Capturas reales: `captures/01-rc9-start.png`, `02-new-dialog.png`, `03-save.png`, `04-new-filled.png`, `05-desktop-state.png`. La última demuestra el impedimento del entorno, no un defecto de Dino. El proceso rc9 se deja abierto en el diálogo de guardado; no se fuerza su cierre ni se guarda sobre proyectos existentes.

## Matriz funcional

Fuentes oficiales: [EngMod2T](https://vannik.co.za/EngMod2T.htm), [Post2T outputs](https://vannik.co.za/EngMod2T%20-%20Outputs.htm), [MOTA overview](https://www.iwt.com.au/mota-software/overview/), [MOTA samples](https://www.iwt.com.au/mota-software/samples/). Consulta 2026-10-29. El enlace al manual desde la página oficial de MOTA devuelve 404; no se atribuyen detalles no consultados. La documentación muestra capacidades anunciadas, no una prueba independiente de precisión.

Leyenda: U=implementada y usable; D=implementada con dificultad; C=núcleo sin acceso Desktop demostrado; A=ausente/necesaria; F=fuera del alcance. NV indica falta de nueva comprobación gráfica, no ausencia de función. Evidencia previa: `results/dino-trial-rc9-package-acceptance-20261029/receipt.json`; no sustituye este recorrido práctico.

| Capacidad | Referencia comercial documentada | Dino y evidencia | Clasificación |
|---|---|---|---|
| Crear motor monocilíndrico | MOTA: dimensiones por menús; EngMod: preprocesador Dat2T | Diálogo real, nombre sintético y motor creados; valores iniciales marcados supuestos | U, GUI parcial |
| Cilindro/cárter/unidades | MOTA exige geometría completa | Controles mm/cm³ y magnitudes derivadas visibles en rc9; modificación y límites no probados en GUI actual | D/NV |
| Distribución/puertos/transferencias | MOTA admite cambios de porting | Tabla rc9 muestra eventos derivados y roles técnicos en inglés; edición profunda NV | D/NV |
| Admisión/láminas | MOTA anuncia pistón, láminas y disco | Selector rc9 pistón/láminas visible; pruebas funcionales existentes de unión al solver; disco fuera del alcance implementado | U para selector, NV edición; F disco |
| Escape dimensional | MOTA cámara/silenciador; EngMod análisis de ondas | Página Escape y comparación existentes; no recorrida durante esta prueba | NV, sin nueva certificación |
| Guardar/reabrir/duplicar | Recorrido necesario del producto | Guardado alcanzó diálogo Windows; bloqueo impidió confirmar; duplicación no recorrida | NV |
| RPM, modelos y recursos | MOTA ejecución y comparación; EngMod simulador separado | Barra rc9 muestra 3000 rpm, 1 ciclo, 60 s; no ejecución nueva | NV |
| Progreso/cancelación/checkpoint | Documentación consultada no permite comparar detalle | Aceptación previa rc9; nueva interacción pendiente | NV |
| Potencia HP/kW/CV y torque | Post2T curvas por RPM; MOTA gráficos de prestaciones | Selector y panel existentes; sin nuevo uso gráfico ni curva calculada | NV |
| Superposición A/B/lectura RPM | Ambas herramientas comparan configuraciones | Evidencia previa y pruebas existentes; recorrido gráfico pendiente | NV |
| Presión/flujo/PV por ciclo | Post2T clasifica resultados por ángulo, RPM y desplazamiento | Vistas requieren primarios auditables; no comprobadas gráficamente ahora | NV; no declarar ausente |
| Llenado/barrido | Post2T anuncia delivery ratio | Transporte existe; acceso específico y significado físico no verificados; no añadir controles sin cierre identificado | C/NV |
| Mediciones | Post2T importa trazas y curvas de banco | Importación y contraste existentes; GUI actual pendiente | NV |
| Exportar/reutilizar histórico | Post2T datos numéricos reutilizables | CSV de Desktop antes no tenía JSON requerido por su propio importador; corregido y prueba funcional pasa | D → U automatizado, GUI pendiente |
| Reabrir CSV exploratorio | Reutilización necesaria, alcance de tabla frente a evidencia | Exportación tabular no contiene los primarios que exige auditoría; aviso explícito conserva artifacts originales | D; no se concede validación por CSV |
| Multicilindro/turbo/optimización automática | EngMod multicilindro/mapas; MOTA optimizadores | No requisito de esta entrega monocilíndrica | F |

## Escenarios de la prueba real

1. Crear: alcanzado; nuevo proyecto `synthetic-product-review`, motor `SYNTHETIC 125`.
2. Configurar geometría: controles visibles; no se certifica edición completa.
3. Escape: pendiente.
4. Guardar/cerrar/reabrir/duplicar: diálogo de guardado alcanzado; operación sin confirmar por bloqueo Windows.
5–9. Simulación, cancelación, recuperación, curvas, A/B y trazas: pendientes de uso gráfico en esta evaluación. Ninguna campaña iniciada.
10. Exportar/reutilizar: defecto reproducido por contrato importador/exportador y corregido con prueba funcional automatizada, sin presentarlo como prueba GUI.

## Defectos y fricciones priorizados

| ID | Prioridad | Evidencia y reproducción | Esperado/cambio mínimo | Estado |
|---|---|---|---|---|
| EXPORT-01 | P1 | Importar reporte histórico, exportar tabla CSV, abrir CSV exportado: faltaba JSON compañero requerido por `load_results` | Exportar CSV + JSON con identidades, unidades, clasificación, valores y hash del CSV; reabrir por ruta existente | Implementado; test funcional |
| EXPORT-02 | P1 | CSV histórico reabierto se trataba como importación externa genérica, mientras JSON se identifica histórico | Leer schema del compañero también para CSV y conservar aviso histórico/sintético | Implementado; test funcional |
| EXPORT-03 | P2 | Tabla exploratoria no es paquete de primarios y no sirve como archivo de recuperación | Explicar en tooltip y confirmación qué conservar para reabrir; no inventar evidencia desde CSV | Implementado |
| LABEL-01 | P2 | Captura 01: `intake`, `transfer`, `exhaust`, identificadores internos en tabla de lumbreras | Etiquetas en español con identificadores técnicos disponibles en detalles, tras probar edición | Pendiente |
| INPUT-01 | P2 | Captura 01: procedencias extensas y campos `sin clasificar`; formulario inicia en plantilla | Mejorar lectura por grupos sin sustituir datos desconocidos ni inferir geometría real | Pendiente; observar edición antes de modificar |
| ENV-01 | Bloqueo externo | Captura 05 y error real `no active desktop` | Desbloquear sesión Windows y continuar recorrido desde guardado | Pendiente |

No hay P0 de producto demostrado. No se confunden el bloqueo de Windows ni la falta de datos experimentales con defectos de la interfaz.

## Implementación y límites

Se reutiliza el schema histórico y el importador existentes. Se mantienen unidades, identidades y puntos inválidos como huecos; se verifica el hash al reabrir. El compañero existente se protege frente a sobrescritura. Se informa al usuario que ambos archivos son necesarios. No se cambia física, baseline, versión empaquetada ni selección experimental.

La nueva prueba usa datos sintéticos inválidos a propósito, exporta, reabre por el servicio y la página de Desktop, comprueba procedencia histórica, estados/unidades/identidades, protección del compañero y rechazo de CSV alterado. La aceptación gráfica y el caso real histórico del entorno siguen pendientes; el test histórico existente puede omitir por falta de raíz configurada.

Siguiente trabajo concreto: con Windows desbloqueado, completar guardar/reabrir/duplicar, editar escape e iniciar/cancelar un punto acotado; después cargar históricos compatibles, recorrer A/B/trazas y probar el CSV+JSON desde la interfaz de desarrollo. No se necesita un build para esa comprobación. Solo después corresponde decidir aceptación integrada.
