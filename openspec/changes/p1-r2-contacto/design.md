## Detector fijado antes de evaluar
Entrada: centros x_i y SOLO (rho_i,u_i,p_i), gamma. No Y, referencia analítica,
tiempo, ventana ni posición inicial/exacta. Se recorren todas las caras interiores.
En cada par adyacente, rho_bar=(rho_i+rho_j)/2, p_bar=(p_i+p_j)/2,
a²=gamma*p_bar/rho_bar, delta q=q_j-q_i y h=x_j-x_i.

c0 = delta rho - delta p/a²
c- = (delta p/a² - rho_bar*delta u/a)/2
c+ = (delta p/a² + rho_bar*delta u/a)/2

Estas son amplitudes en unidades de densidad de los modos característicos de
Euler linealizado alrededor de la media de la cara. Un contacto con p/u constantes
solo excita c0; las ondas acústicas/rarefacción se proyectan sobre c-/c+.
Una cara es candidata si |c0| > |c-|+|c+|: domina la contribución de contacto
sobre la suma acústica, sin parámetro calibrado. Entre candidatas se exige un
máximo global único de |c0|/h y se devuelve (x_i+x_j)/2. Si no hay candidatas
o hay empate exacto del máximo: no se detecta inequívocamente y no aprueba.
No interpolación subcelda, suavizado, recorte, tolerancia ajustada ni selección
de ventanas. Un máximo único no demuestra que un perfil arbitrario tenga un
solo contacto; el alcance es el contacto único de Sod y el microcaso definido.

Fundamento: la onda central conserva p/u y cambia rho, mientras las familias
acústicas tienen variaciones correlacionadas. Fuente primaria explicativa:
https://www.clawpack.org/riemann_book/html/Euler_approximate.html
La proyección local propuesta es un observable, NO un cambio del flujo HLLC.

## Protocolo congelado
Reevaluar los ocho arrays íntegros de P1-R1 (Sod y contacto puro,
N200/400/800/1600, CFL0.4); no es necesario reintegrar soluciones sin cambios.
Verificar hashes y conservar A/B/C y D anterior como diagnósticos separados.
D nuevo debe ser independiente, único y error<=2dx en las cuatro mallas y ambos
casos. Error absoluto no creciente al refinar (incluye error exactamente cero).
Sod contractual continúa N400, mismo EOS/IC/tfinal/L1/L2/threshold.
El microcaso es el ya fijado en P1-R1: rho1/2, p=u=1, x0=.25, tf=.25,
R1/gamma1.4, fronteras fijas, posición exacta.5 solo para comparación.
T06 conserva íntegramente su contrato de especie: rango, conservación y L1.

## Gates
Revisión independiente read-only. Si detector no independiente: NOT_INDEPENDENT;
si no cumple precisión: ACCURACY_UNRESOLVED; sin ajustar algoritmo a resultados.
Solo PASS autoriza contrato nuevo 1D_CONTRACT_V1_R2, conservando v1 byte a byte,
y los tres fixes P2. Solo PASS más T05 corregido PASS habilita T01–T12 completos.
No P2B antes de P2A PASS; no P3/0D/UI/paquetes. Máximo3 reparaciones P2.
