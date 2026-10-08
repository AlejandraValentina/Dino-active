# KT100 reference case V1

`KT100_REFERENCE_CASE_V1` identifica el **KT100SP** anunciado por Yamaha para
la clase doméstica japonesa FP2 en diciembre de 1998. El comunicado oficial
describe un motor monocilíndrico 2T con válvula a pistón, refrigerado por aire,
97,6 cm³ declarados, diámetro/carrera 52 × 46 mm, compresión 9,0:1, encendido
TCI, lubricación por premezcla y carburador Walbro WB40. Describe además tubo de
escape oval y una cámara silenciadora escalonada opcional. [Comunicado Yamaha
(1998)](https://global.yamaha-motor.com/jp/news/1998/1216/kart.html)

La publicación no precisa número de serie/año de producción, régimen nominal o
rango de uso, longitud de biela, cronometraje o dimensiones de puertos,
volumen del cárter, curva de encendido, dosificación del carburador ni
dimensiones del escape. Esos valores figuran como `UNKNOWN`; no se completan
con especificaciones de KT100S/SE/SD/SEC. El reglamento australiano KT100S y
una tesis académica con identidad de variante distinta se guardan como
referencias de reconciliación, no como fuentes de valores KT100SP.

## Geometría y provenance

El desplazamiento derivado de los valores nominales publicados es
`π × 52² × 46 / 4000 = 97,690965 cm³`; Yamaha publica 97,6 cm³ con una cifra
decimal. La diferencia nominal es 0,090965 cm³; no se supone truncamiento para
hacerla coincidir. Si 52 y 46 mm fueran valores redondeados al milímetro más
cercano, el intervalo geométrico resultante sería 94,779789–100,661046 cm³,
que contiene 97,6. Yamaha no declara esa precisión ni su regla de redondeo, así
que se conserva la discrepancia explícita y la compatibilidad queda condicional.
El área
del pistón es `2123,716634 mm²`, carrera barrida por cilindro `97,690965 cm³`
y radio de manivela `23 mm`. El volumen de holgura condicional es
`12,211371 cm³`, asumiendo que 9,0:1 significa `VBDC/VTDC`; esa interpretación
no está especificada por Yamaha. La función cinemática volumen/ángulo usa
longitud de biela sintética de 100 mm. También se implementan velocidad media
del pistón, frecuencia de ciclo 2T y conversión de trabajo por ciclo a potencia
y par equivalente; ninguna completa datos reales de rendimiento.

Los documentos legibles por máquina están en
[`kt100_reference_v1_provenance.json`](../../configs/reference/kt100_reference_v1_provenance.json),
[`kt100_model_fixture_v1.json`](../../configs/fixtures/kt100_model_fixture_v1.json)
y [`source-inventory.json`](../../results/kt100-reference-v1-20261001/source-inventory.json).
Cada supuesto del fixture declara valor, unidad, razón, sensibilidad prevista,
impacto esperado y origen conceptual.

## Fixture y ejecución

`KT100_MODEL_FIXTURE_V1` es un proyecto MotorSim distinto del caso documental.
Sus puertos, conductos rectos, biela de 100 mm, cárter de 250 cm³, propiedades
del gas, condiciones iniciales y fuente térmica prescrita son supuestos
sintéticos. No son geometría Yamaha, combustión química ni poder calorífico de
combustible.

La campaña usa el modelo existente de cuatro volúmenes 0D I/K/C/E, RK4
adaptativo perfil B, banda exterior fija de 100 Pa y horizonte existente de
hasta 30 ciclos. El detector nativo solo da convergencia de periodo 1. No es
E13-R1, no detecta periodo 2 y no modela ondas en conductos finitos. El barrido
5000/7000/9000/11000/13000 rpm se eligió como una malla numérica fija, no como
rango de funcionamiento del KT100SP. Cuatro puntos convergieron al criterio
0D; 5000 rpm terminó tras 17 ciclos por ocho rechazos consecutivos.

Cada trayectoria del barrido se repitió desde la condición inicial y el
historial por ciclo, estado y contadores de integración coincidieron
exactamente. Esto es replay determinista; el API 0D no tiene restart y no se
declara verificación de reinicio. Los balances discretos e independientes de
masa, energía y marcador fresco pasaron por ciclo completado. Fresh delivery no
se ledgeriza por separado, el short-circuit no se resuelve, el marcador no es
el conjunto de cuatro especies de P6 y CFL no aplica a 0D. Por eso los gates
completos de P5-C/P6/P7 y E13 no quedan acreditados.

En el ledger global independiente, el máximo de los valores normalizados
observados entre los cinco últimos ciclos completados fue `4,181e-8` para masa,
`1,377e-7` para energía y `3,769e-8` para el marcador fresco. Son comprobaciones
del modelo 0D con sus estados sintéticos, no balances de un motor medido.
Una auditoría offline de todos los estados de fin de ciclo conservados confirmó
masa y energía positivas, estado finito y marcador dentro de `[0,m]` en todos
los ciclos completos. No hay estado final guardado para el ciclo incompleto de
5000 rpm; el criterio no acredita etapas de 1D o cuatro especies.

El preflight de topología híbrida completa terminó en `ValueError: invalid
species state`. El artefacto pequeño se conserva en
[`kt100-reference-v1-20261001-smoke`](../../results/kt100-reference-v1-20261001-smoke/).
No se modificó física para ocultar ese fallo. La exploración 0D no se presenta
como sustituto de esa verificación.

## Resultados de referencia sintéticos

Todos los valores de trabajo, potencia, par y presión son solo salidas de este
fixture sintético y no resultados de un Yamaha real.

| RPM exploratorio | Estado 0D | Ciclos | Trabajo J/ciclo | Potencia derivada W | Par equivalente N·m | Presión máxima Pa |
|---:|---|---:|---:|---:|---:|---:|
| 5000 | No convergió; 8 rechazos consecutivos | 17 | 12,798787 | 1066,566 | 2,03699 | 1 723 551 |
| 7000 | Periodo 1 | 19 | 10,857579 | 1266,718 | 1,72804 | 1 755 497 |
| 9000 | Periodo 1 | 21 | 9,350470 | 1402,570 | 1,48817 | 1 793 150 |
| 11000 | Periodo 1 | 22 | 8,181700 | 1499,978 | 1,30216 | 1 828 130 |
| 13000 | Periodo 1 | 25 | 7,244386 | 1569,617 | 1,15298 | 1 857 503 |

El punto de 5000 rpm se conserva como no convergido, aunque el balance del
último ciclo completado pasara. No se extrapola ni se presenta una curva como
rendimiento del KT100.

La sensibilidad fue preregistrada en 9000 rpm —punto medio de la malla— con
perturbaciones independientes de ±5 % en biela y longitud total de escape.
Las cuatro variantes convergieron en 20–21 ciclos. El trabajo varió entre
−0,1353 % y +0,1513 %; la presión máxima entre −0,1323 % y +0,1206 %. Es una
descripción local para dos supuestos sintéticos, no calibración ni análisis de
incertidumbre completo. Protocolo y datos: [`sensitivity-preregistration.json`](../../results/kt100-reference-v1-20261001/sensitivity-preregistration.json)
y [`sensitivity.json`](../../results/kt100-reference-v1-20261001/sensitivity-runs/sensitivity.json).

## Claims y estado

Claim permitido: MotorSim puede representar y ejecutar una configuración de
referencia basada en geometría KT100SP publicada, completada con supuestos
sintéticos identificados explícitamente.

No se afirma que MotorSim prediga con precisión el KT100, que este fixture esté
validado, ni que haya validación experimental o predictiva. Estado P9 intacto:
`P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`, `NOT_PERFORMED`,
`NOT_CLAIMED`. Decisión y hashes de evidencia:
[`decision.json`](../../results/kt100-reference-v1-20261001/decision.json).

Reproducir la configuración con `python -m scripts.build_kt100_fixture`;
reproducir el barrido con `python -m scripts.run_kt100_reference_study
--output results/kt100-reference-v1-20261001 --rpm 5000 --rpm 7000 --rpm 9000
--rpm 11000 --rpm 13000`. Las ejecuciones son costosas y están limitadas por
los guardas temporales existentes.
