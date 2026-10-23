# Primeras curvas RPM periódicas de Dino 2T

## Resultado

**Los seis puntos A/B a8000,9000 y10000RPM alcanzaron periodicidad global según el contrato V2 vigente.** Clasificación conservada: `PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED`. Hay tres comparaciones globales consecutivas válidas en cada punto; no se cambiaron umbrales. No es una validación experimental ni una demostración de independencia de malla.

Se reutilizó A9000c104 sin pasos del solver y se continuaron los otros cinco puntos desde sus propios checkpoints del ciclo30, en el orden autorizado. No hubo reinicios desde cero, transferencia de estados entreRPM/variantes, modificaciones físicas ni ampliación de límites. Ningún punto quedó incompleto.

## Potencia y torque calculados

Potencia al eje estimada con el FMEP explícito sintético85000Pa y el trabajo de bombeo del cárter; HP mecánico=745,6998716W.

| RPM | A HP | A Nm | B HP | B Nm | Ciclos A/B | Estado |
|---:|---:|---:|---:|---:|---:|---|
| 8000 | 4.1159 | 3.6636 | 4.0929 | 3.6432 | 105/105 | PERIOD_1 observado |
| 9000 | 4.5061 | 3.5653 | 4.4781 | 3.5432 | 104/104 | PERIOD_1 observado |
| 10000 | 4.7254 | 3.3649 | 4.8801 | 3.4751 | 104/103 | PERIOD_1 observado |

La potencia crece entre los tres regímenes muestreados y el torque disminuye. El máximo de potencia **entre estos puntos** está a10000RPM; no se ajustó ni extrapoló un pico fuera de la grilla.

## Respuesta al escape +20mm

B conserva la modificación existente del primer tramo83→103mm; el resto de las condiciones físicas es el correspondiente a cada punto preregistrado. A igualRPM, combustible, AFR suministrado, combustión, fricción y controles son comunes. Los controles dependientes del régimen conservan el mapa de válvula y su extensión explícita completamente abierta a10000.

| RPM | B−A [W] | B−A [HP] | B−A [Nm] | Cambio relativo | Aire atrapado A/B [mg] |
|---:|---:|---:|---:|---:|---:|
| 8000 | -17.116 | -0.02295 | -0.02043 | -0.558% | 30.26870/30.15432 |
| 9000 | -20.835 | -0.02794 | -0.02211 | -0.620% | 29.68748/29.59000 |
| 10000 | +115.405 | +0.15476 | +0.11020 | +3.275% | 28.92130/29.44745 |

La carga fresca total atrapada (aire+combustible) A/B fue34,52586/34,40851mg a8000;33,58287/33,47526mg a9000;32,47687/33,05121mg a10000. La mayor carga calculada de B a10000 acompaña su mayor trabajo indicado; a8000/9000 ocurre lo contrario.

Las ondas de entrada de escape A/B son distintas: diferencias RMS1193,75Pa a8000,876,40Pa a9000 y1158,74Pa a10000. Las diferencias RMS en la sección media son128,32/93,94/152,51Pa. Las trazas originales tienen720muestras por ciclo a0,5° y se comparan por fase, sin crear muestras ni interpolar valores ausentes. Desktop muestra las curvas de presión de la celda de entrada; esto no constituye un campo espacial completo de las31celdas.

La interpretación compatible con esos datos es una modificación del acoplamiento de ondas y de la carga retenida causada por la geometría. Es una inferencia dentro del modelo, no una medición causal experimental. La respuesta ya no depende de comparar un escape purgándose con otro periódico, dentro de las tolerancias vigentes.

**No se declara una mejora de diseño validada.** Ambas variantes tienen31celdas de escape y la misma partición por tramos, pero el primer tramo de3celdas pasa de27,667a34,333mm/celda al alargarlo. La igualdad de conteos no elimina diferencias de dispersión/difusión numérica. Sin una cota espacial no se puede separar de forma concluyente el efecto físico del error de discretización, especialmente para diferencias del0,6%. No se ejecutó aquí otra campaña de malla.

## Cambio respecto del ciclo30

| Variante | RPM | HP ciclo30 | HP periódico | Cambio [W] |
|---|---:|---:|---:|---:|
| A_original | 8000 | 4.11231 | 4.11587 | +2.654 |
| A_original | 9000 | 4.48309 | 4.50608 | +17.143 |
| A_original | 10000 | 4.69801 | 4.72536 | +20.396 |
| B_header_plus20 | 8000 | 4.08713 | 4.09292 | +4.312 |
| B_header_plus20 | 9000 | 4.45842 | 4.47813 | +14.703 |
| B_header_plus20 | 10000 | 4.85674 | 4.88012 | +17.440 |

Las diferencias B−A del ciclo30 eran−18,77/−18,39/+118,36W; periódicas son−17,12/−20,84/+115,41W. El signo se conserva, pero los valores cambian: no se reutilizaron las potencias transitorias como resultados estacionarios. La variación de los últimos5ciclos es pequeña (rango máximo de trabajo0,000903J y de aire0,000651mg), y **no se presenta como una cota de error espacial o físico**.

## Presupuesto, recuperación y conservación

| Variante | RPM | Ciclos adicionales | Continuación [s] | Acumulado del punto [s] |
|---|---:|---:|---:|---:|
| A_original | 8000 | 75 | 487.821 | 708.983 |
| A_original | 9000 | 74 | 490.325 | 710.599 |
| A_original | 10000 | 74 | 485.227 | 715.634 |
| B_header_plus20 | 8000 | 75 | 489.954 | 730.210 |
| B_header_plus20 | 9000 | 74 | 487.331 | 710.147 |
| B_header_plus20 | 10000 | 73 | 478.753 | 706.288 |

A9000 pertenece a la entrega anterior: sus74ciclos adicionales no se repitieron. Esta ejecución calculó371ciclos nuevos en los cinco puntos restantes. Los productores consumieron2429.086s; el coordinador completo2472.625s y su lanzador2473.422s (**41,22min**, límite3300s). Preparación de cero pasos10.937s, también dentro del margen global disponible. Cada continuación quedó por debajo de600s, de111ciclos y de512MiB. No hubo reintentos ni ampliaciones.

El costo acumulado de los seis puntos, contando sus corridas históricas y la continuación previa de A9000, es4281.862s (**71,36min**); no es tiempo nuevo de esta campaña. Se contabilizan los1362.451s originales y490,325s de A9000 por separado, sin reiniciar sus presupuestos históricos.

Pico máximo observado en los cinco puntos nuevos180,39MiB. Cero rechazos CFL; guardas originales activas. Los residuos relativos máximos registrados en los seis historiales son menores que8,85e-15(masa),9,94e-15(energía) y1,49e-14(especies). Se verificaron los625archivos diagnósticos de ciclos completos, sus grillas de fase, hashes y las comparaciones del detector; cada checkpoint final restaura exactamente, sin pasos físicos. Los checkpoints/resultados originales permanecen íntegros. Los29hashes de implementación científica coinciden con los históricos.

Estas son verificaciones focalizadas de integridad y balances del productor; no se ejecutó replay ni una nueva auditoría independiente/general. Los puntos retienen el estado de auditoría NOT_PERFORMED.

## Desktop y reproducción

Proyecto externo listo para abrir: `DINO_ARTIFACT_ROOT/periodic-rpm-curves-v1-20261023/periodic-rpm-curves.dino.json`. Incluye12referencias: seis resultados originales y seis periódicos, también indexados desde el historial. En **Análisis → Mostrar corridas**, seleccionar las seis corridas periódicas del root nuevo y **Ver selección**; las originales permiten volver a la curva de30ciclos. El panel permite ocultar/mostrar transitorios; los puntos periódicos se dibujan llenos, los transitorios huecos/punteados y las ausencias quedan como huecos.

Se abrió el Desktop real desde el proyecto guardado, se cargaron las seis corridas periódicas, se visualizaron potencia/torque y diferencias a igualesRPM, se cambiaron las trazas de escape entre8000/9000/10000, se exportaron CSV, se volvieron a cargar las seis originales y se regresó a las nuevas. No se inició ningún solver desde esa comprobación visual.

- [Curvas periódicas](captures/01-periodic-power-torque.png).
- [Desktop con curvas y estados visibles](captures/04-desktop-periodic-curves.png).
- [Comparación a igualesRPM](captures/03-equal-rpm-comparison.png).
- [Curvas exploratorias originales](captures/06-original-exploratory-curves.png).
- [Ondas de escape10000RPM](captures/pressure-10000.png) y capturas equivalentes8000/9000.
- CSV originales y nuevos: `original-cycle30-power-torque.csv` y `continued-power-torque.csv` en el artifact root nuevo.

## Límites y cierre

Las curvas son estacionarias **dentro del contrato numérico actual**, no soluciones exactamente idénticas ni prestaciones experimentalmente validadas. Persisten la independencia de malla no demostrada, EOS con gamma constante, temperaturas de pared impuestas, láminas cuasiestáticas, transferencias idealizadas, modelo de barrido parcial no calibrado, válvula sintética y fricción sintética. Estos límites no se eliminan al alcanzar periodicidad.

No queda un bloqueo de periodicidad en esta grilla. No se autoriza otra campaña ni se inicia un objetivo posterior. Solver, modelos, UI y evidencia histórica se preservaron; el cambio de producto quedó limitado a la continuación explícita y su contabilidad en el coordinador existente.21pruebas focales PASS; OpenSpec strict y program-status check registrados en el receipt. Revisión propia: SELF_REVIEW. No se atribuye revisión independiente. Commits locales, sin push.
