# Programa MOTORSIM_2T_COMMERCIAL_CORE

> **Vista derivada, no autoridad.** El estado operativo de estas tareas vive en
> `results/2t-commercial-core-20261002/program-status.json` → `queue` (AGENTS.md §5).
> Ante divergencia prevalece la cola.

Estado reconstruido desde `401d8d7`. Las fases son una cola durable única; marcar
solo trabajo comprobado. Mantener P4–P9 y los recibos históricos intactos.

- [x] AUD-11 scientific decision recorded as CASE B; `OPEN_END_PLENUM_V2`
      equations, provenance and tests preregistered in commit `80fcf62` before
      implementation/campaign; audit remediation mode exited because no other
      AUD items remain open.
- [x] Additive boundary module and P5-C opt-in wiring implemented; V1 defaults,
      equations, Fixtures A/B and P3-R1 are unchanged. Focused tests
      pass; see `tests/test_open_end_plenum_v2.py` and
      `tests/test_kt100_open_end_plenum_v2.py`.
- [x] Replayed and instrumented all five preserved r5 failure faces; every RPM
      matches its original accepted-step count, failure angle and error exactly.
      Receipt: `results/2t-commercial-core-20261002/aud-11-kt100-r5-failure-face-instrumentation-v2.json`.
- [x] Execute exactly one preregistered five-point KT100 V2 campaign using the
      committed `OPEN_END_PLENUM_V2` config. All five points reached 390° and
      passed state/admissibility/species checks, then cycle-primary construction
      failed with `KeyError('transfer1')` because the evidence writer used the
      product label instead of P6 key `tr1`. No primary cycle was emitted; this
      is not a physical boundary failure or periodicity result. Raw R6 artifacts
      are preserved and the campaign is not rerun. Receipt:
      `results/2t-commercial-core-20261002/aud-11-kt100-v2-campaign-audit.json`.
- [x] Fix the evidence-layer transfer-name mapping and cover both transfers;
      `tests/test_kt100_open_end_plenum_v2.py` passes. This correction does not
      retroactively create missing R6 primary evidence.
- [x] Inspect R6 for offline recovery: no cycles, trajectory, step trace, or
      checkpoint is persisted, so a primary decision result cannot be rebuilt.
- [x] Preregister and commit exactly one `KT100_V2_EVIDENCE_RECOVERY_R1` run
      with the R6 config/controls and only the already-tested evidence mapping
      delta; preserve R6 and write R1 into a new output directory.
- [ ] Execute the single R1 recovery campaign and audit its primary results
      without tuning; classify whatever outcome the frozen contract produces.

- [ ] Fase 1: harness reusable y evidencia multi-ciclo. Parcial: harness y
      contrato de periodicidad implementados; KT100 r5 falla antes del ciclo 1
      por rama de admisión reservoir sin solución. Se validan self-fixtures,
      period-1/2, auditoría y restart de paso aceptado; el multi-ciclo de un
      motor no queda verificado. No declarar VERIFIED.
- [ ] Fase 2: KT100 V2, cinco puntos exploratorios y provenance. Parcial:
      capability V2 y sus pruebas focales pasan, pero la única campaña R6 no
      emitió primarios por el defecto del agregador descrito arriba. No se
      obtuvo evidencia de convergencia ni performance. Preservar r2–r6; no
      reejecutar esta campaña ni declarar fallo físico de la frontera.
- [ ] Fase 3: geometría genérica 2T: transferencias múltiples, escape complejo,
      perfiles de área, piston-port y asociaciones con conductos.
- [x] Fase 3a: API/configuración separada `GENERIC_2T_PORTS_V1`; conserva los
      proyectos históricos, calcula áreas/eventos continuos, perfiles por
      apertura y agregados por conducto, serializa geometry + derived profiles
      con binding SHA-256. 17 pruebas focales y 54 pruebas de geometría,
      admisión, cinemática, proyectos y simulación aprobadas.
- [ ] Fase 3b: integración de esta configuración en un engine case ejecutable,
      topología variable con ledgers globales, schema de proyecto y GUI. El
      adaptador opt-in `motorsim.two_stroke_ports_p5c` ahora resuelve y suma
      aperturas genéricas como áreas de entrada a las interfaces existentes de
      P5-C, sin editar P5; admite varias ventanas por cada una de las dos rutas
      transfer existentes. No descarta silenciosamente una tercera ruta: la
      rechaza. Tres pruebas nuevas verifican RHS geométrico, rechazo de ruta
      extra y datos inválidos; junto con 8 pruebas genéricas, 11 pasaron. Sigue
      parcial: la física histórica P5-C admite solo dos rutas, no hay topología
      variable/full-core, schema persistente ni GUI.
- [ ] Fase 4: métricas de barrido con definiciones matemáticas y ledgers P6.
- [x] Fase 4a: funciones puras `MOTORSIM_2T_SCAVENGING_METRICS_V1`, masas,
      reference charge y nueve ratios con valores undefined explícitos para
      denominadores cero; cinco pruebas analíticas/negativas aprobadas.
- [x] Fase 4b: extraer snapshots de cierre de transfers/escape desde evidencia
      primaria de ciclo, ligarlos a cierres exactos de geometría, exigir span
      completo 360°, ledgers P6 concordantes y agregar auditor offline. Fixtures
      geométricos/primarios y regresiones focales pasan.
- [x] Fase 4b1: adaptador de primary trajectory que exige snapshots únicos en
      ángulos de cierre resueltos, cierre terminal, ledger P6 cumulativo y
      summary concordante; no interpola. Tests de evento ausente, resumen stale
      y bool-as-number cubiertos.
- [x] Fase 4c: verificados ledgers P6 y outputs V2 durante operación periódica
      en dos fixtures internos completos, sin cambiar transporte. Fixture A
      alcanzó P1 en ciclo 16; Fixture B, con cámara 20% más larga, alcanzó P1
      en ciclo 19. Los ciclos tienen snapshots exactos de cierre, outputs
      ligados a sus trazas/ledgers y balances de especie reconstruidos. Evidencia
      comprimida preservada en `fixture-a-periodicity-extension-20261002-v1`
      y `fixture-b-long-chamber-primary-20261002-v1`; auditoría adicional de
      fuel para ciclos 13–16 en `fixture-a-fuel-output-audit-20261002.json`.
      Son fixtures sintéticos `CONDITIONAL_ON_P4`, no validación experimental ni
      cierre de Commercial Core.
- [ ] Fase 5: reed estática y/o dinámica, según alcance físico derivable.
- [x] Fase 5a: `STATIC_REED_V1` y `DYNAMIC_REED_V1` multi-petal, respuesta,
      contactos, flujo y serialization/replay individual. `motorsim.reed`
      conserva mecánica desacoplada y reutiliza `simulation.restriction`; 16
      pruebas reed más 48 regresiones P6/scavenging/ports, y 64 tests focales
      de harness/evidencia, aprobados. Se corrigió contacto a tope al final de
      un paso con redondeo de una ULP. Sin conexión productiva a P5/P6.
- [ ] Fase 5b: integración del estado reed con el timestep/etapas de P5-C/P6,
      especies, ledgers y casos de operación del engine. Bloqueada localmente:
      la reed estática ya se resuelve desde presión en cada stage del integrador
      nuevo y se ejercitó en ciclos completos A/B. Sigue bloqueada la reed
      dinámica: el contrato no especifica el acoplamiento de impactos/restitución
      con SSPRK2 ni el balance de trabajo diferencial y disipación mecánica.
      Esto no cambia P5 histórico ni autoriza post-step operator splitting.
- [ ] Fase 6: sistema de cámara de expansión sobre ducts quasi-1D existentes.
- [x] Fase 6a: ensamblado geométrico conectado y trazas de solver en
      `motorsim.expansion_chamber`, reutilizando `gas1d.mesh.segments_mesh` y
      `gas1d.solver`. Once pruebas de geometría, esquema, estados inválidos,
      flujo, presión/temperatura/Mach, características, tiempos de llegada y
      mapeo de un estado producido por el solver aprobadas. La cámara participa
      ahora en los stages SSPRK2 y ciclos A/B con especies/ledgers; evidencia
      sintética `CONDITIONAL_ON_P4`.
- [x] Fase 7: transferencia térmica configurable y ledger energético.
- [x] Fase 7a: superficies térmicas direccionables, pared prescrita o mapa
      RPM/carga acotado, correlación explícita `CONSTANT_H_V1`, esquema durable
      y ledger trapezoidal por ciclo en `motorsim.thermal`; nueve pruebas
      analíticas/negativas aprobadas. La correlación prescrita se evalúa en
      ambos stages del motor integrado y el balance térmico se registra en
      ciclos sintéticos completos. No modela capacidad térmica dinámica.
- [x] Fase 8: `COMBUSTION_MODEL_V2`, separado de P7 prescrito histórico.
- [x] Fase 8a: single/double Wiebe, ignition, efficiency/map y CA10/50/90 en
      `motorsim.combustion`, con serialization y 11 pruebas. Esta capability
      prescribe fracción de quemado, landmarks CA10/50/90 e ignition; no incluye
      química, conversión de especie ni energía liberada y no modifica P7.
- [x] Fase 9: modelo de cárter V2 y acoplamiento de admisión/transferencia.
- [x] Fase 9a: volumen de cárter V2 con cinemática/biela existente, dV/dt
      analítico y compresión geométrica, más link 0D bidireccional que reutiliza
      `simulation.restriction`; ocho pruebas analíticas/negativas. El nuevo
      integrador resuelve volúmenes cárter/cilindro y flujos de admisión/
      transferencia con especies y ledgers en ambos stages SSPRK2. Evidencia
      sintética `CONDITIONAL_ON_P4`.
- [x] Fase 10: pérdidas mecánicas y rendimiento al freno con provenance.
- [x] Fase 10a: términos FMEP explícitos por fuente, mapas RPM/carga,
      provenance y derivación analítica IMEP/BMEP, potencia y par 2T en
      `motorsim.mechanical`; cuatro pruebas analíticas/negativas. El collector
      usa el modelo cuando está explícitamente configurado; no altera la energía
      del solver ni afirma calibración medida.
- [ ] Fase 11: combustible, AFR y BSFC consistentes con P6.
- [x] Fase 11a: propiedades de combustible explícitas con provenance y cálculo
      de AFR/equivalence, inventario entregado/atrapado/quemado/no quemado,
      short-circuit explícito desde ledger P6 (sin inferirlo de delivered menos
      trapped), energía potencial, fuel flow e ISFC/BSFC de 2T;
      nueve pruebas analíticas/negativas. Parcial: adaptador consume masas
      suministradas, no se acopla a la campaña P6 ni al ledger energético.
- [x] Fase 12: geometría/actuación de powervalve.
- [x] Fase 12a: mapa RPM→posición lineal y aplicación geométrica al techo del
      escape principal móvil en `motorsim.powervalve`, reutilizando área/eventos
      de `GENERIC_2T_PORTS_V1`; siete pruebas analíticas/negativas aprobadas.
      El mapa RPM se resuelve en cada stage SSPRK2 del motor y cambia áreas y
      cierres exactos. No hay servo ni calibración medida.
- [x] Fase 13: plenum, airbox, boost bottle y uniones.
- [x] Fase 13a: schema de volúmenes/conexiones, atmosphere P6, intercambio
      conservativo 0D/1D con Riemann P3 + donor real P6 y estimación Helmholtz
      con longitud efectiva explícita; ocho pruebas. El helper de interfaz
      aplica incrementos opuestos y conserva masa, energía y especies. La
      topología reusable no está conectada como red completa al estado SSPRK2
      del motor integrado.
- [ ] Fase 14: esquema unificado de outputs por ángulo y ciclo/RPM.
- [x] Fase 14a: `MOTORSIM_ENGINEERING_OUTPUTS_V1` con unidades, source,
      dependency status, trazas/metrics opcionales, estados undefined y controles
      de no-claim; diez tests incluyendo esquema inválido. Parcial: outputs aún
      no recolectados de un ciclo full-core arbitrario ni ligados a evidence.
- [x] Fase 15: importación exploratoria generalizada sin cambiar P9.
- [x] Fase 15a: importador separado de presión/dyno con units, incertidumbre,
      provenance, raw+SHA256 y overlay exacto con métricas descriptivas;
      15 pruebas focales. Siempre EXPLORATORY_COMPARISON, nunca P9 elegible.
      Importador + parser/persistence heredados + calificación P9: 56 PASS;
      OpenSpec estricto PASS. Hash congelado P9 reconfirmado:
      `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`.
      En un intento de incluir la ventana GUI heredada de `external_data`, Qt
      terminó con access violation en `ExternalWindowTests.test_import_confirm_`
      `roundtrip_unknown_conditions_and_previous_preserved`; parser/persistencia
      se validaron por separado. P9 no se editó ni ejecutó.
- [x] Fase 16a: registrar `HONDA_CR250R_2007_REFERENCE_CASE_PARTIAL_V1` desde
      la ficha oficial Honda, con parámetros publicados como DOCUMENTED y los
      que faltan como null/UNKNOWN; prueba offline de provenance aprobada.
      Queda marcado `NOT_SIMULATION_READY`: la fuente no define biela, cárter,
      timing/geometría de lumbreras, conductos ni estados de frontera. No se
      inventaron especificaciones ni se ejecutó otro motor.
- [ ] Gate final: integración arbitraria 2T, regresiones, auditoría y dos casos;
      declarar readiness solo con todos los requisitos del Commercial Core.

- [ ] Integración end-to-end autorizada (continuación 2026-10-02):
      conservar P4–P9 y convertir los módulos existentes en un único motor.
      La etiqueta `CONDITIONAL_ON_P4` sigue obligatoria para la evidencia nueva.
- [x] 17a. Integrador gas/especies con stage SSPRK2 común y transferencias N:
      iniciado en `motorsim.integrated_2t`. Reutiliza EOS/HLLC/P3 y donor P6;
      fixture de malla estática con tres transfers prueba conservación local,
      backflow/donor, geometría de celda en CFL, vaciado bruto de cámara 0D,
      flujo con entrada y salida simultáneas, calor prescrito, restart atómico
      y JSON replay. Cerrado como fundación integrada; la suite pertinente pasó
      y dos fixtures internos completan ciclos. Esto no declara readiness ni
      elimina la condición P4.
- [x] 17b. Reed estática/intake/crankcase integrado por etapas, retroflujo, especie y
      ledger global; checkpoint/replay de estado mecánico reed. Parcial: el
      modelo estático existente limita el área de admisión por presión en cada
      stage común y el flujo conserva donor/ledger P6. `CrankcaseGeometry` V2
      resuelve volúmenes opuestos de cárter/cilindro y trabajo p·dV en ambos
      stages; el fixture A completa dos ciclos con reed estática y cárter móvil.
      El subtramo estático está cerrado condicionalmente. La reed dinámica y su
      estado de restart siguen en `BLOCKED_LOCAL` separado: faltan una relación
      de volumen desplazado y la identidad de los volúmenes de control a cada
      lado para cerrar presión-trabajo y ledger de energía. Avanzar la reed por
      separado y alimentar después el flujo sería splitting no validado;
      `DYNAMIC_REED_V1` continúa disponible como componente autónomo.
- [x] 17c. Topología generic ports N con piston intake, transfers y exhaust
      expansion-chamber en los mismos stages; scavenging ledger con cierres
      geométricos y flujos con signo. Parcial: el mesh real de
      `ExpansionChamber` se avanzó como la ruta exhaust en ambos SSPRK2 stages
      con flujo y especies conservativos. El binding de áreas genéricas y el
      mapa de powervalve participan ahora de una trayectoria angular aceptada
      sintética 0–90° a 3000 rpm; el chequeo detectó y corrigió selección
      invertida del donante P6 en caras internas con flujo inverso. La
      regresión comprueba la composición del donante por stage y la ruta
      mantiene admisibilidad. Fixtures A y B completaron horizontes periódicos
      con snapshots exactos de cierre y outputs V2 ligados a P6 por ciclo.
      Cerrado para las topologías internas ensayadas; evidencia sintética y
      `CONDITIONAL_ON_P4`. La deuda de reservoir V2 continúa local a KT100.
- [x] 17d. Integración de P7 prescrito, paredes térmicas, combustible/especies y
      trabajo mecánico integrados con ledger único sin doble conteo. Parcial:
      el P7 prescrito existente ya puede configurarse por ángulo de ciclo;
      captura las cuatro especies reales del cilindro, aplica conversión y
      calor en ambos stages SSPRK2, y agrega fuentes a ledgers globales de
      especie/energía. El checkpoint V2 guarda evento activo/histórico y la
      identidad del ángulo P7. El fixture A completa dos ciclos y prueba
      balances globales de masa/energía/cuatro especies y fuentes no vacuas de
      P7, pared térmica, fresh/fuel delivery, short-circuit y trabajo indicado.
      El brake work se calcula en la prueba con FMEP sintético explícito. Se
      añadió al ledger V3 el fuel short-circuited usando el donor real de
      escape. Ahora los outputs V2 reconstruyen flujos y residual de fuel desde
      etapas aceptadas y se validan en ambos fixtures. Aún no se define fuel
      atrapado desde inventario terminal ni se justifica equivalencia de `Q_F`
      y LHV; equivalence ratio sigue UNDEFINED sin AFR estequiométrico. Estos
      valores dependientes de propiedades/evento quedan como subtramo
      `BLOCKED_LOCAL` independiente; no se rellenan por inferencia. V4 añade
      masas de pseudo-especies en el cierre exacto del último puerto del
      cilindro y su cociente fresh-air/fuel claramente distinto de AFR; sin
      instante exacto permanece UNDEFINED. AFR estequiométrica y relación entre
      `Q_F` y LHV siguen bloqueadas por falta de propiedades explícitas.
- [x] 17e. Periodicidad P1/P2, evidencia primaria, collector engineering,
      checkpoint/restart/replay continuo y fixtures integrados completos para
      las capacidades soportadas. El collector V4 incorpora las masas en el
      último cierre exacto de puertos y no altera V1–V3.
      Progreso: el fixture A restaura en 360° y reproduce exactamente el
      snapshot JSON a 720° con el mismo grid angular absoluto. Fixture A alcanza
      P1 en ciclo 16 y Fixture B en ciclo 19; periodicidad, collector y replay
      verificados en dos fixtures sintéticos, sin aceptación global.
- [x] 18. Segundo fixture integrado independiente: el resultado actual es el
      Fixture C piston-port sin reed de AUD-09, que difiere materialmente de A;
      no se reutiliza ni renombra el antiguo Fixture B de cámara 20% más larga,
      supersedido por auditoría. La regresión amplia P4–P8 se ejecuta como tarea
      independiente de continuación y no equivale al gate Commercial Core.

## Cola autónoma

- `DONE_CONDITIONAL` — Fundación común acotada: estado conservativo gas/especies N-route,
      SSPRK2, ledgers, CFL de ducto/cámara y restart geométricamente consistente;
      revisión read-only puntual completada; casos sintéticos siguen condicionados a P4.
- `DONE` — La reed estática, intake y cárter geométrico participan en los stages
      comunes. `BLOCKED_LOCAL` separado para dinámica multi-petal: la geometría
      actual no identifica el volumen barrido ni los volúmenes de control que
      reciben su presión-trabajo; no usar un split no verificado.
- `DONE_CONDITIONAL` — `ExpansionChamber`, generic ports/powervalve, cierres
      exactos y ledgers por ciclo verificados en fixtures A/B. La frontera
      reservoir V2 es una deuda separada de KT100 y no se cambió.
- `DONE` — P7, paredes, fuel-species y mecánica participan de etapas o outputs
      para las entradas explícitas actuales. Quedan `BLOCKED_LOCAL` los outputs
      que requieren un evento total de fuel atrapado, AFR estequiométrica y LHV
      documentados; los datos ausentes permanecen `UNDEFINED`.
- `DONE_CONDITIONAL` — Evidencia primaria, periodicidad P1, collector,
      checkpoint/replay y Fixture A completo; sintético, no aceptación global.
- `DONE_CONDITIONAL` — Fixture C piston-port sin reed constituye el segundo caso
      integrado materialmente distinto; preserva su identidad AUD-09 y no
      convierte los antiguos resultados Fixture B supersedidos en evidencia.
- `DONE` — Regresión del 2026-10-05: 25 módulos de pruebas P4–P8,
      300 pasaron, cuatro warnings NumPy 1.25 preexistentes, 177,49 s; sin
      campañas ni resultados físicos nuevos.
- `DONE` — V4 reporta fresh_air/fuel pseudo-especies en el último cierre exacto
      transfer/exhaust y su cociente de especies no-AFR; V3 permanece intacto.
      El collector reconstruye el evento desde geometría y lo enlaza al stage
      aceptado; rechaza snapshots adulterados. La prueba integrada focal pasó.
      AFR estequiométrica y LHV sin propiedad explícita siguen `UNDEFINED`.
- `BLOCKED_LOCAL` — KT100 V2: la única recuperación R1 ya se consumió. Su punto
      de 5000 RPM se reconstruyó offline con 23 ciclos y auditoría PASS, pero
      terminó en `NUMERICAL_FAILURE` antes de periodicidad; los otros cuatro
      RPM no empezaron. No declarar verificación ni reintentar bajo R1.

Comprobación agrupada del avance autónomo: el 2026-10-02 se ejecutaron 204
pruebas focales de provenance, puertos/P5-C, scavenging, reed, cámara, thermal,
combustion, cárter, mecánica, fuel, powervalve, network, engineering outputs,
importador, harness, P5-B/P5-C y P6; todas pasaron. Esta suite no incluye KT100
ni campañas físicas. Los regresos P4–P8 se acreditan separadamente; los
fixtures unitarios no equivalen a verificación completa de engine.

Continuación de cierre integrada: el 2026-10-02 se ejecutó el fixture A con
reed estática, cárter/cilindro slider-crank, tres transferencias, intake,
expansion chamber multi-sección, mezcla atmosférica sintética etiquetada,
P7 a 300° y pared prescrita. Completó los ciclos 0→360° y 360→720° respetando
`max_cfl=0.4`; los ledgers globales de masa/energía/especies cierran, y hay
fresh delivery, fuel delivery/short-circuit, short-circuit fresco, P7 heat,
wall heat y cylinder work positivos. Un checkpoint en 360° reanudó el segundo
ciclo con igualdad exacta del snapshot JSON a 720° usando el mismo grid
angular absoluto. El brake work se calculó aparte sobre el trabajo indicado
medio de ambos ciclos y un término FMEP sintético explícito; no es salida
integrada persistida. `tests/test_integrated_2t.py`: 21/21; grupo
integrado/P5-C/P6/P7/reed/puertos: 73/73; OpenSpec estricto, `py_compile` y
`git diff --check`: PASS. Esto no prueba periodicidad P1/P2, cierres exactos de
scavenging, dos ejecuciones independientes completas, output de ingeniería,
segunda configuración, propiedades de combustible/LHV justificadas, reed
dinámica ni Commercial Core READY. La frontera fue `nonreflecting` existente;
no se implementó reservoir V2 ni se reintentó KT100.

## Deuda de integración no global

- El P5-C histórico tiene dos conductos transfer fijos y el callback geométrico
  no expone un estado SSPRK2 de etapa a un componente externo. Se dejó intacto.
  `two_stroke_ports_p5c` puede enlazar aperturas a esas dos rutas, pero tercera
  ruta, reed dinámica y volúmenes externos en las mismas etapas requieren una
  extensión integrada nueva y separada.
- El P6 expone ledgers de fresh delivered y short-circuit agregados, pero el
  primary evidence congelado no contiene un acumulador durable de delivered
  fresh_air/fuel por especie. Fuel accounting acepta ledgers de cuatro
  especies explícitos; no se derivan AFR/BSFC desde el contador escalar.
- La fase 1/2 queda localmente bloqueada por la capability de frontera ya
  registrada en `docs/gasdynamic/generalized_reservoir_boundary_v2_debt.md`.
  Las funciones independientes continúan; no repetir ni ajustar KT100.
- El segundo caso Honda solo aporta procedencia documental parcial y no puede
  alimentar una corrida sin reemplazar UNKNOWN por supuestos.

Para cada fase registrar contrato, código, pruebas unitarias/analíticas/negativas,
integración, restart/replay, conservación, regresiones, auditoría, revisión puntual,
OpenSpec estricto y commit. Las campañas con gates numéricos deben preregistrar
thresholds y horizonte antes de ejecutarse.

### Continuación de evidencia primaria y salida del ciclo — 2026-10-02

Se construyó `MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V1` recalculando desde los
stages SSPRK2 aceptados: estado inicial/terminal, composición, flujos externos,
fuente P7, calor de pared, trabajo de energía del cilindro/cárter, inventarios,
residuos independientes y CFL. Los deltas de ledgers checkpoint se usan como
cross-check, no como autoridad de los términos de ciclo. El registro queda
vinculado a identidad de configuración, EOS y límites angulares exactos.

Se corrigieron dos errores de contabilidad detectados al enlazar esa evidencia:
el acumulador P7 de masa supuestamente limitada restaba con signo incorrecto y
contaba como pérdida incluso una fuente aplicada íntegramente; el observable de
trabajo indicado confundía el término de energía del gas `-p·dV/dt` con el
trabajo producido `∮p·dV`. El ledger energético del integrador no cambió; la
conversión a trabajo indicado se hace únicamente al construir observables.
También se equilibró la presión inicial sintética de cilindro y cárter con la
atmósfera a 101325 Pa, usando `rhoE=101325/(gamma-1)` para `gamma=1.35`.

El collector integrado produce `MOTORSIM_ENGINEERING_OUTPUTS_V2` a partir de
una trayectoria completa: presión/temperatura/masa/volumen de cámaras, cuatro
especies, calor P7, calor de pared, trabajo/potencia/torque/IMEP indicados,
caudal de combustible del ledger P6, cuatro especies por celda y flujo firmado
por cara de ducto, áreas/flujos de puertos y balance de energía. Las métricas de freno
solo se definen si se entrega un `MechanicalLossModel` explícito; los cálculos
de scavenging, AFR/equivalence ratio, ISFC y BSFC siguen `UNDEFINED` por ausencia
de cierres geométricos exactos o de una relación LHV aprobada.

Diagnóstico sin cambios de solver, malla, CFL ni thresholds: ciclos 1–6 del
fixture A completan y son admisibles, pero ciclo 1 tiene trabajo indicado
negativo; los pares 1→2 son `INVALID` y 2→3 a 5→6 son `FAIL` en el contrato
`REFERENCE_PERIODIC_CONVERGENCE_V1`. No hay P1/P2 ni periodicidad acreditada.
La salida V2 reúne canales por celda/cara de ducto, Mach y áreas/flujos de
puertos; los cierres geométricos exactos y sus snapshots P6 siguen pendientes.
Fixture A permanece bloqueado y Fixture B no se inicia aún.

Pruebas actuales: 21 focales integradas y 12 de salida de ingeniería (33 en
conjunto) aprobadas; el grupo integrador/P5-C/P6/P7/reed/puertos/output pasó
85/85; OpenSpec estricto aprobado. Regresión P4–P8 amplia y revisión
independiente del delta actual siguen pendientes. Esto es evidencia de trabajo
integrado parcial, no cierre del Commercial Core.

### Integración de cierres geométricos y alineación de trazas — 2026-10-02

La evidencia primaria integrada se versionó como
`MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V2`. Cuando hay un `TwoStrokePortSet`
vinculado y RPM constante, el constructor deriva los cierres agregados exactos
de transferencia y escape, resolviendo antes el techo powervalve a ese RPM.
Solo registra el estado terminal SSPRK2 en un ángulo de cierre si existe una
única fila aceptada en ese ángulo. Los ciclos de RPM variable con powervalve,
geometría sin cierre o evidencia angular faltante conservan el estado
`UNAVAILABLE`; no se interpola.

El fixture A usa ahora para su escape auxiliar un perfil sintético con intervalos
realmente cerrados. El perfil anterior solo tocaba área cero en puntos aislados
y, de acuerdo con `duct_closing_angles`, no definía un cierre del conducto. La
corrección cambia la geometría sintética y obliga a repetir el diagnóstico de
seis ciclos; los resultados numéricos anteriores quedan como evidencia de la
revisión previa, no como resultado del fixture actualizado.

El collector de ingeniería toma cada muestra inicial de paso desde su estado y
RHS de etapa 1 alineados; añade el endpoint del ciclo mediante una evaluación
RHS de solo lectura sobre el estado terminal aceptado. La tasa P7 de ese punto
es el request prescrito previo a cualquier limitador de un paso futuro y no
participa de integrales ni balances. Con reference-charge mass positiva,
scavenging se deriva de las dos instantáneas de cuatro especies y los ledgers
P6 de ese mismo ciclo. Sin cierres exactos, el valor permanece null/UNDEFINED.

Evidencia de esta continuación: prueba focal del ciclo integrado aprobada;
`tests/test_integrated_2t.py` + `tests/test_engineering_outputs.py`: 33/33;
OpenSpec estricto, `py_compile` y `git diff --check`: PASS. El grupo de regresión
integrado de 85 pruebas pasó nuevamente tras este cambio. Se repitieron seis
ciclos completos del fixture revisado, todos con cierres exactos. El trabajo
indicado fue `[-111.5764, 17.2841, 52.2598, 57.1227, 53.2165, 50.4537] J`;
primer ciclo negativo, 1→2 INVALID, pares restantes FAIL y sin P1/P2. Los ratios
de scavenging con referencia sintética explícita fueron
`[0.57136, 0.49767, 0.47893, 0.50271, 0.53278, 0.55344]`. Artefacto primario y
outputs: `results/2t-commercial-core-20261002/fixture-a-integrated-cycles-20261002-v2.json.gz`,
SHA-256 `c037c83f81796b7fb9a93bdae6b6ffff070c44e030977ef69d6329dcf1279dc2`.
La suite amplia seleccionada actual P4–P8 pasó 300 pruebas en `.venv` Python
3.11, con cuatro warnings NumPy preexistentes. Falta revisión independiente de
este delta. No declarar periodicidad ni Commercial Core READY.


### Revisión independiente read-only de cierres V2 — 2026-10-02

La revisión independiente puntual del delta actual no encontró defectos materiales
en la derivación de cierres, la alineación estado/flujo por stage, la reconstrucción
de integrales, la compatibilidad de salida V1/V2 ni el artefacto LFS. Confirmó
que el powervalve se resuelve a RPM constante y que el snapshot se captura solo
en un endpoint SSPRK2 aceptado, único y exacto; el punto terminal del collector
se evalúa en solo lectura. La revisión comprobó el puntero LFS y su tamaño/hash,
y que P4–P8 y la infraestructura de orquestación no están en el delta. Esta es
una revisión puntual de implementación/evidencia, no una aprobación del motor
completo. Fixture A sigue sin convergencia P1/P2; no cambia su bloqueo.


### Replay integrado de seis ciclos — 2026-10-02

Se ejecutaron dos recorridos independientes de Fixture A hasta 2160°/ciclo 6,
a 3000 RPM y CFL máximo 0.4. Un recorrido fue continuo; el otro guardó
checkpoint al cerrar el ciclo 3, creó una instancia nueva y restauró antes de
continuar. Los snapshots completos finales fueron estructuralmente iguales,
incluyendo estados, especies, ledgers, reloj y traza aceptada; los seis
registros primarios y outputs de ingeniería V2 también fueron iguales. Los seis
outputs validaron con el modelo de pérdidas sintético explícito. Se aceptaron
11.176 pasos. Por ciclo, CFL máximo fue ≤0.4; residuos globales de masa y especies
se mantuvieron alrededor de 1e-18 kg y los de energía alrededor de 1e-12 J.
El ciclo 1 conserva trabajo indicado negativo y la secuencia no converge P1/P2;
esto verifica replay/conservación, no Commercial Core readiness. Evidencia del
recorrido actual en `results/2t-commercial-core-20261002/fixture-a-restart-replay-audit-20261002.json`;
la trayectoria primaria completa existente sigue en el artefacto V2 LFS.


### P1 integrado y contabilidad de combustible por ciclo — 2026-10-02

Fixture A completó un horizonte de 16 ciclos al mismo punto sintético (3000 RPM,
CFL 0.4), sin cambiar solver, geometría, valores iniciales ni thresholds. Los
ciclos 1–12 reprodujeron exactamente sus artefactos previos; 12→13 falló y
13→14, 14→15 y 15→16 pasaron `REFERENCE_PERIODIC_CONVERGENCE_V1`, por lo que el
detector clasificó `PERIOD_1` en el ciclo 16. El trabajo del primer ciclo
continúa negativo y la transición inicial sigue visible. Fixture B no se inicia
en esta actualización. Trayectorias 7–12 y 13–16 conservadas bajo `results/`.

El primary collector ahora integra por separado fresh_air bruto que entra por
la frontera de admisión, fuel que entra, fuel cortocircuitado, conversión de fuel
por el ledger P7, inventario global terminal y residuo global de fuel. El V2 de
ingeniería deriva AFR bruto de los flujos aceptados, ISFC/BSFC solo con potencia
positiva (no requieren LHV), y mantiene equivalence ratio `UNDEFINED` sin AFR
estequiométrico explícito. El inventario terminal es el pseudo-especie fuel
remanente en todo el sistema, no una estimación de fuel atrapado. Los registros
V2 previos se leen usando su flujo firmado guardado de la cara de admisión; la
ausencia de esa evidencia produce error, nunca una mezcla asumida.

La corrida física no cambió para esta conexión de outputs. Suite focal integrada
y de salida: 33 pruebas aprobadas; compatibility fallback de V2 probado. Sigue
pendiente definir una propiedad estequiométrica defendible si se requiere
equivalence ratio numérico. P1 del fixture A no implica validación P4 ni
readiness comercial.


### Segundo fixture integrado independiente — 2026-10-02

Se probó el límite de admisión piston-port sin reed como candidato B. La corrida
no aceptó el paso a 107.651626° después de 25 reducciones; se conserva como
intento fallido, no como regresión del motor general. Sin cambiar solver, se
continuó con una variación alternativa permitida: Fixture B mantiene el modelo
reed estático y cambia todas las longitudes axiales de la cámara de expansión
por un factor explícito 1.2 respecto de A.

Fixture B completó ciclos hasta 6840° (ciclo 19), 33.434 pasos aceptados, CFL
0.4, y alcanzó `PERIOD_1` tras tres PASS consecutivos 16→17, 17→18, 18→19 bajo
`REFERENCE_PERIODIC_CONVERGENCE_V1`; el primer par sigue INVALID. Cada output V2
se construyó y validó con el modelo de pérdidas sintético explícito y referencia
de scavenging sintética. La trayectoria completa por stage y outputs están en
`results/2t-commercial-core-20261002/fixture-b-long-chamber-primary-20261002-v1.json.gz`.
La configuración difiere de A en identidad y longitudes del escape; no afirma
validación real. Equivalence ratio continúa UNDEFINED sin estequiometría. El
Commercial Core no está READY.


Verificación final de esta tanda (2026-10-02): `tests/test_integrated_2t.py`,
`test_engineering_outputs.py`, P5-C/P6/P7, reed y puertos: **85 passed**. La
suite seleccionada P4–P8 de la orden: **300 passed**, cuatro warnings NumPy
preexistentes. OpenSpec estricto aprobado. La clasificación P1 de A y B se
obtuvo con el detector contractual sin cambiar thresholds. P4/P5-C histórico,
P6, P7, P8 y P9 no fueron modificados.

### Addendum 2026-10-02 — generic-port contract and periodic fixtures

Historical implementation note: `GENERIC_2T_PORTS_V1` temporarily accepted a
finite nonnegative discharge coefficient and treated `Cd = 0` as a closed-flow
path. AUD-12 later restored the frozen positive-finite contract; zero is now
rejected. Focused validation: 40 tests across generic ports, the P5-C adapter,
powervalve, and integrated engine; OpenSpec strict validation passed. Fixture A
reached `PERIOD_1` at cycle 16 and Fixture B at cycle 19; their V2 outputs and
P6-linked scavenging quantities were validated per cycle. These internal
synthetic results remain `CONDITIONAL_ON_P4`; independent review of the latest
fuel/output and Fixture B delta remains pending, and full-core readiness is not
claimed.

### Combustible species at exact exhaust closure — 2026-10-02

Engineering output V2 now reports `cylinder_fuel_species_at_exhaust_close_kg`
from the accepted exact cylinder snapshot, or keeps it `UNDEFINED` if that
snapshot is unavailable. The field is explicitly not total trapped fuel and is
not reconstructed from global terminal inventory. The 33-test integrated/output
suite and OpenSpec strict validation passed. Stoichiometric AFR and a Q_F-to-LHV
binding remain unresolved; no fuel chemistry or value was inferred.

### Integración de plenum finito de admisión — 2026-10-05

- [x] Enlazar un plenum finito opcional con la cara izquierda del ducto de
  admisión usando el helper conservativo P3 en ambos stages SSPRK2.
- [x] Incluir masa, energía y cuatro especies del plenum en estado, CFL,
  inventario global, checkpoint/replay e identidad de configuración.
- [x] Exponer el estado del volumen de red en la evidencia primaria/output V2
  con canales dinámicos direccionados por ID.
- [x] Verificar flujo en ambas direcciones, donor de especie, ledgers globales,
  límite de vaciado, replay tras serialización JSON y actualización volumétrica
  con el promedio de ambas etapas SSPRK2 para masa, energía y las cuatro especies.

Resultado de la regresión afectada: 99 pruebas integradas/red/P5-C/P6/P7/reed/
puertos aprobadas; OpenSpec estricto, compilación Python, `git diff --check`,
Git LFS fsck y hash P9 comprobados. La revisión independiente del delta no
encontró defectos concretos; no es aceptación del motor completo. Ninguna
campaña KT100 se ejecutó. El resultado sintético continúa sujeto a las etiquetas
de dependencia vigentes y no cambia el estado global parcial.

### Volúmenes de red en endpoints externos múltiples — 2026-10-05

- [x] Normalizar el plenum heredado y permitir nodos finitos inmutables en los
  endpoints intake-left y exhaust-right, con orientación y unicidad validadas.
- [x] Integrar los flujos opuestos de cada nodo en ambas etapas SSPRK2, cuatro
  especies, CFL, estado/restart, identidad, inventario global y ciclo primario.
- [x] Reconstruir siete señales V2 por volumen y rechazar identidades de nodo,
  geometrías o definiciones malformadas.
- [x] Verificar un ciclo sintético completo con dos volúmenes simultáneos,
  intercambios no nulos y cierres globales de masa, energía y especies.

Resultado: 100 pruebas integradas/red/P5-C/P6/P7/reed/puertos aprobadas y la
prueba focal de replay multi-volumen pasó tras añadir comparación de muestras
inicial, intermedia y terminal con el estado primario. OpenSpec estricto pasó.
La revisión independiente no encontró defectos concretos. No se agregó una
nueva ley de interfaz, frontera atmosférica o propagación acústica;
`effective_length_m` sigue siendo metadata en el enlace ideal P3. La
clasificación global continúa parcial y condicional.

### Configuración serializable del motor integrado — 2026-10-05

- [x] Incorporar `MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V1` para reconstruir sin
  callback externo las configuraciones resueltas por slider-crank y puertos
  genéricos existentes.
- [x] Preservar estados primitivos y especies iniciales, mallas, EOS, fronteras,
  reed, puertos/powervalve, volúmenes de red, térmica, RPM y evento P7.
- [x] Rechazar callbacks geométricos arbitrarios, configuración malformada,
  deriva de parámetros vivos y arreglos geométricos de malla mutables.
- [x] Confirmar JSON canónico, identidad y snapshot inicial exactos, además de
  restore/checkpoint y replay exacto del siguiente paso.

Cinco pruebas focales y 105 regresiones integradas/red/P5-C/P6/P7/reed/puertos
aprobaron. OpenSpec estricto, `compileall` y `git diff --check` aprobaron. La
revisión independiente puntual encontró inicialmente una vía de mutación in
place de mallas; el contrato `DuctPath2T` se endureció para aceptar solamente
`Mesh` con arreglos tupla y la revisión confirmó el cierre. La fábrica V1 no
serializa callbacks arbitrarios ni acredita el motor completo; clasificación
global permanece `MOTORSIM_2T_COMMERCIAL_CORE_PARTIAL`.

### Geometría explícita ignora callback sombreado — 2026-10-05

- [x] Cuando slider-crank y el binding de puertos resuelven todos los campos
  geométricos, no invocar el callback heredado del constructor: su salida y
  efectos laterales no forman parte de la configuración reconstruible.
- [x] Probar que el callback puede fallar y aun así la geometría explícita se
  resuelve igual en el motor original y el reconstruido.
- [x] Repetir la regresión integrada/red/P5-C/P6/P7/reed/puertos completa.
- [x] Obtener revisión independiente de solo lectura del delta.

Resultado: callback con excepción no invocado en la ruta explícita; geometría
igual en original/reconstruido. Revisión independiente sin hallazgos concretos.
La regresión amplia afectada pasó **105 pruebas**; OpenSpec estricto pasa. La
configuración V1 sigue limitada a slider-crank y puertos genéricos explícitos;
no se atribuye aceptación al motor completo.


### Ingesta de auditoría externa `audit_8cdf66e` — 2026-10-05

- [x] Preservar byte por byte `docs/gasdynamic/audit_8cdf66e.md` y registrar
  su alcance independiente exacto `ab92aee..8cdf66e`.
- [x] Incorporar `AUD-01`…`AUD-18` con prioridad, dependencias y hallazgos en
  `results/2t-commercial-core-20261002/program-status.json`; activar
  `AUDIT_REMEDIATION_MODE`.
- [x] Aplicar la errata editorial: A1, A2 y A3 son defectos y bloquean toda
  evidencia de ciclo preexistente. Los artefactos A/B se preservan marcados
  `HISTORICAL_SUPERSEDED_BY_POSTHOC_AUDIT`; no se reutilizan como aceptación.
- [x] Reconciliar contra HEAD `3d10f79`, sin revertir cambios posteriores. La
  revisión puntual actual está registrada en
  `results/2t-commercial-core-20261002/audits/audit-triage-3d10f79.json`; no es
  aceptación end-to-end ni revisión de ciclos.
- [x] Cerrar AUD-01…AUD-07 antes de nuevas capabilities o campañas; evidencias
  de implementación, productores y estados están registradas en la cola durable.
- [x] AUD-08: preregistro aislado en commit previo y regeneración fija de Fixture
  A; el resultado no converge dentro de los 20 ciclos registrados.

AUD-11 forensic protocol (2026-10-05): see
`docs/gasdynamic/aud11_reservoir_forensic.md`. The bounded monotone V1 branch,
orientation mirror, and full-state Riemann discriminator were checked; 7
focused tests pass. That historical forensic analysis recorded outcome C;
the subsequent explicit human/scientific decision is CASE B and authorizes the
separate `OPEN_END_PLENUM_V2` contract. The capability and analytical tests are
implemented, and the one preregistered KT100 campaign was executed. Its five
points reached the terminal angle, but the evidence writer failed before any
cycle primary was emitted. See the R6 audit receipt; the mapping bug is fixed,
the campaign is not repeated, and no convergence or physical KT100 claim is
made. The audit review itself remains independent only for its exact range;
later implementation review is punctual/self-review, not whole-core acceptance.

### AUD-13 — bounded mesh diagnostic (2026-10-05)

- [x] Preserve the existing five-section synthetic expansion-chamber geometry
  and compare 7, 33, 65, and 130 finite volumes (target dx 0.13, 0.02, 0.01,
  and 0.005 m).
- [x] Compare a straight 50 mm synthetic transfer duct at 2, 4, 8, 16, and 32
  cells; use the existing first-order gas1d solver, identical smooth pressure
  pulse, closed wall ends, CFL 0.4, and a fixed 0.35 L/a observation horizon.
- [x] Record mesh, sensor trace, steps, rejected steps, CFL and normalized
  conservation ledger in `results/2t-commercial-core-20261002/aud-13-mesh-study-20261005.json`.

Reproduction: `python scripts/aud13_mesh_study.py
results/2t-commercial-core-20261002/aud-13-mesh-study-20261005.json`.
`python -m pytest tests/test_aud13_mesh_study.py -q` — 1 passed. All nine runs
completed and conserved to floating-point scale. The coarse 7-cell chamber
sensor increment was 15.07 Pa, versus 76.88 Pa at 65 cells and 76.88 Pa at
130 cells; the 2-cell transfer result was likewise strongly mesh-sensitive.
These values are diagnostic, not a convergence gate. No adequacy threshold was
specified, so this closes the missing-study task but does not claim that any
production mesh resolves all waves or is physically sufficient.

No se ejecutaron campañas ni se tocaron resultados KT100.

### AUD-14 — métrica de entrega/short-circuit y combustible (2026-10-05)

- [x] Definir entrega y cortocircuito como integrales brutas de cruces de
  especies frescas (fresh_air + fuel), sin deduplicación de recirculaciones ni
  afirmación de masa neta única. El cortocircuito solo cuenta especie fresca
  saliente cuando admisión por transfer y escape están abiertos; flujo inverso
  por escape queda fuera.
- [x] Publicar esas semánticas con nombres explícitos en
  `MOTORSIM_ENGINEERING_OUTPUTS_V3`; conservar validadores y builders V1/V2
  intactos.
- [x] Separar el cociente bruto de especies de entrada
  (`gross_intake_air_fuel_ratio`) de AFR atrapado/quemado, que queda UNDEFINED.
- [x] Calcular ISFC/BSFC desde el sumidero de combustible pseudo-especie P7,
  no desde la entrega por admisión. Con cero consumo P7 o potencia no positiva,
  el resultado queda UNDEFINED, nunca 0 g/kWh.
- [x] Añadir prueba de que retroflujo de escape y áreas cerradas no cuentan como
  cortocircuito; distinguir explícitamente entrega fresh_air de carga fresca
  total fresh_air + fuel.

V3 registra que el sumidero P7 es conversión prescrita de contabilidad, no
combustión medida ni validación experimental. `python -m pytest
tests/test_engineering_outputs.py tests/test_integrated_2t.py -q` — 58 passed.
La salida V2 queda disponible con la semántica anterior para los consumidores
existentes; los nuevos resultados integrados usan V3.

### AUD-15 — fixture sintético de timing (en progreso)

- [x] Extender la validación del productor para admitir Fixture D marcado como
  `AUDIT_REMEDIATION_FIXTURE`; no se ha iniciado una campaña.
- [x] Crear `fixture-d-engine-config-v2.json`, idéntico a A salvo identidad
  sintética y P7 de 350° a 390°. Una evaluación geométrica sin integración
  confirma área de escape cero en todo el intervalo, muestreado cada 0.5°.
- [x] Commitear configuración/productor en `01172a2d7b2f7f97db9a7a46e12cf328962aef52`
  y el preregistro separado en `57dfa97032037a96ab3869cf46b7180f35bb77a0`;
  ambos preceden a toda integración.
- [x] Ejecutar únicamente los dos ciclos preregistrados, con restart tras el
  ciclo 1; ambos ciclos completos y admisibles, replay exacto.
- [x] Confirmar que los 160 pasos contiguos del evento P7 350–390° tienen
  320 evaluaciones SSPRK2 con área de escape exactamente cero.
- [x] Preservar métricas y hashes en
  `results/2t-commercial-core-20261002/aud-15-fixture-d-20261005-v1/decision.json`;
  la prueba offline de evidencia y las cinco pruebas del productor pasan (6).
- [x] Mantener la conclusión limitada al diagnóstico sintético de timing: sin
  criterio de convergencia, calibración ni validación experimental.

Validación previa de configuración: `tests/test_integrated_cycle_evidence_producer.py`
— 5 passed; `--validate-only` funciona fuera del repositorio. No se ha ejecutado
antes de la campaña. La campaña se ejecutó solo después del preregistro.

### AUD-16 — cross-check de etapas, restart y geometría (2026-10-05)

- [x] En `make_integrated_cycle_primary`, recalcular ambos RHS SSPRK2 por paso
  desde estados, ángulos y RPM guardados mediante `_assemble`; contrastar rates,
  flujos externos, caras, interfaces, geometría, trabajo, thermal y fuente P7
  contra el trace. El evento P7 se reconstruye desde su checkpoint y los estados
  de captura, incluyendo el limitador de disponibilidad.
- [x] Rechazar campos faltantes del ledger en vez de compararlos consigo
  mismos; todo valor integrado debe contrastar contra la diferencia de ledger
  entre checkpoints.
- [x] Endurecer `restore` para validar el esquema y finitud del trace, continuidad
  temporal/angular y de estados, RPM/dt, geometría/volúmenes por etapa y estado
  terminal; fallos no mutan el engine.
- [x] Contrastar las tasas de volumen de un callback sintético con una derivada
  central angular independiente multiplicada por la velocidad angular.
- [x] Pruebas adversariales: rate alterado, ledger incompleto y geometría de
  trace corrupta son rechazados; recorrido de ciclo positivo se conserva.

Validación: `python -m pytest tests/test_integrated_2t.py -q` — **48 passed**.

### AUD-17 — periodicity detector V2 para trabajo con signo (2026-10-05)

- [x] Conservar intactos `compare_cycles`/`PeriodicDetector` V1 y añadir
  `compare_cycles_v2`/`PeriodicDetectorV2` bajo un contrato de detector propio.
- [x] V2 admite trabajo indicado negativo con
  `abs(a-b)/max(1 J, abs(a), abs(b)) <= 0.005`; el resto de observables y gates
  reutiliza las métricas V1. El registro de ciclo sigue en su schema V1.
- [x] V2 serializa/restaura su identidad, reproduce toda la historia y conserva
  precedencia period-1 y streaks A/B independientes; rechaza snapshots V1.
- [x] Cubrir comparación negativa, cruce de signo, bool inválido, convergencia
  period-1/period-2, restore y separación V1/V2.

Validación focal: `python -m pytest tests/test_reference_harness.py -q` —
**13 passed**. OpenSpec estricto queda por ejecutar tras los cambios AUD-16/17.

### AUD-18 — pruebas sin escritura y hashes portables (2026-10-05)

- [x] Hacer que la prueba del generador use un root de repositorio temporal y
  otro directorio de trabajo; ejecutar dos veces, comprobar bytes deterministas
  y verificar que `examples/projects/` del checkout no cambia.
- [x] Preservar los hashes crudos históricos de la campaña de frontera baja y
  añadir `source_sha256_lf`; la prueba compara texto LF normalizado para que
  LF y CRLF identifiquen el mismo código.
- [x] Añadir prueba directa que demuestra igualdad de hash para fuentes LF y
  CRLF.

Validación focal: `python -m pytest tests/test_example_projects.py
tests/test_low_rpm_diagnostics.py -q` — **11 passed**; `examples/projects/`
permanece sin cambios.


### Correcciones prioritarias AUD-01 / AUD-02 — 2026-10-05

- [x] AUD-01: sumar la tracción `p_duct * (A_mesh - A_open)` a la cara
  de ducto en admisión, ambas caras de transfer y escape. La parte abierta
  conserva el flujo Riemann; la parte bloqueada aporta solo momento, sin
  masa, energía ni especie.
- [x] AUD-01: verificar gas uniforme en reposo con apertura 0 %, 50 % y 100 %;
  las celdas conservan RHS de momento nulo y la tracción integrada es `p*A`.
- [x] AUD-02: reemplazar la presión de cámara errónea de 289500 Pa por
  101325 Pa y verificar p/T de ambos estados iniciales (101325 Pa, 300 K).
- [x] AUD-02: reconciliar el test sintético de dos ciclos que, tras corregir
  el estado inicial, observa `p7_availability_limited_kg = 1.0249018819006299e-07`
  frente a su aserción histórica exacta de cero. Se sustituyó por verificación
  del ledger del limitador (incluida su cota de escala), derivada del estado
  inicial ya corregido. No se usa el resultado como evidencia de ciclo.

Pruebas focales: 4 PASS. El módulo `tests/test_integrated_2t.py` terminó con
40 PASS tras actualizar la aserción de P7 descrita arriba; no se declara
PASS de ciclo. A/B permanecen supersedidos hasta AUD-08.


### Separación de composición externa AUD-03 — 2026-10-05

- [x] Separar el donante de admisión (`atmosphere_species`) del ambiente de
  salida (`outlet_species`), cuyo valor por defecto es fresh-air puro.
- [x] En flujo inverso por escape, verificar que el intercambio trae fresh-air
  y cero fuel aunque el reservoir de admisión contenga combustible.
- [x] Evolucionar la configuración reconstruible a
  `MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V2`; conservar lectura V1 con la
  composición anterior aplicada a ambos extremos para preservar su replay.
- [x] Incluir ambas composiciones en guard, identidad y JSON canónico.

Pruebas focales de AUD-03 y configuración: 3 PASS; incluye roundtrip V2,
lectura compatible V1 y backflow de escape sin introducir combustible.


### Cierre focal AUD-04 — 2026-10-05

- [x] Normalizar solo las fracciones derivadas por la suma validada de especies;
  conservar sin mutación las masas extensivas admitidas por tolerancia de
  redondeo.
- [x] Registrar en helpers de fixture el ángulo, paso intentado y razón exacta
  antes de reducir el paso; la aserción del harness inspecciona esos registros.
- [x] Prueba de roundoff confirma que una fracción derivada no excede 1 y que
  los valores extensivos originales permanecen intactos.

El módulo afectado terminó con **40 PASS** en 51,90 s. No se generaron ni
persistieron artefactos A/B nuevos.


### Productor reproducible AUD-05 — 2026-10-05

- [x] Versionar configuraciones JSON V2 de Fixture A y la variante histórica B
  bajo `results/2t-commercial-core-20261002/fixtures/`. Ambas declaran
  `HISTORICAL_SUPERSEDED_BY_POSTHOC_AUDIT`; no son evidencia actual.
- [x] Añadir `scripts/produce_integrated_cycle_evidence.py`: reconstruye el
  motor solo desde configuración versionada, guarda ciclos gzip deterministas,
  registra rechazos y ejecuta auditoría de restart exacto.
- [x] Exigir preregistro cuyo archivo esté contenido en el commit declarado y
  cuyo SHA de configuración, horizonte, ciclo de restart y contrato de
  periodicidad coincidan antes de integrar.
- [x] Verificar `--validate-only` fuera del repositorio para ambos fixtures y
  comprobar que el modo de integración se rehúsa sin preregistro.

Comprobaciones: `pytest tests/test_integrated_cycle_evidence_producer.py`
(**2 PASS**); no se ejecutó ninguna integración ni se generaron ciclos.


### Reconciliación de revisión AUD-06 — 2026-10-05

- [x] Conservar `audit_8cdf66e.md` como revisión independiente únicamente
  del delta `ab92aee..8cdf66e`.
- [x] Registrar el recibo `audit-triage-3d10f79.json` como lectura independiente
  acotada al HEAD de entrada y a los hallazgos enumerados; no equivale a
  aceptación del motor ni revisa el código posterior.
- [x] Downgradear a `SELF_REVIEW` los claims históricos del Commercial Core
  sin recibo durable identificable; preservar su texto y alcance histórico.
- [x] Mantener como `SELF_REVIEW` la inspección local de este delta.

P4–P8 conserva sus artefactos de revisión independientes separados; no se
modificaron ni se atribuyó su alcance al Commercial Core.


### Normalización durable AUD-07 — 2026-10-05

- [x] Mantener P4=`P4_PASS` y el resultado P4–P8 de 300 pruebas como
  conteo histórico de la auditoría externa; no atribuirlo a una corrida actual.
- [x] Corregir el alcance del harness: el productor/configuración ya existen;
  el siguiente bloqueo de ciclos es el preregistro independiente AUD-08.
- [x] Marcar las campañas A/B y los claims de Fixture B como históricos
  supersedidos, preservando sus JSON originales.
- [x] Normalizar estados, referencias a commits, bloqueos de dependencias y
  próximos pasos; el registro actual contiene 29 tareas con enums válidos.
- [x] Separar la evidencia independiente P4–P8 de la revisión Comercial Core.

Captura de estado reconciliada contra `a10d2dca698369f0eb95c310b78d48226ac63037`;
los próximos commits de este modo deben actualizar esa referencia.


### Preregistro AUD-08 — 2026-10-05

- [x] Fijar Fixture A y su hash de configuración V2. Fixture B queda excluida
  por no ser una topología suficientemente distinta.
- [x] Fijar 20 ciclos completos, sin terminación temprana, y detector V1/hash
  existentes sin cambios.
- [x] Fijar replay exacto desde el snapshot de ciclo 3 a ciclo 4.
- [x] Commitear el preregistro aislado antes de integrar:
  `cdafa6e1b37978bb825bb04b0260a17544802e06`.
- [x] Verificar el blob y hash canónico del preregistro y ejecutar exclusivamente
  la campaña registrada mediante el productor versionado.
- [x] Completar 20/20 ciclos admisibles; replay exacto desde ciclo 3 a 4.
- [x] Evaluar offline con `REFERENCE_PERIODIC_CONVERGENCE_V1`, sin cambiar el
  contrato ni sus thresholds. Resultado: ninguna comparación pasa y no hay
  convergencia dentro del horizonte fijo.

La campaña se conserva como evidencia sintética `CONDITIONAL_ON_P4`; no es
aceptación del Commercial Core. Artefactos en
`results/2t-commercial-core-20261002/aud-08-fixture-a-20261005-v1/`.


### Verificación del preregistro AUD-08 en Windows — 2026-10-05

- [x] El gate comparó el JSON parseado del árbol y del blob del commit
  preregistrado `cdafa6e1b37978bb825bb04b0260a17544802e06`.
- [x] El primer intento detectó solo CRLF vs LF; el productor ahora verifica
  igualdad estructural y calcula SHA canónico independiente de BOM/finales.
- [x] Los tests cubren LF frente a CRLF+BOM.
- [x] Commitear el refuerzo del productor antes de los ciclos y comprobarlo
  contra el blob del preregistro.


### Reconciliación de prioridad 2 — AUD-10 y AUD-12 — 2026-10-05

- [x] AUD-10: el colector de outputs obtiene los ductos de admisión,
  transferencias y escape por rol; IDs como `inlet` y `pipe` no causan `KeyError`.
- [x] AUD-10: documentar el límite del schema integrado V2: un camino de
  admisión, al menos tres transferencias y un escape. Otra cardinalidad exige
  una versión de configuración distinta; la geometría genérica sigue separada.
- [x] AUD-12: restaurar en `GENERIC_2T_PORTS_V1` el requisito de Cd positivo;
  Cd=0 vuelve a ser rechazado y el test negativo quedó restablecido.

Validación focal: `pytest tests/test_integrated_2t.py tests/test_two_stroke_ports.py` — **50 PASS**; OpenSpec estricto y `git diff --check` PASS.


### AUD-09 — fixture piston-port sin reed — 2026-10-05

- [x] Crear Fixture C sintético desde la configuración V2 versionada; conserva
  la admisión piston-port y elimina la reed. Hash canónico: `9095a5e6…f65a27`.
- [x] El productor permite C y conserva un `failure.json` con causa, ángulo,
  estado parcial, ledger y rechazos si no completa el horizonte. Cuatro pruebas
  del productor y `--validate-only` desde otra carpeta pasan.
- [x] Revisar el antecedente disponible (solo resume fallo a 107.651626°, sin
  traza cruda) y preregistrar Fixture C/horizonte en commit separado
  `5a093bbf4df5f3d8d2fd53b807967f302037ee00`.
- [x] Ejecutar 20 ciclos; replay exacto 3→4; `PERIOD_1` al ciclo 20 con tres
  comparaciones lag-1 PASS finales.
- [x] Conservar los 14.283 rechazos CFL en `manifest.json`. Cerca del ángulo
  histórico, la propuesta de 0,5° excede CFL y avanza al reducirse a 0,25°;
  no reaparece rechazo por masa de especies. La traza histórica cruda no existe,
  así que no se atribuye causalidad exacta; el fallo no se reproduce tras AUD-01/04.

Evidencia sintética `CONDITIONAL_ON_P4`, no aceptación del Commercial Core.
Artefactos: `results/2t-commercial-core-20261002/aud-09-fixture-c-20261005-v1/`.


Evaluador de evidencia: la campaña C se verificó offline con su preregistro y
blob del productor; cinco pruebas focales de productor/evaluador pasan.

### Continuidad autónoma — auditoría cycle 24 y biblioteca de combustible — 2026-10-06

- [x] Confirmar que la R1 persistida no tiene estado de fallo suficiente para
  inspeccionar el paso inválido y usar únicamente el checkpoint aceptado cycle20
  del mismo punto de 5000 RPM; reproducir cycle21–23 exactamente antes de
  detener el diagnóstico en el fallo de cycle24. No iniciar otra campaña ni
  escribir en el directorio R1.
- [x] Guardar en
  `results/2t-commercial-core-20261002/kt100_cycle24_forensics.json` el estado
  aceptado, ambos estados RHS SSPRK2, el candidato, ductos/cámaras/especies,
  fronteras, áreas, termodinámica, CFL/dt, ledger, excepción y hashes de las
  fuentes primarias.
- [x] Clasificar la causa inmediata como `rhoY` del escalar legado una ULP por
  encima de `rho` en una celda de admisión casi pura. El estado P6 de cuatro
  especies permanece válido; no hay evidencia de fallo de densidad ni de
  especie negativa. No cambian las ecuaciones termodinámicas de EOS, solver, flujo, geometría, frontera ni CFL; sí se añade el adaptador de vista primitiva P5 acotado.
- [x] Añadir un adaptador P5 explícito con tolerancia máxima de 8 ULP solo para
  la conversión conservativa→primitiva del escalar `rhoY`; el `IdealGas.primitive`
  general permanece estricto. Un estado 32 ULP fuera del límite se rechaza.
- [x] Reproducir el caso capturado como fixture P5 de una celda y conservar un
  test para el exceso de 1 ULP y otro para el exceso no físico fuera de cota.
- [ ] Repetir una prueba de trayectoria/fixed-horizon KT100: **no autorizada**;
  R1 consumida. La corrección de admissibility no constituye evidencia de que
  KT100 complete cycle24.
- [x] Implementar FUEL_LIBRARY_V1 con perfiles ANCAP incompletos, provenance,
  snapshots de definición completa con hash, fórmula elemental versionada,
  operaciones de biblioteca e import/export JSON; `tests/test_fuel_library.py`
  y regresión `tests/test_fuel.py` pasan. Sin integración de combustión, sin
  valores químicos ANCAP inferidos y sin cambiar pseudo-AFR V4.
- [x] Resolver la geometría y el acoplamiento SSPRK2 de reed dinámica usando un
  fixture sintético preregistrado; mantener separado el caso real KT100. Diseño
  y preregistro congelados antes de las pruebas acopladas.

- [x] Registrar el fallo de KT100 R1 cycle24 desde el checkpoint cycle20,
  reproducir cycles21–23 exactamente y recuperar el paso inválido del cycle24.
  El defecto general es un `rhoY` legado que supera `rho` por una ULP. Se añadió
  la conversión P5 acotada a 8 ULP; el validador `IdealGas.primitive` general
  sigue estricto y el caso a 32 ULP continúa rechazado. 79 pruebas focales
  aprobadas. La trayectoria cycle24 no se reintentó; R1 está consumida, no hay
  evidencia de periodicidad KT100 y no se autorizó R2.

### Reed dinámica — integración sintética verificada, sin validación real

- [x] Commit de la preregistración antes de cualquier prueba numérica acoplada:
  forma lineal de lámina articulada, relación entre ancho, largo, área de
  cortina y área de volumen barrido, balance de presión-trabajo y disipación;
  provenance `SYNTHETIC_ASSUMPTION` en
  `docs/gasdynamic/dynamic_reed_coupling_v1_preregistration.md`; congelado en
  `004b1841579497fe0e2273257be0104ccaa4abd2` antes de los tests acoplados.
- [x] Implementar geometría versionada y un acoplamiento stage-coherent SSPRK2
  de dos volúmenes 0D, cuatro especies, reed y ledger de disipación, con rechazo
  atómico fuera de dominio. `tests/test_reed_coupling.py` y
  `tests/test_reed.py`: 26 aprobados; OpenSpec estricto aprobado.
- [x] Verificar fixtures sintéticos breves, donor forward/reverse, conservación,
  restart exacto y determinismo. No se repitieron Fixture A/C ni KT100.
- [x] Enlazar el estado al endpoint 1D terminal de admisión y al cárter de
  `IntegratedEngine2T`: volumen de ducto `Vmesh + (W L / 2) x`, volumen de
  cárter `Vbase - (W L / 2) x`, ecuaciones de volumen móvil y términos `p dV`
  dentro de ambos stages SSPRK2; actualizar conservativas extensivas de la celda
  móvil antes de recuperar densidades; derivar masa de las cuatro especies P6;
  flujo de área limitado por la geometría y área disponible; donor de cuatro
  especies derivado del signo del flujo.
- [x] Versionar configuración V3/estado V8 solo para binding dinámico; vincular
  geometría y estado al hash/configuración, checkpoint/restart y prueba de
  round-trip. El CFL usa el volumen efectivo de la celda terminal.
- [x] Incluir energía cinética/elástica y ledger explícito de disipación en el
  inventario global; el ciclo primario y collector V4 reconstruyen volúmenes,
  balance energético y señales `reed:*` desde estados aceptados.
- [x] Comprobar donor forward/reverse, balances, round-trip, restart y una vuelta
  sintética completa reconstruida por el collector V4. Evidencia automatizada
  nueva: `tests/test_integrated_2t.py`; no es una campaña de un motor real.
- [x] Regresión final de este delta: `tests/test_integrated_2t.py` **55 passed**;
  `tests/test_reed_coupling.py tests/test_reed.py` **28 passed**; regresiones
  P5-C/P6 `tests/test_p5c_integrated.py tests/test_p5b_integrated_coupling.py
  tests/test_p6_species.py` **62 passed**; OpenSpec estricto y `py_compile`
  aprobados. Revisión adversarial fue autorrevisión secuencial; no se declara
  revisión independiente ni aceptación del Commercial Core.
- [ ] Geometría real, selección de parámetros, contacto con stops y validación
  experimental siguen fuera de este contrato; los stages que cruzan el dominio
  se rechazan sin clipping.
