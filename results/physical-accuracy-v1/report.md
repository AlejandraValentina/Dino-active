# Dino 2T — primera evaluación de precisión física

## Decisión técnica

La baja potencia se explica dentro del modelo por **bajo llenado de aire fresco, alta dilución y combustión limitada por oxígeno**, seguido de pérdidas térmicas y mecánicas importantes. No se encontró una incongruencia en la conversión trabajo → potencia → torque: se usa un ciclo por revolución. No hay evidencia para atribuir el déficit frente a un motor de competición a un error concreto del HLLC/SSPRK2 ni para reconstruir ese núcleo.

**La precisión experimental de Dino sigue sin determinarse.** La configuración funcional no reproduce un motor medido identificable y varias relaciones físicas decisivas son supuestos sintéticos. Una curva periódica resuelve el transitorio del modelo, pero no identifica esos supuestos ni su error físico. No se ejecutó una referencia experimental incompleta ni se ajustó ningún coeficiente.

Alcance realizado: reducción offline de los seis últimos ciclos periódicos existentes, lectura de código/configuraciones y búsqueda acotada de fuentes experimentales. Cero pasos del solver, cero campañas, cero modificaciones de física, Desktop o resultados históricos. Es SELF_REVIEW; no una auditoría independiente de primarias.

## 1. Qué producen realmente los seis puntos

HP mecánico = 745,6998716 W. IMEP: trabajo neto del gas en el cilindro / cilindrada; BMEP: trabajo al eje / cilindrada. Se separa el trabajo del cárter. Cilindrada exacta: 124,628 cm³.

|Variante|RPM|HP al eje|Torque Nm|IMEP bar|BMEP bar|Aire atrapado mg/ciclo|Residual quemado al cierre|
|---|---:|---:|---:|---:|---:|---:|---:|
|A|8000|4.116|3.664|2.794|1.847|30.27|54.8%|
|A|9000|4.506|3.565|2.744|1.797|29.69|53.4%|
|A|10000|4.725|3.365|2.642|1.696|28.92|52.5%|
|B|8000|4.093|3.643|2.783|1.837|30.15|54.8%|
|B|9000|4.478|3.543|2.732|1.786|29.59|53.4%|
|B|10000|4.880|3.475|2.699|1.752|29.45|51.9%|

Son PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED según el detector existente. No tienen validación experimental ni independencia espacial demostrada. El incremento de HP con RPM no representa mejor llenado: en A disminuyen IMEP y torque, mientras crece la frecuencia de ciclos.

## 2. Balance causal de A a 9000 RPM, ciclo 104

### Aire, combustible y barrido

- Referencia de aire seco: p·Vd/(R·T) = **146,666 mg**, a 101325 Pa, 300 K, R=287. No se multiplica este denominador por la fracción de aire de la mezcla.
- Aire aspirado bruto por la cara atmosférica: **37,595 mg**; retorno a admisión: **3,121 mg**; admisión neta: **34,474 mg/ciclo**. Delivery ratio de aire seco bruto **0,2563**, neto **0,2350**.
- Aire bruto que cruza las tres transferencias al cilindro: **34,581 mg**. Quedan **29,687 mg** al cierre del escape: eficiencia de carga respecto del aire seco de referencia **20,24%**.
- Cociente inventario atrapado / aire bruto transferido = **85,85%**; respecto de admisión neta = **86,12%**. Son indicadores de retención en operación periódica, no una eficiencia de atrapamiento identificada mediante trazador: el inventario incluye aire fresco que quedó de ciclos anteriores. No se asigna una TE experimental a estos cocientes.
- Salen por el escape del cilindro **4,800 mg de aire fresco** y **0,981 mg de combustible** en todo el ciclo. El ledger de cortocircuito registra **3,473 mg de mezcla fresca sólo durante el solapamiento**; no equivale a toda la pérdida de aire. El ledger fresh_delivered registra mezcla fresca en las transferencias, no aire aspirado atmosférico: **37,598 mg**.
- Al cierre quedan **72,040 mg totales**, con **38,457 mg de gases quemados**, un **53,38%** de residual quemado. La especie separada residual representa el gas inicial y casi se ha purgado; omitir la especie burned daría una conclusión falsa de ausencia de residuales.
- El combustible suministrado bruto es **3,269 mg**, neto **2,998 mg**; el atrapado es **3,895 mg**, porque incluye combustible no quemado retenido de ciclos anteriores. No es una fuente espontánea ni equivale a una masa nueva admitida ese ciclo.
- AFR suministrado **11,5**, de transferencia bruta **11,46**, atrapado **7,62**, estequiométrico del combustible sintético **14,713**. El aire atrapado sólo permite quemar **2,01782 mg**; se queman **2,01690 mg**, apenas **51,78% del combustible atrapado**. La limitación está ya en la carga disponible, no en un gran rechazo numérico de la etapa de combustión. Añadir combustible sin aire no resuelve este límite.

**Interpretación:** el motor calculado respira poco en términos absolutos; el porcentaje de aire retenido del que sí entra no compensa la admisión neta de sólo 0,235 masas de referencia. La mezcla rica y el residual explican conjuntamente la escasa energía por ciclo. El balance no identifica por sí solo cuánto de ese llenado proviene de geometría, láminas, ondas o cierre de barrido.

### Energía, trabajo y pérdidas

|Magnitud|J/ciclo|Equivalente a 9000 RPM|
|---|---:|---:|
|LHV del combustible efectivamente quemado|86,727|13,009 kW químicos|
|Calor aplicado por combustión, eficiencia prescrita 0,85|73,718|11,058 kW térmicos|
|Calor a paredes del cilindro, culata y pistón|23,866|3,580 kW térmicos|
|Calor neto a todas las paredes del sistema|26,453|3,968 kW térmicos|
|Energía externa neta entrante|−14,272|−2,141 kW|
|Trabajo neto del cilindro|34,193|5,129 kW indicados|
|Trabajo neto del cárter|−1,199|−0,180 kW|
|Trabajo neto combinado de los gases sobre pistón|32,995|4,949 kW|
|Fricción explícita, FMEP 0,85 bar|10,593|1,589 kW|
|Trabajo al eje|22,401|3,360 kW = 4,506 HP|

Las filas son niveles y subconjuntos del balance: **no se suman todas como pérdidas independientes**. El calor del cilindro ya está incluido en el total de paredes. La energía externa es el flujo neto por las fronteras, no la entalpía bruta de escape. La diferencia entre LHV quemado y calor aplicado, **13,009 J**, procede de la eficiencia térmica de combustión prescrita, no de que se queme el 85% del combustible atrapado.

Cierra la primera ley del sistema: ΔU = 73,717672 −14,271533 −34,193439 +1,198841 −26,453005 = **−0,001463 J**. Residuo de esta reducción: **−3,2·10⁻¹² J**. Esto verifica consistencia contable con el ledger guardado; no valida la física ni sustituye una auditoría independiente.

El calor de las paredes del cilindro representa **32,37% del calor aplicado**. Es una dependencia grande de un modelo térmico no identificado. No corresponde convertir esos 23,866 J directamente en potencia recuperable: cambiar transferencia térmica cambia temperaturas, ondas, llenado y trabajo.

La fricción elimina **32,1% del trabajo neto de los gases sobre el pistón**. Con la misma trayectoria y restando cero fricción, el cálculo daría **6,637 HP**, todavía una potencia modesta. Es un contrafactual contable, no una nueva simulación. Por tanto, la fricción no explica por sí sola el gran déficit.

El trabajo negativo de compresión del cilindro (**−54,563 J**) no es enteramente una pérdida de bombeo: parte se recupera en expansión. Una integración aproximada de las muestras de 0,5° separa trabajo con escape abierto **+1,989 J** y cerrado **+32,213 J**; total **34,202 J**, a 0,00856 J del ledger de pasos aceptados. No debe restarse otra vez ese intercambio al trabajo indicado. La pérdida neta directamente identificada del cárter es 1,199 J.

### Presiones y restricciones

Presión absoluta: cárter **0,904–1,333 bar**, cilindro **1,047–47,239 bar**, entrada del escape **0,980–1,108 bar**, mitad del escape **1,040–1,063 bar**. La onda en el conducto resulta débil en esta configuración. No se dispone de una presión medida del mismo motor con la que declarar si está subestimada.

Las áreas máximas registradas son admisión real **960 mm²**, transferencias **256 +256 +174 mm²**, escape **801 mm²**. Son máximos, no áreas abiertas durante todo el ciclo. Los contadores de port_limited incluyen intervalos con puerto cerrado; no prueban estrangulamiento sónico permanente. No existe evidencia suficiente para responsabilizar a una rigidez de lámina concreta: no se realizó el experimento de rigidez cancelado.

## 3. Qué corresponde a configuración y qué corresponde al modelo

|Mecanismo|Evidencia existente|Conclusión y acción técnica|
|---|---|---|
|Configuración|Bore 56, carrera 50,6, cárter de compresión 1,35, escape A/B con 20 mm de diferencia; controles y combustible sintéticos|No es una réplica Honda RS125 ni X30. Debe conservarse como caso funcional, sin trasladar su potencia a todos los 125 cc.|
|Admisión y transferencias|Láminas reducidas, caras abiertas al cárter y control por pistón al cilindro; baja admisión neta medida|Conservar integración, pero para un motor real requieren geometría, rigidez/levantamiento y descarga documentados. No hay prueba de fallo estructural de transporte ni causa única identificada.|
|Barrido|GAS_EXCHANGE_V2 mezcla salida homogénea y desplazamiento preferente de quemados con mixed_outflow_fraction=0,5 sintético; entalpía del donante sigue homogénea|Es un cierre conservativo, no una curva de barrido identificada por geometría. Influye directamente en residual, aire y combustible retenidos; impide un claim predictivo sin caracterización experimental o CFD. La dirección de puertos no determina ese coeficiente.|
|Combustión|Wiebe fija, eficiencia 0,85, combustible sintético y consumo limitado por aire disponible|Produce trabajo positivo coherente con su ley prescrita, pero no predice variación de duración/eficiencia con dilución, riqueza y RPM; el residual no cambia directamente la velocidad Wiebe ni reproduce por sí mismo extinción o química de mezcla rica. Para precisión cuantitativa requiere ley de liberación de calor o presión medida; no multiplicar calor para igualar HP.|
|Transferencia térmica|CONSTANT_H_V1, h=500 en cilindro y pared a 473 K; área lateral fija 0,008902 m² en cada fase|La superficie lateral completa no varía con el pistón: aproximación fuerte cerca de PMS. Para un modelo geométricamente predictivo debe representarse el área mojada instantánea y contrastarse el intercambio/temperaturas, sin suponer que toda la energía ganada se vuelve trabajo. No se cuantificó su sesgo de potencia mediante rerun.|
|Fricción|FMEP explícito constante 0,85 bar; 1,589 kW a 9000|No es fallback silencioso, pero tampoco pérdida medida del motor. Debe identificarse con evidencia; eliminarla no resuelve el bajo llenado.|
|Escape y discretización|Conducto 1D y EOS caloríficamente perfecto; onda registrada y periodicidad global|Conservar núcleo. La convergencia espacial histórica no fue demostrada; no se puede asignar una cota de error a HP ni asegurar que los pequeños deltas A/B superen el error numérico. Periodicidad no es independencia de malla.|

**Separación cuantitativa posible:** carga, energía y pérdidas dentro de la solución calculada. **Separación imposible con esta evidencia:** porcentajes del error frente a un motor real atribuibles a cada cierre físico. Es un problema de identificación: varios mecanismos modifican simultáneamente la misma carga y el mismo trabajo. No se ha demostrado que ajustar uno solo cure la precisión.

## 4. Referencia experimental y decisión sobre una corrida

### Honda RS125 — referencia preferida, datos no accesibles en su integridad

[SAE 2004-01-3561](https://saemobilus.sae.org/papers/validation-a-computer-simulation-a-high-performance-two-stroke-motorcycle-racing-engine-2004-01-3561), Fleck y colaboradores, documenta un estudio de simulación contrastada de una RS125. El resumen público describe medidas de dinamómetro y presión en cilindro/escape a plena carga. El [registro de Queen’s University Belfast](https://pure.qub.ac.uk/en/publications/validation-of-a-computer-simulation-of-a-high-performance-two-str/) confirma la publicación, pero no ofrece un manuscrito descargable en el acceso consultado. No se obtuvo el texto completo ni los datos asociados. Esto es una limitación de acceso, no una afirmación de que los autores no los midieron.

Faltan para reconstruir **ese ensayo**: definición exacta del motor y su escape, puertos y volúmenes, admisión y descarga, condiciones del ensayo y combustible, parámetros de barrido/combustión/fricción empleados y un punto medido con plano de potencia e incertidumbre. Las presiones angulares serían necesarias para localizar el origen del error, aunque no se exige una campaña de cinco RPM para una primera comparación de potencia. Una descripción secundaria de la RS125 no sustituye los datos originales. Las curvas V4 de Boretti 2017 son de otro modelo y no se han usado como dinamómetro Honda.

### Alternativa abierta seleccionada: IAME X30

[Ortenzi y Bossaglia, Energies 16 (2023), 4947](https://www.mdpi.com/1996-1073/16/13/4947) ofrece una referencia pública más accesible: figuras 7–9 con distribución y geometría, y figura 10 con potencia medida y simulada. Se descargó el PDF original y se inspeccionaron visualmente páginas 16–18. Publica encendido a 22° BTDC y lambda 0,85 para su simulación. Sin embargo, el artículo declara restricciones sobre los datos; no entrega el paquete completo de entradas del ensayo. No se identificaron en ese material las curvas de descarga, caracterización de láminas y barrido, volúmenes y condiciones térmicas suficientes para una reproducción sin supuestos. La figura 11 es delivery ratio calculado por su modelo, no una medida independiente que valide el llenado de Dino. Su concordancia simulación/medición no es la precisión de Dino. Como orientación exclusivamente, la curva medida de la figura 10 está alrededor de 16 kW a 9000 RPM (lectura gráfica aproximada, no dato tabulado), frente a nuestros 3,36 kW en un motor diferente: no es un error de predicción calculable.

Es el candidato abierto recomendado para reunir una referencia reproducible; Honda sigue siendo preferible si se obtiene su paquete técnico. No se crea hoy una configuración X30 incompleta presentada como exacta. Una cifra comercial de potencia máxima de otro motor tampoco es un punto experimental comparable a nuestra configuración.

Se examinó además la disponibilidad de la tesis experimental de [Gore, NCSU, 2024](https://repository.lib.ncsu.edu/bitstreams/24433484-a6eb-4ad8-80f1-a18fa75c4ef6/download). El índice público incluye ensayos KT100, pero la descarga directa respondió 503 y no se inspeccionaron métodos completos. No se certifica su suficiencia ni se reabre KT100 con información incompleta.

**Decisión de ejecución: NO EJECUTADA.** Ningún conjunto consultado aporta todavía las entradas suficientes para una reproducción del mismo motor sin inventar parámetros fundamentales. No se calculó un porcentaje de error Dino/experimento. No se confunde una comparación orientativa entre distintos motores con validación.

## 5. Conclusión de cierre

1. El déficit calculado está dominado aguas arriba por aire fresco escaso y alta dilución: sólo 29,69 mg atrapados y unos 2,02 mg quemados a 9000. La térmica y la fricción reducen adicionalmente la conversión al eje. Hay cierre contable, no un error de unidades demostrado.
2. La configuración funcional y sus cierres sintéticos no constituyen todavía un motor experimental reproducido. No se puede decidir a partir de sus 4–5 HP que el núcleo gasdinámico sea inválido, ni declarar que ya predice correctamente un motor real.
3. Conservar solver, integración y flujo Desktop. Las correcciones de precisión identificadas son área térmica instantánea y caracterización del llenado/barrido, descarga, combustión y pérdidas del motor real; su magnitud debe venir de datos, no de HP objetivo. El cierre de barrido actual es la limitación estructural más directa para predecir cambios de puertos, mientras la térmica fija y combustión prescrita limitan la precisión absoluta.
4. El bloqueo actual para una comparación cuantitativa es **REFERENCIA_EXPERIMENTAL_NO_REPRODUCIBLE_CON_DATOS_ACCESIBLES**. El camino acotado es obtener el paquete de un solo motor/punto (preferentemente RS125; alternativa pública X30), fijar sus entradas y contrastar potencia/IMEP y presión sin calibración previa. Sin esas entradas otra corrida sólo mediría otro supuesto.
5. Esta evaluación termina aquí. No se inicia otra campaña, experimento de rigidez, reconstrucción ni calibración. Precisión predictiva: **NO DETERMINADA**. Validación experimental: **NO REALIZADA**.

## Reproducibilidad

`scripts/diagnostics/physical_accuracy_v1.py --output results/physical-accuracy-v1/balance.json` reduce artefactos existentes sin crear motor ni integrar pasos. `balance.json` conserva magnitudes, identidades y hashes. Verifica 29 hashes científicos UTF-8/LF bajo la convención del receipt histórico, conserva además sus hashes de bytes, y compara hashes originales de los 6 resultados, 6 manifests y 6 checkpoints finales, además de los 6 hashes de diagnósticos finales contra sus manifests. No se modificó ningún binding para aceptar diferencias.

El PDF de Energies se conserva fuera de Git bajo el root de artifacts configurado para esta evaluación, con SHA-256 en `sources.json`. Las capturas de sus páginas se usaron para lectura, no como resultados de Dino. Los resultados anteriores mantienen su clasificación exploratoria sin auditoría independiente; las comprobaciones offline de este informe no la convierten en validación.

## Comprobaciones de cierre

- Análisis offline: 7 tests PASS.
- Regresión de los archivos test_p4_* a test_p8_*: 247 PASS, 3 SKIP y 4 advertencias preexistentes de NumPy; 179,75 s. Son pruebas de regresión, no nuevos ensayos científicos.
- OpenSpec: cambio válido y 62 elementos PASS con --all --strict.
- program-status: CHECK OK, promote none, STOP_A_GATE_REACHED; cierre de evaluación, no validación predictiva.
- Los dos BLOCKED_LOCAL heredados (empaquetado interactivo y SPV1) se reevaluaron como ajenos a este objetivo y no impiden la reducción offline; no se reactivaron ni se borraron.
- Un primer lanzamiento del wrapper de OpenSpec falló al no resolver el comando PowerShell como ejecutable; el check se ejecutó correctamente mediante powershell, sin cambiar OpenSpec.
- Históricos y cambios locales ajenos conservados; commit local focal, sin push.
