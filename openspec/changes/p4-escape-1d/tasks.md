## P4 — orden cec0f5b3
- [x] Registrar aceptación humanaP3, congelar baseline y archivar cambio aceptado.
- [x] Revisión independiente inicial de contrato de puerto y limitaciónBCexterior.
- [x] Formalizar fixtures y ejecutar P4A/E01–E05 cuantitativos; revisión independiente PASS.
- [ ] P4B/E06–E11, reflexiones, longitud, RPM, refinamiento y CFL.
- [ ] Sólo trasP4A/P4B PASS: camino híbrido, revolución cronometrada y E12–E15.
- [x] RegresionesP0/P2/P3 y revisión independiente final (confirma bloqueo, noP4PASS).
- [ ] Gate final y aceptación humana posterior. NoP5.

P3 archivado con14/19 tareas: las5 restantes son casillas históricas reservoir,
explícitamente sustituidas porR1; no se marcaron como realizadas. CierreR1 y
aceptación humana acreditados. Se preserva borrado ajeno redme.txt.

## Estado final — P4_BLOCKED_WAVE_PHYSICS / SCIENTIFIC_CHANGE_REQUIRED
P3 aceptado por la usuaria y archivado en2026-09-18-p3-acoplamiento-conservativo.
Baseline ec6ec55 y72 evidenciasP3 intactos; aceptación en docs/gasdynamic/p3_human_acceptance.json.
P4 no se archiva. No motor híbrido, convergencia periódica, potencia indicada ni
comparación entre ciclosmotor: dependen deP4B PASS que no se obtuvo. NoP5.

Implementado sólo banco experimental aislado: puerto variableideal, cara dividida
P3+pared reflectiva, integrador conjuntoSSPRK2 con eventos/CFL, adaptador de ductos
existentes, sensores/snapshots/ledgers. El camino2T_0D_BASELINE sigueintacto.
P4C/2T_0D1D_EXHAUST de motor no creado; no presentar banco como motorhíbrido.

| Gate | Resultado |
|---|---|
| E01–E05 cerrado/apertura/descarga/cierre/backflow | PASS, revisión independiente |
| E06–E09 recto/difusor/convergente/cadena | Casos individuales PASS |
| E10 longitud, incluido control a volumen idéntico | PASS |
| E11 RPM y eventos (banco, no motor) | PASS |
| Refinamiento difusor | PASS |
| Refinamiento descarga | FAIL en presión integrada y masa |
| SensibilidadCFL focal ambos bancos | PASS |
| E12–E14 motor/conservación/convergencia/comparación | NOT_RUN, bloqueados porP4B |
| E15 positividad | PASS en19 bancos; motor NOT_RUN |

Criterios congelados antes de ejecutar: no se ajustaron tras resultados.
Mayor residuo global normalizado3.378286968e-15. Puerto cerrado:m/E/F exactamente0.
Backflow al cilindro usaYlocal~.2, noYatmósfera0. Reacción axial sobre abertura
y paredcomplementaria registrada porstage. Cd1, sin calibración/pérdida añadida.
Eventos físicos90°/112.2040961°/247.7959039°/270°, Amax200mm², todos alcanzados.

## Incumplimiento de refinamiento — descarga
| N | Integral presión (Pa·s) | Intercambio masa (kg) | Arrival (s) |
|---|---:|---:|---:|
| 100 | 164.729319651 | -9.70056603322e-05 | 0.00087477247055 |
| 200 | 164.804998778 | -9.70077286939e-05 | 0.000879296215498 |
| 400 | 164.899734482 | -9.70099933774e-05 | 0.000874901407169 |

Diferencias presión .0756791278→.0947357040 Pa·s; masa2.06836170034e-9→
2.26468347229e-9kg: ambas aumentan. Revisor recalculó desdehistory, flujos por
stage y cambio final de masa, descartando bugdelagregador. Sensores reales
.099/.1005/.09975m; fallo de masa independiente de posiciónsensor. Magnitud
pequeña no autoriza relajar el criterio. Causa numérica/física no determinada.
No atribuirla a la BC sin evidencia. No repetir bancos ni iniciarP4C.

Timingblowdown: llegada102kPa sensores .099/.297m en .000873870597/.001438368459s;
delta .000564497862s dentro envolvente .000328402386.. .000615957624s.
Velocidades u+a muestreadas340.9325..544.5545m/s; no trayectoria reconstruida ni
validación de amplitud fuerte. Pulso débil100Pa separado para coeficientes.
Longitud/cadena: cambiarheader.2→.3m retrasa onda; controlheader+.1/tail−.1
conserva volumen4.08407045e-4m³ y también retrasa retorno. No es sólo volumen.
RPM2500/3000/3500: misma llegada física.000729366873s, ángulos190.9405031 /
193.1286037 /195.3167043°. No acredita régimenperiódico.

## Casos ejecutados y conservación
19 integraciones nuevas, todas completas;510.907s sumados dentro delsolver,
no tiempo total de orquestación. Máximo271.25s, inferior600s; no timeoutfísico.

| Caso | Tiempo (s) | Residuo global máximo |
|---|---:|---:|
| closed_N100_CFL0.4 | 1.828 | 1.6144e-16 |
| blowdown_N100_CFL0.4 | 17.844 | 1.9855e-15 |
| backflow_N100_CFL0.4 | 5.406 | 6.3219e-16 |
| straight_N100_CFL0.4_RPM3000 | 2.031 | 4.2153e-16 |
| diffuser_N100_CFL0.4_RPM3000 | 2.641 | 4.3901e-16 |
| converger_N100_CFL0.4_RPM3000 | 3.422 | 1.2541e-15 |
| chain_N100_CFL0.4_RPM3000 | 4.000 | 7.3072e-16 |
| long_N100_CFL0.4_RPM3000 | 4.469 | 5.3439e-16 |
| equal_volume_N100_CFL0.4_RPM3000 | 4.281 | 5.6364e-16 |
| chain_N100_CFL0.4_RPM2500 | 3.938 | 7.3072e-16 |
| chain_N100_CFL0.4_RPM3500 | 3.968 | 6.1172e-16 |
| diffuser_N200_CFL0.4_RPM3000 | 13.234 | 2.5985e-16 |
| diffuser_N400_CFL0.4_RPM3000 | 48.531 | 6.0445e-16 |
| diffuser_N100_CFL0.2_RPM3000 | 5.203 | 6.6553e-16 |
| diffuser_N100_CFL0.6_RPM3000 | 1.969 | 3.2333e-16 |
| blowdown_N200_CFL0.4 | 70.360 | 3.3783e-15 |
| blowdown_N400_CFL0.4 | 271.250 | 2.7061e-15 |
| blowdown_N100_CFL0.2 | 34.516 | 3.0037e-15 |
| blowdown_N100_CFL0.6 | 12.016 | 1.5523e-15 |

## Evidencia y revisión
- [x] 88 pruebas PASS,23.571s; incluye5 focales puerto/geometría y83 históricas.
- [x] P2 completo T01–T12/58 finales y FIRST_ORDER/R4 reevaluados offline PASS.
- [x] Siete regresiones históricasP0 offline PASS; sin nuevas campañasP0/P2/P3.
- [x] P3 C00/C00B reevaluados; evidenciaC01–C12 intacta por72SHA256, siete archivosP3 y27P2 congelados.
- [x] Revisión independiente /root/p3_review: P4A PASS, P4B STOP; regresiones confirmadas.
- [x] Autorrevisión de alcance/índice/hashes/documentación separada; no revisión general nueva.
- [x] Gráficas de banco inspeccionadas visualmente; no son capturaWindows ni aceptaciónhumana.

Frontera exterior nonreflectingP2 con estadoexplícito. Revisor documentó salto
potencial100000→98724.6267Pa al cambiarentropía donante en un estado térmico
artificial. No se cambióBC; en campaña no hay evidencia de que ese fenómeno cause
el fallo. Se conserva alcance de truncamiento característico lineal/local, no
radiación de escape real ni anecoico universal.

Dos fallos de infraestructura preservados: primerP4B se rechazó por timeoutdel
comando fuera del rango del esquema, antes de integrar; corregido a3500s totales,
600s porcaso intactos. P4_CLOSE completó88tests yregresiones, pero falló al fusionar
checkIDhistorical duplicado con nombrecomando. Corregido a baseline_command y
validado por IDsdisjuntos/dry-run, sin repetirtests. No afirmar que ese runnativo
pasó: permaneceFAILED_INFRASTRUCTURE. P4A nativoBLOCKED sólo reviewerhook;
P4B nativoSCIENTIFIC_CHANGE_REQUIRED por fallo real. Dictámenes adjuntos separados.

Comandos reales desde raíz, Python .venv: `-m dev_orchestrator.runners.run_phase`
P4A/P4B/P4_CLOSE con `--dependency P2=docs/gasdynamic/p2_accepted_dependency.json`.
No relanzar campañas trasSTOP sin resolver decisióncientífica. Evidencia:
results/p4-exhaust-20260918; gráficas port-blowdown.png/svg y waves-refinement.png/svg.
No publicar, no modificarcredenciales/globales, noarchivarP4. Borradoajeno redme.txt
conservado fuera decommits. OpenSpecautomático sigueomitido.

OpenSpec estricto: cambioP4 y specconsolidadaP3 PASS. AtributosGit locales
preservan bytes de los tres módulosP4 revisados; sin configuración global.

## P4-R1 — diagnóstico autorizado 2026-09-21

- [x] Auditar posiciones históricas y fijar observables antes de ejecutar.
- [x] Preparar registro de vecinos sin modificar solver; prueba de paridad exacta.
- [x] Ejecutar nominal y CFL focal, control y N800 sólo si corresponde.
- [x] Registrar tablas, señales, ledger y clasificación sin cambiar gate.
- [x] Revisión independiente de resultados y cierre documental.

Definición previa: docs/gasdynamic/p4_r1_observables.md. Históricos intactos.

## Resultado P4-R1 — 2026-09-21

**P4_R1_PERFORMANCE_DIAGNOSTIC_REQUIRED**. Defecto de sensor confirmado
(P4_R1_METRIC_IMPLEMENTATION_DEFECT) y corregido exclusivamente en el observable.
P4 sigue abierto/bloqueado; no P4C, P5, cambio de gate, aceptación ni archivo.

Definiciones previas: [p4_r1_observables.md](../../../docs/gasdynamic/p4_r1_observables.md).
Código: dev_orchestrator/p4_r1.py, commit previo87851ec. Fuente numérica y
historias anteriores:120 hashes intactos. Tres nominales reproducen exactamente
celdas, cámara, stages, dt, eventos, conteos y ledgers anteriores.

### Auditoría histórica (sin reemplazar evidencia)

Qp: rectángulo derecho por paso aceptado, |p−100000 Pa|, Pa·s, sin normalización.
El sensor pedido0,1 m se desplazaba al centro más cercano. La cuadratura también
introduce dependencia de dt; no se ha demostrado un cambio arbitrario de logging.
Qm: ledger SSPRK2 dt/2*(mdot1+mdot2), kg, negativo al salir de cámara.
Ventana idéntica0→0,012222222222222223 s. Los siguientes Qp con trapecios aún
usan el sensor histórico desplazado; no son los Qp corregidos a posición fija.

| N | x histórico m | Qp histórico Pa·s | Qp PL mismo sensor Pa·s | Qm kg |
|---|---:|---:|---:|---:|
| 100 | 0.099 | 164.729319650664 | 164.785356822589 | -9.70056603322141e-05 |
| 200 | 0.1005 | 164.804998778420 | 164.833308019080 | -9.70077286939145e-05 |
| 400 | 0.09975 | 164.899734482389 | 164.913887996882 | -9.70099933773868e-05 |

### Q corregidos, misma posición x=0,1 m

Interpolación geométrica entre dos centros vecinos, t0 más todos los finales de
paso; integral exacta del valor absoluto de la señal lineal temporal, con cruce
por cero dividido. Sin decimación ni cambio de solución. Masa sin cambios.

| N | Qp completo Pa·s | Qm completo kg | Estado |
|---|---:|---:|---|
| 100 | 164.742346961691 | -9.70056603322141e-05 | Completo |
| 200 | 164.854748982338 | -9.70077286939145e-05 | Completo |
| 400 | 164.903227803894 | -9.70099933773868e-05 | Completo |
| 800 | — | — | Timeout, integral parcial excluida |

| Observable | Mallas | Q_fino−Q_grueso | Diferencia absoluta |
|---|---|---:|---:|
| Q_pressure | 100→200 | 1.12402020647409e-01 | 1.12402020647409e-01 |
| Q_pressure | 200→400 | 4.84788215557046e-02 | 4.84788215557046e-02 |
| Q_mass | 100→200 | -2.06836170033812e-09 | 2.06836170033812e-09 |
| Q_mass | 200→400 | -2.26468347228764e-09 | 2.26468347228764e-09 |

D400→800 no disponible para ambos. N800 parcial: Qp=159,317364741868 Pa·s,
Qm=−9,538417249462383e−5 kg, sólo0→0,008968816321386268 s; **no comparable**
con integrales de ventana completa. Sin Richardson ni extrapolación.

### Eventos y fase

Apertura física90°/0,000555555555555556 s alcanzada en todas las descargas.
Cierre programado270°/0,010555555555555556 s alcanzado sólo en100/200/400;
N800 termina241,438693785°. No confundir evento programado con alcanzado.
Llegada=primer cruce ascendente interpolado102000 Pa, sin posición analítica.
Diferencias son entre mallas sucesivas, no errores contra solución exacta.

| N | Llegada s | CA ° | Diferencia llegada s | Cierre alcanzado |
|---|---:|---:|---:|---|
| 100 | 8.763254918959e-04 | 95.773858854 | — | Sí |
| 200 | 8.774345295839e-04 | 95.793821533 | +1.109037687947e-06 | Sí |
| 400 | 8.755830727586e-04 | 95.760495310 | -1.851456825306e-06 | Sí |
| 800 | 8.745722624311e-04 | 95.742300724 | -1.010810327483e-06 | No |

La llegadaN800 ocurrió antes del timeout y es observable; su integral completa no.
La secuencia de llegadas100/200/400 no es monótona; la última diferencia absoluta
se reduce, pero esto no acredita el gate completo. No se identificó un candidato
poscierre >=2000 Pa en las descargas completas. EnN800 la ventana poscierre
**no fue observada**. No atribuir causalmente picos a reflexiones con un único sensor.
Señales y extremos físicos conservados; sin mover ventanas tras mirar resultados.
La presión final de los completos permanece~100,22 kPa, cola pequeña no nula;
no prueba por sí sola independencia de la ventana ni convergencia de fase.

### Sensibilidad temporal focal

Ratio=|Q_CFL0,2−Q_CFL0,4|/D200→400 nominal. Umbrales diagnósticos definidos
antes: <=0,1 pequeño; >=0,5 comparable; intermedio inconcluso. No nuevos gatesP4.

| Observable | N | Q CFL0,4 | Q CFL0,2 | Diferencia absoluta | Ratio |
|---|---:|---:|---:|---:|---:|
| Q_pressure | 200 | 164.85474898234 | 164.85463129893 | 1.176834054775e-04 | 0.002427522 |
| Q_pressure | 400 | 164.90322780389 | 164.90318343251 | 4.437138409230e-05 | 0.000915274 |
| Q_mass | 200 | -9.7007728693914e-05 | -9.7007736044853e-05 | 7.350938610530e-12 | 0.003245901 |
| Q_mass | 400 | -9.7009993377387e-05 | -9.7009995946039e-05 | 2.568652240778e-12 | 0.001134221 |

Los cuatro cambios son pequeños; esto no estima rigurosamente todo el error
 temporal, pero no muestra contaminación comparable en este contraste. CFL
productivo0,4 intacto; no estudio general dx/dt ni campañas extra.

### Control simple equivalente a E06

Tubo recto0,75 m/20 mm, puerto constante200 mm² durante180→234°;
0→0,003 s. Referencia lineal débil y L1 definidos antes de ejecutar, no solución
exacta no lineal ni prueba de ondas fuertes. Área idéntica en todos los stages.

| N | L1 normalizado | Qp Pa·s | Qm kg | Llegada s | Tiempo s |
|---|---:|---:|---:|---:|---:|
| 100 | 0.0062372757199 | 0.00754161710579 | -3.656141330082e-13 | 2.008493799925e-05 | 2.157 |
| 200 | 0.00216432946744 | 0.00758034425026 | -3.479762774394e-13 | 2.069141848764e-05 | 8.563 |
| 400 | 0.000710559647888 | 0.00757161321307 | -3.201751655362e-13 | 2.191874214232e-05 | 34.938 |

Control convergente, sin N800 adicional. Su masa neta casi cero se informa sin
ratio relativo mal condicionado. El contraste débil/fuerte no aísla por sí solo
el puerto como causa: amplitud y condiciones también difieren.

### Ledger, conservación, admissibilidad y coste

Residuo de masa=|Qm−(m_final−m_inicial)|/masa_inicial_total. Auditoría adicional
por suma independiente de stages. Conservación y positividad PASS en todos los
intervalos alcanzados; N800 no aprueba final/eventos porque está incompleto.

| Caso | Pasos | Tiempo solver s | dt mínimo s | dt máximo s | CFL máximo | Residuo global | Residuo masa |
|---|---:|---:|---:|---:|---:|---:|---:|
| blowdown_N100_CFL0.4 | 2673 | 17.969 | 7.982491720e-07 | 7.039515698e-06 | 0.40000000000000008 | 1.985464998e-15 | 9.307525320e-16 |
| blowdown_N200_CFL0.4 | 5405 | 71.000 | 3.920881915e-07 | 3.519757849e-06 | 0.40000000000000008 | 3.378286968e-15 | 3.412759284e-15 |
| blowdown_N400_CFL0.4 | 10868 | 286.672 | 1.591807538e-08 | 1.759878924e-06 | 0.40000000000000008 | 2.706076806e-15 | 1.068641796e-15 |
| blowdown_N200_CFL0.2 | 10765 | 137.985 | 3.137548774e-07 | 1.759878924e-06 | 0.20000000000000004 | 6.210941787e-15 | 1.895977380e-15 |
| blowdown_N400_CFL0.2 | 21700 | 559.922 | 1.264635145e-07 | 8.799394622e-07 | 0.20000000000000004 | 4.827967923e-15 | 9.307525320e-16 |
| control_N100_CFL0.4 | 342 | 2.157 | 2.554574926e-06 | 8.799394527e-06 | 0.40000000000000002 | 4.578090050e-16 | 9.159964826e-17 |
| control_N200_CFL0.4 | 699 | 8.563 | 6.408287310e-07 | 4.399697286e-06 | 0.40000000000000002 | 6.253467629e-16 | 3.245364873e-16 |
| control_N400_CFL0.4 | 1403 | 34.938 | 9.401554711e-07 | 2.199848634e-06 | 0.40000000000000002 | 7.938648579e-16 | 4.692226554e-17 |
| blowdown_N800_CFL0.4 | 16963 | 900.031 | 2.069854083e-07 | 8.799394622e-07 | 0.40000000000000008 | 6.608845935e-15 | 1.930449696e-15 |

| Caso | RHS | HLLC | HLLE | Rechazos |
|---|---:|---:|---:|---:|
| blowdown_N100_CFL0.4 | 5921 | 597209 | 0 | 575 |
| blowdown_N200_CFL0.4 | 12018 | 2413958 | 0 | 1208 |
| blowdown_N400_CFL0.4 | 24161 | 9685325 | 0 | 2425 |
| blowdown_N200_CFL0.2 | 23860 | 4792712 | 0 | 2330 |
| blowdown_N400_CFL0.2 | 48182 | 19314651 | 0 | 4782 |
| control_N100_CFL0.4 | 684 | 69084 | 0 | 0 |
| control_N200_CFL0.4 | 1429 | 287229 | 0 | 31 |
| control_N400_CFL0.4 | 2882 | 1155682 | 0 | 76 |
| blowdown_N800_CFL0.4 | 38700 | 30997419 | 0 | 4774 |

Suma de nueve tiempos de solver2019,237 s; ocho completos y un parcial.
N800900,031 s: control del límite al comienzo de paso, sin extensión; exceso
0,031 s corresponde a finalizar el paso antes de comprobarlo de nuevo.
CFL máximo0,4000000000000001 es redondeo; verificación contractual por límites
de cada stage PASS, sin tolerancia nueva. Mayor residuo global6,60884593495e−15.

Perfil N800:16963 pasos,38700 RHS/reconstrucciones/evaluaciones de puerto,
37419 evaluaciones de coupling abierto,30921300 Riemann internos+38700 pared,
30997419 HLLC totales, ceroHLLE.4774 rechazos por stage_CFL.
Coste observado0,0530584802 s/paso aceptado, incluidos rechazos y logging.
Inferencia de cuentas contrastada con characteristic==RHS y2*pasos+rechazos==RHS.
Microperfil offline del estado final:20 repeticiones sin avanzar estado y un
snapshot cProfile. Reconstrucción4,648 ms, Riemann internos7,895 ms,
puerto/coupling0,0544 ms, exterior0,0132 ms por snapshot en ese equipo.
No son porcentajes del coste global: excluyen advances, validación, ledgers,
logging y variación de estados. Sin optimización ni integración adicional.

### Verificación y revisión

Tres tests focales PASS (0,074 s en run), reproducción offline de nueve métricas
PASS, paridad exacta nominal histórica PASS,120 hashes PASS, OpenSpec estricto
P4 PASS. No repetidas regresiones generalesP0/P2/P3: fuentes congeladas intactas.
Autorrevisión del postproceso y visualización de señales separada de revisión
independiente read-only por /root/p3_review. Esta última confirmó métricas,
CFL/control, conteos, congelación y estado final; pidió distinguir cierre
programado del no alcanzadoN800, recogido en diagnostics.json y esta tabla.
Sin aceptación humana deP4. Gate nativo conservaSCIENTIFIC_CHANGE_REQUIRED;
la ejecución del protocoloCOMPLETED no equivale a integraciónN800 completa.

Evidencia: results/p4-r1-20260921, signals.png/svg, performance.json,
snapshot-profile.txt, diagnostics.json, independent-review.json, decision.json,
run/artifacts/cases (incluye parcial), inventory-all.json. Históricos intactos.

Comandos desde raíz:
- `.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P4_R1 --dependency P2=docs/gasdynamic/p2_accepted_dependency.json`
- `.venv\Scripts\python.exe -m dev_orchestrator.p4_r1_profile results/p4-r1-20260921/run/artifacts/cases/blowdown_N800_CFL0.4.json.gz results/p4-r1-20260921`
- `python dev_orchestrator/p4_r1_plot.py results/p4-r1-20260921` (matplotlib sólo herramienta offline disponible; no dependencia del producto).
- `openspec validate p4-escape-1d --strict --no-interactive`

STOP. Pendientes: Q800 de ventana completa, D400→800 y convergencia global de
descarga. Resolver siguiente autorización sobre rendimiento antes de otra
integración; no ampliar timeout automáticamente. No propuesta de cambio del
gate porque no se acreditó el caso preasintótico. P4B/P4C siguen pendientes.
No publicación, archivo, nueva candidata ni modificación de producto.

## P4-R1E — orden6e7321b2, 2026-09-21

- [x] Congelar solver, observables y evidenciaR1; elección restart desde t=0.
- [x] Ejecutar únicamente N800/CFL0,4 con límite1500s.
- [x] Evaluar todas las condicionesR1 con Q completos y revisión independiente.

1500s es límite de integración;1650s del comando deja margen de serialización,
no amplía el solver. Estimación previa900,031/0,734≈1226s. No optimización.
No existe API de resume de tiempo/eventos/ledger: los arrays finales anteriores
no se convierten en checkpoint. Se comprueba paridad exacta del prefijo aceptado.
Mismo prepare/measured/compare deR1 por importación, sin modificar esos archivos.
Mismas condiciones de presión, masa, llegada, conservación, positividad,CFL,
control y temporal. Fallo de fase se registra separadamente. Timeout→
P4_R2_PERFORMANCE_OPTIMIZATION_REQUIRED, sin optimizar ni repetir en esta orden.

## Resultado P4-R1E — 2026-09-21

**P4_R1_PREASYMPTOTIC_REFINEMENT_CONFIRMED** bajo todas las condicionesR1.
Una sola integración nueva N800/CFL0,4, reiniciada desde t=0; completó
0→0,012222222222222223 s (CA80→300) en1139,360 s, límite1500s.
No resume ambiguo, optimización ni cambio científico. No aceptaciónP4 ni
modificación de su gate; STOP antes deP4C/P5 y sin archivo/publicación.

Reutilizados los ocho completosR1 por hashes (tres nominales, dos CFL y tres
controles). El N800 parcial sólo se usa para auditar el prefijo registrado:
16963 history/stages idénticos, no para integrales de convergencia.
Fuentes y evidencia:120+31 hashes intactos. prepare/measured/compare y definición
R1 sin cambios, sensor0,1m, cuadratura lineal y ledgerSSPRK2 originales.

| N | Qp Pa·s | Qm kg | Llegada s | Llegada CA ° |
|---|---:|---:|---:|---:|
| 100 | 164.742346961691 | -9.70056603322141e-05 | 8.763254918959e-04 | 95.773858854 |
| 200 | 164.854748982338 | -9.70077286939145e-05 | 8.774345295839e-04 | 95.793821533 |
| 400 | 164.903227803894 | -9.70099933773868e-05 | 8.755830727586e-04 | 95.760495310 |
| 800 | 164.923093338473 | -9.70116526264108e-05 | 8.745722624311e-04 | 95.742300724 |

| Mallas | D presión Pa·s | D masa kg | D llegada s |
|---|---:|---:|---:|
| 100→200 | 1.124020206474e-01 | 2.068361700338e-09 | 1.109037687947e-06 |
| 200→400 | 4.847882155570e-02 | 2.264683472288e-09 | 1.851456825306e-06 |
| 400→800 | 1.986553457897e-02 | 1.659249024012e-09 | 1.010810327483e-06 |

D400→800 menor queD200→400 en presión, masa y llegada. Se conservan todas
las condiciones: conservación, admisibilidad, CFL, control convergente y efecto
 temporal pequeño. El control/CFL no se repitió. No Richardson, cambio de umbral
ni tolerancia relativa de masa añadida. relative_mass_difference sólo diagnóstico:
1.710360538235e-05.

### Registro N800 completo

Pasos21831; RHS48516; HLLC38854978; HLLE0.
Rechazos stage_CFL4854; downgrades0.
dt mínimo9.154256934776e-08 s; máximo8.799394622473e-07 s.
CFL máximo0.40000000000000008; comparación contractual dt<=límites de cada
stage PASS, sin tolerancia nueva. Ledger masa frente inventario:
3.757482443841e-15, normalizado por masa inicial total.

| Balance combinado | Residuo final dimensional | Máximo normalizado por paso |
|---|---:|---:|
| Masa kg | -6.505213034913e-19 | 3.860899391836e-15 |
| Energía J | -8.313350008393e-13 | 6.608845934951e-15 |
| Especie kg | 1.084202172486e-18 | 3.757482443841e-15 |

Normalización contractual: masa inicial, energía inicial, masa inicial para
especie. Máximo porstage3.146163579517e-16; conservaciónPASS al límite1e−10.
Mínimos del dominio1D: rho=0.70632205811636 kg/m³,
p=99999.999999999971 Pa,T=299.99999999999977 K.
Y∈[0.19999999999992873,0.80000000000002869] dentro de[0,1].
Admisibilidad de cámara y tubo comprobada por el solver en sus stages.

### Cierre y señal poscierre

Cierre270° alcanzado a0,010555555555555556s. Cámara y ledger al cierre son
exactamente iguales a sus valores finales. Hay2489 muestras posteriores:
p mínimo100227,85042879335Pa, máximo101249,2443580738Pa. Señal completa
conservada en el artifact y graficada en signals.png/svg; zoom sólo visual.
No se identificó candidato poscierre con el detectorR1 ya congelado.

En el instante exacto270° la geometría congelada devuelve área
1,4210854715202002e−19m² por aritmética flotante; trazas guardadas sin redondear
con flujo~−9,9848245e−19kg/s. Para t>t_cierre área/flujo son exactamente cero.
No clamp, tolerancia ni modificación de ley de puerto; no ocultar esta diferencia
entre instante de cierre y estados estrictamente posteriores.

### Incidencia de auditoría, sin repetir integración

El run nativo conserva summary.state=FAILED_INFRASTRUCTURE y gate
SCIENTIFIC_CHANGE_REQUIRED: comparaba tuplas en memoria con listas JSON.
No es un fallo numérico; las nueve condiciones científicas calculadas son true.
Se corrigió sólo same_json_value, normalizando tupla/lista vía JSON, sin redondear
ni aplicar tolerancia. Tres regresiones puras PASS: estructuras equivalentes,
un ULP distinto y stage ausente. No integración tras el fix.

La decisión offline exige primero151 hashes intactos, prefijo persistido exacto,
reproducción exacta de measured y todas las condiciones originales. Originales
nativos preservados en run/; audit-correction.json explica el diagnóstico y
 decision.json registra el estado científico. No presentar run nativo comoPASS.
Preflight del wrapper con resultado anterior inyectado fue offline, cero
integraciones; sólo la ejecución formal de1139,360s adquirió nueva evidencia.

OpenSpec estrictoP4 PASS. Autorrevisión del diff y señales separada de revisión
independiente read-only. No regresiones físicas generales ni campañas adicionales.
Evidencia: results/p4-r1e-20260921; fuente previa c3ebf1f.
Comando ejecutado: `.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P4_R1E --dependency P2=docs/gasdynamic/p2_accepted_dependency.json`.
Pruebas puras: `.venv\Scripts\python.exe -m unittest discover -s tests -p test_p4_r1e.py -v`.

Pendiente exclusivamente de nueva orden humana: revisión del gateP4 y decisión
sobre continuarP4. La confirmaciónR1 no habilitaP4C niP5, no acepta ni archivaP4.

Revisión independiente final /root/p3_review: confirma PREASYMPTOTIC, recalcula
Q/diferencias/balances, valida151 hashes y prefijo JSON exacto. Acepta corrección
de auditoría, no aceptación humanaP4. Recibo: independent-review.json.

## P4-R2 — orden2df31e6d
- [x] Revisión independiente y adopción versionada P4_REFINEMENT_R2.
- [x] Reevaluación offline de16 casos/6 agregados restantes: P4B PASS bajoR2.
- [x] Implementar P4C aislado y medir un ciclo antes de multiciclo.
- [x] Evaluar E12/E15 del ciclo medido y ejecutar regresiones; aplicar STOP de coste.
- [ ] E13 periódico y E14 G1/G2/retorno causal; E12/E15 sobre la campaña completa.

Delta: docs/gasdynamic/p4_refinement_r2.md; evidencia results/p4-r2-20260921/gate-review.json.
Sin integración nueva para PartesA/B. E11 histórico es banco, no ciclo motor.

### Resultado P4C — P4_BLOCKED_PERFORMANCE

Definición registrada antes de ejecución en docs/gasdynamic/p4c_hybrid.md,
commit4747eb2. Ruta interna motorsim/hybrid_exhaust.py, sin import UI/JSON;
legacy y kernels congelados intactos. Adaptador I/K/C reutiliza fuentes Model;
puerto usa P3/P4. Combustión350→390 conserva F analítica mediante coordenada
transformada, calor SSPRK2 registrado separado de su primitiva. Revisión previa
independiente aprobó esa adaptación; corrigió sólo evaluadorCFL por etapas y
retiró tolerancia de especie antes de integrar. Ocho pruebas focales PASS.

G1 recto .75m/20mm,N250; G2 cadenaP4B,N251, ambos dxobjetivo3mm.
G2 configurado, **no ejecutado**. Motor, RPM3000 e iniciales canónicos:
tubo/exterior100kPa/500K/Y0/u0. La justificación cuantitativa de malla y
periodicidad (30máximo,3comparaciones tras ciclo5) precede al coste medido.

| Medición G1 | Resultado |
|---|---:|
| Ciclos completos | 1, 180→540° |
| Solver / ciclo con postproceso | 261,563 / 263,328 s |
| Proyección30 ciclos / presupuesto | 7899,840 / 600 s |
| Pasos aceptados / RHS | 13164 / 35379 |
| HLLC / HLLE | 8861357 / 0 |
| Rechazos stage_CFL | 9051 |
| Balance global normalizado m/E/F | 4,45e−15 / 4,52e−15 / 1,37e−15 |
| Máximo residuo etapa / segmento | 3,53e−16 / 1,15e−14 |
| Intercambio puerto m/E/F haciaC | −3,29831227e−5 kg / −23,08635686 J / −3,24525813e−6 kg |
| rho/p/T mínimos1D | 0,519827851 kg/m³ / 99983,4422 Pa / 499,997876 K |
| Y mínimo/máximo1D | 0 / 0,4481253805 |
| Trazas de puerto cerrado | 13634, intercambio exactamente0 |
| Trazas con backflow | 0, no acreditado por este ciclo |

**E12 y E15 PASS únicamente para el ciclo medido**. EOS valida todas las
etapas1D y Model las0D, sin clipping. Extremos0D de trazas RHS guardadas:
p[91346,1073;1410384,7069]Pa,T[299,004389;1277,892918]K,Y[0;1]. No confundir
estos extremos muestreados con un listado de todos los estados intermedios.
El puerto es interno y no se suma como fuente externa del inventario conjunto.
Audit offline vuelve a sumar inventarios/ledger; diferencias de unos ULP entre
fsum y acumulación secuencial están expuestas, no se retocan los datos.

Calor numérico0,523078783273J, primitiva0,523078782839J;
diferencia4,3388e−10J. Especie quemada analítica6,53848478549e−7kg.
Diagnósticos indicados del **primer ciclo transitorio**, no prestaciones periódicas:
W=−0,418168664J, P=−20,9084332W, par=−0,0665536099Nm.
El signo negativo no se oculta ni se interpreta como potencia al eje.

El historial contiene sólo ciclo1; periodicidad=null. Guard30×tiempo>600s
obliga STOP antes de G2 o ciclo2. Incluso mínimo7ciclos costaría1843,296s con
esta medida; no se cambia el mínimo ni la malla para forzar continuación.
**E13/E14 pendientes**: sin comparación G1/G2, tiempo/ángulo de retorno ni
causalidad demostrada. backflow_local=true nativo es una comprobación vacua
en este ciclo; soporte P3/P4A previo no equivale a evidencia híbrida nueva.

### Evidencia, comandos y regresiones

results/p4-r2-20260921/p4c conserva run nativo completo y arrays gzip;
hybrid-audit.json registra auditoría, hybrid-traces.png/svg muestran señales
reales guardadas. Sensores efectivos0,1005/0,2985/0,4995m: p/u/M/Y cada paso,
p/u/T/Y/M en snapshots completos. Cara de puerto de segunda etapa y flujo
promedioSSPRK2 etiquetados; no se presentan como evaluación puntual idéntica.
No se guardó ni afirmó un checkpoint reanudable.

Comandos reales:

- `.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P4C_PREFLIGHT --dependency P2=docs/gasdynamic/p2_accepted_dependency.json`
- `.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P4_CLOSE --dependency P2=docs/gasdynamic/p2_accepted_dependency.json`
- `python -m dev_orchestrator.p4_hybrid_report results/p4-r2-20260921` (sólo auditoría/figuras offline).
- `openspec validate p4-escape-1d --strict --no-interactive`

P4_CLOSE:88 testsPASS(24,292s), más8focalesPASS; histórico offlineP0/P2/P3
todoPASS,0 nuevas integraciones de campaña en regresiones. P4A/P4B y151hashes
congelados intactos. El Python del venv no tiene matplotlib; generar figura con
él falló tras guardar auditoría. Se usó Python3.11 existente con matplotlib para
postproceso, sin instalar dependencias ni repetir integración.

Ambos runs nativos tienen gateBLOCKED únicamente por review_not_approved del
hook dummy; no errores ni scopeviolations. Conservarlo, adjuntar revisión
independiente separada. Ese bloqueo técnico no sustituye al STOP científico/
operativo P4_BLOCKED_PERFORMANCE. Autorrevisión de código/diff/figuras separada
de la revisión read-only /root/p3_review. Sin aceptaciónP4, archivo, push niP5.

Dictamen independiente final: **P4_BLOCKED_PERFORMANCE**, R2/P4B aprobados,
96 tests y regresiones confirmadas, sin P4 PASS. Recibos separados:
results/p4-r2-20260921/independent-review.json y decision.json; inventario SHA256
de31 archivos de evidencia en inventory-all.json. OpenSpec estricto final PASS.
Commits previos:84b36b9 deltaR2,4747eb2 fuente previa,a3087ba medición/STOP.

## P4-R3 — orden5e36dbe4
- [x] Registrar aceptación humana R2/P4B, sin aceptar P4.
- [x] Perfil estándar y clasificación de coste antes de optimización.
- [x] Optimizaciones aisladas y equivalencia por bloque.
- [x] Perfil intermedio, benchmark completo, regresiones y reviewer.
- [ ] Performance<=20s/ciclo, proyección30<=600s con margen.
- [ ] Reanudar periodicidad/G2 sólo con performance PASS.

## P4-C3-R3 — corrección de auditoría supervisada (2026-09-28)

- [x] Corregir la captura pre/post: `stage_a` conserva `pre_cells`, `pre_z` y
  `pre_t` antes del commit; `op0/stage_a` aporta primitiva y flujos observados,
  `cells1/z1/op1` aporta `stage_b`, y `cells_new/z_new/ws_new` aporta `after`.
- [x] Alinear `interface_info` con `stage_a/op0`: `p_chamber`, cámara,
  primera celda y `sample_time_pre_step` son pre-step; se conserva
  `history_record_time_post_step` para el commit-time del historial.
- [x] Añadir prueba real de un paso: estados pre/post distintos, primitiva
  derivada consistente, presión de cámara derivada de `stage_a`, cámara y
  primera celda alineadas, y ambos tiempos ordenados. Los siete tests focales
  existentes permanecen PASS.
- [x] Alinear la selección causal de retorno con `sample_time_pre_step`, con
  fallback al timestamp externo para compatibilidad.
- [x] Auditar la interfaz con `ExactRiemann` independiente y reconstruir la
  pared como ghost reflectante físico `(rho,-u,p,Y)` mediante
  `ExactRiemann(last, ghost, EOS).sample(0)`; conservar `C2_VOLUME` y no usar
  HLLC productivo en el auditor.
- [x] Regenerar `results/p4-c3-r3-20260928` desde el fixture único. Los números
  de `174b261` quedan `SUPERSEDED/INVALIDATED` por mezcla de captura pre/post;
  la física y el solver no cambian.
- [x] Resultado vigente: retorno `PASS`, `selected_time` pre-step
  `0.0026532366020821743 s`, flujo `0.0002698587123830558 kg/s`, y registro
  post-step `0.0026543865163682658 s`; ExactRiemann `INCONCLUSIVE`, errores
  relativos `(1.7797458457669132e-07, 3.4548877071827627e-06,
  6.581792616275487e-04, 8.898729228831856e-08)`, máximo
  `6.581792616275487e-04`; momento `max_abs_residual =
  5.840234051652552e-06`, `max_relative_residual = 1.9399428518812518`,
  `median_relative_residual = 0.018615083342715104`. Conservación `PASS`,
  residuo máximo `1.3929103469155642e-15`.
- [x] C3 permanece `P4_SCI_C3_INCONCLUSIVE`: no existe threshold aprobado y
  no se inventó ninguno; momentum max_abs/max_relative/median_relative son
  diagnósticos, no gate. E13 `NO EJECUTADO`; P9 `STOPPED`.

### P4_R3_COMPILED_BACKEND_DECISION_REQUIRED

R2/P4B aceptados por la usuaria, recibo docs/gasdynamic/p4_r3_acceptance.json.
NO P4_HUMAN_ACCEPTED. Contratos/physics/meshN250/CFL/eventos/0D intactos.
SCALAR_REFERENCE disponible por motorsim.hybrid_exhaust y selector interno
hybrid_fast.run_cycle(...,backend='SCALAR_REFERENCE'/'STRUCTURAL'/'NUMPY').
No import productivo de estos backends ni cambio UI/JSON/EXE.

| Camino | Wall, s/ciclo | CPU, s | Speedup | 30ciclos, s |
|---|---:|---:|---:|---:|
| ReferenciaR2 | 263,328 | No registrado | 1× | 7899,840 |
| Cachés estructurales | 226,773529 | 226,203125 | 1,161× | 6803,206 |
| NumPy1 | 35,469199 | 35,406250 | 7,424× | 1064,076 |
| NumPy2 | 35,443038 | 35,250000 | 7,430× | 1063,291 |

Tres ventanas100µs antes/intermedio/después:17,531/13,709/1,047s con cProfile.
Al ser viable se perfiló además el ciclo NumPy completo:63,682498s instrumentados,
**excluidos** de la comparación de performance. Top final inclusivo: RHS55,52%,
HLLC25,15%, evaluación0D24,52%, MUSCL11,27%, primitivas7,50%; no sumar anidados.
Tabla completa self/inclusive/calls, CPU/RAM, clasificaciónA–F y opcionesA–D:
docs/gasdynamic/p4_r3_performance.md. No se midieron allocations acumuladas ni
se inventan CPU/RAM del baseline histórico. Mismo Windows10/i5-10400/Python3.11.0.

Bloque1cachea primitivas inmutables, geometría y evaluación0D por estado/tiempo;
equivalencia exacta antes del siguiente bloque. Bloque2NumPy2.3.0 aplica las
mismas operaciones float64 a EOS/MUSCL/HLLC/CFL y avances de celdas; BC/P3 y
fallbacks siguen escalares congelados. Fallback/downgrade por cara/celda;
puerto agrega conteo por cara sin subrazón interna inventada. Dependencia sólo
requirements-experimental.txt; pip check PASS, sin compilados/globales.

Equivalencia **exacta, máximo absoluto0** para estados0D/1D, pC/pPuerto,
flujosm/E/F, sensores, trabajo, inventarios/ledgers en bloque1, ambas medidas
NumPy y perfil completo. Mismos eventos,13164pasos/26328etapas aceptadas,
35379RHS,8861357HLLC/0HLLE,9051rechazosCFL. Revisor verificó histories/stages
completos. Balances/admisibilidad y ausencia de backflow coinciden conR2.
Performance mejora sustancialmente, pero NO cumple; no periódico/G2/E14/P4PASS.

### Regresiones y revisión

101 testsPASS(25,178s):88 históricos +8 adaptador +5 batch. EOS/MUSCL/HLLC/HLLE,
supersónico/igualdad/downgrade y dos microintegraciones descarga/backflow contra
referencia. Replay offline adicional:3P4A+16P4B,190 snapshots/finales,27050caras,
igualdad exacta. Gates históricos aceptados intactos; P0/P2/P3 offlinePASS,
151hashes históricos y cinco referenciasR3 intactos. No repetir campañas largas.

Primer cierreFAILED_INFRASTRUCTURE: el archivo nuevo gas1d/batch.py alteraba
inventario glob congeladoP2, sin cambiar archivos científicos. Movido a
motorsim/exhaust_batch.py; cuerpo idéntico exceptoimports, no tocarvalidadores.
Fallo conservado en regression-infrastructure-failure; corrección en
namespace-correction.json; regresión posteriorPASS. Reviewer confirmó fix sin
necesidad de repetir benchmark; el perfil completo posterior también fue exacto.

Autorrevisión de fuentes/diff separada de revisión independiente read-only
/root/p3_review: confirma perfiles/equivalencia/101tests/replay/bloqueo. No
ejecutó integraciones; sólo lecturas y evaluaciones puntuales de kernels.
Runs nativos restantes BLOCKED por review_not_approved del hook dummy,
sin errors/scopeviolations; conservar junto al dictamen externo independiente.
El estado técnico del hook no sustituye la decisión de performance.

### Evidencia y reproducción

results/p4-r3-20260921: artifacts/ contiene perfilbase; structural/ el bloque1;
numpy/ las dos medidas finales y perfilporventanas; full-profile/ perfilcompleto;
regression/ la comprobación final; decision.json e independent-review.json
separan resultado medido, aceptación humana y revisión. Mantener originales.

Comandos ejecutados (no relanzar automáticamente):

- `.venv\Scripts\python.exe -m pip install -r requirements-experimental.txt`
- `.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P4_R3_PROFILE --dependency P2=docs/gasdynamic/p2_accepted_dependency.json`
- Misma invocación con P4_R3_STRUCTURAL, P4_R3_NUMPY, P4_R3_CLOSE y P4_R3_FULL_PROFILE.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p test_gas1d_batch.py -v`
- `openspec validate p4-escape-1d --strict --no-interactive`

Falta decisión humana sobre AcontinuarNumPy/BNumba/Cextensión/Dresoluciónfutura.
Para20s falta1,77346× adicional,43,613% menos wall. Cotas instrumentadasAmdahl
orientativas en el documento, no promesa de compilación. No implementarB/C,
ampliar600s, aceptarP4, archivar, publicar ni iniciarP5. Borrado ajeno preservado.

OpenSpec estricto final PASS; inventario SHA256 de82 archivos de evidencia.
Commits:75210ad aceptación/perfil,655b9a9 bloqueestructural,5e7680e batching,
2675763 benchmarks,d89dc70 correcciónnamespace,11ff512 regresiones/perfilcompleto.
## P4-R4 — evaluación Numba serial (orden 8f6dbacb)

- [x] Compatibilidad registrada: Windows 10 x64, Python 3.11.0, NumPy 2.3.0, Numba 0.62.1, llvmlite 0.45.1; `pip check` PASS. No se cambió Python/NumPy ni packaging.
- [x] HLLC float64 `njit(cache=True, fastmath=False, parallel=False)` y backend seleccionable `NUMBA_EXPERIMENTAL`; SCALAR/NUMPY permanecen disponibles.
- [x] Microbenchmark: equivalencia PASS con tolerancia prefijada; caras G1 480° 1,51879× (diagnóstico aleatorio 0,98782× conservado). JIT inicial 4,779 s en el fixture G1.
- [x] Focal: tres ventanas congeladas G1, equivalencia completa de estados, historia, eventos, contadores, balances y observables; 5 tests Numba PASS; speedups 1,665× / 1,864× / 1,335×.
- [x] Dos G1 completos calientes: 37,313 s (primero, JIT fuera del resultado) y 26,599 s; equivalencia exacta, 13.164 pasos, 26.328 RHS aceptados, 35.379 RHS totales, 8.861.357 HLLC, 0 HLLE, 9.051 rechazos. Proyección 30 ciclos 1.119,38 s / 797,98 s.
- [x] OpenSpec estricto PASS y regresiones focales Numba PASS.
- [x] Suite pertinente P0/P1/P2/P3/P4 y Numba: 106 tests PASS (24,100 s). La ejecución amplia de 449 tests conserva cinco fallos preexistentes/ambientales fuera de R4 (P1 habilitada por roadmap, UI CAE, P0 baseline y dos límites de memoria/cancelación); no se atribuyen al backend.
- [ ] Gate de rendimiento: **P4_R4_NUMBA_NATIVE_EXTENSION_DECISION_REQUIRED** (>25 s/ciclo; la segunda medición sigue sobre 20–25 s). No iniciar periodicidad G1, G2, E14 ni P5.
- [ ] Revisión independiente conectada: el runner dummy quedó BLOCKED por `review_not_approved`; conservar la evidencia y distinguirla de la autorrevisión.

Evidencia: `results/p4-r4-20260921/artifacts/benchmark.json`,
`dev_orchestrator/runs/20260921T134738-P4_R4_FOCAL-c72685bc1449/artifacts/focal.json`
y `dev_orchestrator/runs/20260921T134518-P4_R4_MICRO-2fc258aaeab7/artifacts/micro.json`.

## P4-R5 — fusión del hot path Numba antes de extensión nativa (orden fusión)

- [x] Revisión independiente P4-R4 read-only repetida; dummy BLOCKED conservado; revisión real **INDEPENDENT_REVIEW_PENDING** (sin reviewer conectado), checklist float64/fastmath/parallel/equivalencia/benchmark/JIT/tests.
- [x] Ciencia congelada: Euler quasi1D/HLLC/HLLE/MUSCL/minmod/SSP-RK2/CFL/EOS/source/P3/port/geometría/eventos/malla G1 250 verificados, fastmath=False parallel=False.
- [x] Perfil backend Numba actual (26.599 s) en 12 categorías A-L (Python 41.6%, SSP 15.3%, HLLC 12.6%, diagnósticos 8.8%, etc.) y cProfile top20; sin optimizar antes de identificar hotspots.
- [x] Medición de crossings: 106137 Python→Numba, 35379 HLLC faces (8.861.357 flujos), 48546 primitives, 176895 face_state, 74874 coupling, ~1.45 GB allocations temporales por ciclo.
- [x] Kernel fusionado `gas1d_rhs_numba` en `motorsim/exhaust_numba.py` + `exhaust_numba_fused.py` (`FUSED_ENABLED=True`): primitive+MUSCL+HLLC en una sola región compilada, sin duplicar física, comparando contra SCALAR/NUMPY/NUMBA_R4.
- [x] Arrays de trabajo prealocados y reutilizados (w, lf, rf, flux, speeds, codes, bad) sin aliasing que cambie estados; in-place autorizado con equivalencia matemática y preservación de q^n/stages/ledgers; 3 tests aliasing PASS.
- [x] Gate focal: 3 ventanas G1 idénticas a R4, equivalencia exacta 11/11 campos, speedups R5 vs R4 1.136×/1.519×/1.411× agregado 1.33× ≥1.2 PASS.
- [x] Microbenchmark 1000 RHS: R4 0.381653 s vs R5 0.069238 s speedup 5.512× ≥1.15 PASS.
- [x] Dos G1 completos calientes con JIT fuera: 19.519 s / 19.223 s wall (19.141/19.187 cycle), equivalencia exacta 13 campos, 13.164 pasos, 35.379 RHS, 8.861.357 HLLC, proyección 30× 574.92 s ≤600 → **P4_R5_NUMBA_FUSED_PERFORMANCE_PASS** (≤20 s). Segunda medida también 19.18 <20, mediana 19.16.
- [x] Periodicidad G1: 30 ciclos con NUMBA_FUSED, sin streak 3 PASS (sensor_max ~0.60, work_rel 0.03); G2 15 ciclos diagnóstico similar; E14 requiere G1 PASS, no acreditado. Checkpoints deterministas por ciclo guardados. Estado final **P4_BLOCKED_PERIODIC_CONVERGENCE** (no P4 PASS, no P5).
- [x] Regresiones: 101 tests patrón P4_R3_CLOSE PASS (26.371 s) + 5 Numba + 3 aliasing fused = 109 (106 pertinentes), OpenSpec estricto PASS, 449 amplios con 5 fallos preexistentes no atribuidos.
- [x] Revisión final read-only sobre profile/kernel/equivalencia/fastmath/parallel/allocations/SSP/balances/benchmark/regresiones; dummy BLOCKED conservado.

Evidencia: `results/p4-r5-20260921/artifacts/` (profile_r4/r5, crossings, micro_rhs, focal, benchmark, periodic), `docs/gasdynamic/p4_r5_fused.md`, `results/p4-r5-20260921/decision.json`, `results/p4-r5-20260921/independent-review.json` (INDEPENDENT_REVIEW_PENDING), `motorsim/exhaust_numba_fused.py`.

## P4-R6 — diagnóstico de periodicidad / posible órbita de período 2 (orden diagnóstico)

- [x] D1 exacto 1–30 con thresholds contractuales, tablas completas work/cyl/sensor/port/inventarios y sensor_max localizado (sensor 0, fase 123.5–124°, p~100k vs 30k, denom~100k, metric 0.60).
- [x] D2/diagnóstico lag2 (n vs n-2): work 0.00005–0.001, sensor_max 0.006–0.02 tras ciclo 24 vs D1 0.60; D3≈D1, D4≈D2 → período 2.
- [x] Vector X_n (I/K/C + pipe integrals): ||X_n-X_{n-1}|| max 0.324, ||X_n-X_{n-2}|| max 0.00004–0.0007 sostenido → `PERIOD_2_ORBIT_CANDIDATE`.
- [x] Invariancia 360°: geometry/port.area/events/volumes/dV idénticos theta vs theta+360 exacto; HybridSystem heat_start +360 correcto → PASS.
- [x] Handoff n→n+1: state/cells/inventories/angle/composition/ledger exactos, sin reinicialización silenciosa → PASS.
- [x] Búsqueda 720°: 720 solo en módulos 4T, no en camino híbrido 2T → `PERIOD_MAPPING_DEFECT` no encontrado.
- [x] Restart determinism: checkpoint G1-28 → rerun ciclo 29 reproduce exacto (state/cells/work/history 0 diff) → PASS.
- [x] Odd/even: W odd 13.838 vs even 13.331 (diff 3.6%), cada subsecuencia converge (5e-05/0.00014); pipe mass odd 1.48e-04 vs even 1.04e-04, port mass odd -6.54e-05 vs even -4.92e-05; divergencia ya en pipe al inicio del ciclo.
- [x] G2 15 ciclos: D1 sensor_max 0.005 en 4–5 luego 0.46–0.55, D2 sensor_max 0.004–0.009 tras ciclo 7 → mismo patrón period-2, causa común.
- [x] Clasificación: **P4_R6_PERIOD_2_ORBIT_CONFIRMED** — 360 PASS, handoff PASS, metric no defect, D2/vector convergen, D1 no, odd/even reproducibles. No P4 PASS, `SCIENTIFIC_CHANGE_REQUIRED`, STOP, no P5. No promediar ni relajar thresholds.

Evidencia: `results/p4-r6-20260921/artifacts/diagnosis.json` (D1/D2/D3/D4, vector, odd/even), `results/p4-r6-20260921/artifacts/g1_cycles/` (30), `g2_cycles/` (15), `docs/gasdynamic/p4_r6_diagnosis.md`, `results/p4-r6-20260921/decision.json`.

## P4-R7 — robustez numérica de la órbita de período 2 (orden diagnóstico)

- [x] A/B = finales ciclo 29/30 (hashes 449a31/3421b6) con N250/CFL0.4/NUMBA_FUSED.
- [x] Cierre Poincaré: A→B* exact 0.0 PASS, B→A* work 0.00040 vector 0.000033 PASS, sensor 0.02650 >0.005 pero <<0.60 D1 y consistente con lag2 histórico 0.015; cross A* vs B sensor 0.60 FAIL confirma period-2.
- [x] Continuación 6 ciclos desde A: D1 sensor 0.60 FAIL, D2 sensor 0.01–0.05 FAIL per 0.005 pero work/vector PASS, sin 3 D2 consecutivos sensor PASS.
- [x] Backend 4 ciclos desde ciclo28: NUMBA_FUSED vs NUMPY_REFERENCE diff 0.0 exact, misma clasificación period-2 → PASS.
- [x] CFL 8 ciclos desde ciclo28: 0.4 vs 0.2 work diff 2e-05 sensor 0.603 vs 0.603, D1/D2 idénticos → period-2 persiste, no `TIME_SENSITIVE`.
- [x] Espacial G1 canónico N200(200)/N250(250)/N300(300) 10–30 ciclos: N200 amp 0.281 mean 13.595, N250 amp 0.253 mean 13.584, N300 amp 0.128 mean 13.529, todos period-2, amplitud no crece → `SPATIAL` PASS.
- [x] Comparación órbita: mean 13.5–13.6, amplitudes 0.28/0.25/0.12, Delta_AB p_cyl min 56 Pa en 348° max 237k Pa en 179.5° amplificación desde 81.5° (blowdown).
- [x] Conservación/admisibilidad/CFL PASS en todas las variantes.
- [x] Clasificación: **P4_R7_PERIOD_2_ROBUST_NUMERICAL_ORBIT** (Caso A con matiz sensor) — robusta numéricamente como period-2 (backend/CFL/espacial), aunque sensor estricto 0.005 no se alcanza ni en lag2 original; requiere decisión científica para E13. No P4 PASS, no P5, no multicore AUTO (workers=1).

Evidencia: `results/p4-r7-20260921/closure.json`, `continuation.json`, `backend.json`, `cfl.json`, `spatial_N*.json`, `orbit_comparison.json`, `docs/gasdynamic/p4_r7_robustness.md`, `results/p4-r7-20260921/decision.json` (multicore no modificado, workers=1).

## P4-R12 — cierre por ramas (orden 87e62d1e)

- [x] Auditoría N400 ciclo54 válida: continuación normal desde `restart_cycle50`; D2 compara 54 contra 52 y reproduce `sensor_max=0.009046195029969764`; conservación/admisibilidad PASS.
- [x] Continuación única N350 desde `restart_cycle50`: sólo ciclos 51 y 52 ejecutados; ciclo52 PASS, conservación/admisibilidad PASS.
- [x] Seguimientos impar/par independientes: N350 impar 5, par 3; N400 impar 6, par 2 con secuencia par `[PASS,PASS,FAIL]`.
- [x] Corrección de serialización booleana: JSON `true`/`false`, nunca cadenas; tests específicos de streak y `numpy.bool_` PASS.
- [x] R11 corregido y separado: `P4_R11_PERIOD2_LAG2_CLOSURE_CONFIRMED` permanece válido bajo su contrato global.
- [x] Clasificación terminal R12: **P4_R12_ONE_BRANCH_NONCLOSURE**.
- [x] OpenSpec estricto PASS; no se ejecutaron N400 56/58/60, E13-R1, P4 PASS ni P5.

## P4-R13 — horizonte fijo N400 (orden 235a9a48)

- [x] Restart54 validado: N400, backend NUMBA_FUSED, CFL 0,4, float64, ángulo/ciclo 54; continuación física 55–60 sin early stop.
- [x] Ciclos 55, 56, 57, 58, 59 y 60 completados con conservación/admisibilidad PASS; checkpoints y FULL_DEBUG guardados.
- [x] Comparaciones disponibles: 58 vs 56 y 60 vs 58 PASS; control impar 57 vs 55 y 59 vs 57 PASS.
- [x] Se conserva el FAIL R12 de 54 (`0.009046195029969764`); 56 vs 54 queda como brecha explícita porque R12 no guardó historia angular completa y no se repitió R12.
- [x] Horizonte termina en 60; no se ejecutaron 62+, N350/N300/N500, E13-R1, P4 PASS ni P5.
- [x] Clasificación conservadora: **P4_R13_N400_EVEN_INTERMITTENT_NONCLOSURE**; no se acredita cierre eventual sin 56 vs 54.
- [x] Tests R13/R12: 10 PASS; OpenSpec estricto PASS.

## P4-R13A — cierre de evidencia 56 vs 54

- [x] Replay sólo 51–54 desde el restart N400 ciclo50; terminal ciclo54 bitwise exacto contra restart R12: `P4_R13A_CYCLE54_REPLAY_EQUIVALENCE_PASS`.
- [x] Reutilizado el `full_cycle56.json.gz` existente; 56 vs 54 PASS, `sensor_max=0.0011905119731371136`, sensor dominante 0, fase 132,5°.
- [x] Secuencia par sin gap: 50 PASS, 52 PASS, 54 FAIL, 56 PASS, 58 PASS, 60 PASS.
- [x] Clasificación corregida: **P4_R13_N400_EVEN_EVENTUAL_CLOSURE**; el FAIL de 54 permanece visible.
- [x] Tests R13A/R13/R12: 15 PASS; OpenSpec estricto PASS.
- [x] No se repitieron 55/56 de R13, no se ejecutaron 61+, E13-R1, P4 PASS ni P5.
- [x] 23/09/2026 — Decisión humana: P4 BLOCKED/NOT_GRANTED y P5 AUTHORIZED_CONDITIONAL; documentación actualizada. No se implementó P5 ni se reabrió P4.

## P4-C3-R5 — contrato aprobado 2026-09-28 (sin adquisición)

### Correcciones de revisión P1/P2

- [x] Exigir `solver_time` y `target_final_time` finitos, con llegada al objetivo;
  conservar `INCONCLUSIVE` para evidencia ausente/truncada y `FAIL` sólo para
  estados explícitos de fallo del solver.
- [x] Blindar A/B0/B1 frente a caras, fluxes, ondas y razones persistidas
  ausentes, cortas o no numéricas; mantener `FAIL` para contradicción semántica
  válida de `fallback_reason`.
- [x] Ejecutar tests focales P4-C3-R5/R4/return y OpenSpec estricto; no ejecutar
  adquisición, E13/G2 ni P9.

- [x] Congelar recibo aprobado A/B0/B1/B2 en `p4_c3_r5_preregistration_proposal.md`;
  C3 sigue `P4_SCI_C3_INCONCLUSIVE`, E13/G2 `NOT_EXECUTED`, P9 `STOPPED`.
- [x] Capturar diagnósticamente todas las caras de momentum de stage A/B:
  estados reconstruidos, flux vectorial completo, ondas, fallback y `down`.
- [x] Auditar B0 independiente con identidad exacta de caras y
  `downgraded_cells`; cualquier ausencia/diferencia bloquea B1/B2.
- [x] Auditar B1 independiente HLLC/HLLE con paridad exacta de vector, ondas y
  razón; no usar ULP ni umbral de magnitud frente a ExactRiemann.
- [x] Auditar B2 con replay bitwise de fuente, RHS, `q1`, `q2` y combinación
  SSPRK2 en checkpoints declarados; conservar residual de volumen como métrica.
- [x] Añadir pruebas sintéticas de independencia, mutación, fallback, runtime,
  serialización/hash y un caso analítico B2 no fabricado por el helper.
- [x] Ejecutar sólo tests focales y OpenSpec estricto; no ejecutar adquisición
  C3-R5, E13/G2, P9 ni campañas costosas.

- [ ] Revisión independiente final R5 sin hallazgos bloqueantes.
- [ ] Ejecutar exactamente una adquisición focal C3-R5 y persistir evidencia;
  no ejecutar E13/G2 ni P9.
- [ ] Revisión independiente final R5 sin hallazgos bloqueantes (pendiente de reviewer conectado); 26 tests focales, regresiones relacionadas y OpenSpec strict PASS.
- [x] Una única adquisición focal C3-R5 ejecutada y evaluada; evidencia en `results/p4-c3-r5-20260928/`.

## Auditoría C3-R5 y E13/G2 — 2026-09-28
- [x] C3-R5 formalizado como `P4_SCI_C3_PASS` con una única adquisición y recibo `results/p4-c3-r5-20260928/c3-closure-receipt.json`. La revisión independiente conectada sigue pendiente; la autorrevisión no se presenta como independiente.
- [x] Auditoría R6/R7/R10/R10A/R11/R12/R13/R13A y OpenSpec: `E13_CONTRACT_ALREADY_SUPPORTS_PERIOD2`; G2 histórico 1–30 permanece `P4_G2_MAX30_WITHOUT_E13_CONVERGENCE` (rama B sin cierre). P4 sigue BLOCKED/NOT_GRANTED; no se ejecutaron campañas nuevas, P5 ni P9.
- [x] Detalle: `docs/gasdynamic/p4_e13_g2_contract_audit_20260928.md`.

## Auditoría causal G2 — 2026-09-29
- [x] Se revisaron continuidad, emparejamiento lag-2, identidad de ramas, conservación, admisibilidad, CFL, backend, malla y checkpoints; no se identificó defecto técnico reproducible.
- [x] Rama A cerró (streak 5); rama B falló 14/14 comparaciones y terminó en `sensor_max=0.0290580`; resultado contractual `E13_G2_FAIL` bajo `max_cycles=30`.
- [ ] Decisión humana si se desea cambiar el horizonte contractual; no se ejecutaron ciclos 31+, no se cambiaron thresholds ni física.
- [x] Auditoría detallada: `docs/gasdynamic/p4_g2_root_cause_audit_20260929.md`.

## G2-v2 — preregistración 2026-09-29
- [x] Preregistrado antes de la adquisición: único delta `max_cycles=400`; thresholds, métricas, ramas, streaks, solver, malla, CFL y física congelados.
- [ ] Verificar continuation desde ciclo30 y ejecutar hasta PASS o ciclo400; no ejecutar ciclo401+.
- [ ] Persistir evaluación, decisión, regresiones y matriz P4 final sólo después de la adquisición.
- [x] Documento: `docs/gasdynamic/p4_g2_v2_preregistration_20260929.md`.

## Cierre técnico P4 con G2-v2 — 2026-09-29
- [x] Continuation validada desde ciclo30 y ciclos31–50 ejecutados; parada temprana contractual en ciclo50 por `CONVERGED_PERIOD2`.
- [x] `E13_G2_V2_PASS`: rama A streak15, rama B streak3; conservación, admisibilidad y CFL PASS. Evidencia `results/p4-g2-v2-20260929/`.
- [x] Matriz final P4 persistida en `results/p4-g2-v2-20260929/p4-final-gate-matrix.json`; clasificación técnica `P4_PASS`.
- [ ] Revisión independiente conectada; permanece `INDEPENDENT_REVIEW_PENDING`. P5, P9 y validación experimental no iniciados.
- [x] Cierre: `docs/gasdynamic/p4_final_closure_g2_v2_20260929.md`.

## Recuperación de evidencia G2-v2 tras revisión adversarial — 2026-09-29

- [x] Preservar sin cambios los tres hallazgos BLOCKER/MAJOR en commit `544d2dc`; la revisión histórica continúa BLOCKED.
- [x] Corregir persistencia de historias angulares e insumos E13, restauración versionada del detector y gate CFL explícito; regresiones negativas y continuous/restart PASS.
- [x] Recalcular el estado del detector desde los ciclos originales 1–30, sin constantes manuales: al ciclo30 lag1=0, A=5, B=0.
- [x] Nueva adquisición G2-v2 en `results/p4-g2-v2-reaudit-20260929-r2/`: ciclos31–50, sin 51+; 20 estados terminales coinciden exactamente con la corrida histórica.
- [x] Auditor offline independiente del código productivo recalculó E13, conservación, admisibilidad, CFL, identidad, ancestry y detector: `E13_G2_V2_PASS`, período2 ciclo50, A=15, B=3, `sensor_max=0.000508629756519752`.
- [x] 152 pruebas P4/E13 PASS, OpenSpec estricto PASS, `git diff --check` y Git LFS fsck PASS; matriz técnica nueva en `p4-recovery-matrix.json`.
- [ ] Nueva revisión independiente en otro contexto: `READY_FOR_NEW_INDEPENDENT_REVIEW`; no se registra `INDEPENDENT_REVIEW_PASS` ni validación experimental.

## Remediación del MAJOR R2 de auditoría — 2026-09-29

- [x] Preservar intactos el reporte y receipt R2 bloqueados de `4214703`; no reinterpretar sus hallazgos históricos.
- [x] Rechazar tipos no numéricos en `dt`, límites CFL y demás entradas numéricas científicas del auditor; `dt` debe ser finito y positivo. Evidencia malformada queda `INCONCLUSIVE`.
- [x] Regresión exacta R2 sobre copia del checkpoint50 con `dt=false` y hash de cierre actualizado: `MALFORMED_CFL_DT`, nunca PASS; pruebas adversariales de booleanos, nulos, texto, arrays, cero, negativos y no finitos.
- [x] Reauditar los checkpoints G2-v2 existentes sin simular de nuevo: `E13_G2_V2_PASS`, período2 ciclo50, seed 0/5/0, final A15/B3; 44 FAIL, 48/50 PASS; conservación, admisibilidad y CFL PASS.
- [x] Confirmar P4 técnico `P4_PASS` sobre gates históricos intactos; runtime binding C3 siete hashes exactos y P5–P8 seis hashes de provenance exactos. Mantener P5–P8 revalidados; campaña P8 no repetida por ausencia de impacto productivo.
- [x] 183 pruebas P4/E13, 109 P5–P8/acoplamiento y 53 regresiones adicionales PASS; OpenSpec estricto en cuatro cambios, `git diff --check` y `git lfs fsck` PASS. [Auditoría y receipt nuevos](../../../results/p4-g2-v2-r2-remediation-20260929/receipt.json).
- [ ] Nueva revisión independiente: `READY_FOR_NEW_INDEPENDENT_REVIEW`. R2 histórico sigue BLOCKED; no hay validación experimental ni autorización P9.

## Revisión adversarial R3 P4→P8 — 2026-09-29
- [x] Reproducción R2 `dt=false` tras actualizar hash: `MALFORMED_CFL_DT`, clasificación `E13_G2_V2_INCONCLUSIVE`; 82 pruebas focales PASS.
- [x] Recalcular independientemente métricas 44/48/50 y verificar tipado estricto del auditor G2.
- [x] Revisar artefactos C3 y pruebas/provenance P5–P8 con agentes de solo lectura; validación LFS y OpenSpec PASS.
- [ ] R3 no ratifica P4→P8: BLOCKER R3-001 por ledger bruto de conservación G2 31–50 ausente; MAJOR R3-002 por gate replay P8 que acepta salidas divergentes. La evidencia de conservación no prueba un fallo físico; se detuvo ratificación conforme al hard stop.
- [ ] Confirmar runtime binding C3 completo y repetir revisión independiente tras corregir los hallazgos; P9 permanece detenido.
- Reporte: `docs/gasdynamic/p4_p8_independent_review_r3_20260929.md`; receipt: `results/p4-p8-independent-review-r3-20260929/review.json`.

## Remediación R3 y recuperación técnica P4→P8 — 2026-09-29
- [x] Preservar sin cambios el reporte y receipt R3 BLOCKED de `17b3652`; R3 permanece como registro histórico, no como aceptación.
- [x] R3-001: adquirir 31–50 con ledger primario de inventarios, flujos de etapa, fuentes, intervalos y balances; auditar de forma independiente desde entradas persistidas. Los estados conservativos/celdas 31–50 coinciden exactamente con la adquisición previa.
- [x] Mutation tests del auditor: inventarios inicial/final y flujos alterados, términos faltantes, no finitos, malformados y residuo diagnóstico mutado; decisión basada en recálculo independiente.
- [x] G2-v2 revalidado: `E13_G2_V2_PASS`, período 2 en ciclo 50, A=15/B=3; conservación, admisibilidad y CFL pasan. Evidencia primaria/auditoría: `results/p4-g2-v2-ledger-recovery-20260929-retry/`.
- [x] R3-002: gate exacto ampliado a estado conservativo terminal, ledgers acumulados, especies, entrega fresca, short-circuit, eventos y estado P7; digest SHA-256 canónico de cada recorrido independiente.
- [x] Mutation tests de fresh delivery, short-circuit y divergencia del digest impiden aprobar replay alterado; P6 snapshot/restore conserva el baseline de ledger de especies y su tipo canónico.
- [x] Repetir únicamente los cinco anchors P8 porque la evidencia anterior no persistía ambos estados terminales requeridos por el gate corregido; los cinco anchors aprueban finite, geometría, admisibilidad, especies, P7, CFL, masa/energía, restart y replay determinista. Evidencia: `results/p8-wide-rpm-replay-r3-20260929-r3/`; semántica `BOUNDED_TRANSIENT_INDICATED`.
- [x] Revalidar suites P4 (188 PASS, 2 campañas/adquisiciones excluidas), G2 focal (57 PASS, 1 adquisición excluida), P5–P7 (90 PASS), P8 replay (12 PASS, campaña probada por adquisición separada), P6 snapshot (16 PASS); OpenSpec estricto en P4/P5/P7/P8.
- [x] Runtime binding C3-R5: siete hashes/componentes coinciden exactamente; no se repitió C3.
- [x] Matriz de recuperación: `results/p4-p8-r3-remediation-20260929/recovery-matrix.json`. P4 recuperado técnicamente; aceptación sigue pendiente de revisor independiente final. P5–P8 continúan condicionales a P4.
- [x] Revisión independiente final R4 ejecutada el 2026-09-30 desde HEAD `3ae81d0`; resultado `INDEPENDENT_REVIEW_BLOCKED` por MAJOR R4-001 reproducible en la auditoría durable P8. No se concede aceptación P4→P8; validación experimental permanece `NOT_PERFORMED` y P9 `STOPPED_NOT_AUTHORIZED`.
- Reporte de remediación: `docs/gasdynamic/p4_p8_r3_remediation_20260929.md`.

## Revisión independiente final R4 P4→P8 — 2026-09-30
- [x] Verificar baseline limpio `3ae81d0d6197a39198297bb579178c2eaaa04c1a`, igual a `origin/main`; preservar reportes y receipts R1/R2/R3.
- [x] Reauditar R3-001 desde ledger primario; mutaciones de inventarios, flujos, fuentes, términos faltantes, no finitos, volumen de control e intervalos se rechazan. G2 sigue `E13_G2_V2_PASS`, ciclo 50, período 2, A=15/B=3; estados/celdas 31–50 tienen igualdad exacta tras parseo.
- [x] Reproducir R2 `dt=false` con hash actualizado: `MALFORMED_CFL_DT`, nunca PASS. Revisar C3 receipt y sus siete hashes runtime-binding sin repetir adquisición.
- [x] Ejecutar suites focales P4/E13, P5–P7, P8 replay y P6 snapshot; OpenSpec estricto P4/P5/P7/P8, `git diff --check` y Git LFS fsck aprobaron. Las exclusiones por filtro inicial y de campañas se identifican en el reporte R4.
- [x] Reproducir en copia temporal la alteración concordante de `fresh_mass_delivered_kg`, `fresh_short_circuit_mass_kg` y `replay_terminal_digests.first` en JSON consolidado/individual: `_audit_p8` conserva `closure_ok=true`, `replay_ok=true` y `csv_equal=true` en los tres casos.
- [ ] Corregir fuera de esta revisión la verificación durable P8 y repetir auditoría adversarial; hasta entonces `INDEPENDENT_REVIEW_BLOCKED`, P4–P8 no ratificados, P9 detenido y validación experimental `NOT_PERFORMED`.
- Reporte R4: `docs/gasdynamic/p4_p8_independent_review_r4_20260930.md`; receipt: `results/p4-p8-independent-review-r4-20260930/review.json`.

## Ratificación independiente final P4→P8 — 2026-09-30
- [x] Desde HEAD `78615563ad7f8e4f1dde9ee05226119ffc3433a4`, reproducir en copia temporal el ataque FINAL-001 coherente contra el anchor P8 de 2500 rpm; el auditor rechaza el terminal alterado con `trajectory_terminal_mismatch: conservative_state` y la evidencia comprometida queda intacta.
- [x] Revisar la captura post-install aceptada, comparación exacta trajectory→terminal, orden digest/preimage y ataques de estado/ledger/restart/summary; revisar `q_n` vs estado instalado sin tolerancia añadida.
- [x] Reauditar desde los diez artefactos primarios la campaña actual de cinco anchors P8: los cinco pasan todos los gates, con semántica `BOUNDED_TRANSIENT_INDICATED`.
- [x] Recalcular offline G2 desde checkpoints y ledger durables hasta ciclo 50: `E13_G2_V2_PASS`, período 2, A=15/B=3; reproducir R2 `dt=false` como `INCONCLUSIVE / MALFORMED_CFL_DT`.
- [x] Verificar igualdad de siete hashes runtime-binding C3 y recalcular offline sus 777 registros guardados: retorno causal, A, B0, B1 en ambas etapas, B2 y conservación PASS; sin nueva adquisición.
- [x] Ejecutar P4/E13 (190), regresión R2 exacta (1), P5–P7/acoplamiento (100), P8/R4 (23; solo prueba de campaña excluida), OpenSpec estricto P4/P5/P7/P8, `git diff --check` y `git lfs fsck`; todos pasan.
- [x] Resultado independiente: `INDEPENDENT_REVIEW_PASS`; P4 `P4_PASS`; P5–P8 `REVALIDATED_ON_P4_PASS`; P9 queda `READY_FOR_P9_HUMAN_AUTHORIZATION`, no iniciado; validación experimental `NOT_PERFORMED`.
- [x] Preservar sin cambios los reportes y receipts históricos `INDEPENDENT_REVIEW_BLOCKED`.
- Reporte: `docs/gasdynamic/p4_p8_independent_final_pass_20260930.md`; receipt: `results/p4-p8-independent-final-pass-20260930/review.json`.
