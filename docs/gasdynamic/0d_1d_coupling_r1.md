# P3-R1 — FINITE_WELL_MIXED_0D_COUPLING

Orden38a85593 autoriza un objeto físico distinto del reservoir prescritoP2.
Esta definición sustituye SOLO la interfaz futuraP3 de P1: los documentosP1–R5
y BC verificadas permanecen intactos como históricos y baselineP2.

## Volumen de control
Estado m,U,F,V: rho=m/V,e=U/m,T=e/cv,p=(gamma-1)*rho*e,Y=F/m.
W0D=(rho,0,p,Y): volumen homogéneo estacionario, sin momentum axial.
La aproximación representa conexión directa a una cara; sin Cd, puerto o apertura.
La energía total del contenido coincide con U porque su velocidad representativa
es cero. Energía cinética entrante se incorpora a interna bajo la hipótesis de
mezcla/disipación interna. No construir momentum temporal ni restar su cinética.

## Interfaz
Normal n apunta hacia afuera del tubo. Si n=-1, estados Riemann=(W0D,W1D);
si n=+1, (W1D,W0D). Una llamada HLLC contractual con fallback HLLE completo.
Gx=A*F_Riemann, Fout=n*Gx. d(m,U,F)0D=Fout[0,2,3], tubo recibe opuesto.
La orientación NO selecciona inflow/outflow: dirección emerge del flujo calculado.
El momentumGx[1] actúa normalmente en1D; fuerza/impulso externoFout[1] se
registra como reacción en cámara/pared, sin trabajo por pared estacionaria.
La energía es TODO el flujo numérico Euler, no m_dot*cvT ni otra entalpía por
rama. Especie TODO el componente Riemann, sin donor manual: HLLE puede difundir
un contacto, por lo que su razón especie/masa no debe sustituirse por otra.

## Gate R1 previo a P3B
C00: p100kPa,T0D300K,T1D299/300/301K,u0,Yambos.3, A.01m², ambas normales.
Referencia contacto Euler estacionario: flujosm/E/F nulos, presión transmitida.
C00B: mismos datos, Y0D.8/Y1D.2, velocidades±10^-1...±10^-5 y0m/s.
Guardar flujos y SM/método. Cada magnitud de flujom/E/F debe disminuir
estrictamente al reducir |u| en cada década y valer0 en reposo. Sin deadband.
Forward/reverse: p0D80/120kPa,p1D100kPa,T300K,u1D0; signo correspondiente,
vector HLLC íntegro, incrementos opuestos, especie HLLC coherente; fallback
probado por equivalencia de vector, no reemplazo manual. Regresión P2/P0,
revisión científica independiente requerida antes de actualizar volumen finito.

## Tiempo (solo después de R1 PASS)
CFL1D global. Sistema conjunto q=(C_i,m,U,F). Forward Euler o SSP-RK2 Heun:
q1=q+dtL(q,t), q2=q1+dtL(q1,t+dt), qnew=.5q+.5q2.
Mismo intercambio en RHS0D/1D de cada etapa, no congelarlo en el paso.
Rechazo conjunto ante inadmisibilidad o CFL del stage2, dt/2 hasta12 segúnP2.
Minmod y reconstrucciónP2 reutilizados; estado exterior para reconstrucción es
W0D del stage y el problema Riemann se resuelve solo al evaluar el flujo.
Ninguna segunda BC de presión/temperatura en la cara acoplada.
Para V(t), agregar únicamente-p*dV/dt a U y ledger; geometría1D estacionaria.
La etapa intermedia Euler extendida de Heun se valida a t+2dt antes de combinar
con estado inicial; el estado combinado usa V(t+dt). No hay momentum0D.


## P3B: fixtures congelados antes de ejecutar
Ambos métodos, CFL.4,N60,L.3m,A.0003m²,V0D.0001m³, pared derecha,
tubo inicialmente100kPa/300K/u0. Equilibrio: cámara100kPa,Yambos.3,tf.0015s.
Blowdown: cámara120kPa, Y0D.8,Ytubo.2,tf.0003s. Filling: cámara80kPa,
mismas fracciones,tf.0003s. Reversión: blowdown extendido tf.004s, sin reset.
C01 drift normalizado<=1e-12; C02/C03 signos de masa/energía y onda en tubo;
C04 al menos un cruce natural con bracket/instante interpolado; C05/C06
especieHLLC donante<=1e-12 normalizada (no reemplazar HLLE); C07 residuos
globales y de stages<=1e-10. Todos: finitud/positividad estricta y CFL porstage.
Referencia de signos proviene del gradiente inicial; conservación del balance
cerrado; no se usa el modelo0D antiguo como solución de referencia. Máximo300s
por caso y parada anteFAIL. Primera ejecución formal conserva todos resultados.

## P3C: definición previa a ejecución
Gate P3B independiente PASS. C08: N80, ambos métodos, CFL.4, mismo tubo y
estado uniforme100kPa/300K/Y.3; V(t)=V0[1+.05sin(2pi*t/.003)], tf=.003s.
Comparar inventario de energía con trabajo integrado por stages -p*Vdot,
recalculado desde presiones y derivada analítica. Residuos<=1e-10.

C09–C11: MUSCL, N40/80/160 y CFL.2/.4/.6, sin alterar solver. Pulso gaussiano
incidente ε=1Pa, centro.15m, ancho.03m, tubo.3m, área.0003m², cámara.0001m³,
p0=100kPa,T0=300K,Y=.3, tf=.0009s. Inicialización y referencia final mediante
cuadratura de conservadas por celda. No es soporte compacto: registrar colas
iniciales y reflexión analítica en pared derecha al tiempo final.

Referencia independiente linealizada del modelo R1 (revisada antes del run):
Z=rho*a; p'=pi+pr,u=(pr-pi)/Z; u*=(pch-2pi)/(2Z),p*=pch/2+pi.
Con dU/dt=-A*rho*h0*u*, resulta pch_dot=(2pi-pch)/tau,tau=2V/(aA).
pr=pch/2. Usar convolución causal desde0, pch(0)=0; en tubo evaluar pr(t-x/a)
y anular para argumento negativo. pi=ε exp(-[(x+a*t-.15)/.03]^2).
No imponer coeficiente reflejado: medirlo y compararlo con esta derivación.

C09: L1 normalizado por ε para presión y ε/Z para velocidad; errores de cámara
normalizados por Vε/a² (m), Vε/(gamma-1) (U), .3Vε/a² (F), ε (p).
Onda saliente desde característica del flujo, error temporal L1/ε. Presupuesto
fijo .025 para cada error (escala de accuracy acústica T03); no adaptación al
resultado. C10: cada error final de perfil y cámara disminuye40→80→160 para
cada CFL. C11: las tres diferencias de presión entre pares CFL, L1/ε, deben
ser no mayores enN160 que enN40; registrarN80. No exige monotonía intermedia.
C12: positividad de todas las etapas B/C, especie admisible, CFL por etapa y
rechazo de estado inicial inválido. Máximo300s/caso; conservar fallos y detener.

### Corrección de infraestructura del evaluador C09
Primer run P3C conserva C08 PASS ambos métodos; primer N40/CFL.2 integrado,
pero sin resultado retenido al fallar cuadratura final relativa cerca de momento
nulo. Sin resultado científico acústico en ese run. Se repite sólo ese caso y
los pendientes, reutilizando C08 por SHA256. Inicialización permanece idéntica.
Evaluación final usa GL4 compuesto8/16 subdivisiones/celda, separando frente
causal si cruza celda; diferencia<=1e-10 de A*dx*(rho0,ε/a,p0/(gamma-1),.3rho0).
Es control de convergencia de cuadratura, no cota rigurosa. Registrado y revisado
independientemente; ningún cambio en solver, datos, mallas, CFL ni accuracy .025.

## Adaptador y comprobación aislada de trabajo
C01–C12 PASS con revisión independiente habilita coupling_adapter.py: lectura
por nombre de volumen existente y copia inversa de m/U/F; EOS tomada del caso,
V de geometry(angle), sin conectar puertos ni ejecutar el modelo de motor.
Pruebas cubren layouts2T/4T, invariancia del resto del estado y rechazo de volumen
incompatible. La comprobación adiabática aislada prevista en diseño se realiza
con doble de prueba de cara sellada (no prueba R1): conserva m/F y contrasta
U=U0*(V0/V)^(gamma-1) al cuarto de ciclo de V(t), refinamientoN20/40/80,
error final relativo<1e-5. No introduce condición de frontera nueva en producto.
