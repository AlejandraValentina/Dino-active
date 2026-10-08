## Context y estado de autorización
Modelo, caso, aproximaciones y protocolo aprobados expresamente por la usuaria
el 15/09/2026 para implementar y ejecutar el prototipo de consola. Se conserva
debajo la definición y sus tolerancias previas; las menciones a aprobación futura
describen su estado documental original. No se autoriza integración Qt, JSON,
ondas, barridos ni entrega 6. Evidencia de ejecución en tasks.md.
Se recomienda **modelo 0D de cuatro volúmenes homogéneos con restricciones
cuasiestacionarias reversibles**. Solo monocilíndrico 2T atmosférico de encendido por
chispa, admisión al cárter por falda recta, un régimen y una condición sintética.
La chispa se aproxima por un inicio de aporte energético prescrito; no se predice llama.
Diferir ondas/inercia reduce la capacidad sobre el escape y necesita aprobación.
Ninguna validación documental autoriza por sí sola el prototipo ni la integración Qt.

## Decisions: circuito y estados
Circuito fijo, enlaces bidireccionales (flechas indican únicamente signo positivo):

`reservorio exterior I → conducto I → cárter → transferencias → cilindro → conducto E → reservorio exterior E`

Cuatro estados propios: conducto de admisión I, cárter K, cilindro C, conducto de
escape E. Cada uno integra masa m [kg], energía interna sensible U [J] y masa de
carga fresca F [kg]; residual Rm=m−F es derivado. Uniformidad instantánea de p/T/Y
por volumen, sin cantidad de movimiento, energía cinética macroscópica ni potencial.
Reservorios exteriores infinitos: p absoluta [Pa], T [K] y fracción fresca Y fija;
no integran estado ni devuelven automáticamente la mezcla que salió anteriormente.
Los enlaces no almacenan masa/energía. La elección de sistemas abiertos se apoya
en balances de volumen de control [1]; el precedente 2T de [4] sustenta esta división
termodinámica, no sus calibraciones ni el modelo más complejo de aquella publicación.

Gas ideal caloríficamente perfecto, mismas propiedades para fresca/residual:

- Y=F/m; T=U/(m*cv); p=m*R*T/V; u=cv*T; h=cp*T.
- R=287 J/(kg K); gamma=1.35; cv=R/(gamma−1)=820 y cp=1107 J/(kg K).

Estos valores son parámetros sintéticos explícitos, no propiedades de productos
reales a alta temperatura. Sin disociación, reacción química ni variación de cp(T).
Las relaciones caloríficas y pV sustentan el cierre, no la elección numérica [2].

## Balances y signos
Para cada volumen i, evaluando todos los enlaces con el mismo estado de etapa:

```
dm_i/dt = sum_in(q) − sum_out(q)                         [kg/s]
dU_i/dt = sum_in(q*h_donante) − sum_out(q*h_i)
          − p_i*dV_i/dt + Qdot_i                       [J/s]
dF_i/dt = sum_in(q*Y_donante) − sum_out(q*Y_i) − Bdot_i  [kg/s]
```

q es magnitud no negativa; la selección de donante sigue el signo físico del enlace.
Un flujo interno se computa una sola vez: mismo q, h y Y con signos opuestos en
ambos extremos. h es entalpía de remanso del donante homogéneo; el chorro se mezcla
y disipa en el receptor sin sustraer dos veces su energía cinética. No se añade
trabajo de flujo p/rho aparte de h [1]. Bdot solo convierte el marcador fresco en
residual en C; no destruye masa total. Qdot solo aporta energía en C.

Trabajo indicado objetivo: W_C=integral_ciclo(p_C*dV_C) [J/ciclo], positivo si el gas
trabaja sobre el pistón, incluyendo todo el ciclo abierto. Registrar además W_K=
integral(p_K*dV_K) como diagnóstico de bombeo del cárter. W_C no descuenta ese
trabajo ni fricción y **no es trabajo al eje**; no inferir potencia/par al freno.

## Volúmenes variables y geometría reutilizada
En las ecuaciones se convierten mm→m, mm²→m² (1e−6) y cm³→m³ (1e−6).
Con r=S/2, biela l, ángulo theta en radianes para funciones trigonométricas:

```
x = r*(1−cos(theta)) + l − sqrt(l²−r²*sin(theta)²)
dx/dtheta = r*sin(theta) + r²*sin(theta)*cos(theta)/sqrt(l²−r²*sin(theta)²)
A_p = pi*D²/4; V_d=A_p*S; V_clear=V_d/(C_geom−1)
V_C = V_clear + A_p*x
V_K = V_K_PMI + A_p*(S−x)
dV_C/dt = A_p*(dx/dtheta)*omega; dV_K/dt = −dV_C/dt
omega = 2*pi*n/60 [rad/s]; dtheta_deg/dt=6*n [grados/s]
```

Reutilizar `kinematics.piston_position` (forma racionalizada estable) y sus
convenciones; no interpolar la tabla de un grado para integrar. K supone área
inferior del pistón igual a A_p y que el desplazamiento de biela/cigüeñal no agrega
variación angular: queda absorbido en el volumen libre de PMI. Sin fugas, sin
volúmenes de transferencias ni conductos añadidos al valor registrado. Hipótesis
por aprobar, no deducida del JSON. V_C+V_K constante es un control geométrico.

Ventanas: conservar las leyes de `ports.py` y `intake.py`, evaluadas al ángulo actual:
A_escape/transfer=w*max(0,min(h,x−u)); A_adm=w*max(0,min(h,u+h−f−x)), en mm².
La admisión requiere u>=S y 0<d=u+h−f<S para el caso con encendido; ninguna fila
sin función participa por inferencia. Ventanas de igual función son enlaces en
paralelo entre los mismos volúmenes, no un único conducto por cada lumbrera.

## Restricciones y retorno de flujo
En cada enlace de área geométrica A, A_ef=Cd*A. Cd es explícito, constante,
igual en ambos sentidos para este caso; no se supone que A geométrica sea efectiva.
Elegir el extremo de mayor p como aguas arriba (p_u,T_u,Y_u); el otro es p_d.
Reservorios/CV en reposo se tratan como estados de remanso; enlace adiabático,
cuasiestacionario, descarga en volumen bien mezclado. p iguales o A=0 ⇒ q=0.
Con beta=p_d/p_u y beta_crit=(2/(gamma+1))**(gamma/(gamma−1)):

```
q = Cd*A*p_u/sqrt(R*T_u) * Phi(beta)                       [kg/s]
Phi = sqrt(2*gamma/(gamma−1) * (beta**(2/gamma) − beta**((gamma+1)/gamma)))
      si beta_crit < beta <= 1
Phi = sqrt(gamma)*(2/(gamma+1))**((gamma+1)/(2*(gamma−1)))
      si 0 < beta <= beta_crit
```

Se cambia donante, signo, h e Y juntos al invertirse presión, también en
transferencias y ventanas. No hay válvulas antirretorno ficticias. La ley de
estrangulamiento deriva de flujo isentrópico compresible [3]; Cd representa una
corrección empírica propuesta, **sin calibrar**, no una validación de esa ley en
las ventanas reales. No se resuelven recuperación de presión ni choques de chorro.

## Conductos: capacidad que se propone reducir
Cada recorrido del editor se reduce a **un depósito 0D de volumen fijo**:
V_I/E=sum(V_tramo); A_min,I/E=min(pi*D1²/4,pi*D2²/4 de todos los tramos).
Una restricción de A_min conecta I con su reservorio exterior y otra E con el suyo;
son pérdidas concentradas asignadas a los extremos exteriores por convención.
La ventana de falda conecta I↔K y las ventanas de escape C↔E con sus propias áreas.
Las longitudes solo aportan volumen almacenado; diámetros aportan volumen y A_min.
No usar área de lumbrera para inventar un diámetro ni cambiar el JSON o sus sentidos.
Para el prototipo las listas deben ser completas, no vacías y continuas; un editor
puede seguir guardando geometrías que el futuro caso rechace con explicación.

**Sí:** almacenamiento de masa/energía y presión uniforme transitoria en I/E;
respuesta de llenado/vaciado ante cambios de volumen agregado, sección limitante
u otra presión exterior prescrita. **No:** inercia axial, fricción distribuida,
propagación/reflexión, tiempo de viaje acústico, pulsos de retorno de una cámara
sintonizada, resonancia ni RPM óptimas. No es “1D”. Cambios de orden, ubicación de
conos o perfiles con los mismos V/A_min son indistinguibles. Alargar un escape
solo cambia su capacidad 0D, no predice cuándo vuelve una onda ni cuál escape rinde
mejor. Aunque aparezcan oscilaciones temporales, no acreditan sintonía. La separación
entre almacenamiento, inercia y efectos de ondas se contrasta con [5] y [6].

Se recomienda esta reducción **solo para comprobar el primer núcleo acoplado**.
Si no se aprueba explícitamente diferir ondas, este diseño no habilita el prototipo;
no se renombra ni se implementa silenciosamente una alternativa.

Transferencias K↔C: suma de restricciones de las ventanas existentes, con Cd_T
agregado explícito; almacenamiento e inercia del trayecto se **desprecian**, no se
consideran conocidos. V_transferencia=0 es una aproximación del modelo, no una
medición ni un campo dimensional que completar con cero. No se precisa otra
longitud en esta reducción; falta Cd_T y la aceptación de despreciar el volumen
muerto y tránsito. Si eso no es admisible para un motor real, faltan volumen,
sección/longitud y pérdidas del trayecto y habrá que redefinir el modelo antes de
usarlo. No se abre ahora un editor ni se añade ese volumen al cárter.

## Carga fresca, residual, barrido y energía prescrita
Y es la fracción másica de carga fresca aún no procesada por el aporte energético;
1−Y es residual o carga ya procesada. Mismas propiedades para ambos marcadores.
Todo efluente tiene Y del volumen donante: mezcla homogénea perfecta, sin chorros,
capas, cortocircuito calibrado ni mapa de barrido. El escape puede llevar fresca
y el retorno puede contaminar el cárter. Medir flujos de ambos marcadores y Y_C al
cierre, sin llamarlos barrido real validado. Mezcla perfecta es un límite ideal,
distinto de desplazamiento y cortocircuito [5]; no se añade un factor de ajuste.

Aporte prescrito por masa fresca atrapada al inicio theta_s, con ventanas C cerradas
durante todo el aporte. Se captura F_s=F_C(theta_s), q_f=800000 J/kg de carga fresca
y Q_ciclo=q_f*F_s [J]. No hay combustible explícito, relación aire/combustible, PCI,
inyección ni evaporización: q_f es un parámetro sintético energético, no consumo.
Para theta_deg acumulado, inicio theta_s=350°+360k y duración Delta=40°:

```
z=(theta_deg−theta_s)/Delta
b(z)=0 si z<=0; z−sin(2*pi*z)/(2*pi) si 0<z<1; 1 si z>=1
db/dtheta_deg=(1−cos(2*pi*z))/Delta dentro del intervalo, 0 fuera
Qdot_C=Q_ciclo*(db/dtheta_deg)*6*n
Bdot_C=F_s*(db/dtheta_deg)*6*n
```

Así integral Qdot dt=Q_ciclo e integral Bdot dt=F_s; se convierte el marcador
sin salto instantáneo de masa/energía y sin volver a calentar residual como fresca.
F_s=0 ⇒ Q_ciclo=0, registrar ausencia de aporte, no inventar encendido. El caso no
podrá acreditarse como ciclo encendido si queda sin carga fresca/aporte. No es ley
de llama predictiva ni rendimiento de combustión medido. La forma sinusoidal se
elige por integral exacta y derivada continua, no por ajuste experimental.

Paredes adiabáticas en los cuatro CV: Q_pared=0 (sin temperatura de pared o h ocultos).
Sin radiación, blow-by, fricción mecánica, distribución ni calor químico adicional.
Las irreversibilidades de descarga/mezcla no se restan como pérdida de energía:
se conserva entalpía y no se contabilizan dos veces. No modela equilibrio térmico
de piezas ni pérdidas al eje. Todo ello debe aprobarse como alcance de viabilidad.

## Caso único de desarrollo: S2T-0D-01
**Todos los valores de entrada siguientes son supuestos sintéticos**, cero mediciones
y cero calibración experimental. No corresponden a fabricante/modelo real. Nombre
descriptivo de prueba; fabricante/modelo vacíos. No llenar proyectos de la usuaria.

| Entradas geométricas reutilizadas de JSON v5 | Valor |
| --- | --- |
| cycle / cylinder_count | 2T / 1 |
| bore_mm / stroke_mm / rod_length_mm | 54 / 56 / 100 mm |
| compression_ratio (geométrica) | 8:1 |
| crankcase_volume_bdc_cm3 | 250 cm³, libre en PMI, excluye conductos |
| Escape: una ventana, función escape, u/h/w | 32 / 10 / 20 mm |
| Transferencia: dos ventanas individuales, función transfer, u/h/w de cada una | 44 / 10 / 12 mm |
| intake.mode, u/h/w/f | piston_port; 64 / 10 / 20 / 42 mm |
| ducts.intake, un tubo L/D1/D2 | 100 / 20 / 20 mm |
| ducts.exhaust, tubo seguido de cono L/D1/D2 | 100 / 20 / 20; 100 / 20 / 40 mm |

Conservar referencias v3/v4/v5 existentes. Derivados exactos a partir de estas
entradas: V_d=40.824*pi cm³; V_clear=5.832*pi cm³; V_C,PMI=46.656*pi cm³;
V_K,PMS=250+40.824*pi cm³; V_I=10*pi cm³; V_E=(100/3)*pi cm³;
A_min,I=A_min,E=100*pi mm². La relación geométrica no es compresión efectiva
atrapada. Escape abre/cierra 90°/270°; admisión 270°/90°; transferencias derivadas
del cruce x=44 mm. Sin modificar los criterios geométricos ya aprobados.

| Entradas adicionales, fuera del JSON actual | Valor o convención fijada para aprobación |
| --- | --- |
| Régimen / velocidad angular | 3000 rpm constante; omega=100*pi rad/s; ciclo=0.020 s |
| Carga | Condición fija sin mariposa: dos reservorios a 100000 Pa absolutos y energía específica q_f prescrita; no % de carga ni par impuesto |
| Reservorio I: p / T / Y | 100000 Pa abs / 300 K / 1 |
| Reservorio E: p / T / Y | 100000 Pa abs / 500 K / 0; devuelve gas residual sintético si hay retorno |
| Cd admisión por falda / cada escape / cada transferencia | 0.70 / 0.70 / 0.65, ambos sentidos |
| Cd extremo exterior I / extremo exterior E | 0.80 / 0.80, ambos sentidos |
| Gas / calor / pérdidas / aporte | Valores y leyes definidos arriba, sin otros coeficientes |
| Arranque y referencia angular | t=0 en theta=180° (PMI); PMS=0°/360°, siguiente inicio de calor=350°; calor termina=390° |

| Estado inicial propio a theta=180° | p absoluta [Pa] | T [K] | Y fresca | V [cm³] |
| --- | --- | --- | --- | --- |
| I | 100000 | 300 | 1 | 10*pi |
| K | 120000 | 330 | 1 | 250 |
| C | 140000 | 700 | 0 | 46.656*pi |
| E | 100000 | 500 | 0 | (100/3)*pi |

En todos, m0=p0*V0/(R*T0), U0=m0*cv*T0, F0=Y0*m0; se derivan, no se ingresan
por separado. Los estados iniciales no son un ciclo estabilizado; C>K al inicio
fuerza un retorno de transferencia comprobable. No se garantiza convergencia.
El circuito, Cd, régimen, contornos, estados, q_f/ángulos y opciones físicas no
existen en JSON v5: quedan aquí, sin nuevo formato, fixture de proyecto ni controles.

## Prueba de viabilidad — protocolo previo ahora autorizado
Un prototipo pequeño de biblioteca estándar, sin Qt ni importar solver antiguo.
Propuesta numérica única: RK4 explícito en tiempo sobre m/U y F advectada, con
acumuladores de flujo/calor/trabajo y paso máximo expresado en grados. Durante
todo el aporte con C cerrado, F_C se evalúa analíticamente como F_s*(1−b)
en **todas las etapas**, incluidos extremos, en vez de integrar esa componente
por RK4; la conversión acumulada de cada paso es F_s*(b_fin−b_inicio). Al terminar
el aporte se retoma la ecuación de advección. No se espera a que una etapa prediga
F negativa ni se recorta/renormaliza el estado. Alinear pasos con puntos
muertos, aperturas/cierres calculados, inicio/fin de calor y límites de ciclo;
no obtener eventos desde muestras de dibujo. Cada etapa reutiliza geometría y
calcula cada enlace una vez. No hay malla espacial ni plataforma de solvers.

**Comprobaciones elementales independientes antes del ciclo completo** (otros
problemas matemáticos pequeños, no otros motores de desarrollo):

| Comprobación | Referencia y criterio previo |
| --- | --- |
| Geometría y signo de trabajo | V_C+V_K constante; V_I=10*pi y V_E=100*pi/3 cm³, A_min=100*pi mm². Error relativo <=1e−9, sin integración temporal |
| Flujo compresible | Para gamma=1.4, R=287, p_u=200000 Pa, T_u=300 K, A=1e−4 m², Cd=1 y p_d=100000 Pa: beta_crit≈0.5282817877 y q≈0.04667117 kg/s por fórmula analítica independiente; error relativo <=1e−5. A=0 o p iguales: flujo exactamente cero; invertir extremos con T/Y distintos invierte donante y signos; comprobar rama subcrítica beta=0.8, q≈0.03821455284 kg/s por sustitución manual (mismo error relativo), y continuidad a beta_crit ±1e−6 |
| Recipientes aislados conectados, V fijos, sin calor | Masa y energía conjunta conservadas; entalpía/fresca transferidas con igual magnitud y signo opuesto. Error de balance <=1e−7 relativo a inventario inicial; F también constante sin conversión |
| Compresión cerrada adiabática | p*V**gamma constante y W=(p1*V1−p2*V2)/(gamma−1); error relativo <=1e−4 en p y trabajo con escala mínima 1 J. Solo prueba interna; no sustituye motor abierto |
| Calor en masa/volumen fijo | U_fin−U_ini=q_f*F_s y F_fin=0 con la ley propuesta; error <=1e−5 relativo en energía y <=1e−7 de masa inicial en F; sin crear/destruir masa total |
| Mezcla homogénea aislada del motor | Recipiente isotermo de masa constante M, entrada fresca y salida mezclada iguales, F(0)=0: Y=1−exp(−q*t/M). Con q*t/M=1, Y=0.6321205588; error absoluto <=1e−4 |

Las referencias se evalúan por sustitución analítica separada, no llamando a la
función bajo prueba; no se ejecutaron hoy como pruebas de un solver. Solo se comprobó la aritmética de
las referencias del documento, sin importar MotorSim ni integrar estados. Los controles algebraicos son más
estrictos que integración/mezcla, sin exigir precisión de máquina al motor.

**Experimento integrado único:** mismo caso desde los mismos estados iniciales,
resoluciones máximas 0.5°, 0.25° y 0.125°, en ese orden. Tres ejecuciones como
comprobación mínima de resolución, no barrido de regímenes ni campaña de modelos.
Guardar últimas dos vueltas a nodos comunes de 0.5° y resúmenes por ciclo; los
extremos y flujos se monitorizan en cada paso, no solo en la salida muestreada.

En cada vuelta de 180° a 180°+360°, auditar por CV y globalmente:

- Residuo masa: Delta m−integral(in−out). Escala max(m_inicio, integral de flujos
  absolutos, 1e−9 kg); límite relativo 1e−6. Residuo fresca incluye integral Bdot,
  con misma escala y límite. Flujos internos cancelan al sumar CV.
- Residuo energía: Delta U−[H_in−H_out+Q−W_C−W_K], por CV su propio trabajo.
  Escala max(U_inicio, |H_in|+|H_out|+|Q|+|W_C|+|W_K|,1 J); límite 1e−5.
  Auditar también contra cuadratura independiente sobre salida refinada; no basta
  sumar el mismo RHS y declarar independencia. Para esa cuadratura permitir 0.1 %
  de la misma escala por muestreo; no sustituye conservación discreta.
- Toda masa, V, U, p y T positiva/finita; 0<=F<=m sin recortar ni renormalizar
  silenciosamente. Aplicar la solución analítica de F_C durante **todo** el
  intervalo de calor cerrado, según el método anterior, y contabilizar su conversión
  por diferencia analítica. Fuera de ese intervalo, una etapa F no física exige
  rechazo controlado. Con A=0 el flujo debe ser cero; a theta=180° inicial el
  signo de transferencia es C→K y el efluente tiene Y_C=0 y h_C.
- Registrar p_C(theta), pares (V_C,p_C), W_C/W_K, m/U/T/Y/V de cada CV, signos y
  magnitudes de flujos, Q_ciclo, F_s, balances, máximos, resolución y motivo de parada.
  Sin curvas ficticias ni expectativas de un pico/trabajo positivo inventados.

Convergencia propuesta: por tres vueltas consecutivas desde la vuelta 5, diferencias
entre estados al mismo theta=180° de m,U <=0.2 % (denominadores max(|actual|,|previo|,
1e−9 kg o 1 J)), de Y <=0.002 absoluto en todos los CV y de W_C <=0.5 % con escala
max(|W_C actual|,|previo|,1 J). Además cambio máximo de p_C en nodos comunes <=0.5 %
con escala max(p_max actual,p_max previo,100000 Pa), y balances dentro de límites.
F_s y Q_ciclo del ciclo convergido deben ser >0 para acreditar el caso encendido.
No basta converger masa dejando presión o energía derivando.

Sensibilidad: entre las dos resoluciones más finas convergidas, W_C y masas netas
por enlace cambian <=1 % (escalas mínimas 1 J y 1e−7 kg); p_C máximo y norma máxima
de diferencia de curva <=1 % de p_max fino. Diferencia de estado final Y <=0.005.
La discrepancia fina no debe superar la gruesa en magnitudes fuera del piso numérico;
si no cumplen, viabilidad no acreditada y revisión puntual del motivo, sin relajar
estos umbrales tras observar el fallo. Son criterios de estabilidad numérica útil
para comparar iteraciones de desarrollo, no error físico frente a mediciones.

Límites propuestos antes de ejecutar: 30 vueltas por resolución; 60 s de pared por
resolución y 180 s para las tres; proceso completo <=512 MiB de memoria residente.
Medir tiempo monotónico, máximo de memoria del proceso (incluye runtime), CPU,
Windows y versiones en el equipo real; nada medido todavía. Meta de hoja: hasta
un minuto por punto típico y diez minutos por diez puntos; no demostrada, y no se
ensayan esos diez puntos. Si no converge en el presupuesto, terminar como
**no convergido / presupuesto excedido**, no prolongar corridas ni esconder coste.

Rechazo de etapa no física: dividir paso por dos, hasta 8 rechazos seguidos y paso
mínimo 0.001°; cualquiera de esos límites aborta con CV, ángulo y causa. Topes de
2 millones de evaluaciones del RHS por resolución, T fuera de [100,4000] K o
p fuera de [1000,2e7] Pa abortan como fuera del dominio de esta prueba (no límites
universales del gas). No reparar datos ni limitar temperaturas para seguir.
Comprobar cancelación y presupuesto al menos cada 0.5 s; emitir avance por vuelta
y como máximo cada 1 s entre avances; cancelación sale en <=1 s. No reintentos
indefinidos. Un benchmark aislado del orificio no acredita coste del ciclo acoplado.

## Aprobaciones previas — obtenidas por orden explícita del 15/09/2026
1. Reducir explícitamente el primer caso a depósitos 0D sin ondas/inercia ni sintonía,
   incluida pérdida concentrada A_min/Cd y transferencia sin almacenamiento.
2. Aceptar gas caloríficamente perfecto, mezcla perfecta, paredes adiabáticas y
   conversión/energía prescritas en lugar de combustión predictiva; caso y parámetros
   sintéticos de esta definición sin calibración experimental.
3. Aprobar el experimento y límites/tolerancias previos, y autorizar expresamente
   la implementación y ejecución del prototipo. La integración a interfaz y cambios
   de archivo siguen sin autorizarse por esta definición.

## Diagnóstico localizado anterior — evidencia del método fijo

La orden posterior autoriza diagnóstico y corrección de defectos demostrados,
sin cambiar el método para forzar aceptación. La vuelta reconstruida reproduce
exactamente la evidencia de 54821600: RK4 de paso fijo atraviesa el equilibrio
de presión dentro de sus etapas en los enlaces exteriores I/E. Con E cerrado
al cilindro, sin calor/trabajo y p_E>p_res, el modelo continuo conserva Y_E durante
la descarga; la trayectoria numérica cambia Y_E por retornos entre etapas.
No se encontró un defecto de signos, donante, unidades o cuadratura. Evidencia,
intervalos y controles en tasks.md; las tolerancias anteriores permanecen intactas.

De la ley ya aprobada, cerca de equilibrio q es proporcional a
sign(Delta p)*sqrt(abs(Delta p)); su pendiente no está acotada al acercarse a cero.
Esto explica por qué un paso fijo que conserva inventarios algebraicamente puede
introducir retornos numéricos. Las etapas intermedias RK4 no son una salida densa
independiente: dos de ellas comparten tiempo pero tienen estados distintos.
Reutilizar sus pesos en la auditoría ocultaría la discrepancia sin corregir Y.

**Única modificación propuesta, no implementada:** conservar RK4 y añadir control
local mediante comparación de un paso y dos medios pasos; aceptar la trayectoria
de los medios pasos solo cuando el indicador de error lo permita, o reducir el
paso. Incluir m/U/F y transportes, mantener F_C analítica, alineación con eventos,
auditoría independiente sobre pasos aceptados y todos los topes actuales.
La diferencia sería un indicador, sin extrapolación que presuponga suavidad en
la inversión de flujo. Las tolerancias de ese control local requieren fijación
y aprobación antes de ejecutarlo; no reemplazan ni relajan las de aceptación.

Coste directo sin reutilización: 12 evaluaciones RHS por intento frente a 4,
más intentos/pasos si se necesita reducirlo. No se ha medido ese coste ni probado
que alcance precisión o presupuesto; si alcanza el mínimo de 0,001° o cualquier
tope debe detenerse con diagnóstico. No se propone anular caudales, recortar
estados o alterar Cd/energía/contornos. No se ejecutó otra serie oficial.

## Decisión numérica y ensayo adaptativo autorizado — 15/09/2026

La orden posterior aprueba implementar RK4 por duplicación de paso y el ensayo
acotado siguiente. Sustituye únicamente la decisión numérica pendiente anterior;
se conservan su diagnóstico, las decisiones físicas y la aceptación original.

Para cada propuesta h: desde copias del mismo estado, una rama RK4(h) y otra
RK4(h/2) seguida de RK4(h/2). Para cada m/U/F de los cuatro CV:
e_j=abs(y_dos_medios_j-y_completo_j)/15;
s_j=atol_j+rtol*max(abs(y_inicio_j),abs(y_dos_medios_j)); E=max(e_j/s_j).
Aceptar solo E<=1 y controles físicos aplicables; conservar exclusivamente los
dos medios pasos, sin extrapolar el estado. El divisor 15 es el estimador de
orden cuatro autorizado, no cota garantizada cerca de inversiones de flujo.

| Perfil | h máximo propuesto | rtol | atol m/F [kg] | atol U [J] |
| --- | --- | --- | --- | --- |
| A | 0,5° | 1e-6 | 1e-12 | 1e-6 |
| B | 0,25° | 3e-7 | 3e-13 | 3e-7 |
| C | 0,125° | 1e-7 | 1e-13 | 1e-7 |

Son tolerancias nuevas **locales**, no cambios de balances, repetibilidad,
convergencia o sensibilidad. Factor del controlador=min(2,max(0.2,0.9*E**(-1/5)));
E=0 permite factor 2; estimador no finito rechaza y reduce por 0,2. Un rechazo
siempre reduce, con ocho consecutivos como máximo; etapa no física conserva
reducción por dos. Dominio T/p y demás presupuestos previos siguen vigentes.

Mínimo 0,001° **por medio paso realmente ejecutado**: propuesta h>=0,002°.
No imponer un mínimo al paso rechazado y continuar como si hubiera aprobado.
Acortar para no atravesar eventos/nodos de salida ni dejar un resto menor al
mínimo; si no se puede, detener con causa. Coincidencias de eventos calculados
y nodos solo se unifican al nivel de redondeo de máquina, no por tolerancia física.

Las ramas no comparten inventarios ni acumuladores mutables. F_s se captura una
vez en el estado aceptado al inicio del aporte; F_C sigue analítica en todas las
etapas y la conversión por diferencia de primitiva en cada recorrido. Acumular
solo la rama aceptada; auditar por trapecios sus dos intervalos reales, incluido
el estado intermedio. Las etapas internas no son muestras aceptadas. Contar todos
los RHS ejecutados, incluidos intentos descartados (12 nominales, sin reutilización).
La implementación actual evalúa además derivadas al validar/obtener tres extremos
por intento y un inicio por ciclo: se cuentan también contra el límite de RHS,
distinguiendo etapas y extremos (15 evaluaciones por intento completo, más inicios).
Registrar h propuesto y medios pasos efectivos, sus extremos/causas de rechazo,
mínimo/máximo/media, coste, estados, flujos, balances y resultados originales.

Antes de la serie, repetir el intervalo diagnosticado 300–300,5° desde su estado
registrado, comparar p/m/U/F/Y y masas por sentido, y comprobar retorno físico,
rechazo por error con estados positivos, descarte, eventos y controles elementales.
Si no reduce la deriva o agota un límite, detener sin serie formal. En otro caso,
una sola serie A/B/C desde los estados originales, sin arranque caliente:
30 ciclos/60 s por perfil, 180 s total, 512 MiB, 2 millones RHS y límites previos.
Convergencia completa permite parar antes; no reajustar perfiles tras ver resultados.
La comparación incluye Y_E y sigue requiriendo la convergencia de los tres perfiles.
Entrega 5 abierta, sin Qt/JSON, nuevas campañas, autenticación o archivo del cambio.

## Variante exterior regularizada autorizada — 15/09/2026

La nueva orden autoriza expresamente modificar la ley de los enlaces exterior→I
y E→exterior, conservando ejecutable la ley original. No es equivalencia exacta
ni calibración física. Interiores, áreas, Cd, propiedades, calor, contornos y
estados iniciales permanecen iguales. RK4 adaptativo y perfiles anteriores intactos.

Con dp=p_izquierda-p_derecha y z=abs(dp)/delta_p: caudal cero si dp=0;
si 0<z<1 multiplicar q_original por sqrt(z)*(1,5-0,5*z); si z>=1 usar
exactamente la evaluación original. Transportar masa, entalpía y fresca con el
mismo factor y donante. Sin zona muerta, recorte de estados ni bloqueo de retorno.
Dentro de la banda, evaluar la diferencia compresible como
exp(2/gamma*log_beta)*(-expm1((gamma-1)/gamma*log_beta)), donde
log_beta=log1p((p_receptor-p_donante)/p_donante). Es una identidad algebraica
que evita restar potencias casi iguales. Fuera de la banda y en la opción original
se conserva la evaluación previa. Se prueban pendientes laterales finitas cerca
de cero; distintas temperaturas pueden dar pendientes distintas, sin afirmar C1
en la igualdad. En el borde, el factor vale uno y su derivada vale cero.

Bandas fijas: principal 100 Pa en ambos exteriores; única alternativa 50 Pa.
Son parámetros del ensayo, no mediciones ni tolerancias. No varían con el paso
ni se reajustan después de ver resultados. El auditor usa los flujos de esta
variante evaluados en ambos extremos de cada medio paso aceptado, con trapecios
independientes; no toma el libro RK para fabricar cierre.

Antes del caso: cero/área, signos/donantes, pendientes y empalme, interiores
intactos, coherencia de transporte; intervalo original 300–300,5° con ambas bandas
y llenado separado. Si falla o no reduce claramente el defecto, no ejecutar serie.
Tras aprobar: A a 100 Pa desde el estado original; sin convergencia completa,
detener sin B/C. Con A aprobado, continuar B/C desde estados originales; detener
también ante fallo de un perfil. Solo con A/B/C y sensibilidad aprobados ejecutar
C a 50 Pa, con sus 60 s separados. Comparar ambas soluciones convergidas mediante
las magnitudes/pisos y umbrales existentes (1 %; Y absoluta 0,005), identificando
dependencia de la banda, no tendencia de refinamiento temporal con dos bandas.
No se infiere validación experimental.

Se mantienen 30 ciclos, 60 s/ejecución, 180 s/serie principal, 512 MiB, 2 millones
de RHS, mínimo real 0,001°, ocho rechazos consecutivos y dominio físico previos.
Progreso y cancelación observables. Conservar evidencias en directorios nuevos;
no reintentos de serie, otras bandas, Qt/JSON, autenticación, archivo u otra entrega.

## Primer tramo gráfico del caso fijo autorizado — 15/09/2026

Nueva orden: integrar únicamente S2T-0D-01 a 3000 rpm, banda exterior 100 Pa,
perfil B. No convierte parámetros del editor en un caso ni modifica proyectos.
Preservar 0cb0c754, física, controles y ensayo anterior. Una ejecución individual
no vuelve a comprobar sensibilidad. Entrega 5 abierta: falta definir/comprobar
su uso con entradas del editor, fuera de este tramo.

`reference_run` ejecuta una sola llamada a `run_adaptive` con `Model`, sin Qt.
`reference_results.reference_inputs()` comparte la definición SyntheticCase,
el perfil B existente y la banda fijada; la ventana no copia constantes del motor.
El comando original y `regularized_trial` permanecen disponibles y sin cambios.
Se mantienen 30 ciclos/60 s de integración, 512 MiB del proceso numérico, 2 millones
de RHS, mínimo real 0,001°, ocho rechazos y dominio físico. El coste de interfaz
se muestra por separado. No se repite la serie A/B/C ni la comparación de bandas.

QProcess inicia Python del entorno con argumentos separados y directorio del
paquete, sin shell ni espera bloqueante. Recibe JSON por líneas con ciclos reales,
tiempo y RHS, sin porcentaje inventado. Solo un proceso activo; Ejecutar y Abrir
resultado quedan deshabilitados durante el cálculo. Nuevo intento borra las curvas
y resultados anteriores antes de arrancar. Error al abrir un archivo conserva
el resultado válido anterior y señala que no se abrió el archivo solicitado.

Cancelación: pipe stdin con `cancel\n`; un hilo estándar del hijo activa Event,
consultado por el monitor existente. EOF también cancela si desaparece el padre.
Consola conserva Ctrl+C. Tras 3 s sin respuesta a cancelar, QProcess.kill detiene
el hijo y se informa cancelación forzada, nunca éxito. Supervisión de interfaz
a 65 s solicita cancelar un proceso sin finalización; no amplía los 60 s del núcleo.
Cerrar primero aplica Guardar/Descartar/Cancelar del editor. Si se permite cerrar,
deshabilita edición, cancela y cierra por señal de proceso finalizado, sin huérfanos.

Pestaña Simulación 2T: caso sintético identificado, explicación de independencia
respecto del proyecto, resumen y detalles efectivos de solo lectura; Ejecutar,
Cancelar y Abrir resultado. Convergencia requiere estado y balances validados,
no solo código cero. Mostrar último ciclo completo: presión absoluta en kPa frente
a ángulo continuo 180–540° (PMI/PMS/PMI) y P-V en cm³/kPa, preservando orden temporal.
Trabajo C/K proviene del resumen del núcleo, no de integrar puntos de dibujo.
Resultados no convergidos/cancelados/errores se identifican como diagnóstico no
aceptado y no muestran curvas de éxito. Limitación visible única: modelo 0D con
energía prescrita, sin ondas ni validación experimental.

Formato de resultados independiente de JSON v5: `manifest.json`, formato
`motorsim-reference-result`, versión 1, versión de modelo
`four-cv-0d-prescribed-heat-v1-external-regularized-rk4-v1`, run_id y unidades.
Vincula nombres fijos `case.json` (entradas efectivas), `summary.json` (estado,
entorno, resumen por ciclo/coste y diagnóstico parcial) y `samples.json` (últimos
dos ciclos completos y muestras parciales), mediante run_id y SHA256. Se reutilizan
los registros/muestras del núcleo, sin ecuaciones de ejecución duplicadas. El
manifiesto se escribe al terminar; una escritura incompleta no parece resultado válido.
`attempts.csv` conserva la traza numérica, no necesaria para dibujar/reabrir.
Hashes detectan mezcla/alteración de archivos; no constituyen firma o autenticidad.

Abrir valida formato/modelo/unidades, nombres y hashes, entradas del caso fijo,
estructura/números finitos, dominio/inventarios, continuidad temporal, correspondencia
de muestras/resumen, balances y tres ciclos de convergencia. No ejecuta contenido.
Límite de 16 MiB por archivo JSON. Carpeta nueva por ejecución, predeterminada en
LOCALAPPDATA/MotorSim/Resultados (alternativa de usuario en otros sistemas); nunca
.venv ni una ruta E: codificada. `--output` permite una carpeta nueva explícita.
Cambiar proyecto o 2T/4T no modifica, reasigna ni borra los resultados del caso.

## Conexión del editor autorizada — 15/09/2026

Extiende el tramo gráfico anterior: segundo origen «Geometría del proyecto ·
ensayo 0D a 3000 rpm», sin modificar S2T-0D-01 ni ecuaciones. GUI usa B/100 Pa;
los restantes valores de SyntheticCase son condiciones de referencia, no medición
ni calibración del motor. No se conoce la procedencia de la geometría del usuario.
No hay edición de condiciones ni selector de solver. Conductos conservan solo
volumen agregado y sección limitante; no hay propagación ni sintonía.

El editor recopila todos sus borradores (no disco): error numérico bloquea y se
informa junto con ausencias/incompatibilidades; ningún None sustituto por error
sale hacia el cálculo. Un proyecto guardable puede no ser ejecutable. Preflight
exige 2T/1 cilindro, mecanismo/compresión y cárter completos, falda completa en su
dominio, exactamente 1 escape y 2 transferencias efectivos, conductos completos
y continuos. Intersección analítica de intervalos abiertos de eventos con 350–390°,
incluidos desplazamientos de 360°, verifica cierre en todo el aporte; no decide
desde muestreo de curvas. La comprobación se repite antes del cálculo en el hijo.

`project_case` construye un caso independiente heredando solo las condiciones
fijas. Canoniza escape primero y transferencias por (top, height, width), asignados
a enlaces 4, 2 y 3 respectivamente (índices desde cero, seis enlaces sin cambios).
Con geometrías idénticas el intercambio de transferencias es numéricamente neutro;
se conserva fila original, nombre, función y dimensiones en el mapeo. Identidad
del motor PROJECT-0D + hash de geometría sin nombres; escenario independiente
`S2T-0D-01-reference-conditions-v1`. No muta SyntheticCase ni precarga lumbreras.
Model recibe la geometría canonizada y deriva inventarios iniciales desde sus
volúmenes y p/T/Y fijos; no se copian m/U/F del motor de referencia.

Una copia JSON independiente se envía por archivo temporal exclusivo como argumento
QProcess, se valida en el hijo y queda en case.json. Se retira el temporal al acabar;
el directorio del resultado sigue siendo exclusivo. Cambios posteriores no alteran
las entradas del proceso ni su identidad. El resultado abierto mantiene siempre
su procedencia aunque cambie el selector de la próxima ejecución. Si cambian las
entradas o archivo activo, aviso de configuración anterior sin borrar/recalcular.

Resultados de proyecto: mismo formato/nombres/unidades/model_version, versión 2.
`inputs` incorpora `origin` (kind=project, project_name, source_path o null, dirty),
`project_snapshot` v5 completo, `port_mapping`, `scenario_identifier`; conserva
case/variant/profile/model_version/initial_state. Referencia sigue escribiendo y
leyendo versión 1, origen implícito reference, exactamente reference_inputs().
El lector v2 reconstruye entradas esperadas desde la copia validada y condiciones
fijas; compara contrato íntegro, no confía en parámetros arbitrarios. Además de
hashes/dominio/unidades/estado/convergencia, verifica volúmenes y flujos de las
muestras contra Model evaluado en esos estados, sin integrar de nuevo. Reabrir no
depende de la existencia del proyecto original. B se usa en GUI; C solo se admite
en contrato para la comprobación de consola autorizada mediante --profile-c-check.

Protocolo nuevo, separado de la serie histórica: pruebas de adaptación/contrato/Qt
antes de A (editor, geometría exacta de referencia, B/100), B (copia, solo compresión
8→8,2, editor B/100) y C (misma geometría, consola C/100). Topes previos intactos:
60 s, 30 ciclos, 512 MiB, 2 millones RHS, mínimo 0,001°, ocho rechazos y dominio;
hasta 180 s para estos tres cálculos completos. Comparación A/referencia numérica,
no tiempo. Contraste B/C utiliza las magnitudes/pisos existentes, 1 % relativo
y 0,005 absoluto para Y, sin atribuir tendencia de tres perfiles. Ninguna otra banda,
barrido, búsqueda o tolerancia nueva. Fallos se informan sin reparación automática.
Windows visible/captura y pruebas automáticas se distinguen de aceptación manual.
Tras acreditar el recorrido se registra implementación del alcance acotado,
sin archivar ni iniciar otra entrega; la publicación pertenece a la usuaria.

## Fuentes primarias consultadas — 15/09/2026
[1] [MIT, Control volume form of the conservation laws](https://web.mit.edu/16.unified/www/FALL/thermodynamics/notes/node19.html):
balances abiertos y transporte de entalpía; justifica signos, no coeficientes del caso.
[2] [MIT, Specific Heats](https://web.mit.edu/16.unified/www/FALL/thermodynamics/notes/node18.html):
cierre u(T)/h(T) y adiabática ideal; propiedades constantes son aproximación propuesta.
[3] [NASA Glenn, Mass Flow Choking](https://www.grc.nasa.gov/www/k-12/BGP/mflchk.html):
flujo isentrópico compresible y límite sónico; ramas en razón de presiones obtenidas
por sustitución de relaciones isentrópicas. No proporciona nuestros Cd.
[4] [Krieger, Booy, Myers y Uyehara, SAE 690135](https://doi.org/10.4271/690135):
se consultó únicamente el resumen público del editor, no el texto de pago. Precedente
de sistemas termodinámicos acoplados, flujo por restricciones y repetición de ciclos;
no se copian láminas, ajuste experimental, dos zonas ni contratos de su implementación.
[5] [MIT 2.61, Lecture 8: Intake and exhaust processes](https://ocw.mit.edu/courses/2-61-internal-combustion-engines-spring-2017/6ec38b3fc5493e328115e0a49a565f35_MIT2_61S17_lec8.pdf),
páginas 5–6 y 9 del PDF: distingue inercia/sintonía, retorno/estrangulamiento y
límites de barrido ideal. No se adoptan los ejemplos ni factores de sus figuras.
[6] [Vannik, EngMod2T — Outputs Degree Based](https://vannik.co.za/EngMod2T%20-%20OutputsDegree.htm):
la documentación del fabricante identifica ondas viajeras/reflejadas y pulsos de
retorno; referencia de capacidad que nuestra reducción no representa, no aval del modelo.
Las leyes de calor, topología reducida, parámetros sintéticos y tolerancias son
**decisiones propuestas aquí**, no resultados publicados ni recomendaciones de esas fuentes.
