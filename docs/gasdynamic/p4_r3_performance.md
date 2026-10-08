# P4-R3 — optimización sin cambio científico

Orden5e36dbe4 acepta R2/P4B, no P4. Referencia escalar intacta:
motorsim/exhaust1d.py y motorsim/hybrid_exhaust.py. Receipt de aceptación
congela también benchmarkR2 y contratoP4C. Sin UI/JSON/P5 ni compilados.

## Perfil previo, antes de cambios mayores

Tres ventanas100µs con cProfile: apertura inicial, combustión350°, reapertura
cercana480°. MismaN250/CFL.4; la última usa snapshot reconstruido únicamente
para perfilar, no como checkpoint. No nueva campaña baseline completa:
se conserva263,328s y35379RHS/8861357HLLC/0HLLE históricos. CPU/RAM/cuentas
detalladas sólo para las ventanas nuevas; no inventar valores históricos.

Ventanas:17,531s instrumentados,591RHS; las cifras incluyen overhead de cProfile.
Costes inclusivos: primitivas30,67%, HLLC28,44%, MUSCL19,88%, fuentes0D3,47%,
CFL2,59%. Son ramas anidadas; no sumarlas con EOS ni validaciones internas.
Top self: generadoresEOS13,95%, all11,01%, validateEOS8,18%, comprensiones
exhaust7,52%, generadoresexhaust7,57%, HLLC6,52%, isfinite6,27%, MUSCL5,15%.

Clasificación aproximada, con solapamientos explícitos:
A matemática: HLLC/MUSCL/CFL ~51% inclusivo, mezcla operaciones y overhead.
B redundancia:2036 conversiones de malla frente a unos806 estados nuevos,
~60% de conversiones repetidas, potencial~18% del total instrumentado.
C objetos: comprensiones/generadores visibles >29% self, incluye aritmética;
no es una medición aislada del allocator. Conteo de allocations no disponible.
D evidencia: observe~12% inclusivo, principalmente primitivas ya contadas;
escritura gzip fuera de ventanas. No se eliminará evidencia contractual.
E bucles escalares vectorizables: las ramas primitivas/HLLC/MUSCL dominan ~79%
inclusivo. Esto satisface la condición de autorización NumPy del apartado8.
F geometría: CFL~2,6% inclusivo incluye widths recalculados; geometría0D es
menor y se cacheará sin alterar sus fórmulas. No atribuir todo ese2,6% a geometry.

## Bloques y equivalencia

Bloque1: caché acotada de primitivas por identidad de arrays inmutables,
geometría inmutable y fuentes0D por estado/tiempo idénticos. Mismas fórmulas,
validación de cada estado nuevo y SSPRK2. SCALAR_REFERENCE sigue disponible.
Comparar ciclo completo contra artifactR2 antes de continuar; perfil intermedio.
Bloque2 condicionado al perfil: batching float64 NumPy, mismas ramas/fallbacks.
No cambios CFL/eventos/reintentos/precisión/umbrales ni pérdida de ledgers.

Equivalencia: exigir mismo número de pasos/stages y eventos, mismos gates.
Para cambios de orden aritmético, registrar máximos absolutos/relativos por
campo; referencia de roundoff previa: rtol1e-10, atol1e-13 para estados/flujos
y rtol1e-10, atol1e-8Pa para presiones. Es tolerancia de comparación numérica,
no cambio de gates científicos. Si cambia materialmente, rechazar bloque.
Conservar todas las medidas, no escoger la más rápida. Performance exige
dos ciclos finales<=20s con margen; 20–30s: NEAR_TARGET; >30s:
COMPILED_BACKEND_DECISION_REQUIRED. Sin periodicidad/G2 antes de PASS.

## Bloque1 medido y autorización del batching

G1 completo226,773529s, speedup1,1612×: insuficiente. Equivalencia exacta en
todos los campos comparados, eventos, etapas, conteos y gates. Perfil intermedio
13,709230s instrumentados: HLLC36,67%, MUSCL24,29%, primitivas15,83%, fuentes
cacheadas1,41%. No extrapolar estos tiempos instrumentados al ciclo completo.

NumPy2.3.0 instalado sólo en venv, declarado en requirements-experimental.txt;
no dependencia de la ruta productiva/legacy. Batch EOS/MUSCL/HLLC/CFL y avances
independientes float64, conservando orden algebraico. Fallbacks excepcionales
delegan en HLLC/HLLE escalar congelado, con registros de cara/celda. BC y P3
siguen escalares originales. Inventarios conservan math.fsum.

## Resultado final: decisión requerida

**P4_R3_COMPILED_BACKEND_DECISION_REQUIRED**. Sin performance PASS, periodicidad,
G2 ni aceptación P4. Las dos medidas finales se conservan, sin elegir la mejor.

| Camino | Wall/ciclo, s | CPU, s | Aceleración | Proyección30, s | Pico proceso, MiB |
|---|---:|---:|---:|---:|---:|
| SCALAR_REFERENCE histórico | 263,328 | No registrado | 1× | 7899,840 | No registrado |
| STRUCTURAL | 226,773529 | 226,203125 | 1,161× | 6803,206 | 320,148 |
| NUMPY, medida1 | 35,469199 | 35,406250 | 7,424× | 1064,076 | 328,844 |
| NUMPY, medida2 | 35,443038 | 35,250000 | 7,430× | 1063,291 | 358,707 |

Windows10 build19045, Intel i5-10400,6cores/12hilos, Python3.11.0x64,
NumPy2.3.0 en el mismo equipo. Kernel serial sin multiprocessing/threading.
Wall externo incluye inicialización y postproceso del ciclo; escritura gzip y
comparación quedan fuera. El timer interno también se conserva en el JSON.
Pico de proceso incluye referencia cargada, evidencia, comparación y compresión;
no es memoria exclusiva del integrador. No se midió conteo acumulado de allocations.

El baseline completo no se repitió: se conservaron medida y estados congelados.
Perfil inicial e intermedio sobre tres ventanas representativas (17,531 y13,709s
instrumentados). Perfil NumPy de las mismas ventanas:1,047s. Al hacerse viable,
se perfiló además un G1 completo:63,682498s con cProfile, equivalencia exacta.
Ese tiempo NO participa en el benchmark ni la proyección contractual.

### Hotspots finales, ciclo completo

Porcentajes inclusivos respecto del wall instrumentado; hay anidación, no sumarlos.

| Operación | Llamadas | Inclusivo, s | Self, s | Inclusivo% |
|---|---:|---:|---:|---:|
| RHS | 35379 | 35,3550 | 2,1896 | 55,52 |
| HLLC batch | 35379 | 16,0133 | 7,9180 | 25,15 |
| Evaluación0D cacheada, validación/fuentes/postproceso | 185124 | 15,6165 | 0,6793 | 24,52 |
| Model.evaluate, misses y postproceso | 74874 | 13,7832 | 4,0607 | 21,64 |
| MUSCL batch | 35379 | 7,1739 | 2,4544 | 11,27 |
| EOS primitive batch | 48546 | 4,7734 | 1,4719 | 7,50 |
| BC face_state | 176895 | 3,5041 | 0,8844 | 5,50 |

Los `.prof` y JSON incluyen todas las funciones y top40 self/inclusive/calls.
La evaluación de fuentes para el postproceso acumula8,75% inclusivo en su
comprensión; no se elimina ni oculta ese coste restante.

### Conteos y equivalencia

Cada ciclo completo:13164 pasos aceptados,26328 evaluaciones RHS de etapas
aceptadas,9051 rechazos stage_CFL;35379 RHS totales. HLLC8861357, HLLE0.
MUSCL35379 llamadas/8844750 reconstrucciones de celda; downgrades0.
Conversión a primitivas NumPy:48546 batches/12136500 celdas. Referencia:
123420 conversiones completas/30855000 celdas, derivadas del flujo congelado
y confirmadas por conteos de ventanas (no afirmar cProfile completo baseline).
Perfil completo:51985 llamadas conservative escalares más35379 batches de249
caras;16607 llamadas a coupling,176895 face_state y70758 Boundary.flux.
Los HLLC de caras interiores se evalúan en35379 batches; conteo lógico por
cara se conserva. Fallbacks interiores y downgrades se registran por cara/celda;
puerto registra cara0/conteoHLLE, sin inventar la subrazón interna del puerto.

| Comparación contra R2 | Máximo absoluto | Resultado |
|---|---:|---|
| Estados finales0D/1D | 0 | Exacto |
| p_cylinder y p_port | 0 | Exacto |
| Flujos m/E/F | 0 | Exacto |
| Sensores p/u/M/Y | 0 | Exacto |
| W_indicated | 0 | Exacto |
| Inventarios y ledgers globales | 0 | Exacto |
| Eventos, pasos, etapas, conteos y gates | Sin diferencias | Exacto |

Aplica al bloque estructural, ambas medidas NumPy y perfil completo. Reviewer
también comparó histories/stages completos; no se usó tolerancia para ocultar
diferencias. Balances/admisibilidad coinciden con R2; no nuevo backflow observado.

### Regresiones y corrección de infraestructura

101 tests PASS. Replay offline de3 bancosP4A y16P4B,190 snapshots/finales,
27050 caras: EOS/MUSCL/HLLC/fallbacks exactos. No repetir campañas físicas:
gates históricos aceptados intactos y regresionesP0/P2/P3 PASS.151 hashes y
cinco referenciasR3 intactos. OpenSpec estricto PASS al cierre documental.

La primera regresión falló porque el nuevo archivo gas1d/batch.py ampliaba el
inventario `glob('*.py')` congeladoP2. Se movió a **motorsim/exhaust_batch.py**,
cambiando sólo imports; cuerpo computacional idéntico comprobado y revisado.
No modificar manifiestos ni validadores. Fallo conservado, regresión repetida
PASS. El traslado no necesitó otro benchmark; el perfil completo posterior
también confirmó equivalencia. Los perfiles anteriores conservan el nombre viejo.

### Opciones pendientes de decisión humana

Tomando la medida conservadora35,469199s, falta **1,77346×** adicional o reducir
**43,613%** del wall para20s. Estas opciones no están implementadas ni prometen
una aceleración. El estado no demuestra que futuras mejoras NumPy sean imposibles.

| Opción | Cota/objetivo cuantificado y alcance |
|---|---|
| A: continuar NumPy/estructura | Eliminar todo HLLC (25,15% del perfil) todavía dejaría unos26,55s bajo hipótesis proporcional. Requiere intervenir varios costes, no sólo ese kernel. |
| B: evaluar Numba | Para un RHS que representa55,52%, Amdahl exigiría aproximadamente4,66× en ese bloque con el resto fijo, para alcanzar1,773× global. Requiere autorización y nueva equivalencia. |
| C: extensión compilada | Mismo objetivo global1,773×; incluir coste de interfaz y validaciones. Compilar sólo HLLC no bastaría ni con coste cero bajo ese reparto. Requiere autorización, sin implementaciónC/C++. |
| D: revisar resolución futura | CambiarN/CFL/grados/física no acredita este benchmark. Necesita otra decisión científica y estudio; no se propone una aceleración numérica ficticia. |

Las cotas Amdahl usan reparto **instrumentado**, que puede diferir del wall
sin profiler: son límites orientativos, no predicciones de Numba/C++.
No ampliar600s, no campañaG1 periódica niG2, no checkpoints ficticios, noP5.
