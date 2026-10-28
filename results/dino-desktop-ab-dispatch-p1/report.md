# Desktop A/B dispatch feasibility (bounded, one-cycle)

## Results

| Caso | RPM | Serial (s) | Paralelo, 2 procesos (s) | Speedup | Checkpoints |
|---|---:|---:|---:|---:|---|
| low | 5000, 6000 | 25.659 | 13.782 | 1.862× | idénticos |
| high | 7000, 8000 | 23.275 | 12.332 | 1.887× | idénticos |

Configuración A/B: `A_original` y `B_header_plus20` del proyecto funcional de referencia. Cada punto ejecutó exactamente un ciclo. Los ocho checkpoints fueron idénticos entre la ejecución serial y paralela; todos los puntos terminaron `MAX_CYCLES_NONCONVERGED`. No se evaluó periodicidad ni se hizo una curva de potencia válida.

## Decisión

La ejecución concurrente de dos curvas completas reduce el tiempo en ambos casos, pero queda por debajo del objetivo de 2× (1.862× y 1.887×). Esta alternativa no se integra como entrega P1: la métrica no cumple el umbral y el horizonte de un ciclo no demuestra equivalencia de estados periódicos. No se lanzó la campaña de seis puntos porque la instrucción de esta sesión excluye campañas de periodicidad.

Alcanzar 2× exige distribuir puntos independientes entre más workers y agregar manifiestos/reanudación sin competir por el escritor único de cada curva; esa arquitectura no queda demostrada por esta prueba. No se cambió solver, CFL, discretización, tolerancias ni umbrales.

## Presupuesto y artefactos

Preflight de almacenamiento: PASS, estimación 0.25 GiB más reserva de 2 GiB. Ejecución total: 75.859 s, límite 600 s. Evidencia completa de invocaciones y manifests: `logs/dino-desktop-ab-dispatch-p1.summary.json` y external artifact root `${DINO_ARTIFACT_ROOT}/dino-power-curve-v1/functional-reed-125cc-v1/desktop-ab-p1-*`.

El resultado es una decisión de viabilidad de despacho, no una afirmación de rendimiento periódico, predicción o validación experimental.
