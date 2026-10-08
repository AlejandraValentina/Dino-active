## Implementación
- [x] Comprobar estado posterior a rc5; preservar eliminación ajena de redme.txt.
- [x] Función común, históricos/estados y exportaciones derivadas.
- [x] Vista Rendimiento CAE y navegación, gráficos/selección/tabla.
- [x] Resultados individuales y Comparar sin cambiar compatibilidad.
## Comprobación
- [x] Analítica, negativos/invalidación, históricos, fallidos, A/B, CSV y suite.
- [x] Windows real con barridos2T/4T, captura y responsive.
- [x] OpenSpec estricto y revisión puntual.
- [x] Commit fuente, rc6 limpia, recorrido EXE sin solver y evidencia.
## Pendientes
Aceptación manual final no atribuida. Sin archivar, publicar ni repetir campañas.

17/09/2026: 10 pruebas nuevas aprobadas. Suite inicial269: dos expectativas
desactualizadas (Comparar4T5→7 magnitudes y estado rc5 INACTIVO) corregidas.
Segunda pasada: aserciones aprobadas, un error Windows al eliminar temporal
case.json (WinError5/267) al limpiar test_result_shared_panel_and_project_independence.
Los12tests de workspaces repetidos en aislamiento aprobaron (4,337s), sin cambios
de aplicación por ese incidente. Recorridos Windows visibles automatizados,
no aceptación humana: `E:\MotorSim distribucion\Rendimiento rc6\source-final-100`,
`source-final-125` y `source-final-150`, con gráficos/teclado/tabla/punto/CSV,
fuentes preservadas y ningún worker. Autorrevisión visual de capturas separada;
resumen compactado tras inspección. Sin scroll horizontal global a900×533
lógicos/150 %. Revisión independiente de solo lectura: sin defectos concretos;
10tests aprobados por el revisor. OpenSpec1.3.1 estricto aprobado.
rc6 y su comprobación EXE estaban pendientes al registrar la fuente; acreditadas abajo.

Suite completa final269 aprobada. Corrección visual posterior de contraste de
fila seleccionada y altura del resumen: 10tests afectados aprobados (10,124s),
recorrido Windows125 % repetido en `source-release-125`, sin solver.

## Evidencia de candidata (17/09/2026)
Fuente `799b7d6f9bf6b0061bd9a1de60af682e8061630a`, checkout limpio separado
para preservar eliminación ajena de redme.txt en main. Suite269/54,860s aprobada.
Receta existente Python3.11.0, Qt6.11.2, PyInstaller6.22.3. rc6 extraída en
`E:\MotorSim distribucion\Candidata Rendimiento 0.1.0-rc6\MotorSim`.
ZIP `dist/MotorSim-0.1.0-rc6-windows-x64-799b7d6f.zip`,43.440.060bytes;
SHA256 `0b5d8eaa46a5c82ff2ae82305ed5846467197c4c53b58ff80ef2198dd93e2db1`.
162archivos/104.938.807bytes idénticos al ZIP después del recorrido.
Hash rc5 permanece `f3159c9dd91ddf64e7b02901a9488e6eea60f4c9346eed768bbf2e4f835c9d18`.

`tests/verify_distribution_windows.py --exe <MotorSim.exe> --work <carpeta nueva>
--scale 1 --stage performance`: comprobación Windows automatizada del EXE,
sin Python en PATH ni depender de cwd; abrir barridos2T/4T, seleccionar gráfico
por teclado, tabla, abrir punto, exportar CSV y contrastar precisión exacta,
reutilizar actual y Comparar4T8.0/8.2 con exportación. Ningún worker ni resultado
nuevo. Fuentes científicas conservan hashes. `results/simulacion-2t` intacto
respecto a rc5, sin cambios físicos/solver ni formatos históricos.

Valores de históricos a3000rpm (sin simular):
- 2T referencia: W_C=16.49050751206088J; P=824.525375603044W;
  T=2.624545784638522N·m; pmax=1331530.846070603Pa.
- 4T compresión8.2: W_C=50.95490295791647J; P=1273.8725739479116W;
  T=4.054862340260122N·m; pmax=2685606.691957945Pa.

Evidencia versionada: `results/rendimiento-rc6-20260917/` (tests, JSON y capturas).
Capturas completas: `E:\MotorSim distribucion\Rendimiento rc6`.
Inspección visual del agente separada de automatización: ejes/leyendas/colores,
selección, tabla, secundarios y resultados inspeccionados. Escalado100/125/150 %
en Windows; monitor1440×900, no atribuir recorrido físico FullHD.
OpenSpec estricto aprobado. Una revisión independiente puntual sin defectos.
Único pendiente de cierre: aceptación manual de la usuaria. No archivar ni publicar.

## Corrección UX rc6 autorizada — proyecto y sesión
- [x] CTA explícita con plan compartido; histórico secundario sin diálogo automático.
- [x] Reutilización compatible, invalidación visual y finalización en Rendimiento.
- [x] Progreso y cancelación delegados en el controlador existente.
- [x] Pruebas de flujo 2T/4T y regresión.
- [x] Capturas Windows sin calcular/durante/terminada y reutilización desde Simulación.
- [x] Revisión puntual y OpenSpec estricto; registro de evidencia sin rc7 ni archivo.

Corrección comprobada el17/09/2026: suite274/62,259s aprobada. Revisión independiente
encontró CTA oculto tras cancelación sin puntos convergidos; se corrigió para ofrecer
reintento, conservando diagnóstico. Prueba específica añadida;16tests afectados
posteriores aprobados/16,568s. Fórmulas, solver, física, formatos intactos.

Windows real automatizado (no aceptación manual):2T iniciado desde Rendimiento,
3puntos convergidos/39,328s integración;4T iniciado desde Simulación,3puntos
convergidos/43,562s. Ambos muestran curvas al terminar sin selección de archivo.
La rama de cancelación del script tenía un error de prefijo (`cancel-start` tratado
como inicio de ciclo); falló después de acreditar ambos barridos, antes de iniciar
otro proceso. Se corrigió el script y se ejecutó solo cancelación: cooperativa,
sin puntos iniciados, índice conservado y CTA disponible. No se repitieron barridos.
Evidencia completa en `E:\MotorSim distribucion\Rendimiento UX rc6`, incluidos
el error original del script y resultados persistidos. Capturas/registro versionados
en `results/rendimiento-ux-rc6-20260917/`. Inspección visual del agente: vacío,
progreso real, curvas2T/4T y estado cancelado. OpenSpec estricto aprobado.

Esta corrección se entrega en fuentes, sin construir rc7 ni sobrescribir rc6.
Pendiente aceptación manual; no archivo ni publicación.

## Frontera baja 2T — continuación diagnóstica posterior a a5b7ce9
- [x] Instrumentar sin modificar producción ni devolver observaciones al solver.
- [x] Ejecutar puntos independientes1500/1750/2000/2250/2500/2750/3000 y1000 adicional.
- [x] Capturar primeras violaciones, rechazos y tiempos; diferenciar resultados diagnósticos.
- [x] Analizar offline1000/2000 y comparar mecanismos1500/1750 sin reducir el mínimo.
- [x] Reproducir exactamente campos científicos de1000/2000/3000 de faseA.
- [x] Emitir LOW_RPM_FAILURE_MECHANISM_IDENTIFIED; conservar2500–3500 público.
- [x] Completar suite existente, OpenSpec estricto y revisión independiente puntual.

Evidencia nueva, sin reemplazar la de faseA:
`results/frontera-baja-2t-20260917/`. Tabla completa en `frontera.md`; diagnósticos
detallados `diagnostico-1000.md` y `diagnostico-2000.md`; campaign.json registra
tiempos, pasos, dt angular/segundos, primeros estados inválidos, balances y
derivados. Los JSON individuales conservan el resultado original completo; los
*-observation.json incluyen locales de RK4/advance y rechazos. No se usa el
formato de aplicación para introducir resultados fuera de su rango público.

Comandos desde la raíz (solo la campaña genera integraciones):
`python -m tools.diagnose_low_rpm --output <carpeta nueva>`;
`python -m tools.analyze_low_rpm --evidence <misma carpeta>` reproduce offline
únicamente intentos existentes al mismo paso. Perfil B/100Pa, mínimo0,001°,
30ciclos/60s/2M RHS/512MiB por punto intactos. Ocho ejecuciones independientes,
66,827s integración (66,811s los siete puntos de frontera),68,594s wall de campaña.
Los tiempos incorporan observación y escritura, no son benchmark sin instrumentación.

| RPM | Clasificación | Ciclos | Integración s | Mínimo medio paso aceptado ° | Rechazos | W_C J | pmax Pa | Peor balance independiente % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|1500|FAIL_MIN_STEP|0|0,031|0,002118121|14|—|—|—|
|1750|FAIL_MIN_STEP|0|0,750|0,001963342|33|—|—|—|
|2000|FAIL_NEGATIVE_FRESH|5|8,156|0,001467500|141|15,96071417 diagnóstico|1281871,358 diagnóstico|0,001369350|
|2250|PASS|11|15,625|0,001316776|252|15,88711098|1289143,321|0,001109984|
|2500|PASS|10|14,734|0,001037568|197|16,20929180|1306559,768|0,000664958|
|2750|PASS|10|13,859|0,001092357|159|16,40461571|1320495,930|0,000632005|
|3000|PASS|10|13,656|0,002348157|191|16,49050751|1331530,846|0,000445966|

1000: a181,428527416° el rechazo local domina en C.F, error6,431575698.
El paso actual0,002276846297° requiere siguiente medio0,000706126890°.
El donante de los enlaces internos K↔C cambia al cruzar Δp=0 con F_C inicial0.
Sin coincidencia geométrica ni térmica; esos enlaces no tienen regularización
exterior. Clasificación probable F (cambio de donante no suave), asociado a E
(límite de especie). No se demostró bug del estimador ni rigidez espectral.

2000: primera negativa en K4 a183° del ciclo1, recuperada. Terminal K4 a
2272,799592767° del ciclo6: F_base=0, F_K3=1,20288235e-11kg, salida integrada
9,52323993e-18kg; se resta del inventario base cero, no del inventario K3.
Solo F viola dominio; m/U/T/p permanecen válidos. Escape C↔E cambia donante
entre etapas. Masa/entalpía/fresca usan el donante correcto; conservación interna
de fresca exacta en ese episodio (primer episodio tiene redondeo7,52e-23kg/s).
Overshoot con escala diagnóstica3e-13kg:3,17441331e-5 terminal;259,966 primero.
No se convierte la escala en tolerancia ni floor.

Corrección de interpretación de faseA: sus “ocho rechazos no físicos” eran ocho
rechazos consecutivos totales: seis locales y dos físicos. El rechazo7 en half-1
se repite idéntico como paso completo en el8 al reducir a la mitad. Una reducción
posterior tendría medio0,002586036619° (>mínimo), pero no se ejecuta más allá del
límite8. Que resolvería el problema queda indeterminado, al igual que el estado
final potencial tras una K4 inválida; no se evalúa RHS con F<0.

1500 tiene negativa C.F cerca de la inversión K↔C y acaba por mínimo;1750
presenta el límite superior F_I>m_I (un ulp al final), no F_C<0, y acaba por mínimo.
No hay un único mecanismo de fallo. La transición terminal de esta malla es
monotónica: menor PASS2250, mayor FAIL2000. Frontera candidata >2000 y≤2250,
sin inferir continuidad ni ejecutar2050/2100/2150/2200.2500 sigue siendo un
límite conservador razonable para el ejemplo/perfil, sin garantía general.

Recomendación: siguiente fase separada sobre positividad conservativa de etapas
y cambios de donante, incluidos límites F=0 y F=m. No autoriza correcciones
ahora. No clipping, limiters, nuevas tolerancias, campaña alta/4T ni candidata.
Sin cambios README que anuncien rango, ni cierre/archivo de aceptación manual.

Comprobaciones:6 pruebas diagnósticas iniciales aprobadas/1,194s. Primera suite
292/81,362s: un fallo de espera3s en test_active_process_survives_navigation_and_cancel
(QProcess doble), sin diferencia científica. Sus12 pruebas aisladas aprobaron/3,921s;
segunda suite completa292/84,652s aprobó sin cambiar aplicación, test ni expected.
Se conservan ambos logs: fallo transitorio no reproducido, causa temporal exacta
no establecida; no se atribuye al solver. OpenSpec estricto aprobado.
Revisión independiente puntual de solo lectura sin defectos; cuatro pruebas de
evidencia repetidas/0,393s (hashes, trayectorias, conteos y etapas), sin campañas
ni replay. Autorrevisión separada del diff: ningún cambio en motorsim/ ni README,
eliminación ajena redme.txt conservada fuera del commit. Sin inspección Windows
nueva ni aceptación manual atribuida; esta entrega es diagnóstica de consola.

## Ampliación candidata 2T — fase A del 17/09/2026
- [x] Separar validadores por ciclo y dominio candidato sin habilitarlo en UI/worker.
- [x] Ejecutar ocho puntos independientes del ejemplo2T Referencia, B/100Pa.
- [x] Registrar balances, ciclos, tiempos, trabajo, presión, derivados y paso mínimo.
- [x] Decisión de fase A: BLOCKED; conservar dominio público2500–3500 para ambos ciclos.
- [ ] Fase B condicionada a GO: planes2–57, presupuesto medido, curva29puntos,
  cancelación larga, CSV/gráfico, inspección Windows y exploración superior.
- [ ] Próxima candidata y aceptación manual: no habilitadas por esta evidencia.

Evidencia: `results/rendimiento-dominio-2t-20260917/campaign.json` y ocho JSON
con caso completo, resultados, balances por volumen/global y muestras. Instrumento:
`python -m tools.verify_2t_rpm_domain --output <carpeta nueva>`;8ejecuciones,
101,765s integración,103,234s wall. No altera modelos, estado inicial, B/100Pa,
RK4, límites, tolerancias ni geometría; reemplaza únicamente RPM en el caso
construido desde example_project('2t-reference'). No son archivos GUI nuevos.

| RPM | Estado | Ciclos completos | Integración s | W_C J | pmax Pa | P indicada W | T equivalente N·m | Peor balance independiente % | Mínimo medio paso aceptado ° |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|1000|No convergido|0|0,016|—|—|—|—|—|0,001749209|
|2000|No convergido, diagnóstico|5|7,890|15,96071417|1281871,358|532,023806|2,54022656|0,001369350|0,001467500|
|3000|Convergido|10|13,422|16,49050751|1331530,846|824,525376|2,62454578|0,000445966|0,002348157|
|5000|Convergido|10|13,156|15,30900149|1381589,029|1275,750125|2,43650326|0,000304383|0,001010962|
|8000|Convergido|11|14,703|12,95447089|1454294,859|1727,262786|2,06176808|0,000238753|0,001705345|
|10000|Convergido|12|16,125|11,60180965|1494822,842|1933,634941|1,84648535|0,000325985|0,001151015|
|12000|Convergido|13|17,406|10,42662663|1527206,218|2085,325326|1,65944917|0,000289815|0,001155323|
|15000|Convergido|14|19,047|8,98865893|1564829,778|2247,164733|1,43058950|0,000361196|0,001438810|

Magnitudes del último ciclo completo;2000 es diagnóstico no aceptado. A1000 no
se extrapola trabajo de ciclo desde la fracción ejecutada. Todos los últimos
ciclos completos conservados cumplen balances; mayor residuo discreto normalizado
en esos ciclos6,10e-14 (límites masa/fresca1e-6, energía1e-5). Límite independiente
0,1%; todos inferiores. Estos balances no sustituyen la convergencia fallida.
Los seis aprobados terminan por tres ciclos consecutivos convergidos.

Fallos concretos sin reparación:
-1000: a181,428527416° el controlador requiere paso0,00141225378068°,
 medio paso0,000706126890342°, menor que0,001°. Cero ciclos completos.
-2000: ocho rechazos no físicos a2272,789248620° (ciclo6); etapa C
 a2272,799592767° con F=-9,523239929231602e-18kg, m=5,723536151636247e-5kg.
 No se recorta F ni se relaja su validación. Cinco ciclos completos conservados.

Intervalo público previamente comprobado conservado:2500–3500. Solo se midieron
seis puntos adicionales/aprobados de la lista; no se afirma continuidad3000–15000
ni se escoge un nuevo rango reducido por inferencia. Por eso BLOCKED, no GO.
No curva29puntos, exploración16000/18000/20000 ni nueva fórmula de presupuesto:
son dependencias de GO. Presupuesto300s, tope5puntos, recálculo/cancelación y
formatos históricos se conservan. No se ejecutó otra campaña4T.

Regresión3000: ciclos, balances, muestras de los dos últimos ciclos, W_C, pmax,
controlador/RHS y derivados exactamente iguales al histórico gui-sweep/point-02.
Prueba inicial de regresión corrigió su lectura: las muestras históricas están
en samples.json, no en summary.json; no requirió reintegrar ni corregir solver.
66 pruebas pertinentes aprobadas:5 dominio,17 barridos,22 Rendimiento/recálculo,
10 integración4T y12 adaptador/proyecto. Logs tests-*.log junto a la campaña.
Incluyen cancelaciones con dobles, protección de curva anterior y recálculo;
no acreditan cancelación de un barrido largo ni inspección Windows nueva.
OpenSpec1.3.1 estricto aprobado y diff --check sin defectos de espacios.
Revisión independiente puntual de solo lectura: sin defectos concretos;
verificó casos que difieren solo en RPM, hashes del núcleo y repitió5 pruebas
de dominio/regresión sin solver. Autorrevisión del diff realizada por separado.
Sin nueva inspección visual: no se amplió ni rediseñó la interfaz. Aceptación
manual pendiente; no archivar, publicar ni reemplazar candidatas.

## Recálculo iterativo posterior a d15ec98
- [x] Mantener controles RPM, comparar plan separado del motor y avisar curva anterior.
- [x] Conservar resultados al iniciar/cancelar/fallar; reemplazar al finalizar correctamente.
- [x] Pruebas A–J y regresiones afectadas.
- [x] Windows: tres cálculos, cambio de plan y cancelación/reintento por ciclo 2T/4T.
- [x] Capturas antes/después, revisión puntual, OpenSpec y documentación final.
Sin rc7 ni archivo; detenerse listo para revisión manual.

Recorridos automatizados Windows del17/09/2026, no aceptación manual: por cada
ciclo, cargar Referencia; calcular2500/3500/500 (3puntos), cambiar Final a3000,
recalcular (2puntos), volver a3500, iniciar/cancelar, reintentar (3puntos).
Tres barridos convergidos y uno cancelado por ciclo, sin cambiar de vista,
recargar proyecto ni borrar archivos. Índices en carpetas exclusivas;40archivos
JSON previos verificados por hash en cada recorrido. Integración total229,969s.
2T:39,719/28,125/1,672cancel/41,905s;4T:43,391/29,344/2,578cancel/43,235s.
Resultados completos externos: `E:\MotorSim distribucion\Rendimiento iterativo rc6`.

21tests iniciales de Rendimiento aprobaron. Revisión independiente puntual:
cancelación tardía podía aceptar índice convergido antes de informar conservación.
Corregido registrando el objeto cancelado antes de sincronizar;6tests de recálculo,
incluido ese caso y reentrada, aprobaron/10,724s. Sin otra revisión general.
Primera suite280: un WinError5/267 al limpiar original.csv temporal, sin fallos de
aserciones. Segunda suite281: dos pruebas numéricas alcanzaron el límite512MiB
del proceso de tests; se ajustó teardown de tests UI para despachar DeferredDelete
y liberar objetos Python. Ningún cambio en límites, solver ni criterios físicos.

Inspección visual del agente: plan cambiado conserva datos y aviso textual;
cancelación4T conserva curva de2puntos y plan de3; resultado final actualizado
y controles visibles. Algunas capturas de escritorio quedaron ocluidas por otras
apps; se excluyen de Git. Finales recapturados con QWidget.grab de ventana Qt
real en Windows al reabrir run-3, sin cálculos adicionales. La evidencia separa
ese reabierto de los recorridos con worker real. Sin rc7; aceptación manual pendiente.

Suite final281 aprobada/66,522s tras corregir la limpieza de tests. OpenSpec1.3.1
estricto aprobado. Logs, hashes y capturas seleccionadas:
`results/rendimiento-iterativo-rc6-20260917/`. Causa raíz: ocultación de setup al
existir curva y clear_sweep al iniciar/sincronizar ejecución; ahora se conserva el
objeto mostrado, se compara plan por separado y se consume una nueva serie una
sola vez al completar. Motor incompatible sigue retirándose. Fórmulas, plan_rpms,
límites RPM, persistencia, solver y convergencia sin modificaciones.

## Dominio público 2T tras P0 — autorización del 17/09/2026
- [x] Habilitar 2500–15000 para 2T en el validador compartido; 4T sin cambios.
- [x] Conservar máximo de cinco puntos, presupuestos, solver y cancelación.
- [x] Actualizar ayuda y README, distinguiendo fuente de EXE anteriores.
- [x] Comprobar contratos, solicitud UI hasta 15000, bloqueo 4T y regresiones.
- [x] Autorrevisión puntual del diff y OpenSpec estricto; sin revisión independiente nueva.

41 pruebas aprobadas: dominio 5, sesión Rendimiento 7, barrido 17,
diagnóstico histórico 6 y recálculo 6. Pruebas Qt sin pantalla y procesos dobles;
no son aceptación manual ni nueva campaña física. Se actualizaron aserciones
que trataban 3501 como inválido para 2T. La prueba de hash histórico reconstruye
exclusivamente el límite anterior de rpm_domain.py; hashes científicos y evidencia
preservados. Sin empaquetar ni publicar; probar desde la fuente actual.
