# Periodicidad del motor integrado: causa y resolución acotada

## Decisión técnica

**Se obtuvo un punto periódico contractual A_original a9000RPM, en el ciclo104.** Los ciclos102,103 y104 pasan todas las comparaciones completas V2. El ejecutor paró automáticamente. Clasificación original, sin reinterpretar: `PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED`.

La causa principal es **A: transitorio largo de purga y acomodación térmica del escape inicial**, bajo el modelo discretizado existente. El procedimiento anterior de detener siempre a30ciclos interrumpía esa purga. No se identificó un defecto que requiriera modificar solver, transporte, fronteras o detector. La corrección aplicada fue continuar conservativamente el mismo punto desde su checkpoint, con horizonte suficiente y parada por el criterio ya existente. No se cambiaron ecuaciones, parámetros, umbrales ni estados iniciales; no se ejecutaron otras RPM o variantes.

## Evidencia que discrimina las causas

- El escape tiene31celdas y aproximadamente3,69L frente a125cc de cilindrada. Estaba inicializado con gas residual, sin quemados. En el ciclo30 conservaba1,014g de residual; el inventario total era2,089g y la salida40,283mg/revolución: una escala local de residencia de51,85revoluciones, frente a sólo30revoluciones ejecutadas. Esta estimación se documentó antes de continuar; no era una garantía de convergencia.
- Los57 incumplimientos del ciclo30 eran44fracciones de residual/quemados,8fracciones de aire,3masas de celda del escape y2inventarios globales. Presión y Mach del escape pasan continuamente desde el ciclo4; temperatura desde el15. Cilindro y trabajo pasan desde el6. Un cilindro aparentemente estable no significaba sistema global periódico.
- El residual del escape disminuyó:1,014g(c30),0,666g(c40),0,296g(c56),0,135g(c70),**0,01834g(c104)**. El frente pasó de la cámara de expansión a la salida; el máximo incumplimiento pasó de13,99veces el umbral(c30) a0,883(c104). No se borró ni mezcló artificialmente ninguna especie para acelerar la purga.
- La reducción offline reproduce exactamente todas las comparaciones almacenadas. El balance del escape coincide con las integrales de flujo: discrepancia máxima de masa3,27e-18kg y de especies2,17e-18kg/ciclo. La variación global de especies coincide con los intercambios y las fuentes de combustión, discrepancia máxima7,03e-18kg. No aparece acumulación artificial sin contabilizar.
- Las fronteras existentes permiten salida hacia presión ambiente y entrada inversa con composición explícita. La reserva de salida es aire puro, sin combustible ni fuente de residual. El transporte del residual es conservativo. La EOS mantiene R y gamma constantes: las etiquetas residual/quemado no cambian por sí mismas esas propiedades; el historial térmico y de carga se conserva. El ensanchamiento del frente está afectado por la discretización existente; no se ha medido aquí su error espacial.
- B/C no se sostienen como explicación principal de este punto: sin corregir fronteras ni numerics, el mismo estado evolucionó a tres comparaciones completas válidas. D no explica los fallos observados: las escalas y diferencias usadas coinciden con el contrato, y las magnitudes realmente cambiaban. No se demuestra que el detector cubra cualquier modelo futuro: sus campos P7 son cero bajo la combustión fuel-limited actual. Por eso también se contrastaron, fuera del gate, calor liberado, combustible quemado, carga atrapada y composición de ambas cámaras.

## Resultado transitorio frente al periódico contractual

| Magnitud | Ciclo30 | Ciclo104 |
|---|---:|---:|
| Trabajo indicado [J/rev] |34,06899|34,19344|
| Aire atrapado [mg] |29,58237|29,68748|
| Calor liberado [J/rev] |73,45563|73,71767|
| IMEP [bar] |2,73365|2,74363|
| Potencia indicada [kW] |5,11035|5,12902|
| Torque indicado [Nm] |5,42225|5,44205|
| Potencia al eje estimada [kW] |3,34304|3,36018|
| Torque al eje estimado [Nm] |3,54707|3,56526|

La potencia al eje es **4,506HP mecánicos**, condicionada al FMEP sintético explícito de85000Pa y al trabajo de bombeo del cárter, no una potencia experimental validada. En c104 el trabajo del cárter es−1,19884J/rev; la fricción resta10,59340J/rev. AFR suministrado11,5; atrapado7,62118; combustible quemado2,01690mg/rev. No se ajustó ningún parámetro para producir estos valores.

En los últimos5ciclos, el rango de trabajo fue0,000729J y el de aire atrapado0,000523mg. Entre103y104, la presión RMS cambió1,499Pa en cilindro,0,155Pa en entrada de escape y0,138Pa en su sección media. Calor y combustible quemado cambian4,23e-6en términos relativos; la mayor variación absoluta de fracción de especie en cilindro es1,82e-6. Estas comprobaciones complementan, sin reemplazar, el detector vigente.

Entre30y104, la presión RMS cambió1411Pa en cilindro y241Pa en entrada de escape. El trabajo cambió+0,12445J y la potencia al eje+17,14W. La diferencia A/B exploratoria a9000 era18,39W: **la deriva acumulada tiene el mismo orden que la diferencia entre escapes**. No corresponde promover esa diferencia histórica a mejora/pérdida estacionaria ni comparar A periódico con B transitorio como si fueran estados equivalentes.

## Integridad, conservación y costo

Se preservaron los30ciclos originales y se calcularon74adicionales en una sola invocación. Checkpoint final `next_cycle=105`. Restore final exacto, observables finales reconstruidos exactamente sin pasos físicos; historial, ledger de combustión y estados completos conservados. Los29hashes de implementación coinciden con el punto original. Las104grillas diagnósticas tienen720muestras únicas de0,5°, sin huecos ni duplicaciones; hashes verificados. La evidencia original no se sobrescribió.

Durante los104ciclos, los residuos relativos máximos registrados fueron3,59e-15(masa),3,78e-15(energía),1,32e-14(especies). El balance de energía entre ciclos, reconstruido de inventarios y ledger, difiere como máximo1,65e-11J. Son verificaciones de consistencia sobre diagnósticos del productor; **no hubo replay ni auditoría independiente nueva**.

La continuación consumió490,325s de ejecutor y490,953s incluyendo su lanzador registrado, dentro de600s;434,019s fueron avance del solver,28,680s procesamiento y27,626s otros costos. Captura de diccionarios2,364s incluida dentro del tiempo de solver. CPU463,141s. Los ciclos nuevos tardaron6,023–6,824s cada uno; memoria observada de105,75a136,16MiB, cap512MiB. Cero rechazos CFL. El costo acumulado de los dos productores fue710,599s para104ciclos, equivalentes a0,69333s físicos. No se extrapola esto como costo medido de una curva completa.

## Qué queda para curvas estacionarias utilizables

El bloqueo de existencia de una solución periódica **queda resuelto para A9000 con esta malla y este modelo**. El residual inicial todavía no es exactamente cero: el resultado cumple tolerancias finitas, no igualdad matemática de estados ni ausencia absoluta de deriva futura.

Las curvas Desktop históricas permanecen exploratorias. Para convertirlas, corresponde usar el coordinador/runner ya existente, con presupuestos basados en residencia y continuación de cada checkpoint compatible hasta periodicidad global; repetir únicamente lo necesario en cada punto. B9000 y las otrasRPM aún necesitan su propia demostración de periodicidad. No se autoriza ni lanza aquí ese trabajo. No hacen falta otro solver, nuevas tolerancias ni una campaña genérica de purga.

Persisten las limitaciones físicas previamente declaradas: independencia de malla no demostrada, EOS ideal con gamma constante, condiciones térmicas impuestas, láminas cuasiestáticas, conexiones de transferencia idealizadas, cierre de barrido parcial con fracción0,5 no identificada, mapa de válvula y fricción sintéticos, y ausencia de validación experimental. Periodicidad resuelve la contaminación transitoria; no elimina esos errores ni demuestra capacidad predictiva sobre pequeños cambios de escape.

## Evidencia reproducible

- `receipt.json`: evolución de104ciclos, balances, hashes y resultado final.
- `evolution.png`: inventarios, frente de composición, presión, temperatura y trabajo.
- `protocol.md`: hipótesis, discriminantes, presupuesto y parada congelados antes de ejecutar (commitsff12964,ea99b55).
- Artifact root externo: `DINO_ARTIFACT_ROOT/periodicity-blocker-v1-20261023`; subdirectorios `continuation-001` y `logs`. Checkpoint final SHA256 `60d825868d73ca289cd305c9c59c40e750eecddfd6f9d1a85f554f91bcfc97b7`; manifest `f00028e10d46b008000208c763daac312d9816082ec2f5f66d77225f5bd3577e`.
- Reducción offline: `scripts/diagnostics/analyze_periodicity_blocker_v1.py`, sin pasos del solver.

Pruebas/checks finales se registran en el receipt y en program-status. No push; sin modificaciones de UI, solver, detector, configuraciones ni artifacts históricos.

### Verificaciones finales

26 pruebas focales PASS. Regresión P4–P8:298 PASS,3SKIP y4warnings NumPy preexistentes. El primer intento, con `DINO_ARTIFACT_ROOT` sin configurar, tuvo3fallos de disponibilidad; se conservó ese log y se repitió contra el store existente, sin alterar artefactos ni tests. OpenSpec strict y program-status check PASS. Revisión de esta entrega: SELF_REVIEW; no se atribuye una revisión independiente. No se declara validación experimental ni se promueven las curvas históricas.
