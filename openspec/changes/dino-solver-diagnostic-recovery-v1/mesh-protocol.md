# Protocolo propuesto de refinamiento espacial y separación temporal

**Estado:** diseño; no preregistrado ni autorizado para ejecución. No correr mallas en esta tarea.

## Pregunta y alcance

Evaluar la solución de escape del motor integrado para una geometría y punto de operación congelados. El estudio debe distinguir error de discretización espacial, error temporal, condiciones de frontera e incertidumbre del modelo. No autoriza ranking de diseño, curva RPM ni claim experimental. Las matrices históricas EXHAUST_MESH_V1/V2 quedan inmutables y su conclusión continúa `NOT_ESTABLISHED`.

## Configuración y niveles

- Congelar una variante, geometría de escape, combustible, modelo mecánico, RPM, WOT, condiciones iniciales/de frontera, versión del adaptador, solver y dependencias mediante hashes.
- Resoluciones nominales: 1, 2, 4 y 8 celdas por sección para el mismo perfil geométrico; conservar longitudes, áreas y volúmenes totales, nodos de interfaz y ubicaciones de sensores. Rechazar niveles que no representen la misma geometría.
- Primero completar referencias analíticas de ducto de área constante/suave a cada resolución; estas verifican la implementación numérica y no sustituyen el caso integrado.
- En el caso integrado, evaluar cada nivel con el mismo contrato de periodicidad y observables completos. El máximo de ciclos/budget debe definirse y financiarse en un preregistro separado.

## Separación de error temporal

La corrida primaria debe aplicar el mismo límite físico de paso temporal a todos los niveles, además del evento exacto en límites de puerto, y registrar paso aceptado, rechazo y CFL por subpaso. Si el adaptador no puede aplicar un `dt_max` fijo sin alterar el método, implementar primero una capacidad versionada y probarla con replay; no inferir independencia espacial sólo a CFL nominal constante.

En niveles 2 y 4 se requiere además repetición con `dt_max/2`, manteniendo todo lo demás fijo, para estimar sensibilidad temporal. Una discrepancia temporal material bloquea la comparación espacial hasta que el error temporal sea menor que la incertidumbre de comparación predefinida. Si el presupuesto no cubre la matriz mínima, no iniciar una matriz parcial inconclusiva.

## Observables y comparación

Persistir señales con sus mallas/tiempos originales, sin interpolarlas para producir resultados. Para comparar presión y flujo se podrá calcular, en un evaluador offline versionado, diferencias en fases de ángulo comunes con interpolación exclusivamente como operador de comparación trazado; conservar también las señales nativas. Usar: presión de cilindro y sensores de escape, presión por celda/interfaz, caudal másico firmado, integral de flujo por ciclo, estado de masa/energía/especies por volumen, trabajo indicado y ledgers de conservación. Potencia, torque/BMEP sólo si periodicidad y contrato de outputs los hacen definidos.

## Criterios antes de ejecución

Antes de observar resultados, registrar: incertidumbre numérica de referencia analítica, tolerancias por observable, criterio de monotonía/asintótico, y magnitud mínima que se desea distinguir (por ejemplo, efecto de diseño si ese fuera el objetivo). Las tolerancias no se fijan aquí porque los receipts históricos no justifican un valor de aceptación general. No usar similitud visual ni conservación por sí solas como gate de convergencia. Exigir que las diferencias entre niveles finos caigan debajo de las tolerancias preregistradas y que la corrección temporal sea menor que el error espacial aceptado; de lo contrario `NOT_ESTABLISHED`.

## Recursos, checkpoints y decisión

Un preregistro futuro debe calcular el costo a partir de las mediciones del fixture/perfil y del punto previamente autorizado, añadir margen y memoria por worker, ejecutar con checkpoint por ciclo y punto en root externo, y fijar presupuesto global. Ningún costo de fixture se extrapola como runtime garantizado. No reciclar checkpoint si difiere cualquier hash. Sólo después de preflight, financiación y autorización explícita puede ejecutarse este protocolo.
