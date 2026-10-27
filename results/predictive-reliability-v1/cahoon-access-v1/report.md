# Cahoon 1971 — evaluación de acceso y reconstrucción, 2026-10-27

Estado **PARCIAL** del material accesible; aptitud predictiva **INDETERMINADA**.
No se ha revisado íntegramente la tesis ni se concluye que falten datos en ella.
El PDF original devuelve HTTP403 con HTML de comprobación del servidor tanto
mediante HTTPS local como con la herramienta web. El navegador normal disponible
para agentes informa “No browser is available”. No se descargó un PDF válido;
no se sorteó la comprobación ni se accedió mediante credenciales ajenas.

La ficha institucional confirma tres versiones, medición de presión en admisión,
transferencias, escape y dos posiciones del cilindro; también caudal inducido y
comparación con THROUGH FLOW. Esto acredita la existencia general de mediciones,
no sus valores, condiciones, escalas o incertidumbre por figura.

Un extracto indexado del propio PDF muestra “ENGINE DETAILS”, posible página
impresa 11, y columnas MK.1/MK.2/MK.3. Los valores provisionales por versión se
preservan en assessment.json con visually_verified=false. Hay indicios concretos
de geometría común, distribución y compresiones diferentes; también aparece una
tabla de escape vinculada a Fig.2.2 con longitudes/diámetros en pulgadas. El OCR
mezcla filas y símbolos. No se transcribieron las dimensiones ambiguas ni se
hicieron conversiones para construir conductos. La página PDF, figura y tabla
exactas requieren cotejo del documento original.

## Lo que debe comprobarse por separado para MK1, MK2 y MK3

| Entrada o resultado | Estado de inspección actual |
|---|---|
| Diámetro, carrera, centros de biela | Valores provisionales indexados, pendientes de página original |
| Pistón, altura de corona/falda, compresión efectiva | Definiciones y esquema pendientes |
| Cárter | Relación de compresión indexada; volumen absoluto e inclusiones no comprobados |
| Lumbreras | Ángulos de apertura indexados; cierre, número, perfiles y ley de área pendientes |
| Admisión, transfers y escape | Esquemas, tramos y correspondencia de unidades pendientes |
| Ensayo | RPM, carga, combustible, AFR, encendido, ambiente y condiciones térmicas pendientes |
| Sensores | Ubicaciones generales en resumen; posiciones exactas, referencia de presión y fase pendientes |
| Caudal, prestaciones y curvas de presión | Existencia en resumen; valores y leyendas measured/calculated pendientes |
| Incertidumbres | No comprobadas en las páginas originales |

## Relaciones utilizables solo tras verificar sus definiciones

La cilindrada se obtiene de pi*B^2*S/4, conservando unidades. Una relación de
compresión de cárter permitiría calcular Vmin=Vbarrido/(rcc-1) únicamente si el
texto confirma rcc=Vmax/Vmin, volumen barrido efectivo y límites/inclusiones del
sistema. No se presume que el volumen barrido efectivo coincida exactamente con
la cilindrada ni se suman transfers dos veces. La cinemática biela-manivela
permite convertir ángulo en desplazamiento con B,S,L conocidos; no identifica
por sí sola el perfil/ancho efectivo ni Cd de una lumbrera. La compresión atrapada
requiere conocer su instante y volumen de referencia antes de derivar el volumen
de cámara. Estas relaciones no sustituyen condiciones de ensayo o pérdidas.

## Decisión y siguiente acción concreta

Ninguna versión está seleccionada como configuración ejecutable. No se generaron
CSV de curvas, datos medidos ficticios ni mezcla entre versiones. La revisión
integral queda pendiente de acceso al PDF, con registro durable de los intentos.
Una copia local legítima del mismo documento permitiría continuar con hash,
recuento de páginas, inventario de todas las tablas/figuras/apéndices y cotejo
visual. La verificación numérica de Dino continúa mediante sus propios casos
sintéticos y analíticos y no depende de completar esta obtención documental.

Fuente original: https://pure.qub.ac.uk/files/612264914/Unsteady_gas_flow_through_a_naturally_aspirated_two_stroke_internal_combustion_engine..pdf
Ficha: https://pure.qub.ac.uk/en/studentTheses/unsteady-gas-flow-through-a-naturally-aspirated-two-stroke-intern/
