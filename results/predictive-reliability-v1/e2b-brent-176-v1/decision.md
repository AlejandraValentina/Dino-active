# E2 Brent a 176 celdas — resultado y cierre de autorización

## Decisión

**ACELERACIÓN SUFICIENTE NO DEMOSTRADA; E1.3 NO SE REANUDA.** Brent y bisección
produjeron checkpoints equivalentes dentro de la tolerancia en los ciclos 38 y
39, con conservación aceptada. En el único ciclo completo con tiempos de pared
comparables, el ahorro fue 1.317x, por debajo del objetivo práctico de 2x. El
brazo Brent no completó el ciclo 40 dentro del máximo acumulado autorizado; por
ello no hay una comparación completa de tres ciclos ni evidencia para atribuir
al solver una aceleración mayor.

El coste mínimo de E1.3 sigue sin demostrarse dentro de sus 230.1685 s de solver
restantes. Los tiempos de pared Brent observados (87.03 y 87.17 s/ciclo) dan una
proyección de al menos 261.3 s para tres ciclos antes de margen, pero pared y
tiempo de solver no son intercambiables. El contador solver de este runner no
incluyó las propuestas rechazadas; su tiempo solver reportado no sirve para
probar que E1.3 cabe. Se mantiene bloqueada. No se consumió presupuesto E1.3.

## Entradas y preflight

- Configuración preservada, 176 celdas: SHA-256
  `4e8c01987424c0dae3b12a3af456dcbb951e43a992b2278f539bafdedf56ad73`.
- Checkpoint absoluto de ciclo 37, 13,320 grados: SHA-256
  `5a7ae79230c251d5b277238ef79e5e3ee050d59304c186e4d913c6f9a744085a`.
- Restauración/serialización del checkpoint de ciclo 37: exacta. El recibo
  original está clasificado `TRANSIENT_AT_BUDGET`.
- Preflight de almacenamiento: PASS, reserva 2 GiB y 128 MiB estimados por
  intento. Artefactos externos preservados bajo
  `DINO_ARTIFACT_ROOT/predictive-reliability-v1/e2b-brent-176-v1/`.
- El checkpoint fue generado antes de incorporar Brent. Ambos brazos usaron el
  mismo estado guardado y el código actual, con la selección del solver como
  única diferencia de ejecución. Las identidades de dependencias quedan
  registradas en los preflights y recibos.

## Ejecución y evidencia

Se conservaron tres intentos, sin borrar ni reemplazar sus resultados:

1. 115.4385 s: bisección alcanzó el ciclo 38, pero el runner no había creado su
   subdirectorio y falló al guardar el checkpoint.
2. 116.6084 s acumulados en el segundo intento: bisección volvió a ciclo 38 y
   guardó el checkpoint `f973c4a4f7c433cb6a318fab72c6ee3e11f6112c85fb172df52dfd5a6e2a218f`.
   La verificación de restauración esperaba incorrectamente el ciclo 37. El
   checkpoint se preservó y luego se restauró exactamente.
3. El tercer intento reanudó bisección desde ese ciclo 38, completó los ciclos
   39 y 40, y completó Brent desde ciclo 37 hasta los ciclos 38 y 39. El guard
   detuvo Brent durante el ciclo 40.

El contador de presupuesto reportó 660.0125 s, usando 233 s conservadores para
los dos intentos anteriores. Sus tiempos medidos sumaron 232.0469 s; con el
tercer intento, la suma medida fue 659.0594 s. El guard detuvo el cálculo tras
un paso que cruzó su contador conservador por 0.0125 s. No se inició otro paso
después de alcanzar el límite; no se amplió la autorización.

Comparación de los checkpoints completos:

| Ciclo | Bisección, pared | Brent, pared | Razón Bisección/Brent | Equivalencia |
|---|---:|---:|---:|---|
| 38 | 116.608 s* | 87.033 s | 1.340x* | PASS |
| 39 | 114.785 s | 87.168 s | 1.317x | PASS |

`*` El tiempo de bisección del ciclo 38 incluye la invocación que falló al
escribir/verificar; no se usa para el dictamen de rendimiento. En ciclo 39, la
comparación de snapshots dio cero diferencias fuera de la tolerancia
`1e-10 + 1e-10*max(|a|,|b|)`. Los checkpoints completos 38 y 39 restauraron
exactamente. Los controles globales de masa, energía y especies pasaron en cada
ciclo completo guardado.

Los tiempos solver registrados por el runner suman solo llamadas aceptadas a
`engine.step`; no contabilizan el coste de propuestas rechazadas. Por eso se
conservan como diagnóstico no vinculante y se usa tiempo de pared para la
comparación práctica. No se buscó periodicidad, no se modificaron física,
solver, CFL ni tolerancias y no se evaluó GCI. El resultado de 176 no resuelve
la periodicidad de 88.

## Pruebas y cambios

- `python -m py_compile scripts/diagnostics/compare_root_solvers_176_v1.py`:
  PASS.
- `python -m pytest -q tests/test_compare_root_solvers_176_v1.py tests/test_e2b_local_candidate_v1.py`:
  9 PASS.
- Hash del runner usado por el tercer intento:
  `ed7c44dd183b642d1d8a67e1f0e7268701b3f58649457380380a8a6fecf20b90`.
- El runner de comparación es un harness local de esta medición, no una
  activación de Brent por defecto. Los artefactos externos y los dos intentos
  fallidos quedan intactos.

## E1.3 y datos experimentales

Brent permanece opt-in; no satisface el objetivo de 2x en la pareja completa
observable y no hay tiempo solver válido que pruebe que tres ciclos caben con
margen en el saldo E1.3. Mantener 176 en `TRANSIENT_AT_BUDGET`; 88 también sigue
sin periodicidad demostrada. No se afirma GCI ni capacidad predictiva.

El correo autorizado a McClay Library no se envió: no hay un conector de correo
instalado en esta sesión. Quedó preparado sin firma personal ni adjuntos en
`results/experimental-data-readiness-v1/cahoon-archive-request-ready-to-send.eml`.
El borrador solicita únicamente los datos documentales del MK.1 y los registros
del punto de 6000 RPM.

**Siguiente decisión:** conservar Brent como opt-in y E1.3 bloqueada. Para
avanzar la validación experimental, conectar un mecanismo de correo autorizado
o enviar el `.eml` preparado. No se recomienda ampliar cómputo para completar
la campaña E2 a 176 mientras la aceleración observada siga por debajo de 2x.
