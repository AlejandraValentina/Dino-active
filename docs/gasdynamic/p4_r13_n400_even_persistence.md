# P4-R13: persistencia de la rama par N400

El horizonte 55–60 se fijó antes de ejecutar y se usó el restart durable de
R12 ciclo54, con NUMBA_FUSED, CFL 0,4, float64, workers=1 y sin early stop.
No se repitieron ciclos 50–54 ni se ejecutaron N350/N300/N500.

La evidencia R12 conserva `state.npz` y metadatos de ciclo54, pero no la historia
angular completa de ese ciclo. Por ello 56 vs 54 no puede reconstruirse sin
repetir R12; se deja explícitamente como brecha de evidencia. Las comparaciones
disponibles 58 vs 56 y 60 vs 58 son PASS, al igual que el control impar 57 vs 55
y 59 vs 57. La secuencia histórica completa queda `50 PASS, 52 PASS, 54 FAIL,
56 [sin historia angular R12], 58 PASS, 60 PASS`.

El fallo 54 se conserva y no se sustituye por el tramo favorable posterior.
Con el criterio de la orden, el resultado se clasifica
**P4_R13_N400_EVEN_INTERMITTENT_NONCLOSURE**: no se acredita cierre eventual
porque falta la comparación contractual 56 vs 54. Conservación, CFL y
admisibilidad de los seis ciclos nuevos son PASS; D1 y E13 siguen pendientes.
No se inicia P4 PASS, E13-R1 ni P5, y el horizonte termina en ciclo60.
