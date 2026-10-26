# DINO Commercial Readiness V1 — aceptación funcional

Fecha: 2026-10-26. Resultado: **PASS funcional TRIAL** para el recorrido Desktop solicitado. La evaluación cubre uso desde el EXE empaquetado. Los resultados de una vuelta son transitorios; no se afirman periodicidad, validación experimental ni validación comercial.

## Recorrido comprobado

- Se creó y guardó un diseño desde Dino Desktop, se duplicó la variante y se editó el escape: el primer tramo cambió de 83 mm a 103 mm.
- El EXE ejecutó dos puntos integrados breves a 3000 RPM: base en 9.620 s y variante en 9.838 s. Ambos quedaron `MAX_CYCLES_NONCONVERGED` / `INSUFFICIENT_CYCLES`, correctamente identificados como `TRANSIENT_ESTIMATE`.
- Se recuperaron ambas corridas en Análisis y se compararon en el EXE. Se obtuvo una fila común a 3000 RPM, estado `EXPLORATORIO` y advertencia `TRANSITORIO: diferencia de estimaciones, no ganancia estacionaria`. No aparecieron filas ficticias ni `INCOMPATIBLE` para este par.
- El CSV exportado desde el EXE contiene dos filas con sus hashes, identidades de solver/implementación, RPM, clasificación, periodicidad y estimaciones transitorias. Se verificó su hash tras copiarlo a la carpeta de evidencia.
- Se cerró y relanzó el EXE empaquetado, se reabrió el proyecto guardado y se comprobó que conserva una variante de escape, con longitud 1.099 m frente a 1.079 m de la base.
- Las seis referencias periódicas existentes se reutilizaron para revisar la vista de curvas históricas. No se repitieron campañas ni barridos.

## Causa y corrección de `INCOMPATIBLE`

Los dos resultados de 3000 RPM sí tienen identidades compatibles: mismo solver, implementación, combustible, modelo de pérdidas, contrato de periodicidad e inventario de 44 celdas. Sus hashes de configuración y de resultado difieren porque representan dos configuraciones de escape distintas.

El error visible provenía de `ResultsPage`: al seleccionar corridas locales inyectaba en la comparación el grid RPM del recipe del proyecto (8000/9000/10000), creando puntos `NOT_STARTED` que el comparador mostraba como `INCOMPATIBLE`. Se corrigió el origen: el recipe RPM sólo se aplica cuando los hashes importados pertenecen a las referencias guardadas de ese proyecto. La regresión también comprueba que transitorios compatibles siguen siendo comparables y permanecen explícitamente exploratorios.

Los puntos periódicos históricos que carecen de identidades antiguas siguen separados de este par local; no se les inventaron hashes ni se relajaron las reglas de compatibilidad.

## Regresión y paquete

- Regresión focalizada: **28 PASS** en `test_power_curve.py`, `test_dino_commercial_readiness_v1.py` y `test_dino_desktop_ux_v2.py`.
- EXE TRIAL construido desde commit `fc27542155840cdadbcc2b591ae5cd8e99031899`, `source_dirty=false`; el ZIP pasó `testzip` (1.636 entradas).
- SHA-256 ZIP: `2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`.
- La aplicación se abrió y usó directamente desde el paquete Windows sin ejecutar Python para el usuario. El paquete anterior se conservó.

## Evidencia

- `../captures/17-transient-compatible-v4.png` — comparación compatible del par transitorio dentro del EXE.
- `../captures/18-project-reopened-v4.png` — proyecto persistido después de cerrar y relanzar el EXE.
- `../exports/transient-compatible-v4.csv` — exportación de dos resultados con metadatos.
- `recovery.json` y `receipt.json` — identidades, longitudes, hashes y resumen reproducible.

La aceptación es funcional de producto TRIAL. No es una afirmación de rendimiento estacionario ni de validación física/experimental.
