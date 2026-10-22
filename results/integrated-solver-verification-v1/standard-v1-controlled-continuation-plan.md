# STANDARD_V1 — decisión antes del siguiente paso físico

Autorización del propietario: diagnóstico existente y exactamente UNA opción A
(continuación) o B (sensibilidad de un parámetro). Se selecciona **A**.

## Evidencia previa, sin nuevas simulaciones

En las vueltas 21–30 el peor cociente error/tolerancia decrece de 19.44 a
13.81. En la vuelta 30, 54/57 fallos son del escape, más tres de inventarios
globales. La cantidad de fallos no es monótona porque un frente composicional
cruza celdas, pero su mayor amplitud disminuye. Trabajo, calor y AFR se acercan
a valores repetibles; no hay evidencia de alternancia creciente. La composición
inicial del escape todavía se purga: en el ciclo 30 su inventario residual
inicial pierde 36.343 mg, mientras almacena 26.822 mg de productos, 6.424 mg
de aire y 1.035 mg de combustible. No basta estabilizar el cilindro para que
todo el sistema sea periódico.

El balance de cada especie por volumen entre checkpoints 29 y 30 cierra con
sus flujos y fuentes. Por ejemplo, combustible: cárter -0.017881 mg, transfers
-0.002599 mg en conjunto, cilindro -0.000516 mg, escape +1.035484 mg. No hay
creación de combustible ni razón para cambiar AFR por un error de balance.

El evento activo del ciclo 30 guarda 25.704 mg de aire y 3.0348 mg de
combustible en el encendido; elegibles para quemar: 1.74707 mg. En
`FuelCoupledCombustionV1.capture`, la elegibilidad es el mínimo entre combustible
y oxígeno disponible/oxígeno requerido. La segunda rama limita: no se deduce
esto del cociente aire/combustible quemado, sino del evento persistido y la ley
de captura. En las etapas puede limitar además la disponibilidad instantánea:
los traces completos originales no se conservaron y no permiten contar esos
límites retrospectivamente. Se agregan contadores de tasas ya calculadas en la
continuación; no se introduce otra evaluación física.

La admisión tiene un mínimo de área dominado por las láminas durante succión,
pero eso NO demuestra flujo sónico. La ventana no fue el mínimo durante esa
succión. El doble estrangulamiento de transfers existe, pero no hay contraste
que mida su penalización. La hipótesis de baja renovación se mantiene; no se
selecciona arbitrariamente una rigidez o área para una sensibilidad todavía
confundida con el vaciado del escape y el almacenamiento transitorio.

## Única prueba autorizada

- Restaurar el checkpoint terminal del ciclo 30, validando SHA-256, productor
  original congelado, configuración, solver, RPM, historial y estado exacto.
- Productor original permanece identificado por su hash, sin reemplazarlo por
  el nuevo runner. La continuación tiene identidad propia y enlace al padre.
- Directorio nuevo; padre, configuraciones y checkpoints anteriores inmutables.
- Ejecutar solamente ciclos 31–50, máximo **50 acumulados** y **300 s nuevos**,
  512 MiB RSS, secuencial, 9000 RPM y configuración física idéntica. El límite
  operativo es menor que el máximo anterior de 3072 MiB: el pico medido fue
  110.6 MiB y 512 MiB conserva margen >4x sin exigir reservar 3 GiB libres.
- Mismo comparador V2, umbrales y tres comparaciones consecutivas. No se
  modifica la fricción sintética de postproceso. Sin replay ni auditoría.
- Parar por periodicidad observada, ciclo 50, pared, memoria, integridad,
  conservación o fallo terminal. Sin reintento ni experimento B posterior.

Hipótesis: la composición del escape seguirá perdiendo memoria del estado
inicial y disminuirán las diferencias entre vueltas, mientras carga fresca y
trabajo cambiarán menos. Que siga no convergido al ciclo 50 también es un
resultado interpretable; no se ampliará automáticamente.

Aceptación: continuidad exacta del estado y presupuesto, balances de especies
por compartimento, nueva evolución del error, llenado/AFR/quemado/trabajo, y
distinción entre magnitudes transitorias y periodo observado sin validación
experimental. No hay objetivo de potencia ni cambio físico.
