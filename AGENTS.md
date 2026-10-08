# MotorSim — Instrucciones operativas para agentes (`AGENTS_V2`)

Este archivo es la única instrucción operativa vigente del repositorio. Todo lo
anterior (órdenes P0–P4, STOP históricos, "detenerse al completar", "nueva
autorización", "único escritor", `tasks.md` como único registro) está en
[docs/history/agents_orders_historicas.md](docs/history/agents_orders_historicas.md)
como provenance y **no** es instrucción vigente. No inferir el objetivo ni
reglas desde documentos históricos.

## 0. Al iniciar cada sesión

1. Leer este archivo.
2. Ejecutar `python scripts/agents/program_status.py brief` (objetivo, gate,
   cola, bloqueos, últimos avances, decisión de parada).
3. Ejecutar `python scripts/agents/program_status.py check` y
   `python scripts/agents/program_status.py promote`.
4. Reevaluar **todos** los `BLOCKED_LOCAL` (sección 3) antes de tomar trabajo.
5. Continuar `CURRENT_OBJECTIVE`. No reconstruir planificación desde cero.

Reglas detalladas: [docs/gasdynamic/autonomous_engineering_mode.md](docs/gasdynamic/autonomous_engineering_mode.md).

## 1. CURRENT_OBJECTIVE

```
CURRENT_OBJECTIVE: ENGINE_PHYSICS_V1_R2
change/spec:       openspec/changes/engine-physics-v1-r2/
                   (specs/engine-physics-v1-r2/spec.md es la autoridad de requisitos)
completion:        offline superseding gate de outputs, plausibility gates y
                   operating-point contract; technical result REVIEW hasta
                   R2-EXTERNAL-REVIEW. ENGINE_PHYSICS_V1 permanece
                   FAIL_TERMINAL y no se reabre. El baseline
                   MOTORSIM_2T_V1_CLOSURE_R2 permanece PASS y el gate histórico
                   MOTORSIM_2T_V1_CLOSURE_V1_0 permanece FAIL_TERMINAL.
durable queue:     results/2t-commercial-core-20261002/program-status.json
                   → current_objective, queue, gate_status, progress_log
```

El valor machine-readable vive en `program-status.json → current_objective`; si
difiere de este bloque, prevalece `program-status.json` y se corrige este archivo
en el mismo commit. Objetivos siguientes: `program-status.json → objectives`.
Sólo se pasa automáticamente al siguiente si tiene `owner_approved: true`.

## 2. Condiciones de terminación (las ÚNICAS)

Una sesión, y el relanzador, terminan solamente si:

- **A. Gate alcanzado:** `gate_status.state` es `PASS` o `FAIL_TERMINAL` para
  `CURRENT_OBJECTIVE` y no hay un objetivo siguiente con `owner_approved: true`.
- **B. Decisión del dueño:** existe una decisión científica genuina (sección 3,
  escalamiento), registrada en `owner_decisions_pending` con opciones A/B,
  consecuencias, evidencia y recomendación; no hay alternativa resoluble
  localmente **y** no queda ninguna tarea `READY`.
- **C. Hard stop global real:** repo corrupto, entorno roto (Python/dependencias
  irreparables, disco lleno), conflicto de escritura con otra sesión activa, o
  imposibilidad comprobada de persistir estado. Se registra en `hard_stop`.

**NO son motivos para terminar:** terminar una tarea; hacer un commit; completar
una campaña; completar un preregistro; encontrar un `BLOCKED_LOCAL`; tener
información suficiente para un reporte; agotar una rama de investigación
mientras existan otras resolubles; un test que falla; una revisión con
hallazgos; quedar con menos de 3 `READY` (eso obliga a replanificar).

Si la sesión se agota por contexto o tiempo, no es una terminación: dejar
`program-status.json` consistente y commiteado; el relanzador abre otra sesión.

## 3. Autonomía

- No se requiere autorización humana entre tareas dentro de `CURRENT_OBJECTIVE`.
- **`BLOCKED_LOCAL` genera trabajo.** Al marcar una tarea `BLOCKED_LOCAL`, en el
  mismo commit: crear al menos una tarea `READY` de desbloqueo (diagnostics,
  forensics, modelo `STANDARD_V1`, `SYNTHETIC_ASSUMPTION` etiquetada, minimal
  reproducer, tarea de arquitectura, tarea de verificación o fixture
  alternativo) y listarla en `unblock_tasks`; o, si no existe ninguna local,
  justificarlo en `no_local_unblock_reason` (candidato a condición B).
- Esperar dependencias no es un bloqueo: usar `WAITING`; `promote` la pasa a
  `READY` cuando todas sus dependencias están `DONE`.
- **Menos de 3 `READY`:** la siguiente tarea es replanificar la cola contra
  `CURRENT_OBJECTIVE` (dividir tareas, adelantar preparación no decisoria,
  diagnósticos, regresiones tempranas, deuda que bloquea el gate).
- Blockers obsoletos por cambios ya implementados se cierran con
  `resolution: SUPERSEDED_BY_LATER_CAPABILITY` y la evidencia correspondiente.
- **Escalar al dueño sólo** si: ≥2 alternativas físicamente legítimas, con
  consecuencias materiales, que teoría, contratos, evidencia y tests no
  resuelven, y elegir constituye nueva política científica. Mientras se espera,
  continuar todo lo independiente.
- **Nunca escalar:** bugs, refactors, APIs, nombres, schemas, serialización,
  performance, tests, diagnósticos numéricos, documentación, Git, fallos
  recuperables, elección de un modelo de libro razonable (se implementa como
  `STANDARD_V1`/`SYNTHETIC_ASSUMPTION` versionado y se calibra después).

## 4. Roles y agentes

El orchestrator/tech lead coordina, asigna, integra y mantiene la cola. Roles:
orchestrator; physics/numerics; architecture; implementation; verification;
skeptic/adversarial review; contract/regression guardian; evidence/release
reviewer. Pueden ser subagentes, worktrees o pasadas secuenciales.

- Trabajo paralelo permitido cuando los `write_scope` de las tareas
  `IN_PROGRESS` no se superponen (`check` lo verifica).
- **Una sola autoridad escritora por tarea o por conjunto de archivos en
  conflicto.** "Single writer" no significa "single agent": lectores,
  revisores y escritores de otros scopes trabajan en paralelo.
- Revisión por un agente distinto, read-only y con artefacto durable =
  `INDEPENDENT_REVIEW`. Pasada secuencial del mismo agente = `SELF_REVIEW`.
  Nunca etiquetar una autorrevisión como independiente.

## 5. Cola, progreso y reporte

- `program-status.json` es la **única autoridad operativa**: current objective,
  objectives, queue, blockers, dependencies, progress_log, gate_status.
  Se actualiza en el mismo commit que cambia el estado de una tarea.
- Estados: `READY`, `IN_PROGRESS`, `WAITING`, `BLOCKED_LOCAL`, `REVIEW`, `DONE`.
- `tasks.md` de los changes OpenSpec es vista derivada/documentación, no
  autoridad. Ante divergencia prevalece la cola.
- Progreso: una entrada compacta por tarea/decisión importante con
  `python scripts/agents/program_status.py log --task ID --summary "..."`.
- **Informe completo sólo** ante A, B o C. Sin informes por bloque, feature,
  campaña o subagente.

## 6. Niveles de evidencia

| Nivel | Qué es | Cuándo se exige |
|---|---|---|
| L0 | tests automatizados | todo cambio |
| L1 | corrida de ingeniería + plausibility gates | features y modelos `STANDARD_V1` |
| L2 | corrida AUDIT/referencia (ledgers completos, replay, hashes) | cambios numéricos críticos, fixtures de gate |
| L3 | validación/claim preregistrado + `INDEPENDENT_REVIEW` | gates core/release, validación, claims externos |

Desarrollo normal no exige L2/L3. Preregistro, hashes completos y revisión
independiente se reservan para gates core/release, cambios numéricos críticos,
validación y claims externos. El gate actual (spec v1 closure) exige lo que su
spec define; no se relaja.

## 7. Campañas y contexto

Campañas y corridas largas se lanzan con
`python scripts/agents/run_logged.py --name N --out DIR -- <comando>`: el output
completo va a archivo y se imprime sólo un summary JSON compacto. Leer primero
el summary; abrir logs sólo para diagnosticar y por fragmentos. Presupuestos:
diagnóstico ≤10 min; fixture/integración ≤30 min por configuración; campaña
científica ≤60 min (≤120 min sólo si es gate-critical, con checkpoint/restart y
progreso persistido). Proyección mayor = `BLOCKED_LOCAL` de performance con
tarea de desbloqueo; nunca reducir precisión, CFL ni umbrales para cumplirlo.

## 8. Protección de contratos y evidencia histórica

- No modificar P0–P9 (contratos, código congelado, evidencia, umbrales,
  expected values, tests) para facilitar trabajo nuevo. Capability nueva =
  versión nueva. Criterio nuevo = versionado y, si decide un gate, preregistrado
  y commiteado antes de la campaña.
- Hash congelado P9:
  `openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md`
  → SHA-256 `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`.
- Estado vigente (detalle en `program-status.json`): P4 `P4_PASS`; P5–P8
  `REVALIDATED_ON_P4_PASS`; P9 `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`;
  validación experimental `NOT_PERFORMED`; predictiva `NOT_CLAIMED`; KT100
  `KT100_REFERENCE_CASE_V1`, no verificado, sin R2 sin preregistro nuevo.
  Regresiones P4–P8: reejecutar antes de cualquier cierre (último conteo
  externo: 300 PASS).
- Evidencia histórica supersedida (ciclos A/B pre-auditoría) se conserva y no
  se reinterpreta. Nada sintético se presenta como validación experimental.
- `dev_orchestrator/` no es producto: no empaquetarlo ni depender de él desde
  `motorsim/`.

## 9. Git

- Sin push, force-push, reset/rebase destructivo ni publicación automática.
- Commits pequeños y semánticos; el estado de la cola va en el mismo commit.
- Inspeccionar archivos untracked antes de stage; preservar sin stage los
  directorios `results/kt100-hybrid-model-fixture-v2-harness-20261002*`.
- Preservar cambios ajenos; con otra sesión activa en el mismo working tree,
  trabajar en otro worktree/rama.
- No subir credenciales ni entornos; no codificar rutas absolutas locales.

## 10. Historial

- Órdenes anteriores: [docs/history/agents_orders_historicas.md](docs/history/agents_orders_historicas.md).
- Modo autónomo V1 y su "estado vivo": [docs/history/autonomous_engineering_mode_v1.md](docs/history/autonomous_engineering_mode_v1.md).
- Auditoría externa `ab92aee..8cdf66e`: [docs/gasdynamic/audit_8cdf66e.md](docs/gasdynamic/audit_8cdf66e.md).
