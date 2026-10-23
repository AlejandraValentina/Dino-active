# Referencia experimental seleccionada: IAME X30 Senior

## Decisión cerrada

Seleccionar **un IAME X30 Senior, monocilíndrico de admisión por láminas**, ligado al ensayo de Ortenzi y Bossaglia (2023), como única referencia para el próximo hito. Es la combinación más útil encontrada de documentación dimensional oficial, arquitectura representable y potencia experimental publicada. No se adopta una potencia comercial como dinamómetro.

**Estado: REFERENCIA SELECCIONADA; DATOS DEL EJEMPLAR/ENSAYO PENDIENTES; NO HABILITA TODAVÍA VALIDACIÓN CUANTITATIVA.** Se puede iniciar la adquisición de datos de este motor, no una simulación supuestamente validada. No se sigue buscando indefinidamente otro candidato ni se implementa una configuración nominal mezclando revisiones.

Revisión limitada a cuatro conjuntos de datos. Cero simulaciones, modificaciones del solver, coeficientes o funcionalidades. No se reabrió STANDARD_V1. Fuentes originales descargadas fuera de Git y hashes en sources.json. Revisión SELF_REVIEW, no independiente.

## 1. Candidatos contrastados

|Candidato|Evidencia efectivamente accesible|Decisión|
|---|---|---|
|IAME X30 Senior|Ficha dimensional oficial descargada y artículo experimental original accesible|Seleccionado: documentación verificable más completa para un monocilíndrico compatible. Faltan entradas del ejemplar ensayado y metrología del banco.|
|Honda RS125, SAE 2004-01-3561|Registro institucional y resumen; no se obtuvo texto/datos originales completos|Buen candidato físico, pero no ofrece ahora una base reproducible accesible. No se afirma que los datos no existan.|
|Yamaha KT100, Gore 2024|Índice experimental público; descarga directa actual HTTP503|No fue posible verificar suficientemente los métodos/entradas completos. No se reconstruye desde citas parciales ni se reabre el caso KT100 histórico.|
|Motor V2 del estudio de Van Niekerk 2002|Tesis completa descargada, con entradas de EngMod2T y ensayo de escapes|Descartado para este objetivo: es bicilíndrico y la comparación absoluta normaliza la potencia medida al máximo simulado; no satisface la referencia monocilíndrica independiente solicitada.|

La [tesis original de Pretoria](https://repository.up.ac.za/bitstream/handle/2263/29152/Complete.pdf?sequence=3), pp.35–40 y apéndices G/H, es una advertencia útil: aunque contiene mucha geometría y pruebas de escapes, su potencia es a rueda, usa una corrección que el propio autor cuestiona y reescala la curva para igualar el máximo. No se heredan esas correcciones como validación de Dino. Tampoco se corrige silenciosamente su discrepancia de carrera entre tabla y archivo de entradas.

Para Honda se verificó el [registro QUB de la publicación](https://pure.qub.ac.uk/en/publications/validation-of-a-computer-simulation-of-a-high-performance-two-str/). Para KT100 se intentó nuevamente el [PDF institucional de Gore](https://repository.lib.ncsu.edu/bitstreams/24433484-a6eb-4ad8-80f1-a18fa75c4ef6/download); su falta de acceso no demuestra falta de datos en la tesis.

## 2. Datos del motor seleccionado

**Fuentes:** [IAME, homologación 254/V](https://www.iame-motorsport.com/files/noticeboard/254V_IAME-X30-125cc-LIMIT.-16000-giri-MOTORE-REV.05-AGG2021_21032024111116.pdf), páginas1,4–6,9–11; [Ortenzi y Bossaglia, Energies2023](https://www.mdpi.com/1996-1073/16/13/4947), figuras7–10 y declaración de disponibilidad.

|Entrada|Disponible|Clase de conocimiento / faltante|
|---|---|---|
|Diámetro, carrera, biela|54, 54 y 102 mm|Nominales oficiales; confirmar dimensiones del ejemplar del ensayo.|
|Cilindrada|123,67 cm³ nominal|Derivable de diámetro/carrera; no sustituye medición del ejemplar.|
|Distribución|Escape máximo177,5°; transferencias126±2° y127±2°; planos y límites de anchos|Restricciones de homologación, no mapa área–ángulo medido del motor publicado.|
|Cámara|Volumen reglamentario mínimo9,7 cm³, con inserto de verificación; dibujo de culata|No se copia automáticamente como volumen operativo en PMS. Faltan volumen real ensamblado y convención de medición.|
|Cárter|Plano parcial|No determina por sí solo el volumen libre ensamblado ni su compresión primaria.|
|Admisión|Tillotson HW-27A, venturi27 mm; caja y láminas dibujadas|Faltan variante real, rigidez, levantamiento y descarga efectivos.|
|Escape|Planos acotados y montaje Senior|Falta identificar revisión, longitudes instaladas y silencioso exactos del ensayo.|

No se estimó ningún valor faltante para completar la tabla. Los límites reglamentarios no son distribuciones de incertidumbre ni valores medidos. No se transforma una duración de lumbrera en un ángulo de apertura sin verificar su convención y el mapa real.

El artículo presenta potencia **medida y simulada separadamente** en figura10. Su simulación utiliza lambda0,85 y encendido22°BTDC; no equivale a demostrar que cada condición del banco haya sido medida y documentada. El archivo numérico, correcciones e incertidumbres del ensayo no están publicados en el material accedido; se declaran restricciones de datos. No se encontraron trazas experimentales de presión del X30 allí. Las variaciones de escape de figuras13–14 son simulaciones: no constituyen ensayos A/B medidos. Una curva de torque derivada de potencia/RPM no sería una segunda medición independiente.

La ficha actual y el plano reproducido en el artículo tienen diferencias dimensionales de revisión. Algunas tolerancias pueden superponerse, pero eso no identifica el escape ensayado. Se debe obtener la ficha o medición exacta, en lugar de combinar el cilindro de una revisión con el escape de otra.

## 3. Encaje con Dino actual

La topología monocilíndrica, el cárter de precompresión, admisión por láminas, transferencias y escape por ondas corresponden a componentes existentes. Los tres caminos de transferencia son particularmente próximos al conjunto actual. No requiere otra arquitectura de barridos, Desktop ni un núcleo gasdinámico nuevo.

Esto no demuestra equivalencia física completa: los coeficientes de descarga y la dinámica de láminas no se deducen sólo de un dibujo; el cierre de barrido sigue siendo reducido. Los contornos de lumbreras y las uniones del escape requieren reducción dimensional explícita y comprobación de áreas/volúmenes. El silencioso perforado y las pérdidas de sus transiciones no son automáticamente un tubo liso equivalente. Cualquier aproximación debe declararse antes de contrastar y no corregirse mirando la potencia objetivo.

## 4. Paquete mínimo a conseguir, sin nueva búsqueda abierta

**Primer camino: un pedido único de datos a los autores originales** Fernando Ortenzi (ENEA) y Andrea Bossaglia (IAME), mediante las filiaciones/contactos de la publicación. No se enviaron mensajes. Solicitar el paquete del **X30 Senior del ensayo**, preferentemente a **9000 RPM, WOT**, no la curva del modelo ni una cifra de catálogo:

1. Identificación del ejemplar y revisiones de cilindro, culata, juntas, admisión y escape; archivo de geometría utilizado y mediciones reales de volumen PMS/cárter, puertos, conductos y montaje.
2. Condiciones de ese punto: presión/temperatura/humedad de admisión, mariposa, combustible y aceite, caudales de aire/combustible o AFR medido, encendido efectivo, refrigeración y temperaturas relevantes.
3. Datos originales de RPM y torque/potencia: ubicación del plano de medida, norma/correcciones, accesorios incluidos, calibración, repetibilidad e incertidumbre. Si9000 no es un punto medido, identificar la RPM exacta disponible antes de definir el ensayo; no interpolar para crear una medición.
4. Si existen: mapas de descarga, caracterización de láminas, barrido y pérdidas mecánicas obtenidos independientemente de esa potencia; presión angular de cilindro/escape con posiciones, calibración y referencia PMS.

No se exige que todos los coeficientes de un modelo sean medidos para publicar una discrepancia de un modelo congelado. Sí se exige distinguir parámetros no identificados de entradas físicas reales, y no convertir su ajuste posterior en una predicción independiente. La identificación ausente no puede ocultarse ampliando arbitrariamente la banda de incertidumbre.

**Si el paquete no se libera:** mantener el mismo candidato y medir un X30 identificado, sin buscar otro fixture sintético. Mínimo práctico:

- Metrología de un solo ejemplar: alesómetro/calibre, carrera y biela; bureta con montaje/temperatura documentados para PMS y cárter en ángulo conocido, descontando útiles; mapa de lumbreras con alturas, radios y disco graduado; secciones/longitudes reales de admisión y escape, incluyendo juntas y salidas.
- Caracterizar láminas por fuerza–levantamiento y tope, y descarga en banco de flujo con Δp/caudal. Son datos de componente, no coeficientes ajustados al dinamómetro.
- Un punto estabilizado a9000RPM WOT en banco de motor, con torque/RPM calibrados y al menos tres registros independientes de estabilidad/repetibilidad, caudales y condiciones térmicas/ambientales. Preferir plano de salida directo; un dato a rueda no es intercambiable sin pérdidas medidas.
- Para desambiguar combustión y llenado: p_cilindro(θ), PMS trazable, p_escape(θ) y posiciones; promedios y dispersión ciclo a ciclo. El torque por sí solo no identifica barrido, pérdidas y liberación de calor separadamente. Si es imprescindible identificar atrapamiento, usar una medición independiente de retención/trazador; no inferirlo ajustando HP.

No se autorizan ahora compra, instrumentación ni ejecución de ese ensayo. Es el conjunto finito necesario si no se obtiene el registro existente. Presión angular es valiosa para diagnosticar y validar el ciclo, pero su ausencia no invalida por sí sola una primera comparación de potencia bien condicionada. El dato no sustituible es la geometría/condición del **mismo motor** y una medición trazable en el mismo plano.

## 5. Criterio objetivo de comparación

### Independencia y alcance

Congelar configuración, entradas, parámetros no identificados, solver y criterio antes de ejecutar la predicción. Reservar el punto medido como comprobación: no usar su potencia para ajustar fricción, barrido, descarga o combustión. Si una Wiebe se identifica con la presión del mismo punto, esa presión y el trabajo derivado dejan de ser validación independiente de combustión; sólo cabe un contraste de subsistemas explícitamente limitado. Los datos de caracterización deben ser de componentes u otro punto no reservado.

Comparar régimen/carga, combustible, geometría, estado térmico y plano de potencia coincidentes. Sin pérdidas medidas, no convertir potencia a rueda en potencia al eje mediante un porcentaje supuesto. Nada de normalización del máximo, traslación angular o multiplicadores para mejorar concordancia.

### Magnitudes y errores

A la RPM realmente medida:

- E_P=P_Dino−P_exp y e_P=E_P/P_exp; lo mismo para torque.
- Convención2T: P=2π·n·T/60 y BMEP=2π·T/Vd. La correlación entre estas magnitudes se conserva: potencia, torque y BMEP derivados del mismo sensor no son tres validaciones independientes.
- Con presión: IMEP=∮p·dV/Vd, presión máxima y su fase, y error de forma RMS sobre una ventana angular declarada de360°. Mantener referencia PMS y calibración absolutas; no realinear las curvas buscando menor error. Informar incertidumbre de integración, fase y transductor.

### Incertidumbre y decisión

La [guía NIST TN1297](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-5-combined-standard-uncertainty) combina incertidumbres estándar y covarianzas; su [sección6](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-6-expanded-uncertainty) explica incertidumbre expandida. El factor de cobertura debe justificarse; k≈2 no garantiza95% en cualquier distribución o muestra pequeña.

Para el error, u_val²=u_exp²+u_entradas²+u_num² sólo cuando esas contribuciones sean independientes; en otro caso incluir covarianzas. Estimar repetibilidad/calibración y propagación de entradas medidas, además de error numérico. Tolerancias de periodicidad no son una estimación de u_num. Parámetros sin rango defendible permanecen NO IDENTIFICADOS; no se les inventa una distribución uniforme. La discrepancia estructural del modelo no se suma a la incertidumbre para excusar su error.

**Criterio técnico inicial fijado para una futura comparación local de potencia:** error absoluto conservador |E_P|+U95_val ≤5%·|P_exp|, con U95_val/|P_exp| ≤2%. El5% es una exigencia de ingeniería propuesta para esta primera referencia, no una norma atribuida a SAE o una precisión ya demostrada. Los márgenes se fijan ahora y no se amplían al ver la predicción. Si no hay incertidumbre defendible, resultado INDETERMINADO; si hay error incompatible, NO CONCORDANTE EN ESE PUNTO. Informar además si cero queda dentro de E_P±U95_val, sin usar una banda enorme como prueba de precisión.

No se introduce ahora una campaña de resolución. La incertidumbre numérica pendiente impide satisfacer formalmente el criterio; una comparación preliminar podría informar errores sin proclamar precisión del5%. La presión, si se obtiene, se evalúa con sus errores y bandas propias y sin inventar un umbral universal de forma de onda. Aprobar un único punto tampoco validaría una curva completa, ni demostraría capacidad de discriminar mejoras del2–3% entre escapes.

## 6. Resultado entregado

**Motor único: IAME X30 Senior.** Se verificaron documentación primaria del fabricante y una curva experimental de publicación original. Su representación topológica es viable con Dino, pero aún faltan los datos específicos que vinculen geometría, condiciones e incertidumbre con el motor del banco.

**Decisión:** comenzar la adquisición concreta de ese paquete; no comenzar todavía una validación cuantitativa. El próximo resultado admisible será una predicción congelada contrastada contra un registro independiente del mismo motor, sin ajuste posterior. Este trabajo termina con la selección y el pedido/medición mínimos definidos; no abre otra investigación general ni autoriza simulaciones.
