## P1-R1
- [x] Leer orden y preservar estado ajeno (eliminación de redme.txt).
- [x] Definir estimadores y microcaso antes de la serie, sin modificar gas1d/P1.
- [x] Probar estimadores y ejecutar estudio mediante dev_orchestrator.
- [x] Registrar ocho casos, errores, conservación, tiempos y gate científico.
- [x] Revisión independiente read-only del observable y evidencia.
- [x] OpenSpec estricto, alcance, hashes y commits locales (fuente y cierre).

P2 sigue condicionado; no acredita R1 ni reanudación por preparar herramientas.

## Resultado científico — 17/09/2026
**P1_R1_CONTACT_ACCURACY_UNRESOLVED**. No se adopta 1D_CONTRACT_V1_R1.
B en N400 =0.6909106468612537, error0.005420122851463427 =2.168049140585371dx;
límite sin modificar2dx=0.005. El original A conserva FAIL2.803790396dx.
El refinamiento reduce error absoluto, pero el error en dx aumenta. Cruce único
Y=0.5 y monotonía local estrictamente comprobados en los ocho casos; sin clipping.
Recomendación: no reemplazar A por B contractual con esta evidencia. C/D son
solo diagnósticos, incluso cuando D da menor error; no hay selección por resultado.
D usa densidad dentro de la ventana de B (no localización totalmente independiente).
La ventana queda separada del shock exacto0.8504311464 en todas las mallas.

Fuente f3e4453a781286e885e2f2bd448fd87dd91ad9ba. Ejecución única
20260917T170640-P1_R1_SCIENTIFIC_AMENDMENT-11e76c02c4ca, 8/8 integraciones
completadas, seis pruebas del observable aprobadas dentro del runner.
Evidencia preservada en results/p1-r1-contacto-20260917, arrays y ledgers completos
comprimidos sin pérdida; estudio e inventarios JSON. N400 coincide exactamente
con el Sod previo en estados, flujos e inventarios/ledger (historical-comparison.json).

Gate técnico original BLOCKED por contact_accuracy y review_not_approved
(revisor automático no acredita revisión científica); execution_status COMPLETED,
sin errores de infraestructura ni violaciones de alcance. Se preserva evidence.json;
la revisión independiente posterior se adjunta separadamente, sin reescribirlo.

### Sod: posiciones
Exacto0.6854905240097903. A=max gradiente Y; B=cruce0.5; C=centroide;
D=max gradiente de densidad en ventana diagnóstica.

| N | dx | A | B | C | D |
|---:|---:|---:|---:|---:|---:|
| 200 | 0.005 | 0.695000000000 | 0.693038270129 | 0.692846369895 | 0.680000000000 |
| 400 | 0.0025 | 0.692500000000 | 0.690910646861 | 0.690722941587 | 0.682500000000 |
| 800 | 0.00125 | 0.690000000000 | 0.689376925452 | 0.689133454233 | 0.683750000000 |
| 1600 | 0.000625 | 0.688750000000 | 0.688269622388 | 0.688067783401 | 0.685000000000 |

### Errores absolutos / dx

| Caso | N | A | B | C | D |
|---|---:|---:|---:|---:|---:|
| sod | 200 | 0.009509476 / 1.901895 | 0.007547746 / 1.509549 | 0.007355846 / 1.471169 | 0.005490524 / 1.098105 |
| sod | 400 | 0.007009476 / 2.803790 | 0.005420123 / 2.168049 | 0.005232418 / 2.092967 | 0.002990524 / 1.196210 |
| sod | 800 | 0.004509476 / 3.607581 | 0.003886401 / 3.109121 | 0.003642930 / 2.914344 | 0.001740524 / 1.392419 |
| sod | 1600 | 0.003259476 / 5.215162 | 0.002779098 / 4.446557 | 0.002577259 / 4.123615 | 0.000490524 / 0.784838 |
| pure_contact | 200 | 0.020000000 / 4.000000 | 0.014182855 / 2.836571 | 0.014156059 / 2.831212 | 0.000000000 / 0.000000 |
| pure_contact | 400 | 0.012500000 / 5.000000 | 0.009942601 / 3.977040 | 0.009442889 / 3.777156 | 0.000000000 / 0.000000 |
| pure_contact | 800 | 0.008750000 / 7.000000 | 0.006988725 / 5.590980 | 0.006299126 / 5.039301 | 0.000000000 / 0.000000 |
| pure_contact | 1600 | 0.006250000 / 10.000000 | 0.004919231 / 7.870770 | 0.004391183 / 7.025893 | 0.000000000 / 0.000000 |

### Contacto puro: posiciones
Exacto0.5; p=u=1, rhoL1/rhoR2, YL1/YR0; x inicial0.25, t0.25.
No equivale a repetir o aprobar T06; caso independiente autorizado.

| N | dx | A | B | C | D |
|---:|---:|---:|---:|---:|---:|
| 200 | 0.005 | 0.480000000000 | 0.485817145050 | 0.485843941079 | 0.500000000000 |
| 400 | 0.0025 | 0.487500000000 | 0.490057399123 | 0.490557111067 | 0.500000000000 |
| 800 | 0.00125 | 0.491250000000 | 0.493011274768 | 0.493700874217 | 0.500000000000 |
| 1600 | 0.000625 | 0.493750000000 | 0.495080768753 | 0.495608816580 | 0.500000000000 |

### Errores integrales, conservación y coste
Mismo CFL0.4; conservación = peor residuo normalizado del ledger de cuatro componentes.

| Caso | N | L1 rho | L1 u | L1 p | Conservación | HLLE crudo | Tiempo solver (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| sod | 200 | 0.0114897092 | 0.0180137882 | 0.00957497161 | 2.08513e-16 | 0 | 0.672 |
| sod | 400 | 0.00723442066 | 0.00991462899 | 0.00565659557 | 2.38701e-16 | 0 | 2.610 |
| sod | 800 | 0.0045188563 | 0.00540046592 | 0.00328979815 | 2.91919e-16 | 0 | 10.688 |
| sod | 1600 | 0.00287431027 | 0.00306846633 | 0.00190717127 | 2.44521e-16 | 0 | 45.609 |
| pure_contact | 200 | 0.0254513559 | 1.62092562e-16 | 2.58681965e-16 | 8.40597e-16 | 0 | 0.703 |
| pure_contact | 400 | 0.0180123749 | 2.04003481e-16 | 2.42306175e-16 | 4.9167e-16 | 0 | 3.157 |
| pure_contact | 800 | 0.0127420979 | 2.44665399e-16 | 3.99125177e-16 | 2.39491e-15 | 0 | 12.844 |
| pure_contact | 1600 | 0.00901183596 | 2.78319034e-16 | 3.51663143e-16 | 6.01106e-15 | 0 | 49.579 |

Tiempo acumulado del solver: 125.862s. No incluye referencias,
serialización ni cierre del runner. Los contadores HLLC anteriores no se certifican;
no se corrigieron bajo este gate. HLLE0 en ocho casos.

### Contrato y continuación
Diff científico exacto P1 original→R1: **vacío**; R1 no adoptado. Contrato v1,
N400, 2dx, EOS, IC, tiempo, HLLC/HLLE/FE/CFL y L1/L2 intactos por hashes.
P0/producción también intactos. No hay fixes P2 en esta etapa: contabilidad HLLC,
exterior no reflectivo y rama T05 siguen pendientes. T05 antes: fallo a17pasos;
después: NO EJECUTADO porque el gate no habilitó sus correcciones.
T01–T12 no se reanudó; 0/3 reparaciones P2 consumidas, P2B/P3 sin iniciar.
La siguiente decisión sobre precisión/malla contractual/first-order corresponde
al humano; no se anticipa aquí. Sin publicar, archivar ni aceptación experimental.

### Revisión y cierre documental — 18/09/2026
Revisión independiente read-only /root/p1_r1_review: PASS del estudio y su
implementación; decisión científica UNRESOLVED. Recomputó A/B/C/D en8/8 casos,
verificó11/11 hashes del inventario y equivalencia del SodN400 histórico.
Sin hallazgos bloqueantes del estudio; no autoriza P2. El dictamen sustantivo fue
recibido por mensaje antes de que su turno terminara por límite de uso; no se
atribuye otra ronda posterior. Registro en artifacts/independent-review.json,
separado del stub y vinculado por SHA256 al evidence.json original intacto.
Autorrevisión del principal separada: alcance, diff e inventarios de cierre.
No se repitieron integraciones al retomar; se conservó la evidencia del17/09.

OpenSpec estricto PASS al cierre; diff sin errores de whitespace e inventarios
SHA256 verificados. Fuente f3e4453; el commit que contiene este registro conserva
la evidencia final. Ambos commits locales; sin push. redme.txt ajeno preservado.
