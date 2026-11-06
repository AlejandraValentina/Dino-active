# four-stroke-rpm-curve-v1 Specification

## Purpose
Definir la curva RPM 4T de referencia en Dino, reutilizando el sweep y el
manifiesto 4T existentes, con lectura estricta de la serie y sin comparación
con 2T ni claim de validación experimental.
## Requirements
### Requirement: Barrido RPM 4T validado
El sistema SHALL construir una serie 4T de 2 a 5 puntos con RPM enteros
2500–3500, usando `reference_results.project_inputs`, `sweep.plan_rpms` y el
worker existente con `--sweep-input`. SHALL rechazar listas no exactas, fuera
de dominio o fuera del presupuesto antes de iniciar.

#### Scenario: Serie válida
- **WHEN** se piden 2500/3000/3500 rpm
- **THEN** el adaptador genera una solicitud `{common_inputs, rpms}` y lanza
  `reference_run --sweep-input` sin bloquear la interfaz.

#### Scenario: Serie inválida
- **WHEN** los RPM no son enteros, están fuera de 2500–3500 o la lista no es
  exacta
- **THEN** se rechaza con un motivo legible y no se inicia el worker.

### Requirement: Lectura estricta de la serie
El sistema SHALL leer `series.json` con `sweep.load_sweep` y SHALL validar
identidad, hashes, manifiestos v4, estados y suma de tiempos. SHALL NOT
presentar una serie parcial o alterada como curva completa.

#### Scenario: Serie alterada
- **WHEN** falta un manifiesto de punto, cambia un hash o un estado contradice
  la serie
- **THEN** la UI muestra el error y no grafica como si fuera válida.

### Requirement: Curva RPM 4T en Dino
El sistema SHALL mostrar una página 4T separada con inicio/fin/incremento,
estado, cancelación, tabla por RPM y gráfico `W_C_J` vs RPM, etiquetada
`SYNTHETIC_REFERENCE_0D · NOT_VALIDATED`. SHALL NOT comparar 2T con 4T ni
introducir variantes o estudios de diseño en este change.

#### Scenario: Curva terminada
- **WHEN** la serie termina con todos los puntos convergidos
- **THEN** la tabla y el gráfico muestran los puntos y el estado real de la
  serie; no se atribuye validación experimental.

### Requirement: No regresión y alcance
El sistema SHALL conservar intactos el proyecto 4T B1.1, el proyecto V3 2T, el
solver 2T y los resultados históricos. La verificación SHALL incluir tests del
adaptador, la UI, una serie real acotada y la regresión focalizada 4T/V3.

#### Scenario: Cierre del change
- **WHEN** se ejecutan las suites del change
- **THEN** 2T/V3 siguen pasando y la curva 4T queda cubierta por sus propias
  pruebas.

