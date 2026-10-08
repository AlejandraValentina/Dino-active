# P1-R4 — protocolo previo a ejecución

## Métrica exacta y origen
Fuente congelada:2143a60; implementación numérica b353e90. T11 repite T03:
Euler quasi-1D, área0,01m² constante, L=1m, N800, gamma1,35, R287,
p0=100000Pa,T0=300K,Y0=0,3; pulso gaussiano derecho centro0,25m,
anchura0,04m, amplitud prescrita1e-4*p0=10Pa; BC no reflectivas BASE explícita.
Tiempo final0,45L/a0. Inicial y referencia son integrales conservadas por celda;
p se obtiene de las primitivas de esos promedios conservados.

A(N,C)=max_i[p_i(t_final)-p0], en Pa. No sensor, promedio espacial, integral,
FFT ni amplitud ajustada. Valores históricos A(800,0,6)=8,832393583405064Pa
 y A(800,0,2)=7,99875531278667Pa. Métrica S=abs(Aa-Ab)/10;
denominador10Pa es el parámetro continuo inicial, no el máximo inicial discreto
ni el pico numérico del run de referencia. S=.0833638270618394>0,08.
Diferencia absoluta=.833638270618394Pa. No reinterpretar esta métrica.

0,08 aparece originalmente en5b6b62f, docs/gasdynamic/1d_verification_plan_v1.md,
T11, y manifestv1. La orden original P1 pidió definir ensayo CFL pero no dio0,08.
No hay derivación ni fuente que produzca ese número en documentos/revisión
conservados: tolerancia práctica contractual, no constante física ni boundteórico.
T11 se denomina sensibilidad, no estabilidad; su fallo histórico es válido.
Sod E1<=.015 y diferencia de velocidad<=.005a0 son gates distintos y se conservan.

## Implementación congelada
No editar motorsim/, ni contratos v1/R2/R3, producción0D o evidencia anterior.
Adaptador dev_orchestrator llama definition/solve/measure existentes; cambia
únicamente parámetros de estudio N/CFL fuera del código productivo. Sin monkeypatch.
Manifest previo de hashes de todos los módulosgas1d y documentos normativos.

## Matriz fijada y coste
Primero repetir exactamente T03N800 CFL0,2/0,4/0,6 y comparar arrays/ledger,
contadores y métricas con p2a-attempt-2 deR3 (excluir únicamente wall_seconds).
Estas tres ejecuciones son también la fila contractual del estudio; no duplicarlas.
Luego N400 y1600 con CFL0,1/0,2/0,4/0,6 y N800CFL0,1:12 runs nuevos en total.
Mismo tiempo físico, IC/BC, EOS, método, source, referencia y métricas.
CFL0,1 es diagnóstico temporal del MISMO esquema espacial, no verdad exacta deEuler:
menor paso puede incrementar difusión neta respecto de la solución continua.
Comparar cadaCFL con0,1 de su misma malla y las parejas.2/.4,.4/.6,.2/.6.

N3200 opcional omitido: con24s paraN800CFL.2 y costeO(N²), cuatroCFL
adicionales requerirían~1470s, frente~483s para la matriz principal.
Límite porcaso320s, conjunto900s de adaptador (timeout fase1020s); sin retries.
Registrar fallos sin modificar solver y clasificar infraestructura si timeout.

Porrun: A, diferenciaabs/10, erroresparentT03, amplitudanalítica discreta,
steps, dtmin/max (ledger), CFLrealm ax, residual4componentes, rho/p/Tmínimos,
Ymin/max, HLLC/HLLE, rechazos, runtime. Arrays/ledger/hash completos.
Estabilidad=admisibilidad/conservación<=1e-10/completitud; sensibilidad=comparación
A. Parentgates aN400 se registran como diagnóstico, no se impone allí elgateN800.
No convertir un parenterror grueso en inestabilidad.

## Hipótesis y referencia independiente
Para rama acústica lineal upwind+FE, Taylor da
q_t+a0*q_x=nu_num*q_xx+O(dx²), nu_num=a0*dx*(1-C)/2.
La gaussiana tiene pico aproximado10/sqrt(1+4*nu_num*t/0,04²).
Predicción sin ajustar coeficientes: mayorCFL amortigua menos; diferencias
entreCFL decaen con dx. No es cota rigurosa de HLLC no lineal ni fija tolerancia.
Fuente primaria: LeVeque, notas ecuación modificada,
https://faculty.washington.edu/rjl/classes/hyperbolic2013/am574w2011/am574lecture6.pdf
Tres mallas pueden respaldar tendencia, no demostrar un límite asintótico.

## Decisión posterior
Sin umbral nuevo previo a evidencia. Revisar estabilidad, errores frente solución
acústica independiente, disminución sistemática de sensibilidad y comportamiento.6.
Si no converge: UNRESOLVED o CFL06_NOT_ACCREDITED; no cambiar contrato.
Si casoA respaldado, diseñar gate con estabilidad, ledger original, refinamiento
y límite cuantitativo de exactitud (mantener al menos gatesT03 originales).
No redondear.08 a.09/.10 ni usar predicción aproximada como cota rigurosa.
Revisión independiente read-only de métrica, datos y eventual criterio antes de
adopciónR4. No aprobarP2A todavía. TrasR4PASS ejecutar soloT11 primero;
regresiones necesarias después. P2B/P3 no se usan para rescatar esteestudio.

## Propuesta contractual posterior al estudio, pendiente de revisión
Estudio completo509,375s:12/12 estables y conservativos. S(.2,.6) disminuye
.113607252676→.083363827062→.052871641950. Las otrasdos parejas también
disminuyen; error del pico hacia referencia independiente decrece en cadaCFL.
CFL.6 conserva la misma tendencia, sin evidencia de límite distinto o blow-up.
CasoA respaldado en estas tres mallas; no prueba asintótica general.

Propuesta R4 SOLO first-order, sin editarR3:
1. N400/800/1600, C=.2,.4,.6, mismos IC/BC/t_final; todos completados,
   admisibles sinclipping y cuatroledgers<=1e-10.
2. A=max_i(p_i-p0), S(N;a,b)=abs(Aa-Ab)/10Pa intactos.
   Exigir S(400;a,b)>S(800;a,b)>S(1600;a,b) para cada pareja
   (.2,.4),(.4,.6),(.2,.6), ambastransiciones, sin escoger solo la mejorpareja.
3. E_A(N,C)=abs(A(N,C)-A_ref(N))/10Pa, conA_ref del pico de primitivas
   de integrales conservadas de la solución acústicaanalítica originalT03.
   Exigir E_A(400,C)>E_A(800,C)>E_A(1600,C) para cadaCFL productivo.
4. Conservar todos los gatespadreT03 aN800 y exigirlos también aN1600:
   A/A_ref en[.65,1.05], E1p<=.025,E2p<=.08, velocidaderror<=.01a0,
   admisibilidad yledger. Estos son los límites cuantitativos delobservable,
   preceden al estudio y se contrastan con referenciaindependiente, no con
   otra solución numérica que pueda compartir sesgo. N400errorL1.1/.2
   permanece documentado, no requerido allí porcontratooriginal.
5. Mantener T11SodN400 conE1diferenciasrho/u/p<=.015 y todosgatespadre;
   mantener comparaciónvelocidadT03N800<=.005a0 frenteCFL.2.
6. CFL.1 diagnóstico solamente, no nuevo requisito deproducción.
7. Registrar sensibilidad.08 histórica como diagnóstico que continúaFAIL.
   Esta revisión RETIRA la garantía <=8% enN800, no es criterio equivalente.
   No reemplaza.08 por.09/.10. Añade condicionesdemalla/exactitud y se limita
   al casoacústico y método contratados; no acreditar otrasanchuras/fronteras.
8. MUSCL/SSP-RK2 queda fuera de esta revisión; conservaT11original hasta
   definición posterior. No implementarP2B duranteP1-R4 ni comenzarP3.

Si revisor aprueba, adoptar1D_CONTRACT_V1_R4 y registrarT11primero:
repetir seisruns contractuales (tresSod+tresT03) con fuenteintacta y aplicar
criterioR4 usando también los arrays400/1600conhash delestudio. Después,
reevaluarT01–T12 desde52arraysR3conhash y seisrunsnuevos, conservando deltas
originales y sin atribuir52integracionesnuevas. El solver/otrosgates son idénticos;
esta regresión offline es suficiente solo si hashes y comparacionesconfirmanlo.
P2A numéricamenteverificado no es aceptaciónhumana deP2; human gate pendiente.
