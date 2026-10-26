# Acoplamiento físico: formulación transónica V2 y diagnóstico integrado

## Alcance y procedencia

Se conservaron V1, su contrato y sus 37 casos no admitidos. Baseline rc7 intacta:
fuente `fc27542155840cdadbcc2b591ae5cd8e99031899`, ZIP SHA-256
`2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`.
El acoplamiento histórico sigue siendo el valor predeterminado. No hubo builds,
campañas RPM, warm start, limpieza, modificación de históricos ni push.

El relevamiento histórico verificó hashes de los seis resultados y sus bindings:
48 extremos de conducto, 24 abiertos, cero casos no admitidos al cierre de ciclo.
**Esto no prueba ausencia durante blowdown.** Los diagnósticos históricos no
guardan rho/u/T en esos extremos; sus checkpoints sólo representan fase 0°.
No se reconstruyeron estados instantáneos que no están registrados.

## Cambio de formulación, explícito

V2 es `EQUIVALENT_IDEAL_NOZZLE_CONNECTION_CANDIDATE_V2`: una **tobera ideal
equivalente**, no la expansión brusca separada de V1. Segmentos isentrópicos,
garganta efectiva Cd*A aplicada una vez y choque normal con aumento de entropía.
El perfil divergente equivalente es una hipótesis `STANDARD_V1`; no demuestra la
geometría del chorro real, su separación ni las pérdidas de la lumbrera. Un Cd
identificado para otro modelo no queda automáticamente validado para éste.

En entrada subsónica se resuelven las características con entropía y entalpía del
donante. Con garganta estrangulada, la rama con choque interno conserva caudal y
H0; su pérdida de presión total determina un área de choque entre At y Ap. No se
inventa una posición axial. La entrada supersónica se prescribe sólo cuando todas
las ondas del Riemann exacto se propagan hacia el conducto o quedan estacionarias.
La salida supersónica queda libre mientras un choque no pueda propagarse hacia
el conducto; si hay unstart, se resuelve la compresión admisible. La pared cerrada
incluye la presión dinámica de reflexión, conservando flujo de masa/energía cero.
El CFL incluye características del extremo y señales de choque. Vacío o ausencia
de rama admisible producen errores explícitos; no hay recorte de caudales ni
fallback oculto al modelo anterior.

En el contraejemplo mínimo: la raíz algebraica antigua sin límite de Mach pedía
M=1,06104, sin justificación causal. V2 selecciona M=2,16083 por la relación de
áreas y el problema de ondas; la señal más a la derecha viaja a -150,40047 m/s
(coordenada saliente), con caudal entrante 0,0576073893 kg/s. No se conservó una
característica saliente incompatible con entrada supersónica.

Los 1008 estados del barrido tienen solución: los 37 casos anteriores quedan
resueltos **dentro de esta hipótesis distinta de cierre**. Residuo máximo de caudal
crítico 1,78e-15 relativo, energía 5,56e-16; compatibilidad acústica subsónica
6,26e-13 m/s. Las pruebas incluyen Sod, Rankine-Hugoniot, entropía, orientación,
choques internos/estacionarios, transiciones, vacío y datos inválidos.

## Integración y diagnósticos preregistrados

Selector en `geometry_identity.port_connection_model`, serializado, protegido y
ligado a hashes. Las ocho conexiones cilindro/cárter/láminas/transfers/escape
usan el selector en ambas etapas SSPRK2; la reacción de cara completa no recibe
otra suma de presión del área bloqueada. La red de volúmenes externos conserva
su modelo anterior, fuera de este selector. Los checkpoints de modelos distintos
se rechazan; no se alteran hashes para recuperar evidencia histórica.

Se ejecutaron dos revoluciones de A9000 desde la configuración inicial original,
sin restaurar estados periódicos. Mismo motor, física restante, especies, CFL y
combustión. Resultados **transitorios**, sin afirmación de potencia estacionaria:

| Magnitud, dos revoluciones | Anterior 0,5° | V2 0,5° | V2 0,25° |
|---|---:|---:|---:|
| Trabajo cilindro hacia cigüeñal, J | 14,6516 | 31,8770 | 31,9364 |
| Trabajo cárter hacia cigüeñal, J | -3,0005 | -5,7992 | -5,7994 |
| Calor de combustión, J | 136,0990 | 159,5476 | 159,6904 |
| Tiempo de cálculo, s | 6,8826 | 23,2750 | 44,4822 |

La mayor diferencia normalizada 0,5°/0,25° fue 0,00059114 (0,059114 %), en una
fracción de especies del escape. Densidad/presión/temperatura usan error relativo;
velocidad se normaliza por velocidad del sonido; especies por fracción absoluta,
evitando dividir inventarios casi nulos. Criterio previo: <=1 %.

Residuos globales normalizados de masa, energía y especies <=1,45e-15; restauración
y siguiente paso idénticos entre ejecución original y checkpoint. Los registros
primarios contienen ambas etapas y estados en extremos. La entrada supersónica
no apareció en este diagnóstico breve; su verificación procede de casos
manufacturados y el barrido, no de una supuesta observación en el motor periódico.

## Incidencias conservadas y limitaciones

El primer observador comparaba listas JSON con tuplas Python como si fueran
valores físicos distintos; se corrigió la comparación estructural, sin tolerancia
numérica. El primer piloto V2 se detuvo a 193° por cancelación al invertir p0-p
en una salida lenta de sección completa. Se resolvió con área–Mach/presión de
garganta, sin invertir esa diferencia casi nula; el estado exacto es regresión.
Ambos intentos y los checkpoints se preservan. Las repeticiones son diagnósticos
cortos de correcciones demostradas, no campañas periódicas.

V2 cuesta aproximadamente 3,38 veces más cálculo en este diagnóstico: las raíces
anidadas todavía no están optimizadas. Se priorizó la fidelidad de las relaciones
y su verificabilidad, sin reclamar una mejora de rendimiento. No está identificado
el cierre real de pérdidas de las lumbreras; conservación y solución transónica
no equivalen a validación experimental. No se cambia la baseline de producto.

Evidencia: `historical-port-survey.json`, `transonic-v2-receipt.json`,
`integrated-port-v2-comparison.json`, recibos por caso y summaries de `runlogs/`.
Los streams primarios `.jsonl.gz` permanecen locales con SHA-256 en los recibos;
no se duplican en Git. Los checkpoints compactos y configuraciones son pequeños.
La codificación gzip se aplicó sólo a evidencia recién generada; no a históricos.
Esta revisión es **SELF_REVIEW**, nunca revisión independiente ni validación
predictiva. El avance dependiente es verificar discretización espacial.

El replay numérico L2 de la segunda revolución reprodujo 728 pasos aceptados y
las propuestas nominales rechazadas, verificando ambas etapas sin tolerancias
adicionales. El productor y `audit_integrated_cycle_primary` dieron PASS:
`nozzle-cycle2-replay-audit.json`. No se duplicó el stream primario. Los intentos
de instrumentación fallidos están conservados en los summaries: registro inicial
incompleto de rechazos, reconstrucción de dt en vez de usar el dt original y
normalización de una ruta al serializar el recibo; no se relajó la auditoría.

Regresiones P4–P8: **301 PASS, 3 SKIP**, con la raíz externa original de artefactos
configurada; 4 advertencias de deprecación NumPy preexistentes. Pruebas focalizadas
nuevas: **352 PASS**. Suite del motor integrado más referencias transónicas:
**309 PASS** antes del último endurecimiento, complementada por las pruebas
focalizadas y el replay completo posterior. No sumar conteos como casos únicos.

Pendiente antes de cerrar la selección: endurecer la versión de configuración
para que lectores anteriores no puedan ignorar el selector nuevo. Los resultados
numéricos anteriores permanecen ligados al código productor que realmente se usó.
