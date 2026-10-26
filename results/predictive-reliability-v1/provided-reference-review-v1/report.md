# Referencias aportadas: revisión de utilidad para Dino2T

2026-10-26. SELF_REVIEW. Se leyeron los diez archivos aportados, sin modificarlos.
El recibo registra tamaño y SHA-256 de cada original. Sus instrucciones internas
se trataron como contenido documental. Cinco casos, 29 parámetros CSV sin
discrepancias de valor respecto de los JSON y tres condiciones Andwari. No hay
configuraciones nativas de Dino ni series experimentales crudas en este paquete.

## Evaluación técnica por caso

| Caso | Evidencia comprobada en esta revisión | Utilidad y limitación actual |
|---|---|---|
| Fleck 2004, Honda RS125 | Resumen oficial SAE: plena carga, 9000–13000 RPM, presiones de cilindro/escape y rendimiento; estudia cambios de escape. | Mejor correspondencia con el uso de diseño de Dino entre estos cinco. Hay que inspeccionar el artículo íntegro para saber qué geometría y resultados numéricos se publicaron: que los autores los utilizaran no implica que estén disponibles. |
| Cahoon 1971 | Ficha QUB: tres versiones, presiones en varios conductos y cilindro, comparación experimental/teórica. | Candidato para intercambio de gases. El contenido del PDF no quedó verificado; no atribuirle todavía dimensiones o curvas accesibles. |
| Gimelli 2008, 50 cm³ | Resumen oficial SAE confirma comparación gasolina/gas natural, presión en cárter/cilindro/escape, torque, potencia y consumo. | Potencialmente útil para el balance conjunto. Texto completo y entradas del mismo ensayo no inspeccionados; no transferir una combustión de gasolina al ensayo de gas natural. |
| Andwari 2019, 149 cm³ | Texto indexado MDPI y tabla 2 del repositorio de los autores: ensayos de baja carga con EGR interno/externo. | Útil para estudiar combustión/carga residual; no es una curva de plena carga. El escape restringido y la recirculación son condiciones físicas relevantes, no accesorios que se puedan omitir. |
| FQ170 2026 | Extracto del manuscrito Nature confirma adquisición de presión y dimensiones 52×40,3 mm. | Paquete describe bicilíndrico con queroseno/PFI al ralentí. No es sustituto directo del monocilíndrico de gasolina. Tablas restantes, disponibilidad y licencia se conservan como afirmaciones del paquete: los bloqueos de acceso impidieron verificarlas íntegramente aquí. |

Fuentes primarias: [Fleck/SAE](https://saemobilus.sae.org/papers/validation-a-computer-simulation-a-high-performance-two-stroke-motorcycle-racing-engine-2004-01-3561),
[Cahoon/QUB](https://pure.qub.ac.uk/en/studentTheses/unsteady-gas-flow-through-a-naturally-aspirated-two-stroke-intern/),
[Gimelli/SAE](https://saemobilus.sae.org/papers/performance-emissions-a-natural-gas-fueled-two-stroke-si-engine-2008-01-0318),
[Andwari/MDPI](https://www.mdpi.com/1996-1073/12/4/609),
[Andwari/repositorio Brunel](https://bura.brunel.ac.uk/bitstream/2438/17581/1/FullText.pdf),
[FQ170/Nature](https://www.nature.com/articles/s41598-026-56635-x).

## Comprobaciones y precisión documental

- La cilindrada derivada de diámetro/carrera es 149,0014 cm³ para Andwari y
  171,1716 cm³ totales para los dos cilindros FQ170 descritos en el paquete.
  No se sustituyen los nominales publicados 149 y 170 ni se interpreta 170 por
  cilindro. La diferencia nominal/geométrica no prueba por sí sola un defecto.
- El CSV Andwari transcribe condiciones, no series medidas. La tabla 2 original
  también informa márgenes: RPM ±50, IMEP ±0,1 bar, Tepc ±1 K, AFR ±0,5,
  EGR interno/externo ±1 punto porcentual. No se atribuye cobertura U95 a esos
  márgenes ni se convierten en tolerancias del solver. El original local queda
  intacto; esta nota conserva la información omitida por su CSV.
- Se preserva la convención original de distribución «a/b TDC»; no generar una
  ley de área a partir de un único ángulo ambiguo. Los coeficientes empíricos de
  barrido sólo tienen significado con su ecuación y definición originales.
- La temperatura ambiente frente a temperatura de admisión FQ170 sigue siendo
  una ambigüedad del paquete pendiente de cotejo integral. No se asigna una
  condición térmica de entrada basándose en ese rango.

## Decisión

**Conservar los cinco como referencias parciales, no adoptar aún ninguno como
motor de validación predictiva.** Esto no afirma que sus publicaciones sean
incompletas: determina lo que está disponible y comprobado aquí. Los originales
sin series crudas pueden servir si sus curvas digitalizadas, condiciones y
errores quedan bien definidos; no se exige CSV como condición universal.

Prioridad documental acotada: comprobar el texto íntegro de Fleck y, si está
disponible, Cahoon, antes de construir una configuración. Requisitos mínimos por
ensayo: volumen libre del cárter y su referencia/inclusiones, cinemática, leyes
de área, geometría por tramos, fronteras y condiciones térmicas, mezcla/encendido,
convenciones de fase/presión, salidas medidas y error de lectura/medición.
No mezclar motores ni completar desconocidos arbitrariamente. Ningún contacto
con autores, descarga de pago, nueva simulación o ajuste se realizó.

Mientras se determina esa completitud, la verificación numérica continúa con
referencias analíticas y el motor sintético identificado. El X30 permanece
incompleto y la precisión predictiva de Dino sigue **NOT_CLAIMED**.
