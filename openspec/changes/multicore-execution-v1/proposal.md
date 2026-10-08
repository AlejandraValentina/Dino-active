## Why
MotorSim necesita aprovechar CPUs multinúcleo en campañas científicamente independientes (RPM, geometrías, verificaciones) sin modificar el solver interno ni alterar resultados. El mecanismo debe ser usable primero en herramientas de desarrollo y luego en la aplicación Qt.

## What Changes
Introduce scheduler paralelo a nivel de trabajo usando procesos independientes (ProcessPoolExecutor), con detección automática de workers, aislamiento científico, evidencia aislada por job, cancelación, memory guard, warm-start chains y benchmark del scheduler. Fase A solo en `dev_orchestrator`, sin UI.

## Capabilities
### New Capabilities
- `multicore-execution-v1`: ejecución paralela de trabajos independientes y chains dependientes con determinismo y equivalencia científica.
### Modified Capabilities
Ninguna capacidad pública existente modificada en Fase A.

## Impact
Reutiliza solver validado sin cambios. Añade infraestructura transversal utilizable desde P5/P6 y preparada para P8/productización. No activa `parallel=True` en Numba, no comparte arrays, no altera tolerancias ni periodicidad.
