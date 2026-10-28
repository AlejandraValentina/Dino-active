# Flujo de lumbreras — decisión de ingeniería

2026-10-28. **Decisión: CORREGIR el uso del cierre Riemann escalado como ley
general de restricción cámara–conducto.** La implementación experimental ya
existente `EQUIVALENT_IDEAL_NOZZLE_CONNECTION_CANDIDATE_V2` reproduce las
referencias ensayadas y se conserva seleccionable. No fue necesario escribir
otra frontera ni modificar el solver. No se activa por defecto ni sustituye rc7.

Esta decisión se limita al cierre físico: **no es un fallo de HLLC como solver
Euler, ni una demostración de la ley de pérdidas de una lumbrera real**. Una
tobera equivalente resuelve un modelo físico explícito; el Cd y la separación
del chorro real siguen sin identificación experimental. No se declara una
mejora de precisión absoluta, potencia periódica o independencia de malla.

## 1. Resultado de inspeccionar el código

### Ruta legacy

`interface_flux` resuelve un Riemann Euler entre el estado del conducto y
`Wc=(rho_c,0,p_c,Y_c)`. El flujo extensivo es:

`G = Aef * F_HLLC(Wc,Wd)` con orientación según la cara.

No resuelve la aceleración desde el remanso hasta una garganta ni separa la
sección de garganta de la sección del conducto. Las ondas de HLLC pueden ser
sónicas/supersónicas; eso **no constituye** una ley explícita de estrangulamiento
en `Cd*Ageom`. Cambiar HLLC por el Riemann exacto no subsana ese cierre.

La geometría calcula `Aef=Cd*Ageom` en mm² y el adaptador convierte a m² una vez.
El integrador limita la conexión por el área disponible del conducto y, en
admisión, por la apertura declarada de láminas. La selección por mínimo de dos
aperturas no es multiplicar dos veces el mismo Cd. **No se encontró doble Cd**
en esas rutas. Las áreas de perfiles `effective_profile` se multiplican también
por el Cd declarado: sus datos deben seguir ese contrato, no volver a incluir
un Cd externo no declarado.

El momento de cara legacy incluye `Aef*Fmom+(Ap-Aef)*pd`. Esto interpreta el
área no efectiva como pared estacionaria; no identifica por separado las
fuerzas sobre un chorro separado o la pérdida irreversible de una lumbrera.
Las dimensiones son correctas (N), pero el cierre físico sigue siendo aproximado.

La cámara recibe masa y energía con signo contrario al conducto en cada etapa
SSPRK2. Su momento axial no se integra: la fuerza tiene reacción externa. La
energía se toma del flujo Euler completo, no se sustituye por `mdot*cv*T`.

En el motor integrado, las cuatro especies extensivas P6 se transportan con el
donante seleccionado por el signo del caudal. Durante el barrido existe el
cierre de expulsión de composición previamente declarado. No se debe identificar
ese transporte con el cuarto escalar pasivo del Riemann. Cada flujo de especies
utilizado se aplica con signos opuestos. No se modificó ese modelo.

### Qué significa el contrato R1

[R1](../../docs/gasdynamic/0d_1d_coupling_r1.md) dice expresamente «conexión
directa a una cara; sin Cd, puerto o apertura». Corresponde a `coupling.py` para
ese objeto físico. **No describe por sí solo toda la ruta integrada de lumbreras**,
que añade área efectiva, reacción de pared y transporte P6.

Por tanto, DeepSeek acierta sobre el uso de HLLC y Cd en la ruta legacy. La
afirmación necesita dos precisiones: no hay doble Cd demostrado y el candidato
de tobera ya existe como opción. HLLC se conserva para el flujo entre celdas y
la conexión R1 permanece disponible para su contrato original.

### Candidato reutilizado

V1 distingue garganta y conducto, con expansión separada, pero conserva sus
límites de dominio documentados; no se promueve. V2 utiliza una tobera ideal
equivalente: entalpía del donante, continuidad, compatibilidad de ondas, garganta
sónica y ramas transónicas/choques cuando son admisibles. No impone la presión
estática de un segundo depósito sobre un conducto que ya proporciona ondas.

V2 recibe el área efectiva ya calculada, sin otro Cd. Devuelve el flujo sobre la
cara completa del conducto; `_port_face_flux` no añade de nuevo la presión de la
parte bloqueada. El selector es explícito, serializado y ligado a identidad de
configuración/checkpoint. La red externa conserva su modelo y el interior 1D
conserva HLLC. Las conexiones 0D de sección completa bajo V2 siguen la hipótesis
de depósito–tobera, distinta del objeto R1: no se las presenta como R1 corregido.

## 2. Comparación física mínima

Se fijó el [protocolo](../../docs/gasdynamic/port_flow_verification_v1.md) antes
de la matriz y de los diagnósticos integrados, commit `bd635de`. Referencias
analíticas independientes del código V2: continuidad y relaciones isentrópicas
de un gas ideal caloríficamente perfecto, gamma=1.35 y R=287 J/(kg K).

`mdot = Aef * p0/sqrt(R*T0) * sqrt(gamma) * M *
        (1+(gamma-1)*M²/2)^(-(gamma+1)/(2*(gamma-1)))`.

El máximo se alcanza en M=1 de la garganta; la presión crítica relativa es
`(2/(gamma+1))^(gamma/(gamma-1))`. La energía transportada es `mdot*cp*T0`.
Se calculó el Mach del conducto mediante inversión independiente del caudal,
sin reutilizar las rutinas área–Mach del candidato. Referencias primarias:
[NASA: caudal y bloqueo](https://www.grc.nasa.gov/www/k-12/BGP/mflchk.html),
[NASA: choque normal](https://www.grc.nasa.gov/WWW/k-12/airplane/normal.html).

### Referencias compatibles, no dos problemas confundidos

Se comprobaron **100 estados analíticos compatibles**: ambas orientaciones,
flujo directo e inverso, aperturas geométricas .025/.1/.5/1 y Cd .65/1, garganta
subsónica y sónica, más entradas supersónicas compatibles. La temperatura de
remanso donante fue 900 K desde la cámara y 300 K desde el conducto, para
comprobar también el sentido de la entalpía.

| Caso cámara → conducto; p0=200 kPa, T0=900 K | Referencia kg/s | Legacy kg/s | V2 kg/s |
|---|---:|---:|---:|
| Aef=Ap=1e-4 m², Mconducto=.01 | 4.572031e-4 | 2.286006e-4 | 4.572031e-4 |
| Aef/Ap=.1, Mgarganta=.01 | 4.572031e-5 | 2.286015e-6 | 4.572031e-5 |
| Aef=Ap, límite sónico | 2.660771e-2 | 1.634245e-2 | 2.660771e-2 |
| Aef/Ap=.1, salida supersónica compatible | 2.660771e-3 | 3.265488e-3 | 2.660771e-3 |

En el primer caso, el **Riemann exacto** da 2.286039e-4 kg/s, también alrededor
de la mitad. La discrepancia dominante es el objeto físico de frontera, no
el error aproximado HLLC. En el límite débil, acoplar un estado estacionario
como otro semiespacio Euler introduce una segunda impedancia acústica, en vez
de la condición de entalpía total del depósito. Para apertura reducida aparece
además la multiplicación por Aef sobre un estado que pertenece a la sección Ap.

No hay un factor universal de subestimación: el cuarto caso incluso supera el
caudal crítico de **esa referencia cuasiestacionaria**. No se interpreta ese
límite como cota universal de cualquier transitorio no estacionario.

En el límite sónico de sección completa, legacy transporta `E/mdot` igual a
0.805318 de `cp*T0`; V2 conserva la entalpía total del donante. No es un defecto
de conservación global del sistema legacy: es una diferencia del cierre físico.

V2 pasó los cuatro flujos analíticos (masa, momento, energía, marcador), con
**error relativo máximo 6.63673e-13**, frente al criterio previo 1e-9. Los
controles de choques, causalidad, transiciones y ausencia de solución se
reejecutaron mediante las pruebas transónicas existentes, sin modificar límites.

También se registraron 48 estados inicialmente quietos, relaciones de presión
1.001–10, ambas direcciones y dos aperturas. La fórmula de dos depósitos se
incluye como contexto, **no como solución exacta instantánea del conducto**.
La compresión/rarefacción modifica la presión y velocidad de su cara. Diferir
allí no se contabilizó como error del candidato ni de HLLC.

### Cámara finita y transporte

Cuatro ensayos dinámicos: 200/100 y 100/200 kPa, legacy/V2, una conexión activa
con Aef/Ap=.1, ocho celdas, 50 microsegundos a dt=1 microsegundo. Volúmenes fijos,
extremos cerrados, sin combustión ni calor; composición distinta en ambos lados.

- Masa transferida cámara → conducto: legacy 0.078502 mg; V2 0.230362 mg.
- Masa transferida conducto → cámara: legacy 0.079068 mg; V2 0.215577 mg.
- Residuo global normalizado máximo: 7.181e-16.
- Residuo máximo de cambio de inventario contra flujo integrado, incluyendo
  **cada una de las cuatro especies** de la cámara: 7.138e-16.
- Restauración y siguiente paso idénticos en los cuatro casos.

Estos ensayos demuestran intercambio conservativo en ambos sentidos, no que
los dos modelos deban producir el mismo transitorio.

## 3. Impacto integrado: mismo motor y estado inicial

Dos revoluciones independientes de A9000, 44 celdas totales, primer orden,
CFL y física restante idénticos, sin warm start. El analizador verificó igualdad
de configuración salvo el selector/versionado, campos iniciales idénticos,
hashes de configuración, checkpoint terminal y primarias. Sin MUSCL.

| Magnitud | Legacy | V2 experimental |
|---|---:|---:|
| Admisión neta al cárter, mg / dos revoluciones | 48.501 | 238.774 |
| Transfers → cilindro bruto / inverso, mg | 102.359 / 2.313 | 257.669 / 5.902 |
| Cilindro → escape bruto / inverso, mg | 77.274 / 37.804 | 218.677 / 38.001 |
| Salida exterior bruta / inversa, mg | 24.334 / 21.500 | 54.665 / 11.762 |
| Presión máxima cilindro, MPa | 5.98058 | 5.01879 |
| Presión máxima cárter, kPa | 137.795 | 137.810 |
| Presión máxima escape, kPa | 125.854 | 147.928 |
| Aire fresco atrapado al segundo cierre de escape, mg | 31.838 | 73.227 |
| Combustible atrapado en ese cierre, mg | 3.345 | 6.638 |
| Fracción quemada + residual inicial en ese cierre | 0.492683 | 3.871e-19 |
| Trabajo cilindro acumulado, J | 14.6516 | 31.8770 |
| Tiempo de solver, s | 7.340 | 24.380 |
| Pasos aceptados / propuestas rechazadas | 1444 / 0 | 1450 / 19 |

La composición atrapada se compara exactamente a **632.5°** (272.5° del segundo
ciclo), no al final después de otra combustión. «Quemado» y «residual inicial»
son etiquetas distintas del modelo; su suma expresa aquí la fracción usada.
La casi desaparición de esa fracción en V2 es un resultado del transitorio y
del cierre de barrido existente, **no una validación de barrido perfecto**.
No se cambia ese cierre ni se utiliza el incremento de trabajo como aceptación.

La reacción dinámica y las ondas cambian: no hay proporcionalidad sencilla
entre el déficit del ensayo analítico y los caudales integrados del motor.
Las diferencias son suficientemente grandes para que la elección de esta
frontera importe al producto; no prueban cuál reproduce un motor real.

Ambos diagnósticos pasaron conservación: masa <=8.386e-16, especies <=6.082e-16,
energía <=1.443e-15 normalizados, con checkpoint/restauración y siguiente paso
idénticos. Las 19 propuestas rechazadas por V2 quedaron registradas; no se
relajó CFL/admisibilidad. El coste de solver fue **3.32×**, pared completa
11.692 frente a 29.888 s. Una pareja no constituye benchmark estadístico.

## 4. Pruebas, almacenamiento y reproducibilidad

- Suite focal final: **1514 PASS**, 4.92 s. Incluye controles existentes de
  Riemann, restricción, V1/V2, integración, congelamiento/configuración y 13
  tests del diagnóstico. No sumar las repeticiones como casos únicos.
- P4–P8: **301 PASS, 3 SKIP**, 196.91 s; cuatro avisos NumPy preexistentes.
- Fuente física, contrato R1, modelos térmico/barrido/combustión y Desktop:
  sin cambios en esta intervención. rc7 conservada.
- Preflight pasó antes de las escrituras grandes, reserva 2 GiB. Un artefacto
  preliminar del observador incluyó trazas enteras en sus checkpoints (25.1 MB,
  sobre la estimación de 10 MiB). Se preservó en la raíz externa con SHA-256
  verificado. Se aplicó la compactación de trazas ya existente al observador y
  se añadió un límite de tamaño previo a escritura: recibo final 333,918 bytes.
  Los 100 estados analíticos y los cuatro estados físicos, flujos y balances
  dinámicos quedaron idénticos. No fue una corrección del solver.
- Las dos corridas integradas consumieron aproximadamente 42.8 s de los runners,
  sin extensiones. Se conservaron primarias y checkpoints fuera de Git.
- Revisión: **SELF_REVIEW**. No se presenta como nueva revisión independiente,
  aceptación comercial o validación experimental.

Reproducción acotada con nuevos destinos (los scripts rechazan sobrescritura):

```text
python scripts/diagnostics/verify_port_flow_physics_v1.py --output <nuevo-recibo.json>
python scripts/diagnostics/diagnose_integrated_port_v2.py --output <nuevo-dir-legacy> --model legacy --step-degrees 0.5
python scripts/diagnostics/diagnose_integrated_port_v2.py --output <nuevo-dir-candidato> --model nozzle --step-degrees 0.5
python scripts/diagnostics/summarize_port_flow_impact_v1.py --root <raiz-de-ambos-directorios> --output <nuevo-impacto.json>
```

El analizador espera subdirectorios `legacy` y `candidate`. Los ejecutores
integrados tienen parada de 240 s/checkpoints y preflight propio; no habilitar
la opción espacial MUSCL para reproducir esta intervención. No se ejecuta otra
vez automáticamente. Los comandos concretos y resultados están en los summaries
de `runlogs/`. Ver [recibo](receipt.json), [referencias aisladas](isolated-compact.json),
[impacto y hashes](integrated-impact-verified.json) y [flujos CSV](integrated-impact-verified.csv).

## 5. Cierre y consecuencia para el producto

1. **CORREGIR**, mediante el candidato específico ya implementado, el tratamiento
   de una restricción como simple Riemann escalado. El defecto demostrado es su
   incompatibilidad con los límites depósito–tobera analíticos pertinentes.
2. **Conservar HLLC y R1** en sus alcances, así como la baseline rc7. No se ha
   demostrado doble Cd ni un fallo de conservación que exija reconstruir el 1D.
3. **V2 continúa experimental**. Resuelve esos casos de referencia, pero no
   identifica el chorro separado ni las pérdidas reales. Su recuperación de
   presión ideal no equivale a la expansión separada de V1, especialmente con
   abertura reducida; el mismo Cd no está validado entre ambos modelos.
4. No adoptar automáticamente V2 como frontera de producción: falta evidencia
   medida de caudal/presión en una restricción representativa (geometría, área
   instantánea, sentido y remansos conocidos) para identificar ese cierre y sus
   pérdidas. Los datos de potencia por sí solos no los identifican.
5. Se **cierra esta intervención**. No se abren nuevas mallas, continuaciones ni
   campañas. La hoja de ruta comercial conserva sus entregas; esta evidencia
   impide confundir el funcionamiento de rc7 con precisión predictiva y permite
   reutilizar V2, con su coste y límites, cuando corresponda seleccionar el modelo
   de una validación con datos reales.
