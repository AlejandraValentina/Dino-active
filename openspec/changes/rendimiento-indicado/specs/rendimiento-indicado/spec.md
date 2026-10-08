## ADDED Requirements
### Requirement: Diagnóstico de frontera baja sin corrección
La etapa diagnóstica SHALL ejecutar independientemente1500/1750/2000/2250/2500/
2750/3000 y reproducir1000 con perfil, física, mínimo y positividad intactos.
SHALL registrar estados, ciclos, tiempos, pasos/rechazos, primeros estados
inválidos y últimos ciclos completos diferenciando diagnósticos de resultados.
SHALL observar error por componente en1000, etapa RK y conservación/donantes
en2000, sin clipping, tolerancias nuevas ni inferir continuidad entre muestras.
#### Scenario: Observación de un estado no físico
- **WHEN** una etapa del solver rechaza un estado
- **THEN** capturar su contexto sin cambiar el cálculo y detener la reproducción
  offline en la misma prohibición; no afirmar un estado final no evaluado.
#### Scenario: Frontera observada
- **WHEN** finalizan los puntos autorizados
- **THEN** emitir una única conclusión diagnóstica, mantener2500–3500 público,
  comprobar regresión3000 exacta y no ejecutar campaña alta/4T ni empaquetar.
### Requirement: Puerta numérica de ampliación 2T
El sistema SHALL separar explícitamente dominios por ciclo. La ampliación
candidata2T1000–15000 SHALL condicionarse a ocho puntos1000/2000/3000/5000/8000/
10000/12000/15000 con el ejemplo Referencia, mismo perfil y física, convergencia,
balances contractuales y resultados finitos. SHALL conservar4T2500–3500.
#### Scenario: Falla de la campaña candidata
- **WHEN** un punto obligatorio falla o no converge
- **THEN** registrar RPM, causa, ciclos, tiempos, balances y diagnóstico sin
  reparar física; no habilitar el rango completo ni iniciar la fase B condicionada.
#### Scenario: Campaña aprobada
- **WHEN** los ocho puntos cumplen el contrato y la decisión es GO
- **THEN** habilitar2T1000–15000, planes exactos2–57 puntos, sugerencia1000/15000/500,
  presupuesto acotado justificado por tiempos, progreso/cancelación y gráficos
  reales; medir29 puntos y explorar16000/18000/20000 sin ampliar el límite público.
### Requirement: Derivados indicados comunes
El sistema SHALL derivar potencia y par del W_C y RPM guardados: 2T P=W_C*rpm/60,
T=W_C/(2*pi);4T P=W_C*rpm/120,T=W_C/(4*pi). SHALL rechazar ciclo inválido,
RPM no positiva/no finita y trabajo no finito. No integrar curvas ni aplicar pérdidas.
#### Scenario: Referencia analítica
- **WHEN** W_C es2*pi para2T o4*pi para4T, a3000rpm
- **THEN** resulta T=1N·m y P=100*pi W.
### Requirement: Vista Rendimiento
La navegación SHALL incluir Rendimiento debajo de Simulación, usando CAE existente.
SHALL reutilizar automáticamente el último barrido compatible de sesión o conservar
el compatible ya seleccionado. Sin curva SHALL ofrecer Calcular rendimiento para
el proyecto actual y Abrir barrido existente como acción secundaria. Entrar no
SHALL abrir diálogos ni iniciar cálculos. La acción explícita SHALL delegar en el
barrido actual: plan_rpms, captura, validaciones, worker, persistencia y cancelación.
SHALL mostrar fuente/ciclo/estado/RPM, resumen de mayores valores entre puntos
calculados, cantidad convergida y rango; no atribuir máximos físicos del motor.
#### Scenario: Cambio de proyecto
- **WHEN** el proyecto abierto cambia de ciclo o geometría
- **THEN** se retiran curvas incompatibles sin borrar resultados; abrir un histórico
  explícitamente lo identifica como análisis histórico y conserva sus datos guardados.
#### Scenario: Cálculo explícito y finalización
- **WHEN** se pulsa Calcular rendimiento con un proyecto válido
- **THEN** usa el barrido existente, muestra punto/RPM/ciclos/tiempo/convergidos/pendientes
  y Cancelar; al terminar presenta automáticamente el barrido validado en la misma vista.
#### Scenario: Reutilización desde Simulación
- **WHEN** se completa un barrido compatible desde Simulación y se entra a Rendimiento
- **THEN** muestra sus curvas sin pedir seleccionar el archivo.
### Requirement: Gráficos y consulta fieles
SHALL presentar gráfico combinado RPM/potencia indicada[kW]/par indicado equivalente[N·m],
ejes etiquetados azul/ámbar, puntos y segmentos rectos sin suavizar/interpolar/extrapolar.
SHALL incluir W_C y pmax secundarios, tabla y selección con detalle/abrir resultado.
SHALL mostrar advertencias de magnitudes indicadas sin pérdidas ni valores al eje.
#### Scenario: Punto no convergido
- **WHEN** hay puntos fallidos/cancelados/no ejecutados
- **THEN** no muestran valores ficticios, no unen curvas a través del hueco ni permiten abrirlos como convergidos.
### Requirement: Recálculo iterativo y plan independiente
El panel RPM SHALL permanecer visible. SHALL bloquear campos y cálculo solo
durante ejecución; sin curva ofrecer Calcular rendimiento y con curva Recalcular
rendimiento. La compatibilidad de proyecto SHALL ser distinta de la comparación
exacta plan_rpms contra index.rpms. Cambiar solo RPM SHALL conservar resultados y
mostrar plan anterior/nuevo y advertencia textual; no cargar otra serie ni revertir
los campos. Un plan inválido SHALL impedir ejecutar sin destruir la curva.
#### Scenario: Tres ejecuciones en una sesión
- **WHEN** se calcula, se cambia a otro plan válido y se vuelve a calcular
- **THEN** conserva los controles y genera una carpeta nueva por ejecución,
  reemplaza resultados al completar y permite un tercer cálculo sin reiniciar.
#### Scenario: Cancelación o error de recálculo
- **WHEN** se inicia una nueva curva y luego se cancela o falla
- **THEN** mantiene la curva anterior identificada como tal y el plan configurado,
  muestra el motivo y habilita reintento; sin curva previa vuelve al estado vacío.
#### Scenario: Barrido parcial
- **WHEN** un barrido no cancelado termina con puntos no convergidos
- **THEN** conserva la curva previa si existe; sin ella permite consultar sus
  puntos válidos con las reglas de huecos y estado existentes.
### Requirement: Resultados comparación y CSV
Resultados individuales SHALL mostrar ambos derivados. Comparar SHALL añadirlos
solo bajo compatibilidad existente (incluidas mismasRPM). CSV nuevos SHALL
incluir indicated_power_W e indicated_torque_Nm con precisión completa.
#### Scenario: Lectura histórica
- **WHEN** se abren resultados anteriores con trabajo/ciclo/RPM
- **THEN** deriva al presentar/exportar, sin reescribir los originales.
### Requirement: Comprobación y candidata
SHALL mantener suite y física, comprobar UI/EXE con históricos2T/4T y generar rc6
si aprueban, preservando rc5, capturas/evidencia y aceptación manual separada.
#### Scenario: Redimensionado
- **WHEN** el ancho es reducido
- **THEN** apila secundarios sin scroll horizontal global y conserva acceso por teclado.

### Requirement: Ampliación pública 2T autorizada después de P0
La aplicación SHALL aceptar enteros 2500–15000 para 2T y conservar 2500–3500
para 4T. SHALL conservar barridos exactos de 2–5 puntos, presupuestos, física,
formatos y cancelación. Esta autorización posterior sustituye el límite público
anterior sin alterar las conclusiones de las campañas históricas.
#### Scenario: Régimen alto 2T
- **WHEN** se solicita 15000 rpm en Simulación o Rendimiento para 2T
- **THEN** permite construir la solicitud con esas RPM.
#### Scenario: Fuera del dominio
- **WHEN** se solicita 15001 rpm para 2T o 3501 rpm para 4T
- **THEN** bloquea con el intervalo correspondiente.
