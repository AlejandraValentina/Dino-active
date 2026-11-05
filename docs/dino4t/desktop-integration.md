# Integración Dino 4T en Desktop

Estado: integración de aplicación en prueba interna. La rama de integración conserva la historia original de `dino4t/foundation-v1`; la rama fuente y su worktree no se modifican.

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
- La API 4T ofrece estado de continuación opaco dentro del proceso, pero no un checkpoint serializable ni una operación de cancelación. Desktop limita la duración de pared configurable y conserva los resultados parciales; no ofrece reanudación ni promete detener inmediatamente el cálculo.
- El estado periódico es una propiedad numérica del modelo, no evidencia experimental. Calibración y validación experimental siguen `NOT_PERFORMED`; predictividad sigue `NOT_CLAIMED`.
- No se integra exploración paramétrica 4T ni las páginas de diagnóstico 2T con semánticas distintas. El proyecto 2T y su historial siguen usando los lectores y contratos actuales.

## Empaquetado

El spec de Windows incluye explícitamente los módulos cargados de forma diferida por la API 4T y el JSON de ejemplo que consume su validador. El manifiesto de build declara los esquemas de proyecto y APIs nativas por familia. La aceptación final de la integración requiere ejecutar y probar ese binario empaquetado; las pruebas Python por sí solas no constituyen aceptación Desktop.
