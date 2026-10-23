# Rendimiento integrado: resultado medido

## Decisión técnica

Adoptar la evaluación térmica por etapa del integrador. Eliminar el recorrido completo redundante de superficies reduce el costo del punto sin cambiar el flujo numérico. No continuar microoptimizaciones en esta entrega. X30 permanece congelado por falta del volumen libre de precompresión; el correo no fue enviado.

## Perfil real y causa

Se perfiló un ciclo completo de A a 9000 RPM: 721 pasos aceptados, 27,524 s instrumentados. El árbol de `ThermalSystem.heat_rate_w` consumió 11,254 s acumulados (40,9%). Había 35 superficies: cada llamada revalidaba el conjunto de 35 antes de evaluar una sola superficie. El trabajo de validación era cuadrático en el número de superficies por etapa SSPRK.

La nueva ruta valida el conjunto una vez por etapa y conserva las validaciones de temperatura del gas y pared, el orden de operaciones flotantes y las leyes térmicas originales. No hay caché entre etapas. Las subclases de ThermalSystem conservan su entrada original para respetar sobreescrituras. El código está dentro del módulo integrado, cubierto por sus bindings existentes; no se agregó una dependencia sin hash.

Las llamadas a validación del sistema bajaron de 50.474 a 1.446 en el perfil de un ciclo; las validaciones individuales, de 1.817.165 a 101.185. El tiempo exclusivo de thermal.py bajó de 9,148 a 0,560 s. El perfil completo final duró 16,843 s; estos tiempos instrumentados sirven para atribución, **no** para calcular speedup.

Otros costos exclusivos del perfil inicial: integrador 3,465 s; EOS 2,513 s; especies 2,129 s; Riemann 1,235 s; open-end plenum 0,213 s. Los árboles de HLLC (2,735 s), flujo de especies (2,433 s) e interfaz 0D/1D (0,486 s) se solapan con otros costos y no deben sumarse a los exclusivos. La fuente de combustión costó 0,008 s acumulados. El barrido físico de este modelo se expresa a través del transporte y mezcla de especies y los flujos de puertos; no se introdujo otro modelo ni una campaña para estudiarlo. El detalle completo de funciones queda en los perfiles externos y la síntesis en measurements.json.

## Comparación sin profiler

Mismas configuraciones funcionales existentes A/B a 9000 RPM, tres ciclos desde el mismo estado inicial, tres repeticiones por variante y versión. Una ejecución secuencial, 512 MiB, límite de 180 s por invocación. Misma geometría, CFL, grilla angular, combustible, fricción explícita, conservación y detector V2. Se alternaron baseline/prototipo en la primera matriz; las seis mediciones de la implementación definitiva se ejecutaron después, sin tests ni benchmarks simultáneos. Esta limitación de orden y carga del equipo forma parte del alcance.

| Variante | Anterior, mediana | Optimizada, mediana | Speedup | Reducción |
|---|---:|---:|---:|---:|
| A | 20,151 s | 13,922 s | 1,447× | 30,91% |
| B | 19,943 s | 13,710 s | 1,455× | 31,25% |

Rangos A: 20,135–20,243 s antes; 13,604–13,954 s después. Rangos B: 19,757–19,965 s antes; 13,707–13,782 s después. El tiempo incluye construcción, cálculo, diagnósticos, detector y checkpoints del runner existente. Excluye arranque Python y escritura del registro auxiliar del benchmark; incluyendo ambos, el speedup del proceso completo es 1,443× para A y 1,444× para B.

Medianas descriptivas de las seis ejecuciones de cada versión (no suman exactamente porque son medianas independientes):

| Componente | Anterior | Optimizado |
|---|---:|---:|
| CPU del benchmark | 18,617 s | 12,289 s |
| Pasos del integrador | 17,678 s | 11,408 s |
| Captura del diccionario de trazas, incluida en pasos | 0,092 s | 0,091 s |
| Procesamiento posterior | 1,054 s | 1,105 s |
| Resto de la invocación | 1,188 s | 1,167 s |
| Pico RSS | 101,365 MiB | 101,410 MiB |

El almacenamiento no era el cuello principal: serialización y persistencia atómica consumieron 0,634 s acumulados en el perfil inicial y 0,568 s en el final, por ciclo instrumentado. Es una medición conjunta de JSON + escritura, no de latencia pura del disco. Se solapa con procesamiento/resto; no se suma como categoría independiente. No se cambió el writer.

## Equivalencia y conservación

Los 18 pares de ciclos contrastados tienen igualdad exacta de snapshots completos, ledgers, todas las muestras de presión/flujo/especies/áreas, diagnósticos físicos y evolución del detector. Sólo se excluyeron los campos de tiempo y RSS de los diagnósticos. Diferencia numérica máxima: cero. Misma secuencia de 721 pasos por ciclo y ningún rechazo en estos casos. No se modificaron los controles CFL ni las tolerancias.

Máximos residuos relativos finales A/B: masa 6,11e-16; especies 6,64e-16; energía 9,49e-16. Son los controles conservativos existentes; el benchmark exploratorio no ejecuta una auditoría independiente completa y no se presenta como tal. Los tests de integrador/replay existentes se registran por separado en receipt.json.

La reanudación desde el ciclo 3 produjo un checkpoint completo idéntico al ciclo 4 ininterrumpido, incluida la historia del detector y continuidad de combustión. Se rechazó antes de pasos físicos un checkpoint del productor anterior. No se manipuló ningún binding para aceptar históricos.

## Históricos y reproducibilidad

Baseline Git: fc4603f7faa785f70efba498164c87f16533d9b2. Se conservan un worktree detached, copia original y hashes bajo el artifact root externo, directorio `integrated-performance-v1-20261023`. Los cambios de finales de línea del checkout baseline se verificaron como exclusivamente textuales; los hashes brutos de cada ejecución se conservan y no se sustituyeron. Sólo cambió el contenido ejecutable de integrated_2t.py. Las configuraciones, módulos térmicos originales, contratos P4–P9, checkpoints y resultados históricos permanecen intactos.

La nueva identidad no permite continuar automáticamente checkpoints producidos por el integrador anterior. Esos resultados siguen disponibles con su productor histórico; esta entrega no migra ni recalcula las curvas. Las ejecuciones nuevas de la ruta integrada existente, incluida su utilización desde Desktop, usan la optimización. No se reconstruyó un EXE ni se afirma que un paquete histórico ya la contenga.

El script benchmark_integrated_performance_v1.py admite source-root, config y output explícitos para reproducir el contraste entre el worktree histórico y el repositorio actual. La selección del baseline no se utiliza para eludir controles en campañas científicas.

## Impacto práctico y alcance

Aplicar el factor observado de aproximadamente 1,45× a los 4.281,862 s históricos de seis puntos da **49,2 minutos**, frente a 71,4 minutos. Es una proyección condicionada a igual número de ciclos y comportamiento de costo, no una nueva curva medida. Los tres ciclos de benchmark son transitorios; no acreditan nueva periodicidad ni validación experimental, ni miden todos los regímenes/ciclos tardíos. Tampoco acreditan un speedup adicional por multiproceso.

La mejora es sustancial y elimina trabajo algorítmico redundante sin sacrificar precisión. Una curva completa todavía no es instantánea. Los costos restantes de EOS, transporte de especies y flujos son candidatos medidos para una futura optimización focalizada, pero esta entrega termina aquí y no abre una nueva investigación. La validación física X30 continúa pendiente de información externa.
