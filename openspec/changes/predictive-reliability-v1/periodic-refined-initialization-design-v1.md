# Siguiente malla periódica: diseño de inicialización verificable

2026-10-27. Preparación sin ejecución. Depende de PASS de auditoría27–30.
No campaña de tres mallas ni incorporación al producto.

## Caso y transferencia

Primer destino88, mismo motor sintético/A9000 y formulaciones opt-in. Origen
checkpoint30 original44 y referencia periódica auditada, no checkpoint25 ni
un transitorio refinado previo. Nueva identidad diagnóstica con hash de origen,
configuración numérica nueva y fuente; conservar todos los originales.

P0 conservativo directo, geometría frustum exacta y superficies térmicas
repartidas por geometría con h/Tw intactos. Validar con el checkpoint30 real,
no asumir que los tests sobre25 cubren sus valores. Comparar masa/energía y
especies globales y por padre, momento, presión, temperatura y composición;
restricción inversa al mismo estado fuente hasta roundoff. Mantener active
combustion event, su historia y baseline de ledgers; no crear quemado nuevo.

No es reanudación nativa entre mallas. El constructor genera la identidad de
destino y el checkpoint original sigue siendo incompatible con restore nativo
del destino. No modificar esos controles. Es una nueva inicialización del
mismo motor/RPM para verificación, no warm start V3 entre RPM.

## Reloj físico y detector: dependencia concreta

El checkpoint30 en TDC contiene combustión que comenzó antes del TDC. Resetear
ángulo no envuelto o reloj sin transformar eventos rompería esa historia.
Conservar por ello el reloj físico10800° y los eventos existentes.

Sin embargo, `PeriodicDetectorV2.update` exige índices contiguos desde1. El
primer ciclo completo del nuevo diagnóstico es absoluto31, relativo1. No se
puede pasar31 a un detector vacío ni reutilizar el detector periódico44.

La instrumentación debe obtener observables con fases absolutas originales
(usando31 para comprobar10800→11160°), y registrar **dos índices explícitos**:
absoluto31 para procedencia/física; relativo1 para el contador de la nueva
corrida y su detector. La correspondencia se congela en el manifiesto.
No cambiar ángulos, eventos, observables, configuración hash ni umbrales para
normalizar ese índice administrativo. Incluir tests de restart del detector,
contigüidad y rechazo de desfases antes de avanzar un paso.

## Primera ventana y decisiones

Preparar máximo6 ciclos nuevos88 y300s de pared, checkpoints/receta/detector
por ciclo; preflight16MiB+reserva2GiB. Mantener receta adaptativa, CFL y criterios
originales. Preservar explícitamente la diferencia entre medias conservadas y
variables derivadas. Detener por conservación/admisibilidad o presupuesto.

Registrar error/tolerancia por región y variable, lag1/2, inventarios,
composición, trabajo/IMEP y caudales. Si no hay contracción suficiente o hay
estancamiento sostenido, analizar antes de otra ventana. No asumir que seis
ciclos alcanzan periodicidad ni ejecutar176 automáticamente.

Sólo cuando cada malla tenga su propio período admitido, comparar magnitudes
periódicas en las mismas fases/volúmenes. Mantener el control temporal separado;
el paso reducido transitorio no certifica el período. GCI/Richardson requieren
tendencia justificable, no se fuerzan con trabajo no monótono.

No modificar MUSCL, HLLC, acoplamiento, salida o cierres físicos por diferencias
entre mallas sin un defecto reproducido. Ningún resultado sintético es validación
experimental. rc7 intacta y baseline predictiva todavía no establecida.
