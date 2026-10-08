# Contrato numérico v1 — decisiones P1

Este documento selecciona métodos; no acredita implementación. Las tolerancias
de tests son gates propuestos antes de P2, no resultados ni calibraciones.

## Secuencia obligatoria

P2a: FV de primer orden, estados constantes por celda, HLLC y Forward Euler.
P2b solo después de aprobar T01–T12 de P2a: MUSCL en primitivas ρ,u,p,Y,
minmod de gradientes en malla no uniforme, SSP-RK2 (Heun):
C1=Cn+dt L(Cn); Cn+1=1/2 Cn+1/2[C1+dt L(C1)]. Fuente y BC en cada etapa.
SSP-RK3 no se selecciona inicialmente: coste adicional sin necesidad contractual.
No trasladar RK4 0D. Ambas rutas permanecen comparables; P2 no se autoriza aquí.

## HLLC, especie y robustez

Trabajar con q=Q/A y F=G/A en cada cara común. HLLC restaura la onda de
contacto ausente en HLL, con coste menor que solución exacta iterativa [1,2].
Para k=L,R: H_k=(ρE+p)/ρ. Promedios Roe de u,H con pesos √ρ;
a_tilde²=(γ−1)(H_tilde−u_tilde²/2).
S_L=min(u_L−a_L,u_R−a_R,u_tilde−a_tilde),
S_R=max(u_L+a_L,u_R+a_R,u_tilde+a_tilde).
S_M=[p_R−p_L+ρ_L u_L(S_L−u_L)−ρ_R u_R(S_R−u_R)]/
[ρ_L(S_L−u_L)−ρ_R(S_R−u_R)].
ρ*_k=ρ_k(S_k−u_k)/(S_k−S_M), u*=S_M,
p*_k=p_k+ρ_k(S_k−u_k)(S_M−u_k),
E*_k=E_k+(S_M−u_k)[S_M+p_k/(ρ_k(S_k−u_k))], (ρY)*=ρ*Y_k.
F*=F_k+S_k(q*_k−q_k). Elegir F_L si S_L≥0; F*_L si S_L<0≤S_M;
F*_R si S_M<0<S_R; F_R si S_R≤0. Multiplicar una vez por A_f.
Transporte de especie usa el mismo flujo de masa y composición de la región
donante HLLC; en degeneraciones tomar rama idéntica para todos los componentes.

HLLC no se presupone positivo universalmente. Si denominador es cero/no finito,
si estrellas tienen ρ≤0, e≤0, p*≤0, Y fuera de [0,1], o velocidades mal ordenadas,
usar **HLLE para el vector completo en esa cara** con las mismas cotas S_L,S_R
(Einfeldt [3]); F_HLL=(S_R F_L−S_L F_R+S_L S_R(q_R−q_L))/(S_R−S_L).
Sin reemplazo exclusivo de especie. Registrar cara, razón, estados y contador.
Si no se obtienen cotas físicas finitas, fallar explícitamente. LLF/Rusanov queda
comparador diagnóstico, no fallback adicional. Entropía: cotas de rarefacción
incluyen ambos lados; test de expansión fuerte T12 obligatorio.

MUSCL: s=minmod((v_i−v_left)/(x_i−x_left),(v_right−v_i)/(x_right−x_i)).
minmod=0 si signos difieren; en otro caso pendiente de menor módulo. Extrapolar
a cara desde centroide. Si alguna cara reconstruida viola ρ>0,p>0,0≤Y≤1,
anular **todas las pendientes de esa celda**, sin cambiar promedio conservado.
Es downgrade local explícito con contador. Nunca recortar Y, ρ, p o energía.

Tras cada etapa, comprobar conservados e internas. Etapa inválida: deshacerla
completa (incluidos ledgers), reducir dt/2 y repetir desde el estado previo;
máximo 12 reducciones por paso. No son reparaciones de ciencia/orquestador.
Si alcanza mínimo o agota reducciones: failure con estado anterior intacto.
Este mecanismo detecta fallos; no es prueba matemática de positividad global
en área variable. T12 y los ledgers son gate: si no pasan, no relajar tolerancias,
declarar SCIENTIFIC_CHANGE_REQUIRED antes de incorporar otro algoritmo.

Lección del limiter 0D rechazado: boundedness sola no basta; no reparar un
componente después de evaluar RHS ni destruir balances/orden/reproducibilidad.
Cada intervención debe conservar el flujo compartido completo y ser observable.
No se importa ni adapta el candidato rechazado de tools/.

## CFL, tiempo y precisión

float64, sin GPU, sin azar; orden de reducción fijo. CFL inicial **0.4**;
ensayos **0.2,0.4,0.6**, todos sujetos a positividad y balance, sin parámetro UI.
s_f=max(|S_L|,|S_R|) incluyendo BC; usar el mayor límite en todas las etapas.
dt=CFL min_i[Δx_i/(|u_i|+a_i), 2V_i/(A_L s_L+A_R s_R)],
además truncar al tiempo final y eventos prescritos. El segundo término recupera
Δx/s en tubo uniforme y limita celdas de área variable. dt global, no local.
Recomprobar CFL en etapas SSP; si excede el valor pedido, rechazar y reducir.
No se garantiza positividad solo con la fórmula CFL.
Mínimo dt=1e−12 * t_unit; t_unit=1 s en SI y 1 en tests adimensionales.
Último resto menor al mínimo solo termina si |t_final−t|≤16 eps max(t_unit,|t_final|);
de otro modo falla dt_below_min. No avanzar sin modificar t representable.
Error explícito ante NaN, estados inválidos, cotas imposibles o agotamiento.

## Ledger y diagnóstico obligatorios P2

L_k(t)=sum_i C_i,k(t)−sum_i C_i,k(0)+∫(G_R,k−G_L,k)dt−∫sum_i B_i,k dt.
Cuadratura temporal idéntica a actualización (FE dt; RK2 pesos 1/2,1/2).
Guardar por separado inventarios, entradas/salidas, fuente geométrica y residuo.
Escala D_k=max(sum|C_i,k(0)|,∫(|G_L,k|+|G_R,k|)dt,
∫sum|B_i,k|dt, Qscale_k). Qscale=M0 para masa/especie, M0*a0 para momentum,
E0 para energía. Gate |L_k|/D_k≤1e−10 en cada test. Momentum incluye pared
y fuente: no exigir que el inventario axial permanezca constante en un cono.
En periodicidad emparejar flujos exactamente. En cerrado masa/energía/especie
no intercambian; solo impulso. No usar residuo dividido por cambio neto cero.

Exponer campos ρ,u,p,T,Y,M; flujos por cara de las cuatro componentes;
dt, CFL máximo, intentos rechazados, razón, mínimos ρ/p/T, min/max Y, máximo |M|,
fallbacks HLLE/downgrades MUSCL y balances. Serializar entradas, malla, perfil,
hash fuente y arrays deterministas; excluir tiempos del hash científico.
Objetivo de observación: N=100/200/400/800, tiempo por test y pasos/celda;
O(N) por etapa y O(N²) a tiempo fijo con CFL, memoria O(N). Presupuesto de
seguridad futuro 120 s por subcaso, timeout es infraestructura, no PASS numérico.
No hay promesa de tiempo de motor completo ni optimización prematura.

## Decision log

| ID | Selección | Alternativas | Motivo | Riesgo | Diferido |
|---|---|---|---|---|---|
| D1 | Q=Aq; integrales C | q con fuente dividida | Flujos compartidos y ledger simple | Confundir promedio y punto | Ninguno para P2 |
| D2 | EOS constante R287/γ1.35 encapsulada | Propiedades variables | Compatibilidad 0D y tests analíticos | Gas quemado aproximado | cp(T), química |
| D3 | HLLC con guardia HLLE | HLL, LLF, exacto | Contactos y coste; fallback conservativo | Vacío/rarefacción fuerte | Otro flux requiere decisión científica |
| D4 | FE luego SSP-RK2 | SSP-RK3, RK4 | Baseline auditable y convexidad SSP [4] | SSP no garantiza EOS positiva por sí sola | RK3 |
| D5 | Constante luego MUSCL primitivas | Características, WENO | Progresión separable | Difusión/shocks | WENO |
| D6 | minmod | MC, van Leer | Más disipativo, simple y robusto | Amortigua ondas | Cambiar limiter tras comparación |
| D7 | CFL0.4; ensayos0.2/0.6 | Paso fijo | Velocidades locales y volumen | Source/BC restringen estabilidad | Optimización CFL |
| D8 | Frustum exacto y caras en uniones | Área constante escalonada | Conserva volumen/geometría | Pendiente discontinua | Escalones de área |
| D9 | ρY y flux completo compartido | Clipping, limiter 0D | Conservación y donante coherente | Positividad no universal | Algoritmo alternativo si falla gate |
| D10 | Riemann/características por régimen | Ghost fijo en todo régimen | No sobreimponer datos | Choking/supersónico entrante | Radiación real |
| D11 | Flux integrado único 0D↔1D | Dos fluxes independientes | Cancelación exacta masa/energía/especie | Apertura de puerto y subcycling | P3: Cd, área de puerto y sincronización motor |

## Fuentes técnicas (consultadas 17/09/2026)

[1] E. F. Toro, *Riemann Solvers and Numerical Methods for Fluid Dynamics*,
3rd ed., Springer, 2009. https://doi.org/10.1007/b79761

[2] E. F. Toro, M. Spruce, W. Speares, “Restoration of the contact surface in
the HLL-Riemann solver”, Shock Waves 4, 25–34 (1994).
https://doi.org/10.1007/BF01414629

[3] B. Einfeldt, C. D. Munz, P. L. Roe, B. Sjögreen, “On Godunov-type methods
near low densities”, J. Comput. Phys. 92(2), 273–295 (1991).
https://doi.org/10.1016/0021-9991(91)90211-3

[4] S. Gottlieb, C.-W. Shu, E. Tadmor, “Strong Stability-Preserving High-Order
Time Discretization Methods”, SIAM Review 43(1), 89–112 (2001).
https://doi.org/10.1137/S003614450036757X
Texto autores: https://www.math.umd.edu/~tadmor/pub/linear-stability/Gottlieb-Shu-Tadmor.SIREV-01.pdf

[5] R. J. LeVeque, *Finite Volume Methods for Hyperbolic Problems*, Cambridge
University Press (2002), ISBN 9780521009249.
https://www.clawpack.org/fvmhp_materials/

[6] D. I. Ketcheson, R. J. LeVeque, M. J. del Razo, *Riemann Problems and
Jupyter Solutions*, SIAM (2020), capítulo Euler y soluciones exactas.
https://www.clawpack.org/riemann_book/html/Euler.html

Estos textos fundamentan FV/Riemann/SSP; los umbrales y decisiones GEN1 son
propuestas de ingeniería de P1, no tolerancias atribuidas a los autores.
No se usan calibraciones, algoritmos propietarios ni datos de EngMod2T.
