# Plan de verificación v1 — T01–T12

Todos son requisitos futuros de P2, **no pruebas físicas ejecutadas en P1**.
P1 comprueba completitud, consistencia algebraica y referencias del contrato.
Cada subcaso es independiente. FE/HLLC primero; MUSCL/SSP-RK2 repite todos.
Salvo indicación: SI, γ=1.35, R=287, L=1 m, A=0.01 m², N=400, CFL=0.4,
p0=100000 Pa, T0=300 K, ρ0=p0/(RT0), a0=√(γRT0), Y0=0.3.
Admisibilidad estricta (sin clipping) en todas las etapas aceptadas y ledger
normalizado ≤1e−10 para las cuatro componentes en **todos** los subcasos.
Toda falla, timeout, referencia ausente o denominador inválido impide PASS.

## Métricas comunes y referencias

Construir primero integrales conservadas de referencia ∫A[ρ,ρu,ρE,ρY]dx,
dividir por V_i y derivar primitivas de esos promedios conservados, nunca
promediar Y directamente. En todos los casos (también T02/T06/T09),
Yref=(ρY)ref/ρref. Comparar con igual conversión de la solución numérica,
no con una muestra puntual ni un promedio independiente de primitivas.
E1=sum(V_i |v_i−vref_i|)/(sum V_i * scale),
E2=√[sum(V_i (v_i−vref_i)²)/sum V_i]/scale;
Einf=max|v_i−vref_i|/scale. Escalas por caso positivas antes del ensayo.
Reducción de error al refinar: log2(E_N/E_2N); si ambos errores <1e−12,
clasificar exacto a redondeo, no dividir cero. La solución exacta de Riemann
se calculará independientemente del solver aproximado, con raíz de presión
de residuo relativo ≤1e−12 y 200 iteraciones máximas, o referencia falta.
Integrar solución exacta por piezas (ondas conocidas), cuadratura hasta error
relativo ≤1e−10. No copiar soluciones HLLC como expected. Versionar referencia.

## T01 — Preservación uniforme

Propósito: comprobar flux y conversión EOS sin geometría. IC ρ0,p0,Y0 uniformes,
u=0 y u=0.2a0 (dos subcasos); BC periódicas, dominio común, N=100,
t_final=L/a0. Referencia: misma IC. E∞ de ρ/ρ0,p/p0,T/T0,Y (scale1),
u/a0 ≤1e−12. Inventarios y ledgers comunes. Área constante explícita.

## T02 — Sod

Adimensional: γ=1.4,R=1,A=1,x∈[0,1],discontinuidad x=0.5,N=400,t=0.2.
IC izquierda (ρ,u,p,Y)=(1,0,1,1); derecha=(0.125,0,0.1,0).
BC estados exteriores iniciales fijos (ondas no llegan antes del final).
Referencia exacta Euler de Toro/[6], no γ1.35 por accidente.
Para ρ,p,u escalas1: E1≤0.03, E2≤0.08 para primer orden; MUSCL no peor
E1 que primer orden +1e−10. Shock y contacto: localizarlos por máximo gradiente
de p y Y respectivamente, restringido a ±0.05 alrededor de posición exacta;
error de posición ≤2Δx. Rarefacción: E∞≤0.05 excluyendo 3Δx de sus bordes y
del contacto/shock; E∞ global se registra, no se exige orden alto en shocks.
El ledger incluye impulso debido a presión desigual de extremos.

## T03 — Propagación acústica

Propósito: velocidad/amortiguación lineal. IC gaussiana derecha g=exp(−((x−0.25)/0.04)²),
δp=1e−4 p0 g, ρ=ρ0+δp/a0², u=δp/(ρ0 a0), p=p0+δp, Y=Y0.
BC características no reflectivas al estado base. Dominio común N=800,
t_final=0.45L/a0. Referencia p'=1e−4p0 g(x−a0t), errores O(amplitud²)
no se confunden con error numérico. Centro de pulso = ∫x|p'|dx/∫|p'|dx en
ventana ±0.15L alrededor del centro esperado; velocidad (centro_final−centro_inicial)/t.
Error velocidad ≤1%; amplitud final/analítica entre0.65 y1.05;
E1 presión con scale=1e−4p0 ≤0.025, E2≤0.08. Registrar amortiguación.

## T04 — Reflexión cerrada

IC acústica T03 con centro0.3L y anchura0.04L, N=800. Izquierda no reflectiva,
derecha pared. t_final=1.15L/a0. Sensor x_s=0.7L, interpolación lineal de p
entre centros. Muestrear al menos cada0.001L/a0 (truncar paso a esos eventos).
Incidente ventana [0.30,0.50]L/a0, reflejada [0.90,1.10]L/a0: no se solapan.
I=max p' incidente; R=p' reflejada de mayor módulo con signo.
Referencia acústica R/I=+1, regreso al sensor t=1.0L/a0.
Gate I≥0.5*1e−4p0 (si no, señal inválida); usar denominador max(|I|,1e−8p0),
|R/I−1|≤0.30 primer orden, ≤0.15 MUSCL; tiempo de pico error ≤0.02L/a0.
Ledger cerrado por derecha, no exigir momentum constante.

## T05 — Reflexión abierta ideal

Mismas IC/dominio/sensor/ventanas/t_final/métricas de T04, sustituyendo derecha
por presión abierta p=p0, composición exterior Y0,T0. Referencia R/I=−1.
|R/I+1|≤0.30 primer orden, ≤0.15 MUSCL, R<0, tiempo error≤0.02L/a0;
misma cota de señal incidente y denominador. Referencia ideal acústica, no una
boca de escape real ni BC no reflectiva. Ledger incluye flujos del extremo abierto.

## T06 — Contacto y especie

x∈[0,1],A constante,N=400,p=p0,u=0.2a0; BC periódicas.
IC: ρ=2ρ0,Y=1 en[0.2,0.4], ρ=ρ0,Y=0 fuera; T=p/(ρR).
t_final=0.5L/u. Referencia traslación periódica exacta conservativa del contacto.
E1 ρ (scale2ρ0)≤0.04 y E1 Y (scale1)≤0.06; presión relativa y u/a0 E∞≤1e−10;
0≤Y≤1 estrictos, ledger fresca≤1e−10. MUSCL E1 no peor que primer orden.
No compensar un error fresco con residual negativo.

## T07 — Conservación en tubo constante

Tres subcasos con dominio común,N=200,t_final=0.5L/a0:
(a) periódica con IC T06; (b) dos paredes con IC T03;
(c) abiertos con estado uniforme u=0.2a0 y BC entrada/salida características
consistentes con ese estado (p_total=p0*(1+(γ−1)M²/2)^(γ/(γ−1)),
T_total=T0*(1+(γ−1)M²/2), receptor estático p0).
Referencia integral: identidades ledger, residual de cada componente≤1e−10.
En(b) masa/energía/fresca constantes; momentum incluye impulso de pared.
En(c) no exigir inventarios constantes como sustituto del ledger de flujos.

## T08 — Fuente de área / nozzle

Geometrías x∈[0,1],N=100,200,400: A=0.01 constante;
A=0.01[1+0.2 sin²(πx)] suave (integrales analíticas);
frustum d=0.1+0.02x (A=πd²/4, volumen exacto).
Subcaso reposo: IC p0,T0,Y0,u0=0, paredes,t_final=L/a0.
Referencia equilibrio: E∞ p/p0,ρ/ρ0,u/a0 ≤1e−12 para todas las geometrías.
Subcaso flujo isentrópico: p_total=100000,T_total=300,Y=Y0, M(0)=0.2;
determinar A* por relación A/A*=(1/M)[2/(γ+1)(1+(γ−1)M²/2)]^((γ+1)/(2(γ−1))).
Elegir raíz subsónica continua en cada x; p,T,ρ,u de leyes isentrópicas.
IC promedios exactos; BC p_total/T_total entrada y p_salida exacta,
t_final=L/a0. Referencia estacionaria analítica sin pérdidas ni shock.
E1 p/p_total,ρ/ρ_total,u/a0≤0.01 en N400, errores no aumentan al duplicar N
(tolerancia absoluta1e−12); ledger≤1e−10 incluyendo ∫p A'.
No exigir equilibrio exacto en flujo variable ni interpretar difusión como pérdida física.

## T09 — Backflow

Propósito: donante correcto al invertir flujo. T06 duplicado con u=±0.2a0,
BC periódicas, N400,t_final=0.5L/|u|. Referencias traslaciones exactas opuestas;
mismos criterios T06. Subcasos abiertos independientes u=±0.2a0,ρ0,p0,Y=0.2
en dominio, reservorio entrante Y=0.8 en extremo correspondiente, receptor p0,
reservorio con totales consistentes con el estado uniforme (T07c).
t_final=0.25L/|u|; referencia especie escalón advectado desde entrada:
E1 Y≤0.04, presión y u constantes E∞≤1e−10, flujo de fresca en entrada
igual al másico*0.8 con error absoluto≤1e−12 max(ρ0 a0 A,|flux_mass|).
Verificar signos opuestos e intercambio de donante, sin mezclar estado receptor.

## T10 — Refinamiento

IC suave periódica: ρ=ρ0[1+0.1sin(2πx/L)],p=p0,u=0.2a0,
Y=0.5+0.2sin(2πx/L); dominio común,N=100,200,400,800,
t_final=L/u, referencia traslación periódica exacta de ρ y ρY.
Calcular Yref=(ρY)ref/ρref con promedios conservados, no promedio Y inconsistente.
E1 de ρ/ρ0 y fresca/ρ0: orden observado≥0.7 en cada pareja para FE;
≥1.5 en parejas200/400 y400/800 para MUSCL. No aplicar a Sod.
Ledger y boundedness obligatorios. Registrar coste, celdas y pasos.

## T11 — Sensibilidad CFL

Repetir T02 N400 y T03 N800 con CFL0.2,0.4,0.6, mismas IC/BC/t_final.
Cada ejecución cumple gates del caso padre. Comparar contra CFL0.2:
T02 diferencias E1 normalizadas de ρ,p,u≤0.015;
T03 cambio velocidad≤0.5% a0 y amplitud ≤0.08*amplitud inicial.
Reportar CFL realmente usado, rechazos y tiempo. No elegir solo CFL que pasa;
si0.6 falla, gate T11 falla y requiere decisión explícita antes de cerrar P2.

## T12 — Positividad y especie acotada

Adimensional γ1.4,R1,A1,x∈[0,1],N400, discontinuidad0.5;
IC izquierda(ρ,u,p,Y)=(1,−2,0.4,0), derecha=(1,2,0.4,1),
BC estados iniciales exteriores,t_final=0.1. Expansión fuerte sin vacío exacto;
referencia Riemann exacta con presión mínima positiva. También repetir T06 y
reposo/frustum T08 con Y=0 y Y=1. Verificar todos los estados aceptados,
incluidas etapas: finitos,ρ>0,p>0,T>0,0≤Y≤1 sin tolerancia de clipping.
E1 ρ,p normalizadas por1≤0.05 para expansión; ledgers≤1e−10.
Registrar fallback, downgrade, dt y rechazos; ningún agotamiento admite PASS.
Caso de entrada inválida separado: ρ≤0,p≤0,Y<0/Y>1/NaN debe rechazarse
antes del primer paso, no corregirse. La combinación de conservación y
boundedness es obligatoria: no alcanza una sola de las dos.

## Gates y límites de interpretación

P2a PASS requiere todos los subcasos y métricas T01–T12, sin omisiones;
P2b repite gates y orden adicional. Guardar arrays/ledgers/diagnósticos y
referencias versionadas, fuente, EOS, BC, geometría, CFL y tiempos por caso.
P1_PASS_CONTRACT_READY requiere documentos completos, manifest consistente,
revisión independiente PASS, alcance intacto y dependencia P0 aceptada.
Ausencia contractual: P1_BLOCKED_CONTRACT_INCOMPLETE; contradicción científica
no resuelta: SCIENTIFIC_CHANGE_REQUIRED. No ajustar umbrales tras ver P2 para
ocultar fallos. P1 siempre se detiene en WAITING_HUMAN_APPROVAL, sin P2.
