# Contrato matemático quasi-1D v1 — P1

Estado: contrato propuesto para implementación posterior, no solver ejecutado.
VERIFICATION ≠ VALIDATION. P0 se acepta mediante recibo separado; sus archivos
congelados no cambian. El dominio público actual 2T es 2500–15000 desde d2932da;
la mención 2500–3500 en la orden P1 describe el estado histórico de P0.

## Sistema cerrado y unidades

SI, x creciente desde inicio a fin del segmento, t en s, A(x)>0 fija en el tiempo.
Estado conservado por longitud **Q=A[ρ,ρu,ρE,ρY]**. La implementación futura
guardará integrales de celda **C_i=∫Q dx**, no valores puntuales de Q.
Unidades de C: kg, kg·m/s, J, kg. Y identifica masa fresca pasiva, sin reacción
ni propiedades dependientes de Y. Residual=1−Y. No equivale a una química.

∂t Q + ∂x G = B, con

G=A[ρu, ρu²+p, u(ρE+p), ρuY], B=[0,p∂xA,0,0].

E=e+u²/2, e=cv T, p=(γ−1)ρe=ρRT, h=e+p/ρ=cp T,
H=E+p/ρ, a=√(γp/ρ), M=u/a.
GEN1: R=287 J/(kg·K), γ=1.35, cv=R/(γ−1)=820 J/(kg·K),
cp=γcv=1107 J/(kg·K). Interfaz de propiedades inmutable por caso con R,γ,
derivados cp,cv y conversión conservado/primitivo; no hooks ejecutables de química.
Tests adimensionales declaran explícitamente R,γ distintos (Sod γ=1.4).
No modifican EOS del baseline 0D. Requiere finitud, ρ>0, e>0, p>0, T>0,
0≤ρY≤ρ en toda etapa aceptada. Valores vacíos, NaN o geometría inválida fallan.

## Fuente geométrica y equilibrio

La fuerza axial de presión de pared es **+p A'**: expansión A'>0 da fuente
positiva. No es pérdida por fricción. La energía no recibe fuente de área
porque la pared es fija. Masa, energía y especie solo cambian por fronteras.

dC_i/dt = G_(i−1/2) − G_(i+1/2) + [0,I_i,0,0],
I_i=∫celda p(x) A'(x) dx. Baseline de primer orden:
I_i=p_i(A_R−A_L). Segundo orden: conservar exactamente el término constante,
I_i=p_i(A_R−A_L)+s_p∫(x−x_i)A' dx. Evaluar la integral de pendiente como
[(x−x_i)A]_L^R−V_i por integración por partes; también es exacta para el área
sinusoidal de T08 con su volumen analítico. No aproximar el término constante
mediante cuadratura que pueda romper el reposo. Centros x_i son
centroides volumétricos ∫xA dx/V_i. Todas las caras comparten exactamente un
área y un flujo; el signo se invierte entre celdas vecinas.

Para u=0 y p uniforme, flujo de momentum=p A_f y la fuente lo cancela
exactamente salvo redondeo, incluso en conos y cambios de pendiente. Para A
constante I=0. No se promete equilibrio exacto de flujo estacionario no uniforme:
T08 mide su error y convergencia. No discretizar p A' con áreas diferentes de
las usadas por los flujos ni añadir p A' a energía. Esquinas de pendiente son
caras de malla; salto de área discontinuo no está admitido en GEN1.

## Geometría

Mapear length/start_diameter/end_diameter existentes de mm a m una sola vez.
Por segmento L>0, d0,d1>0: d(x)=d0+(d1−d0)x/L, A=πd²/4.
Partir segmentos en n=ceil(L/dx_target) celdas iguales axialmente, incluyendo
caras en cada unión. Cilindro: d0=d1. Volumen exacto de frustum:
V=π Δx(dL²+dL dR+dR²)/12. Centro volumétrico por integral polinómica exacta.
Longitudes suman L, V suma volumen de segmentos, sin solapes ni duplicar caras.
Uniones requieren diámetros iguales dentro de 1e−12 m + 1e−12 max(d0,d1);
una discrepancia dentro de ese redondeo usa un único diámetro de cara compartido
(el de salida anterior); fuera de tolerancia rechazar, nunca suavizar un escalón.
La regla geométrica es contractual; ningún JSON ni mesh runtime cambia en P1.
Header/diffuser/belly/baffle/stinger son secuencias axiales, no garganta+volumen.

## Fronteras matemáticas

Usar velocidad normal w=n u, n=−1 izquierda, +1 derecha, normal hacia afuera
del conducto. En régimen subsónico hay una característica acústica saliente
J+=w+2a/(γ−1); entropía K=p/ρ^γ y especie siguen el signo de w.
La condición de frontera produce un estado de cara y un único flujo conservativo.
No imponer simultáneamente p,T,u de cara en una salida subsónica.

* Periódica: emparejar caras y usar exactamente el mismo flujo, orientación global x.
* Pared reflectiva / extremo cerrado: ghost ρ,p,Y iguales y u opuesto; velocidad
  de pared cero. Flujo exacto [0,p_wall A,0,0]; presión de pared obtenida por
  problema de Riemann, no necesariamente p de la celda. Momentum incluye reacción.
* Presión abierta ideal (test acústico): p_b=p0. Para salida subsónica usar
  K,Y interiores, ρ_b=(p0/K)^(1/γ), a_b y w_b=J+−2a_b/(γ−1).
  Para entrada usar K,Y del reservorio de prueba (p0,T0,Y0), mismo J+.
  Si el signo calculado contradice el branch, resolver el branch consistente;
  no promediar composiciones ni imponer u=0. T05 opera cerca de reposo.
* No reflectiva matemática, acústica: imponer perturbación entrante J−=J−base,
  extrapolar J+; combinar w=(J++J−)/2, a=(γ−1)(J+−J−)/4. K,Y interiores
  en salida, de exterior en entrada. Es exacta solo linealmente/localmente;
  no representa radiación real desde una boca de escape.
* Reservorio físico ideal: p0,T0,Y0 son **totales** en entrada, estáticos de la
  cámara en reposo. K0=p0/(p0/(RT0))^γ y h0=cp T0. Para w<0 subsónico,
  resolver J+ interior junto con a²/(γ−1)+w²/2=h0 y K=K0; elegir raíz física
  −a<w≤0, sin imponer adicionalmente p=p0. Para w>0 subsónico usar p_b=p0,
  K,Y interiores y J+; energía transportada H_b, no h0 del receptor.
  Choking de entrada: si la solución demanda |w|≥a, usar garganta ideal sónica
  w=−a, T=T0*2/(γ+1), K0,Y0; flujo no depende de característica que ya no sale.
  Supersónica saliente: extrapolar todo, ignorar p receptor. Supersónica entrante
  no se deduce de dos datos de reservorio: exige estado completo externo o error
  explícito unsupported_supersonic_inlet. No extrapolar automáticamente.

Presión abierta ideal y no reflectiva son BC diferentes: reflexión de presión
−1 frente a 0 en acústica. Pared: +1. Salida real a atmósfera requiere radiación,
pérdidas y corrección de extremo futuras: GEN1 no afirma que estén modeladas.

## Interfaz futura 0D↔1D (P3, no implementada)

El 0D suministra V,m,U_interna,m_fresca; derivar ρ,p,T,Y, velocidad de reservorio
cero. Entrada al conducto usa condición de reservorio anterior; retorno al 0D
usa entalpía total y especie del donante 1D. Contrato de puerto:
estado de cámara, estado interior 1D, área de puerto efectiva, orientación y dt;
salida: flujo másico, axial de momentum, energía total, fresca, p de cara,
velocidad y diagnóstico de régimen. A_puerto=A_cara en P2; aperturas/áreas
distintas y coeficientes de pérdidas solo se definirán antes de P3, sin inventar Cd.

Definir F_out hacia afuera del conducto. Mismo incremento integrado en tiempo:
Δm_0D=+∫F_mass,out dt, ΔU_0D=+∫F_energy,out dt,
Δm_f,0D=+∫F_fresh,out dt; conducto recibe negativos. Donante por signo de flujo,
Y_interface nunca del receptor. Movimiento del pistón aporta −p dV en el ledger
0D separado. No sumar otra vez trabajo de flujo p u A: ya está en H.
El 0D no conserva momentum axial: reacción/impulso del puerto se registra en
ledger de pared/cámara. Sin afirmar conservación de momentum de gas aislado.
Usar pasos sincronizados y un único flujo por etapa; subcycling futuro necesita
acumular exactamente ese flujo, nunca dos cálculos independientes. Agotamiento
de masa/especie/energía de cualquier lado rechaza la etapa conjunta.

## Alcance y arquitectura futura

Euler ideal inviscido con trazador, ondas, contactos, shocks y backflow; conductos
de admisión, transferencia y escape, cámaras 0D y reservorios. Sin CFD 2D/3D,
química, emisiones, turbo, multicilindro, estructura, powervalve, fricción compleja,
calor avanzado, combustión predictiva ni optimización. Fuentes futuras de calor
y pérdidas tendrán términos separados en ledger; no se diseñan aquí.
Namespace conceptual motorsim/gas1d/: state, geometry, eos, flux, riemann, mesh,
boundary, solver, diagnostics. No se crean módulos runtime. Ruta 0D permanece
separada de la futura experimental 1D; P2 no reemplaza ni acopla el baseline.
