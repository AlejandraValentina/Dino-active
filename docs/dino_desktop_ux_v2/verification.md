# Verificación visual y funcional

Se preservaron íntegros el informe Opus y las 17 capturas previas en `reference/`. Las capturas posteriores están en `captures/after/` y sus hashes, dimensiones y condiciones constan en `results/dino-desktop-ux-v2/visual-check-receipt.json`.

La ventana Dino 2T se abrió en Windows y se capturó por su área de ventana. Además, el smoke funcional ejecutó en memoria el flujo de crear, editar, renombrar y duplicar variantes; editar el escape sin solver; guardar y volver a abrir un proyecto temporal; preparar preflight sin iniciar una simulación; y comparar dos corridas EXPLORATORY preexistentes referenciadas desde dos artifact roots. El importador normal reaudita ambas. No se inició ningún solver.

Se renderizaron los layouts 1360×900 y 980×680 usando QPA offscreen y factores Qt 100 %, 125 % y 150 %. El cambio global de escala de Windows no se alteró; las escalas 125 % y 150 % son simulación de Qt, no una comprobación del ajuste de pantalla del sistema.

Los resultados abiertos son exploratorios y no identificaron periodicidad. Los diagnósticos de escape continúan sin demostrar independencia espacial. La verificación no promueve esas conclusiones ni cambia evidencia científica.


## Aceptación del paquete Windows (2026-10-14)

El paquete TRIAL final se inició desde su directorio de distribución con `%TEMP%` como directorio de trabajo. La aplicación abrió el proyecto temporal de ejemplo con referencias explícitas a dos corridas EXPLORATORY reales en raíces distintas. Desde Historial se cargó una corrida y luego se compararon ambas, sin seleccionar archivos manualmente. La importación del paquete re-auditó primarias (`PASS`, `recomputed=true`), mostró variante, 3000 RPM, clasificación, periodicidad `NOT_EVALUATED`, conservación reportada, provenance y motivo de métricas indefinidas. Potencia, torque y BMEP permanecieron vacíos. Se representaron presión y flujo de escape (kg/s), con ángulos comunes exactos y sin interpolación.

Las capturas son del HWND real de `Dino2T.exe`: proyecto/variante activa y carga/resultados a 1360×900; comparación a 1360×900 y 980×680; flujo de escape comparado a 980×680; métricas indefinidas, provenance y motivo a 1360×900. El detalle de la comparación geométrica se verificó en los `configuration.json` inmutables: sección de cámara 180→200 mm y discretización de escape EXHAUST_MESH_V1→V2.

El ZIP tiene 299 entradas y `ZipFile.testzip()` PASS. El ejecutable mantiene clasificación TRIAL porque el árbol de fuentes contenía cambios locales. Los detalles, hashes del paquete, binarios, artifacts y capturas están en `results/dino-desktop-ux-v2/packaged-acceptance-receipt.json`. No se inició solver ni campaña.
