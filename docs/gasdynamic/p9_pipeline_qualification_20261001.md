# Calificación sintética aislada del pipeline P9 — 2026-10-01

## Alcance y estado

Este auditor prepara la ingestión offline de P9 v1.0 y se ejercita solo con un
“virtual experiment” analítico independiente de MotorSim. Sus tres escenarios
prueban el camino que pasa las métricas, uno que falla y otro inconcluso. Son
pruebas de software, no una validación experimental ni una evaluación
predictiva. El contrato OpenSpec y sus umbrales permanecen congelados.

Los fixtures siempre declaran `SYNTHETIC_PIPELINE_QUALIFICATION_ONLY`,
`NOT_EXPERIMENTAL`, `NOT_VALID_FOR_P9_DECISION` y
`MUST_NOT_PRODUCE_P9_PASS`. El resultado máximo es
`P9_PIPELINE_QUALIFIED_WITH_SYNTHETIC_DATA`; el estado real continúa
`P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`, con validación experimental
`NOT_PERFORMED` y predictiva `NOT_CLAIMED`.

## Esquema y auditor

Cada carpeta contiene `manifest.json`, `experiment.csv.gz` y
`simulation_primary.csv.gz`. El manifest vincula archivos, tamaño y SHA-256,
unidades (Pa absolutos identificados), procedencia, geometría, convención angular, siete puntos, ciclos,
incertidumbre y recibos sintéticos de P9-A. Cada CSV contiene
`rpm,cycle,angle_deg,pressure_pa`; las trazas son de 0 a 360° CA en pasos de
1° y contienen 50 ciclos consecutivos por punto. Los valores declarados de
trabajo, error, MAPE y estado PASS son datos deliberadamente no confiables.

La geometría fija sintética es un cilindro, diámetro 50 mm, carrera 50 mm,
biela 100 mm y relación geométrica 8:1. El desplazamiento barrido es
`π D² S / 4 = 98.174770 cm³`; el volumen de referencia en TDC es
`14.024967 cm³` y en BDC `112.199737 cm³`. Son datos inventados explícitamente
para el fixture y no representan ni copian un motor medido. El ciclo 2T usa
360° CA, origen TDC, dirección positiva. Los puntos son 3000, 4500, 6000,
7500, 9000, 10500 y 12000 rpm.

Las presiones siguen una función analítica declarada: compresión politrópica
con exponente 1.25 desde 101325 Pa en el volumen BDC, una depresión suave de
barrido/escape y una campana gaussiana de combustión que escala con velocidad.
La variación de ciclo es determinista, no aleatoria; el último extremo se
cierra con el primero. La incertidumbre es sintética y está rotulada: 4500 Pa,
0.08° CA y fracción de variación 0.0004. El generador usa una etiqueta de
semilla estable (`deterministic-analytic-no-randomness-v1`) y gzip con
timestamp cero.

El auditor recalcula volumen biela-manivela desde la geometría y trabajo
indicado por integración trapezoidal cerrada de `∮p dV` a partir de presión
raw. Calcula potencia 2T como `W_i × RPM × cilindros / 60`, alinea RPM bajo el
límite contractual del 1% y vuelve a calcular errores, MAPE, signo, porcentaje
de puntos dentro del 10/15% y forma. Nunca toma summaries o métricas del
manifest como autoridad. Verifica integridad, estructura, unidades, datos
numéricos finitos, geometría, trazas, ciclos consecutivos, incertidumbre y
recibos P9-A. Para period-2 el manifest identifica ramas A/B por separado,
vincula ambas al hash de evidencia y recalcula cada trabajo raw; la comparación
usa el promedio de ambos trabajos y conserva los dos valores. Un test sintético
específico comprueba ese comportamiento. Los datos experimentales podrán etiquetar incertidumbre no
disponible como `EXPERIMENTAL_UNCERTAINTY_UNKNOWN`, según el contrato; ese caso
no se sustituye por valores sintéticos.

## Comandos y resultados

```powershell
python -m motorsim.p9_synthetic tests/fixtures/p9_synthetic
python scripts/qualify_p9_synthetic.py
python -m pytest tests/test_p9_pipeline_qualification.py -q
```

Los casos PASS/FAIL/INCONCLUSIVE se auditan sin llamar al solver de MotorSim.
La prueba de conversión comprueba que 120 J a 6000 rpm y un cilindro dan
12000 W en 2T (y no 6000 W, que sería la mitad de frecuencia de ciclo 4T).
El fixture PASS cumple las métricas sintéticas; FAIL viola el gate de error de
un punto y el escenario inconcluso carece de geometría. Ningún caso autoriza
comparación confirmatoria. Recibos de auditoría e hashes reproducibles están
en `results/p9-pipeline-qualification-20261001/`.

## Búsqueda pública

La búsqueda expandida conserva las diez filas originales y registra otras
diecisiete en `results/p9-dataset-search-20261001/search-expansion.json` (27 en
total). Incluyó búsquedas por tipo de motor, títulos y DOI citados, repositorios
de datos y tesis, anexos, archivos suplementarios, repositorios institucionales,
trabajos de kart/carrera, utilitarios, marinos, DI y SI. Se detectó un trabajo
de 2T monocilíndrico con 2000 trazas continuas, pero la ficha pública no revela
cinco velocidades ni ofrece los archivos numéricos; queda como solicitud de
datos, no como dataset.

Se encontraron trabajos de investigación útiles como pistas: el SAE 2001-28-0059
describe 2000 trazas de presión en un 2T SI monocilíndrico, pero no se verificó
el conteo de RPM, el raw ni licencia; el material de UWTSD contiene presión
resuelta por ángulo y documentación de TDC/calibración, pero la campaña pública
solo analiza 1600 y 2500 rpm y muestra figuras; el estudio de SAE 962535 reporta
presión para TZ250B en dos relaciones de compresión y un rango de velocidades,
sin archivos numéricos públicos verificados. [SAE 2001-28-0059](https://saemobilus.sae.org/papers/experimental-investigation-cyclic-variation-combustion-phases-a-lean-burn-two-stroke-si-engine-2001-28-0059), [tesis UWTSD](https://repository.uwtsd.ac.uk/id/eprint/3981/1/Vacas_J_MRes_Thesis.pdf), [SAE 962535](https://saemobilus.sae.org/papers/cylinder-pressure-analysis-high-performance-two-stroke-engines-962535).

También se hallaron dos falsos positivos representativos: una ficha Mendeley
reciente ofrece presión angular pero es un motor de investigación 4T, y un
estudio kart 2T compara principalmente resultados de banco/dinamómetro. Estos
no satisfacen P9 como comparación de potencia indicada. [Mendeley, motor
AVL 5402](https://data.mendeley.com/datasets/rg4tyrxv2j/1), [QUB kart
2T](https://pure.qub.ac.uk/en/publications/inertial-testing-of-2-stroke-kart-engines/).

No se descargaron archivos de mediciones ni se envió ningún contacto. Los
contactos institucionales verificados y las solicitudes pendientes siguen
documentados en el informe/matriz de búsqueda. Con la evidencia pública
revisada, el mejor siguiente paso es obtener autorización y archivos originales
del candidato Honda RS125 de QUB o del dataset anterior KTM citado en la tesis;
después se debe comprobar el manifest de forma ciega respecto de MotorSim.
