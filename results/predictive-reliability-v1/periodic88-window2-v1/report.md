# Segunda ventana88: recuperación exacta y transitorio de composición

2026-10-27. Preregistro `aa33c82`. L1, SELF_REVIEW; sin modificación del solver.

Se recuperó el checkpoint nativo35 y su detector. La receta parcial36 se
reprodujo exactamente: 856 pasos aceptados, 427 propuestas rechazadas y estado
FAST a12814°. No se recalcularon los ciclos31–35 ni se reinicializó el motor.

Cuatro ciclos completos36–39 en184.445s de pared, frente al límite250s;
solver183.620s, incluidos26.503s de recuperación parcial. Restauración.255s,
detector.021s, serialización.260s. Terminal nativo39 a14040°.

|Relativo/absoluto|Máximo/tolerancia|p90|Mediana|Fallidos/809|Trabajo J|
|---|---:|---:|---:|---:|---:|
|6/36|2.69469|.53320|.06828|28|135.575856|
|7/37|2.53042|.36898|.04028|19|135.776187|
|8/38|2.38205|.32660|.03274|19|135.835797|
|9/39|2.34338|.42866|.06266|27|135.923446|

**TRANSIENT_AT_BUDGET, no periódico.** El máximo disminuye pero su descenso
se ralentiza y p90/mediana/conteo repuntan en39. El trabajo cambia sólo.0645%
en el último par, pero difiere aproximadamente3.82% del44 periódico130.923315J.
Una baja sensibilidad espacial de un único ciclo transitorio no demostraba
independencia de malla del estado periódico.

Entre ciclos propios88, L1 volumétrica relativa de presión en TDC disminuye
.000729→.000440→.000329→.000299; L1 absoluta de fracción quemada es
.001735→.001658→.001680→.001760. Los máximos de composición avanzan de
exhaust[29] a[31], [33], [36]. No basta el conteo para concluir divergencia:
hay que distinguir una estructura transportada de una deriva de inventarios.

Los balances globales existentes pasan, con fuentes químicas y térmicas. No
se infieren flujos brutos de inventarios. La siguiente tarea es localizar el
frente con estados guardados y medir flujos del ciclo39 mediante replay exacto,
sin calcular40 ni modificar criterios. No se autoriza una campaña implícita.

Datos completos: `analysis-combined.json`, `run/cycles.json`, checkpoints,
detector, fases cada30°, receta y verificación parcial. Se conservan fuente44,
rc7 y toda la evidencia. Sin independencia de malla ni validación experimental.
