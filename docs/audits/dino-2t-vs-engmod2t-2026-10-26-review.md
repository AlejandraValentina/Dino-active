# Dino 2T frente a EngMod2T: revisión de la auditoría

Fecha: 2026-10-26. Código inspeccionado: `2f2d722a9e3bcbe31be878e130fbce974048652a`.

Documento de referencia: [auditoría aportada](dino-2t-vs-engmod2t-2026-10-26.md). Se conserva intacto. Sus instrucciones para trabajos posteriores y su hoja de ruta se consideran propuestas, no autorización de implementación. Esta revisión usa inspección de código, receipts e informes existentes y consulta de documentación oficial. No ejecuta simulaciones, builds, pruebas ni cambios físicos. Es una revisión del mismo agente, no una auditoría independiente ni una comparación experimental entre programas.

## Dictamen

Dino tiene una baseline Desktop TRIAL aceptada funcionalmente y una infraestructura de trazabilidad verificable. La evidencia disponible no acredita todavía su capacidad de predecir potencia o de ordenar correctamente dos diseños de escape reales. EngMod2T declara una cobertura de modelado y análisis mucho mayor. La comparación permite identificar brechas funcionales; no permite asignar una relación de precisión ni de velocidad entre ambos productos sin un caso común medido.

La auditoría aportada es útil como inventario técnico y registro de riesgos. Su conclusión física debe moderarse: H1 es una hipótesis relevante que merece una prueba específica si se autoriza, pero sus consecuencias cuantitativas sobre el motor aún no están demostradas.

## Comparación con el producto comercial

EngMod2T se describe como un simulador de ciclo completo con preprocesador, simulador, posprocesador y herramientas de lotes. La página oficial declara gasdinámica en conductos, puertos y plenums. [Introducción oficial](https://vannik.co.za/EngMod2T.htm).

| Aspecto | Dino: evidencia disponible | EngMod2T: declaración pública | Evaluación |
|---|---|---|---|
| Uso Desktop | CRV1 rc7 registra creación, edición, guardado, ejecución y comparación | Suite de preparación, simulación y análisis | Dino tiene un recorrido funcional aceptado, de alcance menor |
| Configuraciones | Motor integrado monocilíndrico con cilindro/cárter y conductos | 1–8 cilindros, varias arquitecturas, admisiones y sobrealimentación | Brecha funcional documentada |
| Combustión y barrido | Cierres simplificados y configuraciones sintéticas según código e informe aportado | Dos zonas, combustión prescrita o turbulenta; barrido Blair refinado | Mayor cobertura declarada del comercial; exactitud relativa sin determinar |
| Gasdinámica | HLLC, SSPRK2; el bucle interior integrado usa estados de celdas adyacentes sin reconstrucción espacial | Método GPB; detalles numéricos públicos limitados | Orden espacial y acoplamiento de Dino necesitan evidencia específica de adecuación |
| Resultados | Curvas y diagnósticos, con limitaciones de interfaz documentadas | Potencia, torque, presiones medias, eficiencias de carga, consumo y temperaturas | Mayor cobertura de análisis declarada del comercial |
| Trazabilidad | Hashes, ledgers y checkpoints con evidencia local | Sin detalle equivalente en las páginas consultadas | Fortaleza documentada de Dino; superioridad relativa no establecida |
| Velocidad | Corridas breves y tiempos históricos/proyecciones registrados | Sin benchmark comparable consultado | No se puede cuantificar la diferencia entre productos |
| Validación predictiva | No se aportó un caso del mismo motor contrastado experimentalmente que cierre la validación | El fabricante declara aplicaciones; no se reprodujeron sus casos | La documentación comercial no sustituye una validación independiente |

Fuentes de las capacidades comerciales: [descripción detallada](https://vannik.co.za/EngMod2TDetails.htm) y [salidas por RPM](https://vannik.co.za/EngMod2T%20-%20OutputsRPM.htm), consultadas el 2026-10-26. Se atribuyen al fabricante, sin certificarlas mediante ejecución del programa.

## Revisión de los hallazgos de la auditoría aportada

### H1: intercambio cámara–conducto

**Confirmado por inspección:** `motorsim/coupling.py::interface_flux` construye un estado de cámara con velocidad cero, resuelve HLLC y escala el flujo por área. El integrado utiliza esta función en conexiones de cilindro y conductos. El contrato `docs/gasdynamic/0d_1d_coupling_r1.md` describe una conexión directa y excluye explícitamente Cd, puerto y apertura. Existe una cuestión de alcance del modelo que debe resolverse documental y físicamente.

**Pendiente de demostración:** las relaciones 0,14–0,40 entre caudal Dino y caudal de tobera proceden de la reducción offline del documento aportado; esta revisión no recalculó ni verificó sus hashes. Aunque la reducción fuera aritméticamente correcta, compara un flujo numérico acoplado no estacionario con una referencia cuasiestacionaria usando presión de celda como contrapresión. Esa comparación detecta una diferencia entre modelos, pero por sí sola no establece el caudal verdadero de la lumbrera ni el error de potencia.

La aproximación acústica y la fórmula de Bernoulli corresponden a hipótesis distintas. Su discrepancia motiva un benchmark con condiciones y referencia compatibles; no demuestra que todo el motor respire entre tres y cinco veces menos de lo debido. Una cámara representada con velocidad macroscópica cero tampoco constituye por sí misma un error: importa la ley de conexión y su dominio de validez.

**Clasificación:** riesgo físico prioritario, con evidencia de implementación y de alcance contractual; magnitud del sesgo e influencia causal sobre potencia aún no determinadas. Sustituir en el documento expresiones como “por qué es incorrecto”, “caudales subestimados 2,5–7×” y la conclusión de “3–5× menos” por formulaciones condicionales hasta contar con una referencia apropiada.

### Disipación y sensibilidad al diseño

El bucle de `IntegratedEngine2T` llama HLLC entre primitivas de celdas vecinas. Esto respalda la descripción de primer orden espacial en esa ruta. Los porcentajes de amplitud citados corresponden a un pulso concreto; no se trasladan directamente a una pérdida porcentual de potencia o a toda onda de escape.

Sin independencia de malla periódica ni una incertidumbre numérica acotada, las diferencias pequeñas A/B no permiten asegurar una mejora física del diseño. Es una limitación suficiente para restringir las afirmaciones predictivas, aunque H1 todavía no esté confirmada.

### X30 y precisión

Comparar un motor sintético de 125 cc con un X30 distinto no produce un error de predicción válido. No permite atribuir el cociente de potencias a H1 ni a un componente concreto. Sigue siendo necesario disponer de la geometría indispensable del motor de referencia y comparar las mismas condiciones y plano de potencia.

La conservación contable y la periodicidad prueban propiedades distintas de la exactitud experimental. La aceptación CRV1 `PASS_FUNCTIONAL_TRIAL` también tiene un alcance funcional explícito. Ninguna de esas evidencias acredita por sí sola precisión comercial.

## Actualización de rendimiento y baseline

- CRV1 rc7 aceptada: productor `fc27542155840cdadbcc2b591ae5cd8e99031899`; SHA-256 del ZIP `2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`, según `results/dino-commercial-readiness-v1/acceptance/receipt.json`. Esta revisión leyó el receipt; no recalculó el hash del paquete.
- Performance V2 registra 7,50–8,36 % de mejora y proyecta 45,28 minutos para seis puntos. La proyección no es una nueva curva medida. Los tiempos históricos de aproximadamente 71 minutos deben identificarse como históricos, sin presentarlos como el rendimiento actual medido.
- V3 permanece congelada y deshabilitada por decisión del usuario. La periodicidad temprana no demostró equivalencia del estado completo.
- V4 ensayó únicamente HLLC compilado con un adaptador diagnóstico: tres ciclos Python 13,18 s; Numba 11,84 s sin JIT, 13,54 s incluyendo 1,70 s inicial; RSS 101,7 frente a 191,0 MiB. Los checkpoints de ese caso coincidieron. Fue descartado para integración.
- V4 consta de un par de corridas integrales cortas: no demuestra reproducibilidad estadística, amortización de JIT en campañas largas ni que toda compilación del núcleo sea inútil. Tampoco acredita 2× de aceleración. Su rechazo no debe ampliarse a backends o componentes que no se probaron.

Fuentes locales: `results/integrated-performance-v2/report.md` y `results/integrated-performance-v4/report.md`. No se mezclan tiempos perfilados, tiempos sin profiler, estimaciones de campañas y tiempos de un ejecutable empaquetado.

## Decisión de producto que permite la evidencia

Mantener la descripción de Dino como baseline funcional TRIAL con capacidades de simulación exploratoria y trazabilidad. No hay base suficiente para presentarlo como sustituto predictivo validado de EngMod2T, atribuirle una precisión porcentual o afirmar superioridad de velocidad o conservación frente al comercial.

Si se decide autorizar trabajo físico posterior, el resultado más informativo sería un benchmark aislado del intercambio cámara–restricción–conducto con referencia, condiciones de contorno y régimen explícitos. Esa propuesta no se ejecuta ni abre una nueva etapa en esta revisión. Primero se debe establecer si el problema denunciado existe bajo condiciones comparables; después correspondería decidir cualquier modificación de modelo.
