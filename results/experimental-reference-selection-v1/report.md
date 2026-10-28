# Selección de referencia experimental — Dino 2T

Fecha: 2026-10-28. Revisión de fuentes primarias; sin crear modelos ejecutables,
rellenar geometría, calibrar ni simular por esta investigación.

## Decisión

**Principal: Greeves 380 cc MK.1 de Cahoon (1971), aptitud PARCIAL.** Es la
mejor base pública inspeccionada para preparar una validación conjunta del
intercambio de gases: geometría básica, relación de compresión de cárter,
distribución, escape acotado, prestaciones, consumo/AFR y presiones de varios
sistemas. La tesis íntegra de 264 páginas se descargó correctamente desde QUB;
el bloqueo anterior de acceso ya no aplica. Esto no resuelve todos sus datos.

**Alternativa: Yamaha MT-110S de Zhang (1995), PARCIAL.** Es el conjunto abierto
más directamente útil para verificar cambios de escape: cinco longitudes de
la misma cámara, con torque/potencia experimentales y presiones. Falta más
geometría de admisión, transfers y cárter que en Cahoon.

**Generalización posterior: IAME X30 Senior, PARCIAL/BLOQUEADO.** Mantenerlo
como contraste moderno de competición, condicionado a medir el volumen libre
del cárter y vincular la revisión geométrica al ejemplar ensayado. No adoptarlo
como primer caso sólo por disponer ya de una curva digitalizada.

**Ninguno de los cinco candidatos queda acreditado como conjunto COMPLETO
para configurar ahora un motor íntegro sin decisiones geométricas no verificadas
y validar potencia absoluta con incertidumbre experimental conocida.** La
elección principal es una prioridad de incorporación documental, no permiso
para construir un Greeves supuesto ni una declaración de validación realizada.

## 1. Candidatos, ordenados por utilidad pública comprobada

| Orden | Motor y fuentes primarias | Datos realmente aprovechables | Límites y nivel de validación posible |
|---|---|---|---|
| 1 | **Greeves 380 MK.1/2/3**, [Cahoon, tesis QUB 1971](https://pure.qub.ac.uk/en/studentTheses/unsteady-gas-flow-through-a-naturally-aspirated-two-stroke-intern/), [PDF íntegro](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/612264914/Unsteady_gas_flow_through_a_naturally_aspirated_two_stroke_internal_combustion_engine..pdf). Relacionado: [Blair–Cahoon SAE 720156](https://doi.org/10.4271/720156). | Tabla de tres versiones; longitudes/diámetros del escape; cárter r=1,6; banco, AFR/BSFC, presiones de cilindro y conductos. | PARCIAL. Preparación de validación de intercambio de gases y motor por versión. No hay presión experimental de cárter identificada. No es A/B de escape aislado: cambian cabeza, distribución, admisión y transferencias. Potencia predictiva absoluta aún bloqueada por detalles geométricos y de ensayo. |
| 2 | **Yamaha MT-110S**, Qi Xian Zhang, *Modelling the scavenging process in a two-stroke I.C. engine*, tesis de maestría, Victoria University of Technology, 1995. [Registro](https://vuir.vu.edu.au/18232/), [PDF](https://vuir.vu.edu.au/18232/1/ZHANG_1995compressed.pdf). | Mismo motor, cámara de expansión de dimensiones publicadas, L3=240/330/400/480/550 mm; cinco curvas experimentales torque/potencia; presiones de cilindro, escape y transfer; calibración del torquímetro. | PARCIAL. Mejor objetivo abierto para cambio de diseño A/B, tras recuperar la geometría faltante. Volumen/compresión de cárter, áreas completas de lumbreras y conductos de admisión/transfer no localizados. Inconsistencia de cilindrada nominal que debe aclararse. |
| 3 | **Morini AH50L**, [Gimelli–Muccillo 2021](https://doi.org/10.3390/en14248372), [PDF abierto](https://mdpi-res.com/d_attachment/energies/energies-14-08372/article_deploy/energies-14-08372.pdf). Antecedente experimental: [Gimelli et al., SAE 2008-01-0318](https://doi.org/10.4271/2008-01-0318); modelo relacionado: [Bozza–Gimelli, 2004-01-0999](https://www.iris.unina.it/handle/11588/100831). | Motor de láminas 41×37,4 mm; Tabla 2; WOT 4000–8500 RPM cada 500; lambda por régimen, potencia y caudales medidos; banco instrumentado para presión de cilindro, cárter y escape. | PARCIAL. Fuente 2021 íntegra y abierta; útil para prestaciones/mezcla una vez completada geometría. No publica en ella biela, volumen de cárter ni escape acotado completo. Instrumentación declarada no equivale a señales crudas públicamente disponibles. No hay A/B de escape identificado. |
| 4 | **IAME X30 Senior**, [Ortenzi–Bossaglia 2023](https://doi.org/10.3390/en16134947), [homologación IAME 254/V](https://www.iame-motorsport.com/files/noticeboard/254V_IAME-X30-125cc-LIMIT.-16000-giri-MOTORE-REV.05-AGG2021_21032024111116.pdf), [MAN-089](https://www.kartcompany.ch/images/iame/manual/E/MAN-089-ENG-X30-125cc-Spec-EU.pdf). | Nominal 54×54 mm, biela 102 mm; planos reglamentarios, láminas y escape; curva de potencia medida Fig. 10 ya inventariada en el proyecto. | PARCIAL/BLOQUEADO. Falta volumen libre de precompresión con referencia angular/fronteras; revisión y dimensiones del ejemplar de banco no plenamente vinculadas. No se identificó A/B experimental de escapes. Referencia posterior de generalización, no configuración lista. |
| 5 | **Honda RS125**, [Fleck et al., SAE 2004-01-3561](https://doi.org/10.4271/2004-01-3561). | Resumen editorial confirma banco WOT 9000–13000 RPM, presiones de cilindro/escape y modificaciones de escape medidas. Es el objetivo más próximo al tipo de claim A/B deseado. | INSUFICIENTE EN ACCESO VERIFICADO: no se obtuvo texto completo legítimo. El resumen dice que los autores usaron geometría, Cd, barrido y combustión; no demuestra que los publicaran íntegramente. No se puede certificar una matriz geométrica ni preparar Dino sólo con ese resumen. |

La clasificación ordena utilidad **disponible e inspeccionada**, no la calidad
potencial de datos privados. El RS125 podría pasar al primer lugar si el texto
y sus datos efectivamente cierran el caso. No se descarta por física, sino por
no haber podido verificar su paquete completo.

## 2. Matriz de la referencia principal: Cahoon MK.1

Las páginas PDF se cuentan desde 1. La numeración impresa no lleva un
desplazamiento constante: hay figuras insertadas. No convertir todas las citas
sumando una constante. `D`=documentado; `M`=resultado experimental procesado;
`C`=calculable con condiciones explícitas; `F`=faltante/no suficientemente determinado;
`S`=supuesto del simulador original, no medición.

| Dato necesario | Evidencia y ubicación exacta | Estado y uso permitido |
|---|---|---|
| Identidad y topología | §2.2, PDF 17–18, impresas 9–10: Greeves motocross, barrido en lazo, dos salidas de escape; versiones MK.1/2/3. | D. Mantener una identidad por versión. Admisión por pistón, sin láminas que reconstruir. |
| Diámetro, carrera, biela | Tabla de especificaciones, PDF 19 / impresa 11: 82, 72 y 139,7 mm. | D; cilindrada geométrica C=380,233 cm³. |
| Cámara | Misma tabla: compresión **atrapada** 6,57 en MK.1; PDF 18: cabeza sin squish. | D/C parcial. No tratar 6,57 como compresión geométrica total. Con cierre de escape simétrico a 264° y cinemática indicada, volumen condicional en PMS≈42,124 cm³; no es una cubicación independiente de cámara ni revela su forma. |
| Cárter | PDF 19: relación de compresión 1,6 para las tres versiones. | D/C condicional. Si r=Vmax/Vmin y Vmax−Vmin=Vd, Vmin=633,722 y Vmax=1013,955 cm³. Falta confirmar qué cavidades/conductos incluye la definición original para no duplicar transferencias en Dino. No hay un volumen absoluto medido publicado identificado. |
| Distribución MK.1 | PDF 19: escape abre 96° ATDC, transfer 115° ATDC, admisión 76° BTDC. | D. Cierres simétricos sólo como derivación bajo control de pistón y la convención indicada; no sustituye un mapa real de ventana. |
| Anchos de lumbreras | PDF 19: escape 58, transfer 64, admisión 46 mm, efectivos en la reducción del autor. | D parcial. Confirmar agregación/proyección, perfil, radios, ángulos y área expuesta; no interpretar sin más como ancho físico de cada una de las dos salidas. |
| Admisión | PDF 19: carburador 32 mm y longitud 7 pulgadas. | D parcial; falta sección completa de conducto/entrada y estado real de carburación/avance por punto. |
| Transfers | PDF 19: longitud 4 pulgadas; ancho efectivo total 64 mm. | D parcial. No localicé una sección hidráulica completa del conducto real y su unión al cárter inequívocamente acotada. Longitud y ancho de ventana no fijan por sí solos ese volumen. |
| Escape | PDF 19 y Figs. 2.1/2.2, PDF 20. L1/L9/L2/L3/L4/L5=17/22/32/32/41/56 pulgadas; D1/D9/D2/D3/D4/D5=1,94/2,92/3,75/3,75/1,625/1,625 pulgadas. | D, reducción del autor. **L son estaciones acumuladas desde cara del pistón**, no longitudes independientes; L3−L2=0 en MK.1. D1 representa dos ramas equivalentes por área, D1=√2·d1; no es un diámetro medido de una rama. Mantener la bifurcación real o declarar/justificar la aproximación equivalente. |
| RPM, carga y procedimiento | §2.6, PDF 37–38 / impresas 21–22: WOT, óptimo de avance y AFR por régimen; ventilador de refrigeración y extracción. Tabla 4.1, PDF 79: 4500–7500 RPM. | D/M. Faltan valores de avance óptimo y condiciones ambientales numéricas por punto. No igualar automáticamente el RPM de una fotografía al punto más próximo del banco. |
| Potencia y torque | Tabla 4.1, PDF 79, y Fig. 4.4, PDF 82; método SOLN en PDF 77. Ejemplo legible: 4500 RPM, 21,51 bhp y BMEP 81,6 psi. | M: potencia/BMEP de banco con corrección atmosférica SAE. Torque C a partir de P y RPM, no una segunda medición independiente. Algunas celdas están ocultas por marca de agua: no reconstruirlas por interpolación como datos medidos. |
| Combustible, AFR y aire | Tabla 4.1: BSFC, AFR y eficiencia volumétrica; §2.3, PDF 24: orificio/airbox y medición volumétrica de combustible; PDF 77: procesamiento. | M. Ejemplo 4500 RPM: BSFC 0,817 lb/(bhp·h), AFR 12,65, eficiencia volumétrica 0,802. Flujo de combustible se deriva de BSFC×potencia; no confundir con masa atrapada ni AFR dentro del cilindro. Caracterización exacta del combustible y sus incertidumbres incompletas. |
| Presión de cilindro | PDF 21 y Fig. 2.5 PDF 23; MK.1 Figs. 4.10–4.16, PDF 88–94. | M, sensor en cabeza; sensor adicional en camisa para fase de barrido. Separar canales, sensibilidad y ventana válida. |
| Presiones de conductos | MK.1: escape Figs. 4.24–4.30; transfer 4.31–4.44; admisión 4.45–4.51. Índice explícito PDF 229 / impresa 48. | M y cálculos mezclados en figuras: usar leyenda/texto de cada caso. Fig. 4.24 está en PDF 102 y declara 4400 RPM; no asignarla al punto de potencia de 4500 RPM sin evidencia. Fig. 2.5 ubica sensores, pero no cierra coordenadas axiales acotadas. |
| Presión de cárter | Discusión PDF 234 / impresa 53. | F para medición: el autor distingue transferencia y cárter y propone medir éste en trabajo futuro. Curvas calculadas de cárter no sirven de referencia experimental. |
| Incertidumbre de presión | §2.4, PDF 27 / impresa 16: estimación del autor de aproximadamente ±3 % del rango completo. | D estimada; **no ±3 % de lectura ni U95**. Faltan presupuesto moderno de incertidumbre, repetibilidad y señales digitales originales. Añadir aparte incertidumbre de digitalización cuando se extraigan curvas. |
| Cd y pérdidas | Apéndice 2, PDF 250–251 / impresas 68–69: leyes supuestas, por ejemplo escape 1→0,7 y transferencia 1→0,75; extremo de transfer al cárter 0,7. | S, no mapa de flujo medido. Pueden documentar la reproducción de THROUGH FLOW, no identificar el Cd real ni demostrar precisión del modelo Dino. |
| Térmica/estado de apertura | PDF 37: termopar en tramo paralelo; PDF 251: discusión de temperatura de referencia; ejemplo PDF 254. | M parcial/S. La temperatura de referencia elevada 200 °F para mejorar fase es una decisión del cálculo original, no temperatura experimental adicional. No calibrarla ni importar presión en EVO para reclamar predicción cerrada de potencia. |

### Conflicto documental que impide copiar el apéndice como configuración

El ejemplo de entrada de THROUGH FLOW, Figs. A2.2, PDF 253–254, usa 4400 RPM
y cotas de escape diferentes de la tabla principal MK.1: D1=1,95 en vez de
1,94 pulgadas; D9=2,94 en vez de 2,92; D2/D3=3,625 en vez de 3,75. No se
demostró que sea una revisión corregida del mismo ensayo. Sus valores de
presión a apertura, temperaturas y otros campos incluyen hipótesis de diseño.
**No combinar esa hoja con la tabla principal para cerrar huecos.**

La evidencia experimental sí es real y valiosa. Lo que no se puede hacer es
convertir la reproducción del análisis de ciclo abierto de THROUGH FLOW en
una validación independiente de combustión, pérdidas y potencia absoluta.

## 3. Alternativa y referencias complementarias: condiciones de uso

### Zhang: A/B experimental auténtico, geometría todavía incompleta

- Tabla 4.2 y Fig. 4.2, PDF 105–106 / impresas 92–93: segmentos de escape
  L1=130 mm/D30; L2=281 mm/D30→99; L3 variable/D99; L4=352 mm/D99→20;
  L5=152 mm/D20. Aquí las longitudes son **segmentos**, a diferencia de Cahoon.
- Tabla 5.1, PDF 120 / impresa 107: 52×50 mm, biela 101 mm; aperturas
  escape 104° ATDC, transfer 128° ATDC, admisión 62° BTDC; CR 5,8 sin
  convención completamente resuelta para un modelo ejecutable.
- El mismo cuadro dice 100 cc, pero 52×50 produce **106,186 cc**. Se deja la
  discrepancia abierta; no corregir una medición por escoger el nombre comercial.
- Capítulo 6, PDF 134–141 / impresas 121–128 y Figs. 6.1–6.5, PDF 135–139:
  cinco curvas medidas a WOT, distinguidas de las curvas discontinuas calculadas.
  Las presiones medidas Figs. 6.6–6.12, PDF 142–148, corresponden a RPM
  específicas: L3=330, 2900/3435/3741 RPM; L3=400, 3328; L3=480, 2550/3250;
  L3=550, 3060. No existe una señal de presión para cada punto de cada curva.
- Instalación de sensores y termopares PDF 129 / impresa 116; torque y
  calibración PDF 122–126; condiciones/procedimiento PDF 132–133. Las pruebas
  publicadas no entregan automáticamente una incertidumbre U95 de las curvas.
- Los Cd de Tabla 4.1, PDF 102, y barrido YAM6, PDF 103, son elecciones del
  modelo; este último se toma de otro estudio por falta de medición propia.
  No importarlos como ensayos del MT-110S.

**Desbloqueo mínimo:** fichero original de geometría del banco o planilla con
volumen de cárter definido, áreas/perfiles de puertos, admisión y transfers;
aclaración de cilindrada/CR y condiciones por punto. El texto dice que se midió
geometría para alimentar el programa (PDF 100), pero eso no prueba que todas
esas medidas estén publicadas. Solicitud concreta al repositorio/archivo de
Victoria University asociado al registro 18232: anexos, input decks y datos
del banco de esa tesis. No se afirma que todavía se conserven ni se contactó
a terceros en esta intervención.

### Morini/Gimelli: datos medidos no equivalen a paquete geométrico

El PDF abierto 2021 identifica AH50L en §2.1, PDF 4, con especificaciones en
Tabla 2, PDF 5; combustible en Tablas 3–5; condiciones en §2.3, PDF 6;
lambda en Fig. 4 y potencia **medida** en Fig. 5, PDF 7. Tablas y figuras
posteriores aportan flujos, eficiencia y emisiones.

El equipo incluye tres canales de presión y caudales (PDF 3–4), pero no se
entrega un conjunto descargable de señales sincronizadas con geometría
completa; la declaración de disponibilidad, PDF 19, no ofrece un repositorio.
Los máximos 4,11 kW/8000 RPM y 4,7 Nm/7500 de Tabla 2 son especificaciones,
no sustituyen Fig. 5. El caso calculado CNG de §4, PDF 14, CR=14 y 5000 RPM,
no es la geometría experimental estándar CR=11,7.

El trabajo 2021 cita explícitamente SAE 2008-01-0318 como antecedente
experimental. Aun así, no se certifica identidad exacta de hardware de cada
campaña por compartir autores y laboratorio. El PDF del modelo 2004 en IRIS
aparece restringido; el enlace histórico al apéndice IEA-AMF de 2008 devolvió
404 en las comprobaciones directas. La indexación de un buscador no equivale
a haber descargado ese documento. Se mantiene esa limitación de acceso.

### X30 y RS125: conservar su utilidad sin sobreafirmar

X30: reutilizar [inventario existente](../x30-public-reconstruction-v1/x30-technical-inputs-v2.json)
y [decisión geométrica](../x30-public-reconstruction-v1/decision.md). El manual,
la homologación y la curva del artículo no acreditan por sí solos que la misma
revisión se montara en el banco. El error de lectura de la curva digitalizada
no es incertidumbre del ensayo. No mezclar resultados del Screamer III KZ del
mismo artículo con X30.

RS125: la autoría del artículo 2004 es B. Fleck, R. Fleck, R. Kee, G. Chatfield
y D. Mackey; **Cartwright no figura como autor**. Un caso de libro
Blair/Cartwright o un motor sintético del repositorio no es el Honda medido
de este artículo. Vía de desbloqueo concreta: texto íntegro por biblioteca/SAE
y, después de comprobar las tablas, los anexos geométricos y las dos
configuraciones de escape vinculadas a sus mediciones. No se compró ni se
obtuvo copia no autorizada.

## 4. Qué adquirir para poder comenzar de forma rigurosa

Para **Cahoon MK.1**, hacer una solicitud única al archivo de tesis/suplementos
de QUB usando el identificador de archivo **612264914**, con estas preguntas
cerradas:

1. ¿Cómo se define r de cárter=1,6 y qué cavidades incluye? Volumen libre en
   PMS/PMI y fronteras de admisión/transfer, o documentación que fije esa
   convención. Evitar contabilizar dos veces el mismo gas.
2. ¿Existen hojas de geometría real MK.1 de admisión, transfers, ventanas y
   unión de los dos primarios? ¿Qué hoja corresponde al banco: especificaciones
   PDF 19 o ejemplo A2.2 PDF 253–254? ¿Hay cotas de sensores?
3. Para un solo punto de banco y su presión a la **misma RPM**, solicitar
   avance, combustible, ambiente, ajustes, temperaturas y registros de carga/
   caudal. No pedir ni reconstruir una campaña completa antes de cerrar esto.

El criterio de cierre de esa adquisición es **una planilla única del MK.1 con
ningún grado geométrico indispensable libre y un punto experimental trazable**.
Si no existen los archivos, la tesis no alcanza para una reconstrucción
predictiva completa: mantenerla como referencia parcial y pasar a la solicitud
geométrica de Zhang. No prolongar automáticamente búsquedas web de la misma
información.

Vía práctica adicional si los archivos históricos no sobreviven: X30 ensamblado
de revisión conocida, cubicación de cárter con pistón en ángulo definido y
conductos delimitados; confirmación de cámara/escape/láminas y condiciones
del banco de Ortenzi–Bossaglia. Medir el volumen no sustituye vincular el
ejemplar a la curva publicada. Para un claim A/B nuevo se necesitan dos
escapes medidos en ese mismo motor; una homologación no proporciona ese ensayo.

Una referencia utilizable permitirá primero comprobar presiones/caudales
con fronteras y condiciones medidas; después potencia absoluta; y finalmente
un cambio A/B reservado como comprobación independiente. Esto describe el
alcance de los datos, no inicia etapas ni simulaciones.

## 5. Trazabilidad y límites de esta selección

Se indexó el texto de los PDFs completos de Cahoon (264 páginas), Zhang
(169) y Gimelli–Muccillo (21), y se verificaron visualmente las tablas,
esquemas y ejemplos relevantes. Se reutilizó la reconstrucción X30 ya
documentada; el RS125 sólo se evaluó hasta el resumen editorial accesible.
No se afirma haber examinado tablas no obtenidas ni que todo dato no localizado
sea inexistente en archivos privados.

Los originales descargados y capturas de lectura permanecen en el caché externo
de artefactos; no se redistribuyen dentro del repositorio. Sus URL, tamaño,
SHA-256 y páginas relevantes figuran en [sources.json](sources.json).
La [selección estructurada](selection.json) conserva cinco identidades separadas.
No se digitalizaron nuevas curvas ni se convirtieron hipótesis de los autores
en mediciones. Las leyendas ilegibles o ambiguas requieren revisión antes de
extraer puntos, con incertidumbre de digitalización independiente de la
incertidumbre del ensayo.

**Cierre: selección resuelta; aptitud global PARCIAL. Adquisición externa
puntual pendiente. No hay validación predictiva nueva ni configuración
ejecutable autorizada por esta selección.**
