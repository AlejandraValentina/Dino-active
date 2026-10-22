# Entrega 1: motor integrado desde Dino Desktop

## Resultado funcional

Implementado y ejecutado desde el botón existente de Desktop: abrir proyecto,
simular, seleccionar historial y mostrar resultados reales. Proyecto:
`configs/reference_cases/functional_reed_125cc_v1.dino.json`.
No se construyó un EXE nuevo; esta aceptación corresponde a la aplicación fuente.

Las láminas responden a presión sin ventana artificial del pistón. Los conductos
de transferencia están abiertos al cárter y controlados por pistón al cilindro.
El barrido modifica el transporte de especies durante el cálculo: interpolación
local conservativa entre mezcla uniforme y expulsión preferente de gases usados,
con límites por inventario disponible. Fracción de mezcla 0.5 declarada sintética
y no identificada; no equivale a reproducir íntegramente un modelo publicado.
Se reutilizaron solver, runner eficiente, proyectos, checkpoints e interfaz.

## Ejecuciones medidas

Caso: 125 cc, 9000 RPM, 44 celdas, CFL 0.4, AFR suministrado 11.5,
láminas originales de 1000 N/m y FMEP explícito sintético de 85000 Pa.

| Ejecución | Ciclos | Tiempo del runner | Pico proceso |
|---|---:|---:|---:|
| Desarrollo desde Desktop | 1–10 | 66.836 s | 211.6 MiB |
| Reanudación desde Desktop | 11–12 únicamente | 13.889 s | 219.8 MiB |
| Comprobación del código final, desde estado inicial | 1–3 | 19.816 s | 215.9 MiB |

Primera corrida: 80.725 s acumulados, aproximadamente 6.73 s/ciclo.
Comprobación final: 17.700 s de avance físico y 1.026 s de procesamiento
diagnóstico; el resto corresponde a otras operaciones del runner.
No son benchmarks de un barrido ni una demostración de velocidad comparativa.
Los checkpoints de los ciclos anteriores se conservaron; se verificaron 15
restores nativos sin pasos adicionales. Las dos ejecuciones tienen identidades
de código diferenciadas, conservadas en receipt y directorios externos.

Todas terminaron `MAX_CYCLES_NONCONVERGED`. En el ciclo 12:

- Trabajo indicado: 34.340 J; trabajo del cárter: −1.170 J.
- Calor liberado: 73.844 J; combustible quemado: 2.020 mg.
- Aire admitido al cárter: 33.482 mg; aire atrapado: 29.719 mg.
- AFR atrapado: 7.639, distinto del suministrado por retención e inventario.
- Potencia indicada instantánea por ciclo: 5.151 kW; torque: 5.465 N·m.
- Estimación al freno con fricción sintética: 3.386 kW y 3.593 N·m.
- Residuos relativos internos de energía, masa y especies: 3.75e−16,
  5.42e−16 y 7.26e−16. No son auditoría independiente.
- 56 comparaciones de periodicidad fallaron: no hay potencia definitiva.

La comprobación final mostró trabajo −52.514, 67.166 y 35.827 J en sus tres
ciclos. La variación inicial es significativa. Sus tarjetas muestran 3.609 kW
y 3.829 N·m como TRANSITORIO, NO CONVERGIDO; las curvas definitivas quedan sin
ese punto. Hay respiración, combustión y trabajo positivo después del arranque,
pero todavía no está demostrado un régimen estacionario ni una predicción real.

En una muestra aceptada a 180° del ciclo final, la fracción fresca del cilindro
era 0.33712 y la del flujo expulsado 0.16856. Esto demuestra que la ley interviene
en el intercambio conservativo, no sólo en una métrica posterior.

## Evidencia de interfaz y pruebas

Capturas reales: `01-project.png`, `02-results.png`, `03-pressure-flow.png`,
`04-exhaust-flow.png`, `05-cylinder-pressure.png`. Presión y caudal corresponden
al ciclo 3 seleccionado; el mapa representa sólo la posición guardada, no un
campo espacial completo. Los hashes están en `receipt.json`.

- Regresión integrada seleccionada: 94 passed, 9 deselected.
- Suite focal final: 22 passed. Hay solapamiento entre suites.
- Tests de conexiones, flujo inverso, transporte conservativo durante etapas,
  restore, compatibilidad legacy y resultados con hashes.
- OpenSpec strict y program-status check: PASS.
- No replay ni auditoría independiente durante la ejecución exploratoria.

Artifacts completos fuera de Git bajo
`E:/Dino-artifacts/functional-desktop-v1-20261022/`.

## Límites y siguiente entrega

No hay bloqueo funcional para abrir, ejecutar y consultar este caso desde
Desktop. Persisten límites científicos: ley de barrido no identificada,
láminas cuasiestáticas, temperatura de cilindro uniforme, EOS común, parámetros
térmicos/fricción sintéticos e independencia espacial no demostrada. La
conservación interna no elimina esas limitaciones.

Estado administrativo REVIEW: funcionalidad de entrega 1 demostrada, sin claim
predictivo ni release empaquetado. No se ejecutó un barrido, ni comparación de
escapes, ni sensibilidad de rigidez. Entregas 2 y 3 requieren su propio alcance.
R2 y evidencia histórica preservados; preparativos locales ajenos sin stage.
