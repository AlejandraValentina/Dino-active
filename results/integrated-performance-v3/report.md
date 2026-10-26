# Performance V3 — resultado del piloto A9000 → A10000

**Decisión: PARTIAL; no integrar la inicialización en el coordinador RPM.** El piloto mostró una reducción grande de ciclos y tiempo, pero el estado periódico final no coincide con el A10000 histórico dentro de los umbrales observables existentes.

## Método y seguridad

Se usó el checkpoint periódico `ab-A-9000` (ciclo 104) con hashes anclados en `results/periodic-rpm-curves-v1/receipt.json`. El nuevo run `perfv3-warm-A10000-from-A9000-20261026` tuvo identidad propia, empezó en ciclo 0, reinició reloj, ledger, historial de combustión y detector, y utilizó las condiciones A10000 existentes. La transferencia conservó exactamente masa, energía y las cuatro especies; no se restauró el checkpoint a través de RPM.

El preflight final pasó en E: con 7,369,408,512 bytes libres, estimación de escritura de 1 GiB, reserva de 2 GiB y margen posterior estimado de 6,295,666,688 bytes. C: conservó aproximadamente 21.1 GiB libres. No se lanzó build ni campaña.

Una primera invocación terminó antes de solver por una discrepancia de binding entre la procedencia y sus diagnósticos. No creó `run.json`, resultado ni checkpoint. Se corrigió y se conservó el log; el segundo lanzamiento fue el único que avanzó el solver.

## Resultado medido

| Medida | A10000 histórico | Piloto warm start | Cambio |
|---|---:|---:|---:|
| Ciclos | 104 | 15 | −89 (−85.58%) |
| Tiempo workflow | 715.63 s | 61.59 s | −654.05 s (−91.39%) |
| Tiempo de solver del piloto | — | 53.49 s | — |
| RSS pico | 180.39 MiB histórico | 108 MiB | — |

El detector vigente aceptó `PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED` en el ciclo 15, con una racha de tres comparaciones. La conservación relativa del último ciclo fue masa `3.78e−16`, energía `4.96e−15` y especies `6.88e−16`. El resultado sigue siendo exploratorio y no auditado.

## Equivalencia con A10000 histórico

Los valores escalares de trabajo, potencia, torque, masas atrapadas, AFR, calor y presiones están cerca del histórico; por ejemplo, freno −0.354%, trabajo indicado −0.236%, aire atrapado −0.2003% y AFR −0.1024%. Sin embargo, aplicar de forma read-only las ecuaciones y umbrales observables de `REFERENCE_PERIODIC_CONVERGENCE_V2` a los registros de ciclo (sin reescribir hashes ni invocar el comparador estricto entre identidades distintas) dio **102 fallos de 413 observables**. Predominan masas y especies de celdas del escape: la diferencia absoluta de fracción de especie quemada alcanza 0.03357 frente al umbral 0.002. Los extremos de presión del escape también quedan fuera de la estrecha envolvente histórica de los ciclos 102–104.

Por tanto, el estado puede superar la periodicidad local entre ciclos y aun así conservar una composición de escape distinta del punto A10000 histórico. Esa diferencia impide demostrar equivalencia física con este único piloto. No se extendió la corrida ni se relajaron criterios.

## Implementación y regresión

La inicialización conservativa hash-bound está en `motorsim/periodic_initialization_v1.py`. Es una API explícita; el coordinador RPM no la utiliza automáticamente. Rechaza cambios de configuración no permitidos y estados dynamic-reed no soportados. La importación Desktop del resultado completado pasó su verificación de integridad.

Regresión: 40 pruebas focalizadas PASS en la primera integración; después de la corrección final de binding, las 4 pruebas de inicialización PASS. El preflight de almacenamiento pasó y el run terminó con checkpoint completo `next_cycle=16`; sus hashes están registrados en `pilot-summary.json`.

## Estado

No se integra el warm start al coordinador RPM. Se conserva el mecanismo experimental y la evidencia para análisis local; no se recomienda usar estos puntos para completar curvas automáticamente hasta resolver la diferencia de estado del escape dentro de una autorización posterior. No se ejecutó otra corrida, no se cambió el solver ni se modificó la baseline TRIAL.

Evidencias: `pilot-contract-v2.json`, `historical-reference-envelope.json`, `pilot-comparison.json`, `pilot-summary.json`, `transfer-review.json` y `checkpoint-stop-review.json`.
