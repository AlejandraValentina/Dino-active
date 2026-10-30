# Desktop como banco de diseño — primera implementación vertical

Fecha: 2026-10-30. Alcance: PySide6, un ejecutable, presentación y navegación. No se cambia solver, física, proyectos ni contratos de resultados. rc7/rc9 protegidas; sin builds ni campañas periódicas. Revisión SELF_REVIEW.

## Contraste del diagnóstico

Se contrastó la observación UX proporcionada por el dueño y los documentos externos disponibles en `docs/audits/`. Esos documentos contienen principalmente observaciones científicas; no se atribuye a DeepSeek un inventario UX adicional no disponible. La aceptación previa `results/desktop-product-maturity-v1/csv-gui-acceptance.json` ya demostraba CSV histórico de 30 puntos. Esta tarea vuelve a comprobar el recorrido después de cambiar la navegación.

Referencia funcional oficial consultada: [EngMod2T](https://vannik.co.za/EngMod2T.htm) distingue construcción del modelo, simulación y postproceso. Se adopta esa secuencia dentro de Dino, sin reproducir su apariencia ni su separación en programas. La consulta de Outputs en esta sesión devolvió timeout; se conserva la comparación documental anterior sin inventar detalles nuevos.

| Capacidad observada | Estado antes | Cambio / límite |
|---|---|---|
| Motor, cárter, puertos, conductos, láminas y escape | Existentes; formularios utilizables, organización agrupada y scroll | Editores conservados en MODELO. Cárter sigue siendo volumen y culata compresión/volumen derivado; no se fabrica una geometría de culata |
| Guardar/reabrir, duplicar variantes | Existentes y comprobados por GUI | Nuevo motor / Abrir / Guardar visibles siempre; gestión de variantes desde explorador |
| Simulación puntual y recuperación | Existentes; preparación escondida en diálogo | SIMULAR accesible directamente; misma página y controles, estado/cancelación persistentes |
| Barrido y A/B paralelo por RPM | Existentes; no ausentes | Preflight gráfico de 2 variantes × 2 RPM, 3 workers supervisados; cancelado antes de ejecutar. Serial sigue predeterminado |
| Curvas de potencia/torque y A/B | Existentes pero enterradas bajo mediciones y metadata | Vista Curvas inicial en RESULTADOS; selección de series y unidades existentes |
| CSV histórico reutilizable | Existente y aceptado, no faltante | Exportación y reapertura gráfica repetidas sólo para verificar la integración nueva; 30 puntos, identidades y huecos conservados |
| Presiones/ondas/variables | Existentes para primarios compatibles; difíciles de localizar | Vistas propias; un agregado de curvas no crea trazas ni geometría |
| Hashes, rutas, recibos y Run ID | Existentes y excesivamente presentes | Ruta y detalle del punto en Trazabilidad; dock accesible para identidad/provenance; Run ID sigue en configuración avanzada de ejecución |
| Llenado/barrido y BSFC de la ruta integrada | Capacidades parciales del núcleo; no hay resultado definido general demostrable en Desktop | No se añaden controles ni se convierten estados UNDEFINED en valores |
| Mapa geométrico detallado de culata, red arbitraria, nuevos modelos físicos | Realmente fuera de la representación actual | No implementados en esta entrega; no se dibujan formas ficticias |

El diagnóstico central de organización interna se confirma; el diagnóstico de ausencia de A/B, exportación reutilizable o paralelismo sería incorrecto. Las capturas `01–03` documentan el estado anterior real, no una recreación.

## Implementación

- Tres modos visibles: MODELO, SIMULAR, RESULTADOS. El componente de ejecución existente pasa a espacio propio sin traslado repetido a un diálogo. Se mantienen aliases internos para consumidores existentes.
- Acciones persistentes para comenzar/abrir/guardar, explorar variantes/corridas/comparaciones y consultar trazabilidad. El menú permanece accesible en compacto.
- Explorador único con vistas de corridas/comparaciones y variantes, reutilizando historial, selección, checkpoint y gestión de variantes.
- RESULTADOS abre en Curvas; Variables, Presiones y ondas, Comparar, Mediciones y Trazabilidad reutilizan los widgets originales. Las vistas tienen scroll propio y conservan procedencia/estado científico visibles.
- Los paths y hashes no encabezan las curvas. No se borran campos ni recibos. El proyecto mantiene su estado sintético y la distinción entre transitorio, periodicidad histórica declarada y validación experimental.

## Recorrido gráfico

Interacción real Windows mediante mouse/teclado sobre Desktop de fuente. No se presenta como prueba de un paquete nuevo.

1. Nuevo motor desde botón visible: proyecto `synthetic-workbench-v1`, nombre sintético; diámetro 56,5 mm, cárter editado a 360 cm³, validar/aplicar.
2. Guardar con diálogo nativo; cerrar aplicación y reabrir el proyecto. Archivo `synthetic-workbench.dino2t.json`.
3. Duplicar como `escape-plus20`; editar primer tramo de 83 a 103 mm y guardar en variante actual. El escape base permanece en 83 mm.
4. SIMULAR → Curva RPM: seleccionar A/B con base, 3000/3500 RPM, 1 ciclo, 120 s agregado. Preflight PASS con procesos y límites declarados (`06`). No se ejecutó ese barrido.
5. Ejecutar un único punto a 3000 RPM, 1 ciclo, 60 s y límites existentes. Termina en 8,79 s declarados, `MAX_CYCLES_NONCONVERGED`, `INSUFFICIENT_CYCLES`, un checkpoint (`07`). No se buscó periodicidad.
6. Abrir histórico compatible de 30 puntos desde RESULTADOS y observar curvas superpuestas HP/torque (`08`). Los valores antiguos no se reinterpretan como prestaciones predictivas.
7. Exportar tabla CSV mediante diálogo nativo a `workbench-historical.csv` con JSON compañero.
8. Abrir ese CSV desde Desktop; Trazabilidad confirma ruta, 30 puntos, SYNTHETIC, NOT_PERFORMED (`09`). Las comprobaciones de conservación del importador existentes siguen vigentes.

## Pruebas y alcance de aceptación

`regression.txt`: 37 PASS, 1 SKIP, 261,64 s. El omitido requiere la raíz histórica externa configurada en el entorno aislado; el histórico sí se usó en la GUI. `final-focused-tests.txt`: 9 PASS después de los ajustes de trazabilidad. `explorer-test.txt`: 1 PASS después de separar vistas del explorador. Las expectativas de dos modos/etiquetas antiguas se actualizan al alcance aprobado; los contratos físicos no se modifican. La prueba de cabeceras selecciona ahora Variables, donde vive la tabla, y conserva sus criterios de anchura y ausencia de scroll horizontal a 1360.

Defectos detectados durante integración: área de simulación inicialmente oculta por el reparentado, reubicación antigua de trazas que competía con la nueva vista y altura insuficiente del historial al apilar el árbol. Corregidos; no se ocultan fallos de las pruebas iniciales (`focused-tests*.txt`).

El encabezado de resultados ahora resume los puntos y estados cargados, sin conservar «sin corrida seleccionada» después de importar ni métricas del conjunto anterior. Procedencia extensa, rutas y detalle se consultan en Trazabilidad; la leyenda de curvas mantiene el aviso experimental visible. `final-result-tests.txt` y `compact-result-tests.txt`: 4 PASS cada uno para estos ajustes posteriores a la regresión completa.

`selection-tests.txt`: 4 PASS después de limpiar también la selección previa al cambiar de conjunto, para que el primer clic sobre un punto vuelva a consultar sus detalles.

Comprobación visual final: `11-final-explorer.png` muestra la corrida real en el explorador; `12-transient-results.png` conserva los marcadores exploratorios; `13-compact-results.png` muestra las curvas con scroll en una ventana nativa de 1225×850 px a escala Windows 125 % (aproximadamente el tamaño lógico admitido de 980×680); `14-final-results.png` muestra la versión final maximizada. Se conservan menús y acciones, y las curvas son accesibles en compacto con desplazamiento vertical. La reducción adicional de ese scroll queda como mejora, sin afirmar que todo el contenido cabe simultáneamente en el tamaño mínimo.

Aceptación: primera vertical funcional de fuente. No es READY_TRIAL de distribución ni cierre científico. Pendientes de producto: división posterior más clara de cilindro/cárter/lumbreras, reducción adicional de textos de simulación, etiquetas técnicas en español y solapamiento de rótulos en tramos breves del escape. No requieren ni autorizan nuevos modelos. La validación predictiva continúa dependiendo de datos externos y E1.3 de presupuesto; no se reabren aquí.
