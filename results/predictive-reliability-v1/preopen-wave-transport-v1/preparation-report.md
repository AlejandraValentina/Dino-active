# Preparación verificada del arco38→39,0–60°

2026-10-27. **PREPARED_ONLY**, cero pasos de solver. No41 ni extensión de
campaña. Se conservan los nativos y resultados anteriores. L1/SELF_REVIEW.

Fuente38 a13680° absolutos/fase0°. Margen de cierre del escape9.363893mm
incluso con válvula totalmente levantada; recorrido de cierre original no
negativo. Prueba de monotonicidad del mecanismo y áreas efectivas muestreadas
ambas confirman cierre durante0–60°. No se cambia la válvula.

|Plantilla|Celdas totales|Máximo error relativo inventario|Máximo error de campo restringido|
|---|---:|---:|---:|
|P0-88|88|0|0|
|P0-176|176|8.90e-16|9.40e-16|
|P0-352|352|1.42e-15|5.88e-16|
|P1-176|176|1.15e-15|9.40e-16|

Inventarios: masa, energía y cada especie; campos: densidad, presión,
velocidad/composición en volúmenes comunes, más contraste de los subcampos
P1 frente aP0. Se guardan métricas completas, no sólo conservación. Todas
las plantillas restauran exactamente en un constructor nuevo, con reloj y
evento/combustible conservados. No se ejecutó un detector ni se pretende
reanudar nativamente entre mallas: las finas tienen identidad diagnóstica nueva.

Usar **preparation-verified/**. Se conserva también preparation/ como primer
artefacto y su fuente exacta prepare-source.py; aquel flag de roundtrip
comparaba dos snapshots del mismo objeto. La preparación verificada añade
restauración real en constructor independiente. No hubo resultados de
evolución ni cambio físico asociado a esa corrección del diagnóstico.

La suite focal actual pasa60 tests. El contraste espacial/temporal de este
arco todavía no está ejecutado. Protocolo en OpenSpec, máximo480s agregados,
180s/caso y watchdog540s, con preflight y fuente sellada antes de comenzar.
Este ensayo no demuestra periodicidad ni independencia espacial del motor.
