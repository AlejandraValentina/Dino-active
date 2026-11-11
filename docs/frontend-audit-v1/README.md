# Auditoría integral del frontend de Dino

**Revisión del producto:** `d44305c` · **Fecha:** 11 de noviembre de 2026.

Se auditó la aplicación fuente integrada con CP0, CP1 y navegación unificada.
El diagnóstico contiene **23 hallazgos: 3 P0, 11 P1, 7 P2 y 2 P3**. Las mejoras
están propuestas; no se implementaron cambios en el producto.

| Entregable | Documento |
|---|---|
| A. Diagnóstico, impacto, causas y evidencia | [Diagnóstico UX/UI](diagnostico.md) |
| Método y cobertura de recorridos | [Metodología y limitaciones](metodologia.md) |
| B. Organización de pantallas y migración | [Propuesta de rediseño](rediseño.md) |
| B. Prototipo y wireframes | [HTML navegable](wireframes.html) · [Modelo](wireframes/modelo.svg) · [Simulación](wireframes/simulacion.svg) · [Resultados](wireframes/resultados.svg) |
| C. Prioridades, capas, dependencias y aceptación | [Backlog ejecutable](backlog.md) |
| D. Evolución frente a reorganización | [Evaluación crítica](rediseño.md#evaluación-crítica-de-alternativas) |
| Evidencia y datos estructurados | [Índice](../../results/frontend-audit-v1/evidence-index.json) · [Hallazgos JSON](../../results/frontend-audit-v1/findings.json) |
| Control final de entrega | [Autorrevisión](self-review.md) |

## Hallazgos que deben resolverse primero

1. **UX-001:** el nativo permite ejecutar el modelo aplicado mientras el editor
   muestra un cambio pendiente; el borrador puede perderse al refrescar resultados.
2. **UX-002:** el bundle nativo no transporta todas las dependencias necesarias
   para abrir las corridas después de importarlo.
3. **UX-003:** Guardar después de importar un proyecto nativo falla por tipo de
   ruta y no informa el error en pantalla.

La recomendación es una reorganización incremental de la experiencia, con
contexto persistente, edición transaccional y recorridos comunes sobre los
servicios existentes. Se mantienen independientes 2T, 4T nativo y 4T 0D.

Esta entrega es investigación/diseño y una **SELF_REVIEW**. No acepta el producto
ni acredita precisión, calibración, validación experimental o predictividad.
El HTML es una propuesta sin UAT en navegador; los SVG fueron renderizados.
