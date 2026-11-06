## Context
Dino2T (`motorsim/desktop/app.py`, `DinoDesktopWindow`) es hoy un producto 2T:
sus proyectos son `MOTORSIM_ENGINE_PROJECT_V3` y su motor base se valida con
`engine_configuration.validate` (2T integrado). El 4T 0D
(`three-cv-0d-prescribed-heat-720-v1`) está cerrado técnicamente en el MotorSim
legacy: `Project` JSON v6, `four_stroke.py`, `reference_run.py` y
`reference_results.py` con manifiesto v4. El worker ya admite 4T:
`runtime.worker_command()` lanza `MotorSimWorker.exe` o
`python -m motorsim.reference_run`, y `reference_run.main` acepta `--cycle 4T`.

La usuaria decidió que el simulador sirva para 2T y 4T, pero que **no** se
comparen entre sí: son motores distintos. Por eso este change agrega un modo 4T
separado y no unifica los proyectos.

## Decisions
### 1. Documento 4T propio, sin campos 2T
Se crea `MOTORSIM_4T_REFERENCE_PROJECT_V1` en
`motorsim/four_stroke_project.py`:

- `schema`, `version`, `name`, `cycle: "4T"`, `created_with`;
- `geometry`: `cylinder_count` (solo 1), `bore_mm`, `stroke_mm`,
  `rod_length_mm`, `compression_ratio`, `notes`;
- `valves`: `intake` y `exhaust` con los seis campos de `Valve`;
- `ducts`: `reference=FOUR_DUCT_REFERENCE`, rutas `intake`/`exhaust` de
  `DuctSegment`;
- `operating_point`: `rpm` entero opcional (2500–3500 para ejecutar);
- `classification: "SYNTHETIC_REFERENCE_0D"`;
- `scientific_status: "NOT_VALIDATED"`;
- `provenance`: origen, fecha, versión de modelo y nota de referencia.

El archivo no escribe `ports`, `intake` 2T, `ducts` 2T,
`crankcase_volume_bdc_cm3` ni `two_stroke_reference`. Así evita la redundancia
R-03 (`project.py:302-305`) y no depende del editor legacy donde vive R-02.

### 2. Adaptador en memoria hacia `Project`
Para ejecutar se construye un `Project(cycle='4T', ...)` con `FourStroke` y los
defaults 2T válidos, y se usa `reference_results.project_inputs(project, origin,
rpm=...)`. El `project_snapshot` que recibe el worker es el contrato interno
existente; el archivo del usuario sigue siendo 4T-only. No se modifica
`Project.to_dict()` ni el formato v6.

### 3. Validación de guardado separada de la ejecución
- Guardar/abrir valida schema, versión, nombre, ciclo 4T, geometría numérica,
  válvulas informadas y conductos 4T. Las válvulas incompletas se conservan
  para corregirlas, igual que en el editor legacy.
- Ejecutar exige `four_stroke.execution_errors(project)` vacío y un RPM válido.
  Un proyecto incompleto se guarda, pero no se presenta como calculable.
- Texto numérico inválido no se convierte en `null` silenciosamente.

### 4. Modo 4T en Dino con workspace separado
`DinoDesktopWindow` conserva el workspace 2T y agrega:
- acciones “Nuevo motor 4T (0D referencia)…”, “Abrir 4T…”, “Guardar 4T…”;
- un `FourStrokeContext` propio (proyecto, dirty, validación, señales);
- un `FourStrokeWorkspace` con Geometría, Válvulas, Conductos, Simulación y
  Resultados;
- título/indicador “Dino · 4T 0D referencia” cuando el proyecto activo es 4T;
- filtros y settings separados para archivos 4T.

No se toca `DesktopContext` para 2T. No hay variantes, estudios de diseño ni
comparación con 2T en B1.1.

### 5. Ejecución con el worker existente
El adaptador 4T:
1. construye `project_inputs` con `origin` y `rpm`;
2. escribe una copia temporal acotada de la solicitud;
3. lanza `worker_command()` con `--cycle 4T --project-input ... --control-stdin`;
4. consume eventos `progress`/`finished`, permite cancelar y no bloquea la UI;
5. lee el `manifest.json` v4 con `reference_results.load_result`.

No se crea solver, worker ni ejecutable nuevo. El `MotorSimWorker.exe` ya
importa `reference_run.main` (`packaging/worker_entry.py`).

### 6. Resultados y procedencia
La vista 4T muestra estado, convergencia, `W_C_J`, `p_max_Pa`, tiempos, pico de
memoria, curvas P-V y p-V de las muestras, y la etiqueta
`SYNTHETIC_REFERENCE_0D · NOT_VALIDATED`. No muestra `W_K` (no aplica a 4T), no
compara con 2T y no atribuye validación experimental.

## Alternatives considered
- **V4 unificado con `cycle`:** un solo proyecto y comparación cross-cycle.
  Se descarta porque la usuaria no quiere comparar 2T con 4T, porque obliga a
  migrar el contrato V3 aceptado y porque el 4T no tiene variantes ni estudios
  de diseño. Alto riesgo para B1.
- **Anexo 4T dentro de V3:** agrega `four_stroke_reference` a un proyecto 2T.
  Se descarta por semántica incorrecta: un motor 4T no es una variante de un
  motor 2T integrado y la procedencia se vuelve ambigua.

## Risks / Trade-offs
- **Dos familias de proyecto:** más superficie de UI y de settings. Mitigación:
  contextos y archivos separados, sin tocar el flujo 2T.
- **Paridad limitada:** B1.1 no incluye variantes, estudios de diseño ni curva
  RPM. Se puede agregar B1.2 sin cambiar el schema.
- **Resultados 4T:** el manifiesto v4 es estricto; si el worker no está
  empaquetado, la ejecución falla con un error claro, no con un resultado falso.
- **R-02/R-03 legacy:** siguen en `MotorSim.exe`; este change no los usa. Si se
  quiere conservar el editor legacy 4T, se corrige en un change aparte.
- **Etiqueta científica:** el 4T 0D es referencia; no se convierte en claim
  predictivo ni en validación experimental.

## Compatibility and verification
- 2T: V3, `engine_configuration`, `DesktopContext`, solver y tests intactos.
- 4T: reutiliza `Project`/`FourStroke`/`reference_run`/`reference_results` sin
  cambiar física, tolerancias ni hashes históricos.
- Tests nuevos: round-trip 4T, rechazo de schema/versión, ausencia de campos 2T,
  ejecución incompleta, adaptador de solicitud, UI 4T y regresión 2T.
- Evidencia de cierre: suite completa, prueba de guardar/abrir, corrida 4T
  acotada y lectura estricta del manifiesto.
