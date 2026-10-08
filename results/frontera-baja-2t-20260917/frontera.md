# Frontera baja 2T — 17/09/2026

**LOW_RPM_FAILURE_MECHANISM_IDENTIFIED**. Ejemplo sintético Referencia, perfil B/100Pa, estado inicial independiente por RPM; sin warm-start ni cambios de solver. Dominio público 2500–3500 sin cambios.

## Tabla de frontera

| RPM | Estado | Ciclos completos | Motivo terminal | dt mínimo aceptado ° | Rechazos | W_C J | pmax Pa | Peor balance independiente % | Magnitudes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1500 | FAIL_MIN_STEP | 0 | paso mínimo: propuesta 0.00149401370936°, medio paso 0.000747006854679° a 182.147871870° | 0.002118121039 | 14 | — | — | — | — |
| 1750 | FAIL_MIN_STEP | 0 | paso mínimo: propuesta 0.00163008534791°, medio paso 0.000815042673953° a 366.458663744° | 0.001963342066 | 33 | — | — | — | — |
| 2000 | FAIL_NEGATIVE_FRESH | 5 | 8 rechazos consecutivos a 2272.789248620°: nonphysical, C a 2272.799592767 grados: F fuera de [0,m]: F=-9.523239929231602e-18, m=5.723536151636247e-05, E=inf | 0.00146750035 | 141 | 15.96071417 | 1281871.358 | 0.001369350407 | diagnostic_last_complete_cycle |
| 2250 | PASS | 11 | convergencia: tres ciclos consecutivos | 0.001316775503 | 252 | 15.88711098 | 1289143.321 | 0.001109984064 | accepted |
| 2500 | PASS | 10 | convergencia: tres ciclos consecutivos | 0.001037567735 | 197 | 16.2092918 | 1306559.768 | 0.0006649575645 | accepted |
| 2750 | PASS | 10 | convergencia: tres ciclos consecutivos | 0.001092356593 | 159 | 16.40461571 | 1320495.93 | 0.0006320049787 | accepted |
| 3000 | PASS | 10 | convergencia: tres ciclos consecutivos | 0.002348157245 | 191 | 16.49050751 | 1331530.846 | 0.0004459656622 | accepted |


Magnitudes diagnostic_last_complete_cycle: no aceptadas. dt mínimo en grados es el mínimo medio paso **aceptado**, no la propuesta que provocó la parada. Sin ciclo completo se usa —; estados parciales y balances parciales quedan en los JSON.

| RPM | Integración s | Wall s | Medios pasos aceptados | dt mínimo s | Máximo rechazos consecutivos | P indicada W | T indicado N·m |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1500 | 0.03100000042 | 0.03100000042 | 30 | 2.353467822e-07 | 5 | — | — |
| 1750 | 0.75 | 0.8600000003 | 1638 | 1.869849587e-07 | 5 | — | — |
| 2000 | 8.155999999 | 8.483999999 | 18014 | 1.222916959e-07 | 8 | 532.0238056 | 2.540226555 |
| 2250 | 15.625 | 15.922 | 33652 | 9.753892618e-08 | 5 | 595.7666619 | 2.528512244 |
| 2500 | 14.734 | 15 | 30342 | 6.917118233e-08 | 5 | 675.3871585 | 2.579788914 |
| 2750 | 13.859 | 14.109 | 30248 | 6.620342988e-08 | 4 | 751.8782202 | 2.61087568 |
| 3000 | 13.656 | 13.891 | 30050 | 1.304531803e-07 | 6 | 824.5253756 | 2.624545785 |


Wall por punto incluye preparación, integración y escritura de resultado/observación; no incluye escritura del índice campaign.json. Los tiempos incluyen observación y no constituyen un benchmark del solver sin instrumentación.

| RPM | Primera violación observada: ángulo ° | Ubicación y motivo |
| --- | --- | --- |
| 1500 | 182.1508599 | C a 182.150859897 grados: F fuera de [0,m]: F=-1.1680240322903648e-15, m=9.316923310771782e-05 |
| 1750 | 366.4766669 | I a 366.476666903 grados: F fuera de [0,m]: F=3.63683134959035e-05, m=3.636831349584725e-05 |
| 2000 | 183 | C a 183.000000000 grados: F fuera de [0,m]: F=-7.798989746792943e-11, m=9.293812436601701e-05 |
| 2250 | 183.2435016 | C a 183.243501583 grados: F fuera de [0,m]: F=-4.057793571494019e-15, m=9.313215400447501e-05 |
| 2500 | 183.75 | C a 183.750000000 grados: F fuera de [0,m]: F=-6.275004061437382e-11, m=9.293810486059244e-05 |
| 2750 | 382.6263363 | I a 382.626336349 grados: F fuera de [0,m]: F=3.631123955052849e-05, m=3.631123955039461e-05 |
| 3000 | 184.5 | C a 184.500000000 grados: F fuera de [0,m]: F=-4.1893184747513826e-11, m=9.29322737260007e-05 |


Primera significa orden de intentos, no menor ángulo: un rechazo puede ocurrir en una etapa futura y reintentarse con un paso menor. Una violación rechazada no implica fallo terminal; también aparece en puntos PASS, que la recuperan.

## Comparación de mecanismos

- 1000: error local C.F al invertir donante en transferencias internas, F_C=0; siguiente medio paso0,000706127° bajo mínimo.
- 1500: K4 da F_C=-1,168024e-15kg al mismo tipo de inversión K↔C; siguiente medio paso0,000747007° bajo mínimo.
- 1750: durante calor prescrito del cilindro, el CV afectado es I; F_I excede m_I por6,776264e-21kg en el último intento (un ulp). Siguiente medio paso0,000815043° bajo mínimo. Es el límite superior F≤m, no fresca negativa en C.
- 2000: primera negativa K4 a183°; negativa terminal K4 en ciclo6 al invertir C↔E con F_C base cero. Seis rechazos locales y dos físicos agotan el límite8.

## Decisión y límites

Menor RPM convergente ensayada:2250; mayor fallida:2000. Transición terminal monotónica en esta malla, mecanismos distintos. Frontera candidata >2000 y≤2250; no se han ensayado2050/2100/2150/2200 ni se infiere continuidad. 2500 sigue siendo un límite conservador razonable para este ejemplo/perfil: convergió de nuevo y deja margen respecto de2250, sin garantía para cualquier geometría.

Hay base técnica para una fase correctiva separada: estudiar positividad conservativa de las etapas de transporte y el cambio de donante interno, incluyendo F=0 y F=m; distinguir error de discretización del redondeo en1750. No basta tratar todo como un único problema de mínimo de paso. Comparar estrategias solo con autorización nueva; no se recomienda clipping silencioso ni relajar límites.

Integración siete puntos=66.811000s; incluyendo1000=66.827000s. Wall campaña=68.594000s. Los diagnósticos offline se ejecutaron después y no se suman como integración nueva.

1000/2000/3000 reproducen exactamente los campos científicos completos de faseA, incluidas trayectorias, muestras, RHS, rechazos y paradas; solo difieren tiempos. 3000 reproduce por transitividad y prueba histórica los resultados acreditados. No hay campaña alta/4T, UI, formatos, candidata ni aceptación manual nuevos.

Detalles: [1000](diagnostico-1000.md), [2000](diagnostico-2000.md), JSON de observación, replay y resultados originales junto a este archivo.
