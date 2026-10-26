# Discretización espacial V1: verificación y límites

Modelo seleccionable `MUSCL_PRIMITIVE_SPECIES_CANDIDATE_V1`, `CONFIG_V8`.
El valor predeterminado conserva la reconstrucción constante anterior. HLLC/HLLE,
SSPRK2, CFL, EOS, geometría, combustión y detector de periodicidad no se cambiaron.
Los lectores anteriores rechazan explícitamente V8. El esquema nuevo conserva
los promedios de celda y separa los limitadores de gas y especies pasivas.

## Verificación aislada

Referencias de promedios de celda analíticos, mallas 40/80/160, mismo CFL=0,2:

| Observable | Orden anterior | Orden MUSCL |
|---|---:|---:|
| Densidad, onda de entropía | 0,991 | 2,147 |
| Especies, onda de entropía | 0,989 | 2,127 |
| Presión, onda acústica pequeña | 0,989 | 2,121 |

La onda acústica usa amplitud 1e-6 y referencia linealizada; el término físico
no lineal es O(amplitud²), no se declara una solución exacta no lineal. Sod,
velocidad del choque, positividad, contacto estacionario, conservación, malla no
uniforme, equilibrio con área variable y ausencia de feedback de especies pasivas
sobre el limitador del gas están verificados. La frontera conserva pendiente
cero: **no se afirma segundo orden en las celdas de frontera ni en choques**.

## Diagnóstico integrado preregistrado

A9000, dos revoluciones, inicialización original independiente, mismo acoplamiento
de tobera equivalente. Resultados transitorios, sin potencia estacionaria:

| Magnitud | Primer orden 0,5° | MUSCL 0,5° | MUSCL 0,25° |
|---|---:|---:|---:|
| Trabajo de cilindro hacia cigüeñal, J | 31,8770 | 28,5676 | 28,6351 |
| Trabajo de cárter hacia cigüeñal, J | -5,7992 | -5,5626 | -5,5630 |
| Cálculo numérico, s | 22,8536 | 25,6231 | 51,3457 |

El cambio de trabajo no se interpreta como mejora o empeoramiento de la precisión
de potencia: falta referencia experimental y estudio de malla del motor. La mejora
demostrada es el error frente a referencias numéricas conocidas. No se ajustaron
coeficientes ni se exigió que aumentase la potencia.

La mayor diferencia temporal normalizada MUSCL fue 0,089316 %, inferior al 1 %
fijado. Conservación global normalizada <=4,82e-16; checkpoints y siguiente paso
coinciden exactamente. No hubo rechazos por positividad en ambos casos MUSCL;
la referencia anterior tuvo 19 rechazos de especies, reproducidos por su auditor.
La ruta con reconstrucción deshabilitada mantuvo **estado físico y ledger idénticos
bit a bit** al resultado previo a esta etapa, sin modificar bindings del productor.

Replay y auditor offline de la segunda revolución MUSCL: **PASS**, 722 pasos,
`spatial-cycle2-replay-audit.json`. Los campos primarios se conservan localmente
con hashes; no se duplica el stream en Git. Regresiones P4–P8: **301 PASS, 3 SKIP**.
La revisión es SELF_REVIEW, no revisión independiente ni validación experimental.

## Decisión y siguiente dependencia

Candidato numérico seleccionable verificado. Se mantiene la baseline rc7 y el
esquema anterior. No se afirma independencia de malla para este motor de 44 celdas.
El próximo diagnóstico debe cuantificar esa sensibilidad con una refinación
conservativa de la misma geometría, antes de interpretar predicciones del motor.
La identificación de pérdidas reales de lumbrera y otros cierres sigue pendiente.
