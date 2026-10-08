# P1-R5E — evidencia completa y revisión científica R5

Adquisición de evidencia separada de adopción contractual. Dos integraciones
nuevas, solver y contratos P1–R4 intactos. Propuesta exacta en r5-candidate.md;
revisión independiente científica PASS registrada en scientific-review.json. Las tablas se calculan
desde finales, sin usar los estados parciales de300s.

## Matriz acústica 3x3
A_ref: pico de primitivas de integrales conservadas de referencia T03.
Eabs=|A-A_ref|, Erel=Eabs/A_ref; E_A=Eabs/10Pa.

| N | CFL | A Pa | A_ref Pa | Eabs Pa | Erel | E_A |
|---|---|---|---|---|---|---|
| 400 | 0.2 | 9.14443393229 | 9.98699441143 | 0.842560479141 | 0.0843657705642 | 0.0842560479141 |
| 400 | 0.4 | 9.1483281148 | 9.98699441143 | 0.838666296637 | 0.0839758451929 | 0.0838666296637 |
| 400 | 0.6 | 9.14993965974 | 9.98699441143 | 0.837054751697 | 0.0838144808351 | 0.0837054751697 |
| 800 | 0.2 | 9.62864623751 | 9.99674574511 | 0.368099507599 | 0.0368219335556 | 0.0368099507599 |
| 800 | 0.4 | 9.63078348491 | 9.99674574511 | 0.365962260199 | 0.0366081392415 | 0.0365962260199 |
| 800 | 0.6 | 9.63281855416 | 9.99674574511 | 0.363927190949 | 0.0364045660686 | 0.0363927190949 |
| 1600 | 0.2 | 9.84430525461 | 9.99918625753 | 0.15488100292 | 0.0154893607271 | 0.015488100292 |
| 1600 | 0.4 | 9.84536868558 | 9.99918625753 | 0.153817571947 | 0.0153830089755 | 0.0153817571947 |
| 1600 | 0.6 | 9.8463535082 | 9.99918625753 | 0.152832749329 | 0.0152845186991 | 0.0152832749329 |

| Pareja CFL | S400 | S800 | S1600 |
|---|---|---|---|
| 0.2_0.4 | 0.000389418250415 | 0.000213724740024 | 0.000106343097286 |
| 0.4_0.6 | 0.000161154493981 | 0.000203506925027 | 9.84822618193e-05 |
| 0.2_0.6 | 0.000550572744396 | 0.000417231665051 | 0.000204825359106 |

## Perfiles, fase y estabilidad

| N | CFL | L1 p | L2 p | Error velocidad relativo | Error posición m |
|---|---|---|---|---|---|
| 400 | 0.2 | 0.00341506124908 | 0.0119844783495 | 3.31494586006e-05 | 1.49172563702e-05 |
| 400 | 0.4 | 0.00347541441305 | 0.0121360003189 | 3.99537615174e-05 | 1.79791926828e-05 |
| 400 | 0.6 | 0.003707094851 | 0.012619885546 | 0.000105221771474 | -4.73497971631e-05 |
| 800 | 0.2 | 0.00120798645828 | 0.00460879589863 | 3.72688864354e-05 | 1.6770998896e-05 |
| 800 | 0.4 | 0.00121933551006 | 0.00464874454574 | 3.81443152386e-05 | 1.71649418574e-05 |
| 800 | 0.6 | 0.00125128513104 | 0.00471622058713 | 2.94522145396e-05 | 1.32534965429e-05 |
| 1600 | 0.2 | 0.000350750888028 | 0.00150683269947 | 3.09070269449e-05 | 1.39081621252e-05 |
| 1600 | 0.4 | 0.000355799198152 | 0.00152029670109 | 3.08827981534e-05 | 1.3897259169e-05 |
| 1600 | 0.6 | 0.000376836004091 | 0.00154533622456 | 3.30278779008e-05 | 1.48625450554e-05 |

| N | CFL | Máximo balance paso | Máximo balance etapa | Admisible | HLLC | HLLE | Tiempo s |
|---|---|---|---|---|---|---|---|
| 400 | 0.2 | 3.11150297412e-16 | 1.59385508251e-16 | True | 718998 | 0 | 18.750 |
| 400 | 0.4 | 2.2948451126e-16 | 1.5177958122e-16 | True | 359898 | 0 | 9.219 |
| 400 | 0.6 | 2.03413105613e-16 | 1.48542315889e-16 | True | 240198 | 0 | 6.125 |
| 800 | 0.2 | 2.6519347554e-16 | 1.55903605274e-16 | True | 2877998 | 0 | 74.203 |
| 800 | 0.4 | 2.39194227358e-16 | 1.55744243832e-16 | True | 1439798 | 0 | 37.515 |
| 800 | 0.6 | 1.75121884091e-16 | 1.52746131192e-16 | True | 1197701 | 0 | 30.469 |
| 1600 | 0.2 | 4.65742228849e-16 | 1.59160444382e-16 | True | 11515998 | 0 | 304.844 |
| 1600 | 0.4 | 4.91126417582e-16 | 1.59498039492e-16 | True | 5759598 | 0 | 153.578 |
| 1600 | 0.6 | 1.22263010731e-16 | 1.57088637639e-16 | True | 4838574 | 0 | 125.234 |

Los errores E_A, L1p y L2p disminuyen en ambas transiciones para cada CFL.
La fase no es monótona en todos los casos: CFL.2 aumenta de400 a800 y .6
cambia de signo; no se oculta. Todos los errores relativos de velocidad están
entre2.945e-5 y1.053e-4, dentro del límite original1e-2; sus valores finos
están cerca de3.1e-5–3.3e-5 y no hay separación sistemática entre CFL.
No se impone una nueva monotonía de fase. La referencia es acústica lineal
de pequeña amplitud, no una solución exacta del Euler no lineal a amplitud finita.

La sensibilidad .4/.6 crece400→800 pero cae800→1600. Las otras dos parejas
disminuyen en ambas transiciones; las tres son menores en1600 que400.
Esto, junto con los errores de perfil/pico y conservación/admisibilidad,
es compatible con régimen preasintótico, no demuestra causalidad ni un límite
asintótico universal. No se elimina N800 ni se agrega una cota ajustada a datos.

## Fundamento matemático del delta propuesto
SSP preserva una propiedad convexa de estabilidad del paso Euler, bajo sus
hipótesis, a discretización espacial fija. No ordena diferencias entre CFL
sobre distintas mallas. Fuente primaria: Gottlieb, Shu y Tadmor2001, §2:
https://www.cfm.brown.edu/people/sg/SSPsiamreview.pdf .

Contraejemplo lógico independiente, no ajuste al solver: e_a=h² y e_b=h³
convergen monótonamente; para h=.9,.45,.225, su diferencia absoluta vale
.081,.111375,.039234375. Por desigualdad triangular,
|A_a-A_b|<=|A_a-A_ref|+|A_b-A_ref|: convergencia individual a referencia
común implica convergencia de diferencias, no monotonía en cada transición.
Minmod cambia de rama/anula pendientes en extremos y el máximo celular
es sensible a fase/malla; son mecanismos plausibles, no una identificación
causal demostrada. No se afirma TVD universal de este Euler/HLLC.

El cambio propuesto retira explícitamente la garantía transición por transición
para segundo orden; NO es equivalente a R4. Conserva error de referencia
estrictamente decreciente por CFL, todos los gates padre y S_fina<S_gruesa
para cada pareja. Los perfiles corroboran que convergencia del pico no está
ocultando deterioro del perfil. FIRST_ORDER mantiene R4 íntegro.

## T10 y adquisición
- order_100_200_density_L1: 1.86132927197.
- order_100_200_fresh_L1: 1.86050063189.
- order_200_400_density_L1: 1.89430821594.
- order_200_400_fresh_L1: 1.89411641807.
- order_400_800_density_L1: 1.90660166169.
- order_400_800_fresh_L1: 1.90688958599.

T10_800: 526.656s; pasos12541; RHS25082; HLLC20065600; HLLE0; dt [1.93733219992e-07, 1.16954323005e-06].

T03_0.2_N1600: 304.844s; pasos3601; RHS7202; HLLC11515998; HLLE0; dt [1.1379648046e-07, 3.6661003203e-07].

Timeout anterior300s; nuevo600s exclusivamente para estos casos. Sin optimizar.
Primer intento de preparar fase falló antes de comandos/integraciones por
lectura cp1252 del roadmap; corregida lectura UTF8. Preservado en setup-failure.
Normalización de ruta relativa corregida en reproductor offline antes de emitir
study.json; ninguna repetición física por ese error. No reparaciones científicas.
El runner nativo conserva BLOCKED/review_not_approved: no tiene reviewer real
conectado. No se sustituye su archivo; dictamen independiente se adjunta separado.

Evidencia: acquisition/artifacts/cases, provenance en study.json (hash de cada
artefacto, configuración, inputs y referencia; solver compatible4620200).
Las ocho soluciones acústicas reutilizadas y T10 anteriores conservan originales.
Comando de reproducción: `.\.venv\Scripts\python.exe -m dev_orchestrator.p1_r5_review --acquisition results/p1-r5e-20260918/acquisition --output results/p1-r5e-20260918/study.json`.

Decisión: **P1_R5_PASS_CFL_SECOND_ORDER_CONTRACT**. Adoptado el delta exacto
1D_CONTRACT_V1_R5 antes del cierre P2. R4 conserva FAIL histórico en segundo
orden; no se reescribe evidencia anterior. Evaluador reforzado para exigir12/12
y todas las comparaciones, observación independiente sin cambios numéricos.

## Verificación completa posterior a adopción R5

70 pruebas PASS; comprobaciones FO/P0 offline, cero integraciones en cierre.
Matriz con58 resultados finales (56 reutilizados y2 nuevos), hashes en provenance.

| Gate | Estado | Subcasos completos |
|---|---|---|
| T01 | PASS | 2/2 |
| T02 | PASS | 1/1 |
| T03 | PASS | 1/1 |
| T04 | PASS | 1/1 |
| T05 | PASS | 1/1 |
| T06 | PASS | 1/1 |
| T07 | PASS | 3/3 |
| T08 | PASS | 18/18 |
| T09 | PASS | 4/4 |
| T10 | PASS | 4/4 |
| T11 | PASS | 12/12 |
| T12 | PASS | 10/10 |

### Errores T10

| N | L1 rho | L2 rho | L1 rhoY | L2 rhoY |
|---|---|---|---|---|
| T10_100 | 0.000913337613828 | 0.00123802917595 | 0.00228294128211 | 0.00313213649265 |
| T10_200 | 0.000251371131953 | 0.000393951711005 | 0.000628677973104 | 0.000997095176925 |
| T10_400 | 6.76194769036e-05 | 0.000124792483267 | 0.0001691384659 | 0.000315903166478 |
| T10_800 | 1.80354721772e-05 | 3.95104106223e-05 | 4.5103622471e-05 | 0.000100025139403 |

### Rendimiento registrado por caso
Tiempos de evidencia reutilizada son históricos; sólo T10_800 y T03_0.2_N1600
se ejecutaron ahora. Se conserva comparación FIRST_ORDER en closure.json.

| Caso | Runtime s | Steps | RHS | HLLC | HLLE |
|---|---|---|---|---|---|
| T01_rest | 1.063 | 251 | 502 | 50200 | 0 |
| T01_moving | 1.297 | 301 | 602 | 60200 | 0 |
| T02_sod | 11.141 | 547 | 1314 | 526914 | 0 |
| T03 | 37.063 | 901 | 1802 | 1439798 | 0 |
| T04 | 150.968 | 3509 | 7243 | 5794400 | 0 |
| T05 | 150.953 | 3510 | 7231 | 5777569 | 0 |
| T06_contact | 66.515 | 3125 | 6500 | 2600000 | 0 |
| T07_periodic | 3.032 | 301 | 602 | 120400 | 0 |
| T07_closed | 2.594 | 251 | 502 | 100902 | 0 |
| T07_open | 2.610 | 301 | 602 | 119798 | 0 |
| T08_constant_rest_100 | 1.062 | 251 | 502 | 50702 | 0 |
| T08_constant_rest_200 | 4.188 | 501 | 1002 | 201402 | 0 |
| T08_constant_rest_400 | 19.250 | 1004 | 2014 | 807614 | 0 |
| T08_smooth_rest_100 | 1.484 | 268 | 570 | 57570 | 0 |
| T08_smooth_rest_200 | 6.625 | 580 | 1319 | 265119 | 0 |
| T08_smooth_rest_400 | 32.188 | 1306 | 3223 | 1292423 | 0 |
| T08_frustum_rest_100 | 1.547 | 273 | 591 | 59691 | 0 |
| T08_frustum_rest_200 | 5.296 | 508 | 1030 | 207030 | 0 |
| T08_frustum_rest_400 | 31.656 | 1292 | 3166 | 1269566 | 0 |
| T08_constant_flow_100 | 1.453 | 299 | 598 | 59202 | 0 |
| T08_constant_flow_200 | 14.047 | 1195 | 3584 | 713216 | 0 |
| T08_constant_flow_400 | 61.406 | 2370 | 7088 | 2828112 | 0 |
| T08_smooth_flow_100 | 3.125 | 448 | 1194 | 118206 | 0 |
| T08_smooth_flow_200 | 12.078 | 890 | 2364 | 470436 | 0 |
| T08_smooth_flow_400 | 45.796 | 1748 | 4600 | 1835400 | 0 |
| T08_frustum_flow_100 | 2.469 | 388 | 954 | 94446 | 0 |
| T08_frustum_flow_200 | 8.594 | 712 | 1651 | 328549 | 0 |
| T08_frustum_flow_400 | 29.265 | 1323 | 2900 | 1157100 | 0 |
| T09_contact | 66.062 | 3125 | 6500 | 2600000 | 0 |
| T09_reverse | 62.391 | 3024 | 6096 | 2438400 | 0 |
| T09_inleft | 29.531 | 1500 | 3000 | 1197000 | 0 |
| T09_inright | 27.891 | 1500 | 3000 | 1197000 | 0 |
| T10_100 | 8.015 | 1567 | 3134 | 313400 | 0 |
| T10_200 | 32.047 | 3135 | 6270 | 1254000 | 0 |
| T10_400 | 129.469 | 6270 | 12540 | 5016000 | 0 |
| T10_800 | 526.656 | 12541 | 25082 | 20065600 | 0 |
| T02_sod_0.2 | 19.500 | 993 | 2225 | 892225 | 0 |
| T02_sod_0.4 | 11.125 | 547 | 1314 | 526914 | 0 |
| T02_sod_0.6 | 9.250 | 421 | 1102 | 441902 | 0 |
| T03_0.2 | 74.203 | 1801 | 3602 | 2877998 | 0 |
| T03_0.4 | 37.515 | 901 | 1802 | 1439798 | 0 |
| T03_0.6 | 30.469 | 675 | 1499 | 1197701 | 0 |
| T03_0.2_N400 | 18.750 | 901 | 1802 | 718998 | 0 |
| T03_0.4_N400 | 9.219 | 451 | 902 | 359898 | 0 |
| T03_0.6_N400 | 6.125 | 301 | 602 | 240198 | 0 |
| T03_0.2_N1600 | 304.844 | 3601 | 7202 | 11515998 | 0 |
| T03_0.4_N1600 | 153.578 | 1801 | 3602 | 5759598 | 0 |
| T03_0.6_N1600 | 125.234 | 1357 | 3026 | 4838574 | 0 |
| T12_expansion | 4.796 | 283 | 581 | 232971 | 10 |
| T12_contact | 66.578 | 3125 | 6500 | 2600000 | 0 |
| T12_pure0 | 69.219 | 3308 | 7232 | 2892800 | 0 |
| T12_pure1 | 69.172 | 3308 | 7232 | 2892800 | 0 |
| T12_frustum_0_100 | 1.657 | 286 | 642 | 64842 | 0 |
| T12_frustum_0_200 | 5.204 | 502 | 1007 | 202407 | 0 |
| T12_frustum_0_400 | 25.828 | 1139 | 2554 | 1024154 | 0 |
| T12_frustum_1_100 | 1.641 | 286 | 642 | 64842 | 0 |
| T12_frustum_1_200 | 5.157 | 502 | 1007 | 202407 | 0 |
| T12_frustum_1_400 | 25.688 | 1139 | 2554 | 1024154 | 0 |

```json
{
  "current_acquisition_seconds": 831.5,
  "maximum_case_seconds": 526.6560000004247,
  "HLLC": 104498544,
  "HLLE": 10,
  "RHS": 189503
}
```

Los831.500s son la suma de las DOS integraciones nuevas, no incluyen lectura,
compresión, pruebas ni revisión. No hubo timeout600 ni necesidad de perfilado.
No se midió memoria máxima de toda la ejecución. Los10 fallbacks HLLE de la
matriz pertenecen al caso de expansión existente, no a las dos adquisiciones.
Máximo balance global del conjunto8.942911515485987e-15; ambos nuevos sinHLLE.

FIRST_ORDER:52 registros bajoR4 PASS, sin reintegración; producción0D, P0 y
contratosP1–R4 conservan hashes. Siete comparaciones históricas P0 ejecutadas
offline contra referencias originales, no nuevas campañas físicas.
Autorrevisión de alcance y hashes separada de revisión independiente.
Revisión independiente final PASS: final-review.json. Decisión derivada
**P2_PASS_1D_CORE_VERIFIED / WAITING_HUMAN_APPROVAL** en decision.json.
Aceptación humana NO emitida, P3 NO iniciado. Gate nativo BLOCKED por
review_not_approved conservado; se adjunta revisión real, no se atribuye
aprobación al stub ni se modifica configuración global.
