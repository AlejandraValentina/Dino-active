# Auditoría inicial: roadmap hacia simulador profesional Dino 2T

Fecha de corte: 2026-10-16. Alcance: inspección documental y de código existente para preparar un plan incremental. No se modificó código de producto y no se ejecutaron simulaciones ni campañas.

## Resumen

El repositorio ya tiene un solver integrado 2T, modelos versionados, flujo EXPLORATORY, evidencia auditable, runner multiproceso IMPL2 en readiness para decisión, editores de diseño, importación de mediciones y una aplicación Windows V3 funcional. Esto no equivale a un simulador profesional validado: los resultados históricos centrales son sintéticos, R2 es un gate offline de semántica de outputs, la campaña V1 tiene estado PARTIAL, la campaña IMPL2 no estaba autorizada/iniciada según su receipt de readiness, y la evidencia de escape no establece independencia espacial ni periodicidad.

La brecha científica dominante para una curva de rendimiento defendible es la resolución/convergencia del modelo de escape y la periodicidad a cada RPM. Para validación experimental se necesita además un dataset trazable independiente. Las bases de UI y workflow pueden reutilizarse; no requieren reconstrucción.

## Inventario de capacidades existentes

| Capacidad | Estado | Evidencia y límite |
|---|---|---|
| Integración 2T de cilindro, cárter, puertos, especies, transferencia térmica y combustión | IMPLEMENTADA; parcialmente verificada | `motorsim/integrated_2t.py`, módulos P6/P7 y tests P1–P8. La presencia del modelo y tests no valida por sí sola fidelidad física. Fuel y varios submodelos son sintéticos/modelados. |
| Conservación y auditoría de primarias | VALIDADA en scopes declarados | R2 offline verifica semántica, conservación y detección de mutaciones en primarias fijas; workflow y receipts de campañas ejecutan auditoría convencional. R2 no es validación experimental ni gate de desempeño general. |
| Periodicidad y clasificación por punto | IMPLEMENTADA | `motorsim/periodicity.py`, runner y contrato de sweep separan periodicidad, no convergencia, invalidación y outputs. Evidencia no garantiza periodicidad: design/exhaust diagnostics fueron transitorios o no evaluados. |
| IMEP/BMEP, potencia, torque, pérdidas y consumo | IMPLEMENTADA con condiciones | `motorsim/p8_performance.py` y adapters de resultados usan magnitudes integradas y pérdidas explícitas. Outputs dependen de modelo mecánico, periodicidad y signo/definición física; resultados de 4000 RPM del piloto incluyen potencia de freno negativa, BSFC indefinido y TE/CE/SE indefinidos. |
| Sweep RPM V1 y evidencia/reportes | IMPLEMENTADA; PARTIAL | Contrato, runner, integridad y reportes existentes. `campaign-receipt-v2.json`/`pilot-analysis-v2.json` registran `PARTIAL_RESOURCE_BUDGET`; program-status mantiene gate `REVIEW`, resumen 27 PERIOD_1 / 3 NUMERICAL_INVALID. El piloto detallado de 4000 RPM no sustenta curvas completas. |
| Ejecutor IMPL2, preflight e identidad aislada | IMPLEMENTADA y aceptada administrativamente en alcance diagnóstico | `implementation-v2-campaign-readiness-receipt.json`: preflight de 30 puntos PASS, 0 solver steps, campaña no autorizada/no iniciada, artefactos v1 incompatibles rechazados, FAST desactivado. Readiness para decisión no equivale a evidencia de campaña ni a aceptación científica de una curva. |
| Checkpoint/restart concurrente | VALIDADA en el scope de integración comunicado | Tests y receipt IMPL2 registran `_run_point` real, spawn, interrupción y resume con hashes/continuidad. Reutilizable por una campaña bajo la identidad/autorización correcta. |
| Refinamiento axial del escape 1/2/4 y 1/2/4/8 | IMPLEMENTADA; conclusión científica PARTIAL | `motorsim/exhaust_mesh_v1.py`, `exhaust_mesh_v2.py`. Recibos: geometría/conservación y tests estructurales PASS; diferencias 1→2→4 no decrecen de modo que aísle respuesta A/B, y 1/2/4/8 no demostró convergencia. No afirmar independencia espacial. |
| Sensibilidad de diseño y visualización de resultados | IMPLEMENTADA; evidencia PARTIAL | `DINO_DESIGN_VALIDATION_V1_PARTIAL`: cinco puntos transitorios y repetición exacta, auditados; periodicidad NOT_EVALUATED/NOT_IDENTIFIED, malla de una celda por sección en la evidencia anterior, sin conclusión de desempeño. El editor y el flujo propagan controles soportados al solver. |
| Workflow local, proyectos, variantes, artefactos, comparación | VALIDADA funcionalmente para EXPLORATORY | `DINO_SIMULATION_WORKFLOW_V1_READY`; preflight, auditoría, conservación, cancelación/restart y comparaciones. VERIFIED requiere contrato/preregistro/autorización; RSS es control cooperativo, no hard cap de sistema operativo. |
| Importación de mediciones | IMPLEMENTADA como contrato/herramienta | `motorsim/measurement_data.py`, `external_data.py`: unidades, RPM, torque/potencia, incertidumbre/provenance y métricas de residuo. No prueba que exista un dataset adecuado ni valida el solver. |
| Optimización/calibración integrada | AUSENTE como capability de producto | No se encontró `motorsim/optimization.py` ni gate de optimización reproducible. Hay sensibilidad y contratos de importación, que no equivalen a optimizador ni a calibración con holdout. |
| Desktop comercial | VALIDADA funcionalmente en V3; V3.1 aún REVIEW | Program-status conserva V3 PASS. V3.1 tiene seis de siete gates y falta recaptura del build exacto en EXE por sesión Windows bloqueada. No afecta evidencia física. |

## Brechas por etapa

### Etapa 1 — Motor físico confiable

**Ya existe:** motor integrado, cinemática/puertos, flujo de masa/especies/energía, combustión y térmica versionadas, pérdidas mecánicas explícitas, conservación, replay, auditorías, detector de periodicidad y refinamiento de escape.

**Falta para cerrar el objetivo:** verificación contra referencias analíticas/independientes que cubran subsistemas relevantes; separar error espacial del temporal; resolver o acotar convergencia del escape; demostrar periodicidad para estados donde se calculen métricas de ciclo; revisar plausibilidad de signos/magnitudes en puntos de operación; declarar incertidumbre/sensibilidad de modelos sintéticos; dataset experimental separado si se pretende validación experimental.

**Límite actual:** R2 PASS es semántico/offline y preserva resultados definidos correctamente; no promueve `ENGINE_PHYSICS_V1` histórico ni demuestra precisión global. Exhaust mesh/convergence y design validation cierran PARTIAL/FAIL_TERMINAL con periodicidad no evaluada y convergencia espacial no demostrada.

### Etapa 2 — Curvas RPM y análisis

**Ya existe:** contrato de sweep de 30 puntos/2 variantes para identidades previas, preflight IMPL2 de 30 configuraciones, selección explícita de implementación, recursos, paralelismo, checkpoint/restart, adapter de outputs, auditoría y formato de reportes.

**Falta:** una autorización de campaña IMPL2 y presupuesto global explícitos; resolver blockers científicos de Etapa 1 para el alcance de claim pretendido; ejecutar puntos autorizados con estado real, verificar cada métrica y reportar huecos. Program-status V1 está PARTIAL; el readiness receipt de IMPL2 dice campaña no autorizada/iniciada. Las curvas y máximos no se pueden inferir de los dos puntos detallados del piloto.

**Visualizaciones:** el workflow/desktop ya ofrece traces, historial y comparación; completar la curva requiere conectar reportes RPM clasificados sin interpolar puntos inválidos. La curva calculada de ingeniería y una curva validada experimentalmente son gates distintos.

### Etapa 3 — Diseño integrado y diagnóstico físico

**Ya existe:** edición de escape, cilindro/distribución y variantes; configuración nativa; sensibilidad de escape; presión/flujo; comparación y provenance; importación experimental contractual.

**Falta:** relacionar cambios con observables aceptados y repetibles después de resolver incertidumbre numérica; cobertura de admisión/transferencia y restricciones; análisis de ondas interpretables; separar diagnóstico causal de hipótesis. La evidencia A/B actual demuestra cambios de respuesta calculada pero no una respuesta independiente de malla ni mejora de desempeño.

### Etapa 4 — Optimización y preparación comercial

**Ya existe:** base de UI Windows, workflow de proyectos/corridas, sensibilidad acotada, comparación, datos de medición con unidades/incertidumbre y exportación/artefactos.

**Falta:** optimizador de parámetros versionado, definición de objetivos y constraints, manejo de identificabilidad, gestión de lotes paramétricos, partición ajuste/holdout, incertidumbre de predicción, informes técnicos reproducibles e integración comercial aceptada. La distribución V3 es funcional; V3.1 tiene pendiente visual de build final. No declarar precisión comercial sin evaluación experimental independiente.

## Camino mínimo a una curva HP/torque real

1. Cerrar las brechas numéricas que afectan al motor/configuración elegidos, sobre todo la resolución del escape y periodicidad en el dominio de RPM objetivo.
2. Congelar una configuración y una identidad IMPL2, con combustible, AFR, WOT y modelo mecánico explícitos; verificar preflight y registrar preregistro, límites y presupuesto global.
3. Obtener autorización explícita para el rango y el cómputo; ejecutar cada punto con la ruta convencional de primarias y auditoría independiente.
4. Incluir en HP/torque sólo puntos cuya clasificación y condiciones contractuales definan esas métricas. Mantener huecos, fallos y métricas indefinidas visibles; no interpolar.
5. Etiquetar el resultado como predicción de ingeniería bajo sus supuestos. Para llamarlo experimentalmente validado, adquirir mediciones trazables de dinamómetro y evaluar contra datos no usados para calibrar.

El estado actual no satisface los pasos de campaña: IMPL2 está en `READY_FOR_CAMPAIGN_DECISION`, pero el receipt consultado dice `campaign_authorized=false` y `campaign_started=false`; además, la evidencia de escape no demuestra independencia de malla. No se ejecutó nada en esta auditoría.

## Orden propuesto, dependencias y esfuerzo relativo

| Orden | Etapa | Dependencia de entrada | Esfuerzo relativo |
|---:|---|---|---|
| 1 | Confianza física y numérica | Mantener las identidades y evidencia existentes; abordar los blockers de escape/periodicidad con cambios versionados | Muy alto |
| 2 | Curvas RPM | Gate numérico suficiente para el claim, preregistro, autorización y presupuesto | Medio-alto; gran parte de la infraestructura ya existe, costo de campaña aún no validado en 30 puntos IMPL2 |
| 3 | Diseño y diagnóstico | Outputs de etapa 1/2 confiables en dominios definidos | Medio |
| 4 | Optimización y comercialización | Curvas y diagnósticos aceptados; dataset experimental independiente | Alto |

Etapa 3 puede avanzar en preparación de interfaz/contratos en paralelo cuando no cambie solver ni suponga causas científicas; su cierre depende de evidencia física interpretable. La calibración/optimización de Etapa 4 depende de mediciones y criterios decididos; no debe anteceder a la identificabilidad.

## Criterios de cierre verificables

- **Etapa 1:** suite versionada de casos analíticos/referencia; balances y replay PASS dentro de tolerancias justificadas; sensibilidad espacial y temporal separada; periodicidad clasificada; plausibility gates conservados; claims y límites declarados; evidencia independiente cuando el contrato la requiera. Experimental validation se cierra aparte.
- **Etapa 2:** preregistro/hash válido; preflight de todos los puntos; ejecución autorizada y recuperable; auditoría/conservación PASS por punto; clasificación y métricas con unidades/provenance; ningún punto omitido o interpolado presentado como calculado; reporte completo con recursos y fallos.
- **Etapa 3:** trazabilidad de parámetros editables hasta el solver; comparación controlada y repetible; diagnóstico referenciado a señales medidas y con error numérico acotado; hipótesis separadas de hallazgos.
- **Etapa 4:** objetivos y constraints reproducibles; trazabilidad de candidatos a corridas; identifiabilidad/uncertidumbre declaradas; holdout experimental separado; informe reproducible; cualquier claim comercial respaldado por validación externa pertinente.

## Riesgos principales

1. **Conservación confundida con exactitud:** conservación es necesaria, no suficiente; incluir referencias y convergencia.
2. **Período confundido con validación:** periodicidad sólo demuestra repetición de estado bajo el modelo; no fidelidad física.
3. **Combustible y pérdidas sintéticos:** provenance/modelo explícito limita extrapolación; no ajustar silenciosamente constantes.
4. **Curvas incompletas maquilladas:** puntos inválidos/ausentes deben ser gaps y no entrar en máximos.
5. **A/B menor que error de malla:** el receipt EXHAUST_MESH_V1 indica que la respuesta de diseño es menor que sensibilidad observada a refinamiento.
6. **Runtime sobreinferido:** 3.738× fue benchmark multiproceso diagnóstico, no campaña completa; proyección serial previa 12.5 h no es medida de campaña paralela. IMPL2 readiness exige presupuesto global antes de ejecución.
7. **Calibración sobreajustada:** ajuste y evaluación experimental deben estar separados.

## Fuentes inspeccionadas

- `results/2t-commercial-core-20261002/program-status.json` (objetivo, cola, gates y clasificaciones).
- `results/full-rpm-sweep-v1/campaign-receipt-v2.json`, `pilot-analysis-v2.json`, `implementation-v2-campaign-readiness-receipt.json`.
- `results/dino-design-validation-v1/final-receipt.json`.
- `results/exhaust-mesh-v1/final-receipt.json`.
- `results/exhaust-numerical-convergence-v2/final-receipt.json`.
- `results/dino-simulation-workflow-v1/implementation-receipt.json`.
- OpenSpec de workflow, design validation y exhaust numerical convergence.
- Código: `motorsim/integrated_2t.py`, `p8_performance.py`, `periodicity.py`, `full_rpm_sweep_v1.py`, `full_rpm_sweep_v1_impl2.py`, `exhaust_mesh_v1.py`, `exhaust_mesh_v2.py`, `measurement_data.py`, `external_data.py`; suites focales de motor, performance, evidencia, sweep, checkpoints, malla y desktop.

## Transición operativa

Auditoría registrada como propuesta futura `DINO_2T_PROFESSIONAL_ROADMAP`, `owner_approved=false`. `CURRENT_OBJECTIVE` y gate no cambian: `DINO_DESKTOP_V3_1_VISUAL_PARITY` continúa ACTIVE/REVIEW, pendiente `V31-PACKAGED-ACCEPTANCE`. Ninguna etapa fue activada; no se ejecutaron pruebas ni simulaciones como parte de esta auditoría.
