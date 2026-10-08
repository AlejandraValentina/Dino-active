## P1-R4
- [x] Comprobar Git, leer orden y preservar eliminación ajena redme.txt.
- [x] Documentar métrica exacta, origen0,08 y protocolo antes de ejecutar (48fa1d3).
- [x] Adaptador de análisis con implementación congelada y pruebas pertinentes.
- [x] Reproducción determinista N800 y matriz de refinamiento/referencia0,1.
- [x] Revisión científica independiente y adopción condicionada R4 (982cee0).
- [x] Tras R4 PASS: seis casos T11 primero y regresiones necesarias para P2A.
- [x] Cierre de revisión final, documentación, OpenSpec estricto y commit local.

## Decisión científica
**P1_R4_PASS_T11_REFINED_CONTRACT**. Se adoptó 1D_CONTRACT_V1_R4 sin editar
solver ni contratos anteriores. El estudio respalda el caso A en las tres mallas:
la dependencia de amplitud con CFL disminuye sistemáticamente al refinar;
no se observa un límite distinto de CFL0,6 ni pérdida de admisibilidad.
Esto es convergencia observada acotada, no demostración asintótica universal.

## Métrica y origen del límite
A(N,C)=max_i[p_i(t_final)-p0], en Pa, del pulso T03 derecho, al tiempo
0,45L/a0. No es señal de sensor, integral ni amplitud ajustada. Caso: L1m,
área0,01m², gamma1,35, R287, p0=100000Pa, T0=300K, Y0=0,3; pulso
centro0,25m, ancho0,04m, BC características no reflectivas BASE explícita.
Primitivas de integrales conservadas por celda; misma definición en todas las mallas.

8,832393583405064Pa es el pico final con CFL0,6;7,99875531278667Pa con CFL0,2.
S=abs(Aa-Ab)/10Pa. Denominador10Pa=1e-4*p0 es amplitud inicial prescrita,
no el máximo inicial discreto ni la amplitud final de otra ejecución.
En N800: diferencia0,833638270618394Pa, S0,0833638270618394>0,08.

El0,08 aparece desde5b6b62f en el plan T11 y manifest P1. La orden original
pidió definir sensibilidad CFL, sin especificar ese valor. No se encontró una
derivación cuantitativa en el contrato ni su evidencia: tolerancia práctica,
no constante física ni cota teórica. T11 ya se llamaba sensibilidad; el fallo
histórico bajoR3 permanece válido, no se redefine como una prueba de estabilidad.

## Estudio congelado
Run `20260918T113736-P1_R4_CFL_REVIEW-f137adf51561`, fuente356284a,
núcleo numérico b353e90 idéntico. 12 integraciones nuevas;509,375s del adaptador.
N800(.2/.4/.6) se repitió primero y coincide exactamente con R3 en arrays,
ledger, pasos, contadores y métricas; solo wall_seconds se excluye del cotejo.
Estas ejecuciones forman la fila N800, no se cuentan dos veces.
N3200 opcional omitido antes del estudio:~1470s adicionales estimados para
cuatro CFL, frente~483s previstos para las tres mallas. No timeout ni reintentos.

### Amplitud del observable, Pa
| N | dx m | CFL0,1 diagnóstico | CFL0,2 | CFL0,4 | CFL0,6 |
| --- | --- | --- | --- | --- | --- |
| 400 | 0.0025 | 6.642147046 | 6.857220385 | 7.359092662 | 7.993292912 |
| 800 | 0.00125 | 7.825034931 | 7.998755313 | 8.384220394 | 8.832393583 |
| 1600 | 0.000625 | 8.715426597 | 8.834082853 | 9.086891736 | 9.362799273 |

### Comparaciones contractuales entre CFL
Misma métrica, sin cambiar denominador.

| N | Pareja CFL | Diferencia absoluta Pa | Diferencia /10Pa |
| --- | --- | --- | --- |
| 400 | 0.2–0.4 | 0.5018722772 | 0.05018722772 |
| 400 | 0.4–0.6 | 0.6342002496 | 0.06342002496 |
| 400 | 0.2–0.6 | 1.136072527 | 0.1136072527 |
| 800 | 0.2–0.4 | 0.3854650811 | 0.03854650811 |
| 800 | 0.4–0.6 | 0.4481731895 | 0.04481731895 |
| 800 | 0.2–0.6 | 0.8336382706 | 0.08336382706 |
| 1600 | 0.2–0.4 | 0.2528088828 | 0.02528088828 |
| 1600 | 0.4–0.6 | 0.2759075367 | 0.02759075367 |
| 1600 | 0.2–0.6 | 0.5287164195 | 0.05287164195 |

### Referencia temporal diagnóstica CFL0,1
Mismo esquema espacial; no referencia exacta de Euler ni nuevo CFL de producción.

| N | CFL frente0,1 | Diferencia absoluta Pa | Diferencia /10Pa |
| --- | --- | --- | --- |
| 400 | 0.2 | 0.2150733385 | 0.02150733385 |
| 400 | 0.4 | 0.7169456157 | 0.07169456157 |
| 400 | 0.6 | 1.351145865 | 0.1351145865 |
| 800 | 0.2 | 0.1737203819 | 0.01737203819 |
| 800 | 0.4 | 0.5591854631 | 0.05591854631 |
| 800 | 0.6 | 1.007358653 | 0.1007358653 |
| 1600 | 0.2 | 0.1186562565 | 0.01186562565 |
| 1600 | 0.4 | 0.3714651393 | 0.03714651393 |
| 1600 | 0.6 | 0.647372676 | 0.0647372676 |

### Pasos, tiempos y CFL real
dt en segundos; incluye truncamiento al mismo tiempo final físico.

| N | CFL pedido | Pasos | dt mínimo s | dt máximo s | CFL real máximo | Runtime s |
| --- | --- | --- | --- | --- | --- | --- |
| 400 | 0.1 | 1801 | 9.168285265e-08 | 7.332404856e-07 | 0.1 | 12.25 |
| 400 | 0.2 | 901 | 9.34549479e-08 | 1.466478204e-06 | 0.2 | 6.125 |
| 400 | 0.4 | 451 | 9.741550414e-08 | 2.932943502e-06 | 0.4 | 3.062 |
| 400 | 0.6 | 301 | 1.020838311e-07 | 4.399390903e-06 | 0.6 | 2.015 |
| 800 | 0.1 | 3601 | 1.008520721e-07 | 3.666164715e-07 | 0.1 | 48.719 |
| 800 | 0.2 | 1801 | 1.020998449e-07 | 7.332318299e-07 | 0.2 | 24.188 |
| 800 | 0.4 | 901 | 1.047820816e-07 | 1.466458724e-06 | 0.4 | 12.344 |
| 800 | 0.6 | 601 | 1.077552266e-07 | 2.199679503e-06 | 0.6 | 8 |
| 1600 | 0.1 | 7201 | 1.069848383e-07 | 1.833068161e-07 | 0.1 | 198.875 |
| 1600 | 0.2 | 3601 | 1.077592355e-07 | 3.666132529e-07 | 0.2 | 101.375 |
| 1600 | 0.4 | 1801 | 1.093755113e-07 | 7.332248911e-07 | 0.4 | 52.156 |
| 1600 | 0.6 | 1201 | 1.110902599e-07 | 1.099834696e-06 | 0.6 | 34.579 |

### Conservación, admisibilidad y fallbacks
Residuo máximo normalizado sobre tiempo y las cuatro componentes.

| N | CFL | Peor residuo | min rho kg/m3 | min p Pa | min T K | HLLE | Rechazos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 400 | 0.1 | 1.334357234e-15 | 1.161440184 | 99999.99982 | 299.9999997 | 0 | 0 |
| 400 | 0.2 | 1.385222823e-16 | 1.161440184 | 99999.99982 | 299.9999997 | 0 | 0 |
| 400 | 0.4 | 1.627222789e-16 | 1.161440184 | 99999.99981 | 299.9999997 | 0 | 0 |
| 400 | 0.6 | 1.363551728e-16 | 1.161440184 | 99999.9998 | 299.9999997 | 0 | 0 |
| 800 | 0.1 | 6.138168148e-15 | 1.161440184 | 99999.9998 | 299.9999997 | 0 | 0 |
| 800 | 0.2 | 2.672325863e-16 | 1.161440184 | 99999.9998 | 299.9999997 | 0 | 0 |
| 800 | 0.4 | 2.987171554e-16 | 1.161440184 | 99999.9998 | 299.9999997 | 0 | 0 |
| 800 | 0.6 | 8.6360929e-16 | 1.161440184 | 99999.99979 | 299.9999997 | 0 | 0 |
| 1600 | 0.1 | 1.04281549e-14 | 1.161440184 | 99999.99979 | 299.9999997 | 0 | 0 |
| 1600 | 0.2 | 6.139037873e-15 | 1.161440184 | 99999.99979 | 299.9999997 | 0 | 0 |
| 1600 | 0.4 | 2.554204664e-16 | 1.161440184 | 99999.99979 | 299.9999997 | 0 | 0 |
| 1600 | 0.6 | 1.833058176e-15 | 1.161440184 | 99999.99979 | 299.9999997 | 0 | 0 |

Las12 ejecuciones mantienen estados aceptados admisibles, sin clipping,
rechazos ni HLLE. Peor residuo1,04281549e-14<1e-10. Extremos deY y residuos
por componente quedan en study/artifacts/study.json; arrays/ledger completos
comprimidos por caso. Estabilidad observada y sensibilidad no son sinónimos.

### Exactitud respecto de referencia independiente
E_A=abs(A-A_ref(N))/10Pa, donde A_ref es pico de las primitivas de integrales
conservadas de la gaussiana trasladada original T03. No reemplazarla por CFL0,1.

| N | CFL | E_A | E1 presión | E2 presión | Gates padre T03 |
| --- | --- | --- | --- | --- | --- |
| 400 | 0.1 | 0.3344847365 | 0.02766327548 | 0.07048821611 | FAIL: pressure_L1 |
| 400 | 0.2 | 0.3129774026 | 0.0255438527 | 0.06563499769 | FAIL: pressure_L1 |
| 400 | 0.4 | 0.2627901749 | 0.02083543745 | 0.05446666587 | PASS |
| 400 | 0.6 | 0.19937015 | 0.01524104916 | 0.04072806772 | PASS |
| 800 | 0.1 | 0.2171710814 | 0.01673611135 | 0.04445588704 | PASS |
| 800 | 0.2 | 0.1997990432 | 0.01524891602 | 0.04072805789 | PASS |
| 800 | 0.4 | 0.1612525351 | 0.01204476627 | 0.03256117189 | PASS |
| 800 | 0.6 | 0.1164352162 | 0.008494524511 | 0.02326341391 | PASS |
| 1600 | 0.1 | 0.1283759661 | 0.009416436455 | 0.02570445094 | PASS |
| 1600 | 0.2 | 0.1165103404 | 0.008492487311 | 0.02326007237 | PASS |
| 1600 | 0.4 | 0.09122945216 | 0.006561753951 | 0.01810136622 | PASS |
| 1600 | 0.6 | 0.06363869848 | 0.004513286973 | 0.01254390621 | PASS |

En N400, CFL0,1/0,2 incumplen E1 de T03: diagnóstico de malla gruesa,
no ocultado ni llamado inestabilidad. El contrato original exige T03 en N800;
R4 conserva allí los límites y los exige también en N1600, donde todos aprueban.

## Interpretación y nuevo criterio
Linealizando la rama acústica, upwind+FE tiene ecuación modificada
q_t+a0*q_x=nu_num*q_xx+O(dx²), nu_num=a0*dx*(1-C)/2.
El pico gaussiano aproximado es10/sqrt(1+4*nu_num*t/0,04²).
Sin ajustar coeficientes, discrepancia máxima observada0,0067071Pa.
La predicción respalda difusión dependiente de CFL; no se usa como cota rigurosa
ni como referencia numérica para cambiar gates. Fuente primaria y derivación en
`docs/gasdynamic/1d_cfl_sensitivity_v1_r4.md`.

Al disminuir CFL a malla fija aumenta esta difusión neta; CFL0,1 puede ser
más preciso temporalmente respecto del esquema semidiscreto pero más amortiguado
respecto de Euler. Todos los CFL acercan su pico a la referencia al refinar.
Órdenes observados de S(.2,.6):0,44656 y0,65693. No se atribuye orden asintótico1.
No hay evidencia de que CFL0,6 tienda a una solución diferente en este estudio.

R4 conserva todos los gates padre T03 en N800 y los exige también en N1600:
pico/analítica[0,65;1,05], E1p<=0,025, E2p<=0,08, velocidad error<=1%,
admisibilidad y balances. Mantiene T11 Sod E1<=0,015 y velocidad<=0,005a0.
Sustituye únicamente la comparación de amplitud<=0,08 por descenso estricto
S400>S800>S1600 para las tres parejas productivas, y E_A400>E_A800>E_A1600
para cada CFL0,2/0,4/0,6. Ambas transiciones son obligatorias.

**Se retira la garantía histórica de diferencia<=8% en N800. No es un criterio
equivalente ni se afirma ausencia de relajación formal.** No se redondeó0,08
a0,09/0,10: el límite cuantitativo de exactitud sigue siendo el T03 preexistente,
y se añaden condiciones de refinamiento. Conclusión limitada a este pulso,
anchura, fronteras y método; sin generalizar a otros casos o validación experimental.
CFL0,1 queda diagnóstico: comprobar sus filas asegura integridad de este estudio,
no lo convierte en un requisito productivo futuro. MUSCL/SSP-RK2 conserva su
T11 original y no se implementa en P1-R4.

Contrato: `docs/gasdynamic/1d_contract_v1_r4.json`. Delta exacto en
`docs/gasdynamic/1d_contract_v1_r4_delta.json`: solamente model_version y
definición T11. P1v1/R2/R3 y solver congelados byte a byte.

## Revalidación T11 primero y regresión P2A
Run `20260918T115319-P2A_R4_VERIFY-7474ef29fc6d`, fuente4ce6809.
Después de adoptar R4 se ejecutaron seis casos nuevos: T02 Sod y T03 para
CFL0,2/0,4/0,6. Todos PASS y deterministas respecto de R3. T11_R4 PASS.
Solo entonces se reevaluaron los52 registros mediante measure/aggregate:
6 nuevos +46 reutilizados con inventario SHA256 y fuente numérica idéntica.
No se presentan52 integraciones nuevas. T01–T12 PASS bajo R4; el overlay
conserva el FAIL de amplitud histórico como diagnóstico y no altera sus archivos.
Tiempo del comando T11+regresión offline:57,000s.
Revisión final independiente PASS: **P2A_PASS_FIRST_ORDER_VERIFIED** bajo R4.
Recibo separado p2a-reviewed-evidence.json; no aceptación humana de P2.

## Pruebas y alcance
8 pruebas pertinentes PASS (3 de estudio,5 del gate): denominador10Pa,
determinismo, hashes congelados, malla ausente, sensibilidad no decreciente,
sesgo común/error padre, y preservación de fallos Sod/velocidad.
Pruebas automatizadas y revisión independiente no son aceptación humana.
No se comprobó UI/Windows porque el producto y su interfaz no cambiaron.
No tocar integración OpenSpec/Codex ni configuración global. No publicar/archivar.
No P2B/P3 ni actualización de EXE; aceptación humana de P2 pendiente.
Presupuesto de reparaciones de solver permanece3/3 usado; R4 no lo reinicia.

Comandos ejecutados:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_p1_r4*.py" -v
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P1_R4_CFL_REVIEW --dependency P0=docs/gasdynamic/p0_accepted_dependency.json --dependency P1=docs/gasdynamic/p1_accepted_dependency.json --dependency P1_R3_BOUNDARY_SEMANTICS_REVIEW=results/p1-r3-fronteras-20260918/reviewed-evidence.json
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P2A_R4_VERIFY --dependency P0=docs/gasdynamic/p0_accepted_dependency.json --dependency P1=docs/gasdynamic/p1_accepted_dependency.json --dependency P1_R4_CFL_REVIEW=results/p1-r4-cfl-20260918/reviewed-evidence.json
openspec validate p1-r4-cfl --strict --no-interactive
```
Los runners nativos terminaron COMPLETED/BLOCKED por reviewer no conectado;
se preservan sin reescribir y los recibos revisados se guardan separadamente.
Evidencia en `results/p1-r4-cfl-20260918/`, con fuente y procedencia explícitas.

## Cierre revisado
Revisor independiente read-only `/root/p1_r4_review`: aprobó estudio/contrato,
implementación del criterio y evidencia final. Verificó15 hashes del estudio,
24 entradas congeladas,10 hashes de verificación y63 del histórico reutilizado;
recalculó amplitudes y confirmó T01–T12 bajo R4. Peor ledger de los seis runs
nuevos8,63609e-16. Autorrevisión de alcance es distinta de esta revisión.
Se mantienen contratos anteriores, producción y solver por hashes; no hay
modificaciones científicas encubiertas en el núcleo para alcanzar PASS.

P1-R4: PASS. P2A: **P2A_PASS_FIRST_ORDER_VERIFIED**. P2 completo no cerrado:
P2B no iniciado y aceptación humana pendiente. No P3, push ni archivo.
La eliminación ajena redme.txt no se incluye. Secuencia local:48fa1d3 protocolo,
356284a adaptador,982cee0 estudio/revisión/adopción R4,4ce6809 gate y regresión.
El commit que contiene este cierre añade los resultados finales y documentación.

OpenSpec estricto y git diff --check: PASS al cierre. Inventarios y blobs de
evidencia comprobados; el diff de motorsim desde2143a60 está vacío.
