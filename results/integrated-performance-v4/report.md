# DINO 2T Performance V4 — piloto de compilación HLLC

**Decisión: DESCARTAR la integración Numba en IntegratedEngine2T.** El microbenchmark acelera HLLC, pero la corrida completa no obtiene una mejora sostenida que justifique el coste de arranque y memoria. El solver y la baseline CRV1 permanecen sin cambios.

## Perfil que motivó el prototipo

Se reutilizaron los perfiles CPU de Performance V1 y V2, sin volver a perfilar ni repetir curvas:

- V1: HLLC acumuló 2,735 s en el ciclo perfilado (los árboles acumulados se solapan); EOS 2,513 s exclusivo, especies 2,129 s e integrador 3,465 s. La optimización de V1 redujo primero trabajo térmico redundante.
- V2, tres ciclos A/B9000: `hllc_flux` consumió 2,24–2,29 s exclusivos bajo `cProfile`, con 189.933 llamadas en A. Los tiempos perfilados no se mezclan con los tiempos sin profiler para proyectar speedup porque `cProfile` eleva el proceso aproximadamente cuatro veces. El perfil identificó HLLC como un componente repetido y aislable, pero no predijo su beneficio integral.

## Prototipo y método

Se probó el HLLC Numba serial ya existente en `motorsim/exhaust_numba.py`, desde un adaptador diagnóstico aislado. El adaptador convierte las tuplas de estado del solver a `float64` y traduce la salida al contrato de HLLC existente. No se cambió el módulo del solver, sus ecuaciones, tolerancias, el backend predeterminado ni la ruta de Desktop. Se mantuvo HLLC Python como referencia.

La comparación integral utilizó la misma configuración histórica A9000, SHA-256 `743a00de51aa4ca214afb5c84b790c1d642c92a4887fa0074bad3d76aa2c1a9c`, y exactamente tres ciclos en cada backend. Estado de ambos: `MAX_CYCLES_NONCONVERGED`, como corresponde a este límite corto. El JIT inicial se midió por separado.

## Mediciones

| Medida | Python | Numba HLLC | Resultado |
|---|---:|---:|---:|
| HLLC envuelto, 200.000 llamadas representativas | 1,8466 s | 0,5978 s | 3,09× en microbenchmark |
| Compilación inicial Numba | — | 1,7042 s | coste por proceso |
| Tres ciclos, solver | 11,1546 s | 9,9511 s | 1,12×; −10,8% |
| Tres ciclos, proceso medido sin JIT | 13,1778 s | 11,8399 s | 1,11×; −10,2% |
| Tres ciclos, proceso incluyendo JIT | 13,1778 s | 13,5442 s | 0,97×; 2,8% más lento |
| RSS pico | 101,71 MiB | 191,04 MiB | +89,33 MiB |

El microbenchmark repitió parejas admisibles de celdas adyacentes tomadas del checkpoint Python del ciclo 3. Incluye conversiones de entrada/salida del adaptador, pero no representa por sí solo la aceleración del solver. En esta simulación de tres ciclos, las 189.933 llamadas históricas no amortizan los 1,704 s de compilación inicial.

## Equivalencia física y checkpoints

- Los tres archivos `checkpoint-next-*.json` son idénticos byte por byte entre backends. Sus SHA-256 son, respectivamente, `0827182274804abb6fb0e6ca75caaaa434696b9f3262b9cd0b3d132656f5bbba`, `94d6fb104ca043a81356425f81a56748595473da838fa7f33c4d31bad40eccf1` y `c5fb436565fdb9d41032f7f9dc8ce6ccab2d86c5e071894e564054c5b66c4d4e`.
- Los diagnósticos de ciclo coinciden exactamente en todas las variables no temporales; las únicas diferencias son `wall_s` y `peak_rss_mib`.
- Trabajo por ciclo: −52,5140 / 67,1656 / 35,8271 J en ambos; calor de combustión: 15,7964 / 120,3027 / 78,6913 J en ambos; presión máxima: 4,69767 / 5,98058 / 4,74968 MPa en ambos.
- El ledger final de masa, especies y energía es idéntico. Residuos relativos: masa `5,51e−17`, especies `6,63e−16`, energía `7,40e−16`.
- Los checkpoints generados son idénticos, lo que conserva su formato y estado numérico; no se ejecutó una continuación adicional para respetar el límite de tres ciclos.

## Regresión, empaquetado y reproducibilidad

Regresión focalizada existente: **8 PASS** (`tests/test_gas1d_numba.py`, `tests/test_gas1d_fused_aliasing.py`, 1,05 s). El entorno de empaquetado Windows `.venv-build` no contiene NumPy ni Numba; la ruta TRIAL actual no puede usar este backend sin agregar dependencias de empaquetado, y no se hizo build.

El preflight de almacenamiento pasó antes de escribir, con estimación de 0,05 GiB en E: y reserva de 2 GiB. Las corridas y archivos brutos permanecen en `E:\Dino-artifacts\integrated-performance-v4\{python-A9000,numba-A9000}`. Cada directorio contiene manifest, tres diagnósticos, tres checkpoints y `v4-benchmark.json`. El ejecutable de benchmark está en `scripts/diagnostics/benchmark_integrated_numba_v4.py`.

**Conclusión:** conservar el HLLC Python como única ruta de IntegratedEngine2T. El prototipo compilado queda documentado para reproducibilidad, no se integra como candidato de producto: la aceleración integral fue 10–11% sin JIT, se volvió negativa al incluir compilación y casi duplicó RSS. La línea Performance V4 se cierra aquí; no se inicia otra investigación de rendimiento.
