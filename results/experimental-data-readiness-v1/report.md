# Experimental Data Readiness — Cahoon MK.1 y Yamaha MT-110S

2026-10-28. Selección de motores cerrada; revisión documental focalizada.
No se ejecutaron simulaciones, tests numéricos, calibraciones ni cambios de Dino.
No se crearon configuraciones ejecutables. Revisión SELF_REVIEW.

## Decisión de cierre

| Referencia | Mejor caso identificable | Decisión para simular el motor sin completar datos |
|---|---|---|
| Cahoon, Greeves 380 MK.1 | Banco a **6000 RPM** y presión de cilindro a 6000 RPM; grupo cercano de presiones de gases a 5960/5980 RPM, que se mantiene separado | **BLOCKED**: geometría hidráulica incompleta/conflictiva y condiciones del mismo ensayo no publicadas con detalle suficiente |
| Zhang, Yamaha MT-110S | **L3=330 mm, 3435 RPM**, tres presiones medidas; comparación de curvas de torque/potencia L3=330/480 mm en el intervalo común | **BLOCKED**: falta geometría esencial del motor y condiciones por registro. El diseño experimental A/B es aprovechable, pero no configura todavía un caso Dino |

Hay observaciones experimentales parciales útiles para futuras comprobaciones;
eso no constituye por sí solo un problema de contorno cerrado para validar un
componente ni habilita potencia absoluta. Ninguno alcanza READY con los
documentos inspeccionados. No se transforma este cierre en una nueva búsqueda.

## Fuentes y convenciones

- Cahoon, W. L., *Unsteady gas flow through a naturally aspirated two stroke
  internal combustion engine*, PhD, Queen's University Belfast, noviembre de
  1971. [Registro institucional](https://pure.qub.ac.uk/en/studentTheses/unsteady-gas-flow-through-a-naturally-aspirated-two-stroke-intern/),
  [PDF completo, 264 páginas](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/612264914/Unsteady_gas_flow_through_a_naturally_aspirated_two_stroke_internal_combustion_engine..pdf).
- Zhang, Qi Xian, *Modelling the scavenging process in a two-stroke I.C.
  engine*, tesis de maestría, Victoria University of Technology, 1995.
  [Registro](https://vuir.vu.edu.au/18232/),
  [PDF completo, 169 páginas](https://vuir.vu.edu.au/18232/1/ZHANG_1995compressed.pdf).

Páginas PDF contadas desde 1. La paginación impresa de Cahoon no tiene un
desplazamiento constante. Clasificación: **M** medición publicada/procesada;
**D** dato documentado, sin afirmar una medición del ejemplar cuando no se
describe; **H** derivable bajo hipótesis explícitas; **A** valor esencial ausente
o no identificado inequívocamente. Un valor supuesto por THROUGH FLOW sigue
siendo una hipótesis del autor, aunque esté escrito en una tabla.

Se consultaron los índices y texto completo de ambas tesis; se revisaron
visualmente tablas, hojas geométricas, esquemas y figuras de los casos
seleccionados. La búsqueda textual negativa no demuestra inexistencia en
cuadernos, tarjetas de entrada o archivos externos. [Índice de evidencia](readiness.json)
conserva hashes y páginas revisadas; los PDFs originales no se redistribuyen.

## 1. Cahoon: el mejor punto y sus límites

### 1.1 Punto de banco MK.1 a 6000 RPM

Tabla 4.1, **PDF 79**, publica:

| Magnitud | Valor original | Clasificación |
|---|---:|---|
| Régimen | 6000 rev/min | M |
| Potencia al freno | 34,36 bhp | M, procesada por SOLN con correcciones atmosféricas SAE |
| BMEP | 97,7 lbf/in² | M/resultado reducido de banco, no independiente de potencia y cilindrada |
| BSFC | 0,779 lb/(bhp·h) | M, consumo específico procesado |
| AFR global | 10,72 | M, no AFR atrapado |
| Eficiencia volumétrica | 0,775 | M, resultado reducido de caudal |

La conversión de bhp mecánico da **25,622 kW**, y P/ω a 6000 RPM da
**40,779 N·m**. Son conversiones de la misma potencia, no dos mediciones
independientes. No derivamos caudal másico absoluto mezclando factores de
corrección no documentados: se conserva BSFC en sus unidades originales.

Fig. 4.13, **PDF 91**, presenta presión de cilindro MK.1 a **6000 RPM**.
Fig. 5.1, **PDF 233 / impresa 52**, relaciona ese registro con máximo de
53,8 atm y BMEP a 6000. Es el mejor emparejamiento nominal localizado, aunque
el método describe pruebas de potencia y fotografías como adquisiciones
separadas; no demuestra simultaneidad ni ajustes idénticos.

### 1.2 Las otras presiones no pertenecen exactamente a ese punto

| Señal MK.1 cercana | RPM rotulada | Fuente exacta |
|---|---:|---|
| Cilindro, ciclo completo | 6000 | Fig. 4.13, PDF 91 |
| Cilindro en fase de barrido, comparación con cálculo | 5960 | Fig. 4.20, PDF 98 |
| Escape, comparación con cálculo | 5960 | Fig. 4.27, PDF 105 |
| Transfer, comparación con cálculo | 5980 | Fig. 4.41, PDF 119 |
| Admisión, comparación con cálculo | 5980 | Fig. 4.48, PDF 126 |

§2.6, **PDF 37–38 / impresas 21–22**, explica la adquisición por pares:
cilindro/barrido, barrido/escape, barrido/transfer y transfer/admisión. La fase
se refiere a PMS y las presiones se representan como P/P0. El ambiente
numérico de cada adquisición no está publicado en estas figuras: no convertir
P/P0 a Pa imponiendo P0=101325 Pa como si fuera el barómetro registrado.

No se agrupan estas curvas como un ensayo exacto de 6000 RPM ni se interpolan
para aparentarlo. Tampoco se adjudica la presión de transfer al cárter:
**PDF 234 / impresa 53** afirma que la presión de cárter debería haberse
medido y la deja como trabajo futuro. La Fig. 5.2, PDF 235, es calculada.

### 1.3 Relación primaria: qué permite deducir y qué no

La tabla de especificaciones **PDF 19 / impresa 11** y el dato CRANKCR en
Fig. A2.2, **PDF 253**, documentan **1,6**. No se localizó una ecuación que
defina expresamente esa relación mediante volúmenes absolutos, una cubicación
ni una definición de cavidades incluidas. El apéndice 3, **PDF 257–261**, define
volúmenes instantáneos VC1/VC2 y el balance energético, pero no proporciona la
ley geométrica numérica ni una medida de volumen libre.

Fig. 3.16, **PDF 73**, y Fig. A3.1, **PDF 260**, sí separan el volumen 0D
del cárter y los conductos 1D mediante los planos de entrada y K8. Esto
documenta los volúmenes de control del cálculo, pero no prueba cómo se midió
o redujo la relación geométrica 1,6 respecto de esos planos.

Bajo las hipótesis explícitas r=Vmax/Vmin y Vmax−Vmin=Vd:

    Vd = π·82²·72/4 = 380,233 cm³
    Vmin = Vd/(1,6−1) = 633,722 cm³
    Vmax = 1013,955 cm³

Estos números son **H**, no volúmenes medidos. Falta verificar la convención
y si se requiere descontar algún volumen representado aparte. Incluso si
se acepta provisionalmente la convención habitual, siguen faltando secciones
de transfer y condiciones de ensayo: resolver sólo la relación primaria no
convierte el conjunto en READY.

### 1.4 Matriz geométrica y de condiciones MK.1

| Parámetro | Estado | Evidencia y limitación |
|---|---|---|
| Bore / stroke / biela | D | 82 / 72 / 139,7 mm, PDF 19; coinciden con PDF 253 |
| Cabeza | D/H | Sin squish, PDF 18; compresión **atrapada** 6,57, PDF 19. Volumen PMS≈42,124 cm³ sólo bajo cierre simétrico, cinemática y definición de compresión atrapada. Forma detallada/cubicación no identificada |
| Distribución | D/H | Escape 96° ATDC, transfer 115° ATDC, admisión 76° BTDC; PDF 19/253. Cierres por simetría de pistón son derivados, no mapa medido de área |
| Anchos efectivos totales | D | Escape 58, transfer 64, admisión 46 mm; PDF 253 explicita que son totales efectivos. No convertirlos en ancho físico de cada ventana |
| Perfiles/radios de ventanas y ángulos de transfer | A | No hay mapa completo dimensionado que cierre área descubierta y dirección de los chorros del MK.1 |
| Admisión básica | D | Longitud total 7 in, carburador 32 mm; PDF 19/253 |
| Admisión detallada del ejemplo MK.1 | D, vínculo pendiente | PDF 253: altura máxima de ventana 27 mm y downdraft 18°; PDF 256: K6=2 in, K7=5 in. Son datos existentes, no ausentes. Falta confirmar que esta hoja y la geometría real del banco usen la misma revisión |
| Sección de admisión no uniforme | H/A | El esquema PDF 256 define transición de área y tramo de diámetro de carburador; no determina completamente la forma física de la transición y cavidades de entrada sin reducción geométrica explícita |
| Transfer | D/A | Longitud 4 in, PDF 19/253, definida desde salida de cárter hasta entrada de cilindro en PDF 253. No se localizó sección completa, volumen ni perfil de conductos; ancho efectivo de lumbrera no basta |
| Escape real | D | Dos primarios que confluyen en el difusor, PDF 18 y Fig. 2.1, PDF 20 |
| Escape reducido | D/H | Fig. 2.2 PDF 20 y tabla PDF 19: estaciones acumuladas L1/L9/L2/L3/L4/L5=17/22/32/32/41/56 in; D1/D9/D2/D3/D4/D5=1,94/2,92/3,75/3,75/1,625/1,625 in. D1=√2·d1 es equivalencia por área, no diámetro de una rama real |
| Secciones equivalentes y unión de ramas | H/A | La reducción está documentada, su identidad exacta con el ensayo y detalle de la unión requieren aclaración; no importar una topología de otro motor |
| Cd de puertos | D, supuesto del autor | Apéndice 2 PDF 250–251: leyes adoptadas, no ensayos de caudal del MK.1. No son coeficientes medidos para validar de manera independiente |
| Carga | D | WOT y búsqueda de máximo BMEP por avance/AFR; PDF 37 |
| Avance por punto | A | Se ajustó y registró chispa en las fotografías, PDF 37–38; no se identificó tabla numérica de avance a 6000/5960/5980 RPM |
| Ambiente y corrección | A numérico | PDF 24/77 indican medición de p/T y correcciones SAE mediante SOLN; valores por registro y factores aplicados no identificados |
| Refrigeración y extracción | D/A | PDF 37: aire de ventilador y extracción de baja depresión; no equivale a temperaturas de pared medidas por región o contrapresión numérica en cada ensayo |
| Temperaturas del mismo punto | A | Se mide temperatura media de escape, PDF 37. No se identificó una tabla vinculada al grupo 6000/5960/5980. Los valores de ejemplo de 4400 RPM no lo sustituyen |
| Presión y temperatura al abrir escape | M-condición/H | PDF 249 explica que THROUGH FLOW recibe presión experimental a apertura; no es predicción ciega de ciclo completo. La temperatura de referencia elevada para corregir fase, PDF 251, es decisión del cálculo original |
| Coordenadas/calibración de sensores | D/A | Ubicación esquemática PDF 21–23 y calibraciones §2.4; faltan coordenadas axiales acotadas y calibración/ambiente asociada a cada registro seleccionado |
| Incertidumbre | D/A | PDF 27 estima ±3 % de rango de presión; no U95, no ±3 % de lectura. Repetibilidad del punto de potencia y datos crudos no publicados identificados |

### 1.5 Conflictos concretos: no existe una corrección justificable por simple lectura

**PDF 249 / impresa 67 identifica expresamente el ejemplo A2.2 como MK.1 a
4400 RPM.** Se precisa así la revisión anterior: no es una hoja de otro motor
sin identificar. Sin embargo, difiere de la tabla principal MK.1:

| Cota | Tabla experimental PDF 19 | A2.2 PDF 254–255 |
|---|---:|---:|
| D1, in | 1,94 | 1,95 |
| D9, in | 2,92 | 2,94 |
| D2 y D3, in | 3,75 | 3,625 |
| L9 / K9, in | **22** | **23** |

Las otras estaciones 17/32/32/41/56 in coinciden. La discrepancia de diámetro
de cámara es −3,33 % y la de estación intermedia es +25,4 mm; no se justifican
como mero redondeo. No hay fe de erratas o vinculación de revisión localizada.
Se conservan dos descripciones, **MK1_MAIN_TABLE** y **MK1_TF_INPUT_4400**;
ninguna se mezcla con MK.2/MK.3 ni se escoge por ajustar mejor la curva.

No usamos el BMEP del ejemplo ni la correlación empírica de presión en EVO
como entradas para después proclamar validación independiente de potencia.

## 2. Yamaha: qué experimento A/B existe realmente

### 2.1 Geometría del cambio

Tabla 4.2, **PDF 105 / impresa 92**, y Fig. 4.2,
**PDF 106 / impresa 93**, definen el mismo escape de cinco segmentos:

| Segmento | Longitud, mm | Diámetro interior inicial→final, mm | Papel |
|---|---:|---:|---|
| L1 | 130 | 30→30 | Constante |
| L2 | 281 | 30→99 | Constante |
| L3 | 240 / 330 / 400 / 480 / 550 | 99→99 | Única dimensión variada declarada |
| L4 | 352 | 99→20 | Constante |
| L5 | 152 | 20→20 | Constante |

Cambiar L3 desplaza el cono convergente y la salida, cambia volumen, superficie
y recorrido acústico; no cambia los diámetros ni las longitudes de los otros
segmentos en el experimento descrito. La Figura 4.13, PDF 115, pertenece al
escape **optimizado calculado**, con otras dimensiones: queda excluida de la
geometría experimental. La Fig. 4.3 mezcla curvas calculadas y el silenciador
original medido: no sustituye las cinco curvas experimentales del capítulo 6.

### 2.2 Resultados de cada variante

| L3, mm | Torque y potencia experimentales | Presiones publicadas a RPM específicas |
|---:|---|---|
| 240 | Fig. 6.1, PDF 135 / impresa 122 | No identificadas en el grupo Fig. 6.6–6.12 |
| 330 | Fig. 6.2, PDF 136 / impresa 123 | 2900, 3435, 3741: Figs. 6.6–6.8, PDF 142–144 |
| 400 | Fig. 6.3, PDF 137 / impresa 124 | 3328: Fig. 6.9, PDF 145 |
| 480 | Fig. 6.4, PDF 138 / impresa 125 | 2550 y 3250: Figs. 6.10–6.11, PDF 146–147 |
| 550 | Fig. 6.5, PDF 139 / impresa 126 | 3060: Fig. 6.12, PDF 148 |

§6.1, **PDF 134**, distingue las curvas medidas de las simuladas; línea
continua experimental y discontinua calculada. La comparación más útil de
curvas es **L3=330 frente a 480 mm**, con superposición de regímenes y
presiones disponibles en ambas configuraciones. No hay par de presiones a
exactamente la misma RPM publicado: 3435 y 3250 no son el mismo punto.

Mejor registro individual: **L3=330 mm, 3435 RPM, Fig. 6.7,
PDF 143 / impresa 130**: presión de cilindro, escape y transfer, con escala
rotulada en 100 kPa y fase de cigüeñal. §5.4.2, **PDF 131 / impresa 118**,
explica adquisición simultánea de las tres presiones y marcador de fase, y
guardado del torque correspondiente en un archivo ASCII. Ese archivo no está
incluido como serie numérica identificada en el PDF. Fig. 6.2 ofrece curvas
medidas; leer/interpolar su torque a 3435 RPM no recupera el registro original
ni crea una segunda medición. No se digitalizan valores en este cierre.

### 2.3 ¿Es un A/B válido y qué falta para reproducirlo?

**Sí, como experimento publicado de modificación de longitud en el mismo
motor; todavía no como fixture ejecutable de validación de Dino.** El texto
no demuestra controles numéricos por registro de mezcla, avance y estado
térmico suficientes para atribuir toda diferencia exclusivamente a longitud.
WOT es una condición de carga documentada, no prueba de AFR idéntico.

| Parámetro esencial | Clase | Fuente y estado |
|---|---|---|
| Motor / cilindro / biela | D | Tabla 5.1, PDF 120 / impresa 107: Yamaha MT-110S, 52×50 mm, biela 101 mm |
| Cilindrada | D/H, conflicto | La tabla dice 100 cc; diámetro/carrera dan 106,186 cc. Aclarar medida antes de calcular BMEP/compresión |
| Cámara / CR | D/A | CR 5,8, misma tabla; convención total/atrapada, volumen real y cabeza no suficientemente determinados |
| Aperturas | D | Escape 104° ATDC, transfer 128° ATDC, admisión 62° BTDC, misma tabla |
| Áreas y perfiles de puertos | A | §4.2 y Fig. 4.1, PDF 102–103, describen ancho/altura/radios/ángulos, sin cerrar todos los valores del ejemplar |
| Cárter | A | Volumen libre o relación primaria con definición no localizada; no derivable sólo de cilindrada |
| Admisión / transfers | A | Se definen fronteras y reducción de conductos, PDF 101; faltan longitudes/secciones completas y carburador del ensayo |
| Escape A/B | D | Tabla 4.2 y Fig. 4.2; dimensiones anteriores, sin importar el escape optimizado de PDF 115 |
| Instrumentación y presiones | M/D | PDF 129: sensores en cabeza/transfer/escape y termopares; PDF 131: señales/torque vinculados por archivo; Fig. 6.7: registro seleccionado |
| Carga y repetición entre escapes | D | WOT, PDF 134; procedimiento PDF 132–133, cambiar L3 y repetir; sin tabla completa de condiciones por punto |
| Ambiente | A numérico | PDF 132 ordena registrar p/T; no se identificaron valores asociados al registro de 3435 RPM y a su alternativa |
| Avance, AFR y combustible por punto | A | No se localizó ficha experimental vinculada; parámetros de combustión/AFR atrapado del modelo en PDF 140 son supuestos, no mediciones para rellenar esos campos |
| Térmica | D/A | Escape aislado, dos termopares y límite de seguridad 600 °C, PDF 129; no tabla térmica por registro. Los 350/450 °C de PDF 104 son simplificaciones del cálculo |
| Barrido y Cd | D, supuestos del autor | PDF 102–103: Cd elegidos y YAM6 tomado de otra referencia por ausencia de ensayo propio. No convierten este motor en otro con geometría o barrido medidos |
| Incertidumbre/repetibilidad | D/A | Calibración del torque PDF 125–126; faltan series originales, dispersión y presupuesto combinado por punto. El grosor de línea de un gráfico no es incertidumbre de banco |

Para desbloquear basta un paquete del **mismo banco MT-110S** con geometría
faltante y registros originales identificados por longitud y RPM; no es
necesario repetir las cinco curvas completas. Primero recuperar el archivo
de 3435 RPM/L3=330 y una referencia de torque a régimen común para otra L3,
con condiciones y calibración asociadas. Si los archivos no existen, no se
reconstruyen mediante el código de otro motor ni ajustando Dino a las curvas.

## 3. Solicitud externa y cierre

Se deja un [borrador técnico para QUB](cahoon-archive-request.md), limitado a
las incógnitas demostradas y a la coherencia del grupo MK.1. Incluye páginas,
conflictos concretos y contacto institucional verificado. **No enviado.**
No se exige otro PDF de la tesis que ya tenemos, ni datos de MK.2/MK.3,
ni nuevas mediciones, ni una campaña completa.

**Cierre global: BLOCKED para el primer caso integrado reproducible.** La
dependencia restante es adquisición documental externa concreta. Se preservan
las fuentes, la selección anterior y los resultados numéricos; rc7 y Dino
permanecen intactos. No se amplía la búsqueda de motores ni se inicia trabajo
experimental o numérico automáticamente.
