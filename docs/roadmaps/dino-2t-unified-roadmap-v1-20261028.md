# Dino 2T — hoja de ruta única: física predictiva y producto V1

Fecha: 2026-10-28. Prioridades adoptadas por instrucción del dueño. Esta hoja
reemplaza el orden de ejecución del plan de núcleo por etapas y del roadmap de
producto V2; conserva ambos como antecedentes y reutiliza sus capacidades.
La autoridad operativa sigue siendo `program-status.json`, que referencia este
documento. Publicar el plan no autoriza ejecutar todas sus etapas ni retomar
automáticamente tareas o campañas históricas.

## Objetivo y reglas de avance

Predecir curvas de potencia y torque y el cambio causado por una modificación
de diseño, dentro de un dominio declarado y con precisión e incertidumbre
respaldadas por mediciones independientes. Periodicidad y conservación son
necesarias, pero no acreditan capacidad predictiva.

- rc7 permanece como referencia funcional TRIAL congelada. El código experimental
  tiene identidades propias; sus resultados no sustituyen evidencia histórica.
- Reutilizar proyectos, editores, solver integrado, coordinadores, resultados,
  checkpoints, importación de mediciones y candidatos verificados existentes.
- Cada etapa entrega un resultado, presupuesto y decisión registrados:
  **ADOPTAR PARA EL ALCANCE DECLARADO / MANTENER EXPERIMENTAL / DESCARTAR /
  BLOQUEADO POR DATOS**. La última no equivale a un defecto numérico.
- Una etapa dependiente usa una formulación congelada. Puede verificarla como
  hipótesis experimental sin afirmar que fue identificada en un motor real.
  Ningún cambio simultáneo de varios cierres impide atribuir sus efectos.
- Ante un defecto fundamental se detiene la rama dependiente, se conserva el
  reproductor y se decide la estrategia antes de continuar.
- Los presupuestos siguientes son límites iniciales propuestos para activar
  entregas futuras, no autorización de cálculo en esta sesión. El preflight suma
  estimación y reserva de 2 GiB por volumen. Los plazos de búsqueda documental
  no incluyen esperas de terceros ni adquisición de un banco.

## Etapas, en el orden adoptado

### 1. Ley de flujo de lumbreras

**Entregable:** ley específica cámara–restricción–conducto, con caudal, momento,
energía, especies, flujo inverso y régimen sónico consistentes con su contrato.

**Estado actual:** diagnóstico cerrado en `2f16248`, decisión **CORREGIR** el uso
del Riemann escalado como ley general de restricción. V2 ya estaba implementada
y pasó 100 referencias analíticas y los controles dinámicos; se conserva como
**MANTENER EXPERIMENTAL**. No se encontró doble Cd ni defecto de HLLC interior.
V2 supone una tobera ideal equivalente, distinta del cierre de expansión separada
V1; no identifica las pérdidas de una lumbrera real.

**Aceptación de formulación:** referencias independientes, ambas direcciones,
conservación, características, admisibilidad y recuperación. Cumplida dentro
del dominio ensayado, según el recibo específico. No equivale a adopción física
universal ni cambia el default legacy.

**Presupuesto/parada:** el diagnóstico acotado autorizado ya terminó. **Cero
ciclos adicionales por esta hoja de ruta.** Sólo se reabre una cuestión puntual
si aparece un defecto reproducible o un contraste de caudal/presión medido que
discrimine los cierres. No se repiten sus matrices ni campañas.

### 2. Ondas de presión y diferencias de diseño distinguibles

**Entregable 2A, próximo:** comparación A/B de la señal de presión del escape,
con tiempo de retorno, fase, amplitud e impulso, y sensibilidad numérica de la
**diferencia A/B**. El resultado debe decir qué cambio de señal se distingue con
los controles ensayados y cuál no puede resolverse.

La decisión de diseño es si la modificación de escape cambia de forma resoluble
el retorno de presión durante el intercambio de gases. Se parte de una condición
sintética congelada y dos geometrías explícitas reutilizables; no se presenta
como X30. El protocolo fija fases, sondas e inicialización físicamente compatible
con cada geometría, sin reutilizar indebidamente inventarios de otro volumen.

Reutilizar primero la evidencia existente de propagación/reflexión, transporte
y sensibilidades. No reabrir el intervalo 90°–150° ni prolongar checkpoints
históricos. Congelar el candidato de acoplamiento y los demás cierres; conservar
legacy como control histórico. No añadir un esquema espacial por anticipado.

**Aceptación 2A:** fases y posiciones de medición compatibles, propagación y
signo de reflexión físicamente correctos, comparación A/B reproducible y error
temporal separado del espacial. La distinción requiere que la diferencia de
interés supere la incertidumbre numérica estimada mediante un método justificado
y declarado antes de ejecutar; si sólo hay sensibilidades entre resoluciones,
se informa ese alcance, sin presentarlas como cotas rigurosas. No se fuerza
Richardson/GCI ni convergencia puntual en discontinuidades.

**Presupuesto 2A:** preparación de referencias y protocolo sin simulación; si
se activa el cálculo, máximo seis ensayos transitorios cortos —dos diseños en
dos resoluciones y hasta dos controles temporales necesarios—, <=120 s cada
uno y **<=600 s acumulados**, un proceso, 512 MiB de RSS y <=1 GiB de artefactos.
La elección de resoluciones y horizonte se fija tras estimar costes y revisar
qué controles ya existen. No constituye una campaña periódica de mallas.

**Parada/decisión 2A:** detenerse si no se puede estimar la incertidumbre, si
ésta no disminuye o si domina la diferencia útil. Entregar **distinguible en el
alcance / no resuelto / defecto localizado**. Si falta evidencia, el informe
identifica una causa o límite y termina; no encadena refinamientos automáticamente.

**Entregable 2B, posterior:** una comparación de trabajo/IMEP y potencia
**periódicos** A/B a un único RPM, con incertidumbre numérica de su diferencia.
Depende de 2A y requiere un protocolo y activación propios. Presupuesto inicial:
como máximo cuatro configuraciones nuevas, <=30 min por configuración y <=60
min acumulados, checkpoints recuperables. No continuar estados ni campañas
históricas por defecto. Si no alcanzan periodicidad o precisión dentro del
presupuesto, no se declara el signo de la mejora como verificado.

La señal de presión transitoria de 2A no sustituye 2B. Las diferencias históricas
de potencia −0.62 %/+3.28 % tampoco son sus valores esperados obligatorios.

### 3. Barrido físicamente identificable

**Entregable:** cierre conservativo de retención/expulsión de especies cuyos
parámetros puedan relacionarse con mediciones de barrido o composición,
documentando el dominio de validez y la identificabilidad.

Reutilizar el transporte y el cierre actuales como controles. No sustituir
automáticamente una mezcla parcial por un modelo de mayor complejidad. Una
curva de potencia sola no identifica eficiencia de barrido, retención y mezcla.

**Aceptación:** reproduce las magnitudes medidas disponibles con incertidumbre
declarada y mantiene masa/especies/energía. Los parámetros no identificables se
declaran; los datos reservados no se usan para ajustar. Sin mediciones adecuadas,
puede cerrarse la verificación numérica, no la identificación física.

**Presupuesto:** <=600 s de controles aislados y hasta dos diagnósticos integrados
de <=240 s cada uno, <=0.25 GiB de resultados nuevos. Adquisición de mediciones
fuera de ese presupuesto, con alcance propio.

**Parada/decisión:** adoptar sólo para el dominio identificado; mantener
experimental o bloquear identificación si distintas parametrizaciones explican
los mismos datos. No compensar barrido incorrecto ajustando combustión o pérdidas.

### 4. Combustión, termodinámica y pérdidas guiadas por evidencia

**Entregable:** mejorar **un componente por iteración**, elegido por sensibilidad
de una predicción relevante y por la medición capaz de discriminarlo. Puede
incluir propiedades termodinámicas y térmica si la evidencia lo justifica.

**Aceptación:** reduce una discrepancia definida frente a datos independientes
y conserva coherencia energética; reproduce cambios de condiciones dentro del
alcance, no sólo un punto ajustado. Mantener el componente simple si cumple.
No modificar parámetros para alcanzar una potencia deseada.

**Presupuesto por componente:** <=600 s de referencia/sensibilidad justificada
y dos controles integrados <=240 s cada uno; <=0.25 GiB. No se activan de una
vez combustión, propiedades, térmica y fricción.

**Parada/decisión:** si el efecto es menor que la incertidumbre o no es
identificable con los datos, conservar la formulación y documentar el límite.
Sólo una mejora demostrada se adopta con nueva identidad de modelo.

### 5. Validación independiente de curvas y cambios de escape

**Entregable:** paquete de motor/ensayo completo, comparación cuantitativa de
potencia y torque y predicción de una modificación de escape reservada.

**Aceptación:** preregistro de dominio, errores y presupuesto de incertidumbre
antes de calcular. Reutilizar el objetivo de ingeniería existente para potencia
cuando corresponda: `|error|+U95_validación <=5 % de P_medida` y
`U95_validación <=2 % de P_medida`. No es precisión actual ni estándar universal;
torque y trazas se evalúan con sus unidades e incertidumbres, sin contar potencia
y torque derivados entre sí como evidencia independiente.

La predicción del **cambio de escape** debe cumplir un criterio propio para
DeltaP/DeltaT: signo y magnitud contrastados con la incertidumbre conjunta y
sus correlaciones. Acertar potencia absoluta al 5 % no acredita mejoras del 0.6 %.
Una diferencia experimental no distinguible tampoco demuestra acierto del signo.
No se ajusta el modelo a la variante reservada ni se extrapola el dominio probado.

**Presupuesto inicial:** hasta seis puntos nuevos —tres RPM comunes, baseline y
escape reservado—, <=30 min por punto y <=60 min acumulados, sin barrido completo.
Las condiciones numéricas deben estar justificadas por la etapa 2; si no caben
en el presupuesto, se informa antes de ejecutar. Parar ante fallo de identidad,
conservación o datos indispensables; no ampliar ciclos o recalibrar para aprobar.

**Decisión:** validado para el dominio declarado / parcial / no validado. Revisión
independiente antes de claims externos. Ni periodicidad ni balances por sí solos
cierran esta etapa.

### 6. Rendimiento y madurez comercial sobre física estabilizada

**Entregable:** distribución Windows del modelo aceptado, representación de
motor propio, comparación con banco y A/B, curvas, recuperación y exportación
utilizables; reducción importante del tiempo total de una tarea real.

Reutilizar Desktop y todas las capacidades aceptadas. Física estabilizada
significa identidad, alcance y limitaciones controlados, no reconstrucción ni
ausencia absoluta de incertidumbre. Sólo se prioriza antes una optimización
local si un coste demostrado impide completar una entrega física autorizada;
no desplaza el orden de esta hoja de ruta.

**Aceptación:** EXE autónomo con flujo completo, estados científicos claros,
comparaciones conservadas y resultados equivalentes a la misma versión física
de referencia. Objetivo de rendimiento: >=2x del tiempo total medido, incluyendo
arranque y guardado, en tarea/hardware congelados; no se usa como baseline una
proyección de 45 minutos ni se exige equivalencia entre modelos físicos distintos.

**Presupuesto:** viabilidad de una alternativa <=600 s en dos casos breves;
confirmación integral de una tarea <=60 min por versión comparada; un build de
aceptación planificado con preflight específico, estimación de bytes y paquete
anterior preservado. Una reconstrucción fallida no inicia builds repetitivos sin
diagnóstico. No reabrir V3 ni integrar el adaptador HLLC de V4 ya descartado.

**Parada/decisión:** descartar optimización marginal o incompatible; no reducir
precisión ni ocultar resultados no convergidos. Sin validación, conservar la
clasificación TRIAL exploratoria aunque la funcionalidad de Windows pase.

## Línea paralela desde el inicio: datos experimentales

**X30 es la referencia principal, no exclusiva.** Reutilizar los inventarios,
geometría documentada, curva digitalizada de Ortenzi/Bossaglia y solicitudes
preparadas. Continúa faltando, entre otros datos del ejemplar/ensayo, el volumen
libre del cárter con ángulo y fronteras definidos. No usar el motor sintético
como X30 ni ajustar ese volumen a la potencia publicada.

Próximo paquete documental: matriz de datos de geometría/condiciones/caudal,
presión/composición/potencia, fuente, incertidumbre, derechos de uso y reserva
para validación. Diferenciar datos que identifican un submodelo de los que
validan el motor y la modificación de escape.

Primera revisión de completitud: **máximo dos horas de trabajo documental por
referencia**, empezando por los materiales ya disponibles. Si no cierra datos
indispensables, registrar solicitud concreta y dependencia externa; no repetir
descargas ni esperar indefinidamente. No enviar solicitudes a terceros sin
autorización. Cahoon sigue bloqueada externamente mientras no exista material
íntegro accesible. Otra referencia puede adoptarse si supera la matriz de
completitud del mismo motor, sin combinar geometrías o fabricar mediciones.

La línea de datos puede habilitar controles locales en etapas 1–4 antes de la
validación global de etapa 5. Su falta no bloquea controles numéricos pertinentes,
pero sí las afirmaciones físicas que necesitan esos datos.

## Próximo entregable concreto y estado de activación

**E2A — Comparación A/B numéricamente calificada de ondas de escape.** Primero
entregar el protocolo con configuración e identidad congeladas, observables,
evidencia reutilizable, coste previsto y criterios de distinción. Después, sólo
al activarse su ejecución, producir las dos señales comparables y el dictamen
acotado de 2A. No incluye potencia periódica ni claims experimentales.

En paralelo queda definida la adquisición de datos, comenzando por la matriz
X30 y los faltantes que permitirían discriminar la descarga de lumbreras.
**Esta sesión adopta el orden y define el entregable; no inicia 2A, 2B ni otra
etapa, no ejecuta simulaciones y no cambia código físico.** Las filas READY
históricas de la cola no autorizan por sí mismas retomar campañas supersedidas.

## Evidencia que fija el punto de partida

- [Lumbreras: decisión y resultados](../../results/port-flow-verification-v1/report.md),
  protocolo `bd635de`, cierre `2f16248`.
- [Baseline CRV1 rc7](../../results/dino-commercial-readiness-v1/acceptance/receipt.json):
  fuente `fc27542155840cdadbcc2b591ae5cd8e99031899`, ZIP SHA-256
  `2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`.
- [Datos X30](../../results/x30-public-reconstruction-v1/decision.md),
  [inventario medido](../../results/predictive-reliability-v1/measured-data-inventory.json)
  y [protocolo experimental existente](../../results/experimental-reference-v1/report.md).
- [Roadmap de producto anterior](dino-2t-product-roadmap-v2-20261028.md): capacidades
  reutilizables; su prioridad de rendimiento primero queda reemplazada por este orden.

Documento revisado como **SELF_REVIEW**. No constituye validación experimental,
aceptación del solver candidato como default ni cierre global de confiabilidad.
