## Implementación y construcción
- [x] Leer orden, Git limpio main y preservar 18194d7/da27ee25; registrar único cambio.
- [x] Centralizar comando fuente/paquete, errores, recursos y diagnóstico.
- [x] Acerca de, ayuda breve y ejemplos generados desde referencias.
- [x] Entorno aislado fijado, receta/spec, avisos/licencias y commit fuente.
- [x] Construcción Windows x64 onedir y ZIP desde referencia limpia.
## Comprobación
- [x] Suite pertinente y revisión puntual de contratos de distribución.
- [x] Extraer fuera del repo; verificar rutas reales GUI/worker, cwd/entorno independientes.
- [x] Recorrido del ejecutable: persistencia, inválidos, alternancia, protección y antiguos.
- [x] Referencia/proyecto, proceso único, cancelación/cierre, errores controlados y procedencia.
- [x] Lectores/comparación/barrido/importación/CSV con evidencia histórica.
- [ ] Tres puntos completos comparados con referencias; tiempos/budget acumulados <=300 s.
- [x] Capturas reales 150 % y compacto; inspección separada de pruebas.
- [x] ZIP final/SHA256/tamaño, README/hoja de ruta y commit de evidencia.
## Pendientes separados
- [ ] Equipo Windows sin Python instalado, solo si existe entorno autorizado.
- [ ] Uso realmente sin conexión, solo si existe aislamiento sin afectar sesión.
- [ ] Aceptación manual de la usuaria; no atribuida a automatización.
- [ ] Validación experimental; fuera de este encargo.

## Registro de preparación
16/09/2026: Windows 10 19045 AMD64, Python 3.11.0 x64. Entorno .venv-build
independiente, PySide6 6.11.2 y PyInstaller 6.22.3; versiones completas fijadas.
224 pruebas aprobadas (36,193 s), incluidos cinco controles de distribución sin
integraciones. Revisión independiente puntual review_windows_distribution:
sin defectos reproducibles; no acredita el protocolo final aún pendiente.

Paquete trial explícitamente marcado source_dirty/trial construido desde trabajo
posterior a da27ee25, abierto directamente fuera del repo con recursos y ejemplos.
Detectado y corregido nombre ZIP truncado por with_suffix sobre versión con puntos;
no hubo ejecuciones físicas ni cambios de modelo. Automatización externa UIA usa
HWND del proceso y teclado para diálogos Qt: evita bloqueos de Invoke modal.
Recorrido trial de editor: guardar incompleto/Guardar como Unicode, rechazar texto
inválido, Cancelar/Descartar cambios, alternar ciclos, leer v1 sin reescribirlo.
Evidencia trial: E:/MotorSim distribucion/Prueba á rc1/Comprobación (no final).
Herramientas UIA son solo de prueba, excluidas del paquete. Ayuda y licencias se
incluyen; no se asignó licencia nueva al código MotorSim.

## Evidencia de la candidata final — 16/09/2026
Fuente **f46613e4ae9a82dc394db8b6509e782c2121cc3c**, main limpio antes de construir.
Comando ejecutado: `.\.venv-build\Scripts\python.exe packaging/build_windows.py`.
Build UTC 20260916T140209Z, source_dirty=false, trial=false. El commit posterior
solo registra esta evidencia y ajustes del controlador externo de pruebas.
Versiones fijadas: Python 3.11.0, PySide6/Addons/Essentials/shiboken6 6.11.2,
PyInstaller 6.22.3, hooks 2026.7; resto en requirements-build.txt/build.json.

ZIP `E:/dino/Dino/dist/MotorSim-0.1.0-rc1-windows-x64-f46613e4.zip`:
43.376.903 bytes, SHA256
`19eeec5047c9f9f5eab22d7938b9680539e5660649659cb209060ec8b4486d6b`.
Carpeta onedir 104.867.240 bytes. GUI PE x64/subsystem Windows, worker x64/console;
Authenticode NotSigned. 160 archivos; qwindows/qmodernwindowsstyle y qtbase_es;
sin .git, entornos, resultados históricos, diseños web ni instrumentación UIA.
Los hashes de todos los archivos extraídos coinciden después del recorrido.

Extraído en `E:/MotorSim distribucion/Candidata final á 0.1.0-rc1/MotorSim`.
Evidencia íntegra en `E:/MotorSim distribucion/Comprobación final rc1` (fuera de Git).
Cada etapa del script `tests/verify_distribution_windows.py` abre el EXE directo,
con cwd `Directorio distinto`, PATH limitado a Windows y sin variables Python/Qt
de desarrollo; LOCALAPPDATA solo del proceso apunta a `Datos` de esa evidencia.
No se alteraron instalaciones, configuración global, credenciales ni políticas.
Se verificaron rutas GUI/worker y módulos cargados: ambos usan
`MotorSim/_internal/python311.dll`; el worker no carga Qt. Sin nueva consola visible
mientras estaba activo. La herramienta externa Python/UIA no suministra dependencias.

### Automatización del ejecutable
- `editor-evidence.json`: Nuevo/Abrir/Guardar/Guardar como, acentos, incompleto,
  error de entrada sin sobreescribir, Cancelar/Descartar, 2T→4T con comprobación de
  selección intermedia, igualdad del JSON recuperado, v1 leído sin reescribir y
  conversión explícita a v6. Ejemplos sintéticos y datos de ensayo separados.
- `cancel-evidence.json`: botón Cancelar (0,235 s) y cierre (0,203 s), ambos
  cooperativos, resultado cancelled y ningún worker huérfano.
- `process-modules.json` / `process-evidence.json`: inspección de módulos con una
  tercera cancelación. Esta activó el límite de seguridad de 3 s; sin manifiesto
  final ni éxito ficticio. Se conserva attempts.csv/case.json. No se acredita
  cancelación cooperativa en este intento ni se atribuye una causa no demostrada.
  La operación externa completa duró 9,186 s; se reserva una cota de 10 s en el
  presupuesto, sin presentar esa cota como integración medida. Sin huérfano.
- `Auxiliar ausente/missing-evidence.json`: copia de control sin worker, mensaje
  útil, sin cálculo ficticio. La candidata original permanece intacta.
  FailedToStart y diagnóstico local también cubiertos por las cinco pruebas unitarias.
- `history-evidence.json`: 4T histórico, comparación A/B compatible, exportar CSV,
  abrir/exportar barrido histórico. Copias fuera del repo; ninguna reintegración.
- `external-evidence.json`: importar CSV de prueba **sintético/no medido**, declarar
  4T/720° y J/ciclo, vista previa, guardar/reabrir, contrastar dos RPM exactas y
  exportar contraste. No representa mediciones ni validación experimental.
- `provenance-evidence.json`: aviso de configuración anterior al editar diámetro,
  lector 2T v1, navegación compacta por teclado; cierre con Descartar explícito.
- `about-evidence.json`: versión/commit reales y ayuda incluidos, accesibles sin Git.

Los fallos del controlador UIA se conservan como archivos *failure.txt: selección
Qt popup, espera de diálogos y confirmación de cierre. Se corrigió el controlador,
no la física ni el producto, y no se repitieron integraciones completas.

### Regresión numérica autorizada
`numerical.json`, `numerical-comparison.json` y `budget.json` identifican resultados.
Referencias: `results/simulacion-2t/integracion-ui-20260915/manifest.json` y
`results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep/point-01,point-02/manifest.json`.

| Caso B/100 Pa | Ciclos | Integración s | W_C J | pmax Pa | RHS | Pico MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2T referencia 3000 | 10 | 13,734 | 16,49050751206088 | 1331530,846070603 | 228171 | 26,523 |
| 4T proyecto 2500 | 7 | 14,797 | 52,302884330421655 | 2641806,76632688 | 305572 | 30,336 |
| 4T proyecto 3000 | 7 | 14,860 | 50,52602475854359 | 2618462,4643861516 | 304466 | 48,840 |

Tres convergidos, balances aprobados, misma secuencia de estados/ciclos/muestras,
trabajos, presiones, RHS/pasos/rechazos y condiciones **exactamente iguales** a las
referencias. Las entradas 2T son iguales completas; en 4T solo difieren nombre del
proyecto, ruta de procedencia e ID de serie. No se omiten diferencias físicas.
No se comparan reloj, memoria ni identificadores de ejecución por igualdad.
Los tres summary.json declaran qt_loaded=false; estados iniciales y límites intactos.
Sin A/B/C, bandas alternativas ni compresión adicional.

Tiempos 4T preparación/escritura/total de punto: 2500 = 0,015/0,265/15,234 s;
3000 = 0,000/0,250/15,110 s. Barrido: integración 29,657, proceso 30,922,
percibido 31,797 s. Cero preparación a esa resolución no significa costo nulo.
**Pendiente temporal 2T:** el contrato v1 no persiste los tiempos adicionales que
emite el worker y la GUI no los conserva. No es posible recuperarlos del resultado
ya ejecutado; no se inventan ni se repite un punto solo para obtener evidencia.
Por eso la tarea conjunta de puntos/tiempos permanece sin marcar, aunque igualdad
y convergencia de los tres puntos están acreditadas.
Presupuesto: tres puntos 43,391 s + dos cancelaciones 0,438 s + cota 10 s del
intento forzado = **53,829 s contabilizados de 300**. Sin reiniciar presupuesto.

### Inspección visual y pendientes
Capturas del EXE extraído: `paquete-editor-150.png`, `paquete-compacto-150.png`,
`paquete-barrido-150.png`, `paquete-importacion-150.png`, `paquete-comparacion-150.png`,
`paquete-acerca.png`. Inspeccionadas editor/compacto/barrido/importación/Acerca de:
legibilidad, foco, reflujo y scroll; compacto 1000×740 y factor Qt 1,5, navegación
por teclado a Simulación. No son aceptación manual de la usuaria.
La captura `paquete-2t-150.png` procede del punto efectivamente calculado.
No se acreditan Windows distintos de Windows 10 19045 x64.

**Por verificar:** desglose temporal 2T, equipo sin Python instalado y offline
real aislado. No existe entorno limpio/aislado disponible; no se desconectó red ni
se cambiaron políticas. Aceptación manual y validación experimental siguen separadas.
Se entrega ZIP candidato con recorrido acreditado y estas limitaciones, no cierre
completo de todas las comprobaciones. Sin publicar, etiquetar, archivar ni ampliar física.


## Hardening rc1 → rc2 autorizado — registro posterior
- [x] Preservar rc1/f46613e y d6f0c63, comprobar árbol inicialmente limpio.
- [x] Inspeccionar evidencia de parada y consumir única reproducción focalizada.
- [x] Corregir tiempos futuros compatibles; regresiones con reloj controlado.
- [x] Conservar diagnóstico local de parada forzada, sin relajar límite.
- [x] Suite completa, revisión independiente y OpenSpec finales.
- [x] Commit fuente limpio y build rc2; conservar ZIP rc1.
- [x] Extraer rc2 fuera del repo y comprobar recorridos Windows/150 %.
- [x] Solo un punto completo 2T y uno 4T B100/3000; contraste exacto y tiempos.
- [x] Identificar artefactos y commit de evidencia; separar pendientes externos.

Diagnóstico histórico **F — evidencia insuficiente**, no resuelto por inferencia.
Prueba original: etapa process de verify_distribution_windows.py, lectura externa
EnumProcessModules/GetModuleFileNameEx de GUI PID7736 y worker PID7052, luego Cancelar.
Ambos procedían de la carpeta rc1 extraída. Caso admitido: entradas de case.json
idénticas a reference_inputs(), S2T-0D-01/B/100 Pa/3000 rpm, no caso fuera de dominio.
Última fila attempts.csv: inicio 222,39608961371155°, paso 0,1039103862884474°,
aceptado, error 0,0013333369482184684, RHS3048, primer ciclo (ninguno completo).
La fila describe un paso hasta 222,5°, no acredita el estado final en el instante
exacto de terminación. No se conserva vector de estado final ni summary/manifest.
Sí existe case.json con run_id: el worker alcanzó la etapa de escritura del resultado.
La GUI registró solicitud de cancelación y, al vencer QTimer(3000), el mismo QProcess
seguía asociado: _kill_if_active llamó kill. Esa es la condición exacta de protección;
no es un límite de presión, dominio físico ni tolerancia numérica.
Faltan traza del worker durante esos tres segundos y tiempos de escritura/IPC;
no se puede distinguir demora de escritura, scheduling o fallo interno con lo guardado.

Única reproducción focalizada: misma rc1, referencia y etapa process, en
`E:/MotorSim distribucion/Hardening rc1 reproducción única`. Cancelación cooperativa,
1,922 s de integración, manifiesto cancelled, sin huérfanos ni consola adicional.
No reprodujo la parada forzada. No se repetirá este diagnóstico ni se declarará causa
B/C/D/E sin evidencia. La rc2 conserva ahora stderr/progreso/salida/PID/programa en
el diagnóstico local si actúa el mismo límite; no es telemetría ni cambia la protección.

Tiempos: el lector existente valida timings opcionales en v1–v4. Se elimina solo
la restricción de escritura >=3 para resultados nuevos y tiempo percibido de la
GUI. Abrir históricos no escribe; no se asignan tiempos retroactivos. JSON motor v6
y versiones de resultados/modelos intactos. Candidata se incrementa a 0.1.0-rc2.
Regresión específica: 9 pruebas aprobadas en 3,176 s, sin integración.
Revisión independiente review_rc2_hardening: sin defectos reproducibles introducidos;
9 pruebas en 1,761 s, sin integración y sin acreditar aún el paquete.

Suite final: **228 aprobadas, 22,262 s**. Primera pasada: 227/228 y timeout
en prueba controlada de hijo sleep; módulo aislado 7/7, 4,833 s. Se ordenó kill
antes del diagnóstico para no supeditar la parada a la escritura del log; ningún
plazo de producto ni prueba se amplió. Revisión informada del cambio puntual.
OpenSpec estricto aprobado. Sin integraciones físicas en estas pruebas.


### Paquete rc2 y comprobación final — 16/09/2026
Fuente limpia **580c3f8e6bf816aaeef9f20f17a9b74a7d481df8**, build UTC
20260916T143214Z; mismo comando/entorno fijado, sin actualizar herramientas.
Carpeta `E:/dino/Dino/dist/MotorSim-0.1.0-rc2-windows-x64-580c3f8e/MotorSim`,
entrada MotorSim.exe; ZIP hermano `MotorSim-0.1.0-rc2-windows-x64-580c3f8e.zip`.
ZIP 43.376.832 bytes; carpeta 104.867.659 bytes; SHA256
`9686135082d2854e1ed7aa653cf21645317f2474bcede8d52f44085fe68a1b35`.
Authenticode NotSigned. Windows 10 19045 AMD64; no se acredita otro Windows.
El hash de rc1 sigue siendo 19eeec5047c9f9f5eab22d7938b9680539e5660649659cb209060ec8b4486d6b, sin sobrescribir ZIP ni evidencia.

Extracción nueva: `E:/MotorSim distribucion/Candidata final á 0.1.0-rc2/MotorSim`.
Evidencia: `E:/MotorSim distribucion/Comprobación final rc2`.
GUI/worker directos desde esa carpeta, cwd ajeno y entorno limitado al proceso;
sin PYTHONPATH/VIRTUAL_ENV, PATH Windows. process-modules.json confirma Python DLL
local en ambos y ausencia de Qt en worker, durante los puntos autorizados, sin
consola visible. Los 160 archivos extraídos conservan hashes de ZIP tras las pruebas.
Sin entornos, tests ni históricos dentro del ZIP. Ayuda/Acerca de muestran rc2/fuente.

- editor-evidence.json: edición, incompleto, inválido, guardar/guardar como, nombre
  Unicode, protección, alternancia comprobada, v1 sin reescritura/conversión explícita.
- history-evidence.json: reabrir 4T, comparar/exportar CSV, abrir barrido previo y CSV,
  sin nuevo barrido numérico.
- external-evidence.json: importación declarada sintética/no medida, vista previa,
  persistencia/reapertura y contraste/CSV, sin cálculos ni atribuir mediciones.
- reopen-evidence.json: reabrir 2T v1 nuevo muestra tiempos, bytes de manifiesto
  intactos; corrupto artificial rechazado conservando el resultado válido.
- cancel-once-evidence.json: control breve del recorrido Windows final, Cancelar
  cooperativo, 0,235 s, sin huérfanos, no resultado aceptado. No fue otra reproducción
  de la inspección de módulos rc1. Cierre final de cada recorrido sin procesos activos.
- Auxiliar ausente/missing-evidence.json: copia de control sin worker, mensaje útil
  sin cálculo. Permiso denegado y FailedToStart cubiertos por regresión controlada;
  no se modificaron ACL, políticas o configuraciones del equipo para simularlos.
- about-evidence.json: rc2/commit y guía breve incluidos.
- Capturas reales Windows con QT_SCALE_FACTOR=1.5: rc2-2t-150.png, rc2-4t-150.png,
  paquete-editor-150.png, paquete-compacto-150.png, paquete-comparacion-150.png,
  paquete-importacion-150.png, paquete-acerca.png, rc2-tiempos-final-150.png.
  Inspección focal de resultado y desglose temporal; sin nueva revisión estética.
  Automatización externa no acredita aceptación manual de la usuaria.

### Dos únicos puntos completos de hardening
hardening-numerical.json y numerical-comparison.json registran referencias/archivos.

| B/100 Pa, 3000 rpm | Ciclos | Integración s | Preparación s | Escritura s | Total punto s | Percibido s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2T referencia | 10 | 13,843 | 0,000 | 0,157 | 14,125 | 14,890 |
| 4T proyecto S4T exacto | 7 | 14,609 | 0,000 | 0,234 | 14,937 | 15,406 |

Preparación corresponde al intervalo existente del worker (resolución de reloj);
no es todo el arranque del proceso, incluido en percibido. Cero no afirma costo nulo.
2T: W_C=16,49050751206088 J, pmax=1331530,846070603 Pa, RHS228171,
pico26,637 MiB. 4T: W_C=50,52602475854359 J, pmax=2618462,4643861516 Pa,
RHS304466, pico29,977 MiB. Ambos balances aprobados.
Comparación exacta de estados/ciclos, trabajos, presión, muestras, condiciones,
RHS/pasos/rechazos contra integracion-ui-20260915 y R2/gui-sweep/point-02.
2T entradas completas iguales; 4T solo difiere nombre/ruta del proyecto y contexto
de serie (ahora punto individual). No se exceptúan diferencias físicas ni se
comparan reloj/memoria por igualdad. Contratos v1/v4 y motor v6 intactos.
Sin A/B/C, otras bandas, barridos completos nuevos ni repetición de puntos.

Integración de esta orden: reproducción única rc1 1,922 s + puntos rc2 28,452 s +
cancelación breve final 0,235 s = **30,609 s**. Si se suma el registro histórico
53,829 s (incluida su cota), acumulado **84,438 s de 300**; no se reinicia presupuesto.

### Estado de cierre
- [x] Desglose temporal futuro 2T corregido y acreditado sin inventar históricos.
- [x] Paquete rc2 reconstruido/probado; no otros defectos reproducibles identificados.
- [ ] Causa original de parada rc1: **F**, faltan traza y tiempos IPC/escritura
  originales; única reproducción no la repitió. No se declara resuelto.
Se detiene este diagnóstico en el límite autorizado, sin nuevos intentos.
El pendiente temporal histórico rc1 sigue sin marcar: no hay datos para rellenarlo;
la corrección hacia adelante se acredita arriba. Cierre técnico total no declarado.
Equipo sin Python instalado y offline real: sin entorno aislado autorizado disponible;
no se alteró equipo/red. Aceptación manual y validación experimental separadas.
La evidencia posterior se registra en otro commit, sin modificar el código empaquetado.
Sin push, tag, release, archivo OpenSpec ni cambios de credenciales/configuración global.
