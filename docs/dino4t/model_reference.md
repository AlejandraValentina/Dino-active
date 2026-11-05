# Dino 4T — Referencia de modelos (`DINO4T_FOUNDATION_V1`, etapa 2)

> **Etapa 2.** Esta referencia describe el estado tras la auditoría crítica de
> [stage2_assessment.md](stage2_assessment.md). Las secciones 4 y 6 reemplazan
> a las de la etapa 1 (combustión de zona única con productos completos y
> contorno `QUASI_STEADY_RESTRICTION_V1`, ambos aún seleccionables para
> reproducir la etapa 1).

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
| `engine.py` | Cilindro 0D, `Plenum` finito, topología por `Connection`, SSPRK2, ledgers |
| `equilibrium.py`, `twozone.py` | Equilibrio químico (Gibbs) y cierre de dos zonas |
| `api.py` | Superficie estable de integración `DINO4T_API_V1` (ver [integration_contract.md](integration_contract.md)) |
| `studies.py` | Barridos con continuación y sensibilidades locales |
| `verification_stage2.py` | Verificación contra soluciones exactas/analíticas/Cantera |
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

## 4. Combustión

La liberación de calor **no es un término fuente**: surge del cambio de
composición porque las entalpías incluyen la de formación (§2). Hay dos
modelos, elegibles con `combustion.zone_model`.

### 4.1 `two_zone_equilibrium` (`TWO_ZONE_EQUILIBRIUM_V1`, por defecto del ejemplo)

* **Fracción quemada prescrita** (entrada de calibración, no predicción):
  Wiebe x_b = (1 − exp(−a y^{m+1}))/(1 − e^{−a}), y = (θ − SOC)/Δθ, con
  a = 5 y m = 2 (Heywood §9.2.1). SOC y Δθ son parámetros de calibración.
* **Zona no quemada:** composición congelada, compresión adiabática reversible
  (la entropía específica s_u es un estado) salvo su parte de la pérdida de calor.
* **Zona quemada:** equilibrio químico a (T_b, p) entre 10 especies
  (O2, N2, AR, CO2, H2O, CO, H2, H, O, OH), por minimización de Gibbs con
  potenciales de elemento (Gordon & McBride 1994). **NO se excluye** porque su
  formación es cinética (Zeldovich): el equilibrio sobrestimaría la energía que
  almacena. Los elementos de la zona quemada son x_b veces los de la mezcla
  que reacciona. El combustible no quemado (1 − η_c) viaja como especie inerte.
* **Cierre algebraico.** El estado integrado del cilindro es solo
  `[U_total, s_u]`. Para cada (U, s_u, V, x_b) se resuelve:
  s_u(T_u, p) = s_u; U = m_u e_u(T_u) + m_b e_b(T_b, p); V = (m_u R_u T_u + m_b R_b T_b)/p.
  Así el integrador, los ledgers y los eventos son los del modelo de zona única.
* **Calor a la pared:** el coeficiente de Woschni usa la T media (pV/mR̄); cada
  zona cede calor según su fracción de volumen. Solo la zona no quemada
  modifica s_u: ds_u = −q_u dt/(m_u T_u).
* **Fusión:** al abrir la válvula de escape, la zona quemada se proyecta sobre
  las 8 especies estándar (H → ½H2, O → ½O2, OH → ½H2O + ¼O2) a U constante.
  Conserva elementos y energía exactamente; los radicales son despreciables allí.
* **Regularización en x_b < 10⁻⁴.** e_b = (U − U_u)/m_b divide por x_b una
  diferencia del tamaño del error de truncación de U. Allí la zona quemada se
  toma como llama adiabática a presión constante con la entalpía de la zona no
  quemada. El error es O(x_reg) en p (<3·10⁻⁵, medido). Sin esto, el
  cierre falla justo después del SOC con pasos angulares grandes.
* **Salidas nuevas:** `T_burned_max_K`, `T_unburned_max_K` (indicador de
  tendencia a detonación, **sin** modelo de autoignición).
* **Límites:** fracción quemada prescrita; zona quemada homogénea; sin cinética
  (NO, CO congelado); sin modelo de llama ni de detonación; equilibrio hasta
  la apertura del escape.

### 4.2 `single_zone` (etapa 1)

Productos de combustión completa (pobre/estequiométrica: CO2 + H2O; rica:
CO/H2 con K = 3,5, Heywood §4.9.1), sin disociación, a T uniforme. Se conserva
para reproducir la etapa 1. Sobrestima la temperatura de explosión a volumen
constante en 295 K y la presión en 8,2 % a φ = 1 respecto del equilibrio
(§ stage2_assessment).

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

## 6. Válvulas y contorno de restricción (`QUASI_STEADY_RESTRICTION_V2`)

* **Válvulas:** alzada armónica sin² o tabulada (PCHIP, sin sobrepaso).
  A_eff = n · Cd(L/D, sentido) · A_ref, con A_ref = curtain πDL o asiento
  πD²/4. Los Cd directo e inverso (reversión) son independientes. Se exige
  A_eff,max ≤ área del conducto de lumbrera.
* **Contorno.** En la cara extrema del conducto se resuelve la presión de cara
  p_f imponiendo tres relaciones:
  1. La característica que llega desde la celda interior (onda simple
     isentrópica, γ congelado de la celda):
     w_f = w_c + 2a_c/(γ−1)[(p_f/p_c)^{(γ−1)/2γ} − 1].
  2. Orificio compresible cuasi-estacionario (Heywood App. C):
     - volumen → conducto: aguas arriba (p_v, T_v), aguas abajo p_f;
     - **conducto → volumen: aguas arriba el estado de estancamiento de la
       cara** (p_0f, T_0f calculados con w_f), aguas abajo p_v.
  3. Continuidad: A_p ρ_f w_f = ṁ.
* **V1 vs V2.** V1 usaba la presión estática de cara como presión total. Un
  extremo abierto ideal (σ = 1) añadía una cabeza dinámica completa de
  pérdida y pasaba 29,3 % menos caudal a **cualquier** Mach. Con V2 el extremo
  abierto ideal fija p_cara = p_amb y reproduce la tobera isentrópica a ≤ 8·10⁻⁶.
* **Raíces.** El residuo de V2 tiene raíces espurias con cara supersónica. La
  rama admisible empieza en el estado sónico de la cara, que sale en forma
  cerrada de la característica:
  x_s = (2 − (γ−1)w_c/a_c)/(γ+1), p_sónico = p_c x_s^{2γ/(γ−1)}. Si el orificio
  demandara más de lo que el conducto puede entregar, el extremo queda
  bloqueado en ese estado.
* **Entrada supersónica.** La rama volumen → conducto no puede representar una cara con M > 1 con una sola
  característica entrante (haría falta una tobera). Si la raíz lo exige, se lanza `RestrictionError`
  («supersonic inflow face»): el paso se rechaza y, si persiste, la corrida termina como
  `failed_numerical` / `MODEL_OUT_OF_VALIDITY`. No se estrangula la entrada (sin referencia independiente).
  En el ejemplo la cara de entrada no pasa de M = 0,6 (`results/dino4t-stage2-v1/audit/engine_face_mach.json`).
* **Flujos.** Masa, especies, trazador y energía (ṁ·h0 del donante, con
  h0 = h_f + w_f²/2 en la cara) son idénticos para el conducto y el volumen.
  La energía cinética del chorro en el lado volumen se disipa (Borda-Carnot).
* **Casos particulares.** Área cero: pared reflectante (onda simple).
  σ = 1 hacia un reservorio: extremo abierto ideal sin corrección de extremo.
* **Hipótesis y limitaciones:**
  - Sin recuperación de presión en la expansión brusca válvula → conducto
    (se supone p_garganta = p_conducto).
  - Onda simple aproximada para ondas fuertes. El caso de choque + contacto
    (p₀/p₁ ≤ 2,5) se reproduce a 0,1 %.
  - Sin inercia de la columna en la garganta ni corrección de extremo acústica.
  - Los Cd son datos de entrada. Un Cd mal medido, o referido a otra área,
    domina el error del llenado (ver sensibilidades).

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

| Simplificación vigente | Siguiente paso |
|---|---|
| Combustión con fracción quemada prescrita (Wiebe); SOC y duración son entradas | modelo de velocidad de llama (turbulencia, relación de equivalencia, residuo) o calibración desde p(θ) medida |
| Equilibrio químico sin NO ni cinética (CO congelado tras el escape) | cinética de Zeldovich para NO; CO cinético en expansión |
| T_no quemada como indicador; sin modelo de autoignición | integral de retardo de autoignición (Livengood-Wu) calibrada |
| Aire seco; combustible vaporizado y premezclado en el ambiente | humedad; inyección PFI/DI, evaporación, película de pared |
| Topología fija admisión-cilindro-escape, con plenum de admisión opcional | red general: uniones, cambios bruscos de área con pérdidas, acelerador, multicilindro |
| Contorno cuasi-estacionario sin recuperación de presión ni inercia de garganta | validación con banco de flujo; modelo de garganta con inercia |
| Cd(L/D) y pérdidas mecánicas sintéticos | datos medidos (banco de flujo, motorizado) |
| Sin blow-by, swirl/tumble | fugas y turbulencia de carga |
| Paredes a temperatura fija | modelo térmico de pared conjugado |
| Python/NumPy: ~10 s por ciclo con dx = 20 mm y dos zonas | núcleos compilados; paralelismo por punto de RPM |
