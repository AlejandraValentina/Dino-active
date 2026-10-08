## P1-R2 — cierre en gate
- [x] Preservar estado local y fijar detector antes de evaluar (3b5c82b).
- [x] Pruebas de independencia/discriminación:7PASS.
- [x] Reevaluar ocho soluciones preservadas vía dev_orchestrator (982a668).
- [x] Revisión independiente: P1_R2_PASS_CONTACT_OBSERVABLE.
- [x] Adoptar1D_CONTRACT_V1_R2 como delta único; originales íntegros.
- [x] Corregir contadores HLLC y estado exterior no reflectivo;6tests finalesPASS.
- [x] Ensayar T05, diagnosticar fallo y retirar excepción no contractual.
- [ ] T05 PASS: bloqueado por incompatibilidad de ramas; requiere decisión científica.
- [ ] Reanudar T01–T12: NO autorizado efectivamente porque T05 no aprueba.
- [x] Revisión puntual,24tests finalesPASS, OpenSpec estricto e integridad.
- [x] Documentar evidencia y commits locales; sin publicar/archivar/P3.

La eliminación previa de redme.txt permanece ajena y fuera de los commits.
P1-R1 y su evidencia no se modifican. R2PASS no equivale a P2A PASS.

## Definición y congelación
HYDRO_CONTACT_CHARACTERISTIC_V1 fue fijado en3b5c82b antes de evaluar.
Código: motorsim/gas1d/contact.py; fórmula y regla en design.md y
[delta normativo](../../../docs/gasdynamic/1d_contact_observable_v1_r2.md).
Entrada únicamente centros/rho/u/p/gamma. Todas las caras, sin Y/exacto/ventana.
Dominio de aplicación: contacto único de Sod y microcaso puro, no detector
universal de múltiples ondas. No se probaron variantes para elegir el menor error.
A/B/C heredados quedan diagnósticos; D anterior condicionado por B se conserva
como antecedente separado, no se confunde con el detector independiente actual.

## Estudio preservado
Reevaluación8/8 de arrays R1, hashes correctos; ninguna nueva integración para
el estudio de malla. Referencia exacta Sod0.6854905240097903; puro0.5.
CFL0.4, estados y ledgers idénticos a R1. El exacto se usa solo DESPUÉS de detectar.

| Caso | N | dx | x exacto | x detectado | Error absoluto | Error/dx | L1 rho | L1 u | L1 p | Conservación |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sod | 200 | 0.005 | 0.685490524010 | 0.680000000000 | 0.005490524 | 1.098105 | 0.01148971 | 0.01801379 | 0.009574972 | 2.0851e-16 |
| sod | 400 | 0.0025 | 0.685490524010 | 0.682500000000 | 0.002990524 | 1.196210 | 0.007234421 | 0.009914629 | 0.005656596 | 2.387e-16 |
| sod | 800 | 0.00125 | 0.685490524010 | 0.683750000000 | 0.001740524 | 1.392419 | 0.004518856 | 0.005400466 | 0.003289798 | 2.9192e-16 |
| sod | 1600 | 0.000625 | 0.685490524010 | 0.685000000000 | 0.000490524 | 0.784838 | 0.00287431 | 0.003068466 | 0.001907171 | 2.4452e-16 |
| pure_contact | 200 | 0.005 | 0.500000000000 | 0.500000000000 | 0.000000000 | 0.000000 | 0.02545136 | 1.620926e-16 | 2.58682e-16 | 8.406e-16 |
| pure_contact | 400 | 0.0025 | 0.500000000000 | 0.500000000000 | 0.000000000 | 0.000000 | 0.01801237 | 2.040035e-16 | 2.423062e-16 | 4.9167e-16 |
| pure_contact | 800 | 0.00125 | 0.500000000000 | 0.500000000000 | 0.000000000 | 0.000000 | 0.0127421 | 2.446654e-16 | 3.991252e-16 | 2.3949e-15 |
| pure_contact | 1600 | 0.000625 | 0.500000000000 | 0.500000000000 | 0.000000000 | 0.000000 | 0.009011836 | 2.78319e-16 | 3.516631e-16 | 6.0111e-15 |

Ocho máximos únicos; errores absolutos Sod decrecientes. Contacto puro: rho1/2,
p=u=1,x0.25,t0.25,BCfijas,gamma1.4/R1; posición exacta obtenida en cuatro
mallas, sin atribuir orden de convergencia a errores cero. Y no participa.
Todos<=2dx. HLLE crudo0 en arrays heredados; contadores HLLC históricos no
se certifican retrospectivamente por haberlos corregido ahora.

### Comparación A/B/C/D, error en dx

| Caso | N | A gradiente Y | B cruce Y | C centroide Y | D hidrodinámico |
|---|---:|---:|---:|---:|---:|
| sod | 200 | 1.901895 | 1.509549 | 1.471169 | 1.098105 |
| sod | 400 | 2.803790 | 2.168049 | 2.092967 | 1.196210 |
| sod | 800 | 3.607581 | 3.109121 | 2.914344 | 1.392419 |
| sod | 1600 | 5.215162 | 4.446557 | 4.123615 | 0.784838 |
| pure_contact | 200 | 4.000000 | 2.836571 | 2.831212 | 0.000000 |
| pure_contact | 400 | 5.000000 | 3.977040 | 3.777156 | 0.000000 |
| pure_contact | 800 | 7.000000 | 5.590980 | 5.039301 | 0.000000 |
| pure_contact | 1600 | 10.000000 | 7.870770 | 7.025893 | 0.000000 |

## Revisión y contrato
Revisor read-only /root/p1_r2_review: PASS del observable, verificó8gzip/hashes,
recalculó8detecciones e identidad del detector con3b5c82b. Máximo|dp| y máximo
acústico de shock excluidos; interior de rarefacción comprobado a posteriori
(no es una ventana del algoritmo). Pruebas ideales también separan shock,
acústica, contacto, ausencia y empate. Sin hallazgos bloqueantes del observable.

El runner original P1_R2 terminó COMPLETED/BLOCKED exclusivamente por stub
review_not_approved. evidence.json se conserva intacto; reviewed-evidence.json
es recibo derivado mediante el evaluador de gates con la revisión independiente,
PASS y hash del original. No se atribuye revisión al stub ni aceptación humana
experimental. Usuario autorizó explícitamente continuación condicional trasPASS.

Diff exacto JSON P1→R2: /model_version y /verification_cases/1/definition.
Único cambio científico: detector de contactoT02. Shock,N400,<=2dx,IC,EOS,
CFL,HLLC,FE,L1/L2 y todoT06 intactos. Manifest original conserva bytes/hash;
R2 y delta literal en docs/gasdynamic/1d_contract_v1_r2*.json.

## Fixes y T05
Commitde1d896 retuvo contadores de llamadas reales (cara periódica una vez,
flujos característicos separados, estadosghost reales enfallback) y uso de
K/Y del estado exterior explícito no reflectivo. La revisión detectó subconteo
cuando falla una frontera después de evaluar caras interiores: corregido y
cubierto con test que verifica4llamadas antes del fallo. No cambia HLLC/HLLE.

Se ensayó además una excepción provisional de8ulp para asignar velocidadcero
cerca del reposo. **Era incompatible con la prohibición expresa de imponeru=0**
y se retiró. Se conserva su código histórico y corrida fallida sin atribuirle
T05 contractual: mismos parámetros/sensor/ventanas, pero BCprovisional no válida.
No se amplía banda, mezcla entropía ni cambia el contrato para aprobar.

T05 histórico: fallo17pasos. Ensayo provisional: fallo2764pasos,t0.002702880649s,
39.078s solver, No consistent open-boundary branch. No alcanzó tiempo final;
no hay coeficiente de reflexión ni pico final aprobados. El estado fallido,
recalculado con70dígitos, exige w_salida=-3.64578601597e-11 y
w_entrada=+4.12278103106e-8. Ninguna rama cumple su signo; no es cancelación
float64. Datos y diagnóstico completo en artifacts/t05-diagnosis.json.
El código final rechaza tanto el estado histórico como el provisional offline.
No se repite la integración después de retirar la excepción: el bloqueo ya está
reproducido y confirmado, no se acredita recorrido completo del código final.

Dictamen independiente: SCIENTIFIC_CHANGE_REQUIRED para fronteraT05, separado
de P1_R2_PASS_CONTACT_OBSERVABLE. Dos fixes retenidos; fix de ramaT05 no resuelto.
Una ronda de reparación/ensayo P2 consumida de3; no gastar las restantes intentando
cambiar la ciencia. T01–T12 no se reanuda, P2B no se inicia, sinP3. La próxima
intervención requiere decisión explícita sobre compatibilidad de la BCabierta.

## Comprobaciones finales
7tests detector +6fixes +11gas1d =24PASS. Autorrevisión de alcance/hash separada
de revisión independiente. P0/P1/producción íntegros; ningún cambio en UI/JSON,
HLLC/HLLE,EOS,CFL o campañas0D. OpenSpec estricto aprobado.
Evidencia en results/p1-r2-contacto-20260918; no se archiva ni publica.
Commits de definición3b5c82b, estudio982a668 y adopción/fixesde1d896;
el commit de cierre contiene retirada de excepción y este registro.
