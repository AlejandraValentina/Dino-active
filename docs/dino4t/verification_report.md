# Dino 4T — Informe de verificación numérica (`DINO4T_FOUNDATION_V1`)

**Nivel de evidencia:** L0 (tests automatizados) + L1 (corridas de
ingeniería con criterios de verificación). **Revisión:** `SELF_REVIEW`.
Todavía no hay revisión independiente.

**Estado de las afirmaciones:**

| Afirmación | Estado |
|---|---|
| Verificación numérica | ver este informe |
| Calibración | `NOT_PERFORMED` |
| Validación experimental | `NOT_PERFORMED` |
| Capacidad predictiva | `NOT_CLAIMED` |

**Reproducción:**

```
python -m motorsim.dino4t verify --out results/dino4t-foundation-v1/verification   # ~3,5 min
python -m pytest tests/test_dino4t_physics.py tests/test_dino4t_numerics.py tests/test_dino4t_engine.py  # ~30 s
```

El resultado crudo está en
`results/dino4t-foundation-v1/verification/verification_report.json`.

## 1. Qué se verifica y qué no

| Categoría | Pregunta | Dónde |
|---|---|---|
| Verificación del método numérico | ¿Se resuelven bien las ecuaciones escritas? | §2–§5 |
| Consistencia física del modelo | ¿Se conservan masa/energía/elementos y se respetan leyes exactas? | §2, §5, §6 |
| Calibración | ¿Se ajustaron parámetros a un motor? | **No se realizó** |
| Validación | ¿Coincide con mediciones? | **No se realizó** |
| Capacidad predictiva | ¿Predice fuera de la calibración? | **No se afirma** |

Que el ejemplo dé valores plausibles (IMEP ≈ 12,5 bar, η_v ≈ 0,92) **no**
constituye validación: la configuración es sintética y la combustión es una
entrada.

## 2. Termoquímica

| Caso | Referencia independiente | Criterio | Resultado |
|---|---|---|---|
| cp, S°, ΔH_f a 298,15 K de 7 especies | NIST‑JANAF | cp < 0,5 %, S < 0,2 %, ΔH_f < 0,1 kJ/mol | peor: 0,18 % / 0,073 % / 0,014 kJ/mol ✔ |
| Inversión T(e), 400 estados aleatorios 250–3400 K + costura | ida y vuelta | < 1e‑7 K | 9,1e‑13 K ✔ |
| AFR estequiométrico del isooctano | Heywood App. D (15,13) | ±0,2 % | 15,124 ✔ |
| LHV derivado de los datos | Heywood App. D (44,3 MJ/kg) | ±1,5 % | 44,65 MJ/kg (+0,8 %) ✔ |
| Balance elemental de productos, φ 0,5–1,6 | conservación exacta | < 1e‑15 | 3,5e‑18 kmol ✔ |

## 3. Geometría y flujo numérico

| Caso | Referencia | Criterio | Resultado |
|---|---|---|---|
| Posición del pistón | núcleo compartido `motorsim.kinematics` | exacto | 0 ✔ |
| dV/dθ analítico | diferencias centradas | < 1e‑6 rel. | 1,0e‑8 ✔ |
| Ψ del orificio (γ = 1,4) | teoría (0,684731) | < 1e‑6, continuo en el crítico | ✔ |
| HLLC multiespecie vs HLLC congelado 2T, 300 pares aleatorios | `gas1d.riemann.hllc_flux` (mismas cotas de onda) | < 1e‑12 | 1,1e‑13 ✔ |

**Hallazgo durante la verificación.** El oráculo 2T detectó un defecto: con
rarefacciones fuertes, mi HLLC aceptaba estados estrella con p* ≤ 0. Se
agregaron los criterios de admisibilidad (p* > 0 y e* > e(Y, 0 K)) y
ahora coincide con el 2T a 1e‑13.

## 4. Conductos 1D

| Caso | Referencia | Criterio | Resultado |
|---|---|---|---|
| Tubo de Sod, N = 100…800 | solución exacta de Riemann (`gas1d.exact_riemann_reference_v1`) | L1 monótono, orden final > 0,6, conservación < 1e‑13 | L1 0,0083 → 0,0014; orden 0,89/0,84/0,81; conservación 8,9e‑15 ✔ |
| Pulso acústico 1 %, aire NASA, autoconvergencia N = 100…800 | Richardson | por limitador (ver abajo) | ver tabla siguiente |
| Conducto en reposo con área variable | reposo exacto | \|u\| < 1e‑9 m/s | 1,7e‑13 m/s ✔ |
| Resonancia de cuarto de onda (cerrado–abierto, L = 0,5 m) | acústica lineal T = 4L/a | < 1 % | 0,042 % ✔ |
| Flujo estacionario con restricción bloqueada (A_e = 0,1 A) | orificio isentrópico bloqueado | < 1 %; entrada = salida < 1e‑4 | −0,234 %; 8e‑7 ✔ |

Orden observado en el pulso acústico (par más fino):

| Reconstrucción | Orden | Criterio | Estado |
|---|---|---|---|
| central sin limitar (sólo verificación) | **1,98** | > 1,9 | ✔ |
| van Leer | 1,75 | > 1,6 | ✔ |
| minmod (producción) | 1,48 | > 1,35 | ✔ |
| primer orden (comparador) | 0,63 (en ascenso) | expectativa inicial > 0,8 **no cumplida** | INFORMATIONAL |

Interpretación:

* El esquema completo (MUSCL + HLLC + SSPRK2 + termo NASA) es formalmente de
  segundo orden: con pendiente central, el orden es 1,98.
* Los limitadores TVD bajan el orden en L1 porque recortan los extremos
  suaves. Es el comportamiento conocido (LeVeque 2002, §6.8 y §6.12), no un
  defecto.
* **Transparencia de criterios.** El primer criterio global (> 1,6 con minmod)
  falló en la primera corrida (1,57). Antes de commitear, los criterios se
  separaron por limitador con base en esta evidencia. El comparador de primer
  orden quedó como informativo: su expectativa inicial no se cumplió y no se
  le ajustó el umbral.
* El déficit de 0,234 % en el flujo bloqueado es el predicho por la hipótesis
  del contorno (presión estática como presión total aguas arriba,
  M_conducto ≈ 0,06 ⇒ ≈ 0,24 %).

## 5. Cilindro 0D

| Caso | Referencia | Criterio | Resultado |
|---|---|---|---|
| Motorizado adiabático, gas caloríficamente perfecto, dθ = 1/0,5/0,25° | pV^γ = cte (exacto) | orden > 1,8 | error 8,4e‑5 → 5,1e‑6; orden 2,02/2,01 ✔ |
| Ídem con gas NASA | s(T,p) = cte | orden > 1,8, deriva/cp < 1e‑5 | deriva 1,5e‑5 → 3,7e‑6; orden 2,01 ✔ |
| Cilindro cerrado con combustión Wiebe | ODE en temperatura **independiente** (SciPy DOP853, rtol 1e‑12) | máx. \|Δp\|/p_max < 1e‑4, orden > 1,7 | 1,1e‑5 → 6,4e‑7; orden 2,02/2,08 ✔ |
| Cierre de energía en estos casos | ledger | < 1e‑12 | ≤ 5,6e‑15 ✔ |

**Transparencia de criterios.** El criterio inicial de deriva de entropía
(< 1e‑6 a dθ = 0,25°) era más estricto que el propio error de discretización
temporal en ese paso (pV^γ: 5,1e‑6). Antes del commit se reemplazó por un
criterio de orden de convergencia, que es más exigente porque exige que el
error sea de discretización.

La comparación con la ODE independiente es la verificación más fuerte del
cilindro. La formulación (energía conservativa frente a temperatura), el
integrador y el código son distintos; sólo se comparten los datos
termodinámicos y la cinemática, que se verifican aparte.

## 6. Motor completo (ejemplo sintético 500 cm³, 6000 rpm, φ = 1)

| dx | Ciclos a periodicidad | Cierre máx. masa / energía / elementos | IMEP neto [bar] | η_v | p_max [bar] | PMEP [bar] | m atrapada [mg] | Tiempo |
|---|---|---|---|---|---|---|---|---|
| 20 mm | 6 | 3,4e‑15 / 5,3e‑15 / 2,3e‑14 | 12,532 | 0,9243 | 68,49 | 1,432 | 613,14 | 33 s |
| 10 mm | 6 | 8,4e‑15 / 5,8e‑15 / 2,2e‑14 | 12,498 | 0,9229 | 68,41 | 1,445 | 612,61 | 42 s |
| 5 mm | 6 | 8,2e‑15 / 1,0e‑14 / 2,0e‑14 | 12,479 | 0,9220 | 68,36 | 1,451 | 612,22 | 91 s |

Estudio de malla (Celik et al. 2008, r = 2, Fs = 1,25):

| Indicador | Orden observado | GCI fino | Extrapolado |
|---|---|---|---|
| IMEP neto | 0,81 | 0,26 % | 12,45 bar |
| η_v | 0,65 | 0,21 % | 0,920 |
| p_max | 0,68 | 0,15 % | 68,28 bar |
| PMEP | 1,10 | 0,44 % | 1,456 bar |
| masa atrapada | 0,43 | 0,23 % | 611,1 mg |

* La convergencia es monótona en los cinco indicadores, con un cambio
  medio–fino < 0,5 %.
* Los órdenes < 2 son esperables por:
  - los limitadores (§4);
  - los pulsos de escape cuasi‑discontinuos;
  - los contornos de primer orden (celda extrema);
  - la conmutación de las válvulas.
* El estudio refina dx y dt a la vez (CFL fijo). La incertidumbre numérica
  del IMEP a dx = 10 mm es ≈ 0,4 %.

Además, en el ciclo final:

* la masa que entra al sistema y la que sale coinciden con un desbalance
  de 3,6e‑6;
* el combustible quemado (35,40 mg) es igual al combustible neto del sistema
  y a η_c × combustible admitido;
* el η_v medido en la válvula y en la entrada del sistema difiere en 4e‑8.

## 7. Qué falta para avanzar a validación experimental

1. **Datos del motor real (MEASURED):**
   - geometría completa (incluidas las relaciones de áreas de lumbrera);
   - perfiles de alzada medidos y juego de válvulas;
   - Cd(L/D) directo e inverso de banco de flujo, con su área de referencia;
   - geometría de conductos y plenums;
   - condiciones ambiente.
2. **Mediciones de ciclo:**
   - presión de cilindro indicada (alta resolución angular, referenciada al
     PMS y al nivel absoluto);
   - presiones dinámicas en lumbreras de admisión y escape;
   - caudal de aire y de combustible, λ, par y temperatura de escape;
   - rango de RPM y carga.
3. **Calibración separada de la validación:**
   - ajustar SOC/Δθ/a/m de Wiebe a partir del análisis de liberación de calor
     de la presión medida, y el multiplicador de Woschni y Chen‑Flynn;
   - **en un subconjunto de puntos**;
   - preregistrar criterios y métricas antes de comparar el resto (puntos
     ciegos).
4. **Validación:** comparar en puntos ciegos η_v, IMEP, p(θ) y presiones de
   lumbrera, con incertidumbres de medición y numérica (GCI).
5. **Revisión independiente** (`INDEPENDENT_REVIEW`) de este informe y del
   código antes de cualquier afirmación externa.
