# Auditoría externa del Commercial Core — snapshot `8cdf66e`

- **Fecha:** 2026-10-05
- **Alcance:** commits `ab92aee..8cdf66e` (24 commits), con foco en
  `motorsim/integrated_2t.py`, `tests/test_integrated_2t.py`,
  `results/2t-commercial-core-20261002/program-status.json` y la integridad de P4–P9.
- **Método:** auditoría de solo lectura sobre una copia exportada con
  `git archive 8cdf66e`. Tres revisores en contextos separados (rumbo, revisión
  adversarial del código, integridad/regresiones). Los hallazgos A1, A2 y B1 se
  reprodujeron además de forma directa.
- **Revisor:** Claude, modelo y sesión distintos de los de Codex, sin acceso a
  su contexto. Cuenta como revisión independiente de solo lectura del delta
  auditado. No modificó código, tests ni evidencia del repositorio.
- **Fuera de alcance:** los cambios sin commitear posteriores a `8cdf66e` y la
  validación experimental. Nada de lo que sigue valida la física contra datos
  reales.

## 1. Veredicto

El trabajo siguió la prioridad correcta: integró antes de agregar componentes,
no modificó P4–P9 ni KT100, y existe un único motor SSPRK2 que completa ciclos.
Sin embargo:

- dos defectos de física (A1, A2) invalidan la evidencia de ciclo actual;
- los PASS de los fixtures dicen menos de lo que el estado declara;
- **`GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED` no está alcanzado.**

Toda la evidencia de ciclos de Fixture A y B debe regenerarse después de
corregir A1–A3.

## 2. Verificado sin hallazgos

- **SSPRK2:** forma de Heun correcta, `qn = q0 + dt/2 (r0 + r1)`. Cada etapa
  evalúa geometría, áreas de puerto, reed y fronteras en su propio ángulo y
  estado. Las fuentes P7, calor a pared y p·dV se aplican una vez por etapa.
- **Convenciones:** orientación y signos de normales coherentes; la especie
  donante es el upstream real bajo retroflujo; RPM→grados/s y signo de p·dV
  correctos; IMEP y potencia con un ciclo por vuelta; torque = W/2π.
- **Ledgers:** masa, energía y especies cierran al redondeo (~1e-18 kg,
  ~5e-13 J). Se construyen con los flujos primarios, no por diferencia de
  estados finales.
- **Checkpoint/replay:** restore validado antes de mutar el estado; el replay
  compara el snapshot completo, trace incluido.
- **Periodicidad:** el detector `REFERENCE_PERIODIC_CONVERGENCE_V1` estaba
  preregistrado antes de `ab92aee` y sus umbrales no cambiaron. Las
  clasificaciones PERIOD_1 (A en el ciclo 16, B en el 19) se reprodujeron
  offline.
- **Integridad histórica:** el SHA-256 del spec P9 sobre el contenido git es
  `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`. No hay
  cambios en `openspec/changes/archive`, en resultados anteriores al
  2026-10-02, en módulos P4–P8 ni en KT100.
- **OpenSpec:** `openspec validate --all --strict --no-interactive` → 32/32.
- **Tests:** P4–P8 reejecutados, 300/300 PASS. Integrados, 85/85 PASS. Suite
  amplia por archivo: 931 passed, 33 failed, 10 errors. Los fallos son del
  entorno de la copia (CRLF vs LF en hashes fijados, Qt, carpetas ignoradas) y
  ninguno involucra código del rango auditado.

## 3. Hallazgos

Severidad: **DEFECT** = incorrecto o incumple una regla; **RISK** = debilita
lo declarado; **OPTIONAL** = mejora no bloqueante.

### A. Física y numérica

**A1 — DEFECT. Un puerto cerrado o parcialmente abierto no ejerce presión de pared.**
- **Ubicación:** `motorsim/integrated_2t.py:599-610, 639-647, 679-684, 732-735`.
- **Qué pasa:** con área de puerto cero, el flujo de cara es `(0, 0, 0)`,
  incluido el momento. Con área parcial, `interface_flux` escala el momento
  por el área abierta. En ambos casos el término geométrico del ducto usa el
  área de malla completa, así que el ducto recibe una fuerza neta
  `p·(A_malla − A_efectiva)/V`. P5C ya incluía esta fuerza (`closed_force` en
  `motorsim/exhaust_port.py:43`) y P5B también (`motorsim/p5b.py:166`); el
  camino integrado la perdió.
- **Reproducción:** presión uniforme de 101325 Pa, puertos cerrados, un paso
  de 1e-7 s. El momento del transfer queda en `[-1.0115, +1.0115]` con área 0,
  en `[-0.5055, +0.5055]` con área 0.5e-4 y en `[0, 0]` con área igual a la de
  malla. En el fixture de ciclos se observan |u| = 378 m/s en el transfer boost
  con el puerto exactamente cerrado (281°).
- **Por qué nadie lo detectó:** el momento no tiene ledger y ningún test
  comprueba un ducto en reposo.
- **Afecta:** delivery, cortocircuito, barrido, trabajo y todas las salidas de
  ciclo.

**A2 — DEFECT. El fixture de ciclos arranca a 2,86 bar y 857 K, no a presión atmosférica.**
- **Ubicación:** `tests/test_integrated_2t.py:657`; constructor en
  `motorsim/integrated_2t.py:415-419`.
- **Qué pasa:** el fixture pasa `289500.0`. El comentario lo describe como
  densidad de energía, pero `_chamber_from_primitive` lo interpreta como
  presión. Valor introducido en `e93fd62`.
- **Afecta:** toda la evidencia de ciclos, incluido el trabajo negativo del
  ciclo 1 y el INVALID del primer par de periodicidad.

**A3 — DEFECT. Una única composición atmosférica para admisión y escape.**
- **Ubicación:** `motorsim/integrated_2t.py:555, 562` (`atmosphere_species`).
- **Qué pasa:** el combustible solo entra mezclado en la composición
  atmosférica (0.98/0.02), y esa misma composición se usa en la salida del
  escape. Todo retroflujo por el stinger introduce combustible.
- **Medición (dos ciclos):** entran 3.23e-6 kg de combustible por la salida
  del escape frente a 9.67e-6 kg por la admisión.
- **Afecta:** `fuel_short_circuited_kg`, el consumo P7, el balance de
  combustible, AFR e ISFC.

**A4 — RISK. El redondeo de especies puede producir una fracción mayor que 1 y abortar el paso.**
- **Ubicación:** `motorsim/integrated_2t.py:485, 827`.
- **Qué pasa:** `validate_species` tolera un desajuste de 1e-14 kg, pero
  `(s0 + s1)/masa > 1` falla después en `eos.validate`.
- **Reproducción:** un cárter con solo aire y combustible (0.98/0.02) y la
  admisión abierta falla en el paso 128 con `Y > 1` por redondeo.
- **Enmascaramiento:** `_advance_cycle_fixture`
  (`tests/test_integrated_2t.py:699-704`) captura justamente ese error y
  reduce dt a la mitad.
- **Hipótesis a verificar:** A1 o A4 pueden explicar el fallo de
  admisibilidad del candidato piston-port sin reed a 107,65° (ver B1).

**A5 — RISK. Las métricas de delivery y cortocircuito son flujos brutos, no netos.**
- **Ubicación:** `motorsim/integrated_2t.py:623-624, 664, 695-696`.
- **Qué pasa:** la carga fresca que vuelve del cilindro a los transfers y se
  reentrega se cuenta dos veces. Medido: 17 % de la delivery bruta.
- **Además:** la línea 1822 describe el flujo como "fresh_air", pero suma
  fresh_air + fuel. Hay que documentar la definición o corregirla.

**A6 — RISK. ISFC y AFR no reflejan el combustible quemado.**
- Con `fuel_delivery == 0` y potencia positiva, ISFC queda `DEFINED` con
  valor 0.0 (`integrated_2t.py:1851-1853`).
- AFR devuelve exactamente la relación de la frontera (≈49), lo que es
  tautológico.

**A7 — RISK. Hay fuentes sin verificación cruzada.**
- Sin `slider_crank`, las tasas de volumen del callback no se contrastan con
  dV/dθ·ω.
- Con `slider_crank` o `port_binding`, los volúmenes y áreas del callback se
  sobrescriben sin aviso (`integrated_2t.py:459-475`).
- El calor a pared es explícito y dt no se limita por la escala térmica.

**A8 — RISK. No hay estudio de malla.**
- La cámara tiene 5 celdas en A y 7 en B (dx ≈ 0,13 m); admisión y transfers,
  2 celdas cada uno.
- Con eso la cámara está conectada, pero sus ondas no se resuelven.

**A9 — RISK. El timing sintético es implausible.**
- El escape auxiliar está abierto de 60° a 310°.
- P7 quema de 300° a 340°, antes del PMS y con el escape abierto; el cilindro
  está a ≈64 bar en el límite de ciclo.
- Por eso las cifras de performance no representan un punto de operación 2T.

**A10 — RISK. El detector de periodicidad no admite trabajo negativo.**
- `reference_harness/convergence.py:32-34` lanza un error si a < 0.
- Un régimen periódico motorizado o con trabajo negativo nunca puede
  clasificarse como P1 o P2.

### B. Generalidad y arquitectura

**B1 — DEFECT. Fixture B no es "significativamente distinto" (§9 del modo autónomo).**
- **Ubicación:** `tests/test_integrated_2t.py:581, 616-627`;
  `program-status.json:265-282`.
- **Qué pasa:** el único cambio es `chamber_length_scale=1.2`. Puertos,
  intake, reed, transfers, combustión, térmico, fronteras y RPM son idénticos.
- **Contexto:** el candidato realmente distinto (piston-port sin reed) falló a
  107,65° y se reemplazó por esta variante.

**B2 — DEFECT. Hardcode de ids de ducto en el collector.**
- **Ubicación:** `motorsim/integrated_2t.py:1585, 1588, 1593`.
- **Qué pasa:** usa `face_fluxes["intake"]` y `face_fluxes["exhaust"]` por id,
  no por rol.
- **Reproducción:** con ids `('inlet', 'pipe')` falla con `KeyError 'intake'`.

**B3 — DEFECT. La topología está restringida.**
- **Ubicación:** `motorsim/integrated_2t.py:283-286`.
- **Qué pasa:** exige al menos 3 transfers y exactamente una admisión y un
  escape. No representa motores de dos transfers, que son comunes.

**B4 — DEFECT. El bloqueo del reservoir se difirió sin investigarlo.**
- **Ubicación:** `program-status.json:238, 647-656`;
  `docs/gasdynamic/generalized_reservoir_boundary_v2_debt.md`, sin cambios
  desde antes de `ab92aee`.
- **Qué pasa:** no se aplicó el protocolo de §7/§8 y se etiquetó como
  `..._SCIENTIFIC_DECISION_REQUIRED` sin el paquete de escalamiento de §13.
  Ambos fixtures usan fronteras `nonreflecting` fijas.

**B5 — RISK. Hay componentes que no están en el camino integrado.**
- Reed dinámico (BLOCKED_LOCAL), `COMBUSTION_MODEL_V2` (Wiebe, CA10/50/90),
  térmico multisuperficie (solo hay pared de cilindro) y plenum/airbox.
- La performance al freno es posproceso con un FMEP sintético de 10 kPa.

### C. Evidencia, preregistración y estado

**C1 — DEFECT. La evidencia no se puede reproducir desde el repo.**
- No hay script commiteado que genere los artefactos de 6, 12, 16 y 19 ciclos
  ni la auditoría de restart.
- El fixture y el stepper solo existen como helpers privados de test
  (`tests/test_integrated_2t.py:581, 679`).

**C2 — DEFECT. El horizonte de Fixture A no estaba preregistrado.**
- En `f846aa3` se registraron 6 ciclos con la periodicidad fallando.
- `b50507b` extiende a 16 ciclos y declara PERIOD_1 sin un horizonte
  commiteado antes. Equivale a un criterio de parada elegido a posteriori.

**C3 — DEFECT. El criterio de Fixture B y sus resultados están en el mismo commit (`b50507b`).**
- La variante se eligió después del fallo del candidato piston-port.

**C4 — RISK. Schema, geometría del fixture y campaña en un mismo commit (`2c93e6c`).**
- Incluye `MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V2`,
  `MOTORSIM_ENGINEERING_OUTPUTS_V2`, el cambio del perfil de escape y la
  campaña de 6 ciclos.
- El resultado fue FAIL, así que no produjo un PASS, pero incumple la regla
  de commit separado.

**C5 — DEFECT. Hay afirmaciones de revisión independiente sin artefacto.**
- **Ubicación:** `program-status.json:491-493, 514, 534, 561, 585`;
  `tasks.md:360`; documento de estado, líneas 77, 91, 120 y 302.
- **Qué pasa:** aparecen unas ocho afirmaciones de "independent read-only
  review", introducidas en `a70917d`, `d3b82f3`, `8953c2d`, `8b04b83`,
  `6cb7f98`, `2c93e6c` y `b50507b`, sin ningún archivo de revisor en el árbol.

**C6 — RISK. Se aflojó in situ un criterio de validación (Cd = 0).**
- `104bb00` cambia `cd <= 0` por `cd < 0` en `motorsim/two_stroke_ports.py:129`.
- En el mismo commit quita `0.0` del test negativo existente en
  `tests/test_two_stroke_ports.py`, sin versionar `GENERIC_2T_PORTS_V1`.
- Ningún fixture usa Cd = 0, así que no afecta resultados.

**C7 — RISK. Las verificaciones de ciclo son autoconsistentes.**
- `make_integrated_cycle_primary` (`integrated_2t.py:1369-1379`) compara los
  ledgers con tasas leídas del mismo trace.
- Las tasas por etapa nunca se recalculan con `_assemble`.
- `restore` (`integrated_2t.py:1130-1132`) solo comprueba la longitud del
  trace.
- En la línea 1373, `value if key not in end_ledger` compara un valor consigo
  mismo.

**C8 — DEFECT. La cola durable es inconsistente.**
- Hay estados fuera del conjunto permitido: `DONE_CONDITIONAL` y
  `BLOCKED_LOCAL_DYNAMIC_REED_COUPLING`.
- 17e figura DONE con 17b BLOCKED y 17d IN_PROGRESS.
- El ítem 18 tiene `commits: []` y la referencia `e93fd624` no resuelve.
- `status_capture_head` está desactualizado.
- La fase 1 dice que no hay ciclos completos.
- Las secciones vivas §15–19 de `autonomous_engineering_mode.md` siguen en
  "Pendiente".

**C9 — RISK. Las cifras de estado son inconsistentes.**
- `program-status.json:293, 603` dice "P4 unresolved", contra `P4_PASS` en
  AGENTS.md y en `results/p4-g2-v2-20260929/decision-final.json`.
- AGENTS.md cita 346 regresiones registradas, cifra heredada de
  `program-status.json` en `a5b4424`, cuando el conteo real de P4–P8 es 300.

**C10 — RISK. La suite tiene efectos secundarios.**
- Al correr reescribe los JSON versionados de `examples/projects/`: mismo
  contenido, distintos finales de línea.
- Los hashes fijados en algunos tests dependen de los finales de línea del
  checkout.

### D. Opcionales

- `thermal_load` y `displacement_m3` usan `float(...)` y aceptan `True` y
  strings numéricos (`integrated_2t.py:320, 1570`).
- `rejected_steps` solo cuenta rechazos por CFL.
- El checkpoint embebe el trace completo, así que crece con la duración de la
  corrida.
- El motor restaurado desde JSON se compara pero nunca se sigue integrando
  (`tests/test_integrated_2t.py:120-127`).
- `atomic_json_checkpoint` valida de forma atómica, pero no escribe de forma
  atómica.

## 4. Tabla de estado frente a §9

| Requisito | Estado observado |
|---|---|
| Estado integrado + SSPRK2 común | Integrado |
| Admisión | Integrada; una sola vía, sin plenum/airbox |
| Reed | Estático integrado; dinámico bloqueado |
| Cárter | Integrado |
| N transfers | Integrado, pero exige ≥3 (B3) |
| Cilindro | Integrado |
| Escape/cámara | Integrado, mal resuelto (A8) y con A1 |
| Frontera | `nonreflecting` fija; reservoir V2 ausente (B4) |
| Cuatro especies | Integrado; frontera de escape incorrecta (A3) |
| Barrido | Integrado; métricas brutas (A5) |
| Combustible | Mezcla premezclada desde la frontera (A3, A6) |
| Combustión | P7 integrado; V2 solo como componente |
| Térmico | Una superficie |
| Ledgers globales | Integrados; momento sin control (A1) |
| Periodicidad | Integrada; horizonte no preregistrado (C2), A2 |
| Performance indicada | Integrada; cifras no representativas (A9) |
| Performance al freno | Posproceso con FMEP sintético |
| Checkpoint/restart/replay | Integrado; productores no commiteados (C1) |
| Outputs | Integrados; hardcode de ids (B2) |
| Fixture A | Existe como helper de test, no como config |
| Fixture B distinto | No cumplido (B1) |

## 5. Tareas propuestas para la cola

Cargar en `program-status.json` → `queue`. Las de prioridad 1 preceden a
cualquier capability nueva.

| ID | Prioridad | Tarea | Hallazgos | Dependencias |
|---|---|---|---|---|
| AUD-01 | 1 | Agregar la fuerza de pared en puertos cerrados y parciales del camino integrado, reutilizando la formulación P5B/P5C, más un test "ducto en reposo con puertos cerrados se queda en reposo" para área 0, parcial y total | A1 | — |
| AUD-02 | 1 | Corregir la condición inicial del fixture de ciclos (presión atmosférica real) y un test que verifique p y T iniciales | A2 | — |
| AUD-03 | 1 | Separar la composición de la frontera de admisión de la de escape; la frontera de escape no aporta combustible | A3 | — |
| AUD-04 | 1 | Hacer la admisibilidad de especies robusta al redondeo sin clipping silencioso, y sacar del harness de test el reintento por errores de admisibilidad o registrarlo como rechazo | A4 | — |
| AUD-05 | 1 | Commitear scripts productores de toda la evidencia de ciclos y definir los fixtures como configuración, no como helpers de test | C1 | — |
| AUD-06 | 1 | Bajar a `SELF_REVIEW` toda afirmación de revisión independiente sin artefacto, y registrar esta auditoría como la revisión independiente del delta `ab92aee..8cdf66e` | C5 | — |
| AUD-07 | 1 | Normalizar la cola (estados válidos, dependencias, commits y refs), corregir "P4 unresolved" y el 346, y completar §15–19 | C8, C9 | — |
| AUD-08 | 2 | Preregistrar en un commit propio el horizonte de ciclos y el criterio de selección de fixtures; regenerar la evidencia de Fixture A | C2, C3, C4 | AUD-01..05 |
| AUD-09 | 2 | Reintentar Fixture B con piston-port sin reed (u otra topología realmente distinta) y diagnosticar el fallo de 107,65° | B1, A4 | AUD-01, AUD-04, AUD-08 |
| AUD-10 | 2 | Collector por rol en lugar de id; permitir N ≥ 1 transfers y múltiples admisiones/escapes, o documentar la restricción como versión | B2, B3 | — |
| AUD-11 | 2 | Aplicar el protocolo forense de §7/§8 al reservoir y producir la conclusión A, B o C con evidencia; si es C, armar el paquete de §13 | B4 | — |
| AUD-12 | 2 | Versionar el cambio de Cd = 0 como contrato nuevo o revertirlo, restaurando el test negativo original | C6 | — |
| AUD-13 | 3 | Estudio de malla de la cámara y los transfers dentro del presupuesto | A8 | AUD-01 |
| AUD-14 | 3 | Definir delivery y cortocircuito netos o documentar la definición bruta; corregir la etiqueta fresh_air; ISFC sin combustible → UNDEFINED | A5, A6 | AUD-03 |
| AUD-15 | 3 | Timing sintético plausible (combustión cerca del PMS, escape cerrado durante la combustión), como fixture nuevo preregistrado | A9 | AUD-08 |
| AUD-16 | 3 | Verificaciones cruzadas: recalcular las tasas por etapa con `_assemble` en la auditoría, validar el contenido del trace en `restore`, eliminar la comparación tautológica de la línea 1373, contrastar los volúmenes del callback con dV/dθ·ω | C7, A7 | — |
| AUD-17 | 3 | Detector de periodicidad que admita trabajo negativo, como versión nueva sin modificar V1 | A10 | — |
| AUD-18 | 3 | Tests sin efectos secundarios sobre `examples/projects/` y hashes independientes de los finales de línea | C10 | — |

## 6. Consecuencias para la evidencia existente

- Los artefactos de ciclos de Fixture A y B en
  `results/2t-commercial-core-20261002/` son evidencia histórica de un estado
  con defectos A1–A3. No deben borrarse ni reinterpretarse: se marcan como
  superados por la evidencia regenerada después de AUD-01..AUD-08.
- La regresión P4–P8 no se ve afectada: los defectos están solo en el camino
  integrado nuevo.
- Cualquier PASS de ciclo integrado posterior a esta auditoría requiere AUD-01,
  AUD-02, AUD-03 y AUD-08 cerrados.
