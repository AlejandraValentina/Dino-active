Sesión autónoma MotorSim #{session_index}. Estado de parada al lanzar: {stop_status}.

1. Leé `AGENTS.md` completo. Es la única instrucción operativa; lo histórico no
   es instrucción.
2. Ejecutá `python scripts/agents/program_status.py brief`, luego `check` y
   `promote`. Reevaluá todos los `BLOCKED_LOCAL` (crear tareas de desbloqueo o
   cerrar los obsoletos). Si hay menos de 3 `READY`, replanificá primero.
3. Continuá `CURRENT_OBJECTIVE` tomando tareas de la cola. Cerrá cada tarea con
   un commit que incluya el cambio de estado y una entrada
   `program_status.py log`. Después tomá la siguiente.
4. Campañas y corridas largas sólo con `scripts/agents/run_logged.py`; leé el
   summary, no el log completo.
5. Terminá **únicamente** por las condiciones A, B o C de `AGENTS.md` §2.
   Terminar una tarea, un commit, una campaña o un preregistro no es motivo.
   Si se te agota el contexto, dejá `program-status.json` consistente y
   commiteado: el relanzador abrirá otra sesión.
6. Sin push. No modificar P0–P9 ni relajar criterios.
