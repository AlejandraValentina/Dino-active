# Primera ventana88: transitorio acotado, todavía no periódico

2026-10-27. Protocolo `89d0b35`, L1/SELF_REVIEW. Origen44/ciclo30 auditado;
nueva inicialización conservativa88 y detector vacío, reloj físico conservado.
Mismo modelo, geometría física, CFL, combustión y tolerancias. Sin modificación
de solver, sin nueva malla176 ni campaña RPM.

## Ejecución y presupuesto

Estado **TRANSIENT_AT_BUDGET**. Completó ciclos relativos1–5 (absolutos31–35)
y parte del6/36. Paró por el límite260s de solver; pared261.02s<300s. El último
checkpoint nativo completo es35 a12600°; el terminal12814° es **FAST+receta**,
no se presenta como checkpoint nativo. Todos se conservan.

|Relativo/absoluto|Máximo error/tolerancia|p90|Mediana|Fallidos/809|Trabajo J|
|---|---:|---:|---:|---:|---:|
|1/31|sin comparación|—|—|—|130.783278|
|2/32|19.84684|5.21537|.33125|251|131.692690|
|3/33|10.80567|3.75085|.38991|264|133.019590|
|4/34|4.32523|1.62314|.21296|136|133.906452|
|5/35|3.02890|.89650|.17368|77|135.143221|

No se inventó comparación para el primer ciclo. La disminución de máximos/p90
es clara aunque el conteo aumenta inicialmente. De809 observables,416 mejoran,
245 son estables y148 empeoran entre las primeras/últimas comparaciones según
el descriptor5%; esas clases no sustituyen el detector ni implican tendencia
monótona de cada variable.

Lag2 sigue FAIL, máximo24.89→15.04→6.37 en los relativos3–5, peor que lag1.
No hay evidencia de período2 establecido ni de período1 admitido.

## Qué bloquea el último ciclo

77 fallidos:26 fracciones de composición del escape,19 masas y24 energías
de celdas del escape,2 temperaturas,3 masas en otros conductos, masa/energía
del cilindro y trabajo. Los inventarios globales de especies ya cumplen sus
criterios. No es correcto reducir el problema a la composición de la salida.

El máximo es quemados en exhaust[13], x=.22483m: ΔY=.0060578, tolerancia.002.
También destacan la capa en x≈.438–.489m y la energía/masa almacenadas allí.
El cilindro cambia.2267% en masa y.3420% en energía; trabajo cambia.9152%
entre34/35 y aún falla el umbral.5%. Todos los balances globales con fuentes
físicas pasan; conservación no equivale a periodicidad.

## El efecto espacial ya alcanza al trabajo

La referencia44 auditada da130.923315J. El88 transitorio llega135.143221J,
**+3.223%**, todavía sin solución periódica. No es una ganancia de potencia
validada ni una calibración: no se cambió ningún parámetro físico.

Durante31–35, la masa de aire en cilindro a300° pasa101.278→103.786mg; el
combustible quemado por ciclo6.8303→7.0388mg y el calor249.647→257.267J.
La referencia44 tiene100.406mg de aire al snapshot de ignición y249.403J.
En esta configuración300° tiene puertos cerrados y precede a la ignición340°;
el muestreo se identifica por fase, no como una medición experimental de cierre.
Los eventos de combustión cruzan TDC: el calor integrado contiene porciones
de eventos contiguos, y no se exige proporcionalidad instantánea con ese aire.

Los datos son compatibles con ajuste de ondas/llenado que modifica masa
disponible para combustión y trabajo. La cercanía de trabajo del primer ciclo
entre mallas **no acotaba** este efecto posterior. No atribuir a mejora física
el incremento de un transitorio ni certificar independencia de malla.

## Comparación espacial y de fase

`analysis-v2.json` compara13 fases reales por revolución, sin interpolación,
con la primaria44/ciclo30. La diferencia final de presión L1 crece.02065→.02874,
y quemados L1.01274→.01847, mientras las diferencias entre ciclos88 disminuyen.
Esto es compatible con acercamiento a otro estado discretizado; no es una
comparación de dos soluciones periódicas ni demostración de divergencia.

La transferencia inicial conserva medias y primitivos de hijos hasta roundoff.
La curva44 es el ciclo real29→30 y el origen fino es el final30: su residual
periódico se publica por separado para no confundirlo con error de remallado.
Se usan coordenadas físicas/volúmenes comunes y los estados **aceptados** de
SSPRK2, no el predictor. L1/L2/Linf y datos de fase están preservados.

No se registraron todos los flujos brutos por interfaz en esta ventana compacta;
no se infieren de inventarios. El replay/auditoría posterior de períodos
aceptados deberá obtenerlos desde las etapas, como en44.

## Decisión siguiente

No cambiar formulaciones ni tolerancias. El descenso19.85→3.03/p90.90 y la
mejora de416 observables justifican preparar otra ventana corta **del mismo88**,
después de verificar recuperación exacta del parcial. Debe conservar identidad
y detector, partir del nativo35 y reproducir sólo el prefijo parcial36 necesario
para comprobar el FAST12814°, sin recalcular31–35 ni fingir restore nativo FAST.

Propuesta máxima: cuatro ciclos completos36–39, incluyendo la recuperación
parcial, con presupuesto250s y parada por estancamiento. Preregistrar antes de
ejecutar; no ampliar automáticamente ni iniciar176. La periodicidad y el error
espacial de trabajo/composición siguen pendientes.39 tests focalizados PASS.
