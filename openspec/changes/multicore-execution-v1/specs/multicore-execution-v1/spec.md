## ADDED Requirements

### Requirement: Ejecución paralela a nivel de trabajo
El scheduler SHALL ejecutar trabajos científicamente independientes en procesos separados usando `ProcessPoolExecutor`, sin modificar el solver interno. Cada worker SHALL tener solver y memoria independientes y configuración inmutable.

#### Scenario: Jobs independientes en paralelo
- **WHEN** se lanza una campaña con N jobs independientes y workers=3
- **THEN** los 3 workers ejecutan en paralelo, cada uno con directorio `campaign/jobs/<job_id>/` aislado y el scheduler agrega solo metadatos al final.

### Requirement: Detección automática conservadora
El sistema SHALL detectar núcleos físicos y aplicar la política: ≤2→1, 3–4→2, 5–6→3, 7–8→4, 9–12→6, >12→min(8,floor(physical*0.5)). Para i5-10400 (6) SHALL ser 3. No SHALL usar todos los cores automáticamente.

#### Scenario: Auto en i5-10400
- **WHEN** `workers=Automatic` en máquina 6 cores
- **THEN** `workers=3` y el usuario puede seleccionar manualmente 1..6.

### Requirement: Aislamiento científico y determinismo
Un job con `workers=1` SHALL ser científicamente equivalente al mismo job con `workers=N` (CFL, malla, tolerancias, física idénticas). Cada job SHALL tener ID determinista y registrar `job_id, worker_id, config hash, solver hash, input hash, backend, timestamps, runtime, terminal state`.

#### Scenario: Equivalencia 1 vs N
- **WHEN** se ejecuta la misma campaña con workers=1 y workers=3
- **THEN** todos los resultados científicos son idénticos y el scheduler reporta `MULTICORE_SCHEDULER_EQUIVALENCE_PASS`.

### Requirement: Evidencia aislada y estados de job
Cada job SHALL escribir solo en su `campaign/jobs/<job_id>/`. Estados posibles: PENDING,RUNNING,PASS,FAILED,CANCELLED,BLOCKED. El fallo de un job SHALL NOT eliminar resultados de los demás.

#### Scenario: Escritura aislada
- **WHEN** 4 workers escriben concurrentemente
- **THEN** no hay colisión en archivo común y cada `jobs/<id>/result.json` es válido.

### Requirement: Cancelación y memory guard
El scheduler SHALL soportar `Cancel all/pending/individual` preservando resultados completados, y SHALL respetar memory guard (estimación + reserva 25% RAM) sin iniciar workers si supera presupuesto.

#### Scenario: Cancel pending
- **WHEN** se cancela con 2 jobs completados y 3 pendientes
- **THEN** los 2 completados permanecen PASS y los 3 pasan a CANCELLED.

### Requirement: Warm-start chains y RPM sweeps
El scheduler SHALL soportar `INDEPENDENT` y `DEPENDENT_CHAIN` (ej. 3000→3500→4000). Chains secuenciales internamente, chains en paralelo, preservando proximidad RPM para warm-start. La estrategia SHALL compararse contra campaña secuencial.

#### Scenario: 3 chains en 3 workers
- **WHEN** sweep 3000–8500 con 3 workers
- **THEN** worker1 3000→3500→4000, worker2 5000→5500→6000, worker3 7000→7500→8000, cada chain secuencial y chains paralelas.

### Requirement: Benchmark y performance evidence
Toda campaña paralela SHALL registrar `sequential_estimated_seconds, parallel_wall_seconds, worker_count, speedup, efficiency` donde `speedup=sequential/parallel` y `efficiency=speedup/workers`, sin prometer escalado lineal, y SHALL benchmark 1–4 workers en i5-10400.

#### Scenario: Benchmark 1–4
- **WHEN** se benchmarkean 4 configuraciones con trabajos idénticos
- **THEN** se reportan runtimes, CPU, RAM y se elige AUTO por throughput total.

### Requirement: Restricciones
El cambio SHALL NOT activar `parallel=True` en Numba, compartir arrays, alterar tolerancias/periodicidad, usar GPU, ni iniciar todos los logical threads automáticamente.

#### Scenario: Verificación de restricción
- **WHEN** se inspecciona `exhaust_numba.py`
- **THEN** `parallel=False` permanece y no hay `prange`.
