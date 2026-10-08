## Decisiones
Continuación diagnóstica tras a5b7ce9: siete puntos de frontera y reproducción1000;
2000 comparte observación y mapa. Herramientas exclusivamente en tools, sin
editar producción. ObservedModel delega a Model.evaluate y registra excepciones;
trace lee locales de advance/RK4 solo al rechazar. No reemplaza operaciones,
estimador ni RHS. Las copias no conservan frames ni se devuelven al solver.
El análisis offline reproduce únicamente intentos ya registrados a idéntico paso,
con RK4 original, deteniéndose ante estado inválido. No integra un paso menor
ni calcula un endpoint pasando por F<0. La siguiente propuesta se calcula
algebraicamente. Comparación exacta1000/2000/3000 acredita no perturbación
científica; tiempos incluyen sobrecosto de observación.

Ampliación candidata posterior a 3c07687: fase A independiente con ocho RPM
1000/2000/3000/5000/8000/10000/12000/15000. `rpm_domain` centraliza contratos por
ciclo; candidato separado del dominio público hasta GO. El instrumento de
consola construye el caso del ejemplo canónico a3000 y reemplaza únicamente RPM
antes de llamar al mismo Model/run_adaptive/Monitor, B/100 Pa. No relaja lector
ni worker, no altera formatos científicos. Evidencia de investigación separada
de resultados importables por GUI. Conserva ciclos, muestras y parada completos.
60s/30ciclos/2M RHS/512MiB por punto sin cambios; ocho ejecuciones, máximo480s
de integración. Una falla no impide medir los demás puntos obligatorios.
Decisión medida: BLOCKED por1000/2000. No ampliar UI, cantidad de puntos ni
presupuesto300s. No fase B, exploración superior ni candidata nueva. Los seis
puntos aislados aprobados no acreditan un intervalo continuo3000–15000.

Corrección iterativa posterior a d15ec98: setup siempre visible, campos deshabilitados
solo con proceso activo. configured_plan/plan_matches_sweep comparan el plan exacto
sin alterar compatible(proyecto). Los eventos de contexto solo invalidan un motor
distinto; las opciones RPM actualizan el aviso sin adoptar resultados. La entrada
a la vista y la finalización consumen nuevas referencias de sesión una sola vez,
para que un índice cancelado no sustituya después la curva conservada. No hay
copia ni mezcla de resultados: self.sweep/rows conservan el objeto anterior hasta
aceptar uno nuevo. Cancelación/error/no convergencia preservan una curva previa;
sin curva previa se admiten puntos válidos parciales no cancelados. Los índices y
diagnósticos del controlador siguen persistidos con la infraestructura anterior.

Corrección UX rc6: las decisiones originales de solo consulta abajo describen la
primera candidata. Ahora la vista detecta compatibilidad mediante configuration_key
y source_path de la procedencia; no usa curvas ajenas como actuales. La apertura
manual conserva el histórico explícitamente identificado hasta cambiar el proyecto.
SimulationView conserva el barrido de sesión; PerformanceView solo referencia el
objeto validado. Las entradas RPM se sincronizan con sus controles existentes;
Calcular rendimiento delega en start_performance → start, sin duplicar ejecución.
Señales pequeñas de contexto/actividad/idle actualizan la vista. Solo se grafican
resultados validados al terminar; progreso toma eventos existentes del worker.
Se conserva el destino de finalización para no sacar al usuario de Rendimiento.
Esta corrección no requiere una nueva candidata antes de mostrar evidencia fuente.

Decisiones de la primera candidata:
Función pura de W_C, RPM y ciclo guardados: 2T P=W_C*rpm/60,T=W_C/(2*pi);
4T P=W_C*rpm/120,T=W_C/(4*pi). Acepta trabajo finito (incluido negativo), RPM
finitas positivas; entradas de aplicación siguen validadas por lectores actuales.
Sin redondear datos ni modificar fuentes. CSV en W/N·m; UI en kW/N·m.
Rendimiento lee load_sweep y puede reutilizar el barrido cargado. No depende del
editor ni crea procesos. Cada punto convergido usa su propio resultado y ciclo;
rechazar mezcla de ciclos. Estados no convergidos conservan huecos y cortan segmentos.
QPainter para gráfico combinado de dos escalas y secundarios, puntos/segmentos
rectos, clic y tabla accesibles. Se reutilizan Header/Panel/Columns y QSS.
Derivados de Comparar se añaden después de aprobar las mismas reglas existentes.
## Comprobación
Analítica independiente 2*pi/4*pi a3000rpm, invalidación, históricos, fallidos,
inversión A/B y CSV. Suite conservada; Windows/EXE con barridos2T/4T históricos.
No ejecutar solver. rc6 desde fuente limpia, preservar rc5 y evidencia. Aceptación
manual pendiente; revisión puntual según AGENTS, sin archivar ni publicar.

## Ampliación pública autorizada después de P0 — 17/09/2026
La aplicación admite **2T 2500–15000 rpm** y conserva **4T 2500–3500 rpm**.
Simulación y Rendimiento usan el mismo validador. Los barridos mantienen 2–5
puntos y 300 s acumulados; ejemplo: Inicio=5000, Final=15000, Incremento=2500.
16000–20000 siguen excluidos. P0 acredita la malla del caso sintético, sin
validación experimental. Solver, tolerancias y formatos sin cambios.
Esta autorización posterior no modifica las conclusiones históricas anteriores.
No se reconstruye EXE: las candidatas previas conservan sus límites.
Ejecutar la fuente actual: `.\.venv\Scripts\python.exe -m motorsim`.
