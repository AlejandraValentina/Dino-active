# Etapa 2 — segundo orden experimental y comparación A/B

2026-10-28. Prerregistro: **35fe19f**, anterior a todas las nuevas ejecuciones.
Revisión: **SELF_REVIEW**.

## Dictamen

**ADOPTAR COMO CANDIDATO**, con alcance limitado a las comprobaciones realizadas.
**DIFERENCIA DISTINGUIBLE** en los observables de presión P1 preregistrados,
durante el segundo ciclo transitorio de las configuraciones E2A.
Se cumplieron los criterios sin modificar umbrales ni modelos físicos.

Esto permite conservar una opción experimental útil para distinguir la
respuesta de esas geometrías en P1. No demuestra resolución uniforme de todas
las ondas del escape, identificación del retorno, potencia periódica,
independencia de malla ni precisión experimental. El esquema predeterminado
de primer orden y rc7 permanecen intactos. **E2B no se inició.**

## Implementación entregada

La capacidad ya estaba implementada en el núcleo integrado; se reutilizó sin
reconstruir ni alterar el solver. `second_order.py` es el verificador aislado
histórico; su composición de una especie no sustituye la ruta integrada.
La ruta adecuada utiliza:

- `spatial_reconstruction_v1.py`: MUSCL en primitivas y cuatro componentes,
  minmod generalizado theta=1,5, pendientes en coordenadas físicas,
  limitación compatible con positividad y simplex sin cambiar promedios.
- `spatial_reconstruction_v2.py`: trazas unilaterales limitadas en extremos,
  conectadas a lumbreras V2 y OPEN_END_PLENUM_V2. Conserva los flujos donantes
  de especies según el sentido del transporte.
- `IntegratedEngine2T`: HLLC interior, SSPRK2, validación de etapas y
  contabilidad conservativa existentes.

Se entregan cuatro configuraciones nativas V8 con selección explícita
`MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2`, un ejecutor acotado,
tests de congelación y análisis reproducible. Tests comprueban igualdad
exacta de estado inicial, inventarios y todos los campos E2A salvo schema y
selector espacial. No se modificó ningún archivo de `motorsim/` ni Desktop.
Las identidades y checkpoints nuevos pertenecen al modelo numérico nuevo;
no se reetiquetan resultados históricos.

## Controles numéricos conocidos

**32 PASS**: positividad, simplex, extremos no uniformes, donantes en ambos
sentidos, cierre conservativo, choque/contacto, reinicio y control histórico
sin cambio del primer orden, además de la congelación A/B.

Referencias suaves con 40/80/160 celdas, SSPRK2, CFL0,2:

| Referencia | Orden observado 80→160, MUSCL |
|---|---:|
| Entropía, densidad L1 | 2,147 |
| Entropía, especies L1 | 2,127 |
| Acústica sinusoidal, presión L1 | 2,121 |
| Pulso gaussiano, presión L1 | 1,843 |

En el pulso, error L1 con 80 celdas: primer orden **3,94491e-8**;
MUSCL **5,56317e-9**, reducción **7,09×**. La atenuación del máximo respecto
del promedio de celda analítico pasa de **20,94% a 5,63%**.
Con 160 celdas: **12,25% a 1,95%**. La referencia acústica es linealizada,
amplitud 1e-6 y error no lineal O(amplitud²); no es un ensayo experimental.
El argmax discreto de posición no mejora monótonamente: no se usa para
afirmar una mejora general de fase. No se exige orden dos en discontinuidades.

## Comparación integrada congelada

Mismas geometrías A/B E2A, diferencia de 20 mm en cabecera, 9000 RPM,
condiciones y dos ciclos independientes. 44/88 celdas totales, 31/62 en
escape; V2 experimental idéntico en A y B. Sondas físicas y operador de
promedio de 10 mm idénticos a E2A. Se reutilizaron los resultados de primer
orden, sin recalcularlos. Amplitud = máximo de presión P1 menos 101325 Pa,
ventana 88–272° del segundo ciclo; no es amplitud de una onda incidente aislada.

| Caso MUSCL | Amplitud P1 (kPa) | Fase del máximo (°) | Impulso (Pa·s) | Solver (s) |
|---|---:|---:|---:|---:|
| A44, paso nominal 0,5° | 69,4085 | 109,5 | 30,2223 | 26,456 |
| B44, paso nominal 0,5° | 54,6045 | 113,5 | 24,5644 | 26,818 |
| A88, paso nominal 0,5° | 69,2824 | 110,5 | 32,4627 | 71,652 |
| B88, paso nominal 0,5° | 50,8934 | 113,5 | 25,4752 | 70,718 |
| A88, paso nominal 0,25° | 69,2821 | 110,5 | 32,4648 | 72,662 |
| B88, paso nominal 0,25° | 50,8935 | 113,5 | 25,4730 | 68,928 |

| Observable P1, B−A fino | Diferencia | Envolvente empírica E2A | Cumple |
|---|---:|---:|---|
| Amplitud | −18,3886 kPa | 11,4855 kPa | Sí |
| Fase del máximo | +3,0° | 2,5° | Sí |
| Retraso por correlación | +4,0465° | 2,5° | Sí |
| Impulso | −6,9918 Pa·s | 6,3148 Pa·s | Sí |

Correlaciones A/B: 0,98485 / 0,96149 / 0,96148 en grueso/fino/fino temporal;
máximos interiores y únicos conforme al control existente. Los signos se
mantienen en los tres pares. El retraso es de la forma de señal comparada;
no se convierte en velocidad de propagación ni en tiempo de reflexión.

La envolvente conserva exactamente la fórmula E2A: dos veces la suma de
sensibilidades espaciales y temporales individuales A y B, más muestreo.
No supone cancelación del error A/B y **no es una cota rigurosa ni U95**.
Con dos mallas no se calcula un orden integrado, Richardson ni GCI.

## Mejora y límites espaciales: resultado no uniforme

La suma de diferencias de amplitud P1 entre mallas pasa de **10,1330 kPa a
3,8372 kPa**, reducción **62,13%**, superior al 30% preregistrado. La
sensibilidad temporal nominal suma **0,347 Pa**. La sensibilidad de fase
del máximo no mejora: suma 1° en ambos esquemas.

También hay observables que empeoran: la suma de sensibilidades espaciales
del impulso pasa de **1,8864 a 3,1513 Pa·s** (+67,1%). La diferencia A/B de
impulso aun supera su envolvente, pero esto no prueba mejor convergencia de
ese observable.

Normas L1 de diferencias de las trazas 44/88, ventana 88–272°, en kPa:

| Sonda x (m) | A primer orden | A MUSCL | B primer orden | B MUSCL |
|---|---:|---:|---:|---:|
| 0,040 | 2,818 | 2,567 | 2,874 | 2,720 |
| 0,250 | 1,587 | 2,861 | 1,465 | 2,470 |
| 0,550 | 0,643 | 1,035 | 0,696 | 1,045 |
| 0,800 | 1,955 | 4,623 | 1,880 | 3,439 |
| 1,020 | 2,977 | 10,195 | 3,313 | 9,851 |

Por tanto, **no se demuestra mejora de convergencia de toda la traza ni del
extremo de salida**. Cerca de 1,020 m la suma de diferencias L1 aumenta de
6,289 a 20,047 kPa. Menor difusión puede exponer estructuras previamente
suavizadas; estos datos no separan ese efecto de otros errores espaciales.
No se diagnostica un defecto nuevo sin prueba específica.

Los mapas espacio–fase documentan la propagación. La correlación automática
entre sondas separadas no cumple sus guardas; sus lags se guardan marcados
inválidos. Un máximo global puede pertenecer a paquetes diferentes: en B,
x=0,550 m tiene su máximo a 261,5°, por lo que no se conecta automáticamente
con el máximo de A a 157,5° como una misma onda.

La descomposición acústica lineal vuelve a fallar las guardas en toda la
ventana de retorno 150–272°. **Retorno/reflexión no identificado** por este
método. No se renombra un pico como reflexión.

El control 0,5→0,25° no divide todos los dt reales: la mediana en 88 celdas
es 4,62963 µs en ambos. El máximo baja de 9,25926 a 4,62963 µs; los pasos
aumentan de 2396/2399 a 2884/2884. No demuestra independencia temporal
absoluta. A88 nominal rechazó 950 propuestas por CFL y tres por masa de
especie inadmisible; B88 rechazó 955 por CFL. Se aplicó la misma reducción
de paso y rechazo conservativo de E2A, sin recortar especies ni aceptar esos
estados. El control 0,25° no tuvo rechazos. La estabilidad demostrada incluye
esta protección adaptativa; no se afirma positividad incondicional a paso fijo.

## Conservación, reinicio, coste y preservación

Máximos residuos relativos integrados: masa **1,798e-15**, energía
**8,912e-16**, especies **8,178e-16**. Los seis casos terminaron a 720° y
restauraron exactamente sus checkpoints nativos. Se preservan checkpoints
por revolución y recetas; no se han cambiado criterios de periodicidad.

Solver de los seis casos: **337,234 s**, frente a **277,982 s** del mismo
conjunto de primer orden, incluyendo el coste original del A44 reutilizado:
**1,213× (+21,3%)**. Medición única por caso, sin intervalo estadístico de
rendimiento. RSS máximo **61,55 MiB**. Artefactos nuevos **21.023.573 bytes**,
fuera del repositorio, bajo la raíz configurable de artefactos; preflight
con 2 GiB de reserva antes de escribir, sin limpieza ni traslado histórico.

Regresión P4–P8: primer intento **298 PASS, 3 FAIL, 3 SKIP** por ausencia de
la variable `DINO_ARTIFACT_ROOT`, no por ausencia o corrupción de evidencia.
Se verificaron los 56 archivos contra el manifiesto, sin alterarlos; sólo
se definió la raíz en el entorno del proceso y se repitieron los tres tests:
**3 PASS**. Cobertura final distinta: **301 PASS, 3 SKIP**. Los logs de ambos
intentos se conservan. No se repitió la suite completa ni se omitieron fallos.

Consumo acumulado conservador **567,162 s / 600 s**: controles, seis casos,
análisis, ambos intentos de regresión, sobrecoste de lanzamiento y 10 s
imputados a verificar archivos históricos. Presupuesto no ampliado.

## Evidencia y cierre

- [Prerregistro](../../docs/gasdynamic/e2-spatial-waves-protocol-v1.md).
- [Decisión y presupuesto completos](adoption.json), [métricas E2A](decision.json).
- [Primer orden frente a MUSCL](first-vs-second-order.png).
- [Presión A/B y proyecciones acústicas](pressure-comparison.png).
- [Mapas de propagación](pressure-propagation.png).
- [Sondas y fase](propagation-metrics.csv), [normas entre mallas](mesh-trace-differences.json).
- [Controles aislados](verification.json), [recibo de ejecución](execution-receipt.json).
- [Inventario y SHA-256 de checkpoints/arrays/recetas](artifact-index.json).

La decisión de candidato corresponde al criterio P1 congelado y al dominio
ensayado. No promueve el esquema a producción ni resuelve las incertidumbres
aguas abajo. Se conserva el primer orden como control y predeterminado de rc7.
No se ejecutan más mallas, ciclos, curvas ni E2B en este cierre.
