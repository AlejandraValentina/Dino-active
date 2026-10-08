# P4-C3-R1 — cierre de evidencia de retorno

## MISSING EVIDENCE

La auditoría de `results/p4-unblock-c3-20260923/` confirma trazas de interfaz y cámara, pero no conserva el estado conservativo de la primera celda ni términos de caras para un balance independiente de momento. La ventana esperada de retorno termina sin un sample posterior suficiente para seleccionar el snapshot contractual.

## ARTIFACT REUSE

Se reutilizaron todos los artefactos existentes. No se repitió C3 porque los datos faltantes no pueden reconstruirse sin ejecutar una captura adicional; no se inventaron estados.

## RETURN SNAPSHOT / EXACT RIEMANN CHECK

La regla predefinida era el primer sample al alcanzar el tiempo esperado con flujo positivo. No existe tal sample en la traza guardada. Por tanto no puede formarse la comparación con `exact_riemann.py` sin datos nuevos.

## INDEPENDENT MOMENTUM BALANCE

Se dejó definido el control de volumen (momento almacenado, flujos de caras y reacción de presión), sin reutilizar una variable productiva. La evidencia disponible no contiene sus términos; el resultado es inconcluso.

## CONSERVATION

La evidencia C3 existente mantiene PASS para masa, energía y especie, y admisibilidad para densidad, presión, temperatura y especie. N=50/100 conserva la respuesta cualitativa de cámara, retorno e inversión de flujo.

## C3 DECISION

`P4_SCI_C3_INCONCLUSIVE`. No se identificó un defecto físico; tampoco se acreditó el acoplamiento de retorno completo.

## FINAL P4 BLOCKER / P5 STATUS

P4 permanece `P4_FINAL_BLOCKED_C3_INCONCLUSIVE`, con G2 E13-R1 no convergente como bloqueo posterior. G2 no se ejecutó nuevamente, P4 no está listo para aceptación humana y P5 no comenzó.
