# 1D_CONTRACT_V1_R5 — T11 segundo orden

Adoptado tras nueve finales y revisión independiente científica PASS.
No constituye aceptación humana de P2. Evidencia: results/p1-r5e-20260918.
Los contratos v1/R2/R3/R4 permanecen intactos.

## T11 — Sensibilidad CFL por método (R5)

FIRST_ORDER+Forward Euler conserva íntegro el criterio 1D_CONTRACT_V1_R4.
La extensión operativa de R4 a MUSCL documentada en P2 se sustituye
exclusivamente por la siguiente rama SECOND_ORDER/MUSCL_SSPRK2.

T02 N400 con CFL0.2/0.4/0.6: gates padre y diferencias E1 rho/p/u<=0.015
frente CFL0.2 intactos. T03 N800: diferencia de velocidad<=0.005a0 intacta.
Para MUSCL/minmod+SSP-RK2: completar T03 N400/800/1600 con CFL0.2/0.4/0.6,
mismas IC, BC, EOS y t_final; admisibilidad estricta sin clipping, CFL de
cada etapa dentro de su límite y cuatro balances de paso/etapa<=1e-10.
En N800 y N1600 se conservan todos los gates T03 originales:
A/A_ref en [0.65,1.05], E1p<=0.025, E2p<=0.08, error velocidad<=0.01a0.
N400 conserva su carácter diagnóstico de exactitud.

A(N,C)=max_i(p_i(t_final)-p0); A_ref(N) es el pico de primitivas derivadas de
integrales conservadas de referencia acústica T03, no el pico continuo.
E_A(N,C)=abs(A-A_ref)/(1e-4*p0). Exigir E_A400>E_A800>E_A1600 para CADA CFL.
S(N;a,b)=abs(A(N,a)-A(N,b))/(1e-4*p0).
Para CADA pareja (.2,.4),(.4,.6),(.2,.6), exigir S1600<S400.
Se retira SOLO la exigencia de S400>S800>S1600 en ambas transiciones
para segundo orden; N800 se conserva y ambas transiciones se registran siempre.
No se agrega límite absoluto de sensibilidad ni se ajusta una tolerancia a datos.
Registrar errores L1/L2 de presión y fase/velocidad por CFL como corroboración
científica del perfil, además del pico; cualquier deterioro sistemático
contradictorio requiere revisión científica, no aprobación por amplitud aislada.
Tres mallas y este benchmark no prueban convergencia asintótica universal.
Todos los demás criterios, T01-T10/T12, T02/T06 y física permanecen intactos.
