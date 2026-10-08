# Modo autónomo de ingeniería — versión V1 (histórica, no operativa)

Copia literal e íntegra de `docs/gasdynamic/autonomous_engineering_mode.md` en el
commit `fb2544d` (2026-10-06), antes de la simplificación V2. Incluye las secciones
"Estado vivo" §15–19, que a esa fecha ya estaban desactualizadas respecto de la
cola (p. ej. "la cola no tiene tareas READY", reed y fuel bloqueados). Las
decisiones científicas de §17 siguen siendo provenance válida; las reglas son
reemplazadas por `docs/gasdynamic/autonomous_engineering_mode.md` V2.

---

# MotorSim — Modo autónomo de ingeniería (`MOTORSIM_AUTONOMOUS_ENGINEERING_TEAM`)

Reglas detalladas de la ORDEN VIGENTE de `AGENTS.md`. Ante conflicto, prevalece
`AGENTS.md`; el estado científico vigente se lee allí y en
`results/2t-commercial-core-20261002/program-status.json`.

## 1. Objetivos

1. `GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED` (sección 9).
2. Después: `MOTORSIM_2T_COMMERCIAL_CORE_READY` (sección 10).

El problema principal no es la falta de features aisladas sino la integración
end-to-end: convertir las capabilities probadas en un único camino
físico/numérico consistente.

## 2. Flujo de trabajo

`problema → orchestrator → investigación → síntesis → implementación →
verificación → revisión adversarial → regresión → integración → siguiente tarea`

Roles (subagentes si existen; si no, pasadas secuenciales declaradas como
autorrevisión):

- **Orchestrator / tech lead**: roadmap, dependencias, cola, integración, merge.
- **Numerical / physics**: Euler cuasi-1D, Riemann, CFL, características,
  fronteras, conservación, SSPRK2, termodinámica.
- **Engine architecture**: interfaces de componentes, estado integrado, grafo
  de etapas, puertos, ductos, válvulas, cárter, cilindro, admisión/escape; sin
  duplicación.
- **Implementation**: workstreams independientes en paralelo; un solo escritor
  por zona del núcleo a la vez.
- **Verification**: unitarios, fixtures analíticos, integración, negativos,
  conservación, restart/replay, evidencia malformada, regresiones.
- **Adversarial reviewer**: intentar romper cada capability. Buscar: expected
  circular, estado stale, etapa SSPRK equivocada, términos de ledger faltantes,
  bool-como-número, NaN/inf, unidades, orientación, especie donante, summary
  como autoridad, fallback oculto, factores de ciclo 2T, estado faltante en
  restart, desajuste trayectoria/terminal.
- **Contract / regression guardian**: P4–P9, evidencia histórica, runtime
  bindings, umbrales preregistrados. Ninguna capability reinterpreta un
  contrato histórico.
- **Evidence / documentation**: OpenSpec, provenance, receipts, program status.

## 3. Arranque de cada sesión

1. `git status`, `git rev-parse HEAD`, `git rev-parse origin/main`,
   `git log --oneline --decorate -40`, `git diff --check`. Usar el HEAD real.
2. Leer el campo `queue` de
   `results/2t-commercial-core-20261002/program-status.json` y la sección 15
   de este documento.
3. Verificar que el SHA-256 de
   `openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md`
   siga siendo
   `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`.
4. Inspeccionar archivos untracked. `motorsim/integrated_2t.py` y
   `tests/test_integrated_2t.py` son trabajo en curso: revisarlos y retomarlos
   o documentar por qué no; no borrarlos. Los directorios
   `results/kt100-hybrid-model-fixture-v2-harness-20261002*` se preservan sin
   stage.

## 4. Cola y presupuesto

- La cola vive en `program-status.json` → `queue`. Cada item tiene: `id`,
  `description`, `dependencies`, `state` (`READY`, `IN_PROGRESS`,
  `BLOCKED_LOCAL`, `REVIEW`, `DONE`), `blocker`, `commits`, `evidence`,
  `next_action`. Se actualiza en cada commit significativo.
- Al quedar una tarea `BLOCKED_LOCAL`, tomar otra `READY`. Reevaluar bloqueos
  cuando una nueva capability pueda resolverlos.
- Presupuesto (estimar antes con corrida corta/profiling): diagnóstico
  ≤10 min; fixture/integración ≤30 min por configuración; campaña científica
  larga ≤60 min continuos, hasta 120 min sólo si es gate-critical, con
  checkpoint/restart usable, progreso persistido y sin alternativa más barata.
  Proyección mayor: `PERFORMANCE_BLOCKED_LOCAL`; perfilar y optimizar sólo con
  transformaciones que preserven la semántica, verificando equivalencia. No
  reducir precisión, CFL ni umbrales para cumplir el presupuesto.
- Preregistración: diseñar, documentar, tests estructurales y commit de
  preregistración; recién después la campaña decisoria, en otro commit.
- Si la sesión se interrumpe, `AGENTS.md`, este documento y
  `program-status.json` commiteados deben bastar para continuar.

## 5. Prioridad de workstreams (el orchestrator reordena por dependencias)

- **A — Fundación de integración**: grafo SSPRK2 común; estado integrado único;
  ledgers globales; esquema de evidencia primaria; checkpoint/restart/replay.
- **B — Intercambio de gases**: admisión/reed/cárter; arquitectura de N
  transfers; escape + cámara de expansión; frontera externa generalizada.
- **C — Termoquímica**: cuatro especies; combustible/AFR; combustión V2;
  térmico; cárter V2.
- **D — Performance**: métricas de barrido; trabajo indicado/IMEP; pérdidas
  mecánicas/FMEP; BMEP/potencia al freno; caudal de combustible; ISFC/BSFC.
- **E — Componentes de producto**: puertos genéricos; reed V1 completo;
  powervalve; plenum/airbox/boost bottle; collector de outputs; importador
  experimental.
- **F — Generalidad**: Fixture A; Fixture B; regresiones P4–P8 completas;
  KT100 solo tras resolver la capability bloqueante; segundo caso documentado.

Diferido hasta cerrar el núcleo (solo interfaces): rotary valve,
multicilindro, turbo, supercharger, opposed piston, uniflow, vehículo, GUI.

## 6. Requisitos técnicos

### Grafo SSPRK2 común
Un único grafo de actualización. Por etapa: geometría, áreas de puertos,
reconstrucción, estados de frontera, flujos Riemann, admisión, cárter,
transfers, cilindro, escape, especies, fuente de combustión, fuente térmica,
ledgers, estado aceptado. Investigar lecturas stale, actualizaciones
duplicadas, orden y splitting inconsistente. Sin integraciones ad hoc fuera del
grafo.

### Estado integrado único
Serializable y suficiente para continuar exactamente:
- Físico: cilindro, cárter, ductos de admisión/transfer/escape, válvulas, reed,
  powervalve, reservoir/plenum, estado conservativo, especies, combustión,
  térmico.
- Acumuladores: masa, energía, especies, entrega fresca, cortocircuito,
  combustible entregado, quemado/no quemado, calor liberado, calor a pared,
  trabajo, pérdidas mecánicas.
- Numérico: tiempo, ángulo, ciclo, etapa SSPRK, dt, CFL, estado del detector de
  periodicidad.

### Ledgers globales
Independientes de los summaries locales; recalculables por ciclo:
- Masa: inicial + entrada externa − salida externa + fuentes contractuales = final.
- Energía: inicial + flujos de entalpía + combustión − calor a pared − trabajo
  + términos contractuales = final.
- Especies: `fresh_air`, `fuel`, `residual`, `burned`.

«Cada componente conserva» no prueba que conserve el motor completo.

### Evidencia primaria
Reconstruible offline: trayectoria → etapa/estado aceptado → terminal de ciclo
→ conservación → periodicidad → trabajo → checkpoint → restart → replay →
digest → summary. Prohibido: PASS almacenado como autoridad, prueba summary
contra summary, residuo sin ledger primario, digest sin preimagen, terminal sin
binding a la trayectoria.

### Reed / cárter
Flujo completo admisión → reed → cárter con dinámica o comportamiento estático,
área, fuerza de presión, especie donante, flujo directo y reverso, ledgers de
masa, energía y especies. No aceptar el reed solo por tests aislados.

### N transfers
Capability nueva para N rutas (al menos primary, secondary y boost) con
geometría, timing, área, Cd, ducto, donante, especies y conservación propios.
No limitar el núcleo a los dos transfers históricos de P5-C.

### Escape
Puerto, header, diffuser, belly, baffle, stinger y frontera externa
participando del motor completo; powervalve y transferencia de calor cuando
corresponda.

### Combustible / P6
Cadena cerrada: entregado → especie fuel → atrapado → combustión → quemado →
contabilidad de no quemado. AFR, phi y caudal se derivan de esa misma
evidencia; no un modelo de combustible separado de P6.

### Combustión
P7 histórico intacto. Capability nueva reutilizable: Wiebe simple/doble,
timing, duración, CA10/50/90, eficiencia, mapas RPM/carga. Un modelo
parametrizado no es predictivo.

### Térmico
Culata, pared de cilindro, pistón, cárter, paredes de transfer y escape. Todo
calor aparece en el ledger de energía, sin doble conteo.

### Performance mecánica
Presión → p-dV → trabajo indicado → IMEP → par/potencia indicados → pérdidas →
FMEP → BMEP → par/potencia al freno; con combustible, ISFC/BSFC. Tests
obligatorios de los factores de ciclo 2T.

### Collector de outputs único
- Por ángulo: presiones de cilindro/cárter/ductos, temperatura, especies,
  liberación de calor, calor a pared, áreas de puertos, caudal másico, Mach.
- Por ciclo/RPM: trabajo, potencia, par, IMEP/FMEP/BMEP, delivery ratio,
  trapping, scavenging y charging efficiency, entrega fresca, cortocircuito,
  AFR, caudal de combustible, ISFC/BSFC, presión pico y ángulo del pico.
- Termo: P-V, lazo de bombeo, balance de energía.

## 7. Reservoir boundary — decisión y estado operativo

AUD-11 fue resuelto por decisión humana/científica como
`CASE B — CAPABILITY LIMITATION`, no como `SCIENTIFIC_DECISION_REQUIRED`.
`LEGACY_CHARACTERISTIC_V1` se conserva para reproducción histórica; su nombre
`nonreflecting` solo se documenta como `EXTERNAL_STATE_RIEMANN / FARFIELD`, sin
reinterpretar evidencia. `OPEN_END_PLENUM_V2` implementa el modelo sintético
preregistrado de plenum abierto; sus ecuaciones y tests no modifican V1,
Fixtures A/B ni P3-R1. La interfaz futura `RESTRICTED_NOZZLE_V1` no tiene
valores implementados, y no se añade `MASS_FLOW_INLET`.

La única campaña preregistrada de KT100 V2 se ejecutó una vez. Los cinco puntos
alcanzaron 390° y pasaron los gates de estado/admisibilidad/especies, pero el
constructor de evidencia falló con `KeyError('transfer1')` antes de emitir
primarios. El mapeo de nombres está corregido y probado; no se repite R6 bajo la
autorización de una campaña. No hay conclusión de periodicidad ni calificación
física del resultado KT100. Ver el recibo
`results/2t-commercial-core-20261002/aud-11-kt100-v2-campaign-audit.json`.

Registro del análisis forense previo a la decisión humana (histórico):
el protocolo AUD-11 quedó documentado en
`docs/gasdynamic/aud11_reservoir_forensic.md`. V1 usa el invariante saliente de
Euler y resuelve la entrada subsónica isentrópica desde el reservoir en reposo.
Para la rama evaluada, `f(w)=w+2a(w)/(gamma-1)` es estrictamente creciente en
`[-a_sonic,0]`, con extremos `J_choke` y `J_rest`; por eso `J+ > J_rest` no
posee raíz en el dominio contractual. La reproducción a 100 kPa, 301 K y
`u=-0.001 m/s` no demuestra un bug del solver. Las pasadas forensics/domain/
skeptic/discriminator se hicieron secuencialmente por el mismo autor y son
autorrevisión, no revisión independiente. Ese análisis preliminar clasificó C:
alternativas estándar con consecuencias materiales y sin criterio disponible.
La decisión humana posterior seleccionó CASE B, autorizó `OPEN_END_PLENUM_V2`,
y quedó registrada arriba; por tanto esta conclusión preliminar no es el estado
operativo vigente.

Como trabajo independiente prioritario, la integración ahora admite un único
plenum finito en la entrada del ducto de admisión: el mismo helper P3 se evalúa
en ambas etapas, los incrementos internos son opuestos, las especies usan el
donante real, el nodo participa del inventario/CFL/restart y la salida V2 puede
trazar presión, temperatura, masa y composición. Ese trabajo sigue siendo
distinto de la frontera atmosférica `OPEN_END_PLENUM_V2`.

Alcance acústico del enlace: el volumen intercambia mediante la interfaz P3
ideal y sin masa; `NetworkConnection.effective_length_m` permanece como dato de
geometría/provenance y no se aplica como inertancia ni propagación acústica en
este camino. La documentación primaria de NASA describe tanto fronteras por
estado de Riemann como fronteras subsónicas basadas en estado de estancamiento
([Cart3D](https://www.nas.nasa.gov/publications/software/docs/cart3d/pages/howto/samples_power/README.html),
[Wind-US](https://www.grc.nasa.gov/www/winddocs/user/bc.html)); los tratamientos
de caudal estrangulado dependen además del estado total y del régimen
([NASA mass-flow choking](https://www.grc.nasa.gov/www/k-12/BGP/mflchk.html)).
Estas referencias documentan alternativas existentes, pero no seleccionan la
semántica de una futura frontera MotorSim ni cambian el bloqueo científico V2.

La integración se generalizó luego a volúmenes finitos en endpoints externos
distintos: intake-left y exhaust-right. El grafo reusa P3 en ambas etapas, y el
estado V7 incorpora ambos volúmenes en configuración, CFL, conservación,
checkpoint/replay, primary cycle y output V2. Una revisión adversarial puntual
no encontró defectos de orientación, balance, restart ni muestras de salida.
V7 no conserva compatibilidad de restore con V6, y no admite conexiones
volumen-a-volumen ni más de un volumen en la misma cara.

## 8. Protocolo ante bloqueos no triviales

No devolver el bloqueo automáticamente al humano. Investigaciones paralelas:
- **Forensics**: reproducir y extraer el estado exacto del fallo.
- **Domain expert**: reconstruir ecuaciones y algoritmo.
- **Skeptic**: buscar un bug ordinario antes de aceptar física nueva.
- **Contract guardian**: impacto sobre contratos cerrados.

Luego: hipótesis → evidencia → contradicciones → experimentos → síntesis.

Para conocimiento externo, priorizar textbooks, papers, métodos numéricos
documentados y literatura de solvers; registrar rationale y referencias. Si no
hay acceso a red, usar la documentación del repo y la teoría estándar, y
registrar `EXTERNAL_RESEARCH_UNAVAILABLE` indicando qué conclusión se obtuvo
sin verificación externa. No inventar citas. No introducir una formulación porque
«parece funcionar».

## 9. `GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED`

Al menos dos fixtures distintos end-to-end con: estado integrado, SSPRK2,
admisión, cárter, N transfers, cilindro, escape/cámara, frontera, cuatro
especies, barrido, combustible, combustión, térmico, ledgers globales,
convergencia periódica (P1/P2/no convergencia clasificados correctamente),
CFL, admisibilidad, performance indicada y al freno, checkpoint, restart,
replay, evidencia primaria, auditoría offline y outputs de ingeniería.

- **Fixture A**: motor sintético con reed, cárter, ≥3 transfers, cámara de
  expansión, cuatro especies, combustible, combustión, térmico y pérdidas
  mecánicas; múltiples ciclos completos.
- **Fixture B**: significativamente distinto (por ejemplo admisión por puerto
  de pistón, otro layout de transfers, otro escape). Sin hardcodes del núcleo
  para A.

## 10. `MOTORSIM_2T_COMMERCIAL_CORE_READY`

Además de la sección 9: config/schema reutilizable, sin hardcodes de fixture,
puertos genéricos integrados, componentes de admisión/escape reutilizables,
outputs estables, protección de regresiones, documentación/provenance y al
menos dos fixtures integrados independientes. No requiere P9 experimental,
GUI, multicilindro ni turbo.

## 11. KT100 y referencias reales

- KT100 no es el fixture principal de desarrollo. Preservar
  `KT100_REFERENCE_CASE_V1` y su provenance (DOCUMENTED,
  DERIVED_FROM_DOCUMENTED, SYNTHETIC_ASSUMPTION, UNKNOWN). Una sola campaña
  nueva, solo con el motor integrado funcionando y la capability de frontera
  resuelta. Sin ajustar parámetros; su éxito no es necesario para la sección 9.
- Honda CR250R u otro motor permanece `DOCUMENTAL_REFERENCE` hasta tener
  información suficiente. No inventar parámetros reales.

## 12. Regresiones y revisión

- Tras cambios productivos sustanciales, correr las regresiones apropiadas.
  Antes de un cierre global, reejecutar la suite amplia P4–P8; no depender de
  resultados históricos.
- Si una modificación cambia un runtime binding científico histórico,
  identificar el impacto de inmediato. No reinterpretar evidencia antigua.
- Revisión adversarial tras cada workstream grande; independiente (read-only)
  cuando exista. El implementador no autorratifica cambios científicos
  significativos.

## 13. Escalamiento al humano

Solo si se cumple todo: ≥2 alternativas científicas legítimas; cambian
materialmente física o resultados; contratos, teoría, evidencia y tests no
resuelven; elegir constituye una nueva política científica. La consulta incluye
opción A, opción B, consecuencias, evidencia y recomendación técnica. Mientras
se espera, continuar todo lo independiente.

No escalar: APIs, nombres, refactors, schemas, organización de tests,
serialización, performance, bugs, diagnósticos numéricos, Git, documentación,
fallos de implementación recuperables.

## 14. Reporte

Sin reportes por feature ni por subagente. Entregar solo cuando: (A) se
alcance la sección 10, o la sección 9 con el resto acotado; (B) exista una
decisión científica humana genuina; o (C) se agoten las tareas independientes
con un hard stop global real.

El informe final incluye: HEAD inicial y final; arquitectura; workstreams;
decisiones científicas; bloqueos resueltos y pendientes; SSPRK2 común; estado
integrado; ledgers; reservoir boundary; admisión/reed; cárter; transfers;
escape/cámara; especies; barrido; combustible; combustión; térmico; pérdidas
mecánicas; performance indicada/al freno; convergencia periódica; checkpoint;
restart; replay; evidencia/auditor; outputs; Fixture A; Fixture B; KT100;
segunda referencia; regresiones P4–P8; estado y hash P9; OpenSpec; Git LFS;
tests; commits; brechas frente a un simulador 2T comercial; clasificación
final de readiness.

Checks de cierre global: suite amplia P4–P8 reejecutada, OpenSpec strict,
`git diff --check`, `git lfs fsck` y hash P9.

---

# Estado vivo

Las secciones siguientes las mantiene el equipo autónomo. Las secciones 1–14
son reglas: no reescribirlas para facilitar trabajo; un cambio de regla se
registra como decisión en la sección 17.

## 15. Objetivo actual

`MOTORSIM_AUTONOMOUS_ENGINEERING_TEAM`: la revisión independiente
`audit_8cdf66e.md` cubre exactamente `ab92aee..8cdf66e`; sus 18 hallazgos fueron
ingeridos y reconciliados con commits posteriores, sin revertirlos. Las
prioridades 1 `AUD-01`…`AUD-07` quedaron cerradas
con cambios trazables. `AUD-08` ejecutó Fixture A desde su preregistro aislado:
20/20 ciclos admisibles, replay exacto ciclo 3→4 y ninguna convergencia de
periodicidad dentro del horizonte. La evaluación está guardada con la evidencia;
no acredita aceptación del Commercial Core. `AUD-09` completó Fixture C piston-port
sin reed: 20/20 ciclos, replay exacto y `PERIOD_1` en el ciclo 20. La traza
histórica cruda no existe, por lo que no se atribuye causa exacta; la ejecución
actual no reprodujo el fallo.
`AUD-11` quedó como CASE B y `OPEN_END_PLENUM_V2` fue preregistrado antes de
implementarse. El preregistro de una sola campaña se consumió; su defecto de
escritura de primarios está corregido, pero no se repite la campaña ni se
reinterpreta como resultado físico. Los ciclos A/B históricos permanecen
supersedidos. La fábrica de configuración V2 conserva lectura V1 por
compatibilidad y solo cubre slider-crank/puertos explícitos.

## 16. Arquitectura vigente

`IntegratedEngine2T` avanza cámara, ductos, especies, reed estática, fuentes
térmicas/P7 y volúmenes finitos opcionales en los endpoints intake-left y
exhaust-right en las mismas dos etapas SSPRK2. Los intercambios de red usan el
helper Riemann P3 existente y la composición real del donante; inventario
global, CFL, checkpoint y output reconstruible incluyen cada nodo. Los
enlaces son ideales y sin masa: su longitud efectiva se serializa, pero no
representa inertancia ni propagación acústica. El checkpoint actual es V7;
V6 no es compatible para restore. `MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V2` (con lectura compatible V1)
reconstruye el subconjunto cuyo estado geométrico completo deriva de
`SliderCrankChambers2T` y `IntegratedPortBinding2T`. En ese caso el callback de
geometría del constructor no se consulta; configuraciones con geometría
arbitraria definida únicamente por callbacks siguen fuera del contrato. La
identidad canónica se comprueba antes de exportar/restaurar y la deriva viva se
rechaza.

## 17. Decisiones científicas

| Fecha | Decisión | Alternativas | Evidencia | Revisión |
|---|---|---|---|---|
| 2026-10-05 | El enlace integrado finito de admisión reutiliza P3 ideal; no se añade una frontera atmosférica ni una nueva política de reservoir | Integrar solo el endpoint existente; tratar longitud efectiva como acústica sería una capability distinta | 99 pruebas focales integradas/P5-C/P6/P7/red/reed/puertos PASS; estado primario/output de un ciclo y conservation rebuild verificados | SELF_REVIEW; no hay recibo independiente durable del delta |
| 2026-10-05 | Generalizar volúmenes integrados a caras externas intake-left y exhaust-right conserva el helper P3 y el ledger existente; no añade aristas internas de red | Mantener un solo nodo de admisión; o modelar redes internas/acústica como otra capability | 100 pruebas integradas/P5-C/P6/P7/red/reed/puertos PASS; replay V7 de dos nodos, ciclo completo, outputs muestreados contra el estado y ledgers globales | SELF_REVIEW; no hay recibo independiente durable del delta |
| 2026-10-05 | La configuración V1 serializa sólo geometría reconstruible desde modelos explícitos. Si slider-crank y binding de puertos resuelven todos los campos, el callback legado queda ignorado y no es parte de la identidad | Ejecutar también el callback podría introducir efectos laterales o fallos que la configuración no puede reproducir; callbacks arbitrarios requerirían otro contrato | JSON canónico y snapshot inicial exactos, guard de deriva y cinco pruebas focales; la regresión integrada amplia actual está registrada en `program-status.json` | SELF_REVIEW conforme AUD-06; no hay recibo independiente durable para este delta |
| 2026-10-05 | AUD-11: `OPEN_END_PLENUM_V2` representa una abertura ideal, estacionaria e isentrópica como `SYNTHETIC_ASSUMPTION`; no es un carburador calibrado ni dato del WB40 | `LEGACY_CHARACTERISTIC_V1` se preserva para reproducción; una tobera restringida exige Cd/área documentados y otro contrato | Preregistro y tests analíticos V2 PASS; la campaña KT100 única no creó ciclos por fallo de agregación, no por un criterio de selección de frontera | Decisión científica humana CASE B; revisión puntual de implementación, no aceptación completa del Commercial Core |

## 18. Convenciones

Sin cambios a P4–P9, contratos, umbrales ni parámetros científicos. Artefactos
sintéticos siguen etiquetados y no sustituyen validación experimental.
`effective_length_m` es geometría/provenance, no una longitud activa en la
interfaz P3 ideal. Todo cambio de semántica de reservoir requiere capability y
contrato propios.

## 19. Blockers abiertos

- AUD-08 está completada con evidencia sintética fija de Fixture A: 20 ciclos,
  restart exacto y sin periodicidad aceptada; no reutilizar los ciclos A/B
  anteriores supersedidos.
- AUD-10 y AUD-12 se resolvieron: colector por roles y límite CONFIG_V2
  explícito; Cd=0 rechazado otra vez por GENERIC_2T_PORTS_V1.
- AUD-09 completó Fixture C piston-port sin reed: 20/20 ciclos, replay exacto y
  `PERIOD_1` al ciclo 20. No reprodujo el fallo histórico; como no hay traza
  cruda, no se atribuye una causa exacta. La evidencia es sintética y condicional
  a P4. AUD-11 está resuelto como CASE B. La cola machine-readable conserva los
  bloqueos locales de reed dinámica, fuel/AFR, Fixture B y la evidencia primaria
  de KT100 V2.
- `OPEN_END_PLENUM_V2` está implementada según el contrato CASE B y sus tests
  analíticos pasan. R6 no tiene ciclos primarios por el defecto recuperable del
  agregador ya corregido; no se vuelve a ejecutar bajo el preregistro consumido.
- La integración de reed dinámica sigue bloqueada por la falta de un contrato
  conservativo seleccionado para impacto, trabajo de presión y disipación. El
  trabajo de combustible con métricas atrapadas sigue bloqueado por observables
  y propiedades de combustible no definidos. Mantener estos items
  `BLOCKED_LOCAL`; no convertirlos en bugs ni inventar parámetros.
- La cola durable no tiene tareas `READY`: además de los bloqueos anteriores,
  la evidencia primaria de KT100 V2 no se puede recuperar dentro del único
  preregistro consumido y Fixture B depende de cerrar el collector integrado.
  Continuar cuando una dependencia se resuelva o se autorice un preregistro
  científico distinto; no ejecutar otra campaña con el contrato consumido.
- Reed dinámica integrada sigue sin contrato conservativo de impacto, trabajo
  de presión y disipación. AFR estequiométrica, LHV y combustible atrapado
  siguen indefinidos; las magnitudes derivadas permanecen `UNDEFINED`.
- El Commercial Core continúa parcial y `CONDITIONAL_ON_P4`, sin validación
  experimental ni aceptación completa. Las salidas de ciclo A/B anteriores
  se conservan solo como historia y están supersedidas por la auditoría.
- `audit_8cdf66e.md` es independiente solo para `ab92aee..8cdf66e`; el recibo
  `audit-triage-3d10f79.json` es una revisión acotada del HEAD de entrada. Los
  demás claims sin artefacto se clasifican `SELF_REVIEW`.
