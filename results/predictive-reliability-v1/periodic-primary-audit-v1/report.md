# Periodicidad44 verificada desde primarias

2026-10-27. **PASS L2 / SELF_REVIEW, sólo para este caso44.** El detector
original reconstruido con primarias27–30 devuelve período1 en30, streak3.
No independencia de malla ni validación experimental; E1 global permanece abierto.

## Evidencia numérica

Se reprodujeron las recetas existentes27–30, incluidas propuestas rechazadas.
Los terminales físicos, relojes, eventos y ledgers coinciden exactamente con
los checkpoints guardados. El auditor existente regeneró SSPRK2, RHS, flujos,
fuentes, conservación y bindings de cada primaria: cuatro PASS.

|Primaria|Auditoría s|Comparación con ciclo anterior|Máximo error/tolerancia|
|---:|---:|---|---:|
|27|71.62|FAIL, contexto26|1.85313|
|28|72.53|PASS,27 también auditado|.87950|
|29|74.13|PASS,28 también auditado|.48308|
|30|74.16|PASS,29 también auditado|.45880|

Las tres comparaciones aceptadas contienen413 observables cada una y proceden
de pares de primarias auditadas. Se mantuvo prefix1–26 para conservar el estado
del detector. No se recalcularon esos ciclos históricos ni hubo ciclo31.
La periodicidad es la definida por el contrato vigente (estado a fase común y
observables integrados); no se afirma identidad bit a bit de ondas entre ciclos.

Residuos máximos de los cuatro ciclos: masa3.17e-18kg, energía1.59e-12J y
especies2.53e-18kg, con fuentes físicas contabilizadas. Se respetaron los
criterios del auditor, sin ampliar tolerancias.

## Defecto del nuevo diagnóstico, identificado y conservado

El intento original terminó STOPPED después de cuatro auditorías PASS. El
wrapper entregó un tag de datos V2 al detector V2. La implementación exige
**datos V1 y semántica de detector V2**; la identidad se rechazó correctamente
antes de comparar valores. No fue una diferencia física del solver.

La corrección conserva literalmente primary['contract']; rechaza contratos
desconocidos. El test reproduce INVALID para la etiqueta equivocada. No se
modificaron primarias, productor, auditor, detector, solver ni umbrales.

`manifest-original.json` y `run/receipt.json` preservan el fallo original.
`reconstruction/receipt.json` contiene el resultado corregido, obtenido leyendo
las mismas primarias con hashes comprimidos y canónicos verificados. Esa
recuperación tomó24.85s y ejecutó **cero pasos del solver**. No se repitieron
las auditorías ni las simulaciones para obtener PASS.

## Recursos y reproducibilidad

- Auditoría292.62s<480s; cuatro primarias≈61.94MB en total, externas bajo la
  raíz configurable de artefactos. Los nombres y SHA-256 están en cada receipt.
- Spool/lectura/escritura por partes existentes, sin nuevo backend. Preflight
  con reserva2GiB; no limpieza ni traslado de históricos. Git conserva sólo
  receipts, manifiestos y diagnósticos pequeños.
-34 tests focalizados PASS, incluido el contrato de datos correcto/incorrecto.
  Fuente del intento original archivada en `ecae527`; corrección `bea74ef`.
- rc7, física, geometría, CFL, MUSCL, HLLC, tobera, salida y criterios originales
  permanecen intactos. Commits locales, sin push.

## Siguiente etapa permitida

La periodicidad44 ya no es la incertidumbre pendiente de este caso. Falta
comparar soluciones periódicas de mallas propias, comenzando por una sola
ventana88 de máximo6 ciclos/300s con nueva identidad diagnóstica, mismo estado
físico conservativamente representado y detector nuevo. El reloj físico y la
combustión en curso se conservan; el contador del detector será relativo.
Su preparación está probada, pero la corrida requiere protocolo registrado.
No iniciar176 ni campaña completa automáticamente.
