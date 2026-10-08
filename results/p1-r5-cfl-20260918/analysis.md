# P1-R5 — revisión offline de sensibilidad CFL de segundo orden

Estado: **P1_R5_CFL_SECOND_ORDER_UNRESOLVED**. P2 permanece
**P2_BLOCKED_SECOND_ORDER**. No se adopta 1D_CONTRACT_V1_R5.
No integraciones nuevas, cambios de solver ni ampliación efectiva de runtime.

## Fundamento y límite de la conclusión

SSP preserva, bajo sus hipótesis y restricción temporal, una propiedad convexa
de estabilidad heredada de Forward Euler sobre una discretización espacial fija.
No implica monotonía entre mallas de la diferencia de amplitudes de dos CFL.
Fuente primaria: Gottlieb, Shu y Tadmor (2001), §2,
https://www.cfm.brown.edu/people/sg/SSPsiamreview.pdf . Esto tampoco demuestra
que este Euler/HLLC sea TVD bajo todas las condiciones.

Contraejemplo lógico, no ajuste a datos ni modelo del solver: errores e_a(h)=h²
y e_b(h)=h³ disminuyen para h=.9,.45,.225, pero |e_a-e_b| vale
.081 → .111375 → .039234375. Convergencia individual no implica monotonía
estricta de la diferencia en cada transición. Por desigualdad triangular,
|A_a-A_b| <= |A_a-A_ref| + |A_b-A_ref|; convergencia a una referencia común
implicaría convergencia de diferencias, no monotonía en cada malla finita.

Minmod anula pendientes ante cambio de signo; su activación y el máximo
celular dependen de la malla. Interacciones de error espacial, temporal,
fase y disipación son explicaciones posibles, no causas demostradas aquí.
Los datos disponibles son compatibles con un régimen preasintótico; tres
mallas no prueban convergencia asintótica. La referencia T03 es acústica lineal
de pequeña amplitud, conservada exactamente como benchmark, no una solución
exacta del Euler no lineal a amplitud finita.

## Reproducción sin integrar

Fuente: resume-remaining-final/artifacts de results/p2b-gas1d-20260918.
Se verifican hashes de solver y evidencia, y se reconstruyen las firmas de IC,
BC, configuración, malla y referencia canónicas. Amplitud desde arrays finales;
A_ref desde primitivas de integrales conservadas de referencia, no pico continuo.
Eabs=|A-A_ref|; Erel=Eabs/A_ref; E_A=Eabs/10 Pa. S=|A_a-A_b|/10 Pa.
El resultado parcial N1600/.2 no aporta una amplitud final.

| N | CFL | A (Pa) | A_ref (Pa) | Eabs (Pa) | Erel | E_A |
|---|---|---|---|---|---|---|
| 400 | 0.2 | 9.14443393229 | 9.98699441143 | 0.842560479141 | 0.0843657705642 | 0.0842560479141 |
| 400 | 0.4 | 9.1483281148 | 9.98699441143 | 0.838666296637 | 0.0839758451929 | 0.0838666296637 |
| 400 | 0.6 | 9.14993965974 | 9.98699441143 | 0.837054751697 | 0.0838144808351 | 0.0837054751697 |
| 800 | 0.2 | 9.62864623751 | 9.99674574511 | 0.368099507599 | 0.0368219335556 | 0.0368099507599 |
| 800 | 0.4 | 9.63078348491 | 9.99674574511 | 0.365962260199 | 0.0366081392415 | 0.0365962260199 |
| 800 | 0.6 | 9.63281855416 | 9.99674574511 | 0.363927190949 | 0.0364045660686 | 0.0363927190949 |
| 1600 | 0.2 | INCOMPLETO | 9.99918625753 | INCOMPLETO | INCOMPLETO | INCOMPLETO |
| 1600 | 0.4 | 9.84536868558 | 9.99918625753 | 0.153817571947 | 0.0153830089755 | 0.0153817571947 |
| 1600 | 0.6 | 9.8463535082 | 9.99918625753 | 0.152832749329 | 0.0152845186991 | 0.0152832749329 |

| Pareja CFL | S400 | S800 | S1600 |
|---|---|---|---|
| [0.2, 0.4] | 0.000389418250415 | 0.000213724740024 | INCOMPLETO |
| [0.4, 0.6] | 0.000161154493981 | 0.000203506925027 | 9.84822618193e-05 |
| [0.2, 0.6] | 0.000550572744396 | 0.000417231665051 | INCOMPLETO |

| N | CFL | Tiempo s | Steps | RHS | HLLC | HLLE | Máximo ledger | Máximo stage | Admisible intervalo registrado |
|---|---|---|---|---|---|---|---|---|---|
| 400 | 0.2 | 18.750 | 901 | 1802 | 718998 | 0 | 3.1115e-16 | 1.59386e-16 | True |
| 400 | 0.4 | 9.219 | 451 | 902 | 359898 | 0 | 2.29485e-16 | 1.5178e-16 | True |
| 400 | 0.6 | 6.125 | 301 | 602 | 240198 | 0 | 2.03413e-16 | 1.48542e-16 | True |
| 800 | 0.2 | 74.203 | 1801 | 3602 | 2877998 | 0 | 2.65193e-16 | 1.55904e-16 | True |
| 800 | 0.4 | 37.515 | 901 | 1802 | 1439798 | 0 | 2.39194e-16 | 1.55744e-16 | True |
| 800 | 0.6 | 30.469 | 675 | 1499 | 1197701 | 0 | 1.75122e-16 | 1.52746e-16 | True |
| 1600 | 0.2 | 300.094 | 3578 | 7156 | 11442444 | 0 | 4.65742e-16 | 1.5916e-16 | True |
| 1600 | 0.4 | 153.578 | 1801 | 3602 | 5759598 | 0 | 4.91126e-16 | 1.59498e-16 | True |
| 1600 | 0.6 | 125.234 | 1357 | 3026 | 4838574 | 0 | 1.22263e-16 | 1.57089e-16 | True |

Todos los intervalos registrados conservan balances <=1e-10 y admisibilidad.
Para N1600/.2 eso solo acredita el intervalo parcial. Los residuos de las
cuatro componentes, checks padre, errores de presión, fase y contadores se
conservan en study.json. Memoria no medida; runtimes son históricos reutilizados.

## Decisión y secuencias

CFL .4 y .6: errores de amplitud decrecientes en las tres mallas; .2:
disminución 400→800, final1600 desconocido. No se observa alejamiento
sistemático en los resultados completos. La pareja .4/.6 tiene sensibilidad
fina menor que gruesa, pero aumenta 400→800: R4 sigue incumplido.
Faltan dos sensibilidades finas (.2/.4 y .2/.6), el error fino .2 y su
estabilidad/admisibilidad hasta el tiempo final. No se elimina N800 ni se
introduce una cota ajustada al máximo observado.

La orden §6 exige justificar cada cláusula con datos disponibles. La revisión
no confunde cuestionar el fundamento universal de R4 con acreditar R5 para
los tres CFL. No hay PASS científico provisional autorizado expresamente.
Conforme a §7, STOP: no se activa la fase B de600s. R4 permanece vigente;
no se modifica ningún contrato anterior ni se atribuye aceptación humana.

T10 N800 y T11 N1600/.2 siguen INCOMPLETE_TIMEOUT históricos; orden400→800
no disponible. T01–T09 PASS, T12 10/10 PASS son evidencia histórica, no una
nueva ejecución. No hay matriz final completa ni cierre P2. P0/FO no fueron
reintegrados: la fase C no se habilitó; sus regresiones anteriores no se
presentan como ejecutadas ahora. Presupuesto3/3 intacto. Sin P3 ni archivo.

Reproducción: `.\.venv\Scripts\python.exe -m dev_orchestrator.p1_r5_offline`.
