# STANDARD_V1 — diagnóstico y única continuación controlada

## Resultado y certeza de las conclusiones

Se ejecutó **sólo la opción A**: restauración exacta del checkpoint 30 y ciclos
**31–50**, sin repetir ciclos ni cambiar parámetros físicos. Resultado:
**MAX_CYCLES_NONCONVERGED**. Se cerró en el máximo autorizado de 50.

| Pregunta | Conclusión | Certeza |
|---|---|---|
| ¿Por qué AFR atrapado < suministrado? | Combustible remanente tras quemar una carga limitada por el oxígeno elegible, seguido de nueva admisión y barrido bien mezclado | Alta, eventos y balances |
| ¿Qué impide la periodicidad? | Desplazamiento de la composición inicial del escape y sus inventarios globales | Alta, 53 de 55 fallos finales |
| ¿Esperar otras 20 vueltas recuperó carga/potencia? | No: aire atrapado -0.085%, trabajo -0.176% | Alta, comparación 30→50 |
| ¿Cuál es la causa física única del bajo llenado? | No aislada; láminas cuasiestáticas gobiernan el mínimo de área, con posibles efectos del doble estrangulamiento y del barrido 0D | Hipótesis, no causalidad demostrada |

## 1. Balance de especies

Se reconstruyó cada volumen entre checkpoints 29→30 y 49→50 usando sus
inventarios, flujos SSPRK integrados y fuentes químicas. Todos los balances
cierran con residuo absoluto inferior a 1e-14 kg; no hay creación de combustible.
CSV completo: [balances por volumen](standard-v1-controlled-species-balances.csv).

Última vuelta, mg:

| Movimiento | Aire | Combustible |
|---|---:|---:|
| Atmósfera → conducto, bruto | 35.669 | 3.102 |
| Conducto → atmósfera, retorno | 3.361 | 0.292 |
| Conducto → cárter | 32.308 | 2.809 |
| Atrapado al cierre exacto del escape | 25.682 | 3.031 |
| Cilindro → escape, sin quemar | 6.683 | 1.069 |
| Consumido por combustión | 25.670 aproximadamente | 1.745 |

Estas masas no se restan como si correspondieran todas a la misma generación
de mezcla. La combustión cruza el PMS y los conductos almacenan gas.

Cambio de inventario de combustible durante la vuelta 50:

| Volumen | Delta mg |
|---|---:|
| Admisión | +0.000001 |
| Cárter | -0.003383 |
| Transfers, suma | -0.000525 |
| Cilindro | -0.000040 |
| Escape | +0.674365 |

El combustible que salió del cilindro no salió instantáneamente del sistema:
parte sigue almacenada en el escape. Su inventario pasó de 31.512 mg en el
ciclo 30 a 48.978 mg en el 50. Combustible no quemado, expulsado del cilindro,
almacenado y descargado al ambiente son magnitudes diferentes.

### Límite de la combustión, verificado directamente

El evento de encendido del ciclo 50 contiene **25.682 mg de aire, 3.0308 mg de
combustible y sólo 1.74558 mg elegibles para quemar**. `capture` calcula
`min(combustible, oxígeno_disponible / oxígeno_requerido)`: limita la segunda
rama. Se leyó el evento y se comprobó la ley del código, sin deducirlo del
cociente entre masa atrapada y combustible quemado.

Los nuevos contadores de tasas ya calculadas por SSPRK muestran 1.744828 mg
solicitados y 1.744765 mg quemados en la vuelta 50. El límite instantáneo por
disponibilidad de oxígeno recorta apenas **0.0036%**. Por tanto, la principal
limitación química se fija al capturar la carga elegible, no en una reducción
grande durante la integración. No se identificó otra restricción significativa.

El AFR permanece 11.5 en la alimentación/cárter, mientras el cilindro conserva
combustible después de consumir el aire elegible y recibe más mezcla. Así se
explica el AFR atrapado cercano a 8.47. La eficiencia 0.85 modifica el calor por
masa quemada; no convierte automáticamente todo el combustible en productos.

## 2. Restricciones y barrido

Durante depresión favorable, el mínimo de área sigue correspondiendo a las
láminas en todas las etapas; área efectiva máxima 954.6 mm², frente a 1134.1
mm² de conducto y 1162.8 mm² de ventana. La ventana híbrida no aparece como
cuello adicional en ese intervalo. Esto no prueba su equivalencia a una
admisión real ni mide qué caudal habría con otra rigidez.

No hay evidencia suficiente para llamar a esto bloqueo sónico: en el
checkpoint 30 los Mach de las celdas de admisión son 0.065–0.068; al invertir
la ley estática de área en sus muestras, la razón presión cárter/extremo del
conducto queda entre 0.900 y 1.000 durante apertura. Son observaciones locales,
no una medida de Mach de garganta en cada etapa del ciclo.

En la vuelta 30 el retorno de aire desde cilindro a transfers fue 0.054 mg
frente a 32.419 mg de entrega bruta: aproximadamente 0.17%. El escape no presentó
retorno al cilindro en las vueltas comparadas 30 y 50. El retorno exterior de
admisión tampoco equivale a reflujo del cárter: ocurre en el conducto aguas
arriba de las láminas. El doble estrangulamiento de transfers existe en el
código; sin A/B no se cuantifica su penalización.

El cilindro conserva **60.97% de productos quemados** en el cierre final. No es
gas residual de la inicialización: esa especie inicial prácticamente desapareció
del cilindro, aunque siga en el escape. Hay renovación fresca baja y expulsión
de aire sin quemar; el modelo 0D mezcla toda la carga y expulsa según composición
donante. No permite distinguir cortocircuito directo de mezcla nueva frente a
aire remanente de otra vuelta, ni aislar cuánto mejoraría un barrido estratificado.
No se presentan esos cocientes como TE/CE/SE identificadas.

## 3. Periodicidad: transitorio localizado, no un PASS oculto

| Ciclo | Fallos V2 | Del escape | Peor error / tolerancia |
|---:|---:|---:|---:|
| 30 | 57 | 54 | 13.813 |
| 41 | 60 | 58 | 11.424 |
| 45 | 58 | 56 | 11.114 |
| 50 | 55 | 53 | 10.933 |

Los otros dos fallos finales son inventarios globales de productos quemados y
residual. Su cambio normalizado es 0.00636 y 0.00832 frente al límite 0.002.
El peor fallo se desplazó de la celda 15 a la 28 del escape: avanza un frente
de composición. El número de celdas fallidas no tiene que decrecer monótonamente.

En las últimas diez vueltas el peor desvío disminuye de 11.424 a 10.933. El
trabajo converge localmente: 29.05287→29.04806 J, con una pequeña inversión de
pendiente final, sin alternancia sostenida. Comparar 48 con 50 también falla
(61 métricas); no hay evidencia de un periodo 2 que explique los fallos.

El escape todavía almacena aproximadamente **2.100 g** y descarga unos
**35.99 mg/vuelta**: inventario/flujo da una escala nominal de unas **58 vueltas**
por renovación, no un plazo garantizado de convergencia. Su especie residual
inicial bajó de 1118.925 a 507.493 mg entre 30 y 50; en la última vuelta pierde
23.597 mg y gana 18.039 mg de productos, 4.067 mg de aire y 0.674 mg de fuel.

No se encontró un error aritmético del detector. Su requisito es estado completo,
incluida composición de todo el escape. Allí residual y burned son etiquetas
transportadas con la misma EOS; pueden seguir cambiando aunque presión/trabajo
sean casi repetibles. Es una condición conservadora, no razón para modificarla
retrospectivamente. Se mantuvieron todos los umbrales.

## 4. Resultado del único experimento

| Magnitud | Ciclo 30 | Ciclo 50 |
|---|---:|---:|
| Aire al cárter mg/vuelta | 32.129 | 32.308 |
| Aire atrapado mg | 25.704 | 25.682 |
| AFR atrapado | 8.46985 | 8.47375 |
| Combustible quemado mg/vuelta | 1.74655 | 1.74476 |
| Calor J/vuelta | 63.8365 | 63.7712 |
| Trabajo indicado J/vuelta | 29.0993 | 29.0481 |
| Potencia indicada equivalente kW | 4.3649 | 4.3572 |
| Freno con fricción sintética kW | 2.5979 | 2.5893 |

Todas son magnitudes transitorias exploratorias, no resultados periódicos ni
potencia validada. Los veinte ciclos adicionales **no recuperaron el llenado**:
se descarta esa explicación para este intervalo, aunque el escape siga purgándose.

## 5. Costo, continuidad y verificaciones

- Continuación: **129.894 s de pared**, 115.295 s dentro de pasos del solver,
  7.613 s de procesamiento; **6.495 s por nueva vuelta** incluyendo overhead.
- Pared acumulada de ambas ejecuciones: **320.410 s**. Nuevo presupuesto: 300 s;
  no se reinició ni ocultó el tiempo anterior.
- Un worker, pico RSS **120.344 MiB**, límite operativo 512 MiB. Cero rechazos
  nuevos y sin error numérico terminal.
- Máximos residuos relativos acumulados en los 50 cierres: masa 3.89e-15,
  energía 8.80e-15, especies 2.98e-15, dentro del límite 1e-8.
- 30 ciclos anteriores preservados idénticos; todos los hashes registrados del
  padre permanecen intactos. Estado inicial de continuación: exactamente 10800°.
- 20 checkpoints nuevos restaurados exactamente, sin pasos físicos; último
  `next_cycle=51`. Sin duplicaciones ni cambios de solver/configuración.
- 24 tests focales PASS, incluida igualdad canónica del siguiente paso tras
  restore y rechazo de bindings/checkpoint alterados. OpenSpec strict y
  program-status check PASS (advertencia preexistente por dos READY ajenas).
- Revisión SELF_REVIEW. Sin replay ni auditoría independiente, según autorización.

Plan previo: [decisión congelada](standard-v1-controlled-continuation-plan.md).
Receipt: [resultado compacto](standard-v1-controlled-continuation-receipt.json).
Artifacts y gráfico: `E:/Dino-artifacts/standard-v1-9000-continuation-20261022/point/`.
No se modificó el informe, receipt ni artifacts de la primera ejecución.

## 6. Próximo cambio mínimo

El llenado bajo no quedó explicado por falta de otras veinte vueltas. La
siguiente sensibilidad física con mayor valor sería **únicamente la rigidez
cuasiestática de las láminas**, manteniendo área, AFR, transferencias, combustión
y válvula: gobierna el área observada, pero su valor es sintético. Un contraste
1000→500 N/m, explícitamente de sensibilidad y sin adoptarlo por la potencia
obtenida, permitiría medir si controla realmente la carga o si el límite se
desplaza a transfer/barrido. Esa prueba B **no se ejecutó** en esta autorización.

No conviene iniciar aún una curva presentada como estacionaria: el punto completo
no pasó periodicidad y la influencia del parámetro de admisión no está identificada.
Tampoco corresponde otra extensión automática por descarte. La contribución de
esta prueba es separar cuantitativamente purga del escape, enriquecimiento químico
y persistencia del bajo llenado, sin alterar el modelo para mejorar su potencia.
