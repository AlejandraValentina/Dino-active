## P1-R3
- [x] Comprobar Git y preservar eliminación ajena de redme.txt.
- [x] Revisar contrato, derivar closed/open/nonreflecting y explicar ramas.
- [x] Revisión conceptual independiente y contrato R3 antes de código.
- [x] Implementar BC ideal y comprobar contadores/base externa explícita.
- [x] Orquestador: T05 N200/400/800 y NR01, revisión y gate R3 PASS.
- [x] Tras gates PASS: revalidar T01–T12 completos con R3.
- [x] Registrar revisión final, gate P2A BLOCKED y commit documental de cierre.

## Resultado de la ejecución — 18/09/2026
**P1_R3_PASS_BOUNDARIES_SEPARATED**. **P2A NO aprobado**: T11 incumple la
sensibilidad de amplitud del pulso. 52/52 casos individuales PASS no equivalen
a matriz completa PASS. T01–T10 y T12 PASS; T11 FAIL. Sin P2B/P3 ni aceptación
humana de P2. No archivar ni publicar. T02 R2/T06, v1/R2 y baseline 0D intactos.

## Diagnóstico y delta contractual
P1 ya distinguía frontera abierta, no reflectiva y reservorio. T05 usaba `open`,
no una BC no reflectiva. El conflicto real era mezclar presión acústica fija con
conmutación de entropía/composición interior–reservorio según el signo de flujo.
Las ramas -3,645786e-11 y +4,122781e-8 m/s son incompatibles también a70dígitos:
J+ queda entre los dos invariantes de reposo y ninguna satisface su signo supuesto.
No se impone velocidad cero ni un epsilon para elegir rama.

Con w normal saliente, Z0=rho0*a0 y j±=w'±p'/Z0:
w'=(j++j-)/2, p'=Z0(j+-j-)/2, Rp=-j-/j+.
Pared: j-=-j+ => Rp=+1; presión liberada: j-=j+ => Rp=-1;
no reflectiva: j-=0 => Rp=0. El reservorio permanece separado.

R3 prescribe p_b=p0 y continuación K_b=K_i, Y_b=Y_i en ambos sentidos:
rho_b=(p0/K_i)^(1/gamma), w_b=w_i+2(a_i-a_b)/(gamma-1).
Se evalúa la diferencia con log1p/expm1; flujo Euler del estado de cara,
sin ghost nuevo ni cambio de ondas. Alcance acústico subsónico; no radiación
real ni reservorio general. En retorno, K/Y son condiciones entrantes explícitas.

Contrato y derivación: `docs/gasdynamic/1d_boundary_semantics_v1_r3.md`.
Delta exacto R2→R3: `docs/gasdynamic/1d_contract_v1_r3_delta.json`:
solo model_version, nombre de BC y definición material de T05. Tolerancias,
T04, T02 y T06 conservados. El delta v1→R2 precedente se conserva por separado.
Código: `motorsim/gas1d/boundary.py`, kind `ideal_open_pressure_release`.
La definición contractual fue comprometida en efaa2ab antes del código1869111.
Las frases de prueba pendiente del contrato sellado describen ese momento;
el recibo `reviewed-evidence.json` registra la aprobación posterior sin reescribirlo.

## T05 antes y después
Antes: ensayo original detenido a17 pasos por ramas inconsistentes. El ensayo
provisional R2 a2764 pasos con excepción de velocidad cero fue retirado y no
acredita T05. Después: tres mallas completadas con signo negativo estable.
N800 es contractual; N200/N400 son diagnóstico, no un nuevo gate de convergencia.
Mismo pulso10Pa, sensor0,7, ventanas, CFL0,4, tf y tolerancia |Rp+1|<=0,30.

| N | Incidente Pa | Reflejada Pa | Rp | Pico t*a0/L | Masa residual normalizado máx. | Energía residual normalizado máx. |
| --- | --- | --- | --- | --- | --- | --- |
| 200 | 5.763065608 | -4.078010004 | -0.7076112405 | 0.999 | 1.471557367e-16 | 1.890005991e-16 |
| 400 | 7.553690705 | -5.894143757 | -0.7802998543 | 0.999 | 1.485546623e-16 | 4.072074895e-16 |
| 800 | 8.525848333 | -7.182159034 | -0.84239817 | 1 | 2.118295642e-16 | 2.125813561e-16 |

| N | min rho kg/m3 | min p Pa | min T K | HLLC | HLLE | Flujos característicos |
| --- | --- | --- | --- | --- | --- | --- |
| 200 | 1.161401954 | 99995.55615 | 299.9965436 | 228850 | 0 | 2300 |
| 400 | 1.161385441 | 99993.63683 | 299.9950508 | 917700 | 0 | 4600 |
| 800 | 1.161374673 | 99992.38516 | 299.9940772 | 2756550 | 0 | 6900 |

Procedencia: estudio T05 generado con1869111 en boundary-attempt-1; copiado con
hashes verificados en boundary-attempt-2, no presentado como repetición.
NR01 se volvió a integrar con el arreglo temporal e5d3d6a. Las mediciones de ese
estudio preceden a la identidad aritmética HLLC b353e90.

T05 N800 sí se repitió en ambas campañas P2A. En la FINAL (b353e90):
I=8.525848333Pa, R=-7.182159034Pa,
Rp=-0.84239817, error=0.15760183<0,30,
pico=1, residual masa=2.963108803e-16, energía=2.993304851e-16.
3450 pasos, HLLC2756550, HLLE0, flujos característicos6900; cero rechazos,
CFLmáx0,4. Mínimos rho=1.161374673,
p=99992.38516, T=299.9940772; PASS.
T04 final Rp=0.8424683014; mismo gate original.

## NR01 independiente
Ambas fronteras características con BASE exterior explícita. I=8.525848333Pa,
R=-4.066925612e-06Pa, Rp=-4.770112549e-07,
|Rp|=4.770112549e-07. Solo diagnóstico: no hay nuevo umbral.
Masa residual normalizado=2.207189443e-16,
energía=4.853973407e-16;
min rho=1.161440184, min p=99999.9998,
min T=299.9999997; HLLC2756550/HLLE0/característicos6900.
La BC usa J-_base, K_base/Y_base cuando ingresa material; no obtiene la base
circularmente del interior. Test unitario en ambos extremos.

## Reparaciones acotadas, sin cambio de método
Presupuesto total consumido3/3. La primera ronda R2 retuvo contadores y exterior
no reflectivo; la excepción de velocidad cero fue retirada. R3 es una enmienda
contractual autorizada, no una reparación encubierta.

Segunda reparación e5d3d6a: NR01 encontró cola temporal9,19575e-13 inferior
al mínimo1e-12 antes de una muestra. Se divide anticipadamente el intervalo
restante en pasos admisibles, sin superar CFL, bajar mínimo ni saltar tiempo.
El primer NR01 fallido se conserva en boundary-attempt-1.

Tercera reparación b353e90: en Sod CFL0,2 una cancelación produjo flujo másico
-1,48225e-17 pese a SM=+5,82048e-17; donante correcto pero especie negativa.
Se evalúa la MISMA identidad Rankine–Hugoniot Fmasa*=rho*SM en vez de restar
estados casi iguales. El archivo HLLC cambió en su evaluación aritmética;
no se cambiaron ondas, estados estrella, EOS, HLLE, donante, CFL ni método.
Sin clipping, tolerancia de especie ni limiter. Fixture exacto y test unitario.
Primera campaña:51/52 casos individuales PASS, Sod0,2 FAIL; además ya excedía
T11 la sensibilidad de amplitud0,08336382706. La corrección no resolvió ni
pretendió relajar ese segundo incumplimiento. Ambas campañas se conservan.

## Matriz final P2A — fuente b353e90
Run `20260918T110612-P2_R3-9d1c983a7e65`, tiempo del adaptador
633.063s. Todos52 resultados completados, sin error de infraestructura.

| Test | Estado | Comprobación |
| --- | --- | --- |
| T01 | PASS | Uniforme reposo y movimiento |
| T02 | PASS | Sod, observable hidrodinámico R2 y errores Euler |
| T03 | PASS | Propagación acústica |
| T04 | PASS | Reflexión cerrada |
| T05 | PASS | Reflexión pressure-release |
| T06 | PASS | Contacto/especie, criterio intacto |
| T07 | PASS | Balances periódico/cerrado/abierto |
| T08 | PASS | 18 casos: reposo y flujo, tres geometrías y mallas |
| T09 | PASS | Contacto, inversión y entradas izquierda/derecha |
| T10 | PASS | Convergencia N100/200/400/800 |
| T11 | FAIL | Sensibilidad amplitud pulso CFL0,6 frente0,2 |
| T12 | PASS | Expansión, contacto, especies0/1, frustum reposo |

| CFL pulso | Amplitud Pa | Diferencia /10Pa respecto0,2 | Límite0,08 |
| --- | --- | --- | --- |
| 0.2 | 7.998755313 | 0 | Referencia |
| 0.4 | 8.384220394 | 0.03854650811 | PASS |
| 0.6 | 8.832393583 | 0.08336382706 | FAIL |

La diferencia0,8336382706Pa supera0,8Pa; exceso0,0336382706Pa.
No se reduce CFL, modifica amplitud/malla, ni aumenta0,08. P2A permanece
bloqueado aunque todos los casos aislados aprueben. No se usa P2B para rescatarlo.

T08: equilibrio estático presión Linf normalizada máxima1,2019882e-13<1e-12;
sin well-balancing nuevo. Flujos smooth/frustum convergen y N400 cumple0,01
para rho/u/p. T10 órdenes rho0,93456/0,96692/0,98337 y especie
0,93162/0,96505/0,98231, todos>=0,7. T12 expansión mantiene rho/p/T positivos,
especie en[0,1], seis fallbacks HLLE por estrella inadmisible, sin limiter.

Peor ledger final=6.534486494e-15<1e-10.
Contabilidad total: HLLC36252480 + HLLE6 = Riemann36252486;
37918 flujos característicos directos separados. Cara periódica compartida una
vez; llamadas anteriores a un fallo de frontera y ghost real de fallback probados.

## Pruebas, evidencia y pendientes
25 unit tests de la campaña final PASS:11 test_gas1d,8 test_p2_fixes y6 test_p1_r3.
No equivalen al gate científico P2A. Comandos reales:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_gas1d.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_p2_fixes.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_p1_r3.py -v
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P2_R3 --dependency P0=docs/gasdynamic/p0_accepted_dependency.json --dependency P1=docs/gasdynamic/p1_accepted_dependency.json --dependency P1_R3_BOUNDARY_SEMANTICS_REVIEW=results/p1-r3-fronteras-20260918/reviewed-evidence.json
```
El comando formal devuelveBLOCKED; no relanzarlo para intentar obtener otro resultado.
Evidencia: `results/p1-r3-fronteras-20260918/`, intentos originales intactos,
arrays comprimidos, logs, inventarios SHA256 y figuras de datos numéricos.
Autorrevisión de alcance y revisión independiente son comprobaciones distintas;
no son aceptación manual ni validación experimental.
Pendientes: resolver T11 mediante decisión autorizada; P2B no iniciado;
human gate al final de P2 pendiente. Sin UI/JSON/EXE/0D/P3 ni publicación.

## Revisión y cierre
Revisión independiente read-only `/root/p1_r3_review`: R3 PASS, P2A BLOCKED.
Verificó la derivación, número de condiciones, ausencia de epsilon/velocidad cero,
flujo de cara, medición T05, arrays T11, contadores de52 casos, admisibilidad,
conservación e inventarios. Sin defecto de medición demostrado en T11.
NR01 no se reevaluó después de la identidad algebraica HLLC; su resultado queda
vinculado a e5d3d6a, no a b353e90. No se atribuye validación experimental.

El runner nativo terminó COMPLETED/BLOCKED. Su evidencia se conserva intacta.
`p2a-reviewed-evidence.json` añade revisión real y vuelve a evaluar el gate:
BLOCKED por P2A/T11, revisión no aprobatoria y presupuesto agotado. El campo
scientific_change_required=false no autoriza continuar: no se propone un cambio
científico específico en este cierre; resolver el incumplimiento requiere nueva
decisión explícita. El recibo R3 PASS separado tampoco habilita P2B.

Autorrevisión de alcance: contratos v1/R2, detector T02, EOS, malla, referencias
y baseline0D preservados por hashes; sin cambios de T06/source/producción/UI/JSON.
OpenSpec estricto PASS (`openspec validate p1-r3-fronteras --strict --no-interactive`),
`git diff --check` PASS. No repetir campañas generales para este registro documental.
La eliminación ajena de redme.txt queda fuera de todos los commits de esta orden.

Secuencia de commits locales:67374ce definición; efaa2ab contrato/revisión previa;
1869111 BC/tests; e5d3d6a evidencia y partición temporal;64a72ec gateR3;
b353e90 diagnóstico y evaluación algebraica HLLC. El commit que contiene este
registro incorpora el cierre y la segunda campaña, sin publicación.
P2A bloqueado; P2B/P3 no iniciados; human gate P2 pendiente; cambios sin archivar.
