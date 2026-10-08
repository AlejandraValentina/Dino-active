## P2
- [x] Leer orden/P1 y registrar aceptación P1 sin modificar contrato ni baseline.
- [x] Implementar núcleo aislado first-order y tests unitarios geométricos/numéricos.
- [x] Implementar referencias independientes, matriz contractual y evidencia P2A.
- [x] Ejecutar P2A mediante orquestador; revisar resultados y defectos concretos.
- [x] Revisión independiente read-only y gate P2A.
- [ ] P2B únicamente después de P2A PASS: MUSCL/minmod y SSP-RK2, repetir matriz.
- [x] Verificar hashes/regresiones P0, OpenSpec, documentar gate y commits.

La eliminación previa de redme.txt es ajena y no se incluye. Sin UI, proyecto JSON,
paquete ni P3. Reparaciones después de primera ejecución: 0/3.
11 unit tests iniciales aprobados; aún no acreditan T01–T12 completos.

## Cierre por STOP científico — 17/09/2026
**SCIENTIFIC_CHANGE_REQUIRED**. P2A no aprobado, P2B no implementado y P3 no
iniciado. Fuente `63e2863921a1d7c2434899247876aa6bb03990fb`, ejecución única
`20260917T164812-P2-07051b7effd6` por dev_orchestrator, con P0/P1 aceptadas.
No se usaron reparaciones: 0/3; la condición científica exige STOP inmediato,
no tres modificaciones arbitrarias para intentar aprobar.

T01 PASS, T02 FAIL, T03 PASS, T04 PASS, T05 FAIL, T06 PASS, T07 PASS.
T08 parcial (solo reposo/área constante N100/N200 cerrados), T09–T12 no ejecutados.
12 subcasos registrados:10PASS/2FAIL. T08 N400 estaba en curso al detener;
no se conserva ni acredita como resultado completo. Solver en subcasos registrados:
96,768s; comando de campaña hasta interrupción:113,766s.

T02 Sod: contacto exacto0,6854905240097903, gradiente máximo contractual Y
ubicado0,6925, error0,00700947599=2,80379dx; límite2dx=0,005. Referencia,
ventana e índice comprobados offline por revisor; sin defecto concreto que
permita corregir este incumplimiento dentro de P1. No se cambiaron método,
N, métrica ni umbral. L1ρ0,00723442/L1p0,00565660/L1u0,00991463; el resto
de gates Sod aprobó. Cambiar el contrato requiere nueva decisión científica.

T03: velocidad340,942089m/s, error relativo2,79958e−5, amplitud0,838695 de
referencia. T04: reflexión+0,842468, pico1,000000L/a. T05: parada a17 pasos,
No consistent open-boundary branch; velocidades de rama a redondeo−2,273737e−13
vs+4,547474e−13. Defecto de robustez pendiente, no imposibilidad física.
T06 E1Y0,058714814 y E1ρ/(2ρ0)0,027241539. Peor ledger registrado
1,74253e−15 frente1e−10. HLLE=0 en subcasos registrados; no atribuir T12 PASS.

Revisión independiente read-only `/root/p2_review`: BLOCKED,
scientific_change_required=true. Hallazgos pendientes además de T05:
contadores HLLC incluyen flujos característicos directos/duplicación de cara
periódica, registros fallback de frontera no guardan ghost real; BC no reflectiva
con base explícita mezcla entropía/composición predeterminadas. No se corrigió
ni implementó más código tras STOP. Las cifras HLLC originales no se certifican.

La campaña hijo fue detenida explícitamente al confirmarse T02. El runner
registró gate técnico FAILED_INFRASTRUCTURE por command_failed:p2a_campaign;
se conserva evidence.json intacto, no se disfraza como corrida completa.
La decisión científica y revisión están en artifacts/p2-scientific-decision.json
junto a evidencia técnica original en `results/p2-gas1d-20260917/`.

11 unit tests PASS en ejecución formal (EOS, HLLC/HLLE, especie, geometría,
fronteras, CFL, equilibrio variable corto, ledger y referencia Sod). No equivalen
a T01–T12 completos. P0: hashes intactos y7regresiones exactas offline PASS;
ninguna nueva integración0D. Contrato P1 congelado intacto. OpenSpec estricto
aprobado; autorrevisión de alcance separada de revisión independiente.
Figuras Sod/pulso SVG y PNG derivadas de arrays conservados; Sod inspeccionada
visualmente. No inspección UI/Windows, paquete ni aceptación de P2 atribuida.
Commit de evidencia registra este cierre. Sin publicar ni archivar; redme.txt ajeno.

## Continuación P1-R2 — 18/09/2026
El observable hidrodinámico T02 aprobó y se adoptó 1D_CONTRACT_V1_R2;
el fallo histórico anterior no se reescribe. Ver tareas de p1-r2-contacto.
Retenidos fixes de contabilidad y estado exterior no reflectivo. T05 no aprueba:
ensayo provisional fallido con excepción retirada de velocidadcero; sus dos
ramas son incompatibles también a70dígitos. SCIENTIFIC_CHANGE_REQUIRED para BC,
sin reanudar T01–T12/P2A ni iniciar P2B/P3. Una ronda de reparación/ensayo de3;
las restantes no autorizan modificar física para superar el gate.

## Continuación P1-R3 — 18/09/2026
R3 aprobado tras revisión conceptual previa; BC pressure-release y T05 PASS.
Campaña final `20260918T110612-P2_R3-9d1c983a7e65`, fuente b353e90:
52/52 casos individuales PASS, T01–T10/T12 PASS, **T11 FAIL**.
Sensibilidad amplitud pulso CFL0,6 frente0,2:0,0833638270618394 >0,08.
**P2A BLOCKED** confirmado por revisión independiente; no bug de medición
identificado. No confundir casos individuales con comparaciones agregadas.
25 unit tests PASS; peor ledger6,53449e-15, HLLC36252480/HLLE6;
baselineP0, P1v1/R2, T02/T06 conservados. Reparaciones acumuladas3/3:
contadores/exterior R2; partición temporal R3; identidad aritmética de masa HLLC.
No clipping, nuevos limiters, cambios de método/ondas, CFL o tolerancias.
Primera campaña R3 preservada:51/52 casos PASS y la misma sensibilidad incumplida.
Tablas, deltas y recibos en `../p1-r3-fronteras/tasks.md` y
`results/p1-r3-fronteras-20260918/`. P2B no iniciado; decisión sobre T11 y
human gate de P2 pendientes. Sin P3, aceptación humana atribuida, archivo o push.
Los registros anteriores conservan su estado histórico.

## Continuación P1-R4 — 18/09/2026
**P2A_PASS_FIRST_ORDER_VERIFIED** bajo1D_CONTRACT_V1_R4, revisado de forma
independiente. El estudio congelado demuestra reducción de sensibilidad en
N400/800/1600 y conserva límites de exactitud T03; se retira explícitamente la
garantía8% aN800. El FAIL históricoR3 no se sobrescribe ni desaparece por cálculo.
Run20260918T115319-P2A_R4_VERIFY-7474ef29fc6d: seis integraciones T11 nuevas,
numéricamente idénticas;46 casos reutilizados por hashes,52 reevaluados.
T01–T12 PASS bajoR4; fuente productiva/solver/P0/contratos anteriores intactos.
Ocho pruebas pertinentes PASS, revisión independiente y OpenSpec estricto.
Ver `../p1-r4-cfl/tasks.md` y `results/p1-r4-cfl-20260918/` para tablas y recibos.
Presupuesto de reparaciones3/3 anterior no reiniciado; R4 fue revisión científica
con implementación congelada. P2B no iniciado, human gate deP2 pendiente;
P2 no se declara completo, no P3/publicación/archivo. redme.txt ajeno preservado.

## P2B — orden actual 18/09/2026
- [x] Registrar P1_R4_HUMAN_ACCEPTED y P2A_HUMAN_ACCEPTED por la usuaria, sin aceptación global P2.
- [x] Congelar baseline first-order y verificar presupuesto de reparaciones por fase.
- [x] Implementar MUSCL/minmod y SSP-RK2 sin alterar primer orden ni física.
- [x] Pruebas de reconstrucción, stages, rechazo completo, BC y contadores.
- [ ] Campaña P2B T01–T12 mediante dev_orchestrator con STOP ante bloqueo científico.
- [x] Comparación P2A/P2B y regresión P0/first-order según alcance ejecutado.
- [x] Revisión independiente, OpenSpec estricto, documentación y commits locales.

Registro inicial: P3 prohibido. Presupuesto P2B0/3 al autorizar; el resultado
inferior registra1/3 usado. No se reinicia el presupuesto anterior deP2A.
Se conserva eliminación ajena redme.txt y toda evidencia previa. Sin push/archivo.

## P2B — resultado 18/09/2026
**FAILED_INFRASTRUCTURE**. No P2B/P2 PASS, no P2_HUMAN_ACCEPTED ni P3.
La implementación está registrada, pero la verificación completa queda pendiente.
La usuaria aceptó específicamente P1-R4 y P2A en la orden a7a088e7; recibos
`docs/gasdynamic/p1_r4_human_acceptance.json` y `p2a_human_acceptance.json`.
No se reescriben estados históricos de las secciones anteriores.

### Arquitectura y alcance del diff
`motorsim/gas1d/methods.py` despacha FIRST_ORDER al solver original sin cambios
y MUSCL_SSPRK2 a `second_order.py`. Reconstruye rho/u/p/Y en centroides reales
con minmod de gradientes izquierdo/derecho; periodicidad con desplazamiento L,
ghosts de BC existentes reflejados geométricamente en extremos. Si una cara es
inadmisible, anula todas las pendientes de esa celda según P1, con contador.
No clipping ni nuevos limiters. Una sola evaluación por cara periódica compartida.
SSP-RK2: C1=Cn+dt L(Cn); C2=C1+dt L(C1); Cnuevo=(Cn+C2)/2.
EOS comprueba C1, C2 y Cnuevo; rechazo completo y dt/2, máximo12 reducciones.
BC/source se evalúan en ambas etapas; ledger usa pesos1/2,1/2; registra por etapa
y paso, contadores de trabajo rechazado incluidos. Modos no expuestos en UI.
No cambios en EOS, HLLC/HLLE, source, malla, BC R3, detector R2, baseline ni JSON.
Adaptador `dev_orchestrator/p2b_campaign.py`, fase P2B y entrada declarativa
permiten presupuesto nuevo3 según política existente, sin cambiar configuración.
El orden prioriza positividad y detiene al primer fallo no resuelto.

### Campaña y reparaciones
Fuentes:012caad aceptación/congelación; cd86d7e implementación;
4620200 reparación1 y conservación de intento1. Sin publicación.
Intento1 `20260918T121546-P2B-012ba5672a64`: falso FAIL del comprobador CFL,
T12_contact completo pero dt/unit redondeó0,4000000000000001.
Reparación1/3: registrar dt y límites originales de cada etapa; comprobar la
misma desigualdad exacta dt<=CFL*unit. Sin epsilon, cambioCFL o nueva aritmética
de integración. Prueba acepta ese redondeo y rechaza nextafter(dt,+infinito).
Revisión independiente aprobó la reparación. Intento1 se conserva intacto.

Intento2 `20260918T121838-P2B-abf510d53a0f`: ocho casos PASS, uno incompleto.
T04 agotó120,062s tras2805 pasos, t=0,002684548582421251s frente
objetivo0,00337310127194846s. No se certifica coeficiente de reflexión parcial.
Campaña383,625s (incluye medición/escritura), detenida antes del resto.
El runner nativo registra BLOCKED por P2B=false y hook de revisión no conectado;
el resumen numérico registra FAILED_INFRASTRUCTURE por wall_timeout. Se conservan
ambos; el reviewer real está documentado aparte, nunca sustituido por el stub.
No se amplió120s/subcaso ni se repitió tras el timeout. T10_800 conserva únicamente
la excepción240s ya documentada, pero no llegó a ejecutarse. Presupuesto P2B1/3.

### Matriz contractual
| Gate | MUSCL_SSPRK2 actual | FIRST_ORDER control R4 |
| --- | --- | --- |
| T01 uniforme | PASS (reposo y movimiento) | PASS |
| T02 Sod | PASS | PASS |
| T03 acústica | PASS | PASS |
| T04 reflexión cerrada | Incompleto: timeout, no resultado final | PASS |
| T05 reflexión abierta R3 | No ejecutado; ideal_open_pressure_release previsto | PASS |
| T06 especie/contacto | No ejecutado como gate T06 | PASS |
| T07 conservación | No ejecutado como suite T07 | PASS |
| T08 área variable/tobera | No ejecutado | PASS |
| T09 backflow | No ejecutado | PASS |
| T10 refinamiento | No ejecutado; orden>=1,5 NO acreditado | PASS |
| T11 CFL R4 | No ejecutado en P2B | PASS |
| T12 positividad | Parcial4/10: expansión, contacto, Y=0, Y=1 PASS | PASS |

FIRST_ORDER: reevaluación agregada offline de52 registros congelados y estudioR4
preexistente, con inventarios/hash verificados. No52 integraciones nuevas ni nueva
campaña0D. La prueba de despacho demuestra identidad de resultado FO salvo tiempo.
T12_contact no se presenta como ejecución formal T06; faltan seis frustums T12.

### Casos ejecutados: conservación y coste
| Caso | Pasos | Tiempo s | HLLC | HLLE | Peor ledger de paso | Peor ledger de etapa |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T01_rest | 251 | 1.063 | 50200 | 0 | 0 | 0 |
| T01_moving | 301 | 1.297 | 60200 | 0 | 0 | 0 |
| T12_expansion | 283 | 4.796 | 232971 | 10 | 1.77636e-15 | 1.16805e-16 |
| T12_contact | 3125 | 66.578 | 2600000 | 0 | 8.71265e-15 | 1.57377e-16 |
| T12_pure0 | 3308 | 69.219 | 2892800 | 0 | 8.83712e-15 | 1.57377e-16 |
| T12_pure1 | 3308 | 69.172 | 2892800 | 0 | 8.83712e-15 | 1.57377e-16 |
| T02_sod | 547 | 11.141 | 526914 | 0 | 2.50216e-16 | 9.88014e-17 |
| T03 | 901 | 37.063 | 1439798 | 0 | 2.39194e-16 | 1.55744e-16 |
| T04 | 2805 | 120.062 | 4648800 | 0 | 2.36012e-16 | 1.5919e-16 |

T04 es parcial; su tiempo no compara soluciones al mismo instante.
Todos los estados aceptados/etapas registrados cumplen rho,p,T>0 y0<=Y<=1.
Cero downgrades observados; los10HLLE son de expansión, motivo inadmissible_star
(vs6 en FO). Rechazos contabilizados exclusivamente por CFL de etapa (1918). En los nueve
registros, incluidoT04parcial:15344483HLLC y10HLLE; no comparar este total parcial
con el total de52casosFO como si fueran campañas equivalentes.
No se midió memoria pico; no se afirma memoria/coste completo de P2B.

### Sod y acústica: comparación al mismo tiempo final
| Métrica | FIRST_ORDER | MUSCL_SSPRK2 |
| --- | ---: | ---: |
| Sod rho_L1 | 0.00723442066 | 0.00224489335 |
| Sod u_L1 | 0.00991462899 | 0.00329297951 |
| Sod p_L1 | 0.00565659557 | 0.00149620259 |
| Sod shock_position_error | 0.00206885359 | 0.00206885359 |
| Sod contact_position_error | 0.00299052401 | 0.00200947599 |
| T03 speed | 340.942089 | 340.945549 |
| T03 speed_relative_error | 2.7995799e-05 | 3.81443152e-05 |
| T03 amplitude | 8.38422039 | 9.63078348 |
| T03 pressure_L1 | 0.0120447663 | 0.00121933551 |
| T03 pressure_L2 | 0.0325611719 | 0.00464874455 |
| T03 disipación 1−A/Aexacta | 0.161305028 | 0.0366081392 |
| T03 error de desplazamiento de centroide, m | 1.25981096e-05 | 1.71649419e-05 |
| T03 tiempo s | 12.032 | 37.063 |

La fase se representa por desplazamiento de centroide al tiempo final, no ángulo
de un armónico. MUSCL reduce difusión pero no mejora universalmente velocidad/fase;
ambas velocidades cumplen1%. R2 localiza el contacto Sod sin usarY ni exacta;
error0,803790396Δx, shock0,827541438Δx, ambos<=2Δx. DiagnósticosY:
Agradiente0,690; Bcruce0,688744681463; Ccentroide0,687914924708;
Dhidrodinámico0,6875, exacto0,685490524010. Son diagnósticos, no cambio de gate.

### Refinamiento disponible
Solo control histórico FO. MUSCL no tiene una serie T10 ejecutada y no se infiere
orden desde Sod/contactos. Se conservan pares contractuales200/400 y400/800>=1,5.
| N | dx | FO rho L1 | FO rho L2 | FO rhoY L1 | FO rhoY L2 | Orden rho L1 desde N anterior | MUSCL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | 0.01 | 0.0107372934 | 0.0119258212 | 0.027045011 | 0.0300422554 | — | No ejecutado |
| 200 | 0.005 | 0.00561778718 | 0.00623977322 | 0.0141788741 | 0.0157516124 | 0.934556 | No ejecutado |
| 400 | 0.0025 | 0.00287404547 | 0.00319226086 | 0.00726325816 | 0.00806932308 | 0.966919 | No ejecutado |
| 800 | 0.00125 | 0.00145368239 | 0.00161463514 | 0.00367642097 | 0.00408454332 | 0.983371 | No ejecutado |

No nuevas conclusiones sobre T05, tobera, backflow o sensibilidadCFL en P2B.
El refinamiento R4 de MUSCL sigue pendiente; el8% histórico no se restaura.

### Regresión, revisión y comandos
49 pruebas pertinentes PASS (nueve P2B más FO, fixes, R2/R3/R4), log conservado.
Siete regresiones históricasP0 exactas offline PASS; hashes de producción,
baseline0D y31 archivos congelados coinciden. UI/JSON y solverFO sin cambios.
Revisión independiente real por `/root/p2b_review`: implementación/fix aprobados
en alcance revisado; cierre bloqueado correcto, no aprobación global P2B.
Autorrevisión: alcance Git, hash/inventarios, documentación y pendientes; distinta
de la revisión independiente. OpenSpec estricto PASS.

Ejecución formal desde raíz (no repetir sin resolver el bloqueo):
```powershell
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P2B --dependency P0=docs/gasdynamic/p0_accepted_dependency.json --dependency P1_R4_CFL_REVIEW=docs/gasdynamic/p1_r4_accepted_dependency.json --dependency P2A_R4_VERIFY=docs/gasdynamic/p2a_accepted_dependency.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_p2b.py -v
openspec validate p2-nucleo-gas1d --strict --no-interactive
```
Suite49: patrones test_p2b.py, test_gas1d.py, test_p2_fixes.py,
test_p1_r2.py, test_p1_r3.py, test_p1_r4.py y test_p1_r4_gate.py mediante unittest.
Evidencia en `results/p2b-gas1d-20260918/`: intentos originales, decision.json,
independent-review.json, regression.json y verification-tests.log.
Pendiente: resolver límite operativo sin cambiar ciencia; terminar T04–T11 y
frustumsT12; acreditar orden, CFLR4 y gate integral; después aceptación humanaP2.
No P3, empaquetado, publicación ni archivo. Eliminación ajena redme.txt preservada.

## Reanudación P2B con 300 s — resultado
**P2_BLOCKED_SECOND_ORDER / SCIENTIFIC_CHANGE_REQUIRED**. No P2 PASS ni P3.
Orden12b4cba5 autorizó únicamente timeout operativo: old_timeout=120s,
new_timeout=300s, reason=infrastructure/runtime only. T10_800 tenía excepción240s,
ahora también300s. Tiempo físico, CFL, mallas y todos los criterios sin cambios.
No hubo optimizaciones del solver. No fue necesario perfilarT04: aprobó150,968s.
Los dos nuevos timeouts no se presentan como fallos científicos; existe además
un incumplimiento R4 independiente que impide aprobar aunque se resuelvan ambos.

- [x] T04 primero aislado; continuar sólo tras PASS y preservar su evidencia.
- [x] T05–T09 completos, con persistencia por subcaso y gate.
- [ ] T10 completo: falta solución finalN800 y pareja400→800.
- [ ] T11 R4: faltaN1600/CFL0,2; además falla comparación disponible0,4/0,6.
- [x] T12 completo10/10; cuatro previos reutilizados con identidad verificada.
- [x] Regresión P0/first-order, revisión puntual, OpenSpec y commits locales.
- [ ] Gate global P2 y aceptación humana; no elegibles.

### Resultado contractual y limitaciones
| Gate | Resultado actual |
| --- | --- |
| T01–T03 | PASS reutilizado con hashes/inputs/configuración/solver idénticos |
| T04 | PASS,150,968s |
| T05 | PASS,150,953s |
| T06 | PASS,66,515s |
| T07 | PASS,3/3 |
| T08 | PASS,18/18 y comparaciones de refinamiento |
| T09 | PASS,4/4 |
| T10 | Incompleto:3/4 soluciones finales;N800timeout |
| T11 | FAIL R4 en comparación completa0,4/0,6;11/12 soluciones finales |
| T12 | PASS,10/10 |

58 registros:56 completos y2 incompletos. No confundir registros con soluciones
finales. Última fase:18 integraciones nuevas(17completas),39PASS reutilizados,
1timeout retenido SIN crédito. Las otras32 integraciones de esta orden están en
resume-300-attempt-1 (31completas). Totales de dos fases:50 integraciones nuevas,
48completas,2timeouts; ocho resultados anteriores reutilizados. El intento de ruta
relativa no integró ningún caso. No repeticiones automáticas de resultados acreditados.

### T04 y T05
| Métrica | T04 | T05 |
| --- | ---: | ---: |
| Tiempo real s | 150.968 | 150.953000001 |
| Pasos | 3509 | 3510 |
| RHS | 7243 | 7231 |
| HLLC | 5794400 | 5777569 |
| HLLE | 0 | 0 |
| Flujos característicos | 7243 | 14462 |
| dt mínimo s | 7.34968071646e-11 | 1.67612205799e-10 |
| dt máximo s | 1.46652916971e-06 | 1.46648196472e-06 |
| CFL máximo diagnóstico | 0.4 | 0.4 |
| Coeficiente de reflexión | 0.975062687919 | -0.974345496683 |
| Error coeficiente | 0.0249373120811 | 0.0256545033169 |
| Error tiempo pico escalado | 0.002 | 0.002 |
| Ledger máximo | 9.67042442344e-16 | 9.64469826127e-16 |
| Ledger etapa máximo | 1.59190256723e-16 | 1.59276521307e-16 |

Evaluaciones de flujo = HLLC+HLLE+flujos característicos (una cara periódica común
se cuenta una vez). T05 utiliza exclusivamente ideal_open_pressure_release R3.
Prefijos completos de ledgers por paso y etapa T04 idénticos al intento120s.
Memoria pico no medida; no se atribuye una cifra por caso.

### T10: refinamiento suave
| N | dx | L1 rho | L2 rho | L1 rhoY | L2 rhoY | Orden rho / rhoY desde anterior | Tiempo s |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 100 | 0.01 | 0.0009133376138 | 0.001238029176 | 0.002282941282 | 0.003132136493 | — | 8.015 |
| 200 | 0.005 | 0.000251371132 | 0.000393951711 | 0.0006286779731 | 0.0009970951769 | 1.861329272 / 1.860500632 | 32.047 |
| 400 | 0.0025 | 6.76194769e-05 | 0.0001247924833 | 0.0001691384659 | 0.0003159031665 | 1.894308216 / 1.894116418 | 129.469 |
| 800 | 0.00125 | — | — | — | — | No acreditado | 300.047 timeout |

200→400 supera1,5 en ambas magnitudes. No inferir400→800, ni calcular error
final usando el estado parcialN800: t=0,008266995416406504s frente
0,014665657704123739s (56,3698%),7069pasos,14138RHS,0rechazos.
Presupuesto300s no se amplió. Comparación FO completa sigue en tabla anterior;
N400 FO L1rho0,00287404547 frente MUSCL0,0000676194769, pero falta el gate global.

### T11: R4, sin volver al 8 por ciento
A=max_i(p_i−100000Pa) al tiempo final; S=abs(Aa−Ab)/10Pa.
El casoN1600/CFL0,2 no completó:300,094s,3578pasos,7156RHS,0rechazos;
t=0,0013117299762084292s frente0,0013199091933711366s (99,3803%).
No se usa ese estado parcial como si estuviera en el tiempo final.

| N | CFL | A final Pa | Error amplitud frente referencia /10Pa | Tiempo s |
| --- | ---: | ---: | ---: | ---: |
| 400 | 0.2 | 9.14443393229 | 0.0842560479141 | 18.750 |
| 400 | 0.4 | 9.1483281148 | 0.0838666296637 | 9.219 |
| 400 | 0.6 | 9.14993965974 | 0.0837054751697 | 6.125 |
| 800 | 0.2 | 9.62864623751 | 0.0368099507599 | 74.203 |
| 800 | 0.4 | 9.63078348491 | 0.0365962260199 | 37.515 |
| 800 | 0.6 | 9.63281855416 | 0.0363927190949 | 30.469 |
| 1600 | 0.2 | — incompleto | — | 300.094 |
| 1600 | 0.4 | 9.84536868558 | 0.0153817571947 | 153.578 |
| 1600 | 0.6 | 9.8463535082 | 0.0152832749329 | 125.234 |

Comparación COMPLETA de CFL0,4 frente0,6:
| N | Sensibilidad S |
| --- | ---: |
| 400 | 0,00016115449398057535 |
| 800 | 0,00020350692502688617 |
| 1600 | 0,00009848226181929931 |

**FAIL: S400>S800 no se cumple.** Es independiente del caso0,2 que agotótiempo.
Los seis arrays involucrados sí tienen tiempo final completo; el revisor recalculó
A desde primitive y obtuvo exactamente esos valores. Que sean pequeños no autoriza
relajar la monotonía estricta R4 ni restaurar8%. El error frente referencia disminuye
para0,4 y0,6; comparaciones Sod y velocidad disponibles PASS. Las comparaciones
que necesitan0,2/N1600 quedan pendientes. No se atribuye defecto al solver.

### T12: diez subcasos
| Caso | Resultado | Tiempo de su registro s | Procedencia |
| --- | --- | ---: | --- |
| T12_contact | PASS | 66.578 | Reutilizado; fuente/inputs/config/hash exactos |
| T12_expansion | PASS | 4.796 | Reutilizado; fuente/inputs/config/hash exactos |
| T12_frustum_0_100 | PASS | 1.657 | Nueva integración de esta orden |
| T12_frustum_0_200 | PASS | 5.204 | Nueva integración de esta orden |
| T12_frustum_0_400 | PASS | 25.828 | Nueva integración de esta orden |
| T12_frustum_1_100 | PASS | 1.641 | Nueva integración de esta orden |
| T12_frustum_1_200 | PASS | 5.157 | Nueva integración de esta orden |
| T12_frustum_1_400 | PASS | 25.688 | Nueva integración de esta orden |
| T12_pure0 | PASS | 69.219 | Reutilizado; fuente/inputs/config/hash exactos |
| T12_pure1 | PASS | 69.172 | Reutilizado; fuente/inputs/config/hash exactos |

Sin clipping ni positivity limiter nuevo; rho,p,T positivos y0<=Y<=1 en etapas
aceptadas registradas. Diez fallbacksHLLE en expansión, motivo inadmissible_star,
cero downgrades; contadores incluyen evaluaciones de intentos rechazados.
En58registros,incluidosdosparciales:95669790HLLC+10HLLE; no comparar ese total
con52casosFO como si fueran el mismo trabajo. Peor ledger8,94291151549e−15;
peor ledger por etapa1,97476173377e−16, ambos bajo1e−10.

### Tiempos por caso y comparación FO
Tiempos reales de integraciones guardadas, no del coste de reutilizar archivos.
Nuevos enestaorden salvo T01–T03 ycuatroT12 señalados como previos.
| Caso | Estado | MUSCL s | FO histórico s |
| --- | --- | ---: | ---: |
| T01_moving | Completo | 1.297 | 0.406 |
| T01_rest | Completo | 1.063 | 0.438 |
| T02_sod | Completo | 11.141 | 2.453 |
| T02_sod_0.2 | Completo | 19.500 | 4.984 |
| T02_sod_0.4 | Completo | 11.125 | 2.515 |
| T02_sod_0.6 | Completo | 9.250 | 1.672 |
| T03 | Completo | 37.063 | 12.032 |
| T03_0.2 | Completo | 74.203 | 23.984 |
| T03_0.2_N1600 | Timeout parcial | 300.094 | — |
| T03_0.2_N400 | Completo | 18.750 | — |
| T03_0.4 | Completo | 37.515 | 12.219 |
| T03_0.4_N1600 | Completo | 153.578 | — |
| T03_0.4_N400 | Completo | 9.219 | — |
| T03_0.6 | Completo | 30.469 | 8.172 |
| T03_0.6_N1600 | Completo | 125.234 | — |
| T03_0.6_N400 | Completo | 6.125 | — |
| T04 | Completo | 150.968 | 46.156 |
| T05 | Completo | 150.953 | 46.079 |
| T06_contact | Completo | 66.515 | 20.047 |
| T07_closed | Completo | 2.594 | 0.890 |
| T07_open | Completo | 2.610 | 0.890 |
| T07_periodic | Completo | 3.032 | 0.984 |
| T08_constant_flow_100 | Completo | 1.453 | 0.469 |
| T08_constant_flow_200 | Completo | 14.047 | 1.907 |
| T08_constant_flow_400 | Completo | 61.406 | 7.766 |
| T08_constant_rest_100 | Completo | 1.062 | 0.422 |
| T08_constant_rest_200 | Completo | 4.188 | 1.625 |
| T08_constant_rest_400 | Completo | 19.250 | 7.000 |
| T08_frustum_flow_100 | Completo | 2.469 | 0.531 |
| T08_frustum_flow_200 | Completo | 8.594 | 2.000 |
| T08_frustum_flow_400 | Completo | 29.265 | 8.015 |
| T08_frustum_rest_100 | Completo | 1.547 | 0.453 |
| T08_frustum_rest_200 | Completo | 5.296 | 1.781 |
| T08_frustum_rest_400 | Completo | 31.656 | 6.813 |
| T08_smooth_flow_100 | Completo | 3.125 | 0.500 |
| T08_smooth_flow_200 | Completo | 12.078 | 2.000 |
| T08_smooth_flow_400 | Completo | 45.796 | 8.094 |
| T08_smooth_rest_100 | Completo | 1.484 | 0.484 |
| T08_smooth_rest_200 | Completo | 6.625 | 1.750 |
| T08_smooth_rest_400 | Completo | 32.188 | 7.438 |
| T09_contact | Completo | 66.062 | 20.422 |
| T09_inleft | Completo | 29.531 | 10.250 |
| T09_inright | Completo | 27.891 | 10.218 |
| T09_reverse | Completo | 62.391 | 20.406 |
| T10_100 | Completo | 8.015 | 2.656 |
| T10_200 | Completo | 32.047 | 10.797 |
| T10_400 | Completo | 129.469 | 44.000 |
| T10_800 | Timeout parcial | 300.047 | 171.438 |
| T12_contact | Completo | 66.578 | 20.000 |
| T12_expansion | Completo | 4.796 | 1.296 |
| T12_frustum_0_100 | Completo | 1.657 | 0.422 |
| T12_frustum_0_200 | Completo | 5.204 | 1.781 |
| T12_frustum_0_400 | Completo | 25.828 | 6.844 |
| T12_frustum_1_100 | Completo | 1.641 | 0.453 |
| T12_frustum_1_200 | Completo | 5.157 | 1.672 |
| T12_frustum_1_400 | Completo | 25.688 | 6.750 |
| T12_pure0 | Completo | 69.219 | 19.828 |
| T12_pure1 | Completo | 69.172 | 20.000 |

Tiempos de casos incompletos no comparan avance físico igual. Acústica y Sod
mantienen tablas previas; se confirma menor difusiónT03, no mejora universal de fase.
T08smooth/frustum reduce errores al refinar, y backflowT09 cumple signo y donor.
Datos detallados, L1 y contadores por caso en resume-remaining-final/artifacts.

### Correcciones, revisión y estado de cierre
Reparación2/3: rutaCLI relativa del checkpoint no resuelta y precedencia de
clasificación científica; falló antes de integrar. Se preserva remaining-path-failure.
Reparación3/3: el agregador sólo evaluaba comparaciones con toda la suite completa,
lo que ocultó la parejaR4disponible al existir otrotimeout. Ahora evalúa cada
comparación con sus propios inputs finales completos. Un FAIL científico ya no
se trata como mero timeout ni permite avanzar. Prueba focal reproduce exactamente
la omisión. También distingue registros de casos realmente completos.

La fase ejecutóT12 antes de detectar esa omisión; sus resultados son reales y se
conservan. Tras detectar el FAIL científico no hubo nuevas integraciones. La
reevaluación fue offline, sobre arrays intactos. Los reportes originales quedaron
sin reescribir; resume-decision.json y resume-reevaluated-gates.json corrigen su
interpretación. El runner original diceBLOCKED y su resumen sóloinfra; no son el
estado científico vigente después de la reparación y revisión.

Revisión independiente `/root/p2b_review`: confirma desde seis arrays finales
el incumplimientoR4, aprueba fixes2/3 y3/3 y corrige expresamente su conclusión
anterior de sóloinfra. No identifica defecto del solver que invalide los resultados.
Autorrevisión separada: alcance, hashes, conteos, artefactos y documentación.
60 pruebas pertinentes PASS; siete regresiones históricasP0 offline PASS;
solver/contratos/P0 exactos, controlFO52 registros bajoR4 PASS y focal de despacho
idéntico incluido en pruebas. No nuevas integraciones0D. OpenSpec estricto PASS.

PresupuestoP2B **3/3 consumido**; no reiniciado por fases operativas. No más ajustes,
rescates o campañas sin nueva orden. Para cerrarP2 falta resolver el incumplimiento
científicoR4 y las dos integraciones incompletas, sin atribuirles aceptación humana.
P1_R4_HUMAN_ACCEPTED yP2A_HUMAN_ACCEPTED permanecen; noP2_HUMAN_ACCEPTED.
Sin P3, publicación, archivo, UI/JSON/EXE ni configuración global. redme.txt ajeno.

Comandos ejecutados desdeE:\dino\Dino:
```powershell
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P2B_RESUME --dependency P0=docs/gasdynamic/p0_accepted_dependency.json --dependency P1_R4_CFL_REVIEW=docs/gasdynamic/p1_r4_accepted_dependency.json --dependency P2A_R4_VERIFY=docs/gasdynamic/p2a_accepted_dependency.json
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P2B_REMAINING --dependency P0=docs/gasdynamic/p0_accepted_dependency.json --dependency P1_R4_CFL_REVIEW=docs/gasdynamic/p1_r4_accepted_dependency.json --dependency P2A_R4_VERIFY=docs/gasdynamic/p2a_accepted_dependency.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_p2b*.py' -v
openspec validate p2-nucleo-gas1d --strict --no-interactive
```
Suite60: test_p2b*.py, test_gas1d.py, test_p2_fixes.py,
test_p1_r2.py, test_p1_r3.py, test_p1_r4.py y test_p1_r4_gate.py con unittest.
Commits operativos8ed6079,e92c1e3,6b6a7dc; el commit de cierre registrafix3,
reevaluación y evidencia final. Todos locales, sinpush.


## P1-R5 — revisión offline (18/09/2026)

- [x] Reproducir ocho finales T11 y conservar N1600/CFL0,2 como parcial.
- [x] Verificar hashes de evidencia/solver e identidad canónica de inputs/configuración.
- [x] Calcular amplitudes desde arrays, referencia conservativa, errores absolutos/relativos, tres parejas CFL, cuatro balances, etapas y contadores.
- [x] Examinar fundamento SSP y contraejemplo lógico sin ajustar tolerancias.
- [ ] Aprobar científicamente R5: falta evidencia final N1600/CFL0,2.
- [ ] Fase B: completar T10 N800 y T11 N1600/CFL0,2 con600s, solo tras PASS científico.
- [ ] Fase C: cierre P2 T01–T12, regresiones P0 y aceptación humana.

Estado **P1_R5_CFL_SECOND_ORDER_UNRESOLVED / P2_BLOCKED_SECOND_ORDER**.
No se adopta contrato nuevo. R4 continúa FAIL en pareja0,4/0,6; no se descarta
N800. La evidencia disponible admite una interpretación preasintótica, pero
no acredita las cláusulas para los tres CFL. Fases B/C no ejecutadas; orden
T10 400→800 desconocido. T01–T09 y T12 conservan PASS histórico, no reejecutado.
P0 y P2A no reintegrados; sin cambios a contratos, solver, UI o formatos.
Resultados y justificación: results/p1-r5-cfl-20260918/analysis.md y study.json.
Reproductor: `.\.venv\Scripts\python.exe -m dev_orchestrator.p1_r5_offline`.
La revisión independiente se registra en review.json separada de autorrevisión.
Sin publicación, archivo ni P3; borrado ajeno redme.txt conservado.

- [x] Revisión independiente read-only /root/p1_r5_review: PASS de reproducción y STOP, NO PASS científico R5. Máximo residuo registrado4.911264175817217e-16.
- [x] Tres pruebas focales del reproductor PASS; OpenSpec estricto p2-nucleo-gas1d PASS. Autorrevisión de alcance separada.

## P1-R5E — adquisición autorizada separada de adopción

Orden594e5cc0 autoriza exactamente T10 N800 y T11 N1600/CFL0,2 con600s cada uno, sin alterar solver/criterios. Sustituye el bloqueo de adquisición de R5, no adopta R5.
- [x] Adquirir ambos casos y conservar hashes, arrays y ledgers.
- [x] Reconstruir matriz3x3 y órdenes T10.
- [x] Revisión científica independiente con datos completos; adoptar R5 únicamente si justificado.
- [x] Evaluar P2 completo únicamente tras R5 PASS.


### Resultado P1-R5E / cierre técnico P2 — 18/09/2026

**P1_R5_PASS_CFL_SECOND_ORDER_CONTRACT**: adoptado1D_CONTRACT_V1_R5 en1228907
tras revisión independiente de nueve finales. Se retira SOLO la monotonía
S400>S800>S1600 para segundo orden; S1600<S400 en las tres parejas junto con
E_A400>E_A800>E_A1600 por CFL y todos gates padre. PerfilesL1/L2 corroboran;
fase no siempre monótona, registrada dentro de límites originales. No nueva
cota empírica, sin omitir N800. FIRST_ORDER conservaR4. Históricos intactos.

T10N800 PASS:526.656s,12541pasos,25082RHS,20065600HLLC,0HLLE.
L1rho1.80354721771955e-5, L1rhoY4.510362247099889e-5.
Orden200→400rho1.89430821594/especie1.89411641807;
400→800rho1.90660166169/especie1.90688958599: criterio>=1.5 intacto.
T11N1600/CFL0.2 completo diagnóstico:304.844s,3601pasos,7202RHS,
11515998HLLC,0HLLE; A9.844305254606297Pa, Eabs0.15488100291986484Pa,
Erel0.015489360727058105. Luego evaluado bajoR5 adoptado: PASS.

[Tablas completas3x3, sensibilidades, dt, balances, perfiles y rendimiento](../../../results/p1-r5e-20260918/analysis.md).
58 finales:56 reutilizados con hashes y2nuevos. T01–T12 PASS; T1210/10.
Máximo residuo8.942911515485987e-15 (<1e-10), admisibilidadPASS;
HLLC104498544,HLLE10,RHS189503 para el conjunto final. Memoria global no medida.
Integraciones nuevas831.500s sumados, mayor caso526.656s. Ningún timeout600.
ReutilizaciónFO52casos bajoR4 PASS; siete regresiones históricasP0 offline PASS.
No nuevas campañas0D; producción/solver/contratosP1–R4 exactos.

- [x] 70 pruebas pertinentes PASS (logs en verification), incluyendo caso Sod ausente.
- [x] Revisión científica independiente /root/p1_r5_review PASS.
- [x] Revisión final puntual independiente PASS, sin hallazgos pendientes.
- [x] Autorrevisión separada de alcance/hashes/evidencia y conservación del borrado ajeno redme.txt.
- [x] P2_HUMAN_ACCEPTED: orden posterior a75bf738 del18/09/2026; recibo separado docs/gasdynamic/p2_human_acceptance.json. No modifica la evidencia histórica WAITING_HUMAN_APPROVAL.

Estado derivado **P2_PASS_1D_CORE_VERIFIED / WAITING_HUMAN_APPROVAL**.
Los reportes nativos BLOCKED/review_not_approved permanecen intactos: el hook
no tiene reviewer real. Dictámenes reales separados y hashes en scientific-review,
final-review y decision.json; no se presenta el stub como revisión.
Los pendientes históricos P1-R5 se resolvieron AHORA por ordenR5E, no retrospectivamente.
Primer registro de fase falló antes de ejecutar por UTF8/roadmap; setup-failure
preservado. Reproductor corrigió ruta relativa antes de análisis, sin reintegrar.
Observación del revisor sobre integridad12/12 y comparativas se corrigió y probó;
ninguna reparación numérica/científica ni modificación del presupuesto3/3 anterior.
Sin publicación, archivo, aceptación humana P2, UI/EXE/JSON ni inicioP3.

Comandos: `python -m dev_orchestrator.runners.run_phase P1_R5E` y
`python -m dev_orchestrator.runners.run_phase P2_R5_VERIFY`, usando
`.venv\Scripts\python.exe` y las dependencias P0, P1_R4_CFL_REVIEW,
P2A_R4_VERIFY de docs/gasdynamic (argv exactos en los logs/evidence.json).
Reproducción de tablas mediante dev_orchestrator.p1_r5_review indicada en analysis.md.

- [x] OpenSpec estricto p2-nucleo-gas1d PASS tras registrar R5 y cierre; git diff --check PASS.
