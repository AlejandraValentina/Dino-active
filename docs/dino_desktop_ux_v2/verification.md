# Verificación visual y funcional

Se preservaron íntegros el informe Opus y las 17 capturas previas en `reference/`. Las capturas posteriores están en `captures/after/` y sus hashes, dimensiones y condiciones constan en `results/dino-desktop-ux-v2/visual-check-receipt.json`.

La ventana Dino 2T se abrió en Windows y se capturó por su área de ventana. Además, el smoke funcional ejecutó en memoria el flujo de crear, editar, renombrar y duplicar variantes; editar el escape sin solver; guardar y volver a abrir un proyecto temporal; preparar preflight sin iniciar una simulación; y comparar dos corridas EXPLORATORY preexistentes referenciadas desde dos artifact roots. El importador normal reaudita ambas. No se inició ningún solver.

Se renderizaron los layouts 1360×900 y 980×680 usando QPA offscreen y factores Qt 100 %, 125 % y 150 %. El cambio global de escala de Windows no se alteró; las escalas 125 % y 150 % son simulación de Qt, no una comprobación del ajuste de pantalla del sistema.

Los resultados abiertos son exploratorios y no identificaron periodicidad. Los diagnósticos de escape continúan sin demostrar independencia espacial. La verificación no promueve esas conclusiones ni cambia evidencia científica.
