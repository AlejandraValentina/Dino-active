# Único control adicional352, checkpoint25

2026-10-27. Depende del estudio `remap-uncertainty-v1`, no de una promoción de
candidatos. Su informe muestra presión y caudal que se aproximan, trabajo no
monótono y frentes de composición que no contraen L1 sobre volúmenes comunes.
P0/P1 inicial y reducción temporal tienen efectos mucho menores que la malla.

## Alcance y presupuesto

Una sola ejecución352 celdas totales (248 escape), P0 desde el checkpoint25
original,9000–9360°, cap.0625°, configuración/modelo/física/criterios inalterados.
Comparación primaria con176/P0/.0625° ya disponible, no repetirlo. Mismo campo
físico P0 original y proyección directa conservativa en centroides exactos.
No se usa un final transitorio refinado como origen ni solución exacta.

Máximo420s de bucle instrumentado,16MiB estimados, preflight reserva2GiB.
Checkpoint/receta recuperable cada30°, nativo al completar. Detener ante estado
inadmisible, balance normalizado>1e-12 o presupuesto. No ampliar automáticamente.
Es una fase adicional separada del presupuesto720s ya cerrado en568.75s.

## Métricas y decisión

Normas L1/L2/Linf presión/densidad/composición proyectadas a los mismos volúmenes
44 para contrastar88→176 y176→352. El par88/176 a.125° es contexto espacial;
176/352 a.0625° es el contraste primario. Verificar pasos reales y conservar
el control temporal176(.125/.0625), sin afirmar que acota el error temporal352.

Registrar inventarios, flujo bruto/reverso/neto, trabajo/IMEP y capas de
composición. Usar cruces de nivel y amplitudes como descriptores, sin forzar una
anchura única cuando existen varias capas. Mantener balances por especie y
subsistema, fuentes globales y restauración nativa.

Si el contraste se contrae, preparar periodicidad costeada con incertidumbre
todavía explícita; no ejecutarla por este protocolo. Si no se contrae, congelar
los refinamientos y localizar el transporte de capas/acoplamiento por análisis
de la evidencia antes de otra ejecución. No GCI automático ni cambios del
solver para reducir diferencias. Revisión SELF_REVIEW, validación no realizada.
