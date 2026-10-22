# STANDARD_V1 125 cc Blair/Cartwright

## Configuración propuesta, protocolo de ejecución y criterios de evaluación

### 0. Estado y alcance

- **Estado:** configuración verificada; primera ejecución exploratoria autorizada,
  resultado en `results/integrated-solver-verification-v1/standard-v1-9000-report.md`.
- **Alcance autorizado actual:** configuración, runner mínimo y primer punto
  exploratorio a 9000 RPM, según §9 y autorización del propietario.
- **Fuera de alcance:** modificar el solver, cambiar la arquitectura,
  calibrar coeficientes para obtener una
  potencia objetivo, lanzar un barrido RPM completo o afirmar capacidad
  predictiva.
- **Regla de honestidad:** ninguna banda de plausibilidad de este documento es
  un objetivo de calibración. Si un resultado cae fuera de banda, se diagnostica
  la causa; no se ajusta un coeficiente para entrar en ella.
- **Configuración:** `configs/reference_cases/standard_v1_125cc_blair_cartwright.json`
- **Builder reproducible:** `scripts/build_standard_v1_125cc.py`
- **SHA-256 del JSON generado:** `301ded4ca6df997a3207e99aef37ee5a2702c782d15aacd50cfec32993d0ed08`

Verificación sin ejecutar el solver:

```powershell
python scripts/build_standard_v1_125cc.py --check
```

---

## 1. Referencia y corrección de la compresión

### 1.1 Fuente principal

Blair, G. P., *Design and Simulation of Two-Stroke Engines*, SAE, 1996,
Sec. 5.5.2 (motor de 125 cc Blair/Cartwright), Sec. 6.1–6.2 (diseño de
conductos y expansión) y Sec. 5.5.2/6.2.4–6.2.6 (combustión, válvula de escape
y prestaciones). La copia local usada para la extracción no se versiona; la
referencia bibliográfica es la fuente primaria.

La referencia es un motor de competición de 125 cc, no un motor de calle. El
objetivo de `STANDARD_V1` es una configuración representativa y documentada, no
una réplica exacta de una moto de serie.

### 1.2 Geometría documentada

| Parámetro | Valor | Procedencia |
|---|---:|---|
| Diámetro | 56.0 mm | Blair Sec. 5.5.2 |
| Carrera | 50.6 mm | Blair Sec. 5.5.2 |
| Biela | 110.0 mm | Blair Sec. 5.5.2 |
| Cilindrada | 124.628 cc | cálculo geométrico |
| CR atrapada de referencia | 9.0, con cierre del escape a 81° BTDC | Blair Sec. 5.5.2 |
| CR cárter | 1.35 | Blair Sec. 5.5.2 |
| Volumen cárter en BDC | 356.081 cc | `Vd/(1.35-1)` |
| Volumen cárter en TDC | 480.709 cc | BDC + Vd |

### 1.3 Corrección importante de la CR geométrica

La fórmula correcta de posición del pistón es la ya implementada en
`motorsim.kinematics.piston_position`:

```text
x(θ) = r·(1 - cos θ) + r·λ·sin²θ / (1 + sqrt(1 - (λ·sin θ)²))
λ = r / L
```

donde `r = carrera/2` y `L` es la biela. Los valores correctos para este motor
son:

| Cierre del escape | `x` (mm) | CR atrapada con `CR_geom = 17.714769879` |
|---:|---:|---:|
| 81° BTDC (279° ATDC) | 24.218102 | 9.000000 |
| 85° BTDC | 26.021283 | 9.595647 |
| 90° BTDC | 28.249031 | 10.331542 |
| 95° BTDC | 30.431364 | 11.052436 |
| 100° BTDC | 32.552219 | 11.753021 |
| 105° BTDC | 34.597071 | 12.428500 |
| 110° BTDC | 36.552987 | 13.074600 |

La tabla de Blair para cierres de 85, 90, 95, 100, 105 y 110° BTDC es
9.6, 10.3, 11.1, 11.8, 12.4 y 13.1. La coincidencia con la última columna
valida la geometría y la CR geométrica.

**Aclaración de semántica:** el escape **abre** a 81° ATDC y **cierra** a 279°
ATDC, que es 81° BTDC. La CR atrapada se define por el cierre, no por la
apertura. Por la simetría del mecanismo, `x(81° BTDC) = x(279° ATDC) = x(81°
ATDC)`, pero el evento físico que atrapa la carga es el cierre. Decir “cierre a
81° ATDC” es incorrecto aunque el valor numérico de `x` coincida.

**Corrección respecto de un cálculo previo:** los valores `x(95) = 27.528 mm`
y `CR_geom = 15.705` eran incorrectos; provenían de una racionalización errónea
de la fórmula de posición. Los valores correctos son `x(95) = 30.431364 mm` y
`CR_geom = 17.714769879`. El motor tiene una CR geométrica alta precisamente
porque el escape permanece abierto durante una fracción grande de la carrera
de compresión; la CR atrapada es 9.0 con la válvula abierta y sube a ~11.1 con
la válvula completamente bajada.

La CR geométrica se obtiene de la condición documentada de 9.0 con el escape
cerrando a 81° BTDC:

```text
CR_geom = 1 + (CR_atrapada - 1) · S / x(81)
        = 1 + 8 · 50.6 / 24.218102
        = 17.714769879
```

El volumen de cámara es:

```text
Vc = Vd / (CR_geom - 1) = 124.628237 / 16.714769879 = 7.456174 cc
```

### 1.4 Válvula de escape y punto de 9000 RPM

El mapa de la válvula es una **suposición lineal**, porque no se dispone del
mapa real:

```text
posición = 1.0 (completamente bajada) a 8500 RPM
posición = 0.0 (completamente levantada) a 9500 RPM
```

A 9000 RPM resulta `posición = 0.5`. El techo efectivo del escape es entonces:

```text
top_9000 = x(81) + 0.5 · (x(95) - x(81))
         = 27.324733 mm
```

Consecuencias:

| Magnitud a 9000 RPM | Valor |
|---|---:|
| Apertura del escape | 87.915283° ATDC |
| Cierre del escape | 272.084717° ATDC |
| Duración del escape | 184.169434° |
| CR atrapada | 10.026218 |

La válvula completamente bajada daría apertura 95° ATDC y CR atrapada 11.052;
la completamente levantada daría 81° ATDC y CR 9.0. El valor 10.026 es
intermedio y es el que se usa en el primer punto.

---

## 2. Configuración

### 2.1 Puertos

`PortDefinition.area_at` devuelve el área **efectiva** (geométrica multiplicada
por el coeficiente de descarga). Las áreas geométricas se obtienen dividiendo
por `Cd`.

| Puerto | Apertura / cierre | Ancho | Altura | `Cd` | Área efectiva máxima |
|---|---:|---:|---:|---:|---:|
| Admisión (`inlet-window`) | ventana amplia; ver 2.1.1 | 38.0 mm | 36.0 mm | 0.85 | 1162.800 mm² |
| Transfer primario | 115° / 245° ATDC | 30.0 mm | 12.191372 mm | 0.70 | 256.019 mm² |
| Transfer secundario | 115° / 245° ATDC | 30.0 mm | 12.191372 mm | 0.70 | 256.019 mm² |
| Boost | 115° / 245° ATDC | 20.4 mm | 12.191372 mm | 0.70 | 174.093 mm² |
| Escape principal | 81° / 279° ATDC (válvula abierta); 95° / 265° (bajada) | 43.0 mm | 26.381898 mm | 0.80 | 907.537 mm² |

El transfer total efectivo es `256.019 + 256.019 + 174.093 = 686.131 mm²`.
El área geométrica máxima del escape es `43 × 26.381898 = 1134.422 mm²`; con
`Cd = 0.8` resulta 907.537 mm². El área geométrica máxima del transfer total es
`80.4 × 12.191372 = 980.186 mm²`; con `Cd = 0.7` resulta 686.130 mm².

#### 2.1.1 Admisión: aproximación deliberada

El solver no tiene una familia de puerto específica para reed; la admisión debe
declararse como `piston_port`. Se usa una ventana amplia que no limita en su apertura máxima, aunque sí
puede limitar en aperturas parciales:

```text
top = 56.0 mm
height = 36.0 mm
width = 38.0 mm
skirt = 42.0 mm
d = top + height - skirt = 50.0 mm  (< carrera 50.6 mm)
```

La ventana está abierta desde 194.23° hasta 165.77° (cruza TDC). El área es
plena entre 302.01° y 57.99°, se reduce hasta cerrar en 165.77° y vuelve a
abrir en 194.23°. Es una ficción para aproximar un cárter controlado por reed:
la ventana tiene un máximo mayor que el conducto, pero SÍ puede limitar el
flujo durante su apertura parcial. El área usada es el mínimo entre ventana,
seis pétalos cuasiestáticos y conducto. No representa una admisión reed pura. Esta es una limitación
estructural del modelo, no una propiedad del motor real.

La alternativa de usar una ventana de 14 mm de altura abriría solo ~268° y
podría representar mejor el cierre del reed, pero limitaría el área a 452.2 mm²
efectivos y convertiría la ventana en el choke. Para el primer punto se prioriza
el flujo y se documenta la ficción.

### 2.2 Conductos y expansión

Se usa la expansión A2 documentada del motor, no el ejemplo empírico de la
Fig. 6.22 (ese ejemplo es un ejercicio de diseño, no la pipa del motor de
referencia).

| Tramo | Longitud | Diámetro inicial | Diámetro final |
|---|---:|---:|---:|
| L1 | 83 mm | 37.5 mm | 37.5 mm |
| L2 | 189 mm | 37.5 mm | 48.5 mm |
| L3 | 209 mm | 48.5 mm | 100.0 mm |
| L4 | 65 mm | 100.0 mm | 116.0 mm |
| L5 | 78 mm | 116.0 mm | 116.0 mm |
| L6 | 205 mm | 116.0 mm | 21.0 mm |
| L7 | 250 mm | 21.0 mm | 21.0 mm |

Longitud total: 1079 mm. Longitud sintonizada L1–L6: 829 mm; con el puerto,
~832 mm. La malla usa `dx_target = 0.040 m`, lo que produce 31 celdas.

Conductos de transfer:

| Conducto | Celdas | Longitud | Área |
|---|---:|---:|---:|
| Primario | 3 | 50 mm | 365.742 mm² geométrica |
| Secundario | 3 | 50 mm | 365.742 mm² geométrica |
| Boost | 3 | 50 mm | 248.704 mm² geométrica |
| Admisión | 4 | 80 mm | Ø38 mm |

Las áreas de los conductos de transfer se hacen coincidir con el área
geométrica máxima del puerto respectivo, no con el área efectiva.

### 2.3 Reed

| Parámetro | Valor | Procedencia |
|---|---:|---|
| Pétalos | 6 | Blair |
| Masa por pétalo | 6.9e-4 kg | estimación |
| Área de presión | 8.626e-4 m² | estimación |
| Ancho efectivo | 0.0227 m | Blair |
| Rigidez efectiva | 1000 N/m | `SYNTHETIC_ASSUMPTION` |
| Amortiguamiento | 0.5 N·s/m | `SYNTHETIC_ASSUMPTION` |
| Tope de levantamiento | 0.013 m | Blair |
| `Cd` | 0.80 | `SYNTHETIC_ASSUMPTION` |

El modelo actual es cuasi-estático: usa rigidez y presión, pero no integra masa
ni amortiguamiento. La frecuencia natural estimada es ~197 Hz y el damping
ratio ~0.31, pero no se usan en el cálculo. La rigidez efectiva no es una
medición del pétalo real.

### 2.4 Combustión y combustible

| Parámetro | Valor | Procedencia |
|---|---:|---|
| Modelo | `FuelCoupledCombustionV1` | solver |
| Componente | Wiebe, peso 1.0 | Blair |
| Retardo | 12° | Blair |
| Duración | 41° | Blair |
| `a` / `m` | 5.25 / 1.25 | Blair |
| Encendido | 340° (20° BTDC) | Blair |
| Eficiencia de combustión | 0.85 | Blair |
| AFR de referencia | 11.5 | Blair |
| Combustible | C 0.86, H 0.14, LHV 43 MJ/kg | surrogate sintético reutilizado |
| AFR estequiométrico | 14.7126 | surrogate |

La mezcla atmosférica se declara `(0.92, 0.08, 0, 0)` en fracciones másicas,
equivalente a AFR 11.5. No se usa el `(0.98, 0.02)` del fixture B, que producía
AFR 49 y era una de las causas del comportamiento no representativo.

### 2.5 Térmica, fronteras y estado inicial

| Elemento | Valor | Procedencia |
|---|---:|---|
| Pared cilindro | 473 K, `h=500 W/m²K` | temperatura Blair; `h` representativo |
| Culata | 473 K, `h=500` | idem |
| Corona del pistón | 473 K, `h=500` | idem |
| Cárter | 353 K, `h=50` | temperatura Blair; `h` representativo |
| Paredes del escape | 623 K, `h=50` por celda | temperatura Blair; `h` representativo |
| Paredes de admisión/transfer | omitidas | limitación del modelo |
| Fronteras | `open_end_plenum_v2`, 101325 Pa, 300 K | solver |
| Especies del outlet | aire `(1,0,0,0)` | supuesto |
| `R` / `gamma` | 287 / 1.35 | solver |
| `max_cfl` | 0.4 | solver |
| `reference_rpm` | 9000 | punto de diseño |

Estado inicial:

- Cárter en TDC con mezcla fresca (0.92 aire / 0.08 combustible).
- Cilindro en TDC con 50% mezcla fresca y 50% residual.
- Admisión y transfers a 300 K con mezcla fresca.
- Escape a 600 K y densidad 0.588 kg/m³ con residual.

Este estado no es un ciclo convergido: es una condición inicial reproducible.
Los primeros ciclos son transitorios y no se usan para conclusiones.

### 2.6 Malla

| Región | Celdas | Resolución |
|---|---:|---|
| Admisión | 4 | 80 mm |
| Transfer primario | 3 | 50 mm |
| Transfer secundario | 3 | 50 mm |
| Boost | 3 | 50 mm |
| Escape | 31 | `dx = 40 mm` |

La malla de escape es más fina que la del fixture B (7 celdas). El costo por
ciclo todavía no está medido para esta configuración.

---

## 3. Justificación de las decisiones

### 3.1 Geometría y compresión

La geometría no se deriva de porcentajes genéricos: se toma del motor
documentado. La CR geométrica 17.7148 no es un valor arbitrario; es la que
reproduce la tabla de CR atrapada de Blair para cierres de 85–110° BTDC. La
coincidencia de los seis valores es una validación fuerte de la cinemática y de
la interpretación de la válvula.

### 3.2 Puertos

- Escape de 43 mm: `43/56 = 0.768`, cerca del criterio de competición ~75% del
  diámetro. El motor real tiene una ventana irregular 40–53–40; se simplifica a
  una ventana rectangular de 43 mm. Esto reduce la fidelidad del blowdown y se
  documenta como incertidumbre.
- Transfer total de 80.4 mm: `80.4/56 = 1.436`, por encima de la banda
  genérica 1.2–1.35 de Blair. Se conserva el valor documentado del motor; no se
  ajusta para cumplir una regla genérica. La consecuencia es una mayor área de
  transfer y un barrido potencialmente más agresivo.
- Admisión de 38 mm: `38/56 = 0.679`, cerca del criterio ~65%. La ventana de
  36 mm de altura es una aproximación por la limitación `piston_port` del
  solver.

### 3.3 Expansión

Se elige la expansión A2 documentada porque es la que corresponde al motor de
referencia. La expansión empírica de la Fig. 6.22 se usa solo como control de
proporciones (`LT ≈ 83.3·a0·θep/RPM`), no como geometría del motor. Mezclar
ambas produciría una configuración incoherente.

### 3.4 Combustión

Los parámetros de Wiebe, retardo, duración, encendido y eficiencia son los
documentados para este motor. El AFR 11.5 es rico, como corresponde a un 2T de
competición refrigerado por carga. El surrogate de combustible es una
aproximación: no reproduce exactamente la volatilidad, el knock ni la
composición del combustible real.

### 3.5 Térmica

Las temperaturas de pared son las documentadas por Blair. Los coeficientes `h`
son representativos, no medidos. La pared del escape se aplica por celda con
`h=50 W/m²K`; esto puede enfriar la onda de escape y afectar la sintonía. Es una
de las primeras sensibilidades a revisar si el comportamiento es anómalo.

### 3.6 Estado inicial y malla

El estado inicial es una condición reproducible, no un ciclo periódico. La
malla de 31 celdas en el escape busca resolver la onda; la comparación con una
malla más gruesa o más fina es parte del protocolo, no una campaña.

---

## 4. Limitaciones del modelo

Estas limitaciones son estructurales y deben acompañar cualquier conclusión:

1. **Cilindro 0D bien mezclado.** No hay estratificación espacial ni
   conservación de la calidad del barrido de loop-scavenge. Las métricas de
   scavenging son post-proceso, no un modelo físico de la interfaz fresca/
   residual. Esta es la diferencia principal frente a EngMod2T/MOTA.
2. **Admisión `piston_port`.** El reed se monta sobre una ventana de pistón
   amplia; la apertura real del reed no se representa con una familia de puerto
   dedicada.
3. **Reed cuasi-estático.** No integra masa ni amortiguamiento; la rigidez es
   sintética.
4. **Un solo escape principal.** No hay ventana auxiliar ni geometría
   irregular 40–53–40; el blowdown y el área temprana quedan simplificados.
5. **Válvula de escape lineal.** El mapa 8500/9500 es una suposición; no se
   conoce el mapa real.
6. **Térmica representativa.** `h` y algunas áreas no están medidos; no hay
   paredes de admisión/transfer.
7. **Estado inicial no convergido.** Los primeros ciclos son transitorios.
8. **Sin datos de dyno del motor real.** No se puede afirmar precisión
   absoluta ni validación experimental.
9. **Transfers con ambos extremos restringidos.** El solver aplica la misma
   área variable a los extremos de cárter y cilindro. No representa un transfer
   permanentemente conectado al cárter. Se registran flujos por ambos extremos
   y tiempo limitado por área, sin modificar esa ecuación.
10. **Malla de escape no medida en costo.** 31 celdas pueden ser costosas.

Nada de esto convierte el modelo en inútil: permite estudiar tendencias y
mecanismos, pero no reemplaza una validación experimental.

---

## 5. Protocolo de ejecución del primer punto (9000 RPM)

### 5.0 Runner necesario

El runner `scripts/run_standard_exploratory_point.py` carga el JSON V5 y
ejecuta directamente un punto. La ejecución autorizada se precisa en §9.
Contrato mínimo:

- Carga el JSON con `IntegratedEngine2T.from_configuration_dict`.
- Fija el RPM del punto y no muta la configuración.
- Ejecuta ciclos completos y guarda un snapshot por ciclo.
- Registra las métricas de 5.4 y los residuos de conservación.
- Persiste checkpoints nativos restaurables sin cambiar el estado físico; el
  runner mínimo no implementa un CLI de resume ni reintentos automáticos.
- Escribe un manifiesto con SHA-256 del config, commit y parámetros.

El runner se implementa separadamente; no modifica el solver.

### 5.1 Preflight

1. Verificar que el árbol de trabajo no tenga cambios no intencionales en el
   solver. Registrar commit y `git status`.
2. Ejecutar `python scripts/build_standard_v1_125cc.py --check`.
3. Verificar el SHA-256 del JSON contra
   `301ded4ca6df997a3207e99aef37ee5a2702c782d15aacd50cfec32993d0ed08`.
4. Verificar que `IntegratedEngine2T.from_configuration_dict(config)` reproduce
   el mismo `configuration_dict()` (lo hace el builder).
5. Autorización explícita recibida para smoke y único punto de §9.
6. Registrar Python, versión del repo, sistema operativo y configuración de
   `max_cfl`.

### 5.2 Inicialización y convergencia

- Punto: 9000 RPM, `reference_rpm=9000`, válvula en posición 0.5.
- Se parte del estado inicial definido en 2.5.
- Un ciclo = 360° de cigüeñal.
- No se asume que 5–8 ciclos sean suficientes.

Criterio de convergencia, evaluado después de al menos 10 ciclos:

| Métrica | Cambio relativo máximo entre ciclos consecutivos |
|---|---:|
| Masa fresca atrapada | < 1% |
| Combustible atrapado | < 1% |
| IMEP | < 2% |
| Presión máxima | < 2% |
| Relación de entrega (DR) | < 2% |
| Eficiencia de atrapamiento (TE) | < 2% |
| Trabajo por ciclo | < 2% |
| BSFC | < 3% |

Se exigen **3 ciclos consecutivos** dentro de esos límites. Si no se alcanza
antes de 30 ciclos, se detiene el punto y se diagnostica; no se declara
convergido ni se ajustan coeficientes para forzarlo.

### 5.3 Conservación y estabilidad

En todos los ciclos:

- Residuo relativo de masa, energía y especies < `1e-8` (el solver ya reporta
  `1e-13` en casos sanos; `1e-8` es un límite de aceptación, no un objetivo).
- Ninguna fracción másica negativa.
- Ningún paso rechazado de forma repetida por CFL.
- Presión y temperatura finitas, sin `NaN`/`Inf`.
- Caudal másico y áreas de puerto no negativos.

Si falla conservación o estabilidad, se detiene y se diagnostica; no se
continúa “hasta que converja”.

### 5.4 Métricas por ciclo

Se registran, como mínimo:

- Masa fresca entregada, atrapada y cortocircuitada.
- Combustible entregado, atrapado y quemado.
- Residual atrapado.
- Relación de entrega, eficiencia de atrapamiento, eficiencia de carga,
  eficiencia de barrido.
- Presión y temperatura máximas; ángulo de presión máxima.
- IMEP, PMEP, trabajo indicado, trabajo de bombeo, fricción, potencia
  indicada/freno, BMEP, BSFC.
- Temperatura de escape y presión media de escape.
- Fracción de short-circuit y composición del escape.
- Áreas efectivas de admisión, transfer y escape en los ángulos clave.

### 5.5 Bandas de plausibilidad (no objetivos de calibración)

Estas bandas son controles de cordura para detectar un modelo mal configurado,
no metas de potencia:

| Métrica | Banda amplia esperada |
|---|---:|
| Masa fresca atrapada | 0.06–0.15 g/ciclo |
| Combustible atrapado | 0.005–0.013 g/ciclo |
| Relación de entrega | 0.7–1.2 |
| Eficiencia de atrapamiento | 0.50–0.85 |
| Presión máxima | 4.5–8.0 MPa |
| Temperatura máxima | 2200–2900 K |
| IMEP | 800–1300 kPa |
| PMEP | 20–200 kPa |
| BMEP | 700–1000 kPa |
| Potencia de freno | 13–20 kW |
| BSFC | 300–550 g/kWh |
| Temperatura de escape | 700–1000 K |

Si un valor cae fuera, se investiga: ¿estado inicial?, ¿malla?, ¿térmica?,
¿reed?, ¿válvula?, ¿combustión? No se modifica el parámetro para “acercarlo” a
la banda.

### 5.6 Sensibilidad mínima

No se lanza una matriz completa. Se hace una comparación acotada:

1. **Malla:** baseline `dx = 40 mm` (31 celdas) contra `dx = 20 mm` (o 60 mm),
   mismo CFL. Comparar IMEP, masa atrapada, presión máxima y DR; diferencia
   objetivo < 5%.
2. **Tiempo:** `max_cfl = 0.4` contra `0.2`, misma malla. Comparar las mismas
   métricas; diferencia objetivo < 2%.

Si la diferencia es mayor, se refina y se repite; no se reduce CFL ni precisión
para ahorrar tiempo. La sensibilidad se hace después de que el baseline
converja, no durante el transitorio.

### 5.7 Costo y presupuesto

- Costo previo de referencia: ~104.5 s por ciclo con 7 celdas de escape en el
  fixture B; ~142.9 s para el ciclo primary; ~235.7 s con auditoría; ~3.6 s de
  serialización.
- Con 31 celdas de escape se espera un costo por ciclo 2–4× mayor. Estimación
  inicial: 200–400 s/ciclo.
- 20 ciclos: ~1.1–2.2 h. El presupuesto de campaña de 60 min puede excederse;
  usar checkpoints y dividir la ejecución.
- El modo exploratorio excluye `make_integrated_cycle_primary`, auditoría
  completa y serialización pesada (~70% del costo). El modo claim las incluye.
- Si el costo proyectado excede el presupuesto, se registra como
  `BLOCKED_LOCAL` de performance; no se baja CFL, precisión ni umbrales.

### 5.8 Condiciones de parada

Detener el punto y diagnosticar si:

- Falla conservación de masa/energía/especies.
- Aparecen especies negativas o estados no finitos.
- Hay rechazos CFL repetidos.
- No converge en 30 ciclos.
- La presión o temperatura es físicamente absurda y no se explica por el
  transitorio.
- El costo excede el presupuesto sin checkpoint.

No se “arregla” ninguno de estos casos ajustando coeficientes de combustión,
`Cd`, `h` o reed para obtener una curva deseada.

### 5.9 Entregables del punto

- Configuración usada y su SHA-256.
- Manifiesto de ejecución: commit, Python, OS, CFL, malla, fecha.
- Ledger por ciclo y resumen de convergencia.
- Métricas en JSON/CSV y gráficos de presión, temperaturas, masas y áreas.
- Informe breve con: qué se observó, qué es robusto, qué es incierto y qué
  limitación del modelo explica cada anomalía.

---

## 6. Criterios de evaluación

### 6.1 Primario: integridad y plausibilidad

1. Conservación y estabilidad dentro de los límites.
2. Convergencia de ciclo dentro de los criterios de 5.2.
3. Coherencia geométrica: CR atrapada, timing, áreas y volúmenes.
4. Plausibilidad física de presión, temperatura, masas y trabajo.
5. Ausencia de patologías numéricas no explicadas.

### 6.2 Secundario: sensibilidad y costo

1. Diferencia de malla < 5% en las métricas clave.
2. Diferencia temporal < 2%.
3. Costo por ciclo y por punto dentro del presupuesto, con checkpoints.
4. Tendencias cualitativas estables (no “ruido” de un ciclo a otro).

### 6.3 Terciario: validación externa

1. Comparación con datos de dyno del motor real, si se consiguen.
2. Comparación con casos Blair/Cartwright publicados.
3. Comparación con EngMod2T/MOTA, entendiendo que la diferencia de modelo de
   scavenging explica parte de la discrepancia.

Sin datos externos, **no se declara validación predictiva**. El primer punto es
un ejercicio de coherencia y sensibilidad, no una prueba de potencia absoluta.

### 6.4 No objetivos

- No igualar una potencia objetivo.
- No calibrar coeficientes para que la curva “se vea bien”.
- No declarar PASS por conservación.
- No extrapolar a todo el rango RPM con un solo punto.
- No presentar el resultado como validación experimental.

---

## 7. Incertidumbres y procedencia

| Parámetro | Valor | Procedencia | Impacto | Cómo reducir |
|---|---:|---|---|---|
| Rigidez del reed | 1000 N/m | sintética | timing/área de admisión | medición o modelo dinámico |
| Masa/amortiguamiento del reed | 6.9e-4 kg / 0.5 | estimación | respuesta dinámica | medición |
| `Cd` de admisión | 0.85 | supuesto | caudal | medición en flujo |
| `Cd` de transfer | 0.70 | supuesto | barrido | medición/CFD |
| `Cd` de escape | 0.80 | supuesto | blowdown | medición/CFD |
| Mapa de válvula | 8500/9500 lineal | supuesto | CR y timing | mapa real |
| `h` cilindro | 500 W/m²K | representativo | presión/temperatura | correlación o medición |
| `h` escape | 50 W/m²K | representativo | sintonía | correlación o medición |
| Paredes admisión/transfer | omitidas | limitación | temperatura del aire | modelo térmico adicional |
| Estado inicial | 50/50 cilindro | supuesto | transitorio | convergencia de ciclos |
| Scavenging | 0D bien mezclado | limitación | TE/DR/short-circuit | modelo multi-zona |
| Ventana de admisión | 38×36 mm | aproximación | flujo | familia de puerto reed |
| Escape | una ventana 43 mm | simplificación | blowdown | ventana irregular/auxiliar |
| Combustible | surrogate C/H | aproximación | LHV/knock | combustible real |
| Malla de escape | 31 celdas | elección | costo/precisión | estudio de malla |
| Datos de dyno | ausentes | bloqueo | validación | campaña experimental |

---

## 8. Reproducibilidad

- `scripts/build_standard_v1_125cc.py` construye la configuración sin ejecutar
  el solver y falla si la CR, el timing, la malla o el roundtrip no coinciden.
- `configs/reference_cases/standard_v1_125cc_blair_cartwright.json` es el
  artefacto generado.
- El builder no usa rutas absolutas locales; el JSON tampoco las contiene.
- Cualquier cambio de geometría, puerto, reed, térmica o malla debe regenerar el
  JSON y actualizar el SHA-256 en este documento.

### Comando de verificación

```powershell
python scripts/build_standard_v1_125cc.py --check
```

Salida esperada (resumen):

```text
geometry Vd=124.628237 cc, VbdC=356.080678 cc, CRgeom=17.714769879
compression CR81=9.000000000, CR95=11.052435625, CR9000=10.026217812
mesh intake=4, primary=3, secondary=3, boost=3, exhaust=31
powervalve 9000=0.500, exhaust_open=87.915283 deg ATDC
```

---

## 9. Primera ejecución exploratoria autorizada (2026-10-22)

El propietario autorizó implementar el runner mínimo y ejecutar sólo 9000 RPM.
No modifica el solver, geometría, coeficientes, AFR ni combustión.

- Runner: `scripts/run_standard_exploratory_point.py`.
- Smoke aislado: 5 grados, máximo 30 s; no es un ciclo ni se reutiliza como resultado.
- Punto: máximo 30 ciclos / 1800 s de pared, secuencial, 3072 MiB RSS.
- Configuración exacta: SHA-256 indicado en este documento; 44 celdas totales.
- Evidencia externa; manifiesto atómico y checkpoint nativo compacto por ciclo.
- Sin primarias, replay ni auditoría independiente. Los residuos de conservación
  son comprobaciones internas del productor; NO equivalen a una auditoría.
- Usa los flujos SSPRK existentes con cuadratura de sus dos etapas; no ejecuta
  un segundo solver para obtener diagnósticos. Series compactas cada ~0.5°.
- La selección mecánica `standard-v1` es explícita, de postproceso: 85000 Pa,
  `SYNTHETIC_ASSUMPTION`, modelo existente, no fricción medida de Blair. No altera
  el estado físico. Potencia de freno y BSFC resultantes son estimaciones.
- Se compara con `compare_cycles_v2` existente, sin alterar umbrales: todo el
  estado terminal de cámaras/conductos/especies, flujos integrados y trabajo.
  Periodo 1 requiere tres comparaciones consecutivas satisfactorias y al menos
  diez ciclos. Esta comprobación exploratoria no sustituye la validación
  completa ni identifica TE/CE/SE; el cuadro previo de métricas adicionales es
  una aspiración diagnóstica, no un detector científico implementado.
- Paradas: periodicidad observada, máximo de ciclos, pared, RAM, estado inválido,
  conservación relativa >1e-8, o 25 intentos consecutivos de paso rechazados.
- Se guardan snapshots exactos en cierres de transfer/escape con válvula
  aplicada. No se interpola masa atrapada.
- Admisión híbrida: ancho 38 mm basado en el diámetro de entrada, altura 36 mm
  y posiciones sintéticas. Un máximo 1162.8 > 1134.1 mm² NO garantiza que la
  ventana nunca restrinja; a 90° su área efectiva es ~702.6 mm².
- Mapa de válvula sintético: posición 0 levantada, 1 bajada; 0.5 representa
  medio recorrido del techo, no mitad de área/caudal ni mapa medido.
- No hay reintento automático, refinamiento ni barrido adicional.

Resultado de la primera ejecución: **30 ciclos / 190.516 s / MAX_CYCLES_NONCONVERGED**.
Informe y receipt: `results/integrated-solver-verification-v1/standard-v1-9000-report.md`.
Trabajo indicado positivo en el último ciclo (29.099 J), sin periodicidad global.
No hubo ajustes de parámetros ni continuación automática.
