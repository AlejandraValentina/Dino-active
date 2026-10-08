# P3 — incompatibilidad de backflow del reservorio congelado

Estado: **P3_BLOCKED_BACKFLOW / SCIENTIFIC_CHANGE_REQUIRED**.
Aceptación humana **P2_HUMAN_ACCEPTED** registrada por orden a75bf738.
P2 permanece verificado dentro de sus casos; este caso nuevo descubre un límite
fuera de su cobertura. No se altera retrospectivamente su evidencia ni aceptación.

## Implementado y alcance real

`motorsim/coupling.py` es una interfaz aislada: estado homogéneo m/U/F/V,
conversión EOS y una evaluación de flujo Euler compartido a partir de la cara
reservoir verificada. Produce incrementos opuestos, pero NO contiene todavía
un integrador 0D/1D, ni una conexión al motor productivo. No importar desde UI.
U es energía interna, y el flujo transporta entalpía total H=cp*T+u²/2;
no se duplica trabajo de flujo. Impulso axial separado, sin momentum0D.
Sin clipping, deadband, otra BC, otro problema Riemann ni alteraciones deP2.

## Reproducción de la incompatibilidad

p_pipe=p0=100000Pa, T0=300K, Y0=.8, Y_pipe=.2, A=.01m²,
EOS R287 y gamma1.35. Velocidad normal w=n*u, normal exterior del tubo.
42 evaluaciones: temperaturas299/300/301K, w=0,±1e-3,±1e-6,±1e-9m/s,
ambas orientaciones. Todos los estados interiores son admisibles/subsónicos.
Flujo positivo sale del tubo hacia0D; negativo sale de0D hacia tubo.

| T_pipe K | w m/s | w_cara m/s | Flujo másico kg/s | Resultado |
|---|---|---|---|---|
| 299.0 | -0.001 | -3.2353357613 | -0.0375747977512 | Definido |
| 299.0 | -1e-06 | -3.23434615101 | -0.0375633055717 | Definido |
| 299.0 | -1e-09 | -3.2343451614 | -0.0375632940795 | Definido |
| 299.0 | 0 | 0 | 0 | Definido |
| 299.0 | 1e-09 | 9.99989424599e-10 | 1.16531227739e-11 | Definido |
| 299.0 | 1e-06 | 1.00000011116e-06 | 1.16532473071e-08 | Definido |
| 299.0 | 0.001 | 0.000999999999976 | 1.16532460114e-05 | Definido |
| 301.0 | -0.001 | — | — | No consistent reservoir inflow branch |
| 301.0 | -1e-06 | — | — | No consistent reservoir inflow branch |
| 301.0 | -1e-09 | — | — | No consistent reservoir inflow branch |
| 301.0 | 0 | 0 | 0 | Definido |
| 301.0 | 1e-09 | 9.99989424599e-10 | 1.15756933867e-11 | Definido |
| 301.0 | 1e-06 | 1.00000011116e-06 | 1.15758170924e-08 | Definido |
| 301.0 | 0.001 | 0.000999999999976 | 1.15758158053e-05 | Definido |

La misma incompatibilidad se reproduce con orientación opuesta. A299K el
límite de entrada w→0− tiene velocidad de cara−3.2343451604m/s y flujo
aproximadamente−0.037563294kg/s; en reposo la rama de salida da flujo0.
A301K ni siquiera existe una raíz entrante física en ese vecindario.
No es una tolerancia de2dx/CFL ni una integración lenta; no se intenta rescatar
con pasos menores, igualando entropías o cambiando el criterio.

## Demostración con el contrato vigente

Entrada reservoir exige simultáneamente:
J+=w+2a/(gamma−1), a²/(gamma−1)+w²/2=h0=cp*T0,
y entropíaK0. Para−a<w<=0, la función
phi(w)=w+2*sqrt((gamma−1)*(h0−w²/2))/(gamma−1)
es creciente porque phi'(w)=1−w/a>0. Su máximo es
Jrest=2*sqrt((gamma−1)*h0)/(gamma−1), alcanzado en w=0.
Para el estado interior301K, J+>Jrest aun con w=−1e−3m/s: no existe raíz
entrante. La rama saliente, con p_pipe=p0 y Ki interior, devuelve el w
interior negativo y tampoco es consistente como salida.

El límite algebraico se obtiene de
(gamma+1)*w²−2*(gamma−1)*J*w+(gamma−1)*J²−4*h0=0.
A299K la raíz negativa es finita; al cambiar a la rama saliente en reposo
se reemplaza K0 por Ki, produciendo el salto. A300K el límite matemático
es0 (la evaluación cuadrática registra1.94e−13 por redondeo, sin clipping).
El problema afecta al cierre de características/entropía congelado deP1,
implementado en boundary.py; no se corrige con un wrapper de signos.

## Energía, especie y contabilidad

No se encontró ambigüedad energética: entrada H=cp*T0=332100J/kg,
retorno H del estado de cara donante. Las pruebas verifican H y especie en
ambos sentidos, rechazo de estados inválidos, equilibrio puntual e impulso.
Los incrementos opuestos son una prueba algebraica, NO un ledger de un sistema
finito ya integrado. No hay todavía ledgers combinados por paso/stage ni p*dV.
SSP-RK2 acoplado, sincronización temporal y adaptador0D quedan sin implementar
hasta resolver la incompatibilidad, conforme al gate P3A antes deP3B.

## Verificación y pendientes

74 pruebas automatizadas PASS (70 previas +4 de interfaz). El test que espera
la excepción documenta que no se oculta; su PASS NO acredita backflow físico.
P2 revalidado offline con58 finales, T01–T12 PASS bajoR5; FIRST_ORDER/R4 intacto.
Siete regresiones históricasP0 offline PASS. Hashes del núcleo/contratos
coincidentes con aceptaciónP2; ninguna integración nueva de producción.

C01–C12 NO completados: C04 bloqueado por la incompatibilidad; restantes
NOT_RUN en la matriz del preflight. No se acredita C01 dinámico por su prueba
puntual de equilibrio. Sin blowdown/filling integrado, onda acústica, refinamiento,
volumen variable ni adaptador productivo; todos dependen del gate no aprobado.
No se declara P3 PASS, no se archiva ni iniciaP4.

Tiempo de tests23.983s; preflight más regresiónoffline11.750s. Cero integraciones
acopladas, por tanto no hay runtime de casos sintéticos ni timeout300 que perfilar.
La evidencia nativa conserva SCIENTIFIC_CHANGE_REQUIRED. Revisión independiente
real se adjunta separada; no se usa el stub como prueba de revisión.

Comando ejecutado desde la raíz:
```powershell
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P3 --dependency P2=docs/gasdynamic/p2_accepted_dependency.json
```
Este comando vuelve a reproducir el bloqueo, no continúa P3B ni aceptaP3.
Evidencia completa y referencias hash: preflight/artifacts/preflight.json,
preflight/artifacts/p2-regression/artifacts/closure.json y logs del runner.

Revisión independiente final /root/p3_review confirma el bloqueo,27hashes
intactos,42evaluaciones/6sinrama, signos/energía/especie y evidencia idéntica
al runner. Sin hallazgos adicionales en código preparatorio. Autorrevisión
de alcance/hashes/documentos separada. OpenSpec estrictoP3/P2 PASS.
