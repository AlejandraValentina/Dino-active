## Entrega 7 — configuración y persistencia
- [x] 7.1 Válvulas, validaciones, ley de alzada/área y cruce analítico comprobados.
- [x] 7.2 JSON v6, lectura v1–v5 y conductos independientes sin pérdida de borradores.
- [x] 7.3 Editor, curvas, guardar/reabrir, alternancia y Windows/150 % comprobados.

Entrega 7 completada técnicamente para el alcance geométrico. Aceptación manual de
la usuaria pendiente y separada; no se atribuye una aceptación a la automatización.

## Entrega 8 — núcleo y condiciones de continuación
- [x] 8.1 Tres volúmenes/nueve componentes y cuatro enlaces; invariantes independientes,
  norma/RK4, trabajo 720°, calor cerrado una vez por período y ausencia de W_K.
- [x] 8.2.1 A100 desde estados originales: convergencia/balances y presupuesto aprobados.
- [x] 8.2.2 B100/C100 desde estados originales: convergencia/balances/presupuesto y
  tolerancias de sensibilidad aprobados, sin arranque caliente.
- [x] 8.2.3 Evaluación histórica R1 realizada: tendencia FALLA pmax/Y_I; no se declara aprobada.
- [x] 8.2.R2 Revisión expresamente autorizada: estabilidad práctica de todas las magnitudes,
  con las demás puertas conservadas. A/B/C reutilizados sin integrar y hashes intactos.
- [x] 8.2.4 C50 ejecutado y aprobación de banda frente a C100 con tolerancias originales.
- [x] 8.3 Integración asíncrona 4T, snapshot independiente sin exigir datos 2T,
  resultados estrictos reabribles de 1441 muestras, comparación y barrido.
- [x] 8.4 Declaración externa del ciclo 4T sin reinterpretar importaciones históricas.
- [x] 8.5 Protocolo integrado: B2500/3000/3500 GUI, C extremos, compresión 8.2 B/C
  y regresión 2T B, todos convergidos; contrastes y presupuestos aprobados.
- [x] 8.6.1 Suite pertinente final y una revisión puntual independiente de la continuación.
- [x] 8.6.2 Capturas de configuración/curvas geométricas/conductos y documentación preservadas.
- [x] 8.6.3 Capturas reales de resultado, comparación y barrido 4T al 150 %, reabriendo evidencia.
- [ ] Aceptación manual del bloque por la usuaria: pendiente, distinta de automatización.
- [ ] Contraste con mediciones y validación experimental: no realizados ni atribuidos.

Entrega 8 completada técnicamente para el alcance 0D autorizado bajo R2 y banda.
Sin archivar, publicar, empaquetar o ampliar física. Los pendientes manuales y
experimentales permanecen separados; no son una aceptación implícita.

## Evidencia histórica R1 del 16/09/2026

Esta sección conserva el estado antes de R2 (commits af11976 y b862900).
Los bloqueos y no-ejecuciones aquí descritos corresponden a ese momento.

Git inicial limpio, main, 6cbed3609562e291a62858891b63539625a2e145, remoto origin
conservado. Cambios propios en commits locales; sin publicar ni tocar credenciales.
AGENTS actualizado para sustituir la prohibición anterior de iniciar 7. Sin init,
update, integración automática ni modificaciones globales.

### Pruebas automatizadas

Suite final completa pertinente: `python -m unittest discover -s tests -p 'test*.py'`,
203/203 aprobadas (18,506 s). Ocho controles numéricos/geométricos nuevos y cinco
controles Qt nuevos. Referencias independientes: seno en 0/110/220°, áreas 24π y
93,75π, cruce 40° partido en 0–20/700–720; compresión pV^gamma, balance U+W=Q,
trabajo neto cerrado de dos vueltas, nueve componentes reales y prueba de secuencia
sin segundo calor. Los controles comunes de donante/recipientes/invariantes se
conservan. Los controles de proceso usan un hijo doble que NO integra; cero
campañas completas dentro de la suite.

Autorrevisión del principal: el extremo con apertura/duración decimal podía dejar
residuo trigonométrico por representación float. Se reconoce el evento analítico
hasta ocho ULP, sin redondear a muestras. Ocho pruebas afectadas aprobadas (0,508 s).
Se contrastaron 715000 evaluaciones geométricas de las trazas existentes con la
fórmula previa: igualdad exacta para S4T-0D-01; no justifica repetir sus ejecuciones.
La referencia textual de conductos 4T quedó específica en el JSON final; los
case.json originales del protocolo conservan el identificador geométrico común
2T usado al ejecutar, sin alterar ninguna dimensión ni evidencia retrospectiva.

Lectura comprobada de resultados históricos v1 (integracion-ui-20260915), v2
(editor-20260915/A) y v3/barrido (barrido-20260915/gui-sweep); reconstrucción exacta
de contratos anteriores sin alterar archivos/hashes. Migración de proyectos v1–v5,
JSON v6 completo/incompleto, texto inválido, guardado seguro, errores/cancelaciones,
borradores específicos y teclado comprobados. No es nueva aceptación histórica.

### Ejecuciones numéricas completas (separadas de la suite)

Directorio local preservado: `results/simulacion-2t/cuatro-tiempos-20260916/`.
Cada perfil conserva case.json, attempts.csv y result.json; protocol.json contiene
presupuesto, puertas y sensibilidad. environment.json: Windows 10 19045, Intel
Core i5-10400, Python 3.11.0, sin Qt cargado. Un mismo proceso de consola conservó
resultados precedentes; los picos RAM incluyen esa retención.

| Perfil/banda | Ciclos / convergencia | W_C J/720° | pmax Pa | Peor balance independiente normalizado | s integración | Pico MiB | RHS |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A100 | 7 / sí | 50.526033958914 | 2618462.697374 | 1.08360976085e-5 | 7.438 | 28.4375 | 160711 |
| B100 | 7 / sí | 50.526024758544 | 2618462.464386 | 7.68337521458e-7 | 14.406 | 45.65625 | 304466 |
| C100 | 7 / sí | 50.526024465131 | 2618464.732577 | 2.59994897697e-7 | 29.281 | 52.37109375 | 607098 |

Balances discretos máximos m/U/F normalizados del último ciclo: A 3.76e-15,
B 1.19e-14, C 5.88e-14. Todos los tres ciclos de cierre de cada ejecución cumplen.
Y finales I/C/E: A [0.9947751982824065, 0, 0],
B [0.9947751875142438, 0, 0], C [0.9947752054491011, 0, 0].
Medios pasos aceptados A/B/C: 21238 / 40472 / 80830;
rechazos error/físicos: 93/6, 59/6, 47/19. Sin recortes de estado.
Presupuesto consumido: **3 ejecuciones, 51.125 s de integración de 720 s**.
No hubo repeticiones numéricas ni C50, ni las ocho ejecuciones integradas dependientes.

Sensibilidad B/C: W 5.8072e-9 relativa, pmax 8.6623e-7 relativa,
curva 1.5602e-8 relativa, máxima diferencia Y 1.7935e-8,
máxima diferencia normalizada de masas por enlace 4.3415e-9. Tolerancias aprobadas.
**Tendencia falla**: pmax A/B 8.8979e-8 < B/C 8.6623e-7;
Y_I A/B 1.0768e-8 < B/C 1.7935e-8. La regla no dispone de pisos adicionales para
estas magnitudes. C encuentra pmax entre nodos comunes (máximo muestreado
2618462.460408 Pa a 376.5°, frente a pmax 2618464.732577 Pa). Explicar la diferencia
no permite dispensar tendencia ni ocultar el fallo de Y_I. No se identificó un
defecto demostrable del modelo/implementación que autorice repetir o corregir física.
Los archivos de diagnóstico de consola NO son resultados GUI aceptados/reabribles.

### Inspección visual Windows (no aceptación manual)

`python tests/verify_four_stroke_windows.py --output results/simulacion-2t/cuatro-tiempos-20260916/windows-150`
ejecutado con escritorio Default desbloqueado y DPR efectivo 1.5, sin cambios de
políticas ni escala global. QProcess.start bloqueado en el recorrido: cero cálculos.
Edición, guardar, cierre/reapertura, cambio de ciclo con datos separados, inválidos,
protección al cerrar y foco/Tab comprobados. Capturas reales en docs/images:
`motorsim-4t-editor-150.png`, `motorsim-4t-alzada-cruce-150.png`,
`motorsim-4t-area-cruce-150.png`, `motorsim-4t-conductos-150.png`,
`motorsim-4t-compacto-150.png`. Inspeccionadas por el principal: grupos adaptables,
scroll vertical para contenido largo, sin scroll horizontal a 700 px lógicos,
foco visible, curvas y cruce legibles. Archivo de prueba claramente sintético;
no representa el caso usado en la prueba numérica (cruce modificado solo para UI).
Registro: windows-150/recorrido.json. Resultado/comparación/barrido 4T no se capturan
porque no fueron habilitados; ninguna imagen ficticia los sustituye.

### Revisión puntual y estado

Subagente de solo lectura review_four_stroke, una única revisión del diff/contratos
y evidencia: sin defectos reproducibles. Recalculó sensibilidad desde resultados,
confirmó el bloqueo y cotejó estado inicial/RHS 2T contra HEAD en diez ángulos con
igualdad exacta, sin otra integración. Autorrevisión del principal de documentación,
compatibilidad, extremo decimal corregido y capturas; no se presenta como revisión
independiente de esas actividades posteriores.

OpenSpec 1.3.1: validación estricta aprobada. status documental completo no es cierre
funcional. Python 3.11.0/PySide6 6.11.2/Node 24.19.0 disponibles, sin instalar nada.
Aceptación manual de la usuaria del bloque 4T: pendiente. Mediciones reales y
validación experimental: pendientes; herramientas de entrega 6 preservadas.
No archivar, empaquetar, publicar ni comenzar otra ampliación física.

### Identificación de resultados preservados (SHA-256 result.json)

- A-100: `429ceae4d3c5885a2db72a49c52b3797c6e9427d7085f9c1ff57077d7a95271e`
- B-100: `f44d8ccac99085318b99859defa06cbc1d276b84d610c9336847e39de005b994`
- C-100: `615f196a99e802cca2c2d58c3c6079744c5a29ead5952f1cd0f88d28f43abd8e`


## Continuación R2 — 16/09/2026

Git inicial limpio en main, b86290082621641b9d2e93579324263bac13852b; af11976 y
6cbed360 preservados, sin reemplazar trabajo por el remoto. Autorización R2 registrada
brevemente en design/spec/AGENTS. No se ejecutaron init/update ni autenticación/push.

### Reevaluación y banda

R1 permanece fallida en tendencia de pmax/Y_I. R2 aprobó por **estabilidad práctica**,
no por monotonía. Lectura directa de A100/B100/C100; identidades, entradas/perfiles/
banda y hashes cotejados, resúmenes y muestras originales validados por el lector
estricto según I/C/E: fase, dimensiones, termodinámica, flujos, balances y correspondencia.
La referencia textual de conductos histórica se conserva como consta arriba.
No hubo reintegración ni modificación de A/B/C. `R2/evaluation.json` guarda el
criterio nuevo separado, A/B y B/C originales, dispersión y diferencias entre ciclos.

| Dispersión completa A/B/C | Valor | Límite R2 |
| --- | ---: | ---: |
| W normalizada | 1.87898844018e-7 | 1e-4 |
| pmax monitorizada normalizada | 8.66229102962e-7 | 1e-4 |
| Curva original, mismos nodos/fase | 9.31400390065e-8 | 1e-4 |
| Enlace 0 normalizada | 1.33875604971e-7 | 1e-4 |
| Enlace 1 normalizada | 1.16371313444e-7 | 1e-4 |
| Enlace 2 normalizada | 1.16835028459e-7 | 1e-4 |
| Enlace 3 normalizada | 1.17558552357e-7 | 1e-4 |
| Y_I absoluta | 1.79348573770e-8 | 5e-5 |
| Y_C / Y_E absolutas | 0 / 0 | 5e-5 |

Umbral 1e-4 = 0,01 %, decisión práctica, no redondeo de máquina ni error exacto.
pmax C monitorizada 2618464.732576508 Pa; máximo de muestras 2618462.4604077553 Pa:
no se reemplaza ni interpola el pico. Últimos cambios de ciclo A/B/C: W
6.40348e-6 / 7.59327e-6 / 7.59224e-6 J; pmax 0.154897 / 0.185855 / 0.185532 Pa;
curva 0.161925 / 0.194232 / 0.194200 Pa; Y_I 4.96305e-8 / 2.12685e-8 / 2.12647e-8.
W/Y/curva superan algunas discrepancias entre perfiles (por ejemplo W B/C
2.93413e-7 J): no puede separarse el residuo periódico ni atribuirse todo al paso.

C50 convergió desde los estados originales. Frente a C100: W 3.76547e-5,
pmax 4.03638e-5, curva 4.03831e-5 y enlaces máximo 3.84136e-5 relativos;
Y_I 2.38796e-5 absoluto. **Banda aprobada** con límites originales 1 % / 0,005,
sin tendencia de tres perfiles. El diagnóstico reutilizado de sensitivity conserva
su bandera R1 no aplicable; `band_acceptance` explicita la aprobación de banda.
No acredita ley original sin regularizar, calibración ni validación experimental.

### Protocolo completo y coste real

Raíz local `results/simulacion-2t/cuatro-tiempos-20260916/R2/` (ignorada por Git).
Nueve ejecuciones nuevas + tres históricas = **12, total 249,015 s de integración**
de 720 s, sin reiniciar presupuesto ni repetir. Límites 60 s/30 ciclos/512 MiB y
RHS/paso/rechazo vigentes conservados. Cada ejecución terminó por tres ciclos
consecutivos de convergencia; balances discretos e independientes aprobados.

| Ejecución nueva | Ciclos | W_C J/ciclo | pmax Pa abs. | Mayor balance independiente normalizado | Integración s | Pico MiB | RHS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C50 / 3000 | 7 | 50.524121921 | 2618359.045767 | 2.373976296e-07 | 31.797 | 27.539 | 607800 |
| GUI B / 2500 | 7 | 52.302884330 | 2641806.766327 | 1.513637312e-06 | 15.281 | 28.793 | 305572 |
| GUI B / 3000 | 7 | 50.526024759 | 2618462.464386 | 7.683375215e-07 | 15.203 | 47.207 | 304466 |
| GUI B / 3500 | 7 | 48.586820856 | 2591893.105038 | 8.447462250e-07 | 14.735 | 55.352 | 305097 |
| C / 2500 | 7 | 52.302883564 | 2641810.895449 | 4.190489924e-07 | 30.063 | 28.793 | 607088 |
| C / 3500 | 7 | 48.586820571 | 2591893.067183 | 2.182603077e-07 | 30.875 | 28.996 | 606681 |
| GUI B / compresión 8.2 | 7 | 50.954902958 | 2685606.691958 | 7.519743835e-07 | 15.531 | 28.395 | 305341 |
| C / compresión 8.2 | 7 | 50.954902429 | 2685613.829712 | 3.412404240e-07 | 30.609 | 28.828 | 607355 |
| Regresión 2T B / 3000 | 10 | 16.490507512 | 1331530.846071 | 4.459656622e-06 | 13.796 | 25.078 | 228171 |

Trabajo 4T completo 720°; última fila 2T completo 360°, no equivalencia entre ciclos.
Picos del barrido incluyen retención de puntos anteriores en el proceso secuencial.
Mayor residuo discreto final entre las nuevas ejecuciones: 7,034e-14 normalizado.
GUI3000: ciclos, muestras y RHS idénticos a B100 original, sin exigir igualdad de
reloj. La copia compresión 8.2 proviene del editor **sin guardar** y solo cambia ese
dato físico; B obtiene ΔW=+0.428878199 J y Δpmax=+67144.227572 Pa respecto a 8.
Es el resultado del caso, no una mejora impuesta ni validación de rendimiento real.

| Contraste B/C | W relativa | pmax relativa | Curva relativa | Máximo enlace relativo | Máximo Y absoluto |
| --- | ---: | ---: | ---: | ---: | ---: |
| C100-2500 | 1.46532480e-08 | 1.56298940e-06 | 7.82693829e-09 | 8.60320716e-09 | 1.39680848e-07 |
| C100-3500 | 5.86756471e-09 | 1.46049774e-08 | 1.59939840e-08 | 1.20173744e-08 | 1.49768277e-08 |
| C100-compression-8.2 | 1.03792786e-08 | 2.65777371e-06 | 5.40990225e-09 | 6.51813979e-09 | 1.81075039e-08 |

Todos los contrastes B/C aprueban tolerancias originales; tendencia no aplicable
con dos perfiles. Regresión 2T: diez ciclos, estados/resúmenes/muestras y RHS
idénticos a `integracion-ui-20260915`; W_K=-3.3651306484080394 J permanece separado.
Lectura estricta adicional de resultados históricos v1/v2/v3 y barrido aprobada.
El B100 histórico se reempaquetó declarativamente en `reference-B100-reader` para
verificar el contrato fijo 4T: no fue una nueva ejecución ni alteró el original.

### Integración, pruebas e inspección

Editor → snapshot → hijo usa geometría/válvulas/distribución/conductos efectivos,
sin completar ausencias desde referencia. 4T no exige borradores inactivos 2T.
Proyecto JSON v6 intacto; resultado 4T v4 con validación de I/C/E, cuatro enlaces,
1441 muestras, unidades/termodinámica/fase/flujos/resumen. Reapertura conserva
procedencia, estado real y límites. Comparación y barrido no muestran W_K ficticio.
CSV identifica J/720°. Externos v2 declaran trabajo 4T/720 o presión con ciclo 2T/4T;
v1 histórico se conserva, presión sin ciclo se abre sin habilitar equivalencia.
Pruebas externas usan fixtures sintéticos temporales, no mediciones inventadas.

Suite final `python -m unittest discover -s tests -p 'test*.py'`: **219 aprobadas,
23,423 s**. Incluye R2 normal/práctica/fallo/ausencias/NaN/Y inválida, propagación
al modelo, RPM/tiempo/dVdt/aporte, contratos/CSV/ciclo, snapshot sin guardar,
validación conjunta, no duplicación, cancelación/cierre/stale y persistencia previa.
Dobles de proceso/secuencia, sin nuevas integraciones completas dentro de la suite.
OpenSpec 1.3.1 estricto aprobado. Sin dependencias ni cambios globales.

Una revisión independiente de solo lectura (`review_four_stroke_r2`) encontró
finitud/coherencia insuficiente en el evaluador R2 y capturas con MotorSim oculto.
Se corrigió el evaluador y se añadió regresión; no afecta los datos originales,
ya comprobados por lector estricto. Se recapturó reabriendo archivos, con inicio de
procesos bloqueado y ventana al frente. No se reintegró ni se abrió otra auditoría.
Autorrevisión del principal: diff, docs, contratos y seis imágenes finales inspeccionadas.

Windows Default desbloqueado, Qt Windows, DPR **1.5**. Automatización GUI para
barrido y compresión; luego reapertura/CSV/comparación y seis capturas reales en
`docs/images/motorsim-4t-*-r2-150.png`: resultado, curvas, comparación,
comparacion-curvas, barrido y barrido-trabajo. Texto y tablas legibles, fase 0–720°,
P-V temporal, scroll vertical disponible, sin K ni curvas sintéticas de presentación.
El recorrido conserva datos identificados EJEMPLO SINTÉTICO. Evidencia:
`R2/windows-execution.json` (operaciones) y `R2/windows-reopen.json` (captura visible
corregida, cero cálculos). Los CSV finales con ciclo están en `sweep-csv-cycle` y
`comparison-csv-cycle`. No se atribuye aceptación manual a estas automatizaciones.

Relectura sin integrar: `python tests/verify_four_stroke_protocol.py --root
results/simulacion-2t/cuatro-tiempos-20260916/R2`. Captura sin calcular:
`python tests/verify_four_stroke_run_windows.py --root
results/simulacion-2t/cuatro-tiempos-20260916/R2`. La opción --execute se utilizó
una sola vez en cada script para los puntos autorizados; rechaza destinos existentes.

Pendientes reales: aceptación manual de la usuaria del bloque; mediciones adecuadas
y validación experimental; publicación a cargo de la usuaria. Entregas 7/8
completadas técnicamente para este alcance, sin pretender monotonía R1, orden de
convergencia o error exacto. No archivar, empaquetar ni iniciar otra ampliación.
