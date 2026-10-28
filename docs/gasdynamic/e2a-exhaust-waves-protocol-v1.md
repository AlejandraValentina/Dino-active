# E2A — protocolo congelado de ondas de escape A/B

2026-10-28. Alcance autorizado: ejecutar esta comparación y detenerse con
DIFERENCIA DISTINGUIBLE / DIFERENCIA NO RESUELTA / DEFECTO LOCALIZADO.
No cerrar precisión de potencia, periodicidad ni validación experimental.

## Configuración física única

Motor sintético funcional de 125 cc, no X30, a **9000 RPM**, desde su estado
inicial a 0° hasta 720° (dos revoluciones, sin warm start). La comparación de
señales corresponde al **segundo ciclo**; el primero forma parte del arranque,
no se elimina ni se usa un checkpoint histórico para prolongarlo.

Se usa `EQUIVALENT_IDEAL_NOZZLE_CONNECTION_CANDIDATE_V2` en A y B porque la
etapa 1 verificó ese cierre cámara–restricción–conducto. Es experimental y
supone tobera equivalente, no una identificación de las pérdidas reales. No
se cambia el acoplamiento entre diseños ni se exige reproducir las potencias
históricas legacy. HLLC interior, primer orden espacial, SSPRK2, CFL=0.4.
Fronteras exteriores **OPEN_END_PLENUM_V2**, 101325 Pa/300 K; gamma=1.35,
R=287 J/(kg K). Barrido, combustión, láminas, pérdidas y coeficientes térmicos
son los del caso fuente; no se modifican sus modelos o parámetros.

| Tramo | Largo A/B, mm | Diámetro entrada/salida, mm |
|---|---:|---:|
| 1 | **83 / 103** | 37.5 / 37.5 |
| 2 | 189 / 189 | 37.5 / 48.5 |
| 3 | 209 / 209 | 48.5 / 100 |
| 4 | 65 / 65 | 100 / 116 |
| 5 | 78 / 78 | 116 / 116 |
| 6 | 205 / 205 | 116 / 21 |
| 7 | 250 / 250 | 21 / 21 |

Largo total A=1.079 m, B=1.099 m. Los cuatro archivos completos en
`results/e2a-exhaust-waves-v1/preparation/` congelan todos los parámetros y
campos iniciales, con SHA-256 en `manifest.json`.

En B se alarga el primer tramo del caso A. Se conservan presión, temperatura,
velocidad y composición iniciales: masa y energía del nuevo volumen aumentan
físicamente. Se escala también su superficie de pared, conservando h=50 W/(m² K)
y Tw=623 K; cambia geometría, no la ley térmica. Se corrige el descriptor
redundante `pipe_sections_mm` de la configuración nueva para que indique 103 mm.
No se modifica el archivo histórico B ni se reutiliza su resultado, cuya
identidad de cierre no corresponde a este estudio.

## Mallas, tiempo, sondas y reutilización

- Dos discretizaciones por diseño: **44 y 88 celdas totales**; 31/62 en escape.
  La fina biseca todos los frustums y distribuye especies y superficie térmica
  con el adaptador existente. Conserva masa, energía y cada especie inicial
  dentro de cada diseño a <=1e-12 relativo. No se remalla un estado evolucionado.
- Paso nominal limitado por 0.5° y los eventos existentes; rechazo conjunto
  ante CFL/admisibilidad según el solver. Controles temporales a 0.25° sobre
  la malla fina de **ambos** diseños. No se cambia CFL ni otros umbrales.
- Se guardan muestras a las mismas fases exactas cada 0.5°. Sondas en
  x=**0.040, 0.250, 0.550, 0.800 y 1.020 m** desde la lumbrera. Cada sonda
  representa el mismo intervalo físico de 10 mm, con promedio de la solución
  P0 ponderado por el volumen exacto del frustum. No se compara un índice de
  celda A con otro B como si fueran la misma posición.
- Se reutiliza **A44/0.5°** de `port-flow-verification-v1-20261028/candidate`:
  configuración, estado inicial nativo y código de producto coinciden; se
  verifican sus hashes y se extraen estados físicos de las primarias completas.
  No se reanuda ni recalcula ese caso. B44, A88, B88 y sus dos controles temporales
  son cinco ejecuciones nuevas. Las sensibilidades antiguas MUSCL y los puntos
  periódicos legacy quedan como antecedentes, no incertidumbre transferible.
- Captura FAST existente para las cinco corridas nuevas, con receta de todos
  los pasos/rechazos y checkpoints nativos al terminar cada ciclo. Los campos
  físicos muestreados no dependen de conservar las trazas completas en RAM.

## Observables y separación de ondas

Magnitudes primarias de diseño en P1 (x=.040 m), fase **88°–272°** del segundo
ciclo: pico de sobrepresión respecto a 101325 Pa, fase del pico, impulso
`integral(p-pamb)dt`, normas L1/L2/Linf de la diferencia A/B y retardo de señal
por correlación normalizada de las trazas centradas. Retardo positivo significa
que B llega después. Búsqueda +/-20°, máximo interior y único, correlación
>=0.95; si el perfil cambia demasiado para describirlo como desplazamiento,
el retardo se declara no identificable.

Los mapas x–ángulo usan las celdas físicas reales y permiten inspeccionar
propagación; no se dibuja una trayectoria inventada de reflexión. En P1, sobre
una referencia local media de **70°–85°**, se calculan las proyecciones
`pi+/-=(delta_p +/- rho_ref*a_ref*delta_u)/2` sólo cuando:

- |delta_p|/p_ref, |delta_u|/a_ref y |delta_rho|/rho_ref <=0.05;
- Mach medio <0.3 y |log(p/p_ref)-gamma*log(rho/rho_ref)|<=0.01.

Fuera de esas hipótesis no se separan amplitudes incidentes/reflejadas mediante
la fórmula acústica. Un pico local de pi- en **150°–272°** se informa únicamente
como candidato de componente dirigida aguas arriba. Para llamarlo reflexión
se necesitaría además una relación causal de propagación con la onda incidente
y la región que la devuelve. Si no se demuestra, el tiempo de retorno reflejado
queda **no identificado**, sin convertir cualquier máximo de presión en reflexión.

## Diferencia distinguible: criterio previo y límites

No hay tres mallas de esta misma trayectoria que permitan justificar GCI ni
una cota rigurosa. Se usa un **filtro de robustez de ingeniería** explícito,
basado en sensibilidades del propio A/B, sin atribuirle un nivel de confianza.
Para cada observable q:

`Sx=|qA88-qA44|+|qB88-qB44|`

`St=|qA88_dt/2-qA88|+|qB88_dt/2-qB88|`

`U_sens=2*(Sx+St)+S_muestreo`.

Se suman sensibilidades individuales para no suponer cancelación de errores
comunes. El factor dos es un margen declarado, **no un orden de convergencia**.
Para fase, S_muestreo=0.5° entre ambos diseños. Para amplitud se suma medio
incremento máximo entre muestras adyacentes por diseño; para impulso, dos veces
la diferencia de cuadraturas con muestras de 0.5°/1°. Son estimaciones de
muestreo sobre la señal guardada, no cotas de derivadas desconocidas.

El retardo de correlación utiliza la mayor de la envolvente de fases de picos
y `2*(|lag88-lag44|+|lag88_dt/2-lag88|)+0.5°`.

**DIFERENCIA DISTINGUIBLE**, limitada a los controles ensayados, requiere:

1. Seis casos disponibles, balances dentro de criterios originales (masa y
   especies <=1e-9, energía <=1e-8 normalizados), configuración y recuperación
   válidas, y presupuesto respetado.
2. Delta de amplitud y retardo de señal mayores que sus envolventes y con signo
   consistente entre las tres parejas. Correlaciones válidas en todas ellas.

Si no se cumplen, **DIFERENCIA NO RESUELTA**, aunque algún observable particular
sí sea robusto. Ningún PASS implica independencia de malla universal. Un defecto
de implementación requiere evidencia localizada de identidad, conservación o
admisibilidad inconsistente; agotar presupuesto, una rama física no admitida o
una señal no separable no se etiquetan automáticamente como defecto.

## Presupuesto y parada

**600 s acumulados** para extracción reutilizada, nuevas corridas, guardado y
análisis/gráficos. El ejecutor reserva 30 s para análisis; detiene pasos a los
570 s globales o 120 s por caso. RSS <=512 MiB, un proceso, <=1 GiB de artefactos,
reserva de disco 2 GiB y preflight previo. Las pruebas del observador no avanzan
el motor; la preparación no ejecuta pasos. El coste histórico reutilizado se
informa separado, no como aceleración.

Se conservan recetas, campos y checkpoints; si se interrumpe un ciclo, el estado
FAST queda acompañado por su receta y último checkpoint nativo, sin afirmar que
el estado FAST aislado sea un checkpoint recuperable. No se amplía el presupuesto,
no se cambia el solver y no se inicia E2B ni otro trabajo al cerrar E2A.

Congelación: protocolo, código del ejecutor, manifiesto y configuraciones
commiteados antes de la primera corrida nueva. Revisión **SELF_REVIEW**.
