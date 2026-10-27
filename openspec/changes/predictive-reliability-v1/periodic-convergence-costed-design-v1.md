# Periodicidad y convergencia: diseño costeado v1

2026-10-27. Preparación, **no autorización automática de ejecución**. Objetivo
DINO_PREDICTIVE_RELIABILITY_V1; rc7 y contratos P0–P9 permanecen intactos.

## Evidencia y dependencias

El checkpoint25 es nativo y verificado; no es periódico. Los controles de
transporte aislado, reflexión/reversión y balances ya están resueltos en su
dominio: no repetirlos. El estudio `remap-uncertainty-v1` muestra que la
sensibilidad temporal y P0/P1 ensayadas no explican el caudal espacial, y que
las capas de composición todavía no contraen su L1 entre44/88/176.
El control352 preregistrado debe informar su decisión antes del siguiente
tramo integrado. Si no completa o no caracteriza la contribución dominante,
no empezar una campaña periódica para ocultar esa incertidumbre.

## Secuencia limitada

1. **Diagnóstico espacial:** cerrar el control352 con referencia176/.0625 y
   declarar qué mejora y qué no. No exigir convergencia puntual en contactos
   ni inferir independencia de potencia del L∞ de composición.
2. **Periodicidad44:** si la evidencia de transporte no descubre un defecto,
   preparar un único tramo desde el checkpoint25 original, máximo4 ciclos y
   90s. Restaurar tanto el estado físico como el detector25 conservado;
   verificar hashes y reproducción de observables sin recalcular históricos.
   Misma configuración, modelo, CFL y receta adaptativa original. No usar el
   checkpoint26 de los diagnósticos como continuación aceptada del piloto.
   Registrar máximo/p90/mediana error/tolerancia, fallidos, período1/2,
   balances, inventarios, trabajo y coste. Exigir el streak original completo.
   Si se estanca o empeora de forma sostenida, parar y analizar; no encadenar
   extensiones para obtener PASS. Este documento no lanza ese tramo.
3. **Mallas siguientes:** sólo tras periodicidad demostrada44, registrar una
   nueva inicialización conservativa del mismo motor/RPM a88 y176 con identidad
   nueva, conservando la referencia44. No confundirla con reanudación nativa ni
   con warm start entre RPM (V3 sigue congelada). Verificar campos además de
   integrales, reiniciar detector de la nueva malla, y permitir que cada malla
   alcance su propia periodicidad. Primera ventana≤10 ciclos por malla,
   ≤600s88/≤1200s176; reevaluar tendencia antes de cualquier nueva ventana.
   No ejecutar todas las ventanas por adelantado.
4. **Temporal:** desde estados periódicos nativos de cada malla, comparar el
   mismo período con paso reducido; registrar identidad numérica/receta nueva.
   El diagnóstico temporal transitorio existente es contexto, no cota del
   error periódico. No cambiar CFL ni tolerancias para cumplir costes.
5. **Auditoría y malla:** reconstruir primarias sólo de los períodos aceptados
   que hagan falta para L2/replay, no de todos los ciclos transitorios. Comparar
   trabajo/IMEP, presión, fases, flujos brutos/reversos/netos, inventarios,
   composición y conservación; campos en fases y volúmenes comunes. Períodos
   de dos ciclos requieren promedios del período completo. No comparar como
   iguales una rama de período2 con un promedio de período1.

## Coste: medidas y escenarios, no predicción de ciclos restantes

Medidas con sus distintas recetas: extensión44 original seis ciclos84.59s
(14.10s/ciclo); diagnóstico88 cap.25°40.07s/ciclo;176 cap.125°108.73s/ciclo.
Son bucles instrumentados y estados distintos; no un benchmark homogéneo de
producto. No extrapolar el caso44 cap.125°57.50s al método adaptativo original.

| Ciclos adicionales por malla |44 min|88 min|176 min|Suma min|
|---:|---:|---:|---:|---:|
|10|2.35|6.68|18.12|27.15|
|40|9.40|26.71|72.49|108.60|
|80|18.80|53.43|144.97|217.20|

Añadir al menos20% de margen de planificación y auditoría separada. No se
afirma que falten10,40 u80 ciclos: todavía no hay ajuste de relajación fiable.
No activar E2 por una hipótesis de80 ciclos; sí cuando una proyección sustentada
exceda120min por configuración o6h acumuladas. En ese caso crear bloqueo de
performance y trabajo de perfil/equivalencia, sin relajar precisión. No iniciar
automáticamente Numba, nueva arquitectura ni cierres físicos.

La auditoría completa registrada de ciclo2 costó≈76.87s44, muy por encima de
la continuación compacta. No multiplicar ese factor por todos los transitorios.
Restauración nativa exacta por sí sola no sustituye replay ni independencia.

## Almacenamiento y recuperación

Preflight real antes de cada ventana, reserva2GiB, máximo1GiB para el estudio
periódico según E1.3. Recetas, detector y checkpoints compactos por ciclo;
configuración, fuente, origen y aceptaciones identificados. Sin borrar ni
reescribir históricos y sin rutas de unidad fijas.

El archivo primario comprimido observado44 ocupa28.3MB. Antes de proyectar
una auditoría de tres mallas hay que verificar cuántos ciclos contiene: su
tamaño por ciclo no se conoce sólo por el tamaño del archivo. Al refinar,
celdas y pasos crecen; el volumen puede crecer≈4× por nivel a CFL equivalente.
Una auditoría de períodos completos puede acercarse o superar1GiB. Registrar
una estimación con cobertura y compresión verificadas antes de escribirla;
si no cabe, resolver persistencia/streaming sin descartar primarias exigidas.

## Decisiones y límites

Periodicidad y error espacial son gates distintos. Sólo aplicar Richardson/GCI
cuando los resultados periódicos y sus tendencias permitan estimarlo. Mantener
GCI≤2% en trabajo/IMEP del criterio vigente, sin ajustar órdenes ni descartar
mallas incómodas. Una pequeña sensibilidad de trabajo transitorio no pasa E1.

Antes de cualquier cierre core: regresiones P4–P8, evidencia requerida por spec
y revisión independiente donde corresponda. Este diseño es SELF_REVIEW y no
cierra E1. Validación experimental sigue NOT_PERFORMED; capacidad predictiva
NOT_CLAIMED. X30 y Cahoon incompletos no se rellenan con supuestos.
