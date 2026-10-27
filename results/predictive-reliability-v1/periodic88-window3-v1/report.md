# Ventana88 número3: parada por progreso insuficiente en40

2026-10-27. Preregistro `180c38f`. L1/SELF_REVIEW, fuente nativa39 verificada.
No cambios físicos, espaciales, temporales, de detector ni tolerancias.

Se ejecutó sólo40 (relativo10),46.253s de pared/45.844s de solver, dentro de
210s/230s/240s. La regla preregistrada detuvo la ventana al incorporar la
historia8–10: dos transiciones sin reducir máximo5% y con p90 creciente.
Esto es una parada de recursos, no una clasificación física de divergencia.
Terminal nativo40 a14400°, detector original y receta recuperables.

|Relativo|Máximo/tolerancia|p90|Mediana|Fallidos/809|Trabajo J|
|---|---:|---:|---:|---:|---:|
|8|2.38205|.32660|.03274|19|135.835797|
|9|2.34338|.42866|.06266|27|135.923446|
|10|2.40811|.79969|.09554|71|136.024369|

71 fallidos:27 aire fresco,27 quemados y17 masas de celdas del escape. No
fallan presiones, temperaturas, energía, cámaras, otros conductos, trabajo ni
inventarios globales. El máximo es quemados en exhaust[38],x=.666474m.

L1/L2 de ΔY quemados en TDC .0017014/.0023557, frente a.0017604/.0023802
en9: bajan, aunque L∞ sube.0046868→.0048162. El centro de |ΔY| avanza
.58930→.62342m y su anchura σ aumenta.10989→.14990m. El número fallido
no demuestra por sí solo una amplitud creciente de toda la estructura.

La presión relativa L1 sube .000299→.000489 (misma definición del análisis
de estados), pero máximo local sigue.001993 y pasa el criterio original.
96.73% del peso de |ΔY quemados| está con |Δp|/p<.001. Hay una señal de
presión mayor que en39, todavía pequeña; no se extrapola estabilidad futura.

El escape gana1.371066mg, pierde.924215mg de quemados; la suma de cambios
absolutos de quemados por celda baja2.0586→1.9706mg. Los balances globales
siguen pasando. No se infieren flujos brutos nuevos para40: sólo se midieron
directamente en39 y no se presume que sean idénticos.

Trabajo cambia.07425% respecto39 y queda≈3.896% por encima de44 periódico;
IMEP10.914410bar.88 continúa transitorio: no es una comparación entre dos
soluciones periódicas ni evidencia de mejora de potencia.

**STOP_NO_SUFFICIENT_PROGRESS. No ejecutar41 ni ampliar presupuesto.**
La siguiente investigación usa estados y flujos guardados para separar
desplazamiento del material y cambios de marcadores dentro del escape. Si
es necesario un ensayo adicional, se definirá por la incertidumbre concreta,
sin campaña periódica automática ni alteración de formulaciones.

`analysis-combined.json` contiene fases y tendencias1–10; `run/` conserva
checkpoint inicial39/final40, detector,13 fases, recetas y receipt. rc7 y
históricos intactos. Sin independencia de malla ni validación experimental.
