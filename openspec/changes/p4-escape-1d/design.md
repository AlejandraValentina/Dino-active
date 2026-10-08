## Contrato IDEAL_PORT_BASELINE
Área geométrica existente: uncovered_area(width,height,piston_position-top),
mm²→m². Aeff=min(Aport,Apipe), Cd=1. Geometría sintética S2T-0D-01 intacta.
Cara totalG=G_P3(Aeff)+(Apipe-Aeff)*(0,p_wall,0,0), p_wall de RiemannparedP2.
Cámara recibe componentes0,2,3 de outwardP3; tubo recibe flujo total.
ReacciónP3 y fuerza sobre paredcerrada separadas; no momentum0D ni trabajo
axial artificial. Aeff0 bypassP3 (no área0 inválida), paredP2 completa exacta.
No deadband. Continuidad para estados finitos y leygeométrica continua.

Usar reconstrucciónP2 con ghostinterior(outflow) sólo para pendiente de primera
celda: minmod=0 en esa celda, sin imponerBCfísica allí. Así la reconstrucción no
salta al abrir/cerrar; fluxfísico real lo define cara dividida. RestoMUSCLP2.
SSPRK2 conjunto, recálculo de0D/puerto/1D porstage, CFLP2 y eventosexactos.
Geometría1D fija, fuente p*dA P2; trabajo0D -p*dV aparte.

## Frontera exterior congelada
nonreflecting con estado explícito exteriorp100kPa,T300K,Y0,u0 para bancos;
truncamiento característico ideal lineal/local, NO radiaciónreal/anecoica general.
Revisión detecta salto de presión al cambiarKdonante en backflow con distinta
entropía: registrar preflight. No cambiarBC. Si afecta campaña o se necesita
otra semántica: P4_BLOCKED_EXHAUST_BOUNDARY/SCIENTIFIC_CHANGE_REQUIRED.

## Secuencia
P4A puerto/banco; P4B ondas/geometría/refinamientos; P4C sólo después ambosPASS.
Definir inputs/métricas antes de cada banco, sin ajustarcriterios a resultados.
Máximo600s por prueba, rollback conjunto, sin clipping ni limiternuevo.
P0/P2/P3 se conservan byte a byte; ningún import productivo del camino nuevo.

## P4A fixtures fijados antes de ejecución
Tubo recto .6m/20mm,N100,CFL.4, gasR287/gamma1.35, estado100kPa/300K/Y.2/u0;
cámara V.0001m³,Y.8, puerto canónico32/10/20mm, carrera56/biela100mm,RPM3000.
E01: cámara100kPa/300K,CA0→40; driftp<=1e-12 y m/U/F cámara exactamenteidénticos.
E02/E03/E04: cámara300kPa/600K,CA80→300; primerflujoabierto saliente, m/U
finalesmenores, presiónsensor.1m supera101kPa, flujoexacto0 trascierre.
E05: cámara80kPa/300K,CA80→145; m/U aumentan, especieentrante usaYcaratubo
(errorabsoluto<=1e-12), noYatmósfera. Todos balancesglobales/stages<=1e-10,
CFLporstage<=solicitado, eventosalcanzadosexactos, rho/p/T>0,Yen[0,1].
Sensores.1/.3/.5m registranp,u,M,Y. Llegada umbral1%contrasteprescrito;
refinamiento y contrastevelocidadlocal se evalúan en P4B, noacreditadosaquí.

## P4B fixtures y criterios previos
Pulsoacústico100Pa, x0=.08m, sigma=.015m, base100kPa/300K/Y.2; u'=p'/Z,
rho'=p'/a². Cámara100kPa/300K/Y.2,V.0001m³, CAinicial180,RPM3000,tf.003s.
Grecto .75m/20mm. Difusor: header.2m/20,cono.15m20→40,resto.4m/40.
Convergente: header.2m/20,cono.15m20→10,resto.4m/10.
Cadena: header.2/20,difusor.15/20→40,belly.05/40,baffle.15/40→20,tail.2/20.
Longitud: header.3m/restoigual; controlisovolumen header.3/tail.1, restoigual.
Nobjetivo100 vía dx=.75/N; extremos de segmentos coinciden con carasP2.
Refinamientos100/200/400 para difusor y blowdownP4A; CFL.2/.4/.6 enN100.
RPM2500/3000/3500 misma cadena/pulso; fase inicial180, leygeométricaidéntica.

Señalreflejada en sensorcercano.05m: pr=(p-p0-Zu)/2. Separación lineal válida
sólo para100Pa, no imponerla a blowdownfuerte. Ventanaretornopredefinida desde
(2Lheader-x0-xs)/a−3sigma/a hasta +2Lcono/a. Signodifusornegativo/convergente
positivo con amplitud>1Pa; rectoreflejoinvoluntario<=2.5Pa. Arrivalcruce1Pa
interpolado, errorrespectocentrodepaquete<=3sigma/a+2dx/a; no ajuste a datos.
ControlL: deltaarrival=2*.1/a dentro3dx/a; controlisovolumen Vigual relativo1e-12.
GateRPM: tiemposfísicosdentro2dx/a y ángulosretornocrecientes conRPM.
Refinamiento: diferencias400–200 menores que200–100 paraarrival,integral|pr|dt
(o presiónperturbada enblowdown) e intercambiomasa. No exigirorden2 en shocks.
CFL: spread/maxabs<=.025 paraesas3métricas; criteriofocal delbanco, no modificaR5.
Blowdown: arrivals entre sensores.1/.3 a102kPa; delta_t acotado por distancia/
max,min(u+a) positivos de todos los estados locales muestreados en snapshots, margen2dx/a0. Es verificación de
tiempo, no validación de amplitud. No interpretarP0 como igualdaddereferencia.
Todos bancos conservan<=1e-10, admisibilidad/CFL/eventos y600s/caso.

## Alcance de interpretación al cierre bloqueado
La cota de llegada es una envolvente global de velocidades locales muestreadas,
no una trayectoria característica reconstruida. Sensores seleccionan el centro
más próximo; blowdown100/200/400 mide en .099/.1005/.09975m. Esto limita comparar
presión a ubicación exactamenteidéntica. La masa global no depende del sensor
 y también incumple el criterio; no reinterpretar el gate como error de sensor.
Los eventos físicos de puerto son90/112.2040961/247.7959039/270°. El listado
numérico además incluye0/180/360 y128.0154749/231.9845251: estos dos últimos son
particiones adicionales calculadas por el cap de entrada, que no se alcanza
porque314.159mm²>área máxima200mm². No implican una segunda apertura física.

## Delta vigente P4-R2
Sólo refinamiento blowdown sustituido por docs/gasdynamic/p4_refinement_r2.md,
versión P4_REFINEMENT_R2. Las secciones anteriores se conservan como contrato
histórico; los otros gates permanecen intactos.

## P4C antes de ejecución
Configuración, transformación de especie, malla, periodicidad y guard operativo:
docs/gasdynamic/p4c_hybrid.md. Esta definición se registra antes de medir un ciclo.

## P4-C3-R5 — contrato aprobado, instrumentación pendiente de adquisición

La aprobación humana del 2026-09-28 congela A/B0/B1/B2 bajo el recibo
`docs/gasdynamic/p4_c3_r5_preregistration_proposal.md`. La instrumentación se
mantiene fuera de las ecuaciones productivas: captura los `N+1` pares de cara,
flux vectorial completo, ondas, razón de fallback, `down`, fuente/RHS de
momentum y el estado provisional SSPRK2 por etapa. El auditor reconstruye el
esténcil MUSCL/minmod en código separado, evalúa HLLC/HLLE sobre los literales y
reproduce sólo momentum. Las identidades son exactas y están vinculadas a
Python/plataforma/arquitectura/`sys.float_info` y hashes de fuente; no hay
fallback ULP ni threshold de magnitud HLLC-vs-Exact. A selecciona internamente
el primer retorno causal positivo en la ventana preregistrada y valida el ledger
existente (`max_global_resid <= 1e-10`, solver `completed`, y `solver_time` y
`target_final_time` finitos con `solver_time >= target_final_time`). Evidencia
truncada o malformada queda `INCONCLUSIVE`; sólo un estado explícito de fallo
del solver es `FAIL`. La única corrida
focal C3-R5 autorizada queda condicionada a revisión independiente limpia;
E13/G2 y P9 permanecen fuera de alcance.

## P4-R3 computacional
La orden5e36dbe4 acepta R2/P4B, sin aceptar P4. Ciencia y referencia escalar
intactas. Perfil, bloques equivalentes y evidencia de coste en
docs/gasdynamic/p4_r3_performance.md. Resultado:
P4_R3_COMPILED_BACKEND_DECISION_REQUIRED. No modifica gates físicos ni habilita
periodicidad/G2/P5. NumPy es dependencia opcional del camino experimental.
