# EXHAUST_MESH_V1 — alcance y resultados

El adaptador crea 1, 2 o 4 celdas axiales por sección geométrica lineal circular. Conserva caras de interfaz únicas, longitud y diámetros extremos de cada sección, calcula el área de cara y el volumen exacto del tronco de cono, y remapea conservativamente masa, especies y energía. El adaptador legacy de una celda por sección sigue sin cambios. La selección se integra al diseñador Desktop y al proyecto; la vista muestra las subdivisiones y la geometría derivada.

El IntegratedEngine2T ya usa flujo HLLC multiplicado por área de cara y la fuente cuasi-1D de cantidad de movimiento `p (A_right - A_left) / V`. La refinación reutiliza esa ruta y el integrador SSPRK2 existente. Las pruebas muestran balance estático con área variable, reducción a área constante, flujo de onda ante una perturbación y CFL con celdas refinadas. No se cambió ninguna ecuación del solver.

## Evidencia diagnóstica

Se ejecutaron seis puntos de un ciclo a 3000 RPM: escape original y escape modificado, cada uno con 1/2/4 celdas por sección. El wall time secuencial fue 360.797 s; cada primary pasó auditoría independiente recomputada y los seis ledgers de masa, energía y especies pasaron. Los máximos de CFL observados no excedieron 0.4. No se evaluó periodicidad.

Las diferencias de presión entre resoluciones no disminuyen de 1→2 a 2→4. En promedio RMS por puntos físicos del escape, la diferencia A/B fue 65, 86 y 114 Pa para 1, 2 y 4 celdas; el cambio por refinamiento fue mucho mayor. El flujo de masa en interfaces A/B también creció con el refinamiento. La respuesta de diseño no se estabilizó respecto del error espacial y no se puede hacer un ranking cuantitativo de diseños.

Cuatro celdas son una opción razonable para nuevos diagnósticos exploratorios de sensibilidad; dos sirven para edición interactiva. Ninguna resolución está demostrada como independiente de malla. Un siguiente estudio con ocho celdas por sección tiene justificación técnica, pero queda fuera de esta matriz.

Los resultados son sintéticos, exploratorios y de un ciclo. No constituyen comparación de prestaciones periódicas ni validación experimental. La matriz y su verificación están resumidas en `results/exhaust-mesh-v1/final-receipt.json`; los artifacts completos están bajo `${DINO_ARTIFACT_ROOT}/exhaust-mesh-v1`.
