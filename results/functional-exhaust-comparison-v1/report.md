# Entrega 2 — comparación funcional de escapes

## Veredicto

**Comparación A/B funcional demostrada desde Dino Desktop; entrega PARTIAL por
curvas RPM bloqueadas por ausencia de periodicidad global.** No se inició grilla
RPM ni se amplió el horizonte. La aceptación funcional de entrega1 y su estado
científico REVIEW se conservan. No hay validación experimental ni predictiva.

## Qué puede hacer el usuario

Se abrió el proyecto de entrega1, se duplicó mediante los diálogos existentes,
se editó la tabla de escape y se guardó B. Se ejecutaron A y B desde el botón de
simulación existente. Se seleccionaron dos filas del historial, se compararon
presiones/caudal y resultados, se guardó la comparación en el proyecto y se
recuperó al reabrirlo, comprobando hashes. No se seleccionaron dos archivos en
un diálogo, ni se movieron artifacts entre directorios.

Proyecto reproducible: `configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json`.
En Desktop, seleccionar `A_original` o `B_header_plus20`; elegir la raíz externa
de esta demostración para consultar sus corridas. En Análisis, usar filtro
Todas las variantes o activa B + baseline A; seleccionar ambas filas y pulsar
Comparar. Guardar comparación vincula las referencias; Guardar proyecto las
persiste. Recuperar comparación vuelve a verificar los resultados. El proyecto
guardado con referencias locales está en el artifact root externo; el ejemplo
Git contiene geometrías y receta sin rutas personales.

## Cambio físico controlado

- A: tramo inicial de 83 mm. B: el mismo tramo de **103 mm**, diámetro 37.5 mm.
- Longitud total: 1079 → 1099 mm; aumento de recorrido geométrico de 20 mm.
- Justificación: cambiar el recorrido y fase de propagación/reflexión sin
  cambiar diámetros ni ángulos de los conos. No se seleccionó para producir
  una potencia objetivo ni implica sintonía óptima demostrada.
- Mismos admisión, transferencias, barrido, combustión, fricción, ambientes,
  condiciones iniciales primitivas y configuración numérica.
- 9000 RPM, CFL configurado 0.4, 44 celdas totales; 31 en el escape, repartidas
  3/5/6/2/2/6/7. La cantidad y partición se conservan; la longitud local de celda
  cambia con el tramo editado.
- Misma presión, temperatura y composición iniciales. El volumen añadido de B
  contiene más inventario inicial a esa misma densidad. No se transfirió un
  checkpoint A a B.
- Ambas parten del estado inicial, secuenciales, hasta 30 ciclos o 300 s y
  512 MiB por punto. Detector sin modificaciones; no se retomaron luego.

El editor anterior no podía guardar el escape real de entrega1: presupuso una
celda por tramo para un perfil de siete tramos con 31 celdas. Se agregó una
edición de longitud que reconoce los límites existentes y transforma cada
tramo afínmente, conservando áreas y primitivas y escalando volúmenes y especies
iniciales. No se modificaron el solver ni el adaptador histórico de refinamiento.
Esta ruta permite longitudes; cambios de diámetro en este perfil se rechazan
explícitamente. Los otros formatos conservan su editor anterior.

## Resultados reales del ciclo 30

| Magnitud | A original | B +20 mm | B − A |
|---|---:|---:|---:|
| Trabajo indicado (J/ciclo) | 34.06899 | 33.94339 | −0.12560 |
| Aire atrapado al cierre (mg) | 29.58237 | 29.49637 | −0.08600 |
| AFR atrapado | 7.60330 | 7.59959 | −0.00371 |
| Calor liberado (J/ciclo) | 73.45563 | 73.24409 | −0.21154 |
| Potencia al freno estimada (kW) | 3.34304 | 3.32464 | −0.01839 |
| Torque al freno estimado (N·m) | 3.54707 | 3.52755 | −0.01952 |
| Tiempo del runner (s) | 220.274 | 222.816 | — |
| Pico RSS del proceso Desktop/worker (MiB) | 227.715 | 228.660 | — |

**Todas las magnitudes de rendimiento anteriores son transitorias**, no puntos
definitivos de una curva. La fricción explícita de 85000 Pa es sintética; las
estimaciones al freno incluyen el trabajo del cárter, sin recortar negativos.
No constituyen medidas de banco. El AFR atrapado es rico y diferente del
suministrado 11.5; no se ajustó para mejorar la potencia.

Las ondas y el intercambio responden a la geometría. Comparando 720 ángulos
exactos comunes, sin interpolación, la presión de entrada del escape difiere
850.86 Pa RMS entre A y B; en el cilindro, 5482.58 Pa RMS. La variación de esas
trazas entre ciclos29 y30 es respectivamente 11.93/11.12 Pa RMS y
98.14/123.52 Pa RMS para A/B. La diferencia A/B supera esa deriva de un ciclo.
La amplitud de variación del trabajo en los últimos cinco ciclos es 0.01170 J
en A y 0.01760 J en B, menor que la separación de 0.12560 J entre variantes.

Esto distingue una respuesta geométrica **en este transitorio acotado**. No
prueba una pérdida o ganancia estacionaria: composición e inventarios todavía
evolucionan. No se demostró independencia espacial; las trazas corresponden a
la entrada de escape y al cilindro, no a un mapa espacial completo del conducto.

## Periodicidad y condición de punto utilizable

Ambos puntos terminaron `MAX_CYCLES_NONCONVERGED`, con ciclos1–30 completos.
Trabajo indicado por ciclo:

| Ciclo | A (J) | B (J) |
|---|---:|---:|
| 1 | −52.51403 | −53.20093 |
| 2 | 67.16563 | 69.55077 |
| 3 | 35.82714 | 33.25008 |
| 10 | 34.42148 | 34.35245 |
| 20 | 34.13962 | 34.03211 |
| 30 | 34.06899 | 33.94339 |

La última comparación terminal pasa los indicadores de cilindro, cárter,
admisión, transferencias y trabajo en ambas variantes. Eso no acredita una
órbita periódica completa del cilindro. Fallan 57 indicadores globales en A y
56 en B: 55/54 del escape y dos de inventario global de especies. En B el peor
indicador del escape vale 14.41 veces su umbral, y el inventario global 6.84.

El criterio utilizable se mantiene: observables admisibles, conservación,
checkpoint íntegro y todas las condiciones del detector existente cumplidas
durante tres comparaciones consecutivas, con mínimo diez ciclos. Los umbrales
incluyen 0.2% para masa/energía de cámaras, 0.5% para presión/temperatura y
trabajo con piso de 1 J, además de especies y todas las celdas del escape.
Pasar sólo el trabajo no permite excluir los demás indicadores.

**Decisión de curva: NO-GO.** El costo permitió completar el horizonte, pero no
se obtuvo un punto globalmente periódico. No se ejecutó la grilla pequeña ni
una campaña extensa. Las curvas definitivas conservan huecos; la tabla separa
las estimaciones transitorias. El bloqueo concreto es la evolución pendiente
del escape/composición, no un botón ni un fallo de ejecución. No se demostró
aquí que esa evolución sea un defecto de ecuaciones ni cuánto tardaría en cesar.

## Tiempo, integridad y pruebas

- Tiempo de ambos runners: **443.089 s**; recorrido completo de demostración
  Desktop: **501.0 s**, incluyendo edición, confirmaciones, carga y recuperación.
- Avance físico: 196.651/202.626 s; procesamiento diagnóstico: 13.879/12.133 s.
  Promedio de runner: 7.34/7.43 s por ciclo. Hubo tests de interfaz en otro
  proceso durante parte de la demostración; no es un benchmark aislado ni una
  proyección de rendimiento de una campaña.
- Rechazos CFL registrados: cero en ambas; CFL aceptado máximo 0.27823/0.27866.
- Residuos relativos internos máximos de masa/especies/energía inferiores a
  4.3e−15. Sin replay ni auditoría independiente en este modo exploratorio.
- Hashes de resultados, manifests, 60 archivos de muestras y checkpoints
  finales verificados. Dos restores nativos exactos, sin pasos: `next_cycle=31`
  y ángulo10800°; mismas identidades de código entre A/B y código físico actual.
- Suite focal: 21 PASS. Regresión Desktop: 43 PASS, un skip por disponibilidad
  del artifact histórico IMPL2. El primer intento de esta suite quedó esperando
  un error modal porque un mock apuntaba al importador anterior; se corrigió
  el destino del mock y se repitió satisfactoriamente. No se cambió validación.
- El coordinador `power_curve_sweep.py` admite checkpoints por invocación y
  reutilización verificada del formato de ingeniería; conserva la reauditoría
  de formatos anteriores y no atribuye auditoría independiente al nuevo formato.
- OpenSpec strict y program-status check: PASS.

Capturas reales: edición `01`, resultados `02`, presión A/B `03`, diferencias
geométricas y métricas indefinidas `04`, flujo A/B `05`, estimaciones transitorias
`06`. Receipt compacto con hashes: `receipt.json`.
Artifacts completos: `E:/Dino-artifacts/functional-exhaust-comparison-v1-20261022/`.

Sin nuevas ecuaciones, calibración, experimento de rigidez, EXE ni push. Los
históricos y los preparativos locales ajenos se preservan. La siguiente entrega
Windows no se inició. El resultado funcional permite editar y comparar el
motor; todavía no permite entregar una curva periódica de potencia/torque.
