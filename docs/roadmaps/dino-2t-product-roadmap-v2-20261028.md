# Dino 2T — hoja de ruta de producto V2

> Orden de prioridades reemplazado por la [hoja de ruta única adoptada](dino-2t-unified-roadmap-v1-20261028.md).
> Se conserva este documento como inventario y antecedente, sin activar sus entregas.

Fecha: 2026-10-28. Evaluación documental y de código sobre HEAD `5cf80cc` y
evidencias existentes; no se ejecutaron simulaciones, builds ni tests nuevos.
No se modificaron código de producto, configuraciones, tolerancias ni resultados.

## 1. Dirección y alcance

La nueva instrucción del dueño reemplaza la precedencia del plan anterior
«sin funcionalidad comercial hasta E5». La verificación científica continúa
cuando resuelve una decisión concreta del producto; no constituye una barrera
general para mejorar su uso o rendimiento. El plan anterior se conserva como
historial. Este documento es una propuesta de entregas, no inicia campañas ni
activa automáticamente tareas pendientes de la cola operativa.

**Primer producto objetivo:** un preparador puede representar un monocilíndrico
2T atmosférico dentro de las topologías admitidas, modificar su escape o
distribución, obtener una comparación A/B en un tiempo práctico y contrastarla
con mediciones. Debe saber si está viendo un transitorio, una solución periódica
calculada o una predicción experimentalmente respaldada.

No se necesita igualar primero toda la cobertura de motores de EngMod2T. Sí se
necesita completar ese recorrido para un alcance explícito y útil.

## 2. Qué existe y qué falta realmente

| Capacidad | Implementado y evidencia | Brecha de producto |
|---|---|---|
| Aplicación Windows autónoma | rc7 aceptada: crear/guardar/reabrir proyectos, duplicar variantes, editar escape, ejecutar y comparar resultados, historial y exportación CSV | Conservar esta referencia. Los cambios posteriores en fuentes no quedan aceptados automáticamente por el EXE histórico |
| Geometría y diseño | En fuentes actuales hay diámetro, carrera, biela, volumen de cárter, compresión, lumbreras y eventos derivados, selección de admisión, combustión y pérdidas. El escape permite largos y diámetros por tramo, perfiles y variantes | No falta un editor entero. Falta completar el ingreso de todos los datos necesarios de un motor propio en el alcance elegido: la plantilla todavía aporta conductos, láminas y otros supuestos; seleccionar reed no equivale a definir sus parámetros reales |
| Cálculo integrado y curvas | Solver integrado, coordinador RPM, seis resultados periódicos históricos A/B, gráficos de potencia/torque y presión | No confundir esa evidencia legacy con la verificación de las formulaciones candidatas actuales. Tampoco equivale a validación de un motor real |
| Cancelación, reanudación y persistencia | Checkpoints, identidades y recuperación implementados. La entrega Windows documentó cancelación/reanudación real y equivalencia con ejecución continua | Reutilizar; no reconstruir otro gestor de corridas. Una nueva distribución conserva sus propias pruebas de integración |
| Rendimiento | V1/V2 incorporaron mejoras; V2 midió reducciones de 7,50–8,36 % en dos casos cortos. La entrega Windows midió 13,491 s para tres ciclos del caso documentado | Seis puntos históricos costaron 71,36 min; 45,28 min después de optimizaciones es una **proyección**, no una curva nueva ni el tiempo de todas las mallas/modelos actuales. Falta una reducción importante del tiempo de una tarea completa |
| Mediciones | Existen `measurement_data.py` y `external_data.py` con contratos de importación, unidades, incertidumbre y comparación | No se encontró en el Desktop inspeccionado un recorrido específico para importar datos de banco y superponerlos con la simulación. «Abrir datos» importa reportes del simulador; no demuestra esa capacidad para archivos de un dinamómetro |
| Precisión predictiva | Conservación, controles numéricos y evidencia de sensibilidad en dominios determinados | Falta una validación cuantitativa del mismo motor y condiciones. Faltan datos esenciales del X30. Las diferencias A/B de −0,62 % y +3,28 % no tienen una incertidumbre predictiva que justifique hoy elegir un escape como mejor |
| Exploración automática | Hay variantes, comparación y coordinación RPM reutilizables | Un barrido RPM no es un optimizador de dimensiones. No está demostrada una capacidad de optimización de producto; queda después de hacer rápida y confiable la comparación manual |

Limitaciones concretas del editor actual: el AFR de operación es metadata
deshabilitada, no una consigna física de mezcla; la carga selecciona pérdidas
cuando hay mapa, no una mariposa; el combustible aparece como snapshot de sólo
lectura. Son restricciones explícitas, no errores demostrados del solver. Deben
resolverse o delimitarse si el producto pretende ofrecer esas decisiones de uso.

### Referencia comercial funcional

EngMod2T documenta preparación de modelos, simulación, procesamiento y lotes;
Post2T permite importar curvas de banco y trazas medidas. MOTA documenta ingreso
de geometría, comparación de modificaciones y optimizadores de escape y puertos.
Son referencias útiles para el recorrido del usuario, no pruebas independientes
de velocidad o precisión frente a Dino.

- [EngMod2T: alcance y programas](https://vannik.co.za/EngMod2T.htm).
- [Post2T: resultados e importación de mediciones](https://vannik.co.za/EngMod2T%20-%20Outputs.htm).
- [MOTA: alcance, diseño y optimización](https://www.iwt.com.au/mota-software/overview/).

No se realizó un benchmark entre aplicaciones ni una evaluación de sus licencias.
No hay base para afirmar un factor de desventaja de Dino frente a esos productos.

## 3. Entregas priorizadas

Los umbrales siguientes son **objetivos de ingeniería propuestos**, no resultados
conseguidos. Las comprobaciones se ejecutarán dentro de cada entrega autorizada,
no durante esta evaluación.

### P1 — Tiempo práctico para comparar diseños

**Entregable:** una distribución con reducción sustancial del tiempo total de
calcular A/B, conservando física, criterios de periodicidad y recuperación.

- Reutilizar perfiles, ejecutores y optimizaciones existentes. Medir la tarea
  real en el modelo y hardware declarados; incluir arranque, cálculo y guardado.
- Objetivo de aceptación: **al menos 2×** de aceleración de pared en una tarea
  congelada de seis puntos A/B, con estados finales equivalentes según criterios
  previos, balances y checkpoints correctos. Una reducción hacia 20–25 min sólo
  sería una traducción aproximada de la proyección de 45 min; no es un compromiso
  medido ni una garantía para cualquier motor.
- Antes de financiar esa comprobación completa, una viabilidad acotada debe
  demostrar beneficio integral en dos casos breves representativos. Separar
  coste inicial y régimen sostenido. No aceptar sólo un microbenchmark.
- Elegir entre aprovechar ejecución independiente en paralelo o un núcleo
  compilado coherente mediante evidencia de beneficio/coste. No comprometer ahora
  una reconstrucción. El coordinador multiproceso existente es reutilizable,
  pero su integración con esta ruta Desktop y su speedup no están demostrados.
- V3 sigue congelada; V4 no se reabre como integración del adaptador HLLC Numba:
  aquel prototipo obtuvo sólo 10–11 % sin JIT y empeoró el tiempo corto con JIT.

**Cierre:** aceptar la mejora medida o rechazar la alternativa ensayada. Si la
viabilidad no justifica el objetivo, informar el límite y su coste; no encadenar
optimizaciones marginales ni bajar precisión para cumplir el tiempo.

### P1 — Representar un motor propio sin editar archivos internos

**Entregable:** completar el recorrido existente para el monocilíndrico elegido,
incluyendo los datos que hoy permanecen en la plantilla y que requiere ese caso.
Priorizar admisión/transferencias, parámetros de láminas cuando corresponda y
condiciones de operación; aprovechar editores, esquemas y validadores existentes.

**Aceptación:** todos los parámetros indispensables del caso se ingresan o
importan desde Desktop con unidades y origen; se guardan y recuperan sin pérdida;
cada control ofrecido modifica la configuración física efectiva; los supuestos
restantes se declaran. Una modificación de escape y otra de distribución generan
variantes comparables y exportables. El usuario no necesita scripts ni JSON manual.

No implica admitir cualquier topología ni crear un carburador nuevo. Un dato que
el modelo no puede representar debe declararse fuera de alcance, no ocultarse
tras un control sin efecto. La prueba funcional se concentra en los campos nuevos
y su conexión, reutilizando la aceptación existente.

### P1 en paralelo — Un motor real con datos suficientes

**Entregable:** un paquete trazable de geometría, admisión/escape, volúmenes,
distribución, combustible, condiciones y mediciones del **mismo motor**. Incluir
incertidumbres y una condición o modificación reservada para comprobación.

**Aceptación de datos:** ningún parámetro indispensable desconocido se completa
con otro motor o un valor elegido para ajustar potencia. Inventario completo con
fuentes, convenciones y faltantes; distinguir los parámetros medidos, derivados
y estimados. Una curva digitalizada aislada no cierra esta entrega.

Reutilizar el inventario y protocolo existentes. El X30 sigue incompleto; Cahoon
continúa como dependencia externa, sin descargas repetitivas. Si las referencias
existentes no permiten cerrar el paquete, priorizar acceso a un motor y ensayos
documentados mediante colaboración, sujeto a disponibilidad y costes externos.
Esta dependencia no bloquea P1 de uso y velocidad. No se envían solicitudes a
terceros automáticamente.

### P2 — Contrastar resultados y decidir si una modificación es distinguible

**Entregable:** conectar los contratos de mediciones existentes con Desktop:
importar CSV de banco, reconocer unidades/condiciones, superponer potencia/torque
y trazas disponibles, mostrar residuos y exportar la comparación reproducible.
El recorrido de importación puede desarrollarse antes de disponer del conjunto
completo, con datos etiquetados de prueba; eso no constituye validación.

**Aceptación funcional:** un archivo medido conserva procedencia, unidades y
condiciones; se compara con la corrida seleccionada a RPM/fases compatibles y
se recupera al reabrir el proyecto. Los datos ausentes no se interpolan como
mediciones ni se sustituyen por resultados calculados.

**Aceptación científica:** con el paquete P1 completo, comparación preregistrada
en un intervalo declarado, inicialmente al menos tres RPM y una condición o
variante no utilizada para ajustar parámetros. Reutilizar el criterio propuesto
existente de potencia: `|error| + U95_validación ≤ 5 % de P_medida`, con
`U95_validación ≤ 2 % de P_medida`, donde aplique y con incertidumbre sustentada.
Es un objetivo propuesto del proyecto, no un estándar ni precisión actual. Las
trazas y otras magnitudes tendrán criterios acordes a sus mediciones antes de
ejecutar. Un fallo produce un límite de uso o un defecto localizado, no calibración
contra los datos reservados.

Para recomendar A sobre B se necesita además que la diferencia relevante supere
su incertidumbre sustentada y que el cambio medido sea compatible con el predicho.
Validar potencia absoluta al 5 % no demuestra poder ordenar cambios del 0,6 %.
Si no se puede resolver una diferencia, el producto debe comunicarla como
**no distinguible con la evidencia disponible**.

La verificación numérica adicional se limita a la magnitud que decide esa
comparación, en la identidad de modelo elegida. El 3,04→1,04 % observado en caudal
transitorio no es una cota del error de potencia periódica. No se inicia por ese
dato una campaña general de mallas o una promoción automática de candidatos.

### P3 — Evaluar familias de diseños con un presupuesto controlado

**Entregable posterior:** exploración de un conjunto pequeño de dimensiones de
escape o distribución, reutilizando variantes, coordinador y comparación.

**Dependencias:** tiempo práctico demostrado en P1 y capacidad de interpretar
las diferencias en P2. El optimizador no es requisito de la primera entrega útil.

**Aceptación:** objetivo definido sobre la banda RPM elegida, restricciones
geométricas, límite de tiempo/disco, cancelación y reanudación, reutilización de
resultados idénticos y clasificación explícita de candidatos no convergidos.
La mejor variante calculada no se presenta como óptimo físico validado.

## 4. Regla de inversión para toda investigación nueva

| Pregunta permitida | Decisión que habilita | Resultado que la termina |
|---|---|---|
| ¿Esta implementación reduce el tiempo real de comparar? | Incorporar o descartar una alternativa de ejecución | Speedup integral, equivalencia y coste de memoria/arranque en dos casos; si es marginal, se descarta |
| ¿Podemos representar este motor con los datos disponibles? | Elegir el primer alcance y conjunto de validación | Lista cerrada de parámetros, fuentes y faltantes indispensables; si faltan, dependencia externa identificada |
| ¿Podemos confiar en el signo/tamaño de esta diferencia A/B? | Recomendar un diseño o declarar la diferencia no resuelta | Contraste medido y presupuesto de incertidumbre de la diferencia, dentro del alcance declarado |
| ¿Este fallo afecta una predicción o una operación del usuario? | Corregir un defecto localizado | Reproductor, causa, prueba de corrección y ausencia de regresión del alcance afectado |

Cada trabajo define antes de empezar configuración, métricas y límite de tiempo,
disco y memoria. Viabilidad diagnóstica: máximo 10 min; comprobación integrada:
máximo 30 min por configuración, salvo decisión posterior explícita de alcance.
Esos límites no autorizan ahora ninguna ejecución ni sustituyen el presupuesto
global de una entrega. Si no alcanza para resolver la pregunta, se informa la
incertidumbre y las opciones; no se amplía automáticamente.

No continuar por inercia con 90°–150°, mallas más finas, campañas periódicas,
nuevos modelos de barrido/combustión ni auditorías generales. Un defecto concreto
que afecte la entrega elegida sí genera una corrección y verificación focalizadas.
Tampoco se debe esperar a validar experimentalmente todo el solver para mejorar
la edición, la importación de banco o el tiempo de ejecución.

## 5. Decisión recomendada

Mantener rc7 como referencia funcional y ofrecer el alcance actual como TRIAL
exploratorio. Avanzar primero en **tiempo hasta comparación y representación del
motor propio**; obtener en paralelo un conjunto experimental completo. Después,
cerrar una comparación de diseño respaldada por mediciones antes de automatizar
la búsqueda de mejores diseños. No declarar paridad predictiva ni comercial
general antes de esa evidencia.

La entrega siguiente debe ser una capacidad utilizable y medible de esas líneas,
no el cierre administrativo de todas las investigaciones históricas.

## Evidencia local utilizada

- [Aceptación CRV1 rc7](../../results/dino-commercial-readiness-v1/acceptance/report.md):
  fuente `fc27542155840cdadbcc2b591ae5cd8e99031899`, ZIP SHA-256
  `2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`.
  Se conserva; no se confunde con el paquete anterior también llamado rc7.
- [Entrega Windows integrada anterior](../../results/windows-integrated-delivery-v1/report.md):
  fuente `da501c72`, pruebas de EXE, cancelación/reanudación y tiempos.
- [Curvas periódicas históricas](../../results/periodic-rpm-curves-v1/report.md).
- [Performance V2](../../results/integrated-performance-v2/report.md) y
  [Performance V4 descartado](../../results/integrated-performance-v4/report.md).
- [Motor integrado desde Desktop](../../results/functional-engine-desktop-v1/report.md).
- [Inventario experimental](../../results/predictive-reliability-v1/measured-data-inventory.json),
  [referencia experimental](../../results/experimental-reference-v1/report.md) y
  [faltantes X30](../../results/x30-public-reconstruction-v1/decision.md).
- Código inspeccionado: `motorsim/desktop/{engine_page,exhaust_page,execution_page,
  results_page,services,new_engine_dialog}.py`, `motorsim/measurement_data.py` y
  `motorsim/external_data.py`. Inspección estática, no aceptación nueva del EXE.

Revisión de este documento: **SELF_REVIEW**. Los archivos locales ajenos y la
cola operativa preexistente permanecen sin editar por esta evaluación.
