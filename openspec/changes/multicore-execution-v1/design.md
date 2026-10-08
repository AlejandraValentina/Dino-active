## Contexto
MotorSim ejecuta campañas de simulación 1D/0D validadas. El solver es secuencial y determinista. El paralelismo debe ser a nivel de trabajo (RPM, configuraciones) usando procesos, no threads del solver.

## Decisiones

### Modelo de ejecución
`multiprocessing.ProcessPoolExecutor` sobre `ThreadPoolExecutor` para trabajos completos, pues cada job es CPU-bound y requiere memoria independiente. Cada proceso tiene solver, memoria, configuración inmutable y directorio de evidencia propio. No compartir estados mutables.

### Detección automática
Físicos preferidos (`psutil.cpu_count(logical=False)` si disponible, fallback `os.cpu_count`). Política conservadora:

- ≤2 →1, 3–4→2, 5–6→3, 7–8→4, 9–12→6, >12→min(8, floor(physical*0.5))

Para i5-10400 (6c/12t) →3 workers. No usar todos los cores automáticamente; reservar para Windows/UI/filesystem/postproceso. Manual permite 1..6.

### Aislamiento científico
`workers=1` vs `workers=N` deben dar resultados idénticos (CFL, malla, tolerancias idénticas). Solo cambia scheduling. Cada job tiene ID determinista (ej. `RPM_6000`), registra `job_id, worker_id, config hash, solver hash, input hash, backend, timestamps, runtime, terminal state`. Orden de finalización no altera resultado final.

### Evidencia aislada
`campaign/jobs/<job_id>/` por proceso; el scheduler solo agrega metadatos/resúmenes al finalizar, sin escrituras JSON concurrentes sobre archivo común.

### Warm-start
Dos tipos: `INDEPENDENT` y `DEPENDENT_CHAIN`. Chains secuenciales internamente, chains en paralelo. Para RPM sweeps, construir chains preservando proximidad RPM (zona baja/media/alta) y comparar contra campaña secuencial.

### Memory guard
Antes de lanzar workers, estimar `estimated_memory_per_job` y verificar `estimated*jobs + reserve(25% RAM) ≤ total`. No iniciar más procesos si supera presupuesto. Reserva conservadora 25% para sistema/UI.

### Benchmark
Medir 1–4 workers en i5-10400 con trabajos idénticos: runtime individual, total, CPU, RAM, speedup `sequential/parallel`, eficiencia `speedup/workers`. AUTO se elige por throughput total, no por job individual.

## Alternativas descartadas
- `parallel=True` en Numba: fuera de alcance, altera solver.
- Threads: GIL limita CPU-bound.
- Compartir arrays: riesgo de condiciones de carrera y no determinismo.
- GPU: no contemplada.

## Riesgos
- Overhead de procesos y filesystem si jobs muy cortos → mitigado con jobs de duración representativa y prealocación.
- Memoria: guard y límite de 8 workers evitan OOM.
- Cancelación: debe preservar resultados completados.

## Capas
Fase A: solo `dev_orchestrator` (este cambio). Fase B: P8 sweeps con chains. Fase C: Qt config `Trabajos simultáneos` con persistencia.
