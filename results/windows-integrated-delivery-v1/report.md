# Dino Desktop Windows 0.1.0-rc7 — aceptación funcional TRIAL

## Abrir la aplicación

Ejecutable ya extraído:

`E:\Dino-Desktop-TRIAL-rc7-final\MotorSim\Dino2T.exe`

No requiere instalador ni Python. Conservar la carpeta completa con `_internal` y `Ejemplos`.

1. Abrir Dino2T.exe.
2. Archivo → Abrir: `Ejemplos/Curvas-periodicas-125cc.dino.json`.
3. Entrar a **Análisis**. En el historial elegir **Todas las variantes**.
4. Seleccionar las seis filas con Ctrl+A y pulsar **Ver selección**. Si el historial está oculto, usar **Mostrar corridas**. Se puede ocultar después para ampliar los gráficos.
5. Para una comparación puntual seleccionar dos corridas A/B de igual RPM y pulsar **Comparar 2 corridas**. Las curvas ofrecen exportación CSV con estados y hashes.
6. Para calcular: elegir variante arriba, **Preparar**, fijar RPM, horizonte, tiempo y memoria; confirmar **Iniciar corrida**. Cancelar conserva el último ciclo completo. Seleccionar esa corrida en el historial y usar **Reanudar checkpoint**; requiere la misma identidad completa y la misma distribución.

La raíz de resultados nuevos es externa al repositorio; por defecto se utiliza AppData/Local/MotorSim/Artifacts. El ejemplo incluye datos de sólo lectura con referencias relativas al proyecto. No mover únicamente el JSON sin su carpeta Datos.

## Distribución

ZIP: `E:\Dino-artifacts\Windows\MotorSim-0.1.0-rc7-windows-x64-da501c72-trial-20261023T152150Z.zip`

Tamaño: 289.244.901 bytes. SHA-256:

`6caddc2eccea470aa8ae5588407661aebbae3d8aeaf5927e70671f29151be655`

Fuente del paquete: commit `da501c72` (SHA completo en receipt.json/build.json). Los commits posteriores de cierre documentan la aceptación; no cambian el código del EXE. El árbol contenía cambios locales ajenos y la distribución conserva la clasificación TRIAL. Se incluyen dependencias, fuentes correspondientes, manifiesto de construcción, avisos e instrucciones INICIO-DINO.txt. No hubo push.

## Integración comprobada

La ruta existente de Desktop es `ExecutionPage → run_exploratory → engineering_workflow → engineering_point → IntegratedEngine2T` para las configuraciones de intercambio acoplado. Se conserva el coordinador de curvas existente y su importador de resultados, sin otro motor ni otra interfaz.

Los 29 módulos de workflow del build se contrastaron contra los archivos incluidos. El integrador es byte por byte el optimizado en la entrega de rendimiento; admisión, transferencias, transporte de especies, barrido acoplado, combustión, trabajo y pérdidas conservan su implementación física. La corrección de esta entrega afecta rutas, dependencias, identidad de distribución y selección de reanudación.

Problemas corregidos:

- Faltaba psutil en el entorno de construcción; quedó fijado en 7.0.0.
- Los imports congelados necesitan fuentes coherentes con `__file__`/inspect y el productor de checkpoints. Se empaqueta motorsim como fuentes ejecutadas por el runtime distribuido.
- El runner consultaba Git al ejecutar. El EXE utiliza el commit del manifiesto de construcción y falla ante una identidad inválida; el código fuente conserva la consulta Git.
- Los ejemplos tenían referencias absolutas de la máquina original. Las referencias explícitas `./` se resuelven respecto del proyecto. Los demás caminos relativos históricos conservan su semántica.
- La prueba real encontró un defecto en Reanudar desde historial: se comparaba identidad de proyecto con identidad efectiva. Ahora se compara la identidad resuelta completa para la RPM seleccionada, incluidos fuentes y build. No se permiten hashes incompatibles.
- El texto de modo aclara que la auditoría depende del modo; ENGINEERING no afirma auditoría independiente. Se actualizó una aserción histórica de test que exigía mayúscula en «Ciclo», conservando el requisito de mostrar el número de ciclo.

## Prueba del EXE real

El ZIP fue verificado por CRC y extraído en una carpeta nueva fuera del repositorio. Se ejecutó Dino2T.exe con C:/Windows/Temp como directorio de trabajo, PYTHONPATH vacío y PATH limitado a directorios del sistema Windows. No se lanzó Python externo ni se ejecutó código fuente para sustituir las acciones de la interfaz. La automatización externa de QA sólo suministró entrada de Windows y comprobó artifacts.

Desde el EXE se abrió el proyecto, se localizaron los seis puntos periódicos A/B a 8000/9000/10000 RPM, se compararon A/B a 9000 RPM y se visualizaron presión, potencia y torque. El CSV exportado contiene las seis filas, sus estados periódicos y provenance. Se verificaron 1.322 archivos históricos copiados, todos idénticos a los originales. No se recalculó ninguna curva histórica.

Se ejecutó A a 9000 RPM, tres ciclos, límite 180 s, memoria 512 MiB, un worker. Después se realizó una segunda ejecución breve: cancelación tras el primer ciclo completo y reanudación desde el botón del historial. Se conservaron el checkpoint y la primera invocación; sólo se calcularon los ciclos 2 y 3 en la segunda. El checkpoint final completo, ledgers e historia del detector coinciden exactamente con la ejecución ininterrumpida. El resultado reanudado se abrió desde el historial y apareció como transitorio, sin prestaciones definitivas. Inicio y cierre normales comprobados.

## Rendimiento medido

| Misma configuración, 3 ciclos a 9000 RPM | EXE final | Fuentes |
|---|---:|---:|
| Invocación del runner, incluidos diagnósticos/checkpoints | 13,491 s | 13,382 s |
| Pasos del integrador | 11,373 s | 11,274 s |
| Procesamiento posterior | 1,019 s | 1,002 s |
| Pico RSS del proceso | 279,5 MiB | 103,2 MiB |

Diferencia de pared observada: +0,81% en el EXE, en una sola pareja; no es un estudio estadístico de overhead. La memoria del EXE incluye Qt y el historial ya cargado. El campo CPU del runner existente es CPU acumulada del proceso y no se usa como CPU de esta invocación, porque el EXE ya había realizado trabajo de interfaz.

Los snapshots completos y las muestras/diagnósticos físicos de los tres ciclos coinciden exactamente con fuentes: diferencia numérica cero, misma historia de periodicidad. Sólo se excluyeron tiempos/RSS de los diagnósticos comparados y se mantuvieron separadas las identidades de productor/build. La reanudación consumió 9,182 s adicionales; la ejecución cancelada y reanudada acumuló 13,915 s del runner. Todos los intentos breves, incluidos los paquetes previos y la referencia fuente, acumularon 59,061 s del runner, dentro del presupuesto diagnóstico de 600 s. No se presenta este total como tiempo de interacción/QA o construcción.

La optimización térmica está incorporada. No se repitió una curva completa ni se presenta la proyección de 49 minutos como una medición nueva.

## Verificaciones y límites

- Desktop/integración: 83 PASS.
- Regresión P4–P8: 298 PASS, 3 SKIP; cuatro avisos NumPy preexistentes.
- OpenSpec `--all --strict`: 67 PASS.
- Integridad ZIP, 29 fuentes de workflow, copia histórica, checkpoint/reanudación y equivalencia fuente/EXE: PASS.
- Conservación interna idéntica a fuentes; no se agregó una auditoría general.
- Program-status: gate funcional de entrega cerrado; detalle en receipt.json y cola.

Las capturas de esta carpeta son del EXE final. Los logs completos, intentos anteriores y artifacts nuevos quedan fuera de Git en el directorio `windows-integrated-delivery-v1` del artifact store.

La aceptación es de producto TRIAL. Los puntos de tres ciclos son no convergidos y se distinguen de los seis periódicos históricos. No se afirma validación experimental, independencia espacial ni precisión predictiva. X30 permanece congelado esperando geometría externa; su documentación y correo no enviado permanecen intactos. Los checkpoints de otra identidad siguen rechazándose; no se migraron históricos. La interfaz conserva sus paneles con desplazamiento y los controles existentes; no hubo rediseño ni nuevas funcionalidades.
