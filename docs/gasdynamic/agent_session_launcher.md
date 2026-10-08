# Relanzador de sesiones autónomas

Objetivo: mientras exista trabajo resoluble para `CURRENT_OBJECTIVE`, abrir
sesiones nuevas automáticamente, sin intervención humana, y detenerse sólo por
las condiciones A/B/C de `AGENTS.md` §2.

## Componentes

| Archivo | Rol |
|---|---|
| `scripts/agents/program_status.py` | lectura/validación de la cola; `stop-status` decide continuar o parar |
| `scripts/agents/launcher.py` | loop externo: stop-status → sesión → medición de progreso |
| `scripts/agents/session_prompt.md` | prompt fijo de reanudación (lee `AGENTS.md` y la cola) |
| `scripts/agents/run_logged.py` | ejecuta un comando con log completo a disco y summary JSON compacto |
| `scripts/agents/launcher.example.json` | configuración (comando del agente, límites) |

## Flujo

```
launcher
  ├─ git rev-parse HEAD            (falla → STOP C)
  ├─ program_status.stop_decision  (STOP_A / STOP_B / STOP_C → exit 10/11/12)
  ├─ render session_prompt.md      → <log_dir>/<ts>-sNNN/prompt.md
  ├─ run agent_command             → session.log + session.summary.json
  ├─ fingerprint (HEAD, len(progress_log), digest de estados de la cola)
  └─ repetir
```

La sesión del agente es la única escritora de `program-status.json`; el
relanzador sólo lo lee.

## Paradas

| Código | Causa |
|---|---|
| 10 | A: gate terminal (`PASS`/`FAIL_TERMINAL`) sin objetivo siguiente aprobado |
| 11 | B: `owner_decisions_pending` abierta y sin tareas `READY`/activas |
| 12 | C: `hard_stop.active`, o git no disponible |
| 20 | salvaguarda: N sesiones seguidas sin commit, sin `progress_log` nuevo ni cambio de la cola |
| 21 | salvaguarda: `max_sessions` alcanzado |
| 22 | otro relanzador tiene el lock (`<log_dir>/launcher.lock`) |

Las salvaguardas 20–22 son operativas y requieren mirar los logs. No son
terminaciones del programa.

## Uso

```
python scripts/agents/launcher.py --config scripts/agents/launcher.example.json --dry-run
python scripts/agents/launcher.py --config scripts/agents/launcher.example.json
```

Observabilidad:
- `<log_dir>/launcher.jsonl` tiene un evento por inicio, fin y parada de
  sesión.
- Cada sesión tiene su propio directorio con prompt, log y summary.
- `log_dir` por defecto es `.agent-sessions/`, ignorado por git.

## Notas

- Verificar los flags de `agent_command` contra la versión instalada de Codex
  CLI. El ejemplo usa `codex exec "<prompt>"`, que es el modo no interactivo.
- No correr el relanzador sobre un working tree donde trabaja otra sesión
  manual: usar un worktree propio.
- Cuando el gate es terminal y existe en `objectives` un objetivo con
  `owner_approved: true`, `stop-status` devuelve `CONTINUE` con
  `ACTION=SWITCH_OBJECTIVE`. Entonces la sesión actualiza `current_objective`
  y `AGENTS.md` §1 en un commit y continúa.
