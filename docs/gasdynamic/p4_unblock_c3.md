# P4 UNBLOCK C3 — retorno 1D→0D

## Alcance

Se ejecutó el benchmark aislado de una cámara 0D finita acoplada a un ducto 1D uniforme de área fija y pared rígida reflectante. Se conservaron CFL, backend, EOS y umbrales contractuales; no se modificó el solver ni se repitieron campañas G2.

## Pre-registro y evidencia

La configuración, estados iniciales, geometría, mallas N=50/100, horizonte y ventana de retorno están en `results/p4-unblock-c3-20260923/c3/`. La señal de salida y la reflexión rígida aparecen en las trazas de interfaz; el flujo invierte su signo durante el retorno. Las trazas de cámara muestran respuesta de presión y energía.

## Conservación y refinamiento

Los dos niveles conservaron el residuo reportado por el fixture y mantuvieron admisibilidad. La persistencia de la señal se observó en ambas mallas. Esto no sustituye un observable contractual de convergencia del retorno.

## Decisión C3

El benchmark queda `P4_SCI_C3_INCONCLUSIVE`: faltan una instantánea de Riemann de retorno independiente y una métrica explícita de reacción de momento en la interfaz. Por ello no se declara verificación completa de los mecanismos de retorno ni se desbloquea P4.

## G2 y estado P4

Se realizó únicamente revisión offline de la evidencia G2 existente. No se ejecutó un nuevo G2. El estado final es `P4_FINAL_BLOCKED_C3_INCONCLUSIVE`; P5 no comenzó y E13-R1 no fue modificado.

## Pruebas y límites

Los artefactos conservan la ejecución C3 y el gap documental. Las pruebas focales y OpenSpec se registran en `regression_tests.json` y deben leerse junto con su salida de ejecución. `redme.txt` permanece eliminado y sin stage.
