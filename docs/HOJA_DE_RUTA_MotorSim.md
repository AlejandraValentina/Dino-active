# MotorSim — Hoja de ruta

Fecha: 14 de septiembre de 2026.
Estado: propuesta de dirección y prioridades. No es una orden de implementar todas las etapas ni una declaración de capacidades existentes.

## 1. Objetivo del producto

Una aplicación de escritorio para describir motores de dos y cuatro tiempos, revisar su geometría, ejecutar los modelos de simulación admitidos y comparar configuraciones con resultados interpretables.

Secuencia de utilidad: **guardar un motor → comprobar su geometría → describir sus sistemas → calcular un caso → comparar modificaciones**.

Python y PySide6/Qt Widgets se mantienen. El rediseño se incorpora al editor actual; no constituye otra aplicación ni exige cambiar de tecnología.

## 2. Punto de partida

El README publicado consultado informa una base de escritorio implementada para nombre, tipo 2T/4T y archivos JSON, con pruebas automatizadas y recorrido manual completo de Windows pendiente [1]. Las capturas compartidas muestran trabajo visual posterior. La nueva ficha de características fue definida en la conversación, pero este documento no da por comprobada su implementación.

Prioridad propuesta: datos generales para 2T y 4T desde el editor común; primera simulación completa de un caso 2T; extensión posterior a un caso 4T. Tener un número de cilindros en una ficha no equivale a disponer de simulación multicilíndrica.

## Estado de avance

`refinamiento-ui-final`: presentación de las ocho vistas y paneles adaptables,
sin ampliar capacidades físicas. 247 pruebas, inspección Windows en tres escalas
y revisión independiente puntual registradas en sus tareas; aceptación manual
final pendiente. La candidata rc4 refinada desde `d6c4e19b` conserva los paquetes
anteriores y aprobó el recorrido automatizado del EXE (un punto y cancelación
breve, históricos y CSV). No acredita validación experimental ni aceptación manual.

`ejemplos-precargados`: cuatro proyectos sintéticos derivados de los casos canónicos
2T/4T y variantes de compresión 8.2, carga protegida y candidata rc4 construida
desde `4e7e559` y comprobada en Windows mediante automatización. 245 pruebas y
revisión puntual, sin nuevas integraciones. Sin ampliar capacidades físicas ni
cerrar aceptación manual; evidencia en sus tareas OpenSpec.

Reorganización UX autorizada: [reorganizacion-ui-final](../openspec/changes/reorganizacion-ui-final/tasks.md).
Navegación por tareas, configuración contextual y análisis embebido implementados;
sin ampliar capacidades ni modificar las entregas científicas. Pruebas, revisión
puntual e inspección Windows registradas; candidata rc3 construida desde `16097c4`
y comprobada por automatización del EXE, conserva rc1/rc2. 238 pruebas aprobadas.
Aceptación manual final, equipo sin Python y offline aislado pendientes.

Seguimiento de la copia local comprobada el 16/09/2026. Las entregas 1 y 2 están
autorizadas y aceptadas. Entrega 3 autorizada para lumbreras,
cárter y admisión por falda recta; decisión de modalidad inicial resuelta. Entrega 4 autorizada el 15/09/2026; entrega 5 ampliada expresamente a Qt y geometría del editor bajo condiciones de referencia, sin ondas ni barridos. Entrega 6 ampliada a punto RPM 2500–3500 y barrido secuencial 2–5 puntos, conservando comparación/CSV; importación externa y contraste descriptivo autorizados el 16/09/2026, sin nuevos cálculos. Contraste con mediciones reales pendiente. Entregas 7 y 8 autorizadas conjuntamente el 16/09/2026 mediante `cuatro-tiempos-basico`, con puertas numéricas previas a la integración. La usuaria comunicó
la realización del recorrido manual, incluido uso sin Internet, y aceptó ambas
entregas el 14/09/2026; su evidencia se registra separada en los cambios enlazados.

| Entrega | Estado | Cambio | Observación |
| --- | --- | --- | --- |
| 1. Características del motor y diseño moderno | Completada | [caracteristicas-motor](../openspec/changes/caracteristicas-motor/tasks.md) | Comprobaciones acreditadas; aceptada por la usuaria. |
| 2. Geometría y cinemática | Completada | [geometria-cinematica](../openspec/changes/geometria-cinematica/tasks.md) | Comprobaciones acreditadas; aceptada por la usuaria. |
| 3. Configuración específica 2T | Completada | [configuracion-2t](../openspec/changes/configuracion-2t/tasks.md) | Lumbreras/cárter y admisión por falda comprobados; 72 pruebas finales y captura Windows. Sin aceptación manual de la usuaria ni validez predictiva. |
| 4. Admisión y escape | Completada | [conductos-admision-escape](../openspec/changes/conductos-admision-escape/tasks.md) | Editor, orden, perfiles y JSON v5 comprobados; 85 pruebas finales y captura Windows/150 %. Sin aceptación manual de la usuaria. |
| 5. Primer caso de simulación 2T | Completada para el alcance acotado implementado | [simulacion-2t](../openspec/changes/simulacion-2t/tasks.md) | Editor admitido → comprobar → ejecutar B/100 Pa a 3000 rpm → consultar/guardar/reabrir con procedencia. Referencia preservada; A/B/C autorizados convergen y contraste B/C aprobado. 146 pruebas, revisión puntual y captura Windows/150 %. Aceptación manual pendiente, separada de implementación; sin calibración ni validez general. |
| 6. Barridos, comparación y contraste experimental | En curso | [comparacion-resultados](../openspec/changes/comparacion-resultados/tasks.md) | Comparación/CSV y RPM/barrido acotado implementados y comprobados. Cinco puntos reales autorizados convergen, referencia 3000 exacta y contrastes B/C extremos aprobados (68,327 s integración). Windows/150 %, pruebas y revisión puntual registradas. Importación CSV externa y contraste descriptivo implementados/comprobados con archivos sintéticos, 50 pruebas y Windows/150 %. Contraste con mediciones reales pendiente mientras falten datos adecuados; validación experimental no realizada. Sin aceptación manual atribuida. |
| 7. Configuración específica 4T | Completada para el alcance geométrico | [cuatro-tiempos-basico](../openspec/changes/cuatro-tiempos-basico/tasks.md) | Válvulas idealizadas, eventos/cruce analíticos, conductos independientes y JSON v6; pruebas y Windows/150 % comprobados. Sin aceptación manual atribuida. |
| 8. Primer caso de simulación 4T | Completada para el alcance 0D autorizado | [cuatro-tiempos-basico](../openspec/changes/cuatro-tiempos-basico/tasks.md) | R1 histórica fallida en tendencia preservada; R2 aprobada por estabilidad práctica y C50/banda aprobada. Editor, ejecución, resultados, comparación y barrido 4T comprobados; 12 ejecuciones/249,015 s, contrastes B/C y regresión 2T exacta. Windows/150 % y 219 pruebas. Aceptación manual y validación experimental pendientes y separadas. |

Candidata de distribución Windows **0.1.0-rc1** construida desde `f46613e`, ZIP
extraído comprobado en Windows 10 x64/150 %, tres puntos numéricamente iguales
a sus referencias. **Por verificar**: desglose temporal 2T, equipo sin Python y
offline aislado; aceptación manual separada. Evidencia mediante
[distribucion-windows](../openspec/changes/distribucion-windows/tasks.md). No cambia
el estado técnico funcional ni elimina pendientes manuales o experimentales.

Hardening: **0.1.0-rc2 construida desde 580c3f8e y comprobada**, tiempos futuros
2T corregidos, 228 pruebas y dos puntos completos numéricamente exactos.
**Cierre técnico parcial / Por verificar**: parada histórica rc1 clasificada F
(evidencia insuficiente; única reproducción cooperativa), sin Python/offline reales
pendientes. Aceptación manual y validación experimental separadas. Sin modificar
física ni estados de las entregas; candidata rc1 preservada.

Estados: **Pendiente**, todavía no iniciada; **En curso**, iniciada e incompleta;
**Por verificar**, implementación preparada con comprobaciones pendientes;
**Completada**, comportamiento y comprobaciones de cierre acreditados.
Las tareas y su evidencia se mantienen únicamente en el cambio enlazado.

## 3. Entregas previstas

| Orden | Entrega | Capacidad utilizable al cerrar | Límite principal |
| --- | --- | --- | --- |
| 1 | Características del motor y diseño moderno | Editar y recuperar la ficha común; calcular cilindrada | Sin simulación |
| 2 | Geometría y cinemática | Examinar posición del pistón y volumen según ángulo de cigüeñal | Mecanismo simple; sin fuerzas ni combustión |
| 3 | Configuración específica 2T | Describir lumbreras y cárter del primer tipo admitido; revisar eventos geométricos | Una configuración inicial, no todas las arquitecturas 2T |
| 4 | Admisión y escape | Introducir dimensiones de conductos por tramos y revisar un esquema | Geometría, no predicción de resonancia |
| 5 | Primer caso de simulación 2T | Ejecutar un motor admitido en un régimen, inspeccionar y guardar sus resultados | Un caso definido y un punto de funcionamiento |
| 6 | Barridos, comparación y contraste experimental | Comparar puntos/configuraciones e importar datos medidos | Series acotadas; sin optimización automática |
| 7 | Configuración específica 4T | Registrar distribución fija y perfiles de alzada; revisar eventos | Sin distribución variable ni dinámica del tren de válvulas |
| 8 | Primer caso de simulación 4T | Ejecutar y comparar un 4T usando la aplicación y visualización existentes | Una configuración inicial, no un simulador universal |

Las entregas 1 y 2 son las próximas prioridades. La descripción de las posteriores fija dirección y límites, no métodos numéricos ni tareas exhaustivas.

### Entrega 1 — Características del motor y diseño moderno

Conservar nombre y tipo de motor. Añadir fabricante, modelo, número de cilindros, diámetro, carrera, longitud de biela entre centros, relación de compresión geométrica y observaciones. Permitir guardar características no informadas sin inventar valores y distinguirlas de entradas inválidas.

Calcular cilindrada por cilindro y total, bajo la hipótesis explícita de geometría común. La cilindrada procede del área del cilindro multiplicada por la carrera; la total suma los desplazamientos [2]. La relación de compresión geométrica es una relación de volúmenes, no una presión [3].

Diseño: fondo liso, tipografía de interfaz legible, acciones compactas y grupos Datos generales/Geometría. Sin cuadrícula, barra lateral vacía ni estados repetidos. Mantener el funcionamiento por teclado y el escalado Windows. La referencia de Stitch inspira el estilo, no añade módulos.

Cierre: editar, guardar, cerrar y reabrir la ficha; leer archivos antiguos; comprobar cálculos y conservación del trabajo ante errores. No volver a rediseñar toda la ventana en cada entrega posterior.

### Entrega 2 — Geometría y cinemática

Mostrar posición del pistón y volumen del cilindro respecto al ángulo de cigüeñal, con un esquema 2D sencillo y curvas calculadas. Usar inicialmente un mecanismo biela-manivela sin descentrado. Identificar puntos muertos y convenciones angulares; el ciclo 4T requiere distinguir sus dos revoluciones aunque se repita la posición mecánica [2].

Calcular el volumen de cámara a partir de la cilindrada por cilindro y la compresión geométrica cuando ambos datos estén disponibles. No crear dos entradas independientes contradictorias para el mismo volumen.

La biela debe ser compatible con el radio de manivela para el mecanismo admitido. Un esquema geométrico no certifica resistencia, holguras ni ausencia de interferencias de piezas reales.

Cierre: las curvas cambian al editar dimensiones, coinciden con casos geométricos conocidos y no se presentan resultados anteriores cuando faltan datos. No exige animación 3D ni cálculo de fuerzas.

### Entrega 3 — Configuración específica 2T

Elegir la primera configuración admitida y registrar las dimensiones necesarias de escape, transferencias y admisión, más el volumen de referencia del cárter. Definir una referencia inequívoca para alturas y ángulos.

Comenzar con una representación geométrica sencilla de lumbrera. Mostrar apertura, cierre, duración y área geométrica descubierta cuando las entradas permitan calcularla. Una dimensión derivada no será otra entrada libre que pueda contradecir la geometría.

No asumir que admisión por pistón, láminas y disco rotativo tienen el mismo comportamiento. La primera implementación abarcará solo la elegida; el resto queda identificado como no admitido, no aproximado silenciosamente.

El área descubierta y los eventos no equivalen a caudal ni a calidad de barrido. La distinción entre masa suministrada, retenida y composición de carga forma parte del problema físico de intercambio de gases 2T [4].

Desde esta entrega se identifica un motor de referencia y qué datos están disponibles, estimados o ausentes. No es necesario bloquear el editor por falta de mediciones experimentales.

Cierre: guardar y recuperar la configuración admitida y revisar sus eventos geométricos con ejemplos calculados de manera independiente.

### Entrega 4 — Admisión y escape

Editor por tramos con longitud y dimensiones interiores. Comenzar con secciones circulares, tubos y conos; incluir solo los componentes necesarios del primer motor 2T. Mostrar un perfil 2D, conexiones fijas y dimensiones coherentes. No construir un editor universal de redes ni CAD.

No mostrar una potencia estimada o una frecuencia óptima solo por dibujar el escape. La simulación gasdinámica de conductos, puertos y volúmenes es una capacidad distinta de su preprocesado geométrico; esa separación también aparece en la descripción oficial de EngMod2T [5].

Cierre: reconstruir una configuración desde el archivo y revisar el perfil y sus dimensiones sin cálculos de funcionamiento.

### Entrega 5 — Primer caso de simulación 2T

Esta es la entrega de mayor riesgo técnico; no se considera un formulario más. Se aborda primero con una prueba de viabilidad corta y cronometrada, y después con el primer ciclo acoplado utilizable desde la aplicación.

Antes del núcleo se concretan, dentro de esta entrega, el motor admitido, un régimen, la condición de carga, combustible y encendido, condiciones de contorno, aproximaciones, magnitudes de comparación y presupuesto de ejecución. La propuesta inicial es un monocilíndrico atmosférico de encendido por chispa, con una admisión y un circuito fijos. No se elige todavía un algoritmo por su nombre ni se hereda automáticamente el solver anterior.

Un caso sintético explícitamente identificado puede verificar el funcionamiento del cálculo. No sustituye un motor medido para establecer validez predictiva.

El caso integrado debe incluir el tratamiento declarado del intercambio de gases, compresión, aporte de energía y expansión. Un ciclo ideal aislado puede ser una prueba interna; no se presenta como simulación completa del motor 2T.

Resultados iniciales: presión frente a ángulo, diagrama presión-volumen y trabajo indicado, junto con las magnitudes adicionales que efectivamente calcule el modelo. No mostrar potencia al eje sin modelar o declarar las pérdidas necesarias: potencia indicada y potencia al freno son magnitudes distintas [6].

Si evaluar un escape sintonizado es una capacidad objetivo de este primer modelo, la prueba debe demostrar el tratamiento de las ondas correspondiente; no se puede obtener esa capacidad cambiando una etiqueta de la interfaz [5]. Cuando el modelo aún no la represente, la limitación debe impedir conclusiones de sintonía.

La ventana debe continuar respondiendo, informar avance real y permitir cancelar. Cada resultado conserva las entradas y versión del modelo que lo generaron. Editar el motor no modifica silenciosamente resultados anteriores.

Cierre: un punto reproducible, comprobaciones del cálculo acordes al modelo, criterio de convergencia cuando corresponda, coste medido y limitaciones visibles. Un punto fallido o no convergido no se muestra como resultado aceptado.

### Entrega 6 — Barridos, comparación y contraste experimental

Añadir una serie pequeña de regímenes, comparación entre una configuración base y una modificación, exportación CSV e importación de curvas medidas para el motor de referencia.

Distinguir dato medido, resultado simulado y valor geométrico. No mezclar curvas obtenidas en condiciones incompatibles ni comparar potencia indicada con potencia medida al eje sin reconciliar magnitudes [6].

Los parámetros ajustados con un conjunto de mediciones se contrastan después con puntos o configuraciones distintos. Un ajuste favorable a los datos usados para calibrar no se presenta como validación independiente.

La comprobación experimental comienza con el primer resultado utilizable si existen mediciones; esta entrega la incorpora al flujo de trabajo. No se posterga toda verificación hasta el final del proyecto.

Cierre: cambiar un parámetro admitido, ejecutar, identificar qué cambió, superponer resultados y conservar la procedencia de ambos. Sin barridos masivos ni optimización automática.

### Entrega 7 — Configuración específica 4T

Añadir válvulas de admisión y escape, dimensiones pertinentes, distribución fija y una representación de la alzada respecto al ángulo. Mostrar apertura, cierre, duración y cruce con referencia angular inequívoca.

Los ángulos de apertura y cierre por sí solos no definen un perfil de alzada único. Los perfiles ingresados, importados o construidos con una ley explícita deben distinguirse. La documentación de EngMod4T separa perfiles de alzada, distribución y datos de descarga/flujo [7].

No equiparar área geométrica de paso con un coeficiente de descarga conocido. No añadir sincronización variable, flexibilidad de levas, rebote de válvulas ni una biblioteca universal.

Cierre: editar y recuperar una distribución fija, revisar su diagrama y conservar los datos comunes al cambiar entre las secciones del proyecto.

### Entrega 8 — Primer caso de simulación 4T

Reutilizar persistencia, geometría que sea aplicable, ejecución, gráficos y comparación. Incorporar el tratamiento específico de válvulas e intercambio de gases del ciclo 4T; no convertir el 2T mediante un simple factor de revoluciones [2,4].

Comenzar con un monocilíndrico atmosférico de encendido por chispa, distribución fija y un régimen. Después incorporar el mismo barrido acotado y contraste experimental establecidos para el 2T.

Cierre: un 4T admitido ejecutable, reproducible y comparado con una referencia identificada, sin duplicar toda la aplicación ni declarar soporte para configuraciones no comprobadas.

## 4. Mejoras de producto complementarias

Empaquetado ejecutable para Windows y acceso directo; exportación de la ficha técnica; duplicación de proyectos; lista de archivos recientes. Son mejoras independientes, no requisitos para desarrollar el núcleo físico ni una autorización para implementarlas todas.

El empaquetado puede entregarse antes de la simulación 4T cuando exista una versión estable que resulte útil distribuir. No se necesita esperar al producto completo.

## 5. Reglas transversales

- Cada entrega termina en una capacidad observable y preserva los proyectos anteriores. Guardar datos incompletos no equivale a autorizar un cálculo con datos ausentes.
- La verificación acompaña cada fórmula y función. La evidencia experimental determina qué afirmaciones predictivas se pueden hacer; cantidad de tests y aspecto visual no la reemplazan.
- Antes de ampliar el núcleo se mide un caso representativo. Meta inicial propuesta de uso: hasta un minuto por punto típico y hasta diez minutos para diez puntos en un equipo de referencia definido. Son objetivos de diseño por comprobar, no prestaciones prometidas ni permiso para relajar exactitud. Un incumplimiento exige revisar el compromiso entre modelo, método y coste.
- No ejecutar corridas largas sin avance observable y una estimación basada en mediciones. No usar reintentos indefinidos como estrategia.
- Una sola hoja de ruta. OpenSpec detalla el cambio activo cuando se vaya a ejecutar; no se generan hoy propuestas y tareas completas para todas las etapas.
- La hoja de ruta no inicia tareas, no modifica la integración global de herramientas y no habilita al agente a continuar con la etapa siguiente sin autorización.

## 6. Fuera de este recorrido inicial

CFD 3D, CAD completo, simulación multicilíndrica acoplada, turbo/sobrealimentación, diésel e inyección directa, química detallada, predicción de emisiones o detonación, optimización automática, nube y plataformas multiagente. Requieren objetivos propios; no entran por haber aparecido en una maqueta.

La prioridad inmediata es terminar la ficha moderna y la geometría útil. El siguiente núcleo es una simulación 2T acotada; el 4T amplía esa base, no provoca otra reconstrucción.

## Referencias

La secuencia, las prioridades y los presupuestos anteriores son propuestas de producto de este documento. Las fuentes sustentan únicamente el estado publicado o las distinciones técnicas indicadas.

[1] README de AlejandraValentina/Dino, consultado el 14/09/2026: https://github.com/AlejandraValentina/Dino/blob/main/README.md

[2] NASA Glenn Research Center, Bore and Stroke: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/bore-and-stroke-old/

[3] NASA Glenn Research Center, Compression Stroke (referencia para la definición geométrica, no adopción de su ciclo ideal como modelo completo): https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/compression-stroke/

[4] MIT OpenCourseWare, 2.61, Lecture 8: Intake and exhaust processes: https://ocw.mit.edu/courses/2-61-internal-combustion-engines-spring-2017/resources/mit2_61s17_lec8/

[5] Vannik Developments, EngMod2T introduction: https://vannik.co.za/EngMod2T.htm

[6] FAA, Aviation Maintenance Technician Handbook — Powerplant, Aircraft Engines (indicated/brake/friction horsepower): https://www.faa.gov/sites/faa.gov/files/03_amtp_ch1.pdf

[7] Vannik Developments, EngMod4T detailed description: https://vannik.co.za/EngMod4TDetails.htm
## Estado de governance P4 → P5 (23/09/2026)

- **P4:** `BLOCKED`; `P4_acceptance = NOT_GRANTED`. La evidencia científica permanece en `P4_FINAL_BLOCKED_C3_INCONCLUSIVE`; P4 no es PASS.
- **P5:** `AUTHORIZED_CONDITIONAL`; dependencia `P4_UNRESOLVED`.
- **Transición:** `CONDITIONALLY_BYPASSED_FOR_DEVELOPMENT`.

P5 comprende intake + transfers 1D: geometría/malla, solver 1D reutilizable, fixtures aislados, topología de acoplamiento con cárter/cilindro, fronteras, conservación, admisibilidad y flujo inverso. `INDEPENDENT_OF_P4`: componentes aislados y sus pruebas. `CONDITIONAL_ON_P4`: cualquier resultado que dependa materialmente del comportamiento gasdinámico integrado. P5 podrá alcanzar `P5_IMPLEMENTATION_VERIFIED_CONDITIONAL`, nunca `P5_FULLY_ACCEPTED` mientras P4 siga bloqueado.

### Ratificación independiente final P4→P8 (30/09/2026)

La revisión independiente final ejecutada desde `78615563ad7f8e4f1dde9ee05226119ffc3433a4` resultó `INDEPENDENT_REVIEW_PASS`. P4 queda `P4_PASS` y su aceptación independiente está otorgada. P5, P6, P7 y P8 quedan `REVALIDATED_ON_P4_PASS`; el bloqueo previo fue una condición de governance ya resuelta, sin reinterpretar ni borrar sus recibos históricos.

P8 conserva exclusivamente la semántica `BOUNDED_TRANSIENT_INDICATED`. La validación experimental permanece `NOT_PERFORMED`. El 2026-10-01 se autorizó iniciar P9 y se preregistró el contrato fijo P9 v1.0 tras validar OpenSpec en modo estricto. Estado actual: `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`; el inventario del workspace no identificó un dataset experimental autorizado suficiente. No se ejecutaron comparaciones P9 ni se reclama validación predictiva. Contrato: [P9 v1.0](../openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md); receipt y hashes: [preregistration.json](../results/p9-readiness-20261001/preregistration.json). La auditoría inicial de readiness se conserva como registro histórico en [reconstrucción P9](../docs/gasdynamic/p9_readiness_contract_reconstruction_20261001.md). Informe de ratificación P4–P8: [revisión final](gasdynamic/p4_p8_independent_final_pass_20260930.md); receipt: [review.json](../results/p4-p8-independent-final-pass-20260930/review.json).
