# P4-R1: observables fijados antes de nuevas integraciones

Orden 47e73e41, 2026-09-21. Baseline 21c9a5b. Sólo diagnóstico y
postproceso; implementación y evidencia histórica congeladas por
`p4_r1_frozen.json`. No cambia el gate P4 ni habilita P4C/P5.

## Descarga y definición histórica

Caso canónico P4: tubo recto L=0,6 m, diámetro20 mm; cámara fija 0,0001 m³,
300000 Pa,600 K,Y=0,8; tubo100000 Pa,300 K,Y=0,2,u=0. Puerto geométrico
canónico S2T, Cd=1, RPM3000; ángulo80→300, t=0→220/18000 s. Exterior
no reflectivo explícito congelado. N100/200/400, CFL0,4.

Qp histórico = sum(dt_j * |p_j - 100000 Pa|), presión al final de cada paso
aceptado, rectángulo derecho, sin normalización, Pa·s. Sensor solicitado0,1 m,
pero centro más cercano real0,099/0,1005/0,09975 m: defecto espacial probado.
Qm histórico = sum(dt_j/2*(mdot_stage1+mdot_stage2)), kg, signo positivo hacia
la cámara, negativo en descarga. Es el ledger del esquema, no sampling externo;
se contrasta con m_final−m_inicial y se normaliza el residuo por masa inicial
total cámara+tubo. La ventana física sí es idéntica. No se sustituyen históricos.

## Observable corregido (única elección, anterior a los resultados)

Sensor x*=0,1 m en todas las mallas. Sean x_i<=x*<x_(i+1) los centros vecinos,
alpha=(x*−x_i)/(x_(i+1)−x_i). p*=(1−alpha)p_i+alpha p_(i+1).
Se solicitan ambos centros mediante el logging ya existente, sin cambiar solver.
Se verifica que las posiciones devueltas sean exactamente las solicitadas.
Se incluye t0 (estado numérico inicial) y todos los extremos de pasos aceptados.

Qp = integral de |p*(t)−100000| en la ventana completa, usando interpolación
lineal temporal entre muestras. Para a,b desviaciones consecutivas:
si ab>=0, contribución dt*(|a|+|b|)/2; si ab<0,
dt*(a²+b²)/(2*(|a|+|b|)). El cruce de cero se integra exactamente.
La integral firmada trapezoidal también se conserva como diagnóstico.
No se deciman muestras antes de integrar. Independiente de exportación/gráfica,
no de dt numérico: esa dependencia se mide con CFL. Qm conserva su definición.

Llegada: primer cruce ascendente interpolado de102000 Pa; CA=80+18000t.
Apertura90° (10/18000 s), cierre270° (190/18000 s), eventos exactos del solver.
Candidato poscierre: primer máximo local después del cierre con prominencia
>=2000 Pa respecto del mínimo desde el cierre. No identifica causalmente una
reflexión; null significa no identificado, no ausencia de ondas. Ventanas fijas;
se examina señal completa y sus extremos para detectar truncamiento de fase.

## Secuencia y clasificación previa

Repetir nominal100/200/400 porque faltan series de vecinos en los históricos.
CFL diagnóstico0,2 en200/400. Para cada Q, ratio=|Q_N,.2−Q_N,.4|/D200_400:
<=0,1 pequeño; >=0,5 comparable; intermedio inconcluso. Son etiquetas del
diagnóstico, no nuevos gates P4. Comparable o inconcluso detienen N800 con
SPACE_TIME_COUPLING_UNRESOLVED; sólo comparable acredita contaminación medida.
No cambiar CFL productivo. Diferencia espacial cero: sólo cambio temporal cero
se considera pequeño; de otro modo comparable.

Control E06 equivalente: tubo recto0,75 m/20 mm, cámara100kPa/300K/Y0,2,
puerto fijo expuesto200 mm² durante180→234° (0→0,003 s). Pulso gaussiano
dp=100 exp(−((x−0,08)/0,015)²) Pa, rho=rho0+dp/a²,u=dp/(rho0*a),Y0,2,
a=sqrt(gamma*R*300). Misma inicialización por integrales de celda canónica.
Mallas100/200/400, mismo sensor físico, llegada al cruce100050 Pa.
Referencia lineal p=100000+100 exp(−((x*−a*t−0,08)/0,015)²).
L1 temporal/(100 Pa*0,003 s) debe disminuir y área permanecer constante para
considerar convergencia diagnóstica del control. No demuestra ondas fuertes;
masa neta casi cero se informa sin cocientes relativos inestables.

Sólo tras temporal pequeño y control convergente: N800 nominal, límite900 s
para esa integración; otros casos600 s. Sin reintentos automáticos. Si timeout,
conservar parcial fuera de la secuencia de Q completos, perfilar sin optimizar.
Preasintótico confirmado exige ambos D400_800<D200_400, diferencia de llegada
400→800 menor que200→400, conservación/admisibilidad/CFL PASS. En otro caso
convergencia espacial no resuelta. Sin Richardson cerca de shocks.
Los fallos numéricos se distinguen de infraestructura en checks y estado.

Revisión independiente de sólo lectura antes y después. Ningún resultado de
este diagnóstico acepta P4 ni modifica su contrato histórico.
