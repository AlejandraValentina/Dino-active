# Tareas — P9 v1.0

- [x] Leer y reconstruir el contrato P9 v1.0 proporcionado por la usuaria.
- [x] Inventariar OpenSpec, roadmap, preregistraciones, evidencia histórica y
      candidatos de datos antes de inspeccionar resultados experimentales.
- [x] Confirmar que P8 solo aporta evidencia sintética
      `BOUNDED_TRANSIENT_INDICATED` y que no hay dataset experimental autorizado
      identificado en `E:\dino`.
- [x] Transcribir los 32 apartados normativos a OpenSpec y pasar validación
      estricta antes de congelar el contrato; `openspec validate
      p9-experimental-validation --strict --no-interactive` aprobado.
- [x] Registrar preregistro P9 v1.0, 2026-10-01, en contrato congelado
      `ba1dff027d66982aba0aeb7ae6f315fa92346a2c`; sus hashes están en
      `results/p9-readiness-20261001/preregistration.json`. Ocurrió antes de
      recibir o inspeccionar el dataset confirmatorio.
- [ ] Obtener dataset experimental autorizado y completo; conservar originales
      y congelar manifest, hashes y metadata antes de comparar.
- [x] Buscar y calificar fuentes públicas para dataset experimental P9 y ampliar
      la matriz de diez a 26 candidatos; la
      búsqueda concluye `DATA_REQUEST_REQUIRED` para el candidato preferido
      Honda RS125/SAE 2004-01-3561. No se halló un archivo numérico descargable
      que permita autorizar dataset P9. Ver informe anterior y expansión en
      `docs/gasdynamic/p9_experimental_dataset_search_20261001.md`,
      `results/p9-dataset-search-20261001/search.json` y
      `results/p9-dataset-search-20261001/search-expansion.json`.
- [x] Normalizar las 27 filas en una única matriz con todas las columnas P9 y
      `null` explícito para datos públicos desconocidos:
      `results/p9-dataset-search-20261001/matrix.json`.
- [ ] Enviar manualmente la solicitud de datos a través del contacto institucional
      verificado de Queen's University Belfast; no se envió ningún mensaje.
- [ ] Calificar la configuración fija y todos los puntos con P9-A (E13,
      máximo 400 ciclos y todos los gates requeridos).
- [x] Implementar el esquema offline preliminar, recálculo de geometría,
      `∮p dV`, potencia 2T, matching RPM, gates de métricas, guardia
      anti-sintético y pruebas negativas. Calificación sintética únicamente;
      no hay adaptador específico para un dataset real.
- [x] Generar y auditar fixtures sintéticos PASS/FAIL/INCONCLUSIVE en
      `tests/fixtures/p9_synthetic/` y conservar los recibos en
      `results/p9-pipeline-qualification-20261001/`.
- [x] Verificar period-1 y ramas period-2 A/B, incluida la media de trabajo
      requerida para la comparación escalar; conservar ambas ramas.
- [x] Ejecutar 27 pruebas P9 sintéticas/negativas y 23 pruebas P8 focales;
      una prueba de campaña P8 se excluyó del smoke porque P9 está aislado y no
      modifica el solver. OpenSpec estricto, `git diff --check` y Git LFS fsck
      aprobados; SHA-256 del contrato coincide con el preregistro.
- [ ] Solicitar y recibir un dataset experimental autorizado, y solo entonces
      adaptar/ejecutar la ingestión real conforme al manifest congelado.
- [ ] Congelar simulación y ejecutar comparación sin calibración ni tuning.
- [ ] Auditar evidencia primaria, ejecutar regresiones afectadas y revisión
      independiente; cerrar solo con clasificación sustentada.

Estado: `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA` (`DATA_REQUEST_REQUIRED`).
OpenSpec estricto aprobado. El pipeline quedó calificado solo con fixtures
sintéticos; esto no es implementación ni validación P9 experimental. La
búsqueda pública ampliada a 26 candidatos no localizó un archivo numérico
completo y autorizado. No se comparó ni calibró MotorSim y no se ejecutó
campaña P9. El contrato y preregistro permanecen intactos.
