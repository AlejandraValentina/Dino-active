# Tareas propuestas

- [x] SDR-PERF-PROFILE: Perfil acotado de fixture de motor y workflow con checkpoint/restart; hotspots de avance, audit, deepcopy, JSON y persistencia registrados. No se seleccionó optimización del solver sin comparación canónica end-to-end. Receipt: `results/dino-stage1-solver-diagnostic-recovery/performance/performance-profile.json`.
- [x] SDR-PERIODICITY-MESH: Detector V2 sí ejecutado; cuatro ciclos sin aceptación antes de timeout. Malla continúa `NOT_ESTABLISHED`; protocolo multi-resolución diseñado, no ejecutado. `mesh-protocol.md`; `science/periodicity-mesh-assessment.json`.
- [x] SDR-IMPL2-IDENTITY: Única diferencia entre 24 fuentes es `motorsim.integrated_2t.py`; se preparó identidad derivada candidata, sin modificar preregistro ni autorizar campaña. Receipt: `results/dino-stage1-solver-diagnostic-recovery/identity/impl2-derivative-identity-candidate.json`.
- [x] SDR-WINDOWS-HARDENING: `run_logged.py` gestiona UTF-8 de hijo y consola cp1252; tests CLI/directo 2 PASS. Pruebas de timeout, límite de memoria cooperativo, cancelación y checkpoint/resume incluidas en la suite acotada.
