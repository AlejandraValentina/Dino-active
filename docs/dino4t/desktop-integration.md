# Integración Dino 4T en Desktop

Estado: integración funcional verificada en un candidato Windows para pruebas internas. La rama de integración conserva la historia original de `dino4t/foundation-v1`; la rama fuente y su worktree no se modifican.

## Frontera de arquitectura

- `DINO4T_API_V1` es la única dependencia de Desktop para validar, ejecutar, interpretar errores y comprobar resúmenes 4T. Desktop no importa el runner o el solver 4T para despachar una corrida.
- `DINO_DESKTOP_ENGINE_PROJECT_4T_V1` persiste configuración nativa 4T, variantes y referencias de corrida. `MOTORSIM_ENGINE_PROJECT_V1..V3` permanece sin cambios y sigue siendo el formato de los proyectos 2T existentes.
- `motorsim.engine_platform` identifica familias e invoca la API 4T. La experiencia 2T mantiene su workflow y sus contratos de corridas actuales; ninguna estructura 2T se impone sobre los resultados 4T.
- El espacio de trabajo 4T usa el mismo ejecutable Desktop, gestión de archivos, contexto de variantes, `CurvePlot`, exportación de informes técnicos y raíz de artefactos. Su editor muestra los campos conocidos del esquema 4T, incluidos los grupos de procedencia, y rechaza claves desconocidas.
- Las selecciones `zone_model`, `restriction_model` y `limiter` se escriben explícitamente en las nuevas configuraciones. Los modelos reportados por cada resultado se conservan como los declara la API.

## Persistencia y análisis

Una corrida Desktop conserva `summary.json`, `config_resolved.json`, `trace_last_cycle.csv` y `run.json`, con hashes, modelo, estado, procedencia, commit y estado dirty. La referencia se agrega al proyecto sin incrustar primarios. La importación de históricos requiere resumen, configuración resuelta y hash compatible; copia los archivos a la raíz de artefactos de Desktop y deja intacta la fuente original.

Las prestaciones solo se grafican para resultados periódicos. La comparación requiere RPM y selección de modelos coincidentes y dos resultados periódicos. Presiones y caudales trazados se etiquetan como ciclo final; si la corrida no es periódica, la vista se identifica como transitoria. Los informes conservan los estados de calibración, validación experimental y capacidad predictiva del resumen nativo.

## Límites explícitos

- El alcance del solver 4T continúa siendo monocilíndrico, encendido por chispa y atmosférico según `DINO4T_API_V1`; la GUI no sugiere multicilindro, turbo, knock, inyección ni datos de banco no presentes.
- La API 4T ofrece estado de continuación opaco dentro del proceso, pero no un checkpoint serializable. La evolución A/B agrega cancelación cooperativa en límites de ciclo completo y conserva el resumen/traza de ciclos completos; después de cerrar el proceso, continuar requiere iniciar otra corrida desde la configuración guardada.
- El estado periódico es una propiedad numérica del modelo, no evidencia experimental. Calibración y validación experimental siguen `NOT_PERFORMED`; predictividad sigue `NOT_CLAIMED`.
- No se integra exploración paramétrica 4T ni las páginas de diagnóstico 2T con semánticas distintas. El proyecto 2T y su historial siguen usando los lectores y contratos actuales.

## Empaquetado

El spec de Windows incluye explícitamente los módulos cargados de forma diferida por la API 4T y el JSON de ejemplo que consume su validador. El manifiesto de build declara los esquemas de proyecto y APIs nativas por familia. La aceptación final de la integración requiere ejecutar y probar ese binario empaquetado; las pruebas Python por sí solas no constituyen aceptación Desktop.

### Candidato integrado

- Candidato interno: `MotorSim-0.1.0-rc12-windows-x64-552c60ed`.
- Fuente exacta del paquete: commit `552c60ed9454a9d86ef05707c38d495d109247c3`, árbol limpio y manifiesto de 254 entradas.
- SHA-256 del ZIP: `752e8e8a14819fa42277fc0667f396a3f686e647e6cf70f6b531b8e6eac637d2`.
- SHA-256 de `Dino2T.exe`: `7ca0ca86c91152b5e0f1d1de1f2bc6f5d3973703cb03e46dcb3c2dc676c7f048`.
- Recibo y capturas: `results/dino4t-desktop-integration-v1/acceptance/windows/receipt.json`.
- La primera distribución reveló que PyInstaller omitía `unittest.mock` usado por la ruta de aceptación. Se conservó ese candidato y su diagnóstico en `verification/packaged-candidate-1-failure.json`; el segundo paquete añadió el import explícito y pasó el recorrido.
- La aceptación empaquetada abrió un proyecto 2T V2 histórico y verificó cuatro hashes de resultados. En el mismo proceso, abrió Desktop 4T, editó geometría y escape de una variante, guardó/reabrió el proyecto, importó el resultado periódico histórico, ejecutó un punto 4T de un ciclo, y exportó CSV e informe HTML.
- La corrida de un ciclo terminó como `NOT_CONVERGED`; la interfaz mostró `Transitorio` y `Presión transitoria · no periódica`. El histórico conservó `PERIODIC_CONVERGED`. Ni la periodicidad ni la corrida sintética se presentan como validación experimental.
- Suite ampliada final: 66 PASS, 1 SKIP (`tests/test_dino_desktop.py` omite la prueba IMPL2 si el artefacto externo no está configurado). Dos verificaciones focalizadas adicionales pasaron para crear 4T desde el selector de Desktop y rechazar la comparación entre el punto periódico histórico y el transitorio real de un ciclo. Las 115 fallas preexistentes de la suite general conservan su baseline en `results/dino4t-stage2-v1/audit/preexisting_failures_at_e95db4c.txt`; no se alteraron contratos científicos para modificarlas.

## Funcionalidad todavía limitada

- La UI impide calcular diferencias de prestaciones si una corrida no es periódica. Una prueba usa el punto histórico periódico y un punto real acotado de un ciclo para comprobar el rechazo. No hay dos configuraciones 4T distintas con resultados periódicos aceptados disponibles en los históricos para presentar una diferencia A/B de diseño con evidencia existente; no se fabricó una segunda curva.
- La API 4T no ofrece cancelación ni checkpoint serializable, por lo que Desktop no promete reanudación/cancelación de una corrida 4T.
- El paquete se acepta para pruebas internas solamente. No es una promoción de release ni validación científica.

## Evolución A/B 4T en curso

La rama `work/dino4t-ab-engineering-v1` desarrolla una comparación estricta de dos variantes. Los
resultados comparables deben estar terminados y periódicos bajo los criterios guardados, tener RPM,
contexto operativo, numerics, modelos, commit limpio y fuentes termodinámicas coincidentes. La ficha
registra cambios de diseño, métricas A/B, diferencias absoluta/relativa, configuraciones resueltas,
procedencia y hashes; CSV conserva floats de ida y JSON/HTML transportan el registro completo. Si
las entradas no cumplen el contrato, la UI no calcula ni exporta deltas.

La cancelación se observa al terminar un ciclo completo de 720°, una vez evaluada periodicidad.
Conserva los ciclos completos como `incomplete` y no afirma periodicidad. No se implementa checkpoint
serializable: el estado de continuación V1 no incluye historial del monitor ni un formato durable con
compatibilidad de versiones. Esta limitación queda explícita; una reanudación exacta no se ofrece.
