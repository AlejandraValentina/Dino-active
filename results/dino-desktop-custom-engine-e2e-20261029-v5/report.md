# Desktop custom-engine A/B end-to-end proof

Configuración enteramente sintética; no es validación experimental ni predicción respaldada.

- Alta desde el diálogo Crear motor; cambios en cilindro, cárter, lumbreras, admisión, transferencia y láminas aplicados y resueltos por el solver.
- Proyecto guardado, ventana cerrada y proyecto reabierto; identidad de motor preservada.
- Variante duplicada desde Proyecto; geometría de escape editada, guardada y reabierta.
- Curva A/B paralela desde Desktop en 4500 y 5000 rpm, un ciclo por punto; artifacts ligados por hash al proyecto.
- Los cuatro puntos se muestran como MAX_CYCLES_NONCONVERGED; la comparación advierte TRANSITORIOS y no declara una mejora definitiva.
- Compatibilidad Windows verificada leyendo el spec de PyInstaller: el bundle Dino incluye fuentes `motorsim`; no se hizo build.
- La corrida de éxito no inyectó cancelación. Cancelación, fallos y recuperación individual conservan las rutas ya existentes y quedan listados en el recibo.

Ver métricas, hashes y referencias en `receipt.json`.
