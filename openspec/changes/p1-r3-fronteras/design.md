## Revisión conceptual previa a cualquier cambio de código
P1 matemático líneas78–100 ya distingue open (reflexión−1), nonreflecting
(reflexión0) y reservoir (totales en entrada). T05 usa Boundary('open'), no
Boundary('nonreflecting') en el extremo derecho. Por tanto NO hay una simple
confusión de nombres ni se está midiendo−1 sobre una BC no reflectiva.

Sí existe mezcla de cierres: open impone p_b=p0 para la prueba acústica, pero
conmuta K/Y interior→reservorio cuando cambia el signo. Las dos fórmulas pueden
no tener solución consistente. La evidencia70dígitos anterior sitúa J+ entre
2a_ext/(gamma−1) y2a_out/(gamma−1): w_out<0 y w_in>0. No es un error puro
de implementación ni lo resuelve corregir precisión. La separación adicional
necesaria es pressure-release acústica frente al cierre material del reservorio.
Esto justifica R3 dentro del delta autorizado; no se afirmará que P1 nunca
distinguió nonreflecting/open, ni se relaja el valor/toleranciaT05.

## Derivación acústica
Coordenada normal saliente, w=n*u; base en reposo, Z0=rho0*a0.
Perturbaciones satisfacen p'_t+rho0*a0²*w'_s=0,
w'_t+p'_s/rho0=0. j+=w'+p'/Z0 (onda saliente),
j-=w'-p'/Z0 (entrante). w'=(j++j-)/2, p'=Z0*(j+-j-)/2.
Presiones de ondas: p_inc=Z0*j+/2, p_ref=-Z0*j-/2.
Pared: w'=0 ⇒j-=-j+ ⇒Rp=+1; velocidad reflejada opuesta.
Pressure-release: p'=0 ⇒j-=j+ ⇒Rp=-1; velocidad resultante no nula.
No reflectiva: j-=0 ⇒p_ref=0, no se prescribe−1.
Fuente primaria para el sistema/eigenestructura:
https://www.clawpack.org/riemann_book/html/Acoustics.html

## Cierre específico ideal_open_pressure_release
Alcance: pequeña perturbación acústica subsónica, no reservorio general ni
radiación física. Prescribir SOLO p_b=p0>0. Continuación isentrópica y de
trazador de orden cero: K_b=K_i=p_i/rho_i^gamma y Y_b=Y_i para ambos signos.
La continuación de K/Y durante el pequeño retorno acústico es explícitamente
parte de este nuevo cierre ideal; no se presenta como donante de un reservorio.
rho_b=(p0/K_i)^(1/gamma), a_b=sqrt(gamma*p0/rho_b),
w_b=w_i+2*(a_i-a_b)/(gamma−1), u_b=n*w_b.
El estado conserva J+ y p_b; E se deriva de EOS, flujo físico Euler del estado
de cara multiplicado por área una sola vez. Sin ghost ni nuevo Riemann solver;
los flujos interiores HLLC/HLLE y ledger compartido se conservan.

No rama por signo microscópico, epsilon, mezcla ni imposiciónw=0. Para evitar
cancelación en a_i-a_b se puede evaluar la identidad exacta
w_b=w_i-2*a_i/(gamma−1)*expm1((gamma−1)/(2*gamma)*log1p((p0-p_i)/p_i)).
Validar EOS/rho/p/T/Y y régimen subsónico; fuera del alcance fallar, no extrapolar
esta idealización a una BC general. Conservación por el mismo flujo de cara,
no por imponer inventarios constantes en un dominio abierto.

Nonreflecting conserva J-_base externo explícito y J+ interior; K/Y del
donante según signo como en contrato original. BASE se declara en las
definiciones de tests, nunca se deduce circularmente del interior.
Reservoir conserva totales/h0/K0 en entrada y presión estática/Kinterior en
salida; no se cambia su implementación ni se valida P3 medianteT05.
Closed/T04 sin cambios.

## Protocolo fijado
T05: BCderecha nueva; todo lo demás original. Mallas200/400 diagnósticas,
800contractual. Mismo pulso10Pa/centro.3/ancho.04, sensor.7, tf1.15L/a0,
muestreo.001L/a0, CFL.4, ventanas incidente[.30,.50],reflejada[.90,1.10].
T05N800 exige amplitudinc>=5Pa, |Rp+1|<=.30,Rp<0,errorpico<=.02L/a0,
ledger<=1e-10 y estados admisibles. En200/400 registrar signo y métricas sin
inventar criterio de convergencia ni trasladar obligatoriamente el gateN800.
NR01: idéntico pulso/sensor/ventanas/tf/N800 queT05, ambas BCnonreflecting
con baseexternaBASE. Medir Rp firmado y |Rp|; sin nuevo umbral acústico.
P1/T03 tiene métricas de propagación, no una cota de reflexiónNR01.
Por caso límite120s solver; fase800s, cuatro integraciones previstas.

Solo revisión conceptual aprobada habilita implementar. Solo R3/T05PASS,
contadores correctos y NRconsistente habilitan campaña P2A completa. T08
equilibrio/source y T12positividad no se reparan inventando nuevos métodos:
STOP científico si el contrato no se satisface y no hay bug concreto.
Una reparación P2 previa de3 consumida; R3es enmienda científica, no reparación.
Sin P2B antes de P2A completoPASS, sin P3/UI/0D/paquetes ni publicación.
