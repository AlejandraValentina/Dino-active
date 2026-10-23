# X30 Senior — lectura aproximada de la curva publicada

Fuente: [Ortenzi y Bossaglia, Energies2023, figura10, p.18](https://www.mdpi.com/1996-1073/16/13/4947), DOI10.3390/en16134947. Se lee exclusivamente la línea naranja X30 Meas; se excluyen triángulos grises del modelo y ambas series Junior.

**No son mediciones originales ni se conocen las RPM de adquisición.** Son lecturas de una curva unida por segmentos. Una lectura a9000RPM puede caer entre muestras originales no identificables; no recupera un registro independiente de banco a esa RPM.

|RPM de lectura|Potencia aproximada kW|Cota de digitalización|Procedencia|
|---:|---:|---|---|
|6500|8.1|±0,3 kW|Figura10, línea naranja X30 Meas|
|7000|9.0|±0,3 kW|Figura10, línea naranja X30 Meas|
|7500|10.1|±0,3 kW|Figura10, línea naranja X30 Meas|
|8000|11.0|±0,3 kW|Figura10, línea naranja X30 Meas|
|8500|12.9|±0,3 kW|Figura10, línea naranja X30 Meas|
|9000|15.1|±0,3 kW|Figura10, línea naranja X30 Meas|
|9500|17.4|±0,3 kW|Figura10, línea naranja X30 Meas|
|10000|19.1|±0,3 kW|Figura10, línea naranja X30 Meas|
|10500|20.4|±0,3 kW|Figura10, línea naranja X30 Meas|
|11000|20.9|±0,3 kW|Figura10, línea naranja X30 Meas|
|11500|21.3|±0,3 kW|Figura10, línea naranja X30 Meas|
|12000|21.3|±0,3 kW|Figura10, línea naranja X30 Meas|
|12500|20.7|±0,3 kW|Figura10, línea naranja X30 Meas|
|13000|19.5|±0,3 kW|Figura10, línea naranja X30 Meas|
|13500|18.2|±0,3 kW|Figura10, línea naranja X30 Meas|
|14000|16.9|±0,3 kW|Figura10, línea naranja X30 Meas|
|14500|16.8|±0,3 kW|Figura10, línea naranja X30 Meas|
|15000|16.5|±0,3 kW|Figura10, línea naranja X30 Meas|
|15500|16.3|±0,3 kW|Figura10, línea naranja X30 Meas|
|16000|16.2|±0,3 kW|Figura10, línea naranja X30 Meas|

## Incertidumbre y reproducción

La cota±0,3kW es conservadora para esta digitalización; **no es U95 ni la incertidumbre del dinamómetro**. Incluye selección/calibración vertical±7píxeles, horizontal±3píxeles con la pendiente local y redondeo±0,05kW. El eje horizontal tiene una cota de lectura±20RPM, ya considerada en la cota de potencia, no una precisión conocida del tacómetro. La banda cubre lectura de la línea, no el error de interpolación que pudiera existir entre muestras experimentales originales.

Se ensamblaron, sin reescalar, las imágenes originales del PDF página18: xref410 (2136×930) y411 (2136×464). Se calibraron seis marcas por eje; se ajustó localmente la línea naranja en ventanas pequeñas, ampliadas ante ocultación por marcadores del modelo. En el extremo6500 y cerca de marcadores se prolonga localmente el trazo visible dentro de esa ventana; no se extrapola fuera del rango publicado. Calibración, coordenadas por lectura, hashes y método están en figure10-digitized.json.

La lectura precisa a9000 da **15,1kW** y sustituye, para este uso aproximado, la orientación visual anterior de alrededor de16kW. El informe histórico se conserva sin alteración. No se deriva una columna de torque como si fuese una medición independiente.

Uso admisible: magnitud, forma y posición aproximada del máximo publicado (aproximadamente21,3kW entre11500–12000RPM), y futuro contraste preliminar claramente identificado. Uso no admisible: ajuste de coeficientes a estos valores o aprobación de precisión predictiva con esta cota como incertidumbre experimental.
