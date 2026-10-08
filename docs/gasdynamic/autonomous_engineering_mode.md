# MotorSim — Modo autónomo de ingeniería V2

Reglas detalladas de `AGENTS.md` (`AGENTS_V2`). Ante conflicto prevalece
`AGENTS.md`; el estado operativo vive sólo en
`results/2t-commercial-core-20261002/program-status.json`. La versión V1 de este
documento, con su "estado vivo" y la tabla de decisiones científicas, está en
[docs/history/autonomous_engineering_mode_v1.md](../history/autonomous_engineering_mode_v1.md).
Este documento no contiene estado: no se edita para registrar avances.

## 1. Ciclo de una sesión

```
brief → check → promote → reevaluar BLOCKED_LOCAL → (READY < 3 ? replanificar)
→ tomar tarea → investigar → implementar → verificar → revisar → regresión
→ commit (código + cola + progress_log) → siguiente tarea
```

1. **Arranque.** `git status`, `git log --oneline -20`, HEAD real.
   `python scripts/agents/program_status.py brief`, `check`, `promote`.
   Verificar hash P9 (`check` lo hace). Inspeccionar untracked sin borrarlos.
2. **Reevaluar bloqueos.** Para cada `BLOCKED_LOCAL`: ¿algún commit posterior lo
   resuelve? → `DONE` con `resolution: SUPERSEDED_BY_LATER_CAPABILITY`. ¿Tiene
   `unblock_tasks` vivas? Si no, crearlas (sección 3).
3. **Elegir trabajo.** Prioridad: tareas del camino crítico del gate → tareas
   de desbloqueo → preparación no decisoria → deuda que afecta al gate. Las
   tareas `POST_*_BACKLOG` no se toman mientras haya trabajo del objetivo.
4. **Cerrar cada tarea** en un commit que incluya el cambio de estado y una
   entrada `progress_log`. Luego tomar la siguiente: cerrar una tarea nunca es
   motivo de terminación.
5. **Fin de sesión** sólo por A, B o C de `AGENTS.md` §2. Si el contexto o el
   tiempo se agotan, dejar la cola consistente y commiteada; el relanzador
   (sección 9) continúa.

## 2. Esquema de la cola

Cada item de `queue`: `id`, `description`, `dependencies`, `state`, `blocker`,
`commits`, `evidence`, `next_action`; opcionales: `objective`, `owner_role`,
`write_scope` (lista de rutas/prefijos), `evidence_level` (`L0`…`L3`),
`unblock_tasks`, `no_local_unblock_reason`, `resolution`, `qualification`,
`classification` (`BLOCKS_<OBJ>` / `POST_<OBJ>_BACKLOG`).

| Estado | Significado |
|---|---|
| `READY` | dependencias `DONE`, tomable ahora |
| `IN_PROGRESS` | con autoridad escritora asignada (`owner_role`, `write_scope`) |
| `WAITING` | sólo espera dependencias; sin bloqueo propio |
| `BLOCKED_LOCAL` | impedimento técnico propio; exige `unblock_tasks` o `no_local_unblock_reason` |
| `REVIEW` | implementado, esperando verificación/revisión |
| `DONE` | con evidencia; alcance limitado en `qualification` si corresponde |

No existen otros estados (`DONE_CONDITIONAL` y similares se expresan como
`DONE` + `qualification`). `check` rechaza estados desconocidos, dependencias
inexistentes, `BLOCKED_LOCAL` sin desbloqueo ni justificación, y `write_scope`
superpuestos entre tareas `IN_PROGRESS`.

## 3. Resolución de bloqueos

No devolver un bloqueo al humano. Para cada `BLOCKED_LOCAL` crear de inmediato
la tarea `READY` que corresponda:

| Tipo de bloqueo | Tarea de desbloqueo |
|---|---|
| fallo numérico/admisibilidad | minimal reproducer + forensics del estado exacto |
| falta un modelo físico estándar | `STANDARD_V1` versionado desde literatura de libro |
| falta un dato del motor | `SYNTHETIC_ASSUMPTION` etiquetada con provenance; nunca inventar datos reales |
| interfaz/estado insuficiente | tarea de arquitectura |
| duda sobre si un resultado es correcto | tarea de verificación (analítica, equilibrio, ledger) |
| fixture que no sirve para el gate | fixture alternativo, versionado y preregistrado si decide el gate |
| performance fuera de presupuesto | profiling + optimización con prueba de equivalencia |

Protocolo para bloqueos no triviales (en paralelo cuando se pueda):
**forensics** (reproducir, extraer estado), **domain** (reconstruir ecuaciones),
**skeptic** (buscar un bug ordinario antes de aceptar física nueva),
**contract guardian** (impacto sobre contratos cerrados). Luego hipótesis →
evidencia → contradicciones → experimento → síntesis.

Conocimiento externo: textbooks, papers y literatura de solvers, con rationale y
referencias. Sin red: teoría estándar y documentación del repo, registrando
`EXTERNAL_RESEARCH_UNAVAILABLE`. No inventar citas. No adoptar una formulación
porque "parece funcionar".

**Escalamiento al dueño** sólo si se cumple todo: ≥2 alternativas científicas
legítimas; cambian materialmente física o resultados; contratos, teoría,
evidencia y tests no resuelven; elegir es nueva política científica. Registrar
en `owner_decisions_pending` (`id`, `question`, `options`, `consequences`,
`evidence`, `recommendation`, `blocks`) y seguir con todo lo independiente.

## 4. Replanificación

Disparadores: menos de 3 `READY`; inicio de sesión; cierre de una tarea del
camino crítico. Procedimiento: leer el spec del objetivo, listar requisitos sin
tarea `DONE`, y crear tareas pequeñas (≤1 sesión) con dependencias explícitas.
Fuentes típicas de tareas legítimas: dividir una tarea grande, preparación no
decisoria (borradores, tests estructurales, scripts productores), regresiones
tempranas, diagnósticos de riesgo, verificación cruzada. Nunca crear tareas
que relajen criterios o reabran contratos congelados.

## 5. Roles

| Rol | Responsabilidad |
|---|---|
| orchestrator / tech lead | cola, dependencias, asignación de `write_scope`, integración, commits |
| physics / numerics | Euler cuasi-1D, Riemann, CFL, fronteras, conservación, SSPRK2, termo |
| architecture | interfaces, estado integrado, grafo de etapas, sin duplicación |
| implementation | workstreams en paralelo dentro de su `write_scope` |
| verification | unitarios, analíticos, negativos, conservación, restart/replay, regresiones |
| skeptic / adversarial | romper cada capability: expected circular, estado stale, etapa SSPRK equivocada, ledger incompleto, bool-como-número, NaN/inf, unidades, orientación, donante, summary como autoridad, fallback oculto, factores 2T, restart incompleto |
| contract / regression guardian | P4–P9, evidencia histórica, bindings, umbrales preregistrados |
| evidence / release reviewer | provenance, niveles L0–L3, claims, gate_status |

Paralelismo: permitido si los `write_scope` no se superponen. Un solo escritor
por scope; los revisores son read-only. El orchestrator integra.

`INDEPENDENT_REVIEW` = agente/sesión distinto, read-only, con artefacto durable
en el repo. Cualquier otra revisión es `SELF_REVIEW`. El implementador no
autorratifica cambios científicos significativos: requieren al menos una pasada
skeptic declarada, y `INDEPENDENT_REVIEW` si deciden un gate L3.

## 6. Niveles de evidencia y gobernanza

L0 tests · L1 corrida de ingeniería + plausibility gates · L2 AUDIT/referencia ·
L3 validación/claim preregistrado + revisión independiente.

- Desarrollo normal (features, modelos `STANDARD_V1`, refactors, outputs,
  performance con test de equivalencia): L0/L1 y code review normal.
- Preregistro + hashes completos + `INDEPENDENT_REVIEW`: gates core/release,
  cambios numéricos críticos, validación y claims externos.
- Preregistro: diseño + tests estructurales en un commit; la campaña decisoria
  en otro commit posterior. Diagnósticos y fixtures de desarrollo no se
  preregistran.
- Todo claim declara su nivel. Ningún resultado L1 se describe como L2/L3.

## 7. Principios técnicos del núcleo

- Un único grafo SSPRK2 y un único estado integrado serializable; sin
  integraciones ad hoc fuera del grafo.
- Ledgers globales de masa, energía y especies recalculables desde flujos
  primarios; "cada componente conserva" no prueba que conserve el motor.
- Evidencia primaria reconstruible offline; prohibido PASS almacenado como
  autoridad, summary contra summary, digest sin preimagen.
- Modelos de libro razonables se implementan como `STANDARD_V1` versionado con
  provenance (`DOCUMENTED`, `DERIVED_FROM_DOCUMENTED`, `SYNTHETIC_ASSUMPTION`,
  `UNKNOWN`); un modelo parametrizado no es predictivo.
- KT100 no es fixture de desarrollo; no se ajustan parámetros para hacerlo
  pasar; una campaña nueva requiere preregistro nuevo.

## 8. Protección histórica y provenance

- P0–P9: contratos, código congelado, evidencia, umbrales, expected values y
  tests no se modifican para facilitar trabajo nuevo; capability nueva =
  versión nueva. Si un cambio toca un runtime binding histórico, identificar el
  impacto de inmediato y no reinterpretar evidencia antigua.
- Evidencia supersedida se conserva con su etiqueta; no se borra ni se reusa.
- Antes de un cierre global: suite P4–P8 reejecutada, OpenSpec strict,
  `git diff --check`, `git lfs fsck`, hash P9.
- Decisiones científicas: se registran en `program-status.json → decisions`
  (la tabla histórica está en el V1 de este documento).

## 9. Continuidad entre sesiones y campañas

- **Relanzador:** `python scripts/agents/launcher.py --config <json>`. Antes de
  cada sesión consulta `program_status.py stop-status`; si es `CONTINUE`, abre
  una sesión nueva con `scripts/agents/session_prompt.md`, registra su log en
  disco y repite. Se detiene sólo por A, B o C (más salvaguardas: sesiones sin
  progreso consecutivas, lock de concurrencia, máximo de sesiones). Diseño en
  [agent_session_launcher.md](agent_session_launcher.md).
- **Campañas:** `scripts/agents/run_logged.py` escribe el output completo a
  archivo y emite un summary JSON compacto (exit code, duración, tail, errores,
  summary propio de la campaña si existe). El agente lee el summary primero y
  abre detalles sólo para diagnosticar.

## 10. Reporte

Durante el desarrollo: sólo `progress_log` (una entrada corta por tarea o
decisión importante). El informe completo se produce únicamente ante A, B o C
e incluye: HEAD inicial/final, objetivo y gate_status, tareas cerradas,
decisiones, bloqueos resueltos/pendientes, niveles de evidencia de cada claim,
regresiones y hash P9, riesgos y siguiente objetivo propuesto.
