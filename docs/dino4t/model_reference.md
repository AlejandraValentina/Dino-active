# Dino 4T — Referencia de modelos (`DINO4T_FOUNDATION_V1`)

Simulador 0D/1D de un motor monocilíndrico de cuatro tiempos, encendido por
chispa. Este documento describe **qué** se resuelve, con **qué hipótesis** y
**de dónde** salen los parámetros. La evidencia de verificación está en
[verification_report.md](verification_report.md). Nada de lo aquí descrito
está calibrado ni validado contra mediciones.

## 1. Alcance y arquitectura

```
reservorio admisión ─(extremo abierto)─ conducto 1D admisión ─(válvulas adm.)─┐
                                                                              cilindro 0D (pistón, Woschni, Wiebe)
reservorio escape ───(extremo abierto)─ conducto 1D escape ───(válvulas esc.)─┘
```

| Módulo (`motorsim/dino4t/`) | Contenido |
|---|---|
| `thermo_data.py`, `thermo.py` | Mezcla de 8 especies, gas térmicamente perfecto NASA‑7 |
| `combustion.py` | Estequiometría, productos pobres/ricos, ley de Wiebe |
| `kinematics.py` | Biela‑manivela, ciclo de 720° |
| `valves.py` | Leyes de alzada, Cd(L/D), áreas efectivas |
| `closures.py` | Woschni 1967, Chen‑Flynn, fricción y calor en conductos |
| `duct.py` | Volúmenes finitos cuasi‑1D multiespecie (HLLC + MUSCL) |
| `restriction.py` | Contorno conducto ↔ volumen 0D (válvula / extremo abierto / cerrado) |
| `engine.py` | Cilindro 0D, topología por `Connection`, SSPRK2, ledgers |
| `cycle_analysis.py` | Indicadores por ciclo, periodicidad |
| `config.py`, `runner.py`, `__main__.py` | Configuración JSON, ejecución, artefactos, CLI |
| `verification.py` | Suite de verificación numérica |
| `motorsim/engine_platform.py` | Contrato común de familias de motor (2T/4T) |

**Separación respecto de Dino 2T.** Ningún archivo 2T fue modificado. Se
reutilizan sólo núcleos independientes del ciclo:
`motorsim.gas1d.mesh.segments_mesh` (volúmenes de troncos de cono exactos) y
`motorsim.kinematics.piston_position`. Los núcleos congelados
`gas1d.riemann.hllc_flux` y `gas1d.exact_riemann_reference_v1` se usan como
**oráculos** de verificación. No se reutilizó, y la razón es física:

* la EOS 2T (γ = 1,35 constante, un escalar pasivo "fresco"), porque es
  inconsistente con la combustión por especies y con γ(T, Y) variable;
* la energía por fuente LHV × Wiebe 2T. Aquí la liberación de calor surge de
  las entalpías de formación (ver §2);
* `integrated_2t` (cárter, lumbreras, láminas), `periodicity` (360°),
  `thermal` y `mechanical`, cuyas superficies y supuestos son específicos del 2T;
* la ley de lumbrera 2T, que es un objeto de investigación abierto en
  `DINO_PREDICTIVE_RELIABILITY_V1`. El 4T usa una ley propia, documentada en §6.

Un test (`test_dino4t_does_not_import_two_stroke_solver`) garantiza que el 4T
no importa módulos del solver 2T.

**Convención angular.** θ = 0° en el PMS de encendido; PMS de cruce en ±360°.
Un ciclo va de −360° a +360°: admisión [−360, −180], compresión [−180, 0],
expansión [0, 180], escape [180, 360].

## 2. Termodinámica

* **Especies:** IC8H18 (isooctano, combustible sustituto), O2, N2, AR, CO2,
  H2O, CO, H2. Además se transporta un trazador pasivo X_b de "gas quemado",
  que permite medir el residuo y el cortocircuito.
* **Datos:** polinomios NASA‑7 copiados verbatim de GRI‑Mech 3.0
  (`thermo30.dat`) y de Burcat–Ruscic (`BURCAT.THR`, isooctano P 4/85). Los
  SHA‑256 de los archivos fuente están en `thermo_data.py`.
* **Gas:** mezcla ideal térmicamente perfecta:
  cp(T,Y) = Σ Y_i cp_i(T), h = Σ Y_i h_i(T), R = R_u Σ Y_i/W_i,
  e = h − RT, γ congelado = cp/(cp−R) y a = √(γRT).
* **Convención energética:** h_i incluye la entalpía de formación a
  298,15 K. Por lo tanto la energía total se conserva a través de la
  combustión **sin término fuente**: el calor liberado es el cambio de
  composición a energía interna fija. El LHV no es un parámetro; se deriva de
  los datos (44,65 MJ/kg para el isooctano, frente a 44,3 en Heywood App. D,
  diferencia atribuible a la entalpía de formación ATcT).
* **Inversión T(e):** Newton con los coeficientes de mezcla precalculados y
  bisección acotada de respaldo en la costura de 1000 K. Rango admisible:
  [100, 6000] K, fuera de él se rechaza el estado sin recortarlo. Rango de
  ajuste de los datos: [300, 3500] K. Si se excede se marca
  `thermo_fit_range_exceeded`.
* **Aire:** aire seco (N2/O2/Ar), con el CO2 y las trazas plegados en el N2.
  No se modela la humedad.

## 3. Cinemática y cilindro 0D (`SINGLE_ZONE_0D_V1`)

V(θ) = V_c + A_p x(θ), con x(θ) dado por el núcleo compartido y dx/dθ analítico.
El estado del cilindro es conservativo: masas m_i, masa de trazador m_b y
energía interna total U.

dm_i/dt = Σ_válvulas ṁ_i + ω_i,   dU/dt = Σ_válvulas Ḣ − p dV/dt − Q̇_pared

donde ṁ_i y Ḣ son los mismos números (con signo opuesto) que el flujo en la
cara del conducto (§6). Hipótesis: zona única homogénea, gas en reposo (sin
energía cinética macroscópica), sin blow‑by, sin swirl/tumble.

## 4. Combustión (`WIEBE_SINGLE_ZONE_V1`, STANDARD_V1)

* **Fracción quemada:** x_b = (1 − exp(−a y^{m+1}))/(1 − e^{−a}), con
  y = (θ − SOC)/Δθ y normalizada para que x_b(Δθ) = 1. Por defecto a = 5,
  m = 2 (Heywood §9.2.1). **SOC y Δθ son entradas de calibración: el modelo no
  predice la combustión.**
* **En SOC** se congela la reacción global del ciclo: combustible quemado
  F = η_c · m_fuel(SOC) con el O2 disponible. Si la mezcla es pobre o
  estequiométrica: CO2 + H2O. Si es rica: CO2, CO, H2O, H2 con equilibrio
  agua‑gas K = 3,5 (Heywood §4.9.1), sin disociación.
* **Integración:** la fuente de especies se aplica como fuente constante en
  cada paso, igual al incremento **exacto** de x_b. Así la masa quemada total
  es exacta, independientemente de dt.
* **Trazador:** la masa no quemada en SOC pasa a X_b = 1 en proporción a x_b.
* Se exige que ambas válvulas estén cerradas durante la combustión.
* **Limitaciones:** no predice velocidad de llama, golpeteo ni emisiones (NO
  requiere dos zonas).

## 5. Transferencia térmica y pérdidas

* **Cilindro, Woschni 1967** (Heywood ec. 12.19–12.20):
  h = C0 B^−0,2 p^0,8 T^−0,55 w^0,8, con p en kPa.
  w = C1 S̄p + C2 (V_d T_r/(p_r V_r))(p − p_mot).
  - C1 = 6,18 con válvulas abiertas y 2,28 en el resto del ciclo.
  - C2 = 3,24·10⁻³ entre SOC y EVO.
  - Estado de referencia en IVC y p_mot politrópico con γ(IVC).
  - Áreas: culata (factor configurable), pistón y camisa expuesta.
  - Las temperaturas de pared son supuestos de la configuración.
* **Conductos:** fricción de Fanning (16/Re laminar, Blasius turbulento,
  Sutherland para μ) y calor por analogía de Colburn. La fricción sólo actúa
  sobre el momento, porque la pared no realiza trabajo.
* **Mecánicas, Chen‑Flynn:** FMEP = A + B·p_max + C·S̄p + D·S̄p². El bombeo no
  está incluido (está en el IMEP neto).

## 6. Válvulas y contorno de restricción (`QUASI_STEADY_RESTRICTION_V1`)

* **Válvulas:** alzada armónica sin² o tabulada (PCHIP, sin sobrepaso).
  A_eff = n · Cd(L/D, sentido) · A_ref, con A_ref = curtain πDL o asiento
  πD²/4. Los Cd directo e inverso (reversión) son independientes. Se exige
  A_eff,max ≤ área del conducto de lumbrera.
* **Contorno.** En la cara extrema del conducto se resuelve la presión de cara
  p_f imponiendo tres relaciones:
  1. La característica que llega desde la celda interior (onda simple
     isentrópica, γ congelado de la celda):
     w_f = w_c + 2a_c/(γ−1)[(p_f/p_c)^{(γ−1)/2γ} − 1].
  2. Orificio compresible cuasi‑estacionario (Heywood App. C):
     - volumen → conducto: aguas arriba (p_v, T_v), aguas abajo p_f;
     - conducto → volumen: aguas arriba (p_f, T0_c), aguas abajo p_v.
  3. Continuidad: A_p ρ_f w_f = ṁ.
* **Unicidad.** El residuo es continuo y estrictamente monótono en p_f, así
  que la raíz es única y se resuelve por Brent en ln p_f.
* **Flujos.** Masa, especies, trazador y energía (ṁ·h0 del donante, entalpía
  exacta) son idénticos para el conducto y para el volumen. Esa igualdad es la
  conservación exacta. La disipación de energía cinética entre garganta y
  conducto (Borda‑Carnot) queda como energía interna.
* **Casos particulares.** Con área cero, el contorno es una pared reflectante
  (onda simple). Con Cd·A = A_p hacia un reservorio, es un extremo abierto.
* **Hipótesis y limitaciones:**
  - El lado conducto → volumen no recupera la presión dinámica del conducto.
    Esto produce un déficit de ~(γ/2)M² respecto del orificio isentrópico; se
    midió 0,24 % con M ≈ 0,06.
  - Las relaciones de onda simple son aproximadas para ondas fuertes.
  - Sin inercia de la columna en la garganta.
  - Sin corrección de extremo acústica.

## 7. Conductos 1D (`QUASI_1D_HLLC_MUSCL_MULTISPECIES_V1`)

* **Variables por celda:** [ρ_1..ρ_ns, ρX_b, ρu, ρE], con ρ = Σρ_i, de modo
  que la masa se conserva si se conservan las especies.
* **Flujo:** HLLC (Toro et al. 1994) con cotas de onda tipo Einfeldt,
  independientes de la EOS (Toro 2009, ec. 10.52). Se recurre a HLLE si el
  estado estrella es degenerado o inadmisible (p* ≤ 0 o e* por debajo de
  e(Y, 0 K)). Las especies y el trazador se transportan con el flujo másico
  del donante de la discontinuidad de contacto.
* **Reconstrucción:** MUSCL en (ρ, u, p), con limitador minmod por defecto
  (también van Leer, MC; `unlimited_central` sólo para verificación). Las
  especies se reconstruyen en primer orden, lo que mantiene Y ∈ [0,1] y ΣY = 1
  en las caras.
* **Fuente de área:** p_i (A_{i+½} − A_{i−½}), bien balanceada (verificado).
* **Geometría:** volúmenes exactos de tronco de cono (núcleo gas1d).

## 8. Integración temporal y conservación

* **Integrador:** SSPRK2 (Heun) sobre el estado conjunto (celdas + cilindro),
  con un paso global:
  dt ≤ CFL · min(dx/(|u|+a), 2V/(A_L s_L + A_R s_R)), dθ ≤ dθ_max y
  dt ≤ 0,2 m_cil/Σ|ṁ|.
* **Rechazos:** un estado inadmisible reduce el paso a la mitad, como máximo
  16 veces. No se recorta ni se corrige ningún estado.
* **Eventos angulares:** los pasos aterrizan exactamente en PMS/PMI,
  apertura/cierre de válvulas, SOC/EOC y los límites de ciclo.
* **Ledgers:** todos los intercambios (reservorios, trabajo de pistón,
  calores) se acumulan con los mismos pesos RK que el estado. El cierre
  relativo de masa, energía y elementos es de ~10⁻¹⁴ a 10⁻¹⁵ por diseño. Un
  cierre mayor indica un error de implementación, no de discretización.

## 9. Indicadores (Heywood cap. 2)

* **Trabajo y presiones medias:** W_net = ∮p dV; IMEP neto/bruto, PMEP, FMEP y
  BMEP; potencias y pares indicados/efectivos; η_mec = W_b/W_bruto.
* **Llenado:** η_v = aire neto por la válvula de admisión / (ρ_aire,entrada V_d).
  También se reporta sobre la entrada del sistema.
* **Carga:** masa atrapada en IVC, fracción residual (X_b en IVC), eficiencia
  de atrapamiento, fracción fresca cortocircuitada y reflujos.
* **Consumo y eficiencia:** combustible por ciclo, η_f,i, η_f,b, ISFC y BSFC.
* **Combustión y temperaturas:** CA10/50/90 (de la traza integrada),
  p_max/θ_pmax, T_max, temperatura entálpica media de escape.
* **Balances:** pérdida térmica y balances de masa por ciclo.

**Periodicidad.** Entre ciclos consecutivos se exige:

* |ΔIMEP|/IMEP ≤ 0,2 %;
* |Δm_atrapada|/m ≤ 0,2 %;
* max|Δp(θ)|/p_max ≤ 0,5 %;
* desbalance de masa del sistema en el ciclo ≤ 0,5 %;

durante 2 ciclos seguidos. La periodicidad es una propiedad numérica, **no**
evidencia de validez.

## 10. Configuración y procedencia

Esquema `DINO4T_ENGINE_CONFIG_V1`. Cada grupo lleva `provenance` ∈
{MEASURED, DOCUMENTED, STANDARD_V1, SYNTHETIC_ASSUMPTION, CALIBRATED}. Una
configuración sin etiqueta es rechazada. El ejemplo
`configs/dino4t/example_single_cylinder_500cc.json` es **sintético**: un
motor genérico de ~500 cm³ con 4 válvulas, sin correspondencia con ningún
motor comercial.

## 11. Simplificaciones vigentes y capacidades pendientes

| Simplificación V1 | Siguiente paso |
|---|---|
| Combustión Wiebe prescrita, zona única | dos zonas (NO, golpeteo), combustión turbulenta (velocidad de llama) |
| Sin disociación | equilibrio químico de productos (CO, H, OH, NO) |
| Mezcla premezclada vaporizada en el ambiente | inyector (PFI/DI), evaporación, película de pared |
| Aire seco | humedad |
| Una sola topología (adm‑cil‑esc) | red general: plenums finitos, uniones, acelerador, multicilindro (la `Connection` ya lo admite para volúmenes 0D) |
| Contorno cuasi‑estacionario (onda simple) | contorno de Riemann no homentrópico con recuperación de presión dinámica; comparación con datos de banco de flujo |
| Sin blow‑by, sin swirl/tumble | modelos de fugas y turbulencia de carga |
| Temperaturas de pared fijas | modelo térmico de pared conjugado |
| Python/NumPy (~7 s/ciclo con dx = 10 mm) | núcleos Numba/compilados; barrido de RPM paralelo |
