# MotorSim — P9 v1.0

## Experimental Performance Validation of a Fixed 2T Configuration

Estado del contrato:

`PROPOSED_FOR_PREREGISTRATION`

Este contrato debe quedar versionado y congelado antes de incorporar o inspeccionar los resultados del dataset experimental utilizado para tomar la decisión P9.

---

# 1. OBJETIVO

P9 evalúa si MotorSim reproduce con precisión previamente definida el rendimiento indicado medido experimentalmente de una configuración física fija de motor 2 tiempos.

P9 NO pretende validar universalmente MotorSim.

Un PASS de P9 únicamente autoriza afirmar que:

> MotorSim reprodujo dentro de los criterios preregistrados el comportamiento experimental observado para la configuración y dominio de operación evaluados.

No autoriza afirmar que:

- MotorSim está validado para cualquier motor 2T;
- MotorSim predice correctamente geometrías no evaluadas;
- el modelo está validado fuera del rango ensayado;
- existe validación predictiva universal.

---

# 2. MAGNITUD PRIMARIA DE VALIDACIÓN

La magnitud primaria será:

`indicated work per cycle`

y su magnitud equivalente:

`indicated power`

calculadas a partir del diagrama experimental presión-volumen.

Preferentemente el dataset debe contener:

`cylinder pressure vs crank angle`

junto con la geometría necesaria para calcular volumen instantáneo.

El trabajo indicado experimental se calculará mediante:

`W_i = ∮ p dV`

La potencia indicada se obtendrá mediante la relación correspondiente al motor 2T y al régimen medido.

MotorSim deberá calcular la misma magnitud bajo la misma definición.

---

# 3. POTENCIA DE BANCO / BRAKE POWER

La potencia o torque medidos al eje NO podrán compararse directamente contra potencia indicada de MotorSim.

Para utilizar brake power sería necesario que MotorSim disponga de un modelo independiente y previamente congelado de:

- fricción;
- pumping/mechanical losses;
- pérdidas en transmisión/acoplamiento cuando corresponda.

Si dicho modelo no existe antes de observar el dataset:

`brake power`

podrá registrarse como información experimental secundaria, pero NO será utilizada para el gate principal P9.

No se introducirá un factor de eficiencia mecánica post-hoc para conseguir concordancia.

---

# 4. CONFIGURACIÓN DEL MOTOR

P9 utilizará UNA configuración física fija.

La evidencia experimental debe identificar como mínimo, cuando corresponda:

- bore;
- stroke;
- connecting rod;
- displacement;
- compression ratio;
- port timing;
- port geometry;
- exhaust geometry;
- intake geometry;
- crankcase geometry;
- ignition timing;
- fuel;
- mixture / AFR o configuración equivalente;
- throttle/load condition;
- exhaust configuration.

La configuración simulada y la experimental deben corresponder al mismo hardware relevante.

Una discrepancia material conocida en configuración invalida ese operating point.

---

# 5. CONDICIONES EXPERIMENTALES

Registrar para cada ensayo, cuando estén disponibles:

- RPM;
- ambient pressure;
- ambient temperature;
- intake temperature;
- exhaust conditions relevantes;
- fuel specification;
- mixture / AFR;
- ignition timing;
- throttle position;
- load;
- coolant/head/engine temperature si corresponde.

No inventar valores ausentes.

Campos relevantes desconocidos deberán constar como:

`UNKNOWN`

y ser evaluados respecto de su impacto antes de aceptar el punto.

---

# 6. OPERATING POINTS

El dataset principal debe contener como mínimo:

`5 operating points`

de RPM.

Deben cubrir una fracción significativa del rango operativo medido e incluir, cuando los datos lo permitan:

- régimen bajo;
- bajo-medio;
- medio;
- alto-medio;
- alto.

No seleccionar puntos después de conocer dónde MotorSim concuerda mejor.

Todos los operating points válidos disponibles dentro del dominio preregistrado deben incluirse.

---

# 7. MATCH DE RPM

Una observación experimental y una simulación podrán considerarse el mismo operating point cuando:

`|RPM_sim - RPM_exp| / RPM_exp <= 1%`

Si MotorSim puede ejecutarse exactamente a la RPM experimental, deberá usarse esa RPM en lugar de interpolar.

No desplazar RPM para mejorar el match.

---

# 8. P9-A — QUALIFICATION OF PREDICTIVE STATE

Antes de comparar una predicción contra datos experimentales, el punto debe superar P9-A.

La simulación deberá alcanzar el régimen periódico definido por el contrato de convergencia MotorSim vigente.

Se reutilizará, siempre que siga siendo aplicable, la semántica E13 ya validada.

Se aceptan:

- período 1;
- período 2.

Límite:

`max_cycles = 400`

No aumentar este límite después de observar un punto que no converge.

---

# 9. PERÍODO 2

Si un operating point converge a período 2:

se conservarán explícitamente ambas ramas.

No se declarará artificialmente período 1.

Para una magnitud experimental que represente promedio multicíclo, el valor escalar de trabajo/potencia podrá calcularse como promedio de las dos ramas:

`mean(branch_A, branch_B)`

pero deberán persistirse también los resultados individuales A y B.

Si el dataset experimental permite resolución ciclo a ciclo, deberá preservarse la comparación correspondiente.

---

# 10. P9-A GATES

Cada operating point debe cumplir:

- periodic-state qualification PASS;
- finite state PASS;
- geometry PASS;
- admissibility PASS;
- species PASS;
- CFL PASS;
- conservation mass PASS;
- conservation energy PASS;
- conservation species PASS;
- P7 combustion event non-vacuous PASS;
- P7 source admissibility PASS;
- restart PASS;
- deterministic replay PASS.

Si cualquiera falla:

el operating point no puede utilizarse para afirmar validación experimental.

---

# 11. DATOS EXPERIMENTALES PRIMARIOS

Preferencia de evidencia, en orden:

1. raw cylinder-pressure/crank-angle data;
2. processed cylinder-pressure trace con proceso documentado;
3. experimentally calculated indicated work/IMEP con metodología y provenance suficientes.

Los datos originales nunca deberán sobrescribirse.

Toda transformación debe generar un artefacto derivado separado.

---

# 12. CICLOS EXPERIMENTALES

Cuando existan datos ciclo a ciclo:

usar al menos:

`50 consecutive fired cycles`

por operating point, salvo limitación documentada del dataset.

Registrar:

- media;
- desviación estándar;
- número de ciclos;
- ciclos descartados;
- criterio de descarte.

No seleccionar manualmente ciclos que mejor coincidan con MotorSim.

---

# 13. TDC Y ALINEACIÓN ANGULAR

El cero angular experimental deberá provenir de:

- encoder;
- procedimiento experimental documentado;
- o corrección previamente determinada independientemente del resultado de MotorSim.

No se permitirá optimizar un phase shift para minimizar el error simulación-experimento.

Cualquier corrección TDC debe aplicarse antes de observar el match final.

---

# 14. MÉTRICA PRIMARIA

Para cada operating point:

`relative_error_i = |P_sim_i - P_exp_i| / |P_exp_i|`

donde P representa indicated power bajo la misma definición.

Si experimentalmente se utiliza trabajo indicado directamente, se aplicará la misma definición sobre W.

---

# 15. GATES DE ERROR POR PUNTO

Para PASS:

cada punto deberá satisfacer:

`relative_error_i <= 15%`

Además:

al menos:

`80%`

de los operating points deberán satisfacer:

`relative_error_i <= 10%`

Con exactamente cinco puntos:

al menos 4 de 5 deben tener error <= 10%

y ninguno puede superar 15%.

---

# 16. MÉTRICA GLOBAL

Se calculará:

`MAPE = mean(relative_error_i)`

Gate:

`MAPE <= 10%`

Este gate es adicional a los gates individuales.

No permite compensar un punto extremadamente malo mediante otros muy buenos.

---

# 17. SIGNO

El signo del trabajo/potencia indicada simulada debe coincidir con el experimental en todos los operating points.

Una predicción de potencia negativa donde la medición experimental sea positiva, o viceversa, produce:

`P9_FAIL`

para el gate de performance.

---

# 18. SHAPE / TREND

Como gate secundario se comprobará que el comportamiento global no sea cualitativamente contradictorio con el experimento.

Si el dataset contiene un máximo interior claramente observado, la posición del máximo simulado deberá encontrarse dentro de:

`± 1 intervalo experimental de RPM`

respecto del máximo medido.

Este gate solo se aplica cuando el muestreo experimental identifica un máximo de manera inequívoca.

No extrapolar un peak fuera del rango ensayado.

---

# 19. PRESSURE TRACE — MÉTRICAS SECUNDARIAS

Cuando exista presión de cilindro suficientemente confiable, registrar también:

- peak cylinder pressure;
- crank angle of peak pressure;
- pressure-trace RMSE;
- integrated indicated work.

Estas métricas son diagnósticas en P9 v1 salvo que sean explícitamente promocionadas a gate antes de inspeccionar los resultados.

No añadir thresholds de presión después de mirar el match.

---

# 20. INCERTIDUMBRE EXPERIMENTAL

Si el dataset proporciona incertidumbre:

debe preservarse.

Registrar para cada magnitud:

- valor;
- uncertainty;
- confidence definition cuando exista.

La incertidumbre no sustituye los thresholds P9 salvo que una revisión contractual anterior al análisis defina un gate específico basado en uncertainty bands.

Si no se conoce la incertidumbre:

registrar:

`EXPERIMENTAL_UNCERTAINTY_UNKNOWN`

Esto constituye una limitación de la fuerza de validación, pero no necesariamente impide ejecutar P9.

---

# 21. CALIBRACIÓN

P9 v1 es:

`VALIDATION_ONLY`

No se permite ajustar parámetros del modelo utilizando el dataset P9.

Queda prohibido ajustar post-hoc:

- port coefficients;
- discharge coefficients;
- heat-transfer parameters;
- combustion parameters;
- ignition;
- friction;
- scavenging coefficients;
- boundary conditions;
- geometry;
- numerical thresholds;

para mejorar concordancia con P9.

Los parámetros de simulación deben quedar congelados antes de revelar los resultados experimentales utilizados para validación.

---

# 22. FUTURA CALIBRACIÓN

Si MotorSim no satisface P9 y se decide calibrar el modelo:

la calibración deberá constituir una fase separada.

Un dataset utilizado para calibración NO podrá posteriormente presentarse como validación independiente del mismo modelo calibrado.

Será necesario reservar o adquirir un dataset distinto para validación.

---

# 23. DATASET FREEZE

Antes de ejecutar la comparación final se creará un manifest del dataset incluyendo:

- filenames;
- SHA-256;
- size;
- operating points;
- channels;
- units;
- metadata;
- exclusions.

Una vez congelado:

no podrá sustituirse silenciosamente un punto experimental.

---

# 24. SIMULATION FREEZE

Antes de revelar la comparación final deberán persistirse:

- MotorSim commit SHA;
- configuration SHA;
- engine geometry SHA;
- runtime binding;
- solver configuration;
- physical constants;
- operating-point definitions.

---

# 25. EVIDENCIA PRIMARY

P9 deberá conservar evidencia primaria suficiente para recalcular offline:

- work;
- indicated power;
- experimental mean;
- experimental uncertainty cuando exista;
- relative errors;
- MAPE;
- gate decisions.

Los summaries no serán autoridad.

---

# 26. AUDITOR P9

El auditor offline debe reconstruir:

raw experimental data
+
primary simulation evidence
→ aligned operating points
→ work/power
→ errors
→ global metrics
→ decision.

No confiar en:

- stored PASS;
- stored MAPE;
- stored relative errors;
- summary-vs-summary equality.

---

# 27. NEGATIVE TESTS

Antes de aceptar P9, el auditor debe rechazar como mínimo:

- NaN;
- inf;
- booleano usado como número;
- unit mismatch;
- dataset hash mismatch;
- missing operating point;
- duplicated operating point;
- RPM mismatch >1%;
- missing primary simulation evidence;
- modified experimental value with unchanged manifest;
- modified summary;
- modified derived metric;
- incomplete periodic qualification.

---

# 28. CLASIFICACIONES

## P9_PASS

Se cumplen:

- dataset válido;
- todos los operating points pasan P9-A;
- todos los puntos tienen error <=15%;
- al menos 80% tienen error <=10%;
- MAPE <=10%;
- signo correcto en todos los puntos;
- demás gates contractuales PASS.

---

## P9_FAIL

Existe evidencia experimental válida y completa, pero uno o más gates científicos preregistrados no se cumplen.

FAIL es un resultado científico legítimo.

No modificar thresholds después de obtenerlo.

---

## P9_INCONCLUSIVE

La evidencia existe pero no permite una decisión válida, por ejemplo:

- metadatos críticos incompletos;
- operating point ambiguo;
- incertidumbre/medición insuficiente;
- evidencia de simulación incompleta;
- problemas de integridad de datos.

---

## P9_EXPERIMENTAL_DATA_REQUIRED

No existe un dataset experimental autorizado suficiente para ejecutar el contrato.

No es FAIL.

---

# 29. CLAIM PERMITIDO TRAS PASS

Si P9 pasa, la afirmación máxima permitida será equivalente a:

`EXPERIMENTALLY_VALIDATED_FOR_THE_TESTED_2T_CONFIGURATION_AND_OPERATING_DOMAIN`

No utilizar:

`universally validated`

ni:

`predictively validated for arbitrary engines`.

---

# 30. CLAIM SI FALLA

Si P9 falla:

preservar resultados completos.

No recalibrar dentro de la misma campaña.

El resultado deberá permanecer:

`P9_FAIL`

para esa versión congelada del modelo.

Una versión futura modificada deberá ejecutar un nuevo proceso de validación.

---

# 31. PREREGISTRATION

Este contrato deberá:

1. convertirse en especificación OpenSpec P9;
2. recibir versión;
3. registrar commit SHA;
4. registrar fecha;
5. marcarse `PREREGISTERED`;
6. ocurrir ANTES de incorporar el dataset experimental de decisión.

Después de la preregistración no podrán modificarse:

- métricas;
- thresholds;
- reglas de alineación;
- número mínimo de puntos;
- criterios PASS/FAIL;

sin crear una nueva versión contractual y declarar invalidado el intento anterior para decisión confirmatoria.

---

# 32. ESTADO INICIAL DESPUÉS DE PREREGISTRAR

Hasta disponer de datos experimentales:

`P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`

P4 continúa:

`P4_PASS`

P5–P8:

`REVALIDATED_ON_P4_PASS`

P8:

`BOUNDED_TRANSIENT_INDICATED`

Experimental validation:

`NOT_PERFORMED`

Predictive validation:

`NOT_CLAIMED`