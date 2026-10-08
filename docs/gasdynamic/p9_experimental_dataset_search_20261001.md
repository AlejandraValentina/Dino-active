# Búsqueda de dataset experimental P9 — 2026-10-01

## Resultado

**Estado: `DATA_REQUEST_REQUIRED`.** El mejor candidato es el ensayo Honda RS125
descrito en SAE 2004-01-3561. Es conceptualmente cercano al contrato P9: un único
motor Honda 125 cm³, monocilíndrico, 2T, a plena carga en un rango reportado de
9000–13000 rpm, con historias de presión en cilindro y escape contra ángulo de
cigüeñal y resultados de dinamómetro. La página pública acredita esas
características, pero no proporciona archivos numéricos, número de puntos,
metadatos experimentales completos ni un enlace de descarga suplementaria.
Por ello todavía no satisface el mínimo P9 de cinco puntos RPM ni permite
reconstruir de manera independiente `∮p dV`.

No encontré otro dataset público cuya evidencia publicada verifique
simultáneamente cinco o más puntos RPM de una configuración fija, presión
numérica contra ángulo, geometría/procedimiento de referencia suficientes y
proveniencia/licencia utilizables. Esto significa “no localizado en la búsqueda
pública realizada”, no que los archivos no existan en archivos privados de los
autores o de las instituciones.

No se descargó ningún conjunto de datos. Se consultaron páginas bibliográficas,
repositorios institucionales y resultados de búsqueda públicos. Se abrió para
lectura el PDF institucional de una tesis UWTSD y el PDF de una tesis NC State;
no se copiaron sus archivos ni se guardó un dataset en el repositorio. No se
ejecutó MotorSim/P9, no se compararon resultados y no se calibró el modelo.
El preregistro y el contrato P9 v1.0 permanecen sin cambios.

## Criterio de calificación

La clasificación se basa en la evidencia pública disponible frente al contrato
congelado en
[`spec.md`](../../openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md)
y su receipt de preregistro
[`preregistration.json`](../../results/p9-readiness-20261001/preregistration.json).
P9 exige una sola configuración física 2T, cinco o más puntos RPM, datos
primarios reproducibles de trabajo/potencia indicada —preferentemente presión
contra ángulo más geometría—, procedencia y condiciones, y alineación/TDC
independientes. Las curvas impresas en una figura no se digitalizaron ni se
consideran dataset confirmatorio.

## Matriz de candidatos

El receipt JSON contiene para cada fila los campos completos solicitados
(geometría, condiciones, ciclos, incertidumbre, canales, acceso, bloqueos y
acción recomendada). `Desconocido` significa que la fuente examinada no lo
establece; no se infirieron valores.

| ID | Motor / fuente | RPM / presión-ángulo / datos numéricos | Clasificación y bloqueo principal |
|---|---|---|---|
| C01 | [Honda RS125, SAE 2004-01-3561](https://saemobilus.sae.org/papers/validation-a-computer-simulation-a-high-performance-two-stroke-motorcycle-racing-engine-2004-01-3561), 2004; Queen's University Belfast y OPTIMUM Power Technology | Rango 9000–13000 rpm; el resumen confirma presión de cilindro/escape contra ángulo y dinamómetro. Número de puntos, ciclos y acceso a raw desconocidos. | `PROMISING_DATA_REQUEST_REQUIRED`; candidato preferido, requiere archivos, ≥5 puntos, geometría/configuración y metadatos. |
| C02 | [Yamaha TZ250B, SAE 962535](https://saemobilus.sae.org/papers/cylinder-pressure-analysis-high-performance-two-stroke-engines-962535), 1996; Queen's University Belfast | Presión de cilindro analizada para configuraciones CR 7.8 y 9.0 a varios regímenes; cantidad de RPM, trazas numéricas y ciclos desconocidos. | `PROMISING_DATA_REQUEST_REQUIRED`; separar una sola CR/configuración y obtener raw más metadata. |
| C03 | [Husqvarna TE250i/KTM, tesis MRes UWTSD](https://repository.uwtsd.ac.uk/id/eprint/3981/1/Vacas_J_MRes_Thesis.pdf), Vacas, 2025 | Campaña actual: 1600 y 2500 rpm; presión medida por grado, hasta ~6000 ciclos, pero el apéndice público contiene figuras. | `INSUFFICIENT_OPERATING_POINTS`; dos velocidades. TDC corregido documentado; archivos numéricos no expuestos. |
| C04 | [Datos previos de KTM citados por la tesis UWTSD](https://repository.uwtsd.ac.uk/id/eprint/3981/1/Vacas_J_MRes_Thesis.pdf) | La tesis menciona presión/datos promediados de 300 ciclos y rango 2000–10000 rpm proporcionados por KTM; no da el número de puntos ni una referencia pública separada. | `PROMISING_DATA_REQUEST_REQUIRED`; pedir la tesis/datos originales y verificar motor, puntos, trazas, configuración y derechos. |
| C05 | [Yamaha KT-100, tesis NC State de Gore](https://repository.lib.ncsu.edu/bitstreams/24433484-a6eb-4ad8-80f1-a18fa75c4ef6/download) | 4250, 6700 y 9100 rpm; presión sincronizada con ángulo y encoder/TDC, pero publicada como figuras; 3 RPM. | `INSUFFICIENT_OPERATING_POINTS`; geometría e instrumentación relativamente descritas, falta ≥5 y archivos crudos. |
| C06 | [Motor SI 2T de 55 cm³ UAV, SAE 01-17-01-0004](https://saemobilus.sae.org/articles/investigation-cylinder-pressure-measurement-methods-a-two-stroke-spark-ignition-engine-01-17-01-0004), 2023 | Presión medida con dos transductores y sensor capacitivo TDC; artículo trata 1000–2000 rpm motorizado para TDC. Número de puntos confirmatorios/raw no verificado. | `INSUFFICIENT_METADATA`; buen precedente metodológico, no se acredita el conjunto P9. |
| C07 | [SI 2T monocilíndrico 149 cm³, artículo EGR](https://www.mdpi.com/1996-1073/12/4/609), 2019 | 1000/2000/3000 rpm; presión y análisis de 120 ciclos, pero velocidad/puntos insuficientes y no se localizó raw numérico descargable. | `INSUFFICIENT_OPERATING_POINTS`; sólo tres regímenes y cargas distintas. |
| C08 | [Motor 2T portátil, SAE 2017-32-0043](https://saemobilus.sae.org/papers/practicability-influencing-factors-a-lean-burn-mode-two-stroke-engines-hand-held-powertools-2017-32-0043), Graz/STIHL | El registro bibliográfico muestra una sección “Data Sets”, pero no se verificó un archivo de presión/ángulo, punto RPM o descarga reutilizable. | `INSUFFICIENT_METADATA`; solicitar contenido y metadatos antes de considerarlo. |
| C09 | [Motor GDI SI 2T 300 cm³, SAE 2018-32-0047](https://saemobilus.sae.org/papers/experimental-investigation-potentiality-a-gdi-system-applied-a-two-stroke-engine-analysis-pollutant-emission-fuel-consumption-reduction-2018-32-0047), Universidad de Florencia/Betamotor | Ensayos de banco sobre emisiones/consumo; el resumen público no acredita presión contra ángulo ni datos crudos de `p-V`. | `INSUFFICIENT_METADATA`; revisar con autores sólo si pueden proveer canal indicado primario. |
| C10 | [Dataset Mendeley d8fhndxmtx.1](https://data.mendeley.com/datasets/d8fhndxmtx/1) (resultado de búsqueda amplia) | 100 ciclos a 2000 rpm y 100 Nm, presión-ángulo cruda; motor dual-fuel diesel/gas, no 2T SI aplicable. | `NOT_COMPATIBLE`; no usar para P9. |

## Hallazgos importantes sobre las tesis KTM/Husqvarna

La tesis MRes pública identifica un Husqvarna TE250i con motor KTM y una campaña
de presión ciclo a ciclo para 1600 y 2500 rpm. Informa medición por grado,
muestras de cientos de ciclos y hasta aproximadamente 6000 ciclos continuos.
Documenta que TFX revisó datos crudos de puesta a punto y devolvió una ganancia
del sensor y offset de TDC (156° y 0.790 mV/psi). El apéndice llamado “Measured
Raw Data” muestra gráficos de runs, no exportaciones CSV/MATLAB/TDMS recuperables.
La tesis no publica cuántos puntos RPM había en otro dataset de KTM que cita:
datos promediados de 300 ciclos entre 2000 y 10000 rpm. Ese segundo conjunto
merece una solicitud independiente, pero no se puede contar como cinco puntos
ni como presión numérica accesible hasta inspeccionar los archivos originales.

La tesis NC State de Matthew Royce Gore describe un Yamaha KT-100 monocilíndrico
2T (97.6 cm³, 52 × 46 mm, CR 8.3:1), transductor Kistler 6052A y encoder de eje
con determinación de TDC. La presión contra ángulo se muestra para 4250, 6700 y
9100 rpm; por tanto no cumple cinco RPM. La fuente consultada es una tesis
institucional de acceso público; no se identificó una licencia abierta separada
para reutilización de sus mediciones.

## Contacto verificado y próximo paso

El registro SAE atribuye a Bryan J. Fleck, Robert Fleck y Robert J. Kee a
Queen's University Belfast, y a Glen F. Chatfield y Dermot O Mackey a OPTIMUM
Power Technology. No se encontró una dirección personal verificable de esos
autores en una fuente institucional actual. El contacto institucional oficial
publicado por [Queen's School of Mechanical and Aerospace Engineering](https://www.qub.ac.uk/schools/SchoolofMechanicalandAerospaceEngineering/Connect/Getintouch/) es
`schooloffice.mae@qub.ac.uk` (también publica `mech.aero@qub.ac.uk`); se recomienda
pedir que deriven la consulta a los autores o al responsable del archivo de
investigación. No se ha enviado ningún mensaje.

### Borrador de solicitud (no enviado)

**Subject:** Request for experimental data — SAE 2004-01-3561 Honda RS125

Dear School Office,

Could you please forward this request to the authors or the appropriate
research-data contact for SAE paper 2004-01-3561, “Validation of a Computer
Simulation of a High Performance Two-Stroke Motorcycle Racing Engine”?

I am working on MotorSim, an independent gas-dynamics software project, and am
preparing a preregistered, no-calibration validation of one fixed two-stroke
configuration. I am seeking the experimental evidence behind the Honda RS125
results, specifically raw or processed in-cylinder pressure versus crank angle
at five or more full-throttle RPM operating points in the reported 9000–13000 rpm
range. We will preserve the original data and provenance and will not tune the
model against the validation measurements.

If shareable, CSV, MATLAB, Excel, acquisition exports or another documented
numeric format would be useful, together with the engine/configuration
identification and geometry (bore, stroke, connecting rod, compression ratio,
port timing and intake/exhaust setup), exact RPM/load/fuel/mixture and ambient
conditions, TDC/encoder procedure, pressure-sensor calibration, cycles per
point, uncertainty and any processing or exclusions. Please also indicate the
license or permission terms required for this research use. If those files are
not available, a pointer to the appropriate author, institution or archive
would be appreciated.

Thank you for your time.

Regards,
MotorSim project

### Solicitudes focales adicionales (no enviadas)

**Queen's University Belfast — SAE 2001-28-0059 y SAE 978510.** Consultar si
conservan las 2000 trazas de presión del estudio monocilíndrico lean-burn y las
capturas presión/ángulo del ensayo transitorio. Para cada paquete, pedir el
modelo/configuración de motor, lista completa de RPM y cargas, indicar cuáles
son puntos estabilizados, formato raw, número de ciclos por punto, geometría,
procedimiento TDC, calibración/incertidumbre y permisos de reutilización. En
SAE 978510, preguntar de forma explícita si hay cinco o más puntos estacionarios;
las mediciones hechas durante aceleración no se asumirán equivalentes. En SAE
2001-28-0059, confirmar si las 2000 trazas cubren cinco o más RPM en una misma
configuración. Contacto de enrutamiento institucional verificado:
`schooloffice.mae@qub.ac.uk`.

**University of Wales Trinity Saint David — datos previos KTM citados en la
tesis MRes 2025.** Pedir al autor, vía la biblioteca institucional, la cita
primaria del dataset de aproximadamente 2000–10000 rpm, si sobreviven sus
archivos de adquisición/setup, puntos exactos, motor/configuración, geometría,
calibración/TDC, incertidumbre y permiso. No se asume que la mención de 300
ciclos o el rango de RPM garantice cinco puntos compatibles. Ruta verificada:
`library@uwtsd.ac.uk`.

Las tres solicitudes anteriores siguen preparadas, pero no se enviaron.

## Búsquedas realizadas y límites

Se buscaron títulos/DOI/autores y frases sobre `two-stroke`, presión de cilindro,
crank angle, datasets/CSV, RPM y tesis; se revisaron registros SAE Mobilus,
resultados institucionales UWTSD y NC State, resultados de repositorios
académicos y búsquedas dirigidas a Zenodo, Figshare y Mendeley Data. Se revisaron
SAE 2004-01-3561, SAE 962535, SAE 2017-32-0043, SAE 2018-32-0047, SAE
01-17-01-0004, la tesis UWTSD 2025, la tesis NC State de Gore y el artículo
EGR abierto de 2019. El resultado Mendeley accesible era de un motor distinto
y 2000 rpm, por lo que se excluyó.

Los artículos SAE examinados exponen metadatos/resúmenes públicos, mientras el
texto completo aparece sujeto a acceso del editor; no se intentó eludir paywalls.
Las páginas públicas no mostraron un archivo numérico descargable del RS125.
La ausencia de un enlace visible no prueba inexistencia de archivos privados o
de un suplemento entregado bajo solicitud.

## Evidencia y estado

- Búsqueda completada: diez candidatos/ramas catalogados en el receipt JSON.
- Mejor candidato: Honda RS125, SAE 2004-01-3561; solicitud pendiente de envío
  manual por la usuaria.
- Clasificación de búsqueda: `DATA_REQUEST_REQUIRED` / candidato
  `PROMISING_DATA_REQUEST_REQUIRED`.
- Archivos experimentales descargados: ninguno; hashes/tamaños: no aplican.
- Comparación, simulación, campaña y calibración P9: no ejecutadas.
- Estado P9: `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`.
- Contrato/preregistro: intactos.

## Ampliación de búsqueda y calificación sintética (actualización del mismo día)

La matriz histórica de diez filas anterior se conserva sin reescritura. Una
segunda búsqueda incorporó 17 leads adicionales, para 27 filas/leads en total,
con una matriz normalizada y límites por campo en
[`search-expansion.json`](../../results/p9-dataset-search-20261001/search-expansion.json).
La matriz completa en el esquema P9, con todas las columnas y `null` explícito
para lo desconocido, está en [`matrix.json`](../../results/p9-dataset-search-20261001/matrix.json).
La nueva consulta del SAE 2001-28-0059 halló una campaña de 2000 trazas
continuas de presión en un 2T SI monocilíndrico, pero el resumen público no
establece cinco RPM ni da archivos de adquisición, configuración completa o
licencia. Queda como `DATA_REQUEST_REQUIRED`, no como dataset P9 listo.

La búsqueda también detectó estudios de kart 2T que ofrecen potencia de banco,
un motor pequeño de investigación con solo una velocidad pública, un HCCI 2T
con presión experimental en un único punto y otros motores 2T de arquitectura
pesada/opposed-piston. El trabajo de SAE 2001-28-0059 describe las 2000 trazas;
el informe técnico Chalmers muestra presión angular experimental para un
prototipo de range-extender a 11200 rpm; ambos son pistas, no archivos de
medición descargables. La tesis UWTSD documenta adquisición/corrección de
ángulo y ganancia, pero su análisis público cubre 1600 y 2500 rpm. [SAE
2001-28-0059](https://saemobilus.sae.org/papers/experimental-investigation-cyclic-variation-combustion-phases-a-lean-burn-two-stroke-si-engine-2001-28-0059),
[Chalmers report](https://research.chalmers.se/publication/534994/file/534994_Fulltext.pdf),
[UWTSD thesis](https://repository.uwtsd.ac.uk/id/eprint/3981/1/Vacas_J_MRes_Thesis.pdf).
La búsqueda de referencias también encontró SAE 978510, con presión de cilindro
y escape capturada a intervalos durante una aceleración en un banco inercial;
la naturaleza transitoria no demuestra por sí sola cinco puntos estacionarios.
[SAE 978510](https://saemobilus.sae.org/papers/validation-two-stroke-engine-simulation-a-transient-test-method-978510).

Una búsqueda de repositorios encontró además una ficha de datos de presión
resuelta por ángulo para el motor AVL 5402 de investigación; ese motor es 4T y
por tanto no se incorporó como candidato compatible. La página del artículo
IAME X30/Screamer III es una comparación modelo-potencia de banco y tampoco
aporta la presión experimental primaria necesaria. [Mendeley AVL
5402](https://data.mendeley.com/datasets/rg4tyrxv2j/1), [IAME 1D model
paper](https://www.mdpi.com/1996-1073/16/13/4947).

La expansión buscó Zenodo, Figshare, Mendeley Data, OSF, Dryad, IEEE DataPort,
suplementos y repositorios académicos/institucionales. El acceso de búsqueda a
IEEE DataPort fue bloqueado por robots; no se infiere ausencia de datos
privados. No se descargó ningún dataset, no se digitalizaron figuras ni se
contactó a autores. Se verificaron rutas institucionales para pedir archivos
de QUB/UWTSD y las solicitudes siguen sin enviar.

La infraestructura sintética ahora disponible se documenta por separado en
[`p9_pipeline_qualification_20261001.md`](p9_pipeline_qualification_20261001.md).
Su calificación no altera esta conclusión de Track A: el estado experimental
P9 sigue `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`,
`NOT_PERFORMED`; no hay comparación, calibración ni campaña confirmatoria.
