# Autonomous roadmap supervisor

The supervisor is external development infrastructure under `dev_orchestrator`; product modules do not import it. It reads durable roadmap/task state, creates a PID lock, records before/after snapshots, invokes only a configured or safely detected CLI, captures logs, and detects missing agent configuration without inventing a command.

Use on Windows:

```powershell
python dev_orchestrator/roadmap_supervisor.py status
python dev_orchestrator/roadmap_supervisor.py once
python dev_orchestrator/roadmap_supervisor.py run
python dev_orchestrator/roadmap_supervisor.py stop
```

`once` returns `SUPERVISOR_READY_AGENT_COMMAND_REQUIRED` when no supported CLI is configured. Configure `agent_command` explicitly in `roadmap_supervisor.json` only after verifying the installed CLI accepts the prompt on stdin. The supervisor preserves the known unstaged `redme.txt` deletion and never pushes.
# Supervisor status checkpoint

The external supervisor is implemented and tested. Two fake-agent autonomy tests cover status/configuration handling and the required repeated-invocation behavior. `codex` and `opencode` binaries are detectable, but no supported prompt command template is configured; therefore the real smoke test returns `SUPERVISOR_READY_AGENT_COMMAND_REQUIRED` and no autonomous run is started. MotorSim remains at P5-B P5B-04.
