# Diagnóstico 1000 rpm — observación, sin corrección

Ciclo 1. Último rechazo por error local antes de la parada por mínimo de paso. No existe ciclo completo ni W_C/pmax aceptados.

| Ángulo ° | h actual ° | medio paso actual ° | dt completo s | dt solicitado completo s | dt solicitado medio s | error normalizado |
| --- | --- | --- | --- | --- | --- | --- |
| 181.4285274 | 0.002276846297 | 0.001138423149 | 3.794743828e-07 | 2.353756301e-07 | 1.176878151e-07 | 6.431575698 |


La propuesta siguiente es h=0,00141225378068°, medio paso=0,000706126890342° <0,001°. El intento actual sí respetaba el mínimo. Componente dominante C.F: diferencia entre paso completo y dos medios, dividida por15 y por la escala contractual. La reproducción offline a idéntico h devuelve exactamente el error observado.

## Error por componente

| Componente | Estado inicial | Completo | Dos medios | Estimación absoluta | Escala | Error normalizado |
| --- | --- | --- | --- | --- | --- | --- |
| I.m | 3.648771955e-05 | 3.648771955e-05 | 3.648771955e-05 | 4.517509052e-22 | 1.124631587e-11 | 4.016879044e-11 |
| I.U | 8.97597901 | 8.97597901 | 8.97597901 | 1.184237893e-16 | 2.992793703e-06 | 3.956964664e-11 |
| I.F | 3.648771955e-05 | 3.648771955e-05 | 3.648771955e-05 | 4.517509052e-22 | 1.124631587e-11 | 4.016879044e-11 |
| K.m | 0.0003202302257 | 0.0003202302626 | 0.0003202302313 | 2.086325264e-12 | 9.636906939e-11 | 0.02164932459 |
| K.U | 88.36690181 | 88.36693794 | 88.36692551 | 8.284202067e-07 | 2.681007765e-05 | 0.03089958252 |
| K.F | 0.0003167564143 | 0.0003167563774 | 0.0003167563484 | 1.929662181e-12 | 9.53269243e-11 | 0.02024257255 |
| C.m | 9.319206578e-05 | 9.318469889e-05 | 9.318473018e-05 | 2.086235559e-12 | 2.825761973e-11 | 0.07382913277 |
| C.U | 51.80437351 | 51.79883667 | 51.7988491 | 8.28372374e-07 | 1.584131205e-05 | 0.0522919043 |
| C.F | 0 | 3.692889118e-11 | 6.587288833e-11 | 1.929599809e-12 | 3.000197619e-13 | 6.431575698 |
| E.m | 7.421758353e-05 | 7.42164662e-05 | 7.42164662e-05 | 8.973670331e-17 | 2.256527506e-11 | 3.976760889e-06 |
| E.U | 31.68469218 | 31.6853243 | 31.68532431 | 4.788086964e-11 | 9.805597292e-06 | 4.88301408e-06 |
| E.F | 0 | 0 | 9.355613334e-16 | 6.237075556e-17 | 3.000000003e-13 | 0.0002079025183 |


## Estado al comienzo del intento

| CV | p Pa | T K | m kg | F kg | Y | U J |
| --- | --- | --- | --- | --- | --- | --- |
| I | 100000 | 300 | 3.648771955e-05 | 3.648771955e-05 | 1 | 8.97597901 |
| K | 123706.5615 | 336.521995 | 0.0003202302257 | 0.0003167564143 | 0.989152144 | 88.36690181 |
| C | 123714.219 | 677.912489 | 9.319206578e-05 | 0 | 0 | 51.80437351 |
| E | 105898.283 | 520.6295689 | 7.421758353e-05 | 0 | 0 | 31.68469218 |


| CV | dm/dt kg/s | dU/dt W | dF/dt kg/s |
| --- | --- | --- | --- |
| I | 1.402076988e-11 | 4.656297676e-06 | 1.402076988e-11 |
| K | 0.0004868024582 | 350.407699 | 0 |
| C | -0.01980685609 | -14849.12413 | 0 |
| E | -0.002938752245 | 1670.145444 | 0 |


## Enlaces y geometría

| Enlace | Área m² | Caudal kg/s | Fresca kg/s | Δp izquierda−derecha Pa | Donante | Retorno |
| --- | --- | --- | --- | --- | --- | --- |
| 0: reservoir-in→I | 0.0003141592654 | 1.402076988e-11 | 1.402076988e-11 | 2.440210665e-07 | reservoir-in | False |
| 1: I→K | 0 | 0 | 0 | -23706.56146 | — | False |
| 2: K→C | 0.00012 | -0.0002434012291 | -0 | -7.65759011 | C | True |
| 3: K→C | 0.00012 | -0.0002434012291 | -0 | -7.65759011 | C | True |
| 4: C→E | 0.0002 | 0.01932005363 | 0 | 17815.93605 | C | False |
| 5: E→reservoir-out | 0.0003141592654 | 0.02225880588 | 0 | 5898.282999 | E | False |


Todos los caudales, entalpías, estados de cada etapa y derivadas están en1000-diagnostic.json. Admisión I–K cerrada; transferencias y escape abiertos. Aporte térmico inactivo.

| Evento | Fase ° | Distancia angular ° |
| --- | --- | --- |
| intake-open | 270 | 88.57147258 |
| intake-close | 90 | 91.42852742 |
| heat-start | 350 | 168.5714726 |
| heat-end | 30 | 151.4285274 |
| Escape-open | 90 | 91.42852742 |
| Escape-close | 270 | 88.57147258 |
| Transferencia 1-open | 117.334444 | 64.09408344 |
| Transferencia 1-close | 242.665556 | 61.2370286 |
| Transferencia 2-open | 117.334444 | 64.09408344 |
| Transferencia 2-close | 242.665556 | 61.2370286 |


No coincide con apertura/cierre ni inicio/fin del calor. Las áreas permanecen constantes en este intento. El cambio relevante es de donante en ambas transferencias K↔C: Δp pasa de−7,65759 a+5,58971Pa entre K1 yK4 del paso completo. La trayectoria de dos medios resuelve la entrada de fresca en otras subetapas. Con F_C inicial=0, el error C.F domina aunque los errores de m/U son <1.

**Mecanismo probable: F (cambio de sentido/donante en enlaces internos no regularizados cerca de Δp=0), con E (F_C=0).** No hay evidencia de evento geométrico A ni error de implementación del estimador D. La regularización exterior C no actúa sobre los enlaces2/3. No se ha realizado análisis espectral que permita afirmar rigidez temporal B. El coeficiente1/15 se aplica correctamente; su hipótesis de suavidad puede perder calidad al cruzar el cambio de donante, sin que eso constituya un bug demostrado.

No se calcula una continuación por debajo del mínimo ni se cambia ninguna ley.
