## Context
Orden explícita del bloque 4T básico. Se conserva a continuación la definición
aprobada para evitar perder valores, puertas de continuación o presupuestos.
## Decisions
Reutilizar geometría, flujos y RK4 mediante una descripción pequeña de tamaños,
conexiones e índices por modelo. Estados 4T reales de nueve componentes, sin K.
Datos de válvulas y conductos 4T separados del histórico 2T. Guardar entradas,
no curvas. Controles compartidos con lectores estrictos según modelo y versión.
## Risks / Trade-offs
La convergencia, sensibilidad y coste no se presuponen. Un fallo bloquea solo
la integración dependiente; no se modifican umbrales para aprobar.
## Definición autorizada

NUEVA ORDEN DE TRABAJO — BLOQUE COMPLETO 4T BÁSICO

Trabajá en MotorSim, en E:\dino\Dino.

Autorizo implementar conjuntamente las entregas 7 y 8 de la hoja de ruta,
dentro del alcance definido a continuación:

configuración 4T → modelo numérico comprobado → ejecución desde el editor →
resultados persistentes → comparación y barrido acotado.

Esta es una autorización de implementación y ejecución, no una solicitud
exclusivamente documental.

Las etapas internas de este encargo están autorizadas de forma condicional:
cuando una comprobación previa aprueba, continuá con la etapa siguiente
sin solicitar nuevamente permiso.

No te detengas solamente porque terminó la especificación, el editor,
el prototipo o una revisión intermedia.

OBJETIVO DE CIERRE

Desde la misma aplicación debe ser posible configurar un 4T monocilíndrico
admitido, guardarlo, calcularlo, cancelar, consultar y reabrir resultados,
comparar configuraciones y ejecutar un barrido corto.

El 2T existente debe conservarse operativo y reproducible.

No incluye ondas, sobrealimentación, diésel, multicilíndricos acoplados,
distribución variable, química detallada, calibración experimental
ni empaquetado ejecutable.

1. CONTINUIDAD Y AUTONOMÍA

Leé AGENTS.md, README, la hoja de ruta y los contratos pertinentes del código.

Comprobá Git y preservá 6cbed360 y cualquier trabajo posterior.
No restaures versiones antiguas ni descartes cambios ajenos.

Actualizá AGENTS.md para registrar este bloque autorizado.
La prohibición anterior de comenzar la entrega 7 deja de aplicar a este encargo.
Las exclusiones generales y la protección del repositorio permanecen.

Creá o reutilizá un único cambio OpenSpec para este bloque:
“cuatro-tiempos-basico”.

La hoja de ruta conserva sus entregas 7 y 8 separadas, pero ambas pueden
remitir al mismo cambio y a sus tareas identificables.
No generes dos especificaciones que dupliquen las mismas decisiones.

Antes de cada parte, documentá lo imprescindible y continuá implementando.
Usá tasks.md como seguimiento; varios commits locales dentro del encargo
están permitidos.

La entrega 6 conserva:
- Herramientas de comparación, barrido e importación implementadas.
- Contraste con mediciones reales pendiente.
- Validación experimental no realizada.
No inventes su cierre experimental ni conviertas esa ausencia en un bloqueo 4T.

Autorización de correcciones:
podés resolver defectos de implementación, integración y validación,
y hacer refactorizaciones pequeñas necesarias para reutilizar componentes.

No podés cambiar silenciosamente las leyes físicas, tolerancias o presupuestos
para obtener un resultado favorable.

Si aparece un bloqueo real, identificá su causa y continuá las partes
independientes que puedan completarse correctamente.
No sustituyas un fallo físico por un resultado de demostración.

2. CONFIGURACIÓN 4T INICIAL

Admití inicialmente:
- Un cilindro.
- Una válvula de admisión.
- Una válvula de escape.
- Distribución fija.
- Alzada prescrita directamente en la válvula.
- Conductos circulares sin ramificaciones.

La ficha común conserva diámetro, carrera, biela y compresión geométrica.
No dupliques esos datos.

Añadí “Configuración 4T”, con dos grupos compactos:
Admisión y Escape.

Por válvula registrá:
- Diámetro de referencia del asiento D [mm].
- Diámetro interior de garganta d [mm].
- Diámetro del vástago s [mm].
- Alzada máxima H [mm].
- Ángulo de apertura a [grados de cigüeñal].
- Duración de apertura Δ [grados de cigüeñal].

El cierre y el ángulo de máxima alzada serán derivados.
No añadas otra entrada de cierre que pueda contradecir apertura y duración.

Las dimensiones describen una aproximación de área, no una culata CAD.
No modeles ángulo de asiento, enmascaramiento, balancines, elasticidad,
holgura de válvulas, rebote ni colisión pistón-válvula.

Los campos pueden quedar sin informar y guardarse.
Validá entradas informadas:
D > 0; d > 0; 0 <= s < d <= D; H > 0.
Apertura: 0 <= a < 720.
Duración: 0 < Δ < 720.
Todos los números deben ser finitos.

Un conjunto incompatible puede conservarse para corregirlo, según las reglas
de edición existentes, pero no debe presentarse como calculable.
Texto numérico inválido no se convierte silenciosamente en null.

No rellenes proyectos existentes con ejemplos ni asumas que tienen
la distribución del caso sintético.

3. CONVENCIÓN ANGULAR, ALZADA Y ÁREA

Fijá para 4T:
- 0°: PMS de intercambio de gases.
- 180°: PMI posterior a admisión.
- 360°: PMS de compresión.
- 540°: PMI posterior a expansión.
- 720°: siguiente PMS de intercambio.

Las fases nominales son orientativas; los eventos de válvulas son los
definidos por el proyecto.

La posición mecánica del pistón se repite cada 360°.
La distribución y el aporte energético 4T se repiten cada 720°.

Primera ley de alzada admitida: seno cuadrado, explícitamente idealizada.

Con φ = (θ − a) módulo 720:

Si 0 < φ < Δ:
    L(θ) = H * sin(pi * φ / Δ)**2
Fuera de ese intervalo:
    L(θ) = 0

Tratá los extremos analíticamente: no dejes aperturas residuales causadas
por redondeo trigonométrico.

Máxima alzada en a + Δ/2, interpretada sobre el ciclo.
Cierre en a + Δ, conservando una representación inequívoca cuando supera 720°.

Área geométrica idealizada:
A_cortina = pi * D * L
A_garganta = pi * (d**2 − s**2) / 4
A_geom = min(A_cortina, A_garganta)

Áreas en mm² antes de convertir a SI.

Identificá esta fórmula como aproximación de cortina cilíndrica limitada
por sección anular. No es área efectiva medida ni geometría exacta del asiento.

Mostrá:
- Apertura, cierre y duración.
- Alzada y área frente al ángulo.
- Intervalos y duración del cruce, obtenidos por intersección periódica
  de las aperturas de ambas válvulas.

No calcules eventos o cruce redondeando a muestras de una gráfica.
No cuentes dos veces el paso por 0°/720°.

Pruebas geométricas independientes:
- Apertura 0°, duración 220° y H=5 mm:
  L(0)=0, L(110)=5, L(220)=0.
- D=24, d=20 y s=5 mm:
  A_garganta = 93.75*pi mm².
  Con L=1 mm, A_geom = 24*pi mm².
  Con L=5 mm, A_geom = 93.75*pi mm².
- Admisión a=700°, Δ=240° y escape a=500°, Δ=240°:
  cruce total de 40°, repartido alrededor de 720°/0°.

El perfil generado se identifica como idealizado, no medido.
Importación de perfiles de leva y leyes alternativas quedan fuera del bloque.

4. CONDUCTOS Y PERSISTENCIA DEL PROYECTO

Reutilizá el editor por tramos para admisión y escape 4T, con las mismas
definiciones geométricas de dimensiones interiores.

Mantené independientes las configuraciones específicas 2T y 4T.
Cambiar el selector de ciclo no debe borrar ni convertir silenciosamente
lumbreras, válvulas o recorridos.

Los conductos históricos asociados al 2T conservan esa interpretación.
No se convierten automáticamente en conductos 4T por abrir un proyecto antiguo.
Reutilizar widgets y cálculos no implica compartir accidentalmente sus datos.

Añadí la siguiente versión del JSON de proyectos; será v6 si v5 sigue vigente.
Documentá una migración directa y conservá lectura de todas las versiones
actualmente admitidas.

Los proyectos antiguos:
- Conservan sus datos.
- No adquieren válvulas inventadas.
- No se reescriben al abrir.
- Mantienen sus configuraciones 2T aunque se consulte la sección 4T.

Guardá entradas y referencias, no curvas derivadas.

Preservá Nuevo/Abrir/Guardar/Guardar como, confirmaciones, errores seguros,
borradores inválidos y protección de cambios.

No construyas un sistema general de migraciones ni cambies de tecnología.

5. MODELO 4T APROBADO PARA ESTA PRIMERA VERSIÓN

Implementá un modelo 0D de tres volúmenes:

reservorio exterior I ↔ admisión I ↔ cilindro C ↔ escape E ↔ reservorio exterior E

Cuatro conexiones:
- Exterior-I.
- I-C, controlada por la válvula de admisión.
- C-E, controlada por la válvula de escape.
- E-exterior.

El cárter no interviene en el intercambio de carga de este modelo 4T.
No reutilices el bombeo del cárter 2T ni agregues un volumen ficticio
para satisfacer índices del código anterior.

Por volumen integrá masa m, energía sensible U y marcador fresco F.
Usá los balances abiertos y transporte de entalpía del núcleo existente,
con selección coherente de donante en retornos.

Cierre aprobado:
- R = 287 J/(kg K).
- gamma = 1.35.
- cv = R/(gamma−1).
- cp = gamma*cv.
- p = (gamma−1)*U/V.
- T = U/(m*cv).
- Y = F/m.

Mismas propiedades para fresca/residual, mezcla homogénea, paredes adiabáticas,
sin fugas, pérdidas mecánicas ni química predictiva.

El cilindro usa la geometría biela-manivela existente.
Admisión y escape se reducen a sus respectivos volúmenes agregados y
secciones mínimas, como en el modelo 0D ya documentado.
No hay inercia, ondas ni sintonía.

Flujos:
- Ley compresible reversible existente.
- Cd=0.70 en ambas válvulas.
- Cd=0.80 en las dos conexiones exteriores.
- Regularización exterior de 100 Pa.
- Válvulas interiores sin esa regularización añadida.

Aporte energético:
- Comienza en 350° y termina en 390°.
- Se repite una vez cada 720°.
- Q_ciclo = 800000 J/kg * F_C al inicio del aporte.
- Reutilizá la ley temporal prescrita y la conversión analítica de F_C
  ya comprobadas, adaptadas al período 720°.
- El cilindro debe permanecer cerrado durante todo el aporte.

No apliques calor de nuevo a 710° por conservar una periodicidad 2T.
No calientes residual como si fuese nueva carga fresca.

La distribución del editor puede describir otros eventos, pero la ejecución
rechaza los que abran el cilindro durante el aporte fijo.

Resultado de trabajo:
W_C = integral de p_C dV_C sobre el ciclo completo de 720°.

Incluye el intercambio de gases; no es trabajo al eje.
W_K no aplica al 4T: no lo presentes como cero calculado ni inventes
un diagnóstico de cárter que no existe.

No añadas potencia al eje, par, consumo, emisiones o detonación.

6. CASO SINTÉTICO 4T Y REUTILIZACIÓN DEL CÓDIGO

Definí un único caso S4T-0D-01, completamente identificado como sintético:

Geometría:
- Diámetro 54 mm.
- Carrera 56 mm.
- Biela 100 mm.
- Compresión geométrica 8:1.
- Un cilindro.

Válvula de admisión:
D=24 mm; d=20 mm; s=5 mm; H=5 mm;
apertura 0°; duración 220°.

Válvula de escape:
D=20 mm; d=18 mm; s=5 mm; H=5 mm;
apertura 500°; duración 220°.

Conducto I:
un tubo de 100 mm de longitud, 20 mm de diámetro interior.

Conducto E:
tubo de 100 mm, diámetro 20 mm;
seguido de cono de 100 mm, diámetro inicial 20 y final 40 mm.

Reservorio I: 100000 Pa absolutos, 300 K, Y=1.
Reservorio E: 100000 Pa absolutos, 500 K, Y=0.

Inicio a θ=0°:
I: 100000 Pa, 300 K, Y=1.
C: 100000 Pa, 500 K, Y=0.
E: 100000 Pa, 500 K, Y=0.

Derivá inventarios iniciales de p/T/Y y volúmenes efectivos.
No copies masas o energías del caso 2T.

Primer régimen de comprobación: 3000 rpm.
Un ciclo 4T dura 120/rpm segundos: a 3000 rpm, 0.04 s.

Todos estos valores son supuestos del caso de desarrollo, no mediciones.
No se promete convergencia antes de ejecutarlo.

Reutilizá las funciones comunes que correspondan, pero revisá los supuestos
codificados sobre:
- Cuatro volúmenes y doce componentes.
- Seis conexiones.
- Índices del cilindro y del marcador fresco.
- Período de 360°.
- Captura de F_s.
- Trabajo del cárter.
- Cantidad y fase de muestras.

Una pequeña descripción por modelo de estados, enlaces y período está autorizada.
No construyas una plataforma universal de redes o solvers.
No fuerces un estado 4T de tres volúmenes a aparentar cuatro.

Conservá el modelo 2T y su reproducibilidad.
El núcleo de consola sigue sin depender de Qt.

7. CONTROL NUMÉRICO Y CRITERIOS PREVIOS

Reutilizá RK4 adaptativo por duplicación de paso y sus perfiles A/B/C.
Conservá sus valores efectivos, rechazo, mínimos, cancelación y presupuestos.

Adaptá la norma a los componentes reales m/U/F de I/C/E:
no incluya acumuladores como estados físicos ni omita componentes por índices.

Cada flujo interno se calcula una vez por etapa y se registra con signos opuestos.
Los intentos rechazados no contaminan flujos, calor, trabajo ni convergencia.
No recortes estados para forzar positividad o composición.

Antes del caso completo, comprobá:
- Geometría y periodicidades 360°/720°.
- Eventos, área y cruce de válvulas.
- Flujo reversible y transporte del donante.
- Masa/energía/fresca de recipientes conectados.
- Compresión cerrada adiabática.
- Aporte y conversión con válvulas cerradas.
- Ausencia de un segundo aporte dentro del ciclo.
- Relación tiempo–ángulo.
- Contabilidad de trabajo sobre 720°.

Usá referencias independientes, no la función probada para generar esperados.

Conservá como criterios del primer 4T:
- Balance discreto de masa y fresca <=1e-6 normalizado.
- Balance discreto de energía <=1e-5.
- Balance independiente <=0.001, es decir 0.1 %.
- Normalizaciones del diseño existente, aplicadas a los volúmenes/enlaces 4T.
- Auditoría independiente sobre cada paso aceptado, no solo sobre la gráfica.

Convergencia:
tres ciclos consecutivos, desde el ciclo 5, con balances aprobados,
aporte positivo y:
- Cambios relativos de m y U <=0.2 %.
- Cambios absolutos de Y <=0.002.
- Cambio relativo de trabajo <=0.5 %, con escala mínima 1 J.
- Diferencia máxima de curva de presión <=0.5 % con la escala ya documentada.

Compará siempre la misma fase del ciclo de 720°.

Sensibilidad entre perfiles:
- Trabajo, pmax, curva y masas netas por enlace <=1 %.
- Cada Y final difiere <=0.005.
- Pisos de normalización existentes, sin redefinirlos después de un fallo.
- En A/B/C, tendencia de refinamiento según la regla ya comprobada.

Aprobación de banda:
comparación C/100 Pa frente a C/50 Pa con esos umbrales,
identificada como dependencia del modelo regularizado, no error experimental.

Límites por ejecución:
30 ciclos de 720°, 60 segundos de integración, 512 MiB del proceso numérico
y los restantes límites actuales de RHS, paso y rechazos.

No dupliques el tiempo permitido porque el ciclo tenga dos revoluciones.
Medí el coste; no lo presupongas.

8. SECUENCIA NUMÉRICA Y CONTINUACIÓN AUTOMÁTICA

Primero ejecutá S4T-0D-01 a 3000 rpm, banda 100 Pa, perfil A.

Si A falla un criterio obligatorio o agota el presupuesto:
diagnosticá y corregí defectos demostrados de implementación.
No cambies física o tolerancias para hacerlo pasar.
Si la causa requiere otra decisión física o numérica, detené solo
la integración funcional del solver y entregá la causa concreta.

Si A cumple, continuá automáticamente con B y C desde los mismos
estados iniciales originales, sin arranque caliente.

Si A/B/C cumplen, ejecutá C a 50 Pa.
Si también cumple la comprobación de banda, el núcleo queda habilitado
para su integración gráfica dentro de esta misma orden.
No pidas otra autorización para conectarlo a la aplicación.

Estas cuatro ejecuciones forman la comprobación inicial, no una campaña
de búsqueda de parámetros. Conservá todos sus resultados.

9. INTEGRACIÓN CON LA APLICACIÓN Y EL EDITOR

Reutilizá la gestión asíncrona, cancelación, resultados, curvas y controles actuales.

La pantalla de simulación debe distinguir claramente 2T y 4T.
Una rotulación común “Simulación” con el ciclo visible está permitida;
no hace falta reconstruir el diseño ni duplicar ventanas completas.

Para 4T ofrecé:
- Caso de referencia S4T-0D-01.
- Proyecto actual, bajo condiciones 4T de referencia.

En proyecto:
capturá datos válidos del editor, incluidos cambios sin guardar.
No uses el archivo de disco ni valores del ejemplo para completar ausencias.

Exigí solo los datos que necesita este modelo 4T.
No exijas cárter, lumbreras o falda 2T.
No uses datos ocultos de una configuración anterior del otro ciclo.

Conservá procedencia y aviso de configuración anterior.
Editar o abrir otro proyecto no modifica una ejecución activa ni sus resultados.

Un solo proceso de cálculo activo, incluidos punto, barrido y referencia.
Cancelar y cerrar siguen protegiendo proyecto y proceso.

Mostrá:
- p absoluta frente a ángulo de ciclo 0–720°.
- P-V en orden temporal.
- Trabajo indicado del cilindro por ciclo de 720°.
- pmax, ciclos, tiempo, balances y motivo de parada.
- Fracciones frescas de I/C/E.

No muestres campos 2T inexistentes para rellenar la tabla.
No conviertas un fallo en una curva anterior o en un éxito del caso de referencia.

La ley de alzada, área aproximada, energía prescrita y ausencia de ondas
deben figurar en el detalle del modelo, con una advertencia breve en pantalla.

10. RESULTADOS, COMPARACIÓN, BARRIDO Y DATOS EXTERNOS

Extendé los contratos de resultados para declarar:
ciclo, período angular, modelo, estados/enlaces efectivos, geometría,
distribución, condiciones, perfil y variante.

Conservá la lectura de los resultados 2T anteriores.
No reinterpretarlos como 4T ni quitar validaciones para aceptar nuevas dimensiones.

Con salida cada 0.5°, una vuelta completa de 720° contiene 1441 muestras,
incluidos ambos extremos para representación.
No cuentes el extremo repetido dos veces en integrales.

Los resultados deben reabrirse sin el proyecto original.
Las versiones y hashes identifican datos; no autorizan ejecutar contenido.

Habilitá comparación entre dos resultados 4T compatibles:
diferencias de geometría/distribución, trabajo, pmax, Y y curvas alineadas.
No compares 2T y 4T como si sus trabajos por ciclo fueran equivalentes.
La comparación entre ciclos distintos queda fuera de este bloque.

Reutilizá el barrido:
2500–3500 rpm, entre 2 y 5 puntos, arranques independientes, ejecución
secuencial y parada al primer fallo. Misma copia de geometría para toda la serie.

Las RPM afectan dt, dV/dt, tasa de calor y tiempo de muestras;
el aporte conserva sus ángulos 350–390°.

CSV y gráficos muestran puntos calculados, sin óptimos inventados.

Adaptá datos externos solo lo necesario para distinguir:
- Trabajo indicado completo 2T: ciclo de 360°.
- Trabajo indicado completo 4T: ciclo de 720°.
- Presión máxima absoluta con ciclo/motor declarado cuando corresponda.

No interpretes automáticamente importaciones históricas 2T como 4T.
Si falta la definición necesaria, impedí el contraste cuantitativo y explicalo.
Conservá procedencia, RPM exactas y ausencia de interpolación.

La falta de mediciones reales sigue siendo un pendiente experimental,
no un permiso para fabricar una validación.

11. COMPROBACIÓN INTEGRADA ACOTADA

Después de aprobar el núcleo, ejecutá estos recorridos reales:

A. Barrido desde la interfaz de un proyecto con geometría exacta S4T-0D-01:
2500, 3000 y 3500 rpm, perfil B/100 Pa.

El punto de 3000 debe reproducir la referencia de consola correspondiente.
No es necesario que coincida su tiempo de pared.

B. Si los tres puntos convergen:
contrastes C/100 Pa de los extremos 2500 y 3500 rpm.
Compará B/C con los umbrales fijados, sin afirmar tendencia de tres perfiles.

C. Proyecto de referencia modificado solo de compresión 8 a 8.2:
ejecutá B/100 Pa a 3000 rpm desde el editor y un contraste C equivalente.
Comprobá propagación real del dato, convergencia, sensibilidad y procedencia.
No exijas de antemano que el trabajo aumente.

D. Una regresión real del caso 2T de referencia, perfil B/100 Pa a 3000 rpm,
contrastada con la evidencia preservada y sus criterios existentes.

Junto con las cuatro ejecuciones iniciales son hasta doce ejecuciones completas
previstas, con un máximo conjunto de 720 segundos de integración.

No lances las dependientes si falla su condición previa.
Las pruebas unitarias de secuencia, cancelación y errores usan dobles;
no ocultes otras series completas dentro de la suite.

Una repetición por corrección demostrada debe quedar identificada y respetar
el presupuesto conjunto. No reinicies presupuestos para prolongar el encargo.

Reutilizá los resultados anteriores para probar comparación, importación,
exportación y capturas. Esas operaciones no requieren volver a simular.

Comprobá también guardar/reabrir 4T, alternar 2T/4T sin pérdidas,
compatibilidad de archivos, cambios sin guardar, resultados obsoletos,
cancelación, cierre, fallo y un único proceso.

12. REVISIÓN, ESTADO Y ENTREGA

Realizá una revisión puntual de las partes modificadas y sus contratos.
Corregí los hallazgos reproducibles y repetí lo afectado.
No encadenes auditorías generales ni conviertas mejoras opcionales en bloqueos.

Ejecutá la suite final pertinente del estado entregado.
Diferenciá pruebas rápidas de las ejecuciones numéricas completas.

Comprobá Windows y escalado al 150 %, con capturas reales del editor 4T,
resultado, comparación y barrido. Reabrí resultados para recapturar;
no recalcules solo para obtener otra imagen.

Actualizá README, tasks.md y la hoja de ruta:
- Entrega 7 según configuración, persistencia y geometría comprobadas.
- Entrega 8 según núcleo e integración realmente acreditados.
- Pendientes manuales y experimentales separados.
- Entrega 6 conserva su pendiente de mediciones reales.

No atribuyas aceptación manual a una automatización.
No declares capacidad predictiva general por aprobar casos sintéticos.

Registrá cambios propios en commits lógicos:
configuración/persistencia, núcleo comprobado e integración,
o una separación equivalente que facilite revisar y revertir.

No publiques ni modifiques credenciales, configuración global o remotos.
La publicación la realizará la usuaria.

La respuesta final debe incluir:
- Funciones completadas de las entregas 7 y 8.
- Modelo y límites efectivamente implementados.
- Tabla de ejecuciones, convergencia, balances, sensibilidad y coste.
- Pruebas y revisión.
- Compatibilidad con 2T y archivos históricos.
- Pendientes concretos.
- Comando para abrir MotorSim.
- Capturas y commits.

No cierres la tarea después de preparar documentos o un prototipo si
las condiciones permiten continuar con el resto del bloque autorizado.

Si se completa el recorrido definido, detenete ahí.
No archives cambios, no empaquetes todavía y no comiences otra ampliación física.
## Revisión de aceptación R2 — autorización posterior a b862900
R1 permanece histórica: convergencia, balances y tolerancias aprobados; tendencia
estricta fallida en pmax/Y_I. R2 no cambia ecuaciones, perfiles ni tolerancias principales.
Reutiliza A100/B100/C100 intactos y exige estados válidos, convergencia completa,
balances, aporte positivo y presupuestos. Conserva métricas A/B y B/C originales.
Acepta tendencia original O estabilidad práctica en TODAS las magnitudes:
dispersión max−min A/B/C normalizada ≤1e-4 para trabajo, pmax, curva y cada enlace;
dispersión absoluta de cada Y ≤5e-5. Escala trabajo=max(abs(W_A/B/C),1 J),
enlace=max(abs(m_A/B/C),1e-7 kg), presión=max(pmax_A/B/C,100000 Pa).
Curva: máximo de dispersiones por nodo de la misma fase, sin interpolar.
1e-4 equivale a 0,01 %, cien veces menor que la tolerancia principal; es una
aceptación práctica explícita, no error exacto, redondeo ni validación experimental.
Separar pmax monitorizado de máximo muestreado y comparar variaciones entre ciclos
finales para no atribuir exclusivamente al paso el residuo periódico.
R2 se persiste separada, con identidades/hashes comprobados. Si aprueba, C50 desde
arranque original, contraste C100/C50 con tolerancias originales sin tendencia.
Si banda aprueba, continuar integración y ocho ejecuciones integradas originales.
Presupuesto acumulado conserva 51,125 s ya consumidos; máximo conjunto 720 s.
Sin nuevas bandas/perfiles, sin repetir A/B/C, sin publicar/archivar/empaquetar.
