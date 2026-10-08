# Tareas de comparacion-resultados

- [x] 1. Comprobar Git, leer contratos y registrar alcance autorizado preservando entrega 5.
- [x] 2. Implementar selección/compatibilidad y diferencias geométricas/descriptivas con lector existente.
- [x] 3. Integrar tabla y superposición A/B por fase con ejes comunes, sin cálculos nuevos.
- [x] 4. Implementar CSV fiel/exclusivo y tratamiento de errores.
- [x] 5. Probar identidades/inversión/porcentajes, entradas, fase/P-V, incompatibilidad, errores y ausencia de cálculos.
- [x] 6. Comprobar Windows/150 % con resultados existentes y capturas/CSV; revisión puntual y OpenSpec.
- [x] 7. Registrar evidencia/pendientes en README/hoja y commit propio sin publicar ni archivar.

Entrega 6 En curso. Barridos e importación de mediciones pendientes, fuera de este
tramo; no se especifican ni implementan. Entrega 5 y aceptación manual pendiente
conservadas. No se repiten simulaciones ni verificaciones históricas.

## Evidencia — 15/09/2026

Inicio main limpio en 5dda9860d4dcb322c839c8cc1ae5f617f6a21387, alineado con referencia
origin/main disponible. Se conserva ese commit, la entrega 5 y todos sus resultados.
Sin fetch/push, credenciales, globales, nuevas dependencias, núcleo ni JSON v5.
Único cambio nuevo: comparacion-resultados. Barridos/importación no especificados.

Implementación: comparison.py interpreta entradas mediante validated_model y
compara campos explícitos, sin igualdad literal de archivos. La vista usa solo
load_result para seleccionar A/B. Nombres, rutas, origen y dirty no se tratan como
condiciones; m/U/F derivados pueden variar. Se canonizan funciones/filas de
lumbreras y se separan descripciones. Tabla desde resumen; curvas desde muestras
del último ciclo, fase documentada y P-V temporal. No se usa el proyecto activo.
Exportación con csv.writer a carpeta exclusiva, valores sin redondear y limpieza
de archivos propios ante error; no declara éxito parcial ni sobrescribe destinos.

### Pruebas automatizadas del tramo

`.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_comparison.py -q`:
**10/10 aprobadas en 2,066 s**, estado final. Fixtures declarados para aritmética/Qt,
no evidencia física; resultados reales existentes para lector y compatibilidad.
Esperados definidos independientemente de compare_results. Comprueban A/A=0,
inversión absoluta y porcentaje respecto a nueva base, A=0 sin denominador artificial,
Y absoluto, resumen distinto de máximos dibujados, compresión, nombres/números
equivalentes/reordenamiento por función, múltiples cambios de ficha/cárter/falda/
lumbrera/tramo, cada condición/metadato ausente, estados no convergidos/balances,
fase por ciclos distintos/P-V temporal, CSV/unidades/identidades/escape, rechazo
de destino existente/fallo de segunda escritura y conservación de datos/fuentes.
Qt comprueba selección ilegible sin reemplazo, incompatibilidad que retira datos
cuantitativos y exportación sin iniciar QProcess ni cambiar proyecto/dirty.
No se ejecutó la suite histórica que inicia ensayos; no hubo simulaciones nuevas.

Una revisión independiente puntual de solo lectura no encontró defectos
reproducibles; ejecutó solo estos 10 tests (1,443 s). Autorrevisión del principal
de diff, exportaciones y capturas. OpenSpec estricto aprobado, sin init/update
ni integración automática. No otra revisión general.

### Resultados existentes utilizados, no ejecuciones nuevas

A/base: `results/simulacion-2t/editor-20260915/A/manifest.json`, compresión 8:1,
run_id `a7f98f7af82d471ebffe53066c24dae8`, último ciclo 10.
B/modificada: `results/simulacion-2t/editor-20260915/B/manifest.json`, compresión 8,2:1,
run_id `85ff236a668f4fd39dcc8c56944641d1`, último ciclo 9.
Ambos perfil **B**, banda 100 Pa y 3000 rpm; convergidos/balances validados.
Única diferencia geométrica detectada: compresión. Sin diferencias descriptivas.
La ejecución histórica C (perfil C) se leyó únicamente para probar incompatibilidad
de perfil, no se usó como geometría B ni se volvió a calcular.

| Magnitud | A | B | B−A | Relativa % |
| --- | ---: | ---: | ---: | ---: |
| W_C J/ciclo | 16,49050751206088 | 16,63155294204956 | 0,14104542998867942 | 0,8553128512601639 |
| W_K J/ciclo | -3,3651306484080394 | -3,3652474266840153 | -0,00011677827597589285 | -0,0034702449377749358 |
| pmax Pa abs. | 1331530,846070603 | 1366927,2751548453 | 35396,42908424232 | 2,6583258802226397 |
| Y_I | 0,9855942761818735 | 0,9858254226456079 | 0,00023114646373445513 | No aplicable |
| Y_K | 0,9771350157648919 | 0,9775046102019959 | 0,00036959443710393725 | No aplicable |
| Y_C | 0,5621858698264297 | 0,5627356966320124 | 0,0005498268055826872 | No aplicable |
| Y_E | 0,38108950299160227 | 0,3819618593595342 | 0,0008723563679319257 | No aplicable |

A comienza su última vuelta en 3420°, B en 3060°: se restan 3240°/2880°
respectivamente, ambos 180–540°, sin mover picos. 721 muestras originales por
ejecución, con volumen temporal sin ordenar. Valores no interpretados como
mejora de motor ni potencia al eje; limitación 0D/energía prescrita conservada.

### Windows visible, captura y exportación

```powershell
.\.venv\Scripts\python.exe tests/verify_comparison_windows.py --output results/simulacion-2t/comparacion-20260915
.\.venv\Scripts\python.exe tests/verify_comparison_windows.py --output results/simulacion-2t/comparacion-20260915 --no-export --suffix=-final
```

Escritorio Default accesible. Automatización de ventanas reales al 150 % efectivo
(DPR 1,5, base 125 % y factor Qt 1,2 solo del proceso), sin aceptación manual.
Botón desde Simulación 2T, selección de A/B vía diálogo, compatibilidad, CSV,
navegación de pestañas, foco Tab y ancho compacto comprobados. Guardas sobre
QProcess.start confirmaron cero procesos de cálculo. Hashes de JSON fuente A/B/C
iguales antes/después, proyecto abierto y dirty conservados.

CSV verificados en `results/simulacion-2t/comparacion-20260915/resumen.csv`
(7 filas de magnitudes) y `curvas.csv` (1442 muestras). Se recuperaron con
csv.DictReader para comprobar valores numéricos completos, unidades, run_id,
fase y orden del volumen contra los resultados guardados. Solo archivos locales
de evidencia, ignorados por Git; no datos personales ni sobrescrituras.

Inspección visual: se corrigió la necesidad de desplazar internamente la tabla
para leer Y_E; resumen/entradas separados en pestañas y tabla ajustada a sus siete
filas. En compacto se alineó arriba para evitar un hueco causado por la altura
de gráficos apilados. Nuevas capturas reabriendo resultados, sin exportar de nuevo
ni calcular. Pruebas afectadas repetidas tras esos ajustes; no campañas físicas.
Capturas preliminares conservadas en `results/simulacion-2t/capturas-comparacion-previas/`.

Capturas reales finales en `docs/images/`, inspeccionadas:
- `motorsim-comparacion-resumen-150-final.png`: A/B, procedencia, condiciones y siete magnitudes.
- `motorsim-comparacion-entradas-150-final.png`: única diferencia de compresión y separación descriptiva.
- `motorsim-comparacion-curvas-150-final.png` y `motorsim-comparacion-curvas-inferior-150-final.png`: superposición, ejes comunes, leyendas, unidades y aviso.
- `motorsim-comparacion-compacta-150-final.png`: disposición vertical y foco visible.

Entrega 6 **En curso: comparación y CSV implementados**. Barridos e importación
de mediciones pendientes y no autorizados en este tramo. No quedan comprobaciones
técnicas pendientes del tramo; aceptación manual no atribuida. Entrega 5 intacta.
Commit propio y publicación a cargo de la usuaria; sin archivar ni iniciar entrega 7.


## Tramo RPM autorizado después de b9fbee4d
Las exclusiones de barrido anteriores describen el primer tramo; esta nueva orden
lo autoriza dentro del mismo cambio. Historia y aceptaciones anteriores intactas.
- [x] 8. Comprobar continuidad y documentar RPM/barrido/contratos acotados.
- [x] 9. Parametrizar punto, secuencia independiente e índice validado sin cambiar física/JSON v5.
- [x] 10. Integrar lista/progreso/cancelación/reapertura/tabla/puntos/CSV y procedencia.
- [x] 11. Pruebas focalizadas y revisión puntual del estado final.
- [x] 12. Barrido GUI B autorizado y contraste C condicional, máximo cinco cálculos/300 s.
- [x] 13. Windows 150 %, captura real, registrar evidencia y commit propio sin publicar.
Aceptación manual del tramo no atribuida. Entrega 6 En curso, importación pendiente.


### Evidencia del tramo RPM — 15/09/2026

Inicio main limpio en **b9fbee4dde043da4389115e2f892e1286cbfccad**, referencia local
origin/main alineada. Sin sustituir trabajo, fetch/push, credenciales, configuración
global, dependencias ni integración automática. Se amplía el mismo cambio.

Implementación: punto 2500–3500; lista exacta 2–5; proceso único secuencial con
copia independiente y receta inicial nueva por punto; índice por avance/parada.
El escenario se reconstruye, las RPM llegan a Model.rate, dV/dt, energía/marcador,
dt y muestras. El único dato temporal que estaba fijo en muestras fue parametrizado;
no se cambiaron leyes, tolerancias, dominio, perfiles, bandas ni JSON v5.
Lector v3, lectores históricos v1/v2, integridad de serie, tabla/puntos/consulta,
CSV y protección A/B de iguales condiciones comprobados. Referencia preservada.

#### Pruebas automatizadas y revisión

Suite `python -m unittest discover -s tests -q`: **172/172**, 16,950 s.
Después del ajuste de cierre, selección focalizada de `test_sweep`,
`test_comparison`, `test_reference_results`, `test_project_simulation` y
`test_simulation_view`: **52/52**, 12,497 s. Incluye **17 controles nuevos** de RPM,
plan exacto, tipos/rangos, propagación analítica, p/T/Y inicial independiente,
v3/tiempo–ángulo, históricos, A/B igual/distinto RPM, copia única, interrupción
intermedia, cancelación antes/durante/entre, ausencia de reintentos, rutas/series
ajenas/hashes/identidad, CSV con vacíos, reapertura/dirty, proceso único, reloj
por punto, destino existente/carrera y cierre protegido sin abrir otro diálogo.
Dobles identificados para secuencia/fallos/cancelación y diagnósticos de estado
inicial, nunca soluciones físicas aceptadas fabricadas. Se conservaron regresiones
existentes de arranque/cancelación breve de procesos; no cálculos completos extras.

Una revisión independiente puntual de solo lectura ejecutó 14+10 tests entonces
existentes y detectó dos defectos: posible apropiación del índice de una carpeta
existente tras fallo de arranque y falta de tiempos persistidos del punto individual.
Corregidos mediante preflight de destino, identidad confirmada por el proceso,
tiempos v3 y pruebas de regresión. No segunda revisión general. Autorrevisión del
principal de correcciones/diff, lectura real/CSV y capturas. OpenSpec estricto
aprobado, sin init/update ni archivo de cambios.

#### Cinco ejecuciones reales autorizadas, sin repetición

`python tests/verify_sweep_windows.py --output results/simulacion-2t/barrido-20260915`.
GUI B2500/B3000/B3500, copia de proyecto **PRUEBA SINTÉTICA — barrido 8:1 sin guardar**,
geometría exacta de referencia. Se editó después a 8,2 en el editor: todos los
puntos conservaron 8:1 y dirty de la copia, con aviso de configuración anterior.
No hubo segundo proceso por doble inicio. Los tres B convergieron con controles,
y B3000 reprodujo **exactamente ciclos, muestras y RHS** de referencia. Solo entonces
se ejecutaron C2500/C3500 desde receta original, perfil C/100 Pa por consola.
No otras RPM/bandas ni estudios; todos los puntos terminaron por tres ciclos
consecutivos de convergencia y balances aprobados.

| Punto | Ciclos | Integración s | Pico proceso MiB | RHS | W_C J/ciclo | W_K J/ciclo | pmax Pa abs. | Peor balance independiente % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B2500 | 10 | 10.218 | 24.902 | 230188 | 16.209291803 | -3.130805795 | 1306559.767536 | 0.000664958 |
| B3000 | 10 | 10.531 | 37.898 | 228171 | 16.490507512 | -3.365130648 | 1331530.846071 | 0.000445966 |
| B3500 | 9 | 9.156 | 43.820 | 205521 | 16.417492892 | -3.404531689 | 1347664.437989 | 0.000364325 |
| C2500 | 10 | 20.172 | 24.758 | 444499 | 16.209260861 | -3.130806445 | 1306558.969862 | 0.000149986 |
| C3500 | 9 | 18.250 | 24.730 | 398857 | 16.417489833 | -3.404531709 | 1347669.132164 | 0.000109784 |

Pico de proceso B incluye el máximo acumulado del único hijo secuencial, no memoria
independiente aislada de cada punto. Integración total **68,327 s**, cinco ejecuciones
(<300 s). Protocolo hasta registrar contrastes **73,235 s**. Serie B: integración
**29,905 s**, proceso/validaciones/índice **31,156 s**, percibido GUI **32,125 s**.
No se ocultaron arranque ni escritura dentro del tiempo de integración.

| Punto | Preparación s | Escritura de datos s | Total del punto hasta registro s |
| --- | ---: | ---: | ---: |
| B2500 | 0.016 | 0.188 | 10.516 |
| B3000 | 0.016 | 0.156 | 10.703 |
| B3500 | 0.016 | 0.172 | 9.344 |
| C2500 | 0.016 | 0.172 | 20.547 |
| C3500 | 0.016 | 0.171 | 18.531 |

El total de serie/interfaz también incluye cierre de metadatos/validaciones; los
instantes medidos por punto se definen en design.md. Consola conserva sus tiempos
en manifiesto v3 y en C-2500.log/C-3500.log. UI conserva total percibido en índice.

#### Contrastes B/C extremos

Sensibilidad usa sus umbrales existentes: trabajo/pmax/curva/masas por enlace ≤1 %
relativo; cada Y ≤0,005 absoluto. Se consultó `tolerances_passed` de la comparación
B/C (sin usar el gate A/B de geometrías ni afirmar tendencia de tres perfiles).
Las diferencias siguientes son fracciones relativas, **no porcentajes**, salvo Y
que es diferencia absoluta. Ambos extremos aprobados.

| RPM | ΔW_C relativa | Δpmax relativa | Δcurva relativa | Máx ΔY absoluta | Máx Δmasa enlace relativa |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2500 | 1.90890447e-06 | 6.10515311e-07 | 6.9912548e-07 | 1.0675316e-06 | 4.26974359e-07 |
| 3500 | 1.86311393e-07 | 3.48318053e-06 | 6.26950758e-08 | 5.0475628e-07 | 1.32192449e-07 |

2500 rpm, ΔY I/K/C/E: 7.59824577e-07, 1.0675316e-06, 9.46644797e-07, 7.01468326e-07.
Δmasas relativas exterior-I/I-K/K-C1/K-C2/C-E/E-exterior: 2.18932853e-07, 2.07252451e-07, 4.01039335e-07, 4.01039335e-07, 4.26974359e-07, 3.82217306e-07.

3500 rpm, ΔY I/K/C/E: 2.76500931e-07, 5.0475628e-07, 4.60770586e-07, 3.84830541e-07.
Δmasas relativas exterior-I/I-K/K-C1/K-C2/C-E/E-exterior: 7.82214412e-08, 7.31080404e-08, 2.58636617e-08, 2.58636617e-08, 3.68729798e-08, 1.32192449e-07.

Evidencia original del protocolo en `results/simulacion-2t/barrido-20260915/protocol.json`;
`gui-sweep/series.json`, sus tres directorios point-NN, C-2500/C-3500 e inputs/logs.
No se alteraron evidencias históricas. No calibración experimental ni comprobación
de precisión/convergencia de todo el intervalo o dominio geométrico.

#### Windows e inspección visual, separadas de aceptación manual

Escritorio Default desbloqueado, Qt Windows, DPR **1,5** efectivo (125 % del equipo
× QT_SCALE_FACTOR=1.2 solo del proceso). Barrido iniciado con botón real, navegación,
resultado persistido, reapertura sin proceso/proyecto original, consulta de las
721 muestras de punto convergido, CSV, foco Tab y ancho compacto comprobados por
automatización visible. CSV real: tres filas; valores numéricos completos, RPM,
tiempos, estados y run_id/series_id coinciden exactamente con los resultados leídos.

Inspección inicial encontró exceso de altura del diálogo y contraste insuficiente
en selección. Se separaron gráficos por pestañas y corrigió la selección. Capturas
finales reabriendo resultados, **sin nuevas integraciones ni exportaciones**:
`python tests/verify_sweep_windows.py --output results/simulacion-2t/barrido-20260915 --reopen --suffix=-final`.
Capturas reales inspeccionadas en `docs/images/`:
- `motorsim-barrido-resumen-150-final.png`.
- `motorsim-barrido-trabajo-150-final.png`.
- `motorsim-barrido-presion-150-final.png`.
- `motorsim-barrido-compacto-150-final.png`.
Primeras capturas conservadas fuera del commit en `results/simulacion-2t/barrido-20260915/capturas-previas/`.

**Tramo implementado y comprobado; aceptación manual de la usuaria no atribuida.**
Entrega 6 **En curso**: comparación, CSV y barrido acotado implementados; importación
de mediciones pendiente y no iniciada. Entrega 5 conserva su aceptación manual
pendiente separada. Commit propio sin push; publicación a cargo de la usuaria.
Sin archivar ni iniciar entrega 7/configuración 4T.


## Tramo datos externos — autorizado 16/09/2026
- [x] 14. Comprobar continuidad a72b47f4 y documentar importación en el mismo cambio.
- [x] 15. Parser/definiciones/procedencia y copia persistente validada, sin simulaciones.
- [x] 16. Vista previa/confirmación, contraste exacto, tabla/puntos/CSV sin alterar fuentes.
- [x] 17. Pruebas pertinentes y una revisión puntual; corregir defectos concretos.
- [x] 18. Windows 150 % con barrido existente/CSV sintético, capturas y evidencia.
- [x] 19. README/hoja/tareas actualizados y commit propio sin publicar.
Mediciones reales y validación experimental pendientes; no inferirlas de fixtures.


### Evidencia del tramo externo — 16/09/2026

Git main limpio al iniciar, HEAD **a72b47f43bce2665eb95e4d8b4277543d4d0a6d2**,
remoto origin existente conservado. Sin sincronizar/remplazar trabajo ni push,
credenciales, globales o dependencias. Se amplía comparacion-resultados, sin otro
roadmap/cambio/informe. Núcleo/criterios/referencia/resultados históricos y JSON v5
intactos; **cero simulaciones nuevas**.

#### Implementación y archivos de prueba

external_data.py valida CSV/definición/procedencia, usa Decimal para RPM exactas,
convierte bar sin perder originales y persiste copia literal/metadatos en carpeta
exclusiva con correspondencia por hash y revalidación. Metadatos desconocidos se
muestran No informado, procedencia inicial No determinada. external_view.py exige
declaración/definición/vista previa/confirmación, conserva selección ante errores y
cancelaciones; consulta independiente del editor con load_sweep, tabla y puntos
sin interpolación ni líneas, detalles legibles separados y CSV exclusivo mediante
utilidad existente. Identifica contraste descriptivo, no equivalencia acreditada,
no validación/calibración. Comparación A/B conserva sus protecciones.

Archivos versionados, todos **EJEMPLO SINTÉTICO**, no mediciones:
- `examples/EJEMPLO_SINTETICO_trabajo.csv`: 2500/3000/3500 y 10/20/−2 J/ciclo.
- `examples/EJEMPLO_SINTETICO_presion_bar.csv`: incluye 13.5 bar y RPM fuera de rango.
- `examples/EJEMPLO_SINTETICO_contraste.csv`: cinco filas desordenadas, 2000/2500/3000/
  3500/4000 con 5/10/20/−2/25 J/ciclo para consulta visible. Valores de prueba
  independientes definidos manualmente, **no derivados del barrido ni medidos**.

#### Pruebas automatizadas

Estado final: **50/50 aprobadas en 6,477 s**, selección `test_external_data` (17),
`test_comparison` (10), `test_sweep` (17) y `test_reference_results` (6). Ejecución
mediante unittest.TestSuite/loadTestsFromName con tests en sys.path y guardas
sobre adaptive.run_adaptive, reference_run.run_adaptive y simulation.run_resolution
que lanzan AssertionError si se intenta integrar. Los dobles controlados del test
de registro sustituyen al runner; no se ejecutó el motor ni la suite general con
procesos de cálculo. Qt sin pantalla separado de inspección Windows.

Pruebas nuevas: UTF-8/BOM, columnas/encabezados, falta de filas, fila/columna en
vacíos/NaN/inf/expresiones/miles/desbordamientos, signo/cero del trabajo y positividad
de presión, 13.5 bar = **1350000 Pa**, definición/unidades desconocidas/manométrica/
trabajo parcial, RPM desordenadas/fuera del rango/duplicadas/equivalentes y distinción
decimal más fina que float. Aritmética independiente 10/20/−2 frente a fixtures
11/18/−1: diferencias **1/−2/1**, relativas **10/−10/50 %**. Son fixtures en memoria,
no convergencia física fabricada. Base cero sin relativa, ausencias/fallos sin
ceros, ausencia de interpolación. Metadatos/procedencia desconocidos, copia exacta,
reapertura sin fuente, rechazo de hash/ruta/reglas/identidad/unidad alterados,
escritura fallida/destino existente, CSV fiel con procedencia y vacíos, cancelación,
vista previa invalidada al editar, conjunto anterior preservado y proyecto/dirty
intactos. Guardas QProcess.start en pruebas de interfaz y recorrido visible.

La primera selección final detectó un supuesto frágil en un test **existente**:
una escritura diminuta puede registrar 0 s por resolución del reloj Windows.
`test_sweep.test_individual_records_separate_times_with_controlled_runner` ahora
inyecta reloj controlado para probar separación de tiempos, sin tocar aplicación,
requisitos ni evidencia histórica. Selección pertinente repetida y aprobada.

Una revisión independiente puntual de solo lectura no encontró defectos
reproducibles; ejecutó 17+10 pruebas, sin motor ni atribuir comprobación visual.
Autorrevisión del principal de diff, exportación y capturas. No otra campaña de
revisión. OpenSpec estricto aprobado; sin init/update ni archivo.

#### Windows al 150 % y contraste sintético descriptivo

El escritorio actual tiene escala base 100 % (dos monitores). El primer intento
con el factor anterior 1,2 se detuvo en la comprobación de DPR antes de importar;
no se acreditó 150 % por ese intento. Factor Qt **1,5 solo del proceso**, DPR 1,5
comprobado, escritorio Default accesible, sin cambiar Windows ni esperar desbloqueo.

Comandos efectivamente ejecutados desde raíz:
```powershell
.\.venv\Scripts\python.exe tests/verify_external_windows.py --output results/simulacion-2t/externos-20260916-150
.\.venv\Scripts\python.exe tests/verify_external_windows.py --output results/simulacion-2t/externos-20260916-150 --reopen --suffix=-final
```

Automatización **con ventanas visibles**, no aceptación manual. Selección del CSV
por botón, declaración Ejemplo sintético/definición completa, vista previa, confirmar
y guardar copia, seleccionar barrido real existente, consultar tabla/gráfico,
exportar, reabrir copia confirmada, navegar pestañas y foco Tab/ancho compacto.
Se inspeccionaron capturas y se sustituyó el volcado técnico por texto legible de
procedencia, configuración y condiciones (solo visual); recaptura por reapertura,
sin nueva importación/exportación ni cálculo.

Serie reutilizada: **98302bb90b6d457cb614e7e8392465e2**, en
`results/simulacion-2t/barrido-20260915/gui-sweep/series.json`.
Importación confirmada: **7d792c0be0f049b5a41cbdd599157abd**, nombre
**EJEMPLO SINTÉTICO — control de importación**, procedencia Ejemplo sintético,
fuente «Valores de prueba definidos independientemente; no derivados del barrido
ni medidos». Motor/configuración/condiciones No informado.
Cinco puntos externos, tres coincidencias exactas convergidas, dos sin pareja.

| RPM | Externo sintético J/ciclo | Simulado guardado J/ciclo | Simulado − externo J/ciclo | Relativa % | Estado |
| --- | ---: | ---: | ---: | ---: | --- |
| 2000 | 5 | — | — | — | Solo externo |
| 2500 | 10 | 16.209291803030894 | 6.209291803030894 | 62.09291803030894 | Coincidente |
| 3000 | 20 | 16.49050751206088 | -3.50949248793912 | -17.5474624396956 | Coincidente |
| 3500 | -2 | 16.41749289193312 | 18.41749289193312 | 920.874644596656 | Coincidente |
| 4000 | 25 | — | — | — | Solo externo |

Estos números verifican importación/aritmética/consulta, **no error experimental**
ni validez de la física. No se buscaron coincidencias favorables ni ajustaron parámetros.
CSV real exportado cotejado valor por valor con Decimal; conserva unidades,
procedencia/ids y vacíos. Hashes del CSV fuente y todos los JSON del barrido iguales
antes/después. Proyecto propio con dirty intacto. Guarda QProcess.start confirmó
cero procesos de cálculo. Evidencia local ignorada en Git:
`results/simulacion-2t/externos-20260916-150/importacion/{original.csv,metadata.json}`,
`exportacion/contraste.csv` y `recorrido.json`.

Capturas reales inspeccionadas/versionadas en docs/images:
- `motorsim-datos-externos-vista-previa-150.png`.
- `motorsim-datos-externos-tabla-150-final.png`.
- `motorsim-datos-externos-puntos-150-final.png`.
- `motorsim-datos-externos-procedencia-150-final.png`.
- `motorsim-datos-externos-compacto-150-final.png`.
Capturas previas conservadas en la carpeta local de evidencia `capturas-previas/`.

**Importación y contraste descriptivo implementados y comprobados con archivos de
prueba. Contraste con mediciones reales pendiente mientras no haya datos adecuados.
Validación experimental del modelo no realizada.** Aceptación manual no atribuida.
Entrega 6 En curso; criterios originales de hoja de ruta conservados. Commit propio
sin publicar; publicación a cargo de la usuaria. Sin archivar ni iniciar entrega 7.
