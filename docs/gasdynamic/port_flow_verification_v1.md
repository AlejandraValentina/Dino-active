# Verificación focal de flujo de lumbreras V1

2026-10-28. Petición del dueño: decidir CORREGIR / CONSERVAR / INDETERMINADO,
sin ampliar esta intervención a mallas, RPM, MUSCL, Desktop ni otros cierres.
Este documento añade un alcance; no cambia el contrato congelado P3-R1.

## Hipótesis y pregunta decisoria

R1 representa un problema de Riemann entre dos estados Euler, uno de ellos
estacionario y homogéneo. No representa por definición una tobera entre un
depósito de remanso y una sección de conducto. Multiplicar su flujo por Cd*A
no introduce las ecuaciones de aceleración hasta una garganta, su presión ni
la relación entre área de garganta y sección del conducto.

Una diferencia frente a una fórmula de orificio con dos depósitos quietos no
prueba por sí misma un defecto: el estado inmediato del conducto y sus ondas
no son un segundo depósito prescrito. La comprobación decisiva será un estado
de conducto compatible con una solución analítica de tobera, además del control
de Riemann exacto para separar diferencias de cierre del error aproximado HLLC.

V1 y V2 ya existen. V1 supone expansión separada y tiene límites de dominio;
V2 supone tobera ideal equivalente, con choque normal admisible. Se reutilizará
V2 si supera sus referencias; no se creará otro modelo ni se cambiará el default.
El área efectiva no identifica por sí sola las pérdidas de una lumbrera real.

## Ensayo fijado antes de ejecutar

1. Matriz algebraica con gamma=1.35, R=287 J/(kg K), sección 1e-4 m²,
   áreas geométricas relativas .025/.1/.5/1 y Cd=.65/1 aplicado una vez.
   Construcción analítica independiente por continuidad y entalpía total:
   Mach de garganta .01/.3/1, cámara donante a 200 kPa/900 K o conducto
   donante a 200 kPa/300 K de remanso, ambas normales. Incluir entrada
   supersónica expandida compatible y presiones arbitrarias con velocidad
   inicial cero para mostrar explícitamente la diferencia entre problemas.
2. El candidato debe reproducir los flujos analíticos de masa, momento,
   energía y marcador a error relativo <=1e-9; simetría de orientación;
   flujo de energía por masa igual a entalpía total del donante. Los cuatro
   componentes extensivos se comprueban en el ensayo dinámico y en el motor.
   El cierre Riemann legacy se mide, no se fuerza a pasar la referencia tobera.
3. Cámara finita conectada a un conducto de ocho celdas por una restricción
   .1 de la sección, extremos externos cerrados, volúmenes fijos, sin fuentes
   térmicas ni químicas. Presiones cámara/conducto 200/100 y 100/200 kPa,
   300 K, 50 microsegundos, dt=1 microsegundo: legacy y V2, primer orden.
   Verificar flujos de ambas etapas, inventarios por especie, masa y energía
   con residuos relativos <=1e-9; restauración y siguiente paso exactos.
4. Sólo si pasa la referencia: reutilizar el diagnóstico integrado existente
   `diagnose_integrated_port_v2.py`: A9000 desde el mismo estado inicial, dos
   revoluciones por ley, 0.5 grados nominales, primer orden espacial. Cambia
   exclusivamente el selector físico y su versión de configuración.
   Registrar entradas/salidas brutas, flujos netos, presiones, composición
   atrapada al cierre, residuos y coste. Es transitorio, no potencia periódica.
5. Reejecutar los tests focales existentes de los candidatos, integración e
   invariancia legacy y la regresión P4–P8. Ningún umbral se modifica.

Presupuesto: <=120 s para algebra y cámara/conducto; <=240 s por diagnóstico
integrado (dos casos, sin extensión); <=100 MiB por caso integrado y 10 MiB
de resúmenes, con preflight y reserva de 2 GiB antes de escribir. Los tests
tienen timeout independiente de 300 s. Ante fallo, conservar checkpoint y
localizarlo; no continuar automáticamente a otra campaña.

## Regla de decisión y límites

CORREGIR significa que el uso de R1 como ley de restricción falla una referencia
física pertinente y que una implementación experimental explícita la reproduce.
No significa que V2 haya identificado las pérdidas, separación o Cd de una
lumbrera real, ni que mejore la predicción de potencia. Si V2 ya está implementada
y supera los controles, se conserva esa integración; no se duplica código.

CONSERVAR requiere que no se demuestre la deficiencia en el alcance evaluado.
INDETERMINADO corresponde a evidencia insuficiente para esa decisión. La
selección/calibración de pérdidas reales puede seguir indeterminada aun con una
deficiencia de cierre demostrada. HLLC interior y R1 para su contrato original
permanecen. No hay promoción del candidato a rc7 ni al default actual.

Fuentes primarias de las relaciones analíticas:
[NASA: caudal y estrangulamiento](https://www.grc.nasa.gov/www/k-12/BGP/mflchk.html)
y [NASA: choque normal](https://www.grc.nasa.gov/WWW/k-12/airplane/normal.html).
Supuestos: gas ideal caloríficamente perfecto, flujo adiabático cuasiestacionario
en la restricción; segmentos isentrópicos salvo choque explícito. No se usa
la potencia de ningún motor como referencia o calibración.
