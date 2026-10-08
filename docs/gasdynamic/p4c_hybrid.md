# P4C: configuración fijada antes de integrar

Ruta aislada `2T_0D1D_EXHAUST`; ninguna importación desde UI/JSON/legacy.
S2T-0D-01 canónico, 3000 RPM, inicio 180°, estados I/K/C originales. El tubo
arranca con el estado E original: 100 kPa, 500 K, Y=0, u=0. Exterior explícito
idéntico al reservoir E: misma BC no reflectiva P4; no cambiar su formulación.
I/K/transferencias, trabajo y calor reutilizan Model (banda exterior 100 Pa).
Se enmascaran exclusivamente C–E y E–exterior reemplazados por el escape 1D.
No hay volumen E ficticio en los inventarios.

## Malla y coste

G1 y G2 reutilizan `p4_waves.segments('straight'/'chain')`: recto .75 m/20 mm;
cadena .2 m/20, .15 m/20→40, .05 m/40, .15 m/40→20, .2 m/20.
Sólo cambia el escape; condiciones iniciales uniformes idénticas.
dx objetivo=.003 m: G1 N250, G2 N251 (redondeo por segmentos).
Es la resolución espacial N200 del blowdown .6 m; respecto de N800, sus
diferencias son Qp 0.04144%, Qm 0.004045%, llegada 2.86227 µs (0.05152°).
Es más fina que N200 del banco débil .75 m. No acredita convergencia del motor.
El blowdown costó aproximadamente 18/71/287/1139 s en N100/200/400/800;
no se toma N800 para el motor ni se reduce N después de observar el coste.

Presupuesto P4 de **600 s por configuración**, máximo **30 ciclos**, mínimo5
y tres comparaciones consecutivas aprobadas (límites de ciclos legacy).
Medir primero un ciclo G1. Proyección conservadora =30×tiempo medido del ciclo,
incluido postproceso de trazas. Si supera600 s, STOP `P4_BLOCKED_PERFORMANCE`:
sin G2, campaña multiciclo, nuevos timeouts ni remallado oportunista.
Si aprueba, continuar hasta periodicidad/límite dentro600 s; aplicar el mismo
guard al primer ciclo G2. Una interrupción numérica prevalece como bloqueo
numérico, no se presenta como medición de un ciclo completo.

## Adaptación del calor sin cambiar solvers

SSPRK2 conjunto, CFL=.4, HLLC/P3/puerto/P2/P4 congelados. Dividir únicamente
en fronteras aceptadas 180→350→390→540°, repitiendo fase cada revolución.
Durante aporte cerrado integrar S_C=F_C+F_inicio b(theta), constante. El estado
físico F_C=F_inicio(1−b) se obtiene con `Model.analytic` original en cada etapa.
Verificar que todas las conexiones del cilindro estén cerradas y S no cambie.
Al final del segmento convertir a F físico. El ledger físico de especie resta
la misma cantidad analítica quemada al inventario y al término externo.
No clipping. El calor en energía usa la cuadratura SSPRK2 de la fuente original;
registrar por separado su diferencia con la primitiva q_fresh F_inicio b.
La revisión independiente previa aceptó esta adaptación bajo esas condiciones.

## Periodicidad fijada antes de ejecutar

Comparar ciclos consecutivos completos. Curvas a igual fase, interpolación
lineal sobre malla común 180.5:0.5:540° (soporte aceptado comprobado). Delta máximo de presión dividido por
máxima presión absoluta de ambos ciclos <=.005, tanto C como cada sensor.
Trabajo: |Wn−Wprev|/max(|Wn|,|Wprev|,1 J)<=.005. Masa de puerto:
|Qmn−Qmprev|/max(|Qmn|,|Qmprev|,masa C inicial)<=.002.
Inventarios finales I/K/C: m/U relativos <=.002; Y absoluto <=.002.
Inventarios integrados del tubo: m/E relativos <=.002, F normalizado por masa
<=.002. Deben cumplir todos, en tres comparaciones consecutivas a partir del
ciclo5; máximo30. Sin resultado periódico, E13 no PASS.

## Auditoría y observabilidad

E12: sumas I/K/C + celdas1D, exterior I y salida1D, calor, trabajo y quema.
Puerto es interno. Residuo normalizado <=1e-10, global y por etapa; especie
normalizada por masa inicial. Registrar ledger físico y transformado separados.
E15: validación0D original y EOS1D en todas las etapas, sin clipping; mantener
las validaciones estrictas de los kernels congelados, reportar extremos.
Registrar trazas completas de etapas y aceptados, flujos y trabajo acumulado.
p_port/Mach son la cara reconstruida de la segunda etapa; flujos son promedio
SSPRK2, no confundirlos con evaluación puntual del estado aceptado final.
Sensores p/u/Mach/Y por paso; p/u/T/Y/Mach completos en snapshots, con T=p/rhoR
del estado real. Guardar posiciones efectivas y arrays completos del tubo.
W/P/par son diagnósticos indicados de un ciclo, no prestaciones convergidas.

E14 requiere G1/G2 y causalidad espacio-temporal blowdown→geometría→puerto,
no una separación acústica lineal aplicada al pulso fuerte. Si el guard impide
G2, onda de retorno/comparación/periodicidad permanecen pendientes; no se
deducen de un pico aislado G1. No checkpoints reanudables ni promesa de resume.
