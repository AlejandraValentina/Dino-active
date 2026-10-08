# 1D_CONTRACT_V1_R4 — sensibilidad CFL first-order

Adoptado tras estudio y revisión independiente, antes de verificar T11 bajo R4.
Recibo: results/p1-r4-cfl-20260918/reviewed-evidence.json (P1_R4_PASS_T11_REFINED_CONTRACT).
P2A no aprobado por esta adopción. Contratos v1/R2/R3 intactos.

## T11 — Sensibilidad CFL (R4 first-order)

T02 N400 con CFL0.2/0.4/0.6: todos los gates padre y diferencias E1 rho/p/u<=0.015
frente CFL0.2, intactos. T03 N800: comparación velocidad<=0.005a0 intacta.
Para FIRST_ORDER+Forward Euler, sustituir exclusivamente el límite comparativo
amplitud<=0.08 por refinamiento N400/800/1600 para CFL0.2/0.4/0.6.
Mismas IC/BC/t_final originales; completar todos los casos, admisibilidad estricta
sin clipping y cuatro ledgers<=1e-10. A(N,C)=max_i(p_i(t_final)-p0), en Pa;
S(N;a,b)=abs(A(N,a)-A(N,b))/(1e-4*p0). Exigir S400>S800>S1600 para las
TRES parejas(.2,.4),(.4,.6),(.2,.6), en ambas transiciones.
E_A=abs(A-A_ref(N))/(1e-4*p0), con A_ref pico de primitivas de integrales
conservadas de referencia acústica T03 original. Exigir E_A400>E_A800>E_A1600
para cada CFL productivo. A N800 y N1600 todos los gates T03 originales:
pico/analítica[0.65,1.05], E1p<=0.025,E2p<=0.08,error velocidad<=0.01a0 y ledger.
N400 es diagnóstico de exactitud; CFL0.1 diagnóstico temporal, no producción.
Registrar diferencia absoluta Pa y normalizada, dt/pasos/CFL real, extrema,
rechazos/fallbacks, conservación, coste y errores. Registrar0.08 histórico
como diagnóstico: R4 RETIRA su garantía en N800, no afirma equivalencia.
Solo este caso/método; tres mallas no prueban límite asintótico universal.
MUSCL/SSP-RK2 no cambia en R4 y conserva T11 original. Ver 1d_cfl_sensitivity_v1_r4.md.

## Fundamento y alcance de la decisión
0,08 era una tolerancia práctica desde5b6b62f, sin derivación localizada.
El fallo histórico0,08336382706 es válido bajo R3; no se reescribe su evidencia.
El esquema acústico lineal upwind+FE da nu_num=a0*dx*(1-C)/2 mediante Taylor;
para gaussiana, Aaprox=10/sqrt(1+4*nu_num*t/0,04²). Es una aproximación de
pequeña amplitud, no una cota rigurosa HLLC. Fuente primaria:
https://faculty.washington.edu/rjl/classes/hyperbolic2013/am574w2011/am574lecture6.pdf

Estudio completo12runs: N400/800/1600 xCFL.1/.2/.4/.6. Sin ajustar coeficientes,
la predicción del pico difiere como máximo0,0067071Pa. Las tres parejas de CFL
reducen diferencia al refinar; el error de cada CFL frente analítica también decrece.
S(.2,.6)=.113607252676,.083363827062,.052871641950. No blow-up, cero HLLE,
peor residuo1,04282e-14. CFL.6 no muestra solución límite distinta en los datos.

Los límites cuantitativos T03 elegidos previamente se mantienen: protegen
exactitud absoluta respecto de una referencia independiente, además de exigir
convergencia de sensibilidad. No se elige una nueva tolerancia para que0,08336
pase. Se RETIRA la garantía del8% y se añade evidencia de refinamiento y
exactitud; el nuevo criterio no es equivalente al anterior ni se presenta como
una mera corrección tipográfica. No se afirma que T11 solo midiera estabilidad.

Caso A respaldado en el dominio ensayado; no demostración de límite asintótico.
CFL.1 aproxima mejor el tiempo del esquema semidiscreto, pero puede ser más
amortiguado y menos próximo a Euler a malla fija. Se conserva como diagnóstico.
N400.1/.2 fallan E1 padre T03, documentados sin llamarlos inestables; los gates
padre se exigen a N800 contractual y N1600, no se cambian para aprobar N400.
Sin cambio de HLLC/HLLE/FE/EOS/CFL/source/BC/especie/positividad ni baseline0D.
