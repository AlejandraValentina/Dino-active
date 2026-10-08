## Alcance y definición previa
Etapa P1_R1_SCIENTIFIC_AMENDMENT. Se conservan método, EOS, CFL0.4, IC,
BC, tiempo y referencia exacta de Sod. Se evalúan N200/400/800/1600; N400
sigue siendo la única malla contractual. Ninguna edición de P1 v1.

A reproduce el máximo de diferencias de Y dividido por distancia entre centros,
ubicado en su punto medio, con ventana histórica ±0.05 alrededor del exacto.
B busca en todo el dominio un único cruce Y=0.5 interpolado linealmente; igualdad
en un centro cuenta una vez, meseta en0.5 es ambigua. No usa el exacto ni clipping.
C pondera los puntos medios por |deltaY| en ventana fija ±0.05 centrada en B.
D usa el máximo gradiente de densidad en esa misma ventana para excluir el shock.
Es independiente en el campo medido, no en la localización de la ventana; diagnóstico
solamente. No elegir la métrica con menor error. Se comprueba monotonía descendente
sin tolerancia en la ventana de B. Se registran los cuatro sobre el mismo array.

Microcaso puro independiente: dominio[0,1], área1, R1/gamma1.4; discontinuidad
inicial0.25, izquierda(rho,u,p,Y)=(1,1,1,1), derecha=(2,1,1,0), fronteras fijas,
tfinal0.25 y posición exacta0.5. Mismas cuatro mallas, FE/HLLC/CFL0.4. No se
altera T06 ni se atribuye su aceptación al microcaso. Referencias promediadas
conservativamente mediante el integrador existente. L1 de rho,u,p sin escala.

Máximo180s por integración,1500s para estudio, cero reparaciones automáticas.
Hashes antes/después para P1/0D/gas1d. Los contadores HLLC previos no se certifican;
HLLE se registra crudo. No corregir su instrumentación bajo esta orden salvo gate.

Si B falla en N400: P1_R1_CONTACT_ACCURACY_UNRESOLVED y STOP. Sin R1 adoptado,
sin fixes P2, T05 ni nueva campaña P2A. Si aprueba, aún requiere revisión específica
y el resto de condiciones antes de cambiar únicamente A→B en versión separada R1.
