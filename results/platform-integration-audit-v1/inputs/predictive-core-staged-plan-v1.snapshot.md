# Núcleo predictivo Dino2T — plan por etapas v1

Fecha: 2026-10-27. Base de código verificada: `f5c0576`. Objetivo vigente:
`DINO_PREDICTIVE_RELIABILITY_V1`. Decisión del dueño registrada:
`OWNER_DECISION_PREDICTIVE_CORE_OPTION_A`.

Alcance: conseguir primero un **monocilíndrico atmosférico numéricamente
convergente y experimentalmente validado**, con incertidumbre cuantificada. La
cobertura funcional y la comparación de paridad con EngMod2T quedan diferidas
hasta que el núcleo físico pase sus gates. Este plan sustituye, para el núcleo
físico, la secuencia de `docs/roadmaps/dino-2t-professional-roadmap-audit.md`
(2026-10-16); conserva sus etapas de producto como referencia histórica.

No se promociona automáticamente ningún candidato. No se exige que las nuevas
formulaciones reproduzcan la física legacy. No se modifican contratos P0–P9, la
baseline rc7, los checkpoints ni la evidencia histórica.

## 1. Estado verificado al iniciar este plan

| Área | Estado | Evidencia |
|---|---|---|
| Acoplamiento cámara–conducto | Tobera ideal equivalente V2 **opt-in**; resuelve 1008/1008 estados declarados; legacy sigue siendo default | `results/predictive-reliability-v1/transonic-v2-receipt.json`, `connection-domain-receipt.json` |
| Orden espacial | MUSCL V1/V2 **opt-in**; orden aislado observado >2.12; celdas de frontera V2 ya no son primer orden | `results/predictive-reliability-v1/spatial-convergence-v1.json`, `spatial-boundary-v2-engine/receipt.json` |
| Motor integrado | Sólo diagnóstico de dos revoluciones (transitorio). Trabajo 44/88/176 = 28.5676/29.4581/30.2026 J; orden ajustado 0.258; GCI no certificable | `results/predictive-reliability-v1/mesh-three-level-analysis-v1.json` |
| Sensibilidad espacial/temporal | Diferencia proyectada de malla 12.27 %; diferencia temporal normalizada 0.0945 %; periodicidad no demostrada | `results/predictive-reliability-v1/endpoint-sensitivity-v2.json` |
| Transporte de especies y salida | Frentes aislados convergen en L1/L2 y anchura; conservación ~1e-14; la frontera real coincide con reservorio sólo en régimen saliente | `results/predictive-reliability-v1/outlet-front-control-v1/report.md` |
| Salida pulsante | Reflexión de pulso débil converge en L1 con signo correcto; balances <2.2e-15; control acústico lineal, no choque finito | `results/predictive-reliability-v1/pulsating-outlet-control-v1/receipt.json` |
| Piloto de periodicidad | Ejecutado: 9 ciclos adicionales desde checkpoint nativo del ciclo 2; `TRANSIENT_AT_BUDGET`; no se detectó período; sin extensión | `results/predictive-reliability-v1/bounded-periodicity-pilot-v1/receipt.json` |
| Térmica de celda móvil | Defecto de denominador corregido: error de conservación ~1e-7 J → ~5e-15 J | `results/predictive-reliability-v1/moving-cell-heat-receipt-v1.json` |
| Validación experimental | No realizada. No hay paquete completo de geometría, condiciones y medición del mismo motor | `results/predictive-reliability-v1/measured-data-inventory.json`, `estado-y-limites.md` |
| Baseline rc7 | Preservada y verificada | `results/predictive-reliability-v1/baseline.json` |

## 2. Tres claims que no se mezclan

| Claim | Qué exige | Qué no prueba |
|---|---|---|
| **Verificación numérica** | Referencias analíticas/independientes, conservación, orden observado, replay exacto | Fidelidad física ni precisión |
| **Validación física** | Comparación ciega contra mediciones independientes del mismo motor y condiciones | Cobertura fuera del caso validado |
| **Capacidad predictiva** | Validación + presupuesto de incertidumbre (numérica, paramétrica, de modelo) + sensibilidad de diseño mayor que la incertidumbre | Extrapolación a otra arquitectura |

Un PASS en una fila no promueve la siguiente. Periodicidad, conservación exacta
y número de tests no son validación.

## 3. Reglas transversales

1. **Sin promoción automática.** Un candidato pasa a default sólo por decisión
   explícita posterior a un PASS de E1 y con identidad física versionada.
2. **Legacy es control, no objetivo.** Las diferencias físicas con legacy son
   esperables si el modelo anterior era incorrecto. Legacy se conserva para
   regresión bit-idéntica e historia; no se exige igualdad de resultados.
3. **Núcleo antes que cierres.** No se implementan barrido multi-zona,
   combustión de dos zonas, calor dependiente del estado ni FMEP correlacionada
   antes de cerrar E1.
4. **Rendimiento condicional.** Se optimiza sólo si impide la verificación
   periódica, y sin cambiar ecuaciones, CFL, tolerancias, conservación ni
   reproducibilidad.
5. **Datos reales sin invención.** Si X30, Honda RS125 o Cahoon siguen
   incompletos, se continúa la búsqueda documental; no se rellenan parámetros.
6. **Identidad explícita.** Toda formulación nueva lleva schema, hash de fuente,
   configuración nativa y criterio de aceptación versionados.
7. **Evidencia histórica intocable.** rc7, checkpoints, receipts y
   clasificaciones previas se conservan; una corrección produce evidencia nueva,
   no un replay reescrito.
8. **Sin funcionalidad comercial** hasta que E5 pase.

## 4. Etapas

### E0 — Estado de referencia y decisión (cerrada)

**Entregable:** este documento; decisión del dueño y tareas de cola en
`results/2t-commercial-core-20261002/program-status.json`.

**Criterio:** `program_status.py check` PASS; sin cambios de física ni de
baseline.

**Decisión:** PASS.

---

### E1 — Verificación integrada de candidatos, sin promoción

Objetivo: demostrar que tobera V2 y MUSCL funcionan en el motor integrado,
alcanzan periodicidad y convergen con refinamiento de malla. Ningún candidato
cambia el default.

#### E1.1 Identidad, conservación y determinismo

- **Entregable:** `results/predictive-reliability-v1/candidate-identity-conservation-v1.json`.
- **Corridas:** dos ciclos, 44 celdas, cuatro configuraciones con identidad
  hasheada: legacy, tobera V2, MUSCL V2, tobera V2 + MUSCL V2.
- **Criterios:** residuo normalizado de masa/momento/energía/especies ≤1e-12;
  cero estados inadmisibles; cero clipping; replay exacto; configuración y
  fuente vinculadas por hash.
- **Presupuesto:** ≤10 min total, ≤50 MiB.
- **Decisión:** PASS si todos; PARTIAL si conserva pero falla replay o
  identidad; FAIL si hay inadmisibilidad o clipping.

#### E1.2 Piloto de periodicidad (ejecutado, PARTIAL)

- **Resultado 2026-10-27:** 9 ciclos adicionales desde checkpoint nativo del
  ciclo 2, `TRANSIENT_AT_BUDGET`; no se detectó período. Sin extensión
  automática.
- **Entregable:** `results/predictive-reliability-v1/bounded-periodicity-pilot-v1/receipt.json`.
- **Protocolo (conservado):** continuación desde checkpoint nativo del ciclo 2
  de la misma corrida, máximo 10 ciclos adicionales, 240 s de pared, checkpoint
  por revolución, detector y umbrales sin cambios.
- **Criterios:** `DETECTED` con todos los observables, o `TRANSIENT_AT_BUDGET`.
  Un período detectado sólo por checkpoint no es un período auditado: exige
  regenerar las primarias con sus recetas.
- **Presupuesto:** ≤240 s, ≤16 MiB.
- **Decisión:** PARTIAL. No se repite el piloto; la siguiente acción es el
  diseño costeado `PRED-PERIODIC-CONVERGENCE-COSTED-DESIGN`.

#### E1.3 Convergencia de malla en estado periódico

- **Dependencia:** `PRED-PERIODIC-CONVERGENCE-COSTED-DESIGN`; si el coste
  proyectado excede el presupuesto, E2 se ejecuta antes.
- **Entregable:** `results/predictive-reliability-v1/candidate-periodic-gci-v1.json`.
- **Corridas:** 44/88/176 celdas, estado periódico (no transitorio frío), misma
  identidad física, checkpoint/restart por ciclo.
- **Criterios:** convergencia monótona; GCI ≤2 % en IMEP y potencia; orden
  observado en [0.5, 2.5] o declarado explícitamente; conservación ≤1e-12;
  replay exacto.
- **Presupuesto:** ≤120 min por invocación (gate-critical con checkpoint),
  ≤6 h total entre sesiones, ≤1 GiB.
- **Decisión:** PASS si todos; PARTIAL si hay tendencia monótona pero GCI >2 %;
  FAIL si no es monótono o viola conservación.

#### E1.4 Comparación con legacy

- **Entregable:** `results/predictive-reliability-v1/legacy-control-comparison-v1.md`.
- **Criterios:** legacy bit-idéntico; diferencias atribuidas por subsistema;
  ninguna exigencia de igualdad física; historia no reinterpretada.
- **Decisión:** PASS si el control es reproducible y las diferencias quedan
  explicadas; FAIL si el control legacy deriva.

**Gate E1:** PASS sólo con E1.1 + periodicidad demostrada + E1.3 (GCI ≤2 %).
Con E1.2 PARTIAL el gate queda PARTIAL y no habilita promoción. La decisión
siguiente es costear los ciclos adicionales que falten (`PRED-PERIODIC-CONVERGENCE-COSTED-DESIGN`)
y, si el coste excede el presupuesto, ejecutar E2 antes de continuar.

---

### E2 — Rendimiento (condicional)

**Disparador:** proyección del diseño costeado o de E1.3 >120 min por
configuración o >6 h totales.

**Objetivo:** hacer viable la verificación periódica multi-malla sin degradar
física, conservación ni replay.

- **Entregables:** perfil por subsistema; benchmark preregistrado; receipt de
  equivalencia numérica contra la ruta auditada.
- **Criterios:** ≤0.5 s/ciclo (31–60 celdas); punto periódico ≤2 min; estudio
  de tres mallas ≤60 min; equivalencia dentro de tolerancia preregistrada;
  conservación y replay intactos.
- **Presupuesto:** ≤10 benchmarks de ≤10 min; ≤100 min total; ≤200 MiB.
- **Decisión:** PASS si cumple objetivos y equivalencia; PARTIAL si acelera pero
  no demuestra equivalencia; FAIL si exige cambiar física o tolerancias.

**Nota:** el rechazo histórico de V4 (Numba) se basó en tres ciclos y no
demuestra que la compilación sea inútil en campañas largas. Cualquier backend
nuevo se juzga con amortización a escala, no con un caso corto.

---

### E3 — Cierres `STANDARD_V1`

**Dependencia:** E1 PASS (o PARTIAL con alcance declarado) y E2 si se disparó.

Orden: calor → termodinámica → barrido → láminas → FMEP.

| Cierre | Modelo | Verificación | No se permite |
|---|---|---|---|
| Calor cilindro | Annand/Woschni con área instantánea | Balance contra literatura; sensibilidad de IMEP | Ajustar h a la potencia |
| Termodinámica | γ/cp por composición y T | Límites ideales y conservación | Constantes por conveniencia |
| Barrido | Multi-zona / curva tipo Blair | Curva SE–DR contra datos de aparato de barrido | Calibrar con potencia |
| Láminas | Dinámica acoplada con topes | Lift vs Δp(t) publicado | Fijar rigidez al resultado |
| FMEP | Correlación declarada | Rango y procedencia | Constante sin identificación |

- **Presupuesto:** ≤30 min por benchmark; ≤5 modelos; ≤2.5 h; ≤500 MiB.
- **Decisión por modelo:** PASS si cumple benchmark y conservación; PARTIAL si
  falta banda de literatura; FAIL si viola positividad o conservación.

---

### E4 — Validación experimental ciega

**Dependencia:** E1 PASS + E3 en el alcance del caso.

**Requisito de datos:** geometría completa (incluido volumen libre de cárter con
ángulo de referencia y fronteras), condiciones de operación, salidas medidas con
incertidumbre y procedencia. X30, Honda RS125 y Cahoon se evalúan sin inventar
parámetros; si faltan, la etapa queda bloqueada y continúa la búsqueda.

**Protocolo:** configuración y criterio congelados antes de correr; predicción
ciega; sin recalibrar con el punto reservado.

- **Criterios:** `|E_P| + U95 ≤ 5 %` en el punto; RPM de potencia máxima ±300;
  RMS de forma ≤10 % en 8000–13 000 RPM; IMEP ±5 %; ángulo de p_max ±2°.
- **Presupuesto:** ≤40 min para 20 puntos después de E2; ≤4 h antes de E2, con
  checkpoint/restart; ≤1 GiB.
- **Decisión:** PASS si todos; PARTIAL si dentro de 2× la banda o con
  diagnóstico por subsistema; FAIL si >2× o tendencia incorrecta. Un FAIL no se
  corrige recalibrando el holdout.

---

### E5 — Capacidad predictiva e incertidumbre

**Dependencia:** E4 PASS o PARTIAL con alcance explícito.

- **Entregable:** presupuesto de incertidumbre combinado (numérica por GCI,
  paramétrica U95, de modelo por variantes de cierre) y criterio de sensibilidad
  de diseño.
- **Criterios:** incertidumbre total reportada; diferencia A/B de diseño ≥3× la
  incertidumbre numérica; ningún claim fuera del dominio validado.
- **Presupuesto:** reutilizar corridas + ≤2 h.
- **Decisión:** PASS si el presupuesto es completo y la señal de diseño supera
  el ruido; PARTIAL si la forma del modelo queda sin cuantificar; FAIL si la
  señal de diseño es menor que la incertidumbre.

---

### E6 — Cobertura (diferida)

No se inicia hasta E5 PASS. Orden previsto: editores de admisión/transfers,
carga parcial/mariposa, caja de aire, silenciador, uniones, válvula rotativa,
multicilindro, sobrealimentación. Cada bloque exige su propio gate y no reabre
el núcleo.

## 5. Resumen de gates

| Etapa | Entregable principal | Gate | Presupuesto |
|---|---|---|---|
| E0 | Plan + decisión + cola | `check` PASS | minutos |
| E1 | Periodicidad + GCI periódico | conservación ≤1e-12; GCI ≤2 %; replay exacto | ≤6 h entre sesiones |
| E2 | Optimización condicional | ≤0.5 s/ciclo; punto ≤2 min; equivalencia | ≤100 min |
| E3 | Cierres `STANDARD_V1` | benchmark por modelo; sin ajuste a potencia | ≤2.5 h |
| E4 | Predicción ciega | `|E_P|+U95 ≤5 %`; RPM ±300; forma ≤10 % | ≤4 h |
| E5 | Incertidumbre + sensibilidad | A/B ≥3× incertidumbre numérica | ≤2 h |
| E6 | Cobertura | gates propios | diferido |

## 6. Presupuesto global y control

- Preflight de almacenamiento con reserva de 2 GiB antes de cada campaña; sin
  limpieza automática.
- Checkpoint por ciclo o por invocación; ninguna extensión automática.
- Una invocación gate-critical ≤120 min; campaña ≤60 min salvo autorización
  explícita con checkpoint/restart.
- Toda corrida conserva configuración, hashes de fuente, receta de pasos y
  receipts; los fallos se conservan, no se reemplazan por un PASS posterior.

## 7. Riesgos

1. **Conservación confundida con exactitud.** Se mitiga con referencias y GCI,
   no con más tests de balance.
2. **Periodicidad confundida con validación.** Se mitiga separando E1 de E4.
3. **GCI inasequible a 176 celdas.** Dispara E2; no se reduce la malla para
   "pasar".
4. **Dependencia externa de datos.** Se mantiene la búsqueda documental; no se
   sustituye por supuestos.
5. **Sobreajuste de cierres.** Ajuste y holdout separados; defaults versionados.
6. **Deriva de legacy.** Regresión bit-idéntica en cada etapa.

## 8. Próxima acción

Completar `PRED-PERIODIC-CONVERGENCE-COSTED-DESIGN` con coste medido; si el
presupuesto se excede, ejecutar E2 antes de E1.3. Luego ejecutar E1.1 y E1.3
con identidad explícita. No se promociona ningún candidato ni se inicia E3
antes del gate E1.

## 9. Adenda 2026-10-28 — dependencias, evidencia y datos externos

**Alcance.** Esta adenda incorpora la revisión independiente y las observaciones
del owner. No reemplaza el plan: corrige dependencias y criterios. No autoriza
etapas, no ejecuta simulaciones y no modifica rc7, P0–P9 ni evidencia histórica.
`PRED-E2B-PERIODIC-AB-V1` sigue siendo el único trabajo en curso y conserva su
presupuesto de 5400 s. H1 y E2A no se repiten; se reutilizan sus receipts.

### 9.1 Evidencia disponible (reutilizar, no repetir)

| Área | Evidencia verificada | Límite |
|---|---|---|
| Ley de lumbreras V2 | `transonic-v2-receipt.json`: 1008/1008 estados algebraicos; residuales máx. masa `1.78e-15`, energía `5.55e-16`, velocidad acústica `6.25e-13`; 37 estados antes no soportados recuperados | `physical_steps: 0`; `experimental_validation: false`; cierre `EQUIVALENT_IDEAL_NOZZLE_NOT_SEPARATED_EXPANSION`; no valida pérdidas reales, separación, flujo inverso real ni respuesta pulsante |
| Ley de lumbreras V1 | `connection-domain-receipt.json`: 971/1008 soportados, 37 no soportados; `ADOPTION_BLOCKED_DOMAIN`; `engine_simulations: 0`; `integrated_model_enabled: false` | No es default; no se promociona por comparación con V2 |
| Referencia de restricción | `restriction-receipt.json`: 1029 tests, conservación y límites de referencia numérica | No demuestra compatibilidad de momento/acústica en conductos |
| Frente de especie / pulso | `outlet-front-control-v1` y `pulsating-outlet-control-v1`: convergencia L1, conservación ~`1e-15`; amplitud reflejada `0.734/0.896/0.963` y L1 final `4.05/1.50/0.43 %` en 32/64/128 celdas | Acústica lineal, no choque finito ni escape pulsante completo; no es validación experimental |
| Espacial integrado | MUSCL V2 opt-in; orden aislado >2.12; trabajo 44/88/176 = `28.5676/29.4581/30.2026 J` | Orden observado `0.258`; GCI no certificable; diferencia espacial/temporal proyectada `12.27 %`; no usar este transitorio para calibrar |
| Periodicidad | Piloto acotado de 9 ciclos, `TRANSIENT_AT_BUDGET` | No se detectó período; no se extendió; no hay resultado periódico validado |
| Térmica moving-cell | Bug de conservación corregido: de ~`1e-7` a ~`5e-15 J` | No valida la ley de pérdida; `CONSTANT_H_V1` y área fija siguen siendo aproximaciones |
| Datos medidos | `measured-data-inventory.json`: A9000 es derivado funcional Blair/Cartwright, no medición same-engine | `validation_blocker`: falta paquete motor medido completo, salidas independientes y U95 defendible; `experimental_validation_performed: false`; `predictive_accuracy_claimed: false` |

El owner menciona “100 estados”; el receipt registra **1008**. Se usa el valor
del receipt y no se repite la verificación algebraica.

### 9.2 Dependencias corregidas

Los IDs son de planificación; no crean tareas de cola ni autorizan ejecución.

| Obs. | ID propuesto | Depende de | Entrega | Gate / criterio | No autoriza |
|---|---|---|---|---|---|
| 1 | `E1.0-PORT-LAW-EVIDENCE` | Receipts V2/V1/restriction y auditoría H1 | Matriz de evidencia y diseño del benchmark físico independiente de la ley de lumbreras | Si no hay referencia independiente para pérdidas, flujo inverso y pulso, V2 sigue experimental; no hay promoción | Simulaciones nuevas ni repetir H1 |
| 2 | `E3.5-COMPONENT` | Datos externos | Plan de banco de flujo, tubo de pulso y motor motado cuando existan datos | Distinguir factible con evidencia actual de requiere medición nueva; no declarar banco disponible sin verificarlo | Inventar datos o sustituir mediciones |
| 3 | `E3.0-UNCERTAINTY` | E1.3 y E3 | Presupuesto de incertidumbre | Numérica + paramétrica + experimental + forma de modelo; U95 solo si todos los componentes son defendibles | Declarar U95 antes de tener componentes |
| 4 | `E5-AB-TOTAL` | `E3.0`; `E4-PREREG` para el criterio y E4 para el cálculo | Criterio preregistrado y cálculo de la incertidumbre total de la diferencia A/B | Incluir covarianza entre variantes; definir el criterio antes de ver mediciones; exigir ≥3× la incertidumbre total, no solo la numérica; si no, no hay claim de diseño | Usar GCI como única incertidumbre |
| 5 | `E2-FALLBACK` | Coste medido de E1.3 | Decisión de presupuesto | No bloquea la validación; si no se alcanza `0.5 s/ciclo`, presupuesto alternativo con autorización del owner; no relajar periodicidad ni precisión | Acelerar degradando física |
| 6 | `E1.3-PERIODIC-GCI` | `PRED-PERIODIC-CONVERGENCE-COSTED-DESIGN` | GCI periódico 44/88/176 para IMEP y potencia | GCI solo si orden observado y régimen asintótico lo sustentan; si no, cota superior/PARTIAL; no PASS | Campaña extendida o malla reducida para “pasar” |
| 7 | `E3-ORDER` | E1 | Orden de cierres por dependencia e impacto | Intercambio de gases → termodinámica → barrido → combustión → pérdidas; no es secuencia rígida; cada modelo condicionado a evidencia | Calibrar cierres contra potencia |
| 8 | `E4-PREREG` | `E3.0`, `E3.5` y configuración candidata | Prerregistro de calibración y validación independiente | Separar calibración de validación; reservar, preferentemente, una configuración física de escape completa y puntos RPM; el A/B requiere su variante; endpoint primario ΔP/ΔT; revisión independiente antes del claim | Ejecutar E4 antes del prerregistro |

### 9.3 Datos externos necesarios

- **Paquete motor medido completo y del mismo motor:** geometría completa,
  volumen libre de cárter y su referencia, cinemática, leyes de área, conductos,
  escape completo, admisión/láminas, combustible/encendido, condiciones térmicas,
  presión de cilindro, presión de cárter/admisión, presión/temperatura de escape,
  torque/potencia, consumo, AFR/lambda, offset de TDC y incertidumbre de cada
  salida.
- **Par A/B de escape:** al menos una configuración física completa y su
  variante, mismo motor y mismo punto, con ΔP/ΔT medido. El objetivo primario es
  predecir la **variación** de potencia, no solo el valor absoluto.
- **Componentes:** caudal másico vs relación de presiones y lift en banco de
  flujo, sentido directo e inverso; impedancia/reflexión en tubo de pulso;
  presión de motor motado.
- **Fuentes candidatas, aún parciales:** X30 (falta volumen de cárter y detalles
  del ensayo), Honda RS125/Fleck (texto completo y datos), Cahoon (acceso),
  Ohigashi 1971 (candidato de admisión, no motor completo), Gimelli/Andwari
  (parciales). Ninguna se adopta sin verificar completitud y convenciones.

No hay sustituto local para estas mediciones. Sin ellas, la validación
experimental sigue `NOT_PERFORMED` y la precisión predictiva `NOT_CLAIMED`.

### 9.4 Criterios que cambian

- **E4 endpoint primario:** ΔP/ΔT del par de escapes. Potencia/torque absolutos
  pasan a secundarios. Los umbrales `|E_P| + U95 ≤ 5 %`, RPM de potencia máxima
  ±300, RMS de forma ≤10 % en 8000–13000, IMEP ±5 % y ángulo de pico ±2° se
  mantienen, pero solo se evalúan con U95 defendible y prerregistrada.
- **U95 antes de usarlo:** si no se pueden cuantificar los cuatro componentes,
  se reportan por separado y no se declara U95 ni capacidad predictiva.
- **GCI:** no es cota rigurosa ni PASS si el orden observado y el régimen
  asintótico no lo sustentan. Se reporta como cota superior/PARTIAL.
- **A/B:** la diferencia usa incertidumbre total con covarianza, no solo GCI.
- **Revisión independiente:** obligatoria antes de cualquier claim predictivo.

### 9.5 Lo que no cambia

- `PRED-E2B-PERIODIC-AB-V1` (A/B periódico autorizado, distinto de la etapa E2
  de rendimiento) sigue siendo el único trabajo en curso; 5400 s acumulados; sin
  RPM adicional, refinamiento ni etapa posterior automática.
- No se ejecutan simulaciones, no se implementan cambios físicos y no se toca
  rc7, P0–P9 ni la evidencia histórica.
- No se crean tareas de cola ni se promociona ningún candidato en esta adenda.

### 9.6 Próxima acción de planificación

Completar la matriz `E1.0-PORT-LAW-EVIDENCE` con los receipts existentes, sin
simulación, y llevarla a decisión del owner. No iniciar E1.3, E2, E3 ni E4. Al
cerrar E2B, el owner decide si E1.0 entra en cola. E1.0 es evidencia documental,
no una etapa de simulación: no altera el presupuesto ni la próxima acción de §8,
y esta adenda no la reemplaza.

## 10. Adenda 2026-10-29 — decisión C, perfil E2B y desbloqueo de E1.3

**Alcance.** Esta adenda registra la decisión del owner posterior al perfil E2B
y corrige únicamente el objetivo de rendimiento de E2. No modifica física,
CFL, tolerancias, conservación, replay, rc7, P0–P9 ni evidencia histórica. No
promociona candidatos.

### 10.1 Decisión del owner

El owner revisó tres opciones:

- **A:** candidato local acotado; probable PARTIAL, sin promesa de 0.5 s/ciclo.
- **B:** backend compilado/columnar versionado; mayor coste y riesgo antes de
  E1.3.
- **C:** relajar E2 a **2–4×** y continuar E1.3/periodicidad.

El owner respondió literalmente `c`. Decisión vigente:
`OWNER_DECISION_E2_TARGET_RELAX_OPTION_C`. Se selecciona **C**: el objetivo de
0.5 s/ciclo queda como referencia histórica, no como criterio vinculante. El
criterio vinculante pasa a ser una aceleración medida de 2–4× respecto de la
ruta auditada, con equivalencia numérica, conservación y replay intactos.

No se autoriza el backend compilado completo B ni se promociona tobera V2,
MUSCL, HLLC ni ningún otro candidato. La optimización sigue siendo condicional
y no puede degradar física, CFL, tolerancias, conservación ni reproducibilidad.

### 10.2 Evidencia del perfil E2B

Perfil acotado A44/B44, V8, 9000 RPM, `capture_trace=False`, segmentos 0–90° y
180–270°:

- Receipt: `results/predictive-reliability-v1/e2b-step-profile-v1.json`.
- Informe: `results/predictive-reliability-v1/e2b-step-profile-v1.md`.
- Runner: `scripts/diagnostics/e2b_step_profile_v1.py`.
- Reporte crudo:
  `DINO_ARTIFACT_ROOT/predictive-reliability-v1/e2b-step-profile-v1-20261029T132349Z/profile-report.json`,
  SHA-256 `7cb756d6c3b767ea7157c49fcee9c754b87388cd79d8d9d69607373afb711fb4`.
- Presupuesto: 69.2167162001133 s, 504727 bytes (0.481345 MiB); PASS.

Resultados principales (A/B, tramo 180–270°):

- Coste actual: 13.8755/14.3571 s/ciclo; 0.5 s/ciclo exigiría 27.751/28.714×.
- `port_connection` 31.284/29.025 %; EOS 18.529/19.144 %; builtins/intérprete
  18.375/18.721 %; conductos 14.321/14.747 %; solver integrado 9.129/9.544 %;
  especies 3.061/3.164 %.
- `_port_exchange` 5.1728/4.6883 s; `root` 4.7854/4.2975 s; `pressure_wave`
  2.1764/2.1268 s; `reconstruct_v2` 1.6824/1.6364 s; HLLC sólo ~6 %.
- 16 conexiones/paso; 110.9/90.1 roots y 1626.9/1602.8 evaluaciones de
  `pressure_wave` por paso aceptado.
- Amdahl: port root 5× → 1.352/1.320×; port root eliminado → 1.477/1.430×;
  cuatro grupos calientes 10× → 4.04/3.922×; todos los grupos no integrados
  10× → 5.52/5.409×. Son cotas superiores de cProfile, no mediciones.
- El perfil es diagnóstico: cProfile añade 3.69–3.98×; los tiempos planos son
  los vinculantes.

### 10.3 Criterio E2 corregido

El resto de E2 se conserva:

- **Entregables:** perfil, benchmark preregistrado y receipt de equivalencia.
- **Objetivo de velocidad:** 2–4× respecto de 13.8755/14.3571 s/ciclo; el
  0.5 s/ciclo original queda histórico y no puede usarse para declarar PASS.
- **Objetivos funcionales:** punto periódico ≤2 min; estudio de tres mallas
  ≤60 min; equivalencia dentro de tolerancia preregistrada; conservación y
  replay intactos.
- **Presupuesto:** ≤10 benchmarks de ≤10 min; ≤100 min total; ≤200 MiB.
- **Decisión:** PASS si alcanza 2–4×, equivalencia, conservación, replay y los
  objetivos funcionales; PARTIAL si acelera con equivalencia pero queda por
  debajo de 2× o no demuestra equivalencia; FAIL si exige cambiar física,
  CFL, tolerancias o si no acelera de forma reproducible.

### 10.4 Candidato local autorizado

Se autoriza un único candidato local acotado, `PRED-E2-LOCAL-CANDIDATE-V1`, con
foco en el cuello medido:

1. reducir validación/EOS redundante y evaluaciones repetidas de
   `pressure_wave` dentro de `port_connection_v2`;
2. evaluar una inversión de raíz más eficiente sin cambiar el modelo;
3. reducir coste de reconstrucción/EOS sólo si la equivalencia se demuestra.

El candidato no puede cambiar ecuaciones, ramas físicas, CFL, tolerancias,
clipping, conservación ni el estado por defecto. No se autoriza un backend
compilado completo ni una reescritura columnar. La equivalencia se preregistra
antes de medir y se contrasta contra la ruta auditada.

### 10.5 Efecto sobre E1.3

`PRED-CORE-PERIODIC-MESH-GCI` sigue `BLOCKED_LOCAL`: el tramo 176 consumió
969.8315 s y dispone de 230.1685 s frente a 364.115 s necesarios. Una
aceleración de 2× reduce el requisito a ~182.06 s, dentro del remanente; por eso
el candidato local es la tarea de desbloqueo. No se ejecuta 176 hasta que el
benchmark y la equivalencia estén registrados y el coste se recalcule.

La sobreasignación de almacenamiento de E1.1 (101222741 bytes = 96.534 MiB
frente a 50 MiB) sigue pendiente de disposición del owner; no se borra ni se
compacta evidencia.

### 10.6 Cola y próxima acción

- `PRED-E2B-STEP-PROFILE-V1`: DONE.
- `PRED-E2-LOCAL-CANDIDATE-V1`: READY; depende del perfil.
- `PRED-CORE-PERIODIC-MESH-GCI`: BLOCKED_LOCAL con
  `unblock_tasks: [PRED-E2-LOCAL-CANDIDATE-V1]`.
- Próxima acción: implementar y medir el candidato local, preregistrar
  equivalencia, escribir receipt y recalcular el coste de 176. Sin promoción y
  sin iniciar E3/E4.
