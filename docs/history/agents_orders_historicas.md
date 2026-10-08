# Órdenes históricas de AGENTS.md (no operativas)

Copia literal e íntegra de `AGENTS.md` en el commit `fb2544d` (2026-10-06),
antes de la simplificación `AGENTS_V2`. Se conserva como provenance y registro
de decisiones. **Nada de este archivo es una instrucción operativa vigente**:
los STOP, "detenerse", "nueva autorización", "único escritor", "tasks.md como
único registro" y demás reglas de órdenes anteriores quedan superados por el
`AGENTS.md` actual. Los estados científicos aquí citados son históricos; el
estado vigente vive en `results/2t-commercial-core-20261002/program-status.json`.

---

# MotorSim — Instrucciones de trabajo para Codex

## ORDEN VIGENTE — MOTORSIM AUTONOMOUS ENGINEERING TEAM

Esta sección es la instrucción operativa vigente del repositorio. Reemplaza,
únicamente donde exista conflicto, las instrucciones históricas de este archivo
relativas a:

- un único agente/escritor como única modalidad permitida;
- detenerse obligatoriamente después de cada cambio;
- requerir nueva autorización humana después de cada entrega;
- prohibición de mantener un roadmap o cola autónoma;
- «La física requiere otra definición»: queda permitida la creación de
  capabilities físicas nuevas y versionadas dentro del alcance del cambio
  `openspec/changes/motorsim-2t-commercial-core`, preregistradas antes de la
  campaña que las utilice, sin modificar las versiones históricas;
- STOP históricos asociados a P4-R*, superados por evidencia posterior
  (`results/p4-g2-v2-20260929/decision-final.json`, clasificación `P4_PASS`).

Las secciones históricas se conservan como provenance y registro de decisiones,
pero NO representan el estado operativo actual cuando contradicen esta sección.

### Estado científico vigente

- P4: `P4_PASS` (`results/p4-g2-v2-20260929/decision-final.json`).
- P5–P8: `REVALIDATED_ON_P4_PASS`
  (`results/p5-p8-revalidation-20260929/revalidation.json`).
- Revisión independiente P4–P8: `INDEPENDENT_REVIEW_PASS`
  (`results/p4-p8-independent-final-pass-20260930/review.json`). Cubre P4–P8,
  no el Commercial Core.
- Commercial Core: aceptación independiente del producto completo
  `NOT_PERFORMED`; los deltas recientes de configuración integrada recibieron
  revisiones independientes puntuales, sin aceptación end-to-end.
- P8 semantics: `BOUNDED_TRANSIENT_INDICATED`.
- Regresiones P4–P8: la revisión externa del rango `ab92aee..8cdf66e` registró
  **300 pruebas PASS**. No usar el conteo histórico 346 como conteo vigente;
  reejecutar la suite antes de cualquier cierre global.
- P9: `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`; contrato congelado,
  SHA-256 `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`
  de `openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md`.
- Experimental validation: `NOT_PERFORMED`. Predictive validation: `NOT_CLAIMED`.
- KT100: `KT100_REFERENCE_CASE_V1`, caso de referencia, no validación. La
  campaña de recuperación R1 está consumida y KT100 no está verificado. R1
  terminó en 5000 RPM durante cycle24 a 142.19487248520613°; se reprodujeron
  exactamente cycles21–23 desde el checkpoint cycle20. El fallo se atribuyó a
  `rhoY` legado una ULP sobre `rho`, y se añadió un adaptador P5 acotado sin
  cambiar las ecuaciones termodinámicas. No hay periodicidad ni calificación
  física; los otros cuatro puntos no se iniciaron. No ejecutar KT100 R2 sin un
  nuevo preregistro autorizado.
- `FUEL_LIBRARY_V1` registra ANCAP Super 95/Premium 97 con RON documentado y
  propiedades químicas desconocidas en `null`; sus perfiles no proporcionan
  AFR/LHV ni habilitan combustión. Su biblioteca,
  provenance e instantánea versionada/hash están implementadas. El perfil puro
  C8H18 `MODELED_SURROGATE` y el enlace aditivo `FUEL_COUPLED_COMBUSTION_V2`
  consumen un snapshot completo; la combustión sintética V1 permanece intacta.
  No se infiere propiedad de lote ANCAP ni se añade P7.
- El collector V4 y Fixture C piston-port sin reed están verificados con
  evidencia sintética existente. Reed dinámica tiene geometría sintética
  preregistrada, componente autónomo y enlace a `IntegratedEngine2T` en las
  mismas etapas SSPRK2, incluyendo volumen variable del endpoint de admisión,
  trabajo de cárter, CFL, identidad/restart y señales V4. La comprobación es
  sintética y acotada; no valida un motor real ni KT100, y no acepta el
  Commercial Core.

Estado machine-readable del Commercial Core:
`results/2t-commercial-core-20261002/program-status.json`; documentación:
`docs/gasdynamic/2t_commercial_core_status_20261002.md`.

### Reconciliación de auditoría y continuidad del equipo

La auditoría independiente `docs/gasdynamic/audit_8cdf66e.md` cubre exactamente
`ab92aee..8cdf66e`; sus hallazgos se reconciliaron con el HEAD actual sin
revertir commits posteriores. `AUD-01`…`AUD-18` y sus estados/clasificaciones
viven en `results/2t-commercial-core-20261002/program-status.json`. La remediación
de auditoría ya no es el modo operativo: los items de auditoría están cerrados a
nivel de finding o explícitamente resueltos por decisión humana. Las tareas
ingenieriles que surgen de un finding pueden seguir en la cola de trabajo sin
reabrir retrospectivamente la auditoría.

La errata de la auditoría que cuenta dos defectos se interpreta como tres: A1,
A2 y A3 bloqueaban la evidencia de ciclos. Los ciclos A/B históricos permanecen
`HISTORICAL_SUPERSEDED_BY_POSTHOC_AUDIT` y no sirven como evidencia vigente.
AUD-11 quedó resuelto como `CASE B — CAPABILITY LIMITATION` por decisión humana;
`OPEN_END_PLENUM_V2` sigue como tarea de implementación preregistrada separada.
Ver `docs/gasdynamic/open_end_plenum_v2_preregistration.md`.

### Modalidad operativa vigente

MotorSim se desarrolla bajo `MOTORSIM_AUTONOMOUS_ENGINEERING_TEAM`. El Codex
principal actúa como coordinador/tech lead y conserva la responsabilidad de
integrar. Puede usar subagentes, agentes read-only, worktrees u otras
capacidades de delegación cuando sean útiles y seguras. No se requiere
autorización humana entre tareas dentro del alcance vigente.

Si no hay subagentes, realizar pasadas secuenciales con roles separados. Una
autorrevisión secuencial NO puede etiquetarse como revisión independiente.

### Continuidad y presupuesto

La cola durable machine-readable (`READY`, `IN_PROGRESS`, `BLOCKED_LOCAL`,
`REVIEW`, `DONE`) vive en el campo `queue` de
`results/2t-commercial-core-20261002/program-status.json` y se actualiza en el
mismo commit que cambia el estado de una tarea. Para el modo autónomo, esta cola
sustituye a `tasks.md` como registro detallado de avance; `tasks.md` del cambio
`motorsim-2t-commercial-core` conserva sus tareas y remite a la cola. Al retomar
una sesión, leer `AGENTS.md`, `docs/gasdynamic/autonomous_engineering_mode.md`
y `program-status.json`, y continuar sin reconstruir planificación.

Un `BLOCKED_LOCAL` no detiene el programa mientras exista otra tarea `READY`.
Presupuesto de cómputo (estimar antes con una corrida corta): diagnóstico
≤10 min; campaña de fixture/integración ≤30 min por configuración; campaña
científica larga ≤60 min continuos, ampliable a 120 min sólo si es gate-critical,
tiene checkpoint/restart usable, persiste progreso y no hay alternativa más
barata. Una proyección mayor es `PERFORMANCE_BLOCKED_LOCAL`, no STOP global; no
se reduce precisión, CFL ni umbrales para cumplir el presupuesto.

Solo se escala al humano una decisión científica cuando existan alternativas
físicamente legítimas con consecuencias materiales y teoría, evidencia,
contratos y tests no permitan resolver entre ellas. Bugs, refactors, APIs,
schemas, performance, serialización, tests, documentación y mantenimiento Git
no requieren autorización humana.

### Protección histórica

No modificar retrospectivamente P4–P9 para facilitar trabajo nuevo. Las nuevas
capacidades se crean como capabilities/versiones nuevas. No modificar
tolerancias, umbrales, expected values o tests existentes solamente para
conseguir PASS. Un criterio nuevo queda versionado y, cuando corresponda,
preregistrado y commiteado antes de ejecutar la campaña que lo utiliza.

### Git

No force-push, no reset ni rebase destructivo, no publicar ni hacer push
automático. No incorporar archivos históricos/untracked al staging sin
inspeccionarlos primero; los directorios `results/kt100-hybrid-model-fixture-v2-harness-20261002*`
no versionados se preservan. Commits pequeños y semánticos.

Reglas detalladas del programa autónomo:
`docs/gasdynamic/autonomous_engineering_mode.md`.

Esta orden permanece vigente hasta que una nueva sección explícitamente marcada
como ORDEN VIGENTE la reemplace.

## Órdenes históricas

P4-R4 autorizado por orden8f6dbacb: evaluación focal Numba serial, equivalencia
y gates en docs/gasdynamic/p4_r4_numba.md. Sustituye STOP R3 sólo en ese alcance.
Sin cambios científicos, packaging, publicación ni P5. Estados siguientes históricos.

P4-R3: **P4_R3_COMPILED_BACKEND_DECISION_REQUIRED**. Registrados
P4_R2_HUMAN_ACCEPTED y P4B_HUMAN_ACCEPTED, NO P4_HUMAN_ACCEPTED.
NumPy35,469/35,443s por cicloN250,7,42–7,43×, equivalencia exacta; proyección
1064/1063s>600.101tests/regresiones y replayP4A/P4B PASS. Referencia escalar,
151hashes históricos y cinco referenciasR3 intactos. Estado de cierre revisado.
STOP: sin compilados, más optimizaciones/campañas, periodicidad/G2/P5, archivo
ni publicación sin nueva orden. NumPy opcional sólo experimental; no UI/JSON.
[Resultados y opciones](docs/gasdynamic/p4_r3_performance.md). Preservar borrado
ajeno redme.txt. Estados anteriores históricos:

P4-R2: P4_R2_PASS_REFINEMENT_CONTRACT y P4B PASS bajoR2; P4C queda
**P4_BLOCKED_PERFORMANCE**. Ciclo G1 N250 completo en263,328s; proyección30
ciclos7899,84>600s. STOP aplicado antes de G2/multiciclo. E12/E15 sólo ciclo
medido; E13/E14/retorno causal pendientes, sin backflow observado.96 pruebas
y regresiones offlineP0/P2/P3 PASS;151 hashes congelados intactos.
No repetir integración, remallar, optimizar, ampliar presupuesto ni iniciarP5
sin nueva orden. No aceptaciónP4, archivo, UI/JSON, publicación o globales.
[Delta](docs/gasdynamic/p4_refinement_r2.md),
[tareas](openspec/changes/p4-escape-1d/tasks.md). Borrado ajeno redme.txt intacto.
Los estados siguientes son históricos.


P4-R1E: **P4_R1_PREASYMPTOTIC_REFINEMENT_CONFIRMED**.
N800 completo desde t=0 en1139,360s; presión, masa y llegada cumplen la reducción
exigida; conservación/admisibilidad/CFL y controles previos PASS.151 hashes
intactos. Incidencia de auditoría tupla/lista corregida offline sin otra integración;
evidencia nativa conservada, no confundir su fallo con el resultado científico.
[Tablas](openspec/changes/p4-escape-1d/tasks.md),
[decisión](results/p4-r1e-20260921/decision.json) y
[señal completa/poscierre](results/p4-r1e-20260921/signals.png).
STOP: no modificar gateP4, aceptar/archivar ni iniciarP4C/P5 sin nueva orden.
Sin publicación; borrado ajeno redme.txt preservado.

Antecedente de autorización P4-R1E:

P4-R1E autorizado por orden6e7321b2: una sola integraciónN800/CFL0,4 desde
 t=0, con timeout1500s exclusivamente operativo. No checkpoint reanudable por
la API congelada (tiempo/eventos/ledger); no se implementa resume. Reutilizar
los ocho completos anteriores, observables y criterios intactos. Sin P4C/P5.
La prohibición histórica de ampliar900s queda sustituida sólo por esta orden.

Antecedente P4-R1:

P4-R1: **P4_R1_PERFORMANCE_DIAGNOSTIC_REQUIRED**. Sensor histórico desplazado
corregido sólo en postproceso; solver intacto (120 hashes). Temporal focal pequeño,
control convergente; N800 agotó900,031 s antes del cierre (241,439° de300° finales).
Q800 completo y D400→800 pendientes. Ocho casos completos, uno parcial; tres tests
focales y OpenSpec estricto PASS, revisión independiente confirma STOP.
[Tablas y definiciones](openspec/changes/p4-escape-1d/tasks.md),
[decisión](results/p4-r1-20260921/decision.json),
[señales](results/p4-r1-20260921/signals.png) y
[perfil offline](results/p4-r1-20260921/performance.json).
No nueva integración, ampliación de timeout u optimización; no aceptaciónP4,
modificación de gate, P4C/P5, publicación o archivo. Borrado ajeno redme.txt intacto.

Antecedente de autorización P4-R1:

P4-R1 autorizado por orden47e73e41: diagnóstico focal con solver congelado,
observable de presión en x=0,1 m y ledger de masa. Definiciones fijadas en
[observables](docs/gasdynamic/p4_r1_observables.md). Esta autorización permite
únicamente las repeticiones focales allí descritas; no cambia el gate P4 ni
habilita P4C/P5. Estado anterior conservado a continuación.


P4: **P4_BLOCKED_WAVE_PHYSICS / SCIENTIFIC_CHANGE_REQUIRED**.
P3_HUMAN_ACCEPTED registrado y archivado; P0/P2/P3 congelados intactos.
P4A/E01–E05 PASS. P4B ejecutó16 casos individuales PASS, pero el refinamiento
100/200/400 de descarga incumple diferencias decrecientes de presión integrada
e intercambio de masa. Revisión independiente confirma fallo desde estados
finales, sin bug del agregador. No cambiar criterios ni repetir campañas para
forzar cierre. P4C no habilitado/implementado; sinP5, UI, JSON o publicación.
88 pruebas y regresiones offlineP0/P2/P3 PASS. [Decisión/evidencia](results/p4-exhaust-20260918/decision.json)
y [tareas y tablas](openspec/changes/p4-escape-1d/tasks.md). Preservar los fallos
nativos de infraestructura documentados; no son la causa del bloqueo científico.

Antecedente de autorización:

P3_HUMAN_ACCEPTED por orden cec0f5b3; baseline ec6ec55 congelado y cambio
archivado. Autorizado únicamente P4 experimental, cambio p4-escape-1d.
Sin reemplazarlegacy/UI/JSON; P4C sólo trasP4A/P4B PASS, sinP5 ni publicación.
Revisión independiente y STOP ante cambio científico necesario.

Antecedente histórico:

P3-R1: **P3_PASS_0D_1D_COUPLING_VERIFIED / WAITING_HUMAN_APPROVAL**.
Interfaz Riemann de cámara homogénea estancada, conservativa por etapa; C00/C00B
y C01–C12 PASS, adaptador de estado aislado2T/4T. 83 pruebas y regresiones
completas offline P0/P2 PASS; 27 hashes congelados intactos. Revisión científica
independiente PASS; aceptación humanaP3 pendiente. Sin conexión productiva,
P4, publicación ni archivo. [Evidencia y decisión](results/p3-r1-20260918/decision.json),
[definición](docs/gasdynamic/0d_1d_coupling_r1.md) y
[registro de casos](openspec/changes/archive/2026-09-18-p3-acoplamiento-conservativo/tasks.md).
Los gates nativos BLOCKED por falta de reviewer hook se conservan; el dictamen
independiente se adjunta separadamente. La orden38a85593 autoriza R1 y sustituye
sólo el cierreP3 reservoir, no las BC ni el núcleoP2.

Antecedente histórico (bloqueo anterior resuelto por nuevo objeto físico R1):

P3: **P3_BLOCKED_BACKFLOW / SCIENTIFIC_CHANGE_REQUIRED**.
P2_HUMAN_ACCEPTED registrado; núcleo y contratos congelados. El preflight
reproduce ausencia de rama/discontinuidad de reservoir al invertir flujo con
entropías distintas. No modificar la frontera para forzar avance sin decisión
científica. Interfaz preparatoria aislada, sin integración finita ni producto.
74 pruebas y regresiones offline P0/P2 PASS no acreditan P3. P3B/P3C pendientes;
sin P4, publicación o archivo. [Evidencia y bloqueo](results/p3-coupling-20260918/analysis.md).

Antecedente de autorización:

Orden a75bf738: **P2_HUMAN_ACCEPTED**, núcleo1D y contratos congelados.
Autorizado exclusivamente P3 aislado mediante dev_orchestrator. Preflight de
frontera reservoir antes de P3A; sólo P3A PASS habilita volumen finito/P3B,
y sólo volumen fijo PASS habilita P3C. Sin P4, producto, UI, JSON o publicación.
Cambio: openspec/changes/p3-acoplamiento-conservativo. Ante una incompatibilidad
del contrato congelado, SCIENTIFIC_CHANGE_REQUIRED, sin cambiar la BC.

Antecedente histórico:

P1-R5E: **P1_R5_PASS_CFL_SECOND_ORDER_CONTRACT**; adoptado R5 solo para
T11 segundo orden tras nueve finales y revisión científica independiente.
**P2_PASS_1D_CORE_VERIFIED / WAITING_HUMAN_APPROVAL**: T01–T12 PASS,
T12 10/10; 70 pruebas, siete regresiones históricas P0 offline, FIRST_ORDER/R4
preservado. T10 N800: 526,656 s; órdenes 400→800: rho 1,906602 / especie 1,906890;
T11 N1600/CFL 0,2: 304,844 s. Sólo dos integraciones nuevas, solver intacto.
Aceptación humana P2 pendiente; NO iniciar P3, archivar ni publicar.
Los gates nativos BLOCKED por falta de reviewer conectado se conservan;
[decisión derivada con revisión independiente](results/p1-r5e-20260918/decision.json)
y [tablas, delta y resultados](results/p1-r5e-20260918/analysis.md).

Antecedente histórico:

P1-R5 (orden350ec78f): **P1_R5_CFL_SECOND_ORDER_UNRESOLVED**.
Revisión offline de ocho finales y un parcial: SSP no implica monotonía CFL
entre mallas, pero falta N1600/CFL0,2 para justificar todas las cláusulas R5.
No se adopta R5; **P2_BLOCKED_SECOND_ORDER**. Fases B/C no habilitadas;
no nuevas integraciones, cambios de solver ni P3. R4 y presupuesto3/3 intactos.
[Análisis y tablas](results/p1-r5-cfl-20260918/analysis.md).

Antecedente histórico:

## Lectura y autoridad

Última orden12b4cba5: reanudación P2B con300s/caso, sin cambios científicos.
Estado vigente **P2_BLOCKED_SECOND_ORDER / SCIENTIFIC_CHANGE_REQUIRED**:
T11 CFL0,4/0,6 incumple monotonía estricta R4 entreN400 yN800, demostrado desde
seis arrays finales completos. Dos timeouts adicionales: T10_800 yT03_0.2_N1600.
T01–T09 yT12(10/10) PASS; no P2PASS niP2_HUMAN_ACCEPTED, noP3.
PresupuestoP2B3/3 agotado, todos fixes de infraestructura/evaluación; solver
4620200 y contratos siguen exactos. No más reparación/campaña/modificación
científica sin nueva orden. No reinterpretar el incumplimiento como sólo timeout.
La revisión anterior que decía sóloinfra quedó corregida explícitamente.
Evidencia/decisión: results/p2b-gas1d-20260918/resume-decision.json.
Sin push, archivo, UI/JSON, cambios globales ni nueva física.

Antecedente histórico:
Orden vigente: P2B tras **P1_R4_HUMAN_ACCEPTED** y **P2A_HUMAN_ACCEPTED**.
MUSCL/minmod SSP-RK2 implementado, first-order congelado. Estado actual
**FAILED_INFRASTRUCTURE**: T04 agotó120s; T01–T03 PASS, T12 parcial4/10,
T05–T11 no ejecutados. No afirmar P2B/P2 PASS ni P2_HUMAN_ACCEPTED.
Revisión independiente confirma STOP sin bug adicional identificado. Presupuesto
P2B1/3 (comprobador CFL, no integración); presupuesto previo P2A3/3 intacto.
No repetir campaña ni ampliar presupuesto temporal sin resolver el bloqueo
explícitamente. No modificar P0/contratos congelados/UI/JSON ni iniciar P3.
La orden actual extiende el refinamiento R4 a MUSCL sin restaurar8%; ver diseño
P2 y evidencia results/p2b-gas1d-20260918. Sin push, archivo o cambios globales.

Antecedente histórico:
Orden más reciente: `p1-r4-cfl`. P1_R4_PASS_T11_REFINED_CONTRACT adoptó
1D_CONTRACT_V1_R4 tras estudio congelado y revisión independiente.
P2A_PASS_FIRST_ORDER_VERIFIED: T01–T12 bajo R4, seis runs T11 nuevos y46
reutilizados con hashes,52 reevaluados. El fallo8% de R3 permanece diagnóstico;
R4 retira esa garantía y exige convergencia con límites T03 originales.
No modificar solver/contratos anteriores/P0 ni reinterpretar PASS como aceptación
humana de P2. P2B/P3 no iniciados en esta entrega; human gate P2 pendiente.
La revisión científica no reinicia presupuesto de reparaciones3/3. Sin publicar,
archivar, integrar comandos globales o cambiar UI/JSON/EXE. Ver tareas R4.

Antecedente histórico:
Orden más reciente: `p1-r3-fronteras`. P1_R3_PASS_BOUNDARIES_SEPARATED:
contrato1D_CONTRACT_V1_R3 adoptado antes del código; T05 PASS y NR01 diagnóstico.
P2A revalidado completo: T01–T10/T12 PASS, T11 FAIL (amplitud CFL0,6 frente0,2:
0,08336382706 >0,08). 52 casos individuales PASS no acreditan P2A.
STOP P2A BLOCKED, revisión independiente coincide;3/3 reparaciones consumidas.
No más fixes, cambios de umbral/CFL, P2B ni P3 sin nueva decisión autorizada.
Human gate de P2 pendiente. Conservar v1/R2, T02/T06, baseline0D e históricos.
Sin publicar, archivar ni modificar UI/JSON/EXE/configuración global.

Antecedente histórico:
Orden más reciente: `p1-r2-contacto`. P1_R2_PASS_CONTACT_OBSERVABLE adopta
1D_CONTRACT_V1_R2 sin alterar v1/T06. P2A NO reanudado: T05 tiene ramas
incompatibles, SCIENTIFIC_CHANGE_REQUIRED. Excepción de velocidadcero retirada;
solo fixes de contabilidad y exterior no reflectivo retenidos. No iniciar P2B/P3
ni modificar BC sin nueva decisión científica. Ver tareas y evidencia del cambio.

Antecedente: `p1-r1-contacto`, etapa P1_R1_SCIENTIFIC_AMENDMENT.
Estudio acotado del observable T02, sin cambiar solver ni P1 congelado.
Resultado P1_R1_CONTACT_ACCURACY_UNRESOLVED: B supera2dx en N400; STOP.
Sin R1 adoptado ni autorización efectiva de fixes P2, T05, P2B o P3.
Las órdenes siguientes conservan su valor histórico; ver tareas del cambio.

Orden vigente: `p2-nucleo-gas1d`. P1_HUMAN_ACCEPTED; contrato P1 congelado.
Implementar/verificar únicamente P2 aislado mediante dev_orchestrator. P2A
first-order precede obligatoriamente a P2B MUSCL/SSP-RK2 con gate y revisión.
Máximo3 reparaciones de implementación, nunca cambiar P1 para pasar. Sin UI,
JSON, acoplamiento 0D, EXE ni P3. P0 y producción anterior conservan hashes.

Antecedente histórico:
Orden vigente: `p1-contrato-gas1d`. Registrar P0_HUMAN_ACCEPTED sin modificar
baseline congelado; ejecutar solo P1 contractual por dev_orchestrator, con cero
reparaciones automáticas y revisión independiente de solo lectura. Sin solver,
UI, JSON de producto, paquetes ni P2. P2–P9 permanecen deshabilitadas. El rango
público 2T 2500–15000 aprobado en d2932da se conserva; no confundirlo con el
estado histórico de P0. Documentos normativos: docs/gasdynamic y cambio P1.
Las órdenes siguientes son históricas y no sustituyen esta autorización.

Orden actual: `positividad-transporte-2t`, candidato conservativo de especie por
etapa RK4, microcasos, campaña baja y regresión histórica; alta RPM solo tras gate.
Mantener física, tolerancias, mínimo, donor, dominio público y candidatas. Integrar
en producción únicamente si aprueba conservación, invariantes e intervención.
Sin clipping, regularización interna, 1D ni cambios de dev_orchestrator.
La infraestructura anterior está registrada en e739cfd/bd0a119 y queda separada.

## DEV ORCHESTRATOR

dev_orchestrator/ es infraestructura de desarrollo y no forma parte del producto ni
del paquete distribuible. El código de motorsim/ no debe depender de ella.

- No incluirla en PyInstaller ni ZIPs; sin dependencias runtime nuevas.
- Puede leer tests/results/specs y ejecutar checks autorizados, no modificar física.
- Detenerse ante SCIENTIFIC_CHANGE_REQUIRED; no cambiar contratos para aprobar.
- Reparaciones/reintentos acotados; sin agentes externos ni encadenamiento autónomo.
- Revisor de solo lectura; el stub dummy no acredita revisión científica independiente.
- Registrar cambios previos, no borrarlos ni atribuirlos a la ejecución.
- No archivar, publicar, modificar configuración global ni empaquetar en esta tarea.

## Órdenes anteriores conservadas

Orden posterior a fase A bloqueada: mapear1500/1750/2000/2250/2500/2750/3000
y diagnosticar1000/2000 mediante observación y análisis offline. Mantener solver,
perfil, positividad, mínimo y dominio público. Sin warm-start, campaña alta/4T,
corrección, candidata ni archivo. Revisión independiente puntual de instrumentación
y conservación. El diagnóstico de2000 puede compartir la ejecución del mapa.

Continuación actual de `rendimiento-indicado`: campaña candidata 2T 1000–15000,
ocho RPM obligatorias, mismo perfil B/100 Pa y solver. Separar validación por
ciclo; 4T permanece 2500–3500. Fase B (29 puntos, UI ampliada y exploración
superior) solo después de GO numérico. No cambiar física para superar fallos.
Registrar fase A y decisión antes de empaquetar; sin publicar ni archivar.

Orden actual: `rendimiento-indicado`, derivación de potencia/par indicados desde
W_C/ciclo/RPM de resultados validados. Vista CAE y CSV nuevos; rc6 si aprueba.
No física, solver, pérdidas mecánicas ni valores al eje. Reutilizar históricos,
sin nuevas integraciones; revisión puntual, commits locales, sin publicar/archivar.

Corrección UX rc6 autorizada: Rendimiento asociado al proyecto, reutilización
automática compatible y CTA explícita que invoca el barrido existente. Esta orden
sustituye el límite de solo consulta para esa vista. Comprobar cálculo, cancelación
y capturas Windows sin campañas generales. No empaquetar rc7 en esta tarea;
mantener física, fórmulas, formatos y candidatas anteriores.

Continuación posterior a d15ec98: controles RPM permanentes y recálculo repetible.
Conservar la curva anterior al recalcular/cancelar/fallar, separar compatibilidad
del motor y del plan RPM. Recorrido explícito de tres cálculos y cancelación por
ciclo 2T/4T autorizado; no rc7, cambios numéricos ni campañas adicionales.

Orden actual: `implementacion-ui-cae-final` traslada la referencia visual confirmada
`Desktop/code.html` a Qt Widgets y prepara rc5. Mantener modelos, contratos,
worker, formatos y candidatas anteriores. Pruebas UI, dos puntos 2T/4T y
cancelación; revisión puntual independiente, commits locales sin publicar/archivar.

Continuación actual de `ejemplos-precargados`: cuatro JSON físicos v6 versionados
en examples/projects, generador canónico, carga real y próxima candidata con
los mismos archivos. Sin solver ni campañas; conservar menús y paquetes previos.

Orden actual: `refinamiento-ui-final`, solo presentación/flujo en ocho workspaces.
Preservar física, worker, formatos, reglas y todas las candidatas/evidencias.
La nueva rc4 se distingue por commit, sin sobrescribir la rc4 de ejemplos ni rc3.
Pruebas UI, históricos y un punto/cancelación breve del paquete; sin campañas.
Una revisión independiente puntual; commits locales, sin publicar ni archivar.

Orden actual: `ejemplos-precargados` añade cuatro proyectos sintéticos desde las
referencias canónicas y su carga protegida; candidata rc4 conservando rc3.
Sin cambios físicos/formatos ni campañas. Se permite usar resultados existentes
para comprobar el paquete. Revisión puntual y commits locales, sin publicar/archivar.

Orden actual: `reorganizacion-ui-final` autoriza únicamente arquitectura visual UX,
reutilizar editores/controladores, navegación por tareas y análisis embebido.
Preservar física, contratos, worker, candidatos rc1/rc2 y evidencia. Leer el cambio.
Pruebas UI y paquete final con un punto/cancelación breve, sin campañas científicas.
Revisión puntual independiente, commits locales sin publicar ni archivar.

Leer README.md y el cambio solicitado dentro de `openspec/changes/` antes de
modificar archivos. `base-escritorio` es la entrega inicial; su límite de nombre,
tipo y archivos pertenece a esa entrega. El cambio autorizado actual es
`cuatro-tiempos-basico`: proposal.md, design.md, specs/cuatro-tiempos-basico/spec.md y tasks.md.
Continuación autorizada: `distribucion-windows` es ahora el cambio activo.
Leer sus proposal/design/spec/tasks. Preparar candidata 0.1.0-rc1 Windows x64
PyInstaller onedir con GUI y worker, probar el ZIP extraído y registrar evidencia.
Esta orden sustituye exclusivamente la prohibición de empaquetar: sin ampliar física,
publicar, etiquetar o archivar. Preservar 18194d7/da27ee25 y evidencia anterior.
Tres puntos completos de regresión (2T B3000 y barrido 4T B2500/3000), cancelaciones
breves y máximo conjunto 300 s de integración; no repetir campañas científicas.
Los presupuestos R2 siguientes son históricos, no el presupuesto de distribución.
Hardening autorizado: preservar rc1/f46613e y d6f0c63; corregir tiempos futuros y
defectos concretos de distribución. Si cambia código, construir rc2 limpia. Máximo
una reproducción focalizada de parada y un punto B100/3000 por ciclo 2T/4T;
sin campañas. Clasificar causa sin inventar evidencia; revisión independiente puntual.
Bloque autorizado de entregas 7 y 8: configuración 4T, JSON v6, modelo de tres
volúmenes I/C/E, ejecución e integración condicionadas a los criterios numéricos.
Preservar 6cbed360 y toda evidencia anterior. Entrega 6 conserva herramientas
implementadas y mediciones/validación experimental pendientes, sin bloquear 4T.
La prohibición anterior de iniciar 7 queda sustituida por esta autorización.
Perfiles/tolerancias/física fijados por la orden; máximo 12 ejecuciones previstas,
720 s de integración conjuntos, 60 s por punto. No lanzar etapas dependientes
si falla su condición previa; continuar las independientes. Un único cambio.
Continuación R2 autorizada: vía de estabilidad práctica definida en design.md;
preservar R1 fallida, af11976/b862900 y evidencia. Reutilizar A/B/C sin integrar.
Continuar C50 e integración/protocolo si sus condiciones aprueban, sin reiniciar
los 51,125 s consumidos del presupuesto conjunto.
Commits locales lógicos sin publicar, sin autenticación/configuración global.
No archivar ni ampliar física fuera del bloque autorizado; empaquetado según la continuación anterior.
No alterar retrospectivamente requisitos ni verificaciones de entregas anteriores.

La [hoja de ruta](docs/HOJA_DE_RUTA_MotorSim.md) define el orden, los objetivos y
las exclusiones; la especificación del cambio activo define requisitos y aceptación.
Su `tasks.md` es el único listado detallado de tareas. La sección «Estado de avance»
de la hoja resume las entregas, sin duplicar ese listado.
Al retomar una sesión, leer esos archivos y README, contrastarlos con código y
pruebas y continuar lo pendiente; no reiniciar ni generar planificación equivalente.
Una entrega autorizada permite avanzar por sus tareas, archivos y pruebas sin
pedir permiso para cada paso. La siguiente entrega requiere nueva autorización.
No inventar decisiones de producto o física que la hoja deje abiertas: informar
la decisión pendiente y detener únicamente el trabajo que dependa de ella.

La usuaria decide alcance y autorización. Estos archivos no inician tareas por
sí mismos. Una petición documental solo autoriza documentación; implementar la
aplicación requiere una petición explícita. No interpretar «documentos completos»
o «ready to apply» de OpenSpec como autorización ni como código terminado.

Los requisitos observables tienen una única fuente: la especificación del cambio
activo. Tras un cierre autorizado, las especificaciones consolidadas estarán en
`openspec/specs/`. La ruta antigua en docs/ es una referencia, no requisitos
alternativos. Si hay una contradicción material nueva, identificarla y no ampliar
silenciosamente el alcance ni escoger la interpretación más exigente.

## Responsable y coordinación

Un Codex principal implementa, prueba e integra el cambio. También coordina el
trabajo: no se construye un orquestador externo, servicio de agentes ni plataforma
multiagente. Hay un único escritor de código por tarea. La elección del modelo
(Astra u otro disponible) pertenece a la configuración del entorno de la usuaria;
no se codifica ni modifica en MotorSim.

Se realiza una revisión puntual al terminar, preferentemente en otra sesión o
con un subagente de solo lectura si está disponible. No requiere agentes
permanentes ni bloquea el trabajo por no disponer de subagentes. Sin revisión
independiente, hacer una pasada separada y declararla como autorrevisión, no como
auditoría independiente. El principal conserva la responsabilidad de integrar.

## Code Review Rules

Revisar únicamente el diff del cambio, su especificación y evidencia de pruebas.
Informar defectos reproducibles, pérdida de datos, requisitos incumplidos o una
comprobación necesaria ausente. Cada hallazgo debe indicar archivo/ubicación,
requisito afectado y reproducción o razonamiento concreto. No inventar evidencia.

Separar defectos de mejoras opcionales. Estas últimas no bloquean la entrega ni
se convierten en requisitos. El revisor no modifica código ni requisitos; el
principal corrige los defectos y vuelve a comprobar lo afectado. No encadenar
revisores o rondas generales indefinidas: ante un bloqueo persistente, entregar
el estado verificable y el impedimento concreto sin declarar éxito.

## Flujo y límites

- Trabajar solo sobre el cambio solicitado; no generar otro plan, otra auditoría
  general ni una etapa futura para ejecutar la tarea actual.
- Mantener tasks.md como único registro detallado de avance. Marcar tareas únicamente con
  evidencia de ejecución; no confundir preparación documental con implementación.
- Respetar la especificación del cambio autorizado. En `base-escritorio` el alcance
  era solo nombre, tipo y archivos, sin geometría. `caracteristicas-motor` incorpora
  ficha y cilindrada geométrica; no autoriza simulación física, rendimiento,
  gráficas ficticias ni arquitectura de solvers.
- Elegir pocos módulos, Python estándar y PySide6. Mantener datos y
  archivos separables de los widgets. No añadir dependencias preventivas.
- No importar código, contratos, fases o infraestructura de proyectos anteriores.
- No modificar requisitos o aceptación para ocultar un fallo o facilitar el cierre.
- Usar comandos con salida y límites de ejecución razonables. No repetir una
  operación bloqueada sin hipótesis nueva; no dejar procesos duplicados o esperas
  indefinidas. Entregar lo verificado y la limitación del entorno.
- No sincronizar specs ni archivar el cambio por el solo hecho de completar
  documentos. Archivar únicamente con trabajo comprobado y cierre autorizado.
- Al completar el cambio autorizado, detenerse. La física requiere otra definición.

## Cuidado del repositorio y entrega

Preservar cambios ajenos, comprobar el estado de Git antes de editar y no
reescribir historia ni descartar trabajo para resolver diferencias. No subir
credenciales, entornos virtuales o datos personales. No modificar configuración
global de Codex, permisos o preferencias del equipo sin autorización específica.
No codificar `E:\dino` como ruta de aplicación.

Actualizar README con instrucciones reales de instalación, ejecución y pruebas
cuando existan. Distinguir pruebas automatizadas, recorrido manual de Windows,
revisión y comprobaciones pendientes. Una prueba sin pantalla no valida Windows.

La entrega informa brevemente archivos cambiados, comprobaciones ejecutadas y
resultados, pendientes y referencia Git. No requiere otro informe obligatorio.
No declarar que funciona el simulador por haber terminado su base de escritorio.

Referencia del formato: https://developers.openai.com/codex/guides/agents-md
