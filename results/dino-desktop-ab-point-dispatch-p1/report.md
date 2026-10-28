# Despacho A/B por puntos independientes — factibilidad P1

Fecha: 2026-10-28. Corrida acotada `EXPLORATORY`; no cambia el solver.

## Método

Se compararon ejecuciones seriales y con tres procesos independientes para seis puntos (tres RPM × dos variantes) de `functional-reed-125cc-v1`, divididos en dos bandas. Cada punto avanzó exactamente un ciclo con el mismo caso y parámetros. Se midió pared integral incluyendo arranque, cálculo y persistencia. No se evaluó periodicidad.

## Resultado

- Banda `low` (4500, 5000, 5500 rpm): 35.417 s serial, 13.018 s paralelo, 2.7205×; checkpoints idénticos: True.
- Banda `high` (7000, 7500, 8000 rpm): 29.280 s serial, 10.557 s paralelo, 2.7735×; checkpoints idénticos: True.

La corrida alcanzó el criterio de viabilidad breve de al menos 2× en ambos casos: `True`. Los doce estados quedaron etiquetados `MAX_CYCLES_NONCONVERGED`: son checkpoints de un ciclo y no resultados periódicos convergidos.

## Alcance de la conclusión

El resultado justifica integrar el coordinador de puntos independientes en Desktop. No prueba el objetivo de aceleración en una curva periódica de seis puntos A/B ni autoriza una afirmación de precisión predictiva. La comparación periódica queda pendiente de activación y presupuesto propios; la validación experimental sigue bloqueada por geometría y mediciones completas del mismo motor.

## Artefactos

- `feasibility.json`: métricas, hashes y clasificación por punto.
- `logs/dino-desktop-ab-point-dispatch-p1.summary.json`: resumen de `run_logged.py`.
- `logs/dino-desktop-ab-point-dispatch-p1.log`: salida completa.
