# STANDARD_V1: primera ejecución real a 9000 RPM

## Resultado

**30 ciclos físicos completos; MAX_CYCLES_NONCONVERGED.** El punto se detuvo
por el límite de ciclos, no por tiempo, RAM, conservación o fallo terminal.
No se amplió ni repitió. No hay curva RPM ni potencia estacionaria validada.

Ejecución: commit `8868729`, un worker secuencial, IntegratedEngine2T directo,
44 celdas (31 escape), CFL máximo configurado 0.4. Configuración física sin
cambios respecto de la revisión: admisión 38×36 mm, AFR suministrado 11.5,
válvula sintética a medio recorrido. Las únicas modificaciones del JSON fueron
aclaraciones de provenance/limitaciones. SHA-256 del archivo definitivo:
`301ded4ca6df997a3207e99aef37ee5a2702c782d15aacd50cfec32993d0ed08`.

Autorización: mensaje del propietario para smoke breve y un punto exploratorio.
Límites registrados antes de ejecutar: smoke 5°/30 s; punto 30 ciclos/1800 s,
RSS máximo 3072 MiB. No replay, construcción de primarias ni auditoría
independiente. Las comprobaciones de conservación son internas del productor.

## Evolución medida

| Ciclo | Trabajo indicado J | Calor de combustión J | AFR atrapado |
|---:|---:|---:|---:|
| 1 | -52.659 | 12.529 | 11.500 |
| 2 | 53.029 | 96.150 | 9.936 |
| 3 | 30.006 | 68.329 | 9.278 |
| 5 | 30.064 | 65.805 | 8.759 |
| 10 | 29.631 | 64.679 | 8.504 |
| 20 | 29.248 | 64.064 | 8.472 |
| 30 | 29.099 | 63.837 | 8.470 |

El primer ciclo es un arranque desde la condición inicial, no una medida de
rendimiento. La combustión cruza el PMS: las integrales de cada vuelta incluyen
el final del evento anterior y el principio del siguiente. No se atribuye todo
el calor de una vuelta a la masa atrapada en esa misma vuelta.

En 29→30 el trabajo cambia 0.0298%, por debajo del límite V2 de 0.5%. Pero
**57 de 413 comprobaciones terminales todavía fallan**. El peor cambio es la
fracción residual de la celda 15 del escape: 0.02763, frente a 0.002 permitido
(13.81 veces el límite). La composición del escape continúa desplazando la
condición inicial. La mejora del trabajo no demuestra periodicidad del motor
completo, ni garantiza cuántos ciclos adicionales serían necesarios.

Se aplicó `compare_cycles_v2` existente sin alterar sus umbrales: cámaras,
conductos, especies, inventarios, flujos integrados y trabajo firmado. El
runner exige tres comparaciones satisfactorias y al menos diez ciclos para
observar periodo 1; no ocurrió. Este runner no identifica periodo 2 ni sustituye
una aceptación científica auditada. El cuadro aspiracional previo del protocolo
no se presenta como un detector implementado.

## Respiración y combustible: último ciclo

Masas en mg por vuelta; atrapadas en el **cierre exacto del escape a 272.0847°**,
sin interpolación. Flujos integrados con las dos etapas SSPRK existentes.

| Ubicación / significado | Aire mg | Combustible mg |
|---|---:|---:|
| Entrada exterior, admisión bruta | 35.474 | 3.085 |
| Retorno hacia la frontera de admisión | 3.345 | 0.291 |
| Paso positivo desde admisión al cárter | 32.129 | 2.794 |
| Atrapado en cilindro al cierre de escape | 25.704 | 3.035 |
| Expulsado sin quemar, cilindro → escape | 6.673 | 1.068 |

Además quedaron 44.976 mg de productos quemados y aproximadamente 0.000031 mg
de la especie residual inicial en el cilindro al cierre. Masa total atrapada:
73.714 mg; fracción de productos quemados aproximadamente 61.0%.

**Diagnóstico: el motor renueva carga, pero el llenado fresco es bajo.** Los
34.923 mg de mezcla que entran al cárter equivalen al 23.8% de los 146.666 mg
de mezcla a 101325 Pa/300 K que ocuparían la cilindrada. Es una comparación de
masa de referencia, no una eficiencia de carga identificada. Los transfers
entregaron al cilindro 32.419 mg de aire en flujo positivo; existe transporte
real, no sólo presión en un recipiente cerrado.

El AFR atrapado de 8.47 es más rico que el 11.5 suministrado. La química consume
aire y deja combustible sin quemar, que puede permanecer o salir por el escape.
Se queman 1.747 mg/vuelta, liberando 63.837 J con el surrogate y eficiencia
0.85 ya configurados. La cantidad es compatible con la limitación de oxígeno
del inventario de aire: no se fuerza la quema de los 3.035 mg atrapados.
No hay evaporación, película de combustible ni química detallada de mezcla rica.

No se identifican TE/CE/SE ni short-circuit causal mediante cocientes de estas
masas: hay almacenamiento, transitorios y mezcla de generaciones de carga.

## Restricciones de flujo

En el último ciclo la depresión favorable a admisión ocupa 2.352 ms de los
6.667 ms de la vuelta. **En todas esas etapas el mínimo de área corresponde a
las láminas cuasiestáticas**, y por esa clasificación pasan los 34.923 mg de
mezcla aspirada. No se observó que la ventana híbrida fuese un cuello adicional
durante depresión favorable. Esto no demuestra equivalencia con un reed real
ni permite extrapolar a otros regímenes.

| Área efectiva máxima, ciclo 30 | mm² |
|---|---:|
| Ventana sintética de admisión | 1162.8 |
| Admisión realmente utilizada / láminas | 954.1 |
| Conducto de admisión, sección geométrica | 1134.1 |
| Transfer primario | 256.0 |
| Transfer secundario | 256.0 |
| Boost | 174.1 |
| Escape con válvula a 0.5 | 800.7 |

En los transfers, el área de puerto es inferior a las secciones de conducto
en ambos extremos. La integral `both_end_port_limited.time_s` incluye el cierre
completo: **no significa que haya flujo durante toda la vuelta**. El doble
estrangulamiento está presente en el modelo y podría condicionar el llenado;
esta corrida no separa su efecto del de las láminas, presiones y barrido.
No se atribuye causalidad cuantitativa sin un contraste adicional autorizado.

## Presiones y trabajo

Extremos de las etapas SSPRK del ciclo 30, presión absoluta:

| Región | Mínimo bar | Máximo bar |
|---|---:|---:|
| Cilindro | 1.036 | 45.600 |
| Cárter | 0.904 | 1.381 |
| Entrada del escape | 0.980 | 1.099 |
| Mitad del escape | 1.040 | 1.062 |

El máximo de cilindro ocurre aproximadamente a 7° ATDC. Las series compactas
guardan estados aceptados cada ~0.5°, sin reconstruir ondas por interpolación.
La presión del escape es modesta en este ensayo; no demuestra una expansión
sintonizada con fuerte recuperación de carga.

Balance de trabajo, último ciclo:

- Trabajo positivo del cilindro: 83.852 J; negativo: -54.753 J.
- Trabajo indicado neto: **29.099 J**, IMEP **233.49 kPa**.
- Trabajo del gas del cárter: **-1.187 J**; costo de bombeo neto correspondiente.
- Trabajo neto de ambos gases sobre el pistón: **27.913 J**.
- Potencia indicada transitoria equivalente: **4.365 kW / 5.853 HP**.
- Torque indicado equivalente: **4.631 N·m**.

No se resta el bombeo del cárter dos veces. La compresión negativa del cilindro
no es toda una pérdida: forma parte del lazo indicado y se recupera parcialmente
durante la expansión.

Balance de energía del cilindro, último ciclo:

- Calor químico: +63.837 J.
- Trabajo indicado: -29.099 J.
- Calor hacia paredes de cilindro/culata/pistón: -21.495 J.
- Entalpía neta saliente inferida del balance: -13.251 J.
- Cambio de energía interna entre PMS consecutivos: -0.00845 J.

La entalpía anterior es una inferencia por cierre del balance, no una medición
independiente de caudales energéticos. Las paredes reciben aproximadamente
33.7% del calor liberado en esta vuelta bajo los coeficientes configurados.

### Fricción: hipótesis separada, no medida

La configuración no aportaba un modelo de fricción. La invocación seleccionó
explícitamente `--mechanical-loss standard-v1`: modelo existente de FMEP
85000 Pa, `SYNTHETIC_ASSUMPTION`, sólo postproceso, sin cambiar el solver.

Implica 10.593 J/vuelta y 1.589 kW de pérdidas mecánicas supuestas. Tras el
bombeo y esa fricción: **2.598 kW / 3.484 HP y 2.756 N·m**. Son estimaciones
transitorias dependientes de una fricción sintética, **no potencia/torque de
freno definitivos del motor de referencia**. No se ajustó ningún valor para
aproximarse a una potencia objetivo.

## Costo, estabilidad e integridad

- Smoke: 5° completos, 0.762 s dentro del proceso / 1.078 s con logger;
  27.57 MiB. No constituye un ciclo ni se mezcló con la corrida principal.
- Punto: **190.516 s** dentro del runner, **190.906 s** con lanzamiento/logger.
- 30 vueltas representan 0.2 s físicos; costo global medio **6.351 s/vuelta**.
- Bucle de cada ciclo, antes de escritura final: 5.929–6.226 s.
- Tiempo en `engine.step`, incluidos intentos rechazados: **172.143 s**.
- Construcción explícita del diccionario de trace, incluida en lo anterior:
  1.235 s. Restante 170.908 s no es física pura: incluye controles y las
  estructuras internas necesarias para capturar los flujos SSPRK.
- Procesamiento diagnóstico y checkpoints medido: **10.387 s**.
- Inicialización, control e I/O restante: **7.986 s**. El manifiesto terminal
  y el lanzamiento completan la diferencia con el tiempo externo del logger.
- CPU del proceso: 180.453 s; un worker. Pico RSS **110.566 MiB**.
- 21637 pasos aceptados; **0 rechazos CFL**. Hubo **8 rechazos por
  `rho/p/Y inadmissible`, todos en el arranque del ciclo 1**, resueltos por la
  reducción local del paso existente. No se relajó CFL ni la admisibilidad.
- CFL aceptado máximo de toda la corrida: **0.26767**, límite configurado 0.4.
- Paso efectivo del ciclo 30: **1.569–9.259 microsegundos**; el mínimo también
  está condicionado por la alineación exacta a eventos.
- Máximos residuos relativos acumulados en cierres de ciclo: masa 1.62e-15,
  energía 4.93e-15, especies 2.02e-15; límite 1e-8.
- 30 checkpoints nativos restaurados exactamente, sin pasos físicos; último
  `next_cycle=31`. Hash terminal, configuración, runner y solver coinciden.
- Ciclos 1–30 contiguos; cierres exactos capturados; sin duplicación.
- **Auditoría independiente: NOT_PERFORMED**, por alcance exploratorio.

Este costo mide un punto de 30 ciclos no convergido; no estima el tiempo hasta
periodicidad ni constituye un speedup científico frente al pipeline auditado.
El runner persiste checkpoints nativos, pero no incluye un CLI de reanudación
ni lanza continuaciones automáticamente.

## Evidencia y verificaciones

Artifacts externos: `E:/Dino-artifacts/standard-v1-9000-20261022/`.
`point/manifest.json` conserva límites, bindings, métricas y clasificación;
`cycle-NNN-diagnostics.json` incluye muestras e integrales;
`checkpoint-next-NNN.json` conserva los estados nativos.
`storage-verification.json` contiene el inventario SHA-256 y los checks de
restauración sin solver. Gráficos: `point/evolution.png` y
`point/last-cycle-pressure-flow.png`.

Resumen durable: [receipt](standard-v1-9000-receipt.json) y
[evolución completa CSV](standard-v1-9000-cycles.csv).

Verificación: 22 tests focales PASS (runner, mecánica y válvula); builder
`--check` PASS; OpenSpec strict del objetivo PASS; program-status check PASS
con advertencia preexistente de dos tareas READY ajenas al alcance. Revisión
de implementación y evidencia: SELF_REVIEW. No se declara revisión independiente.

## Conclusión física

**Se demostró ejecución funcional y trabajo indicado positivo explicable.**
La combustión aporta energía, el cilindro produce trabajo, el cárter consume
trabajo de bombeo y el balance cierra con calor a paredes y entalpía neta.
El costo y la memoria ya permiten observar varias decenas de ciclos en una
invocación breve.

**No se demostró buen llenado ni régimen periódico.** La renovación fresca es
baja, permanece una fracción alta de productos quemados y la mezcla atrapada
se enriquece por combustible remanente. En esta trayectoria gobierna el área
cuasiestática de las láminas; no se observó limitación adicional de la ventana
durante succión favorable. La influencia cuantitativa de rigidez sintética,
doble restricción de transfers, barrido 0D y expansión no se puede separar con
este único punto. Son hipótesis de diagnóstico, no defectos ya demostrados.

Las magnitudes locales se aproximan a valores repetibles, mientras el escape
sigue en transitorio. El ensayo queda cerrado en su límite autorizado, sin
ajustes, extensión, nueva RPM ni barrido. Gate científico general REVIEW;
validación experimental NOT_PERFORMED; capacidad predictiva NOT_CLAIMED.
