# Autorrevisión de la entrega

Tipo: **SELF_REVIEW**. La misma persona/agente investigó y redactó la propuesta.
No se la presenta como revisión independiente ni como aceptación del producto.

## Cobertura del pedido

| Requisito | Comprobación |
|---|---|
| Versión integrada CP0/CP1/unificada | Revisión d44305c fijada; no se usó el paquete rc7 ni la carpeta CP0 antigua |
| Rama/worktree E: independientes | audit/dino-frontend-ux-v1; sin cambios en otros worktrees |
| Aplicación real | Windows/Qt 6.11.2, eventos QTest, capturas e inventarios por recorrido |
| Casos 2T/4T y errores | Puntos reales, curvas acotadas, cancelación, no convergencia, tiempo agotado, legacy e importación defectuosa |
| Navegación y organización | UX-004/005/006/010/012/013/014/021 y arquitectura propuesta |
| Motor/componentes | Edición observada y propuesta de esquema coordinado; no se afirmó que 2T careciera de diagramas existentes |
| Resultados y niveles de evidencia | Cuatro ejes independientes; sin promover datos de ingeniería o legacy |
| Proyectos/undo/recuperación/bundles/PDF | Ejercitados con las limitaciones documentadas por ruta |
| Accesibilidad/resoluciones | Compacto y teclado observados; lector/DPI múltiples pendientes y explicitados |
| A. Diagnóstico | 23 fichas con categoría, ubicación, impacto, evidencia y causa probable |
| B. Diseño | Arquitectura, recorridos, adaptadores, HTML ilustrativo y tres SVG/PNG renderizados |
| C. Backlog | Cada ítem tiene capa, dependencias, aceptación y verificación; todos propuestos/no activados |
| D. Decisión crítica | Reorganización incremental comparada con cambio cosmético y reescritura total |
| Restricciones de producto | Sin cambios en motorsim, solvers, tests, fixtures ni packaging; sin candidato nuevo ni push |

## Reconciliación crítica

- Los tres P0 tienen reproducción en ejecución. La pérdida de borrador se
  contrasta con la configuración realmente enviada al worker. La portabilidad
  falla al abrir las referencias importadas. El fallo de Guardar deja una
  diferencia observable entre el archivo y el contexto y genera una excepción
  del producto fuera del bloque de manejo de errores.
- No se confundió una carencia del alcance global con un incumplimiento de CP1:
  la cola actual se reconoce como 4T 0D y su generalización es una propuesta.
- No se declaró que la validación de entrada no funcione: el valor aplicado
  permaneció intacto en los rechazos; se criticó la recuperación y localización
  del error.
- El 2T no convergido conserva sus rótulos y huecos. El 4T 0D convergido conserva
  su naturaleza de referencia. Integridad de archivos no equivale a validación.
- La equivalencia funcional y UAT del futuro rediseño siguen pendientes. Los
  wireframes no activan funciones científicas nuevas ni reemplazan proyectos.
- El HTML tuvo revisión estructural/sintáctica, no interacción en navegador:
  el conector no tenía navegadores disponibles. Los SVG se renderizaron y se
  corrigió un problema del renderer offscreen que inicialmente producía glifos
  de reemplazo; los PNG finales contienen texto legible con fuente real cargada.
- Los timeouts, errores de inspección y aceptación manual de modales del harness
  se conservan y se distinguen de los defectos del producto.
- Se preservaron los datos externos de auditoría, incluido el original de la
  recuperación y las copias de fixtures. No se limpiaron resultados históricos.
- Una primera comprobación del hash P9 usó bytes CRLF del checkout Windows y
  falló. Se conservó ese resultado como `delivery-check-initial-crlf.json`.
  El verificador se corrigió para usar la normalización LF ya definida por
  `program_status.py`; además comprueba el blob Git congelado y la igualdad
  entre éste y el checkout normalizado. El hash esperado y el spec no cambiaron.

## Verificación reproducible

`audit_tools/frontend_audit/verify_delivery.py` comprueba categorías, IDs,
dependencias, enlaces, capturas/hashes, campos de backlog, reproducción de P0,
recuperación, runtime y ausencia de cambios de producto/fixtures. El resultado
y el número de comprobaciones están en
`results/frontend-audit-v1/delivery-check.json`.

El hash P9 se comprueba exactamente. No se relanzó ni se cerró la regresión CP1
en curso: ésta es una aceptación de documentos/evidencia de investigación, no
de una versión nueva del producto. Las limitaciones completas se conservan en
[metodología](metodologia.md).
