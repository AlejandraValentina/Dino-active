# Allocation Audit — P4-PERF-01

**Fecha:** 2026-09-22
**Archivos analizados:** motorsim/exhaust_numpy.py, exhaust_numba.py, exhaust_batch.py, exhaust_fast.py, hybrid_fast.py

## Hallazgos

### np.empty / np.zeros
- `exhaust_numba.py:90` `np.empty((n,4))` y `np.zeros(n,int64)` para HLLC interior — por RHS, no prealocado (solver scalar reference, no usado en NUMBA_FUSED).
- `exhaust_numpy.py:31-37` fused buffers `w_buf, lf_buf, rf_buf, flux_interior_buf, speeds_interior_buf, codes_buf, bad_buf` **prealocados 1× fuera de RHS, reusados** — OK (R5).
- `exhaust_numpy.py:82,129` `flux=np.empty((n+1,4)); speeds=np.empty(n+1)` **dentro de RHS** cada llamada → 30k allocations/ciclo N250, 53k N400. Cada alloc 8–16KB → 480MB allocations/ciclo. Medido 1.8% wall.

### .copy()
- `exhaust1d.py:98,102` `z.copy()`, `external.copy()` en history/stages (11k entries/ciclo) → necesario para inmutabilidad, no hot.

### tolist()
- `exhaust_batch.py:72,89,90,96` y `exhaust_numpy.py:79,90,91,107,120` `tolist()` para port_flux y boundaries → conversión Python↔Numba necesaria (API espera tuple), overhead 1.5% wall.

### astype/concatenate/stack
- No en hot path critico.

## Preallocation

**Existente (conservado):** fused interior buffers (7 arrays) prealocados, sin aliasing (test `test_gas1d_fused_aliasing` verifica no aliasing, no contaminación SSP, workers aislados, reentrante).

**Propuesto descartado:** prealocar `flux, speeds` (n+1,4) global → ganancia <2% (<5% criterio) y aumenta complejidad (necesita manejo de exterior vs interior, thread safety). Revertido.

## Conclusión

Overhead allocations 1.8% no justifica optimización adicional. Mantener prealocación existente, documentar.

**Gate:** ALLOCATION_AUDIT_COMPLETE
