## Diseño previo a producción
CONSERVATIVE_STAGE_SPECIES_LIMITER experimental, separado en tools. No tocar
producción antes de aprobar. Se mantienen rhs, project, RK4 y controlador.
Los inventarios disponibles son los del estado base y del coeficiente efectivo
de construcción, NO los del estado donde se evaluó la derivada: h/2 para k1,k2,
h para k3; combinación h*(k1+2k2+2k3+k4)/6 para la salida.
La salida combina los flujos ya usados, pero necesita su propia comprobación:
preservar subetapas no garantiza por sí solo la combinación final RK4.

Primera estrategia: sumar salidas por donor; comparar h*salidas con
F_base+h*entradas. Si falta inventario, multiplicar TODAS sus salidas por el
mismo alpha<=1. Cada enlace conserva un único flujo firmado y antisymmetry.
Reservorios no tienen inventario finito. Backflow invierte donor/receptor según q.
No se cambia q ni H, ni se permite |f|>|q|. F=0 sin entradas implica salida cero.

Límite superior: f<=q NO basta. Contraejemplo exacto en reales: base donor
m=F=1, etapa evaluada con Y=.5, q=.1, h=1, sin entradas. Cualquier alpha<=1
da m'=0.9 y F'>=0.95. Reducir fresca saliente empeora F<=m. Este caso exige
rechazo; un factor puramente reductor no tiene solución bajo esas restricciones.
En el caso con entradas, limitar también las entradas al receptor a
m_candidata-F_base+h*salidas. Esto reduce flujos, no inventarios. Puede requerir
repetir límites inferiores porque reducir entradas cambia disponibilidad.
Iteración monótona acotada (64): sin solución representable, InvalidStage;
no aceptar/reparar un estado inválido. No se afirma garantía universal.

Solo activar si el candidato original viola [0,m]; sin activación se devuelven
exactamente derivadas y operaciones originales. Al corregir, reconstruir F y
su libro de enlaces desde flujos, manteniendo todas las posiciones m/U intactas.
Para redondeo se reduce alpha un ulp hacia cero y se comprueba el estado flotante
real; no se amplían tolerancias. F=m puede requerir limitar entradas; si no hay
flujo admisible que lo permita, rechazar. No imponer valores finales.
Durante calor los enlaces C están cerrados y F_C sigue su solución analítica.

Diagnóstico separado: activaciones, alpha mínimo, corrección absoluta por enlace
integrada, máximo, ángulo, ciclo, RPM, etapa, rechazos sin solución. Incluye
intentos rechazados: no equivale a masa neta alterada de la trayectoria aceptada.
En salida final, si hay reversión entre etapas se conservan los enlaces de cada
etapa separadamente, sin sustituir donor por el signo de un promedio.
Los balances independientes mantienen flujos físicos de extremos sin limitarlos:
no relajar su estándar para absorber intervención. Revisión focal independiente.

## Decisión tras ejecución
REJECT_CANDIDATE por gate de baja intervención incumplido en históricos y
campaña baja sin aprobación integral. Conservar únicamente prototipo opt-in;
motorsim/ no importa estos módulos. No se cambia integrador de producción.
Resultados y limitaciones en tasks.md; alta RPM no habilitada. La corrección
de comparación de tuplas/listas fue offline y no alteró la campaña científica.
