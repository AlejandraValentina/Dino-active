## Diseño vigente R1
La orden38a85593 sustituye la interfaz reservoir por Riemann estancado0D y fija
la secuencia R1→P3B(C01–C07)→P3C(C08–C12)→adaptador de estado.
Definición, fixtures congelados, criterios y referencia acústica vigentes en
docs/gasdynamic/0d_1d_coupling_r1.md. La interfaz de producto no se conecta.
El diseño inicial que sigue conserva el antecedente del bloqueo; no gobierna
el cierre R1 ni altera los contratos P2 históricos.

## Contrato y secuencia inicial (histórico)
La aceptaciónP2 se registra separada, con hashes del núcleo y contratos vigentes.
Primero auditar la frontera reservoir existente antes de integrar un volumen
finito: P1 exige usarla en entrada y presión receptora/entalpía del donante en retorno.
Sin cambiar boundary.py, ni crear otro cierre para ocultar incompatibilidades.
P3A exige equilibrio/descarga/llenado/inversión/composición; sólo tras PASS,
P3B volumen finito constante; sólo tras PASS, P3C V(t). Adaptador productivo al final.

## Interfaz única
Estado0D=(m,U,F), V>0, U energía interna; rho=m/V,T=U/(m*cv),
p=(gamma-1)*U/V,Y=F/m. EOS común, sin clipping, sin momentum0D.
Reservoir p0,T0,Y0, normal n hacia afuera del tubo; usar face_state una vez
para obtener w_b=(rho,u,p,Y), luego flujo Euler por área A una vez:
G=A*(rho*u, rho*u*u+p, u*(rho*E+p), rho*u*Y).
F_out=n*G. El tubo recibe -dt*F_out; 0D recibe los componentes0,2,3
con +dt*F_out. Registrar impulso axial, sin inventar estado momentum0D.
Energía transportada m_dot*(cp*T+u²/2), no m_dot*cv*T.
Entrada desde cámara: H=cp*T0; retorno: H del donante1D de cara.
No sumar de nuevo p*u*A. Trabajo -p*dV separado para volumen variable.

## Integración prevista, condicionada
CFL1D limita dt global; SSP-RK2 evalúa flujo compartido en cada stage sobre
ambos estados de ese stage. Pesos1/2 para flujos/ledgers, rollback conjunto
ante inadmisibilidad, sin clipping ni limiter nuevo. No usar RK4 histórico.
El núcleo existente permanece byte a byte congelado; extensión aislada fuera
de gas1d para no alterar su inventario verificado.

## Preflight de reversión
Antes de P3A: p_pipe=p0=100000Pa,T0=300K,Y0=.8,Y_pipe=.2,
T_pipe=299,300,301K; normal+1/-1; velocidad normal w=0,±10^-3,
±10^-6,±10^-9 m/s. Son estados subsónicos estrictamente admisibles.
Referencia: existencia de una rama física del contrato y continuidad al pasar
por reposo sin deadband. No ajustar tolerancia: estudiar límite w→0 de la
fórmula y registrar resultados exactos. Si no existe raíz de entrada ni rama
consistente de salida, SCIENTIFIC_CHANGE_REQUIRED; no implementar otra BC.

## C01–C12 (gates posteriores, no acreditados por preflight)
Todos requieren inputs congelados antes de ejecutar; balances<=1e-10 y
admisibilidad estricta segúnP1. Los casos no ejecutados conservan NOT_RUN.
| Caso | Inputs / referencia | Observable, métrica y criterio |
|---|---|---|
| C01 | p=100kPa,T=300K,Y=.3,u=0,V=.01m3,A=.01m2,L=1m; equilibrio | Flujo nulo y drift normalizado<=1e-12 |
| C02 | Cámara120kPa/tubo100kPa,T300K,Ycam.8/Ytubo.2 | Masa/energía cámara disminuyen; onda compresiva hacia tubo, ledger<=1e-10 |
| C03 | Cámara80kPa/tubo100kPa,T300K,Ycam.8/Ytubo.2 | Masa/energía/presión cámara aumentan, donor tubo, ledger<=1e-10 |
| C04 | Flujo inicial hacia tubo y extremo cerrado; reflexión | Ambos signos y tiempo de inversión, rama continua sin selector nuevo |
| C05 | C02 | FlujoF=flujoM*Ydonor a precisión relativa1e-12 |
| C06 | C03/C04 | Mismo criterio por stage al retornar, sin mezclar receptor |
| C07 | Cámara+tubo cerrado,Vfijo | Inventariosm,U+E,F y residuos<=1e-10 |
| C08 | V(t) prescrita suave, sin motor | Ledger incluyendo integral-p*dV<=1e-10; comprobación adiabática aislada |
| C09 | Pulso pequeño dirigido a cámara | Respuesta de presión0D no nula; reflexión/transferencia por refinamiento, sin coeficiente impuesto |
| C10 | N40/80/160, mismos datos y tiempo | Diferencia fina/intermedia menor que intermedia/gruesa, variablesm/U/F/p |
| C11 | CFL.2/.4/.6 | Todos gates de conservación/admisibilidad, refinamiento de diferencias, sin cota ajustada |
| C12 | Todos anteriores y estados inválidos | Estricta positividad y0<=Y<=1, rechazo conjunto sin clipping |
Los parámetros temporales/onda de C04/C08–C11 requieren congelación antes de
esas ejecuciones, nunca selección posterior. Si el preflight bloquea, no se
inventan resultados ni se presenta esta tabla como campaña ejecutada.

## Revisión R1 autorizada
Orden38a85593 sustituye el cierreP3 reservoir por problemaRiemann con W0D
estacionario; docs/gasdynamic/0d_1d_coupling_r1.md define delta, energía y gates.
El bloqueo anterior se conserva histórico. Ninguna BC P2 cambia. P3B sólo tras
C00/C00B, auditoría de flujo y revisión independiente PASS.
