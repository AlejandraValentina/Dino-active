# Entrega 2B — primera curva RPM desde Dino Desktop

## Resultado

**Funcionalidad de curvas exploratorias implementada y demostrada.**
El usuario puede abrir el motor, seleccionar A/B, ejecutar el barrido existente,
consultar estados y tiempos, ver potencia/torque y diferencias a iguales RPM,
seleccionar las presiones de cada régimen, guardar y recuperar el proyecto.

Los seis puntos son `MAX_CYCLES_NONCONVERGED / NOT_CONVERGED`. El estado
científico permanece REVIEW: no son potencias definitivas, validación
experimental ni capacidad predictiva demostrada. El PASS funcional de esta
entrega no cambia ninguna de esas clasificaciones.

## Ejecución autorizada y reutilización

Se usaron las variantes existentes A_original y B_header_plus20 del motor
representativo de 125 cc, con la diferencia de longitud inicial83→103 mm.
Se reutilizaron los dos resultados9000RPM, verificando su identidad exacta,
resultados, checkpoints y60 archivos de muestras contra el receipt anterior.
No se recalcularon ni modificaron. Se ejecutaron únicamente cuatro puntos nuevos:
A/B8000 y A/B10000, cada uno desde sus condiciones iniciales correspondientes.

Presupuesto fijado antes de ejecutar:30ciclos/300s por punto nuevo,650s acumulados
por variante,512MiB y un worker secuencial;1300s entre ambos coordinadores.
El horizonte no se amplió ni se ajustó ningún coeficiente para obtener potencia.

El preflight encontró que el mapa sintético de válvula terminaba a9500RPM.
Se declaró explícitamente `POWERVALVE_OPEN_ENDPOINT_HOLD_V1` hasta10000:
mantener el extremo que ya estaba completamente abierto. La ruta original
continúa rechazando RPM fuera del mapa cuando esa opción no se selecciona.
No se cambió el modelo de válvula ni el solver. El documento efectivo10000
incluye su extensión y provenance `SYNTHETIC_ASSUMPTION`;8000/9000 mantienen
sus configuraciones originales. Posición del techo:1 a8000,0.5 a9000 y0 a10000,
donde0 significa techo elevado/abierto y1 techo bajado, no ausencia total de área.

Ambas variantes conservan los mismos controles dependientes de RPM, admisión,
transferencias, barrido, combustión, AFR suministrado11.5, ambientes y fricción
explícita sintética de85000Pa. La masa inicial del tramo alargado escala con su
volumen para conservar presión, temperatura y composición iniciales.

## Curvas calculadas: último ciclo completo, estimaciones transitorias

| RPM | A potencia HP | B potencia HP | A torque N·m | B torque N·m | ΔB−A HP |
|---:|---:|---:|---:|---:|---:|
|8000|4.11231|4.08713|3.66042|3.63801|−0.02518|
|9000|4.48309|4.45842|3.54707|3.52755|−0.02467|
|10000|4.69801|4.85674|3.34541|3.45844|+0.15873|

HP corresponde a745.6998715822702W; también se puede seleccionar kW o CV.
La potencia al freno se calcula del trabajo del pistón más el trabajo del
cárter y menos la fricción declarada. No se recortan resultados negativos.
No se promediaron ciclos para ocultar deriva ni se generaron valores intermedios.

La respuesta a B cambia con el régimen en este horizonte: a10000 hay mayor
carga atrapada y trabajo que en A, mientras a8000/9000 son menores. No es una
mejora definitiva demostrada. La comparación usa sólo RPM comunes exactas.

| RPM | Δ trabajo indicado B−A (J) | Δ aire atrapado B−A (mg) | Δ presión entrada escape A/B RMS (Pa) |
|---:|---:|---:|---:|
|8000|−0.14472|−0.12188|1183.17|
|9000|−0.12560|−0.08600|850.86|
|10000|+0.72740|+0.53747|1175.32|

Las presiones se compararon en720 ángulos comunes exactos por régimen. Su
variación RMS entre ciclos29 y30 es8–19Pa en la entrada del escape: menor
que la separación A/B. Las diferencias de trabajo también superan el rango
observado de los últimos cinco ciclos. Esto distingue respuestas de geometría
en el transitorio medido; no establece el límite estacionario ni error numérico.

## Periodicidad, estabilidad observada e incertidumbre

Los seis puntos completaron30ciclos. Los indicadores terminales de cilindro y
cárter pasan en todos; no equivalen por sí solos a una órbita global periódica.
Persisten indicadores del escape y dos de inventario global de especies:

| Variante / RPM | Fallos escape | Rango W ciclos26–30 (J) | Rango aire atrapado (mg) |
|---|---:|---:|---:|
|A8000|50|0.02642|0.01093|
|A9000|55|0.01170|0.00195|
|A10000|70|0.02433|0.00916|
|B8000|49|0.02262|0.00879|
|B9000|54|0.01760|0.00542|
|B10000|71|0.03166|0.01351|

El peor indicador del escape sigue entre13.4 y14.7 veces su umbral. El detector
original exige todas sus condiciones durante tres comparaciones consecutivas,
con mínimo diez ciclos. No se eliminó ninguna condición ni se relajó tolerancia.
Los rangos de trabajo, potencia y carga son variaciones observadas, **no una
cota de incertidumbre estacionaria**. No existe aquí una incertidumbre predictiva
cuantificada que permita afirmar cuánto de la diferencia sobrevivirá al régimen.

Las gráficas exploratorias tienen trazos punteados y marcadores huecos, con
leyenda explícita. Los estados originales y métricas definitivas permanecen
sin valor. Desactivar Mostrar transitorios deja la vista periódica sin puntos
válidos. Las RPM solicitadas ausentes permanecen como huecos, sin líneas que
las atraviesen. Exportar CSV conserva clasificación, estado, tipo exploratorio,
tiempo, variación observada y hashes.

## Discretización y límites físicos

A/B usan44celdas totales,31 de escape, misma partición3/5/6/2/2/6/7 y CFL0.4.
No hubo una variante refinada y otra gruesa. El cambio geométrico sí cambia
el dx de sus tres celdas iniciales; igual número de celdas no demuestra
independencia espacial. No es posible descartar aquí contribución del error
de discretización a las diferencias. Esa limitación aparece en la interfaz;
no se ejecutó una nueva campaña de malla ni se reinterpretó el gate histórico.

Se conservan las limitaciones del modelo: barrido parcial no identificado,
láminas cuasiestáticas, representación1D/0D, parámetros térmicos y pérdidas
sintéticos. La válvula también es sintética. No hay validación experimental.

## Tiempos, recursos y recuperación

| Punto nuevo | Ciclos | Tiempo runner (s) |
|---|---:|---:|
|A8000|30|221.16|
|A10000|30|230.41|
|B8000|30|240.26|
|B10000|30|227.53|

- Tiempo de los cuatro runners:919.36s. Cada uno respetó300s.
- Coordinadores:459.16s A y475.00s B;934.16s en total.
- Verificación posterior de resume completo:463.44s A y479.17s B acumulados;
  **942.61/1300s**. Se invocó el coordinador real con una guarda que prohibía
  llamar al solver: cero llamadas, seis resultados conservados por hash.
- Recorrido Desktop de ejecución, carga, exportación y reapertura:973.34s.
  La visualización final se repitió en modo sólo lectura, sin cálculo físico.
- Pico de proceso durante los puntos nuevos:227.94MiB, bajo512MiB. Un worker
  secuencial dentro de Desktop; no se midió speedup multiproceso.
- CFL aceptado máximo0.32771; ningún rechazo registrado. Paso efectivo entre
  1.57µs y10.42µs. Residuos relativos internos máximos inferiores a5.2e−15.
- Se verificaron los hashes de los180 archivos de muestras y resultados,
  manifests y checkpoints. Se restauraron los seis checkpoints de manera exacta,
  sin pasos: `next_cycle=31`, ángulo10800°, historia de30ciclos y observables
  finales consistentes. No se indujo una nueva interrupción física.
- Los checkpoints válidos y el presupuesto acumulado siguen usando la ruta
  existente de cancelación/reanudación; no se creó otro coordinador.

## Correcciones y pruebas

Se completó el coordinador existente para aceptar referencias explícitas de
puntos completos, sin migrar hashes ni inferirlos buscando archivos. La
identidad de todos los módulos físicos coincide en los seis puntos.
El endpoint-hold sólo se aplica al documento efectivo que lo necesita.
Se reutilizaron el importador verificado, panel de curvas y gráficos existentes.

Durante la corrida apareció un fallo de presentación en la barra, que esperaba
`cycle` en vez del mensaje anidado `solver_progress` del barrido. No detuvo el
solver ni alteró datos. Se corrigieron progreso agregado, RPM, presupuesto y
mensajes de final de punto, y se probaron ambos formatos. No se repitieron
ciclos. La interfaz final corregida abrió los seis resultados sin errores.
Las incidencias previas de automatización del diálogo también se conservaron
en logs y ocurrieron antes del primer paso del solver.

Pruebas:25 PASS/14 deselected en la suite focal final;43 PASS/un skip en la
regresión Desktop. El skip corresponde al artifact histórico IMPL2 no
configurado. OpenSpec strict y program-status check:PASS. No hubo replay ni
auditoría científica independiente; los balances son internos al modelo.

## Siguiente solución técnica acotada, propuesta y no ejecutada

El bloqueo para una curva periódica sigue en el estado del escape/inventarios.
Propuesta: **inicialización por continuación conservativa dentro de la misma
variante**, reutilizando un estado físico ya calculado de un régimen cercano.
No aceptar un checkpoint con RPM incompatible: construir una nueva condición
inicial identificada, conservando los inventarios y estado termodinámico y
cambiando sólo RPM y su control de válvula. Registrar la nueva referencia
inicial de ledger sin borrar ni renombrar especies residuales.

Un único piloto propuesto:A10000 desde el estado A9000 ya disponible, máximo
diez ciclos/120s, usando el detector original. Comparar su extremo con el
arranque frío actual. Si no cumple, cerrar ese piloto y decidir sobre la
evidencia, sin aumentar automáticamente ciclos ni lanzar una curva completa.
Es una propuesta de inicialización en el flujo existente, no un modelo nuevo
ni una garantía de periodicidad. No se implementó ni ejecutó en esta entrega.

## Cómo abrir los resultados

Abrir en Dino Desktop de código fuente el proyecto guardado
`E:/Dino-artifacts/desktop-rpm-curves-v1-20261022/rpm-curves.dino.json`.
En Análisis, seleccionar B y baseline A, actualizar historial, seleccionar las
seis corridas y pulsar Ver selección. El proyecto conserva referencias a todos
los resultados, incluidos los9000 en su root anterior. También puede abrirse
el proyecto de referencia Git y preparar la grilla con la receta
`configs/reference_cases/functional_exhaust_rpm_grid_v1.json`; esta receta es
documentación reproducible de los controles, no un segundo ejecutor.

Evidencia: `01-power-torque-curves.png`, `02-rpm-points.png`,
`03-equal-rpm-deltas.png`, `04-global-and-observed-stability.png`,
`05-desktop-results.png`, `06-periodic-only.png` y `pressure-8000/9000/10000.png`.
Valores exportados: `exploratory-power-torque.csv`. Hashes y provenance compactos:
`receipt.json`. Artifacts completos y logs permanecen fuera de Git.

Sin nuevo EXE, push, campañas adicionales ni cambios de HLLC/SSPRK2, modelos de
admisión/transferencias/barrido/combustión o criterios científicos. Histórico y
cambios locales ajenos preservados. Aceptación funcional exploratoria; ciencia
REVIEW y ninguna promoción de las prestaciones físicas del motor.
