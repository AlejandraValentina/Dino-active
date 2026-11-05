# Dino 4T — Evaluación crítica, etapa 2

**Alcance.** Auditoría independiente de la implementación de la etapa 1 (commit `ed71dbe`),
corrección de los defectos hallados e incorporación de los modelos justificados por la evidencia.
**Nivel de evidencia:** L0 + L1. **Revisión:** `SELF_REVIEW` (el mismo agente que escribió la etapa 1
la auditó; no hay revisión independiente de terceros).

| Afirmación | Estado |
|---|---|
| Verificación numérica | 31 casos de aceptación (`verify`) + tests 4T; suite completa del repositorio en §10 |
| Calibración | `NOT_PERFORMED` |
| Validación experimental | `NOT_PERFORMED` |
| Capacidad predictiva | `NOT_CLAIMED` |

Nada de lo siguiente es una predicción. La configuración de ejemplo es sintética.

## 1. Conclusión

La etapa 1 **no estaba lista para estudiar modificaciones de motor**. Sus 35 tests y su suite de
verificación pasaban, y la conservación cerraba a 1e-14, pero el contorno que acopla conductos y
volúmenes tenía un error de primer orden que esos controles no podían ver. Tras corregirlo, el
simulador reproduce soluciones exactas de problemas no lineales con flujo medio, resonancias y
transitorios de choque con errores de 10⁻⁵–10⁻³. Eso es **verificación**, no validación: sigue sin
haber ninguna comparación con un motor real.

## 2. Defectos detectados

| # | Defecto | Efecto | Estado |
|---|---|---|---|
| D1 | `duct→volumen`: la presión estática de cara se usaba como presión total aguas arriba del orificio. Un extremo abierto ideal añadía una cabeza dinámica completa de pérdida. | **−29,3 %** de caudal a cualquier Mach, p_cara = p_amb + ½ρw². En el ejemplo: η_v subestimada 1,7 % (4000 rpm), 4,2 % (6000), 7,5 % (8000); IMEP 2–8 %. | Corregido (V2) |
| D2 | El residuo de V2 tiene raíces espurias con cara supersónica; la búsqueda de raíz asumía unicidad. Provocó un fallo de bracketing en el soplado de escape a 4000 rpm. | Fallo numérico del motor | Corregido: rama admisible desde el estado sónico (forma cerrada) |
| D3 | Combustión sin disociación. | A φ = 1, volumen constante desde 700 K/22 bar: T +295 K y p +8,2 % frente al equilibrio (Cantera). A φ = 0,8: +118 K, +3,8 %. | Corregido (dos zonas con equilibrio) |
| D4 | Mal condicionamiento de e_b = (U − U_u)/m_b para x_b → 0: divide una diferencia del tamaño del error de truncación por x_b. | Temperatura de la zona quemada sin sentido justo tras el SOC; riesgo de fallo con pasos angulares grandes | Regularizado (x_b < 10⁻⁴), error medido < 3·10⁻⁵ |
| D5 | Tres criterios de aceptación de la etapa 1 eran post-hoc o racionalizaban un resultado (§6). | Evidencia más débil de lo declarado | Revisados |
| D6 | Arranque en caliente incompatible cuando cambia el número de celdas (hallado al correr sensibilidades). | Fallo de la herramienta, no del motor | Corregido y registrado en el resumen |
| D7 | **Procedencia falsa en el resultado.** `summary.models` era una constante (`SINGLE_ZONE_0D_V1`, `QUASI_STEADY_RESTRICTION_V1`) aunque la corrida usara V2 y dos zonas, y `code_commit` no decía si el árbol estaba sin commitear. Los resúmenes del ejemplo guardados antes cargaban esa etiqueta incorrecta. | Un consumidor (Desktop) no podía saber qué modelo produjo un número; riesgo de comparar resultados de modelos distintos | Corregido (`resolved_models`, `code_dirty`); ejemplo regenerado desde árbol limpio |
| D8 | Las claves de configuración desconocidas se ignoraban: la errata `restricton_model` ejecutaba V2 en silencio. | Modelo distinto del pedido, sin aviso | Corregido en la interfaz (`unknown_keys`, rechazo `CONFIG_INVALID`) |
| D9 | V2 podía devolver una cara con M > 1 en la rama volumen → conducto (una sola característica no representa entrada supersónica). | Estado no físico sin aviso, fuera del envolvente del ejemplo (M_cara máx. 0,6; ver §5) | Falla explícita (`RestrictionError`), no estimación; límite documentado (§7.9) |

**Por qué D1 pasó inadvertido.** (a) La conservación discreta compara dos usos de los mismos números de
flujo: un flujo equivocado se conserva perfectamente. (b) El único test de extremo abierto era de
pequeña amplitud, donde ½ρw² es despreciable frente a ρaw. (c) El test de tobera bloqueada daba un
déficit de −0,234 % que atribuí a "una hipótesis del contorno" en lugar de investigarlo; con V2
vale 3·10⁻⁶. **Lección operativa:** un residuo pequeño y "explicado" es una señal, no una conclusión.

**Errores míos durante la auditoría (no del motor).** Dos referencias que construí eran incorrectas y
las detecté antes de atribuirlas al simulador: el problema de Riemann de diafragma no es la solución de
un reservorio con entrada cuasi-estacionaria (la entalpía total no se conserva), y mi autovalor de la
ecuación de Webster tenía invertida la orientación del conducto. Una tercera referencia (trayectoria
de dos zonas integrada en Cantera) quedó **sin resolver** y se descartó; ver §7.

## 3. Cambios implementados

* **Contorno `QUASI_STEADY_RESTRICTION_V2`** (`restriction.py`): el orificio conducto→volumen se alimenta
  del estado de estancamiento de la cara; rama de búsqueda desde el estado sónico; conducto bloqueado
  cuando el orificio demanda más de lo que entrega. V1 sigue seleccionable y reproduce la etapa 1
  **bit a bit** (IMEP 12,498382979526601), lo que garantiza que nada más cambió en la refactorización.
* **Combustión de dos zonas con equilibrio químico** (`equilibrium.py`, `twozone.py`): 10 especies,
  sin NO; estado integrado `[U, s_u]` y cierre algebraico; fusión al abrir el escape. Salidas nuevas:
  `T_burned_max_K`, `T_unburned_max_K`.
* **Plenum finito** (`Plenum`, `intake_plenum` en la configuración) y corridas de ciclos fraccionarios.
* **Herramientas de estudio** (`studies.py`, CLI `sweep` y `sensitivity`): barridos con continuación,
  elasticidades por diferencias centradas, separación entre parámetros físicos y numéricos.
* **Verificación de etapa 2** (`verification_stage2.py`, `tests/test_dino4t_stage2.py`).

## 4. Impacto sobre el ejemplo sintético (6000 rpm, φ = 1)

| Versión | IMEP [bar] | η_v | p_max [bar] | T_quemada máx [K] |
|---|---|---|---|---|
| Etapa 1 (V1, zona única) | 12,498 | 0,9229 | 68,41 | 2672 (media) |
| V2, zona única | 12,872 | 0,9615 | 71,45 | 2672 (media) |
| V2, dos zonas (actual, dx = 10 mm) | 12,600 | 0,9620 | 68,75 | 2745 (zona quemada) |

Ejemplo final (V2 + dos zonas, dx = 10 mm, periódico, cierre ≤ 4·10⁻¹⁴):

| rpm | IMEP [bar] | PMEP [bar] | η_v | p_max [bar] | T_quemada máx [K] | T_no quemada máx [K] |
|---|---|---|---|---|---|---|
| 4000 | 14,43 | 0,31 | 1,006 | 69,7 | 2745 | 922 |
| 6000 | 12,60 | 1,67 | 0,962 | 68,8 | 2745 | 972 |
| 8000 | 9,53 | 1,47 | 0,738 | 53,6 | 2720 | 987 |

(BMEP y potencia efectiva dependen de una fricción sintética: no son predicciones.)

La corrección D1 aumentó η_v; la combustión de dos zonas redujo p_max 3,8 % y IMEP 2,1 % a igual
contorno (dx = 20 mm, mismo caso), con T_quemada máx +74 K respecto de la media de zona única y
T_no quemada máx = 1712 K. En un cilindro cerrado adiabático el signo del cambio de p_max es el
opuesto (+1,2 %): la separación en zonas y la disociación actúan en sentidos contrarios. **El efecto
neto en el motor no se descompone en esos dos aportes** (limitación).

## 5. Evidencia de verificación (31 casos, 0 fallos; `results/dino4t-stage2-v1/verification/`)

| Caso | Referencia independiente | Resultado |
|---|---|---|
| Extremo abierto ideal, M = 0,17–0,71 | tobera isentrópica exacta | error de caudal ≤ 8·10⁻⁶ (V1: −29,3 %) |
| Tobera convergente-divergente estacionaria | relación área-Mach exacta | orden 1,86 (van Leer), error L1 6,5·10⁻⁴ |
| Fanno (4fL/D = 0,5) | relaciones de Fanno | error de Mach 4,8·10⁻⁴ |
| Transferencia de calor de pared | relajación exponencial exacta | 2,7·10⁻³ de ΔT |
| Resonador de Helmholtz (plenum + cuello) | ecuación trascendente exacta tan(kL) = A/(Vk) | 63,945 vs 63,957 Hz (0,018 %); la fórmula concentrada daría 2,1 % |
| Descarga / carga de recipiente | ODE aislada (DOP853) | 1,6·10⁻³ / 7,2·10⁻³ de la sobrepresión inicial |
| Entrada no estacionaria fuerte (p₀/p₁ = 1,5–2,5) | choque + contacto (Rankine-Hugoniot) | caudal 6–9·10⁻⁴; meseta 3–4·10⁻⁵ |
| Reflexión de choque en extremo abierto | liberación isentrópica exacta | 1,3·10⁻⁵–7,5·10⁻⁵ |
| Resonancia del corredor tras IVC | ecuación de Webster del corredor real (FD) | 247,65 vs 249,30 Hz (0,66 %) |
| Solver de equilibrio (36 estados) | Cantera `equilibrate('TP')` | Y: 6·10⁻⁷ |
| Cierre de dos zonas (24 casos) y estado final UV | Cantera + brentq | 1,4·10⁻¹¹ |
| Cilindro cerrado de dos zonas, dθ = 1 → 0,25° | Richardson | orden 1,90–2,00; cierre ≤ 3·10⁻¹⁴ |
| Movimiento isentrópico con gas NASA | ODE DOP853 independiente | error 1,8·10⁻⁵ a dθ = 0,5°; orden 2,02 |
| Cilindro con combustión (zona única) | ODE en temperatura | 6,4·10⁻⁷, orden 2,08 |
| Orden de los limitadores (monótono vs pulso) | control experimental | ver §6 |
| Barrido de régimen de la frontera V2 (26 460 evaluaciones; M −0,9…0,9, 3 T, 3 p, 3 relaciones de área, p_v 0,05–8 bar) | propiedades exigibles a cualquier frontera (sin solución de referencia) | 0 fallos de existencia de raíz, \|M_cara\| ≤ 1, monotonía del caudal en p_v y reparto por donante; 1152 estados declarados fuera de validez (§7.9) |
| Malla del motor completo (dx 20/10/5 mm) | GCI (Celik 2008) | IMEP 0,32 %, η_v 0,28 %, p_max 0,29 %, PMEP 0,24 % |

### Independencia de las verificaciones

| Verificación | Qué comparte con el código | Qué demuestra | Qué **no** demuestra |
|---|---|---|---|
| Equilibrio (36 estados) y cierre de dos zonas (24 estados, estado final UV) frente a Cantera | **Datos** NASA-7 | El solver de Gibbs, el álgebra del cierre y la contabilidad de energía | Los datos termodinámicos; el modelo físico de zona quemada en equilibrio |
| Cilindro de zona única frente a ODE DOP853 en temperatura | Datos termodinámicos y cinemática | Formulación conservativa e integrador (independientes) | Que la combustión prescrita represente un motor |
| Movimiento isentrópico frente a ODE DOP853 | Datos termodinámicos | Integrador y orden temporal | — |
| Orden de convergencia de dos zonas (Richardson) | **Las mismas ecuaciones** | Que la discretización converge a su propio límite | Que ese límite sea correcto (**no es independiente**) |
| Cierres de masa, energía y elementos a 10⁻¹⁴ | Los mismos flujos en ambos lados | Integridad de la contabilidad | Que el flujo sea correcto (D1 cerraba a 10⁻¹⁴) |
| Error de la regularización x_b < 10⁻⁴ (< 3·10⁻⁵) | Se mide frente a la solución sin regularizar del propio código | Que la regularización perturba poco la presión | Exactitud física |
| **Trayectoria integrada de dos zonas** (calor por zona, evolución de s_u, quemado prescrito) | — | — | **Sin referencia independiente** (§7.3) |

**Qué NO prueba esta tabla.** El equilibrio y el cierre comparten los polinomios NASA con Cantera:
se verifica el solver, el álgebra y la contabilidad energética, **no** los datos termodinámicos
(que solo se contrastaron con NIST-JANAF a 298 K en la etapa 1). Los coeficientes de descarga, la
fricción, las temperaturas de pared y la ley de combustión son supuestos.

## 6. Revisión de los tres criterios modificados en la etapa 1

1. **Criterios de orden por limitador (1,35 / 1,6 / 1,9).** Eran post-hoc: se eligieron mirando los
   resultados. La causa del orden < 2 sobre un pulso es el recorte de extremos, y se demostró con un
   control: sobre un escalón monótono sin extremos van Leer y MC recuperan **1,98–1,99** (minmod 1,74;
   sin limitador 1,99); sobre el pulso 1,48–1,75. Regla nueva fijada *a priori*: sobre datos
   monótonos, orden ≥ formal − 0,3; con extremos, solo convergencia (orden > 1). **Justificado.**
2. **Deriva de entropía < 1e-5.** El umbral se fijó después de ver 3,65·10⁻⁶. Se elimina como
   criterio. Se reemplaza por el error frente a una ODE reversible-adiabática independiente
   (DOP853, cp(T) NASA): 1,8·10⁻⁵ a dθ = 0,5° (límite de ingeniería fijado a priori: 10⁻³), orden
   2,02/2,01. **Justificado el criterio nuevo; el anterior no lo estaba.**
3. **Déficit de −0,234 % "esperado" en la tobera bloqueada.** Era el síntoma del defecto D1. **El
   criterio anterior era erróneo.** Con V2 el error es 3·10⁻⁶ y el umbral pasó a 10⁻³.

Además, el comparador de primer orden pasó de "informativo" a una regla coherente: sobre datos
monótonos su orden crece con la malla (0,83 → 0,89 en N = 200–1600), consistente con orden asintótico 1.

## 7. Limitaciones que permanecen (en orden de impacto sobre el uso previsto)

1. **No hay validación.** Ninguna comparación con mediciones. Todo parámetro de ingeniería (Cd,
   fricción, paredes, Wiebe) es sintético.
2. **Cd(L/D) y su área de referencia dominan el llenado** (ver sensibilidades, §8). Sin banco de flujo
   del motor real, los resultados de distribución y de geometría de admisión son tendencias del
   modelo, no estimaciones.
3. **La trayectoria integrada de dos zonas no tiene referencia independiente.** El intento con
   Cantera + DOP853 falló por mal condicionamiento de *mi referencia* en x_b ~ 10⁻⁴ (no se pudo
   distinguir un error del motor de uno de la referencia). Evidencia disponible: cierre contra Cantera
   en 24 estados, orden temporal 2,0, ledgers a 10⁻¹⁴, matriz de estrés. Queda como tarea abierta.
4. **Contorno cuasi-estacionario.** Sin inercia de garganta, sin recuperación de presión en la
   expansión válvula→conducto, onda simple para ondas fuertes (comprobada hasta p₀/p₁ = 2,5).
5. **Combustión prescrita.** La fase y duración de Wiebe son entradas; el modelo no predice cambios de
   la combustión con la carga, el residuo ni el avance. T_no quemada es un indicador, sin autoignición.
6. **Sin uniones con pérdidas.** Los cambios bruscos de área se aproximan con conos empinados; los
   colectores y megáfonos con cambios discontinuos no están modelados.
7. **Discretización de longitudes.** Las sensibilidades a longitudes de conducto mezclan el efecto físico con
   el cambio de tamaño de celda (`ceil(L/dx)`); su ruido numérico es del orden del GCI (~0,3 %).
8. **Rendimiento.** ~10 s por ciclo (Python/NumPy, dx = 20 mm, dos zonas): un barrido de 8 RPM cuesta
   unos 10 min.

9. **Frontera V2 sin entrada estrangulada.** Cuando el orificio volumen → conducto exige más caudal que el que el
   conducto puede aceptar con cara sónica, el código **falla de forma explícita** (`supersonic inflow face`,
   código de API `MODEL_OUT_OF_VALIDITY`) en vez de estrangular la entrada. En el barrido de régimen ocurre en
   1152 de 26 460 estados, principalmente con apertura plena (σ = 1) y relación de presiones volumen/conducto
   ≳ 2, o con el conducto ya entrando a M ≳ 0,5. En el ejemplo la entrada a conducto no pasa de M = 0,6 (4000, 6000 y
   8000 rpm; `results/dino4t-stage2-v1/audit/engine_face_mach.json`), pero **un diseño con escape de apertura casi
   total y soplado fuerte puede alcanzar la región**. Implementarlo exigiría una solución de referencia
   independiente (choque + contacto con entrada estrangulada); no se hizo para no introducir física sin verificación.
10. **Detección de claves desconocidas** compara con el ejemplo y con los literales que lee `config.py`: una clave
    válida colocada en la sección equivocada no se detecta.

## 8. Estudios de ingeniería (consistencia de tendencias, no validación)

Hipótesis fijadas antes de correr (`scripts/dino4t/run_stage2_studies.py`).

**S3 — fase de la admisión (hipótesis H3: el óptimo se retrasa al subir las RPM). Confirmada
cualitativamente.** η_v frente a IVC [°]:

| rpm | −150 | −140 | −130 | −120 | −110 |
|---|---|---|---|---|---|
| 4000 | **1,024** | 1,021 | 1,006 | 0,979 | 0,943 |
| 8000 | 0,626 | 0,686 | 0,737 | 0,780 | **0,811** |

A 8000 rpm el óptimo está fuera del rango probado (monótono creciente).

**S2/S2b — longitud del corredor × RPM (hipótesis H2: el RPM del pico de η_v escala como 1/L).
No respaldada en magnitud; el orden sí.** La primera corrida (S2) usó una malla de 1000 rpm: el «pico» era una parábola de tres
puntos sobre esa malla y los desplazamientos citados (+3 % y −7 %) eran menores que la resolución, de modo que **S2 no
permitía contrastar H2 en magnitud**. S2b repite el estudio con malla de 500 rpm (3000–9000), con un control de
ruido numérico (L × 1,0 con dx = 10 mm; diferencia máx. de η_v 0,0048, media 0,0017). Se declaró antes de correr
(H2b): el pico está ordenado L × 0,7 > L × 1,0 > L × 1,4 y la magnitud no se afirma.

| L × | pico de η_v (parábola, rpm) | máx. η_v | desplazamiento frente a L × 1,0 | predicción ∝ 1/L |
|---|---|---|---|---|
| 0,7 | 4964 | 1,012 | +4,5 % | +43 % |
| 1,0 | 4750 (dx 10 mm: 4732) | 1,074 | — | — |
| 1,4 | 4324 | 1,129 | −9,0 % | −29 % |

* **H2b se cumple** (el orden es monótono y mayor que el ruido: ±18 rpm entre dx = 20 y 10 mm), **H2 no**: el exponente
  local de L es ≈ −0,12 (0,7→1,0) y −0,28 (1,0→1,4), no −1 (la sintonía de Helmholtz con volumen del cilindro daría
  ≈ −0,5).
* El pico de L × 1,0 es una meseta (η_v 1,0736 a 4500 y 1,0737 a 5000 rpm): su posición tiene incertidumbre de ±250 rpm
  **que supera** la diferencia 0,7→1,0 (214 rpm). Solo el desplazamiento 1,0→1,4 (426 rpm) queda por encima de la
  incertidumbre de la malla.
* L × 1,4 muestra un segundo máximo local a 8000 rpm (0,683); no es un lóbulo resuelto y no se interpreta.
* Mi hipótesis era ingenua: el máximo de la *suma* de una envolvente decreciente (estrangulamiento por válvula) y un
  lóbulo de sintonía se desplaza mucho menos que el lóbulo. Esa explicación es **consistente con los datos pero no
  demostrada**; descartar un defecto del modelo exigiría la fase de la presión de lumbrera en IVC frente a RPM, que no se
  midió. El tiempo de tránsito de las ondas sí está verificado de forma independiente (corredor de Webster, 0,66 %).
* No se modificó ningún criterio ni la hipótesis para forzar acuerdo.

**S4 — sensibilidades locales (elasticidades ±5 %, 6000 rpm, dx = 20 mm, 13 parámetros, 27 corridas (base + 2 por parámetro, todas completadas; solo el caso base registra la periodicidad);
`results/dino4t-stage2-v1/studies/S4/sensitivity.json`).** Elasticidad = (d y / y) / (d x / x). No es calibración ni validación:
muestra qué parámetros dominan *en este modelo y este punto*.

| Parámetro (±5 %) | IMEP | η_v | p_max | PMEP | residuo | P_ef |
|---|---|---|---|---|---|---|
| Cd admisión (directo) | +0,47 | +0,43 | +0,43 | +0,18 | -0,24 | +0,57 |
| Cd admisión (inverso) | -0,00 | -0,00 | +0,00 | +0,01 | -0,00 | -0,00 |
| Cd escape (directo) | +0,30 | +0,21 | +0,15 | -0,54 | -1,24 | +0,37 |
| alzada máx. admisión | +0,22 | +0,20 | +0,20 | +0,11 | -0,11 | +0,26 |
| alzada máx. escape | +0,24 | +0,18 | +0,13 | -0,25 | -1,08 | +0,29 |
| longitud del corredor de admisión | +0,02 | +0,10 | +0,13 | +0,56 | -0,09 | +0,02 |
| longitud del tubo de escape | -0,27 | -0,20 | -0,14 | +0,40 | +1,19 | -0,34 |
| temperatura de admisión | -0,70 | +0,35 | -0,55 | -0,73 | +0,24 | -0,85 |
| multiplicador Woschni | -0,06 | -0,01 | -0,01 | -0,06 | +0,25 | -0,08 |
| duración de combustión (Wiebe) | -0,13 | +0,01 | -0,96 | +0,05 | -0,17 | -0,13 |
| fricción A (Chen-Flynn) | +0,00 | +0,00 | +0,00 | +0,00 | +0,00 | -0,03 |
| desfase de la admisión, ±5° [por grado] | +0,048 | +0,003 | +0,248 | +0,004 | -0,000 | +0,117 |
| desfase del escape, ±5° [por grado] | +0,116 | +0,009 | +0,460 | +0,016 | -0,003 | +0,284 |

Lectura (con las salvedades del modelo, no del motor real):

* **η_v:** domina el Cd directo de admisión (0,43), seguido de la temperatura de admisión (+0,35), el Cd de escape (0,21)
  y la alzada de admisión (0,20). **IMEP:** temperatura de admisión (−0,70), Cd de admisión (0,47), Cd de escape (0,30).
* **Gas residual:** lo fija el lado del escape: Cd de escape (−1,24), alzada de escape (−1,08), longitud del tubo de escape
  (+1,19). Una variación del 5 % de la longitud del escape cambia el residuo en ≈ 6 %.
* **Cd inverso de admisión y fricción A:** sensibilidad nula en los indicadores de ciclo (la fricción solo afecta al
  freno, como debe); el reflujo por admisión es pequeño en este punto.
* **Temperatura de admisión y η_v (+0,35).** Con η_v referida a la densidad de entrada, un valor positivo no es
  obvio. Es **consistente con** un desplazamiento de la sintonía (a ∝ √T: +0,5 de elasticidad de frecuencia, con pendiente
  local d ln η_v / d ln rpm ≈ −1 en 6000 rpm, S2b) y con menor calentamiento por pared; no se aisló cada efecto.
* **Resolución:** el ruido de periodicidad (IMEP 0,2 %) y de malla (≈ 0,3–0,5 % en η_v al variar la longitud, por
  ceil(L/dx)) implica que **|e| < ≈ 0,05 no es distinguible de cero** en longitudes y |e| < ≈ 0,02 en el resto. Por eso
  la longitud del corredor de admisión (η_v: 0,10; IMEP: 0,02) está en el límite de resolución.
* **Alcance:** diferencias centradas locales en un punto; no describen el comportamiento fuera de ±5 % ni interacciones.
  Los desfases de distribución mueven apertura y cierre a la vez (±5°): no separan el efecto del cierre del de la
  duración. Las claves `*_timing_shift_deg_per_pct` están mal nombradas (la unidad es «por grado»; se conserva por
  compatibilidad con los resultados guardados).

## 9. Condiciones para avanzar a validación experimental

1. Geometría completa del motor, perfiles de alzada medidos y **Cd(L/D) directo e inverso de banco de
   flujo con su área de referencia**.
2. Presión de cilindro de alta resolución angular (con referencia absoluta y de PMS), presiones
   dinámicas de lumbreras de admisión y escape, flujo de aire y combustible, λ, par.
3. Calibración (Wiebe, multiplicador de Woschni, fricción) con un subconjunto de puntos; puntos ciegos
   y métricas preregistrados antes de comparar.
4. Incertidumbre numérica (GCI, ya disponible) más incertidumbre de medición en cada comparación.
5. `INDEPENDENT_REVIEW` de este informe y del código antes de cualquier afirmación externa.

## 10. Suite completa del repositorio y reproducción

**Tests 4T (77, todos pasan):** física 18, numérica 8, motor 9, etapa 2 y regresiones 28, interfaz de integración 14.

**Suite completa (3518 tests recolectados).** El entorno no tiene `pytest-xdist` y la suite en serie supera las horas; se
repartió por archivo en procesos paralelos (cada archivo con límite de 900 s). Resultado: **115 fallos/errores, el
mismo conjunto exacto que en el commit `e95db4c`** (la base de la rama, antes de cualquier código 4T), ejecutado en un
worktree limpio equivalente: **0 introducidos por el 4T**. Evidencia: `git diff e95db4c HEAD` fuera de `motorsim/dino4t`,
`tests/test_dino4t*`, `docs/dino4t`, `configs/dino4t`, `scripts/dino4t` y `results/dino4t*` solo agrega
`motorsim/engine_platform.py` (archivo nuevo). Lista en `results/dino4t-stage2-v1/audit/preexisting_failures_at_e95db4c.txt`.

Causas de los fallos preexistentes (clasificadas por mensaje): artefactos externos no disponibles en un worktree limpio
(`ArtifactStoreError: REQUIRED_EXTERNAL_ARTIFACT_NOT_AVAILABLE`, rutas de resultados ausentes) y enlaces congelados de
hash/preregistro del 2T (`solver source hash differs from preregistration`, `source/config mismatch`). Un worktree
limpio no reproduce los artefactos ignorados por git del árbol principal, por lo que parte de esos fallos puede no
existir en el árbol principal: **no se investigó ni se tocó** (código y evidencia 2T protegidos). Además, `tests/test_external_data.py` termina con una violación de acceso (segfault, exit 139) de
la GUI/Qt, **idéntica en `e95db4c` y en la rama**, por lo que no es atribuible al 4T; sus tests no se pueden contar.

```
python -m pytest tests/test_dino4t_physics.py tests/test_dino4t_numerics.py tests/test_dino4t_engine.py tests/test_dino4t_stage2.py tests/test_dino4t_api.py
python -m motorsim.dino4t verify --out OUT                 # ~11 min
python -m motorsim.dino4t sweep configs/dino4t/example_single_cylinder_500cc.json --out OUT --param operating_point.rpm=3000:9000:7 --dx-mm 20
python -m motorsim.dino4t sensitivity configs/dino4t/example_single_cylinder_500cc.json --out OUT --dx-mm 20
PYTHONPATH=. python scripts/dino4t/audit_restriction_regimes.py OUT.json        # ~6 s
PYTHONPATH=. python scripts/dino4t/run_stage2_h2_refined.py OUT 1.0 20           # S2b, un L por proceso
```

Referencias de Cantera 3.2.0: `scripts/dino4t/oracle_equilibrium.py` (entorno aislado, no es dependencia del
proyecto); valores en `results/dino4t-stage2-v1/oracle/equilibrium_reference.json`. Procedencia de cada carpeta de
resultados: `results/dino4t-stage2-v1/PROVENANCE.md`.

## 11. Preparación para integrarse en la plataforma común

* **Qué se hizo:** `motorsim/dino4t/api.py` (`DINO4T_API_V1`): `capabilities`, `validate`, `run` con envoltorio
  `{ok, error, summary, artifacts, state}`, errores como datos, progreso en dicts, rechazo de claves desconocidas y
  comprobación de reclamos. Contrato completo, reglas de versionado y brechas de `engine_platform.py`:
  [integration_contract.md](integration_contract.md).
* **Qué NO se hizo (decisión):** no se modificó `engine_platform.py` (arquitectura común ajena al 4T), no se
  registró el 2T, no hay GUI ni barridos en la API, no hay cancelación cooperativa. Las seis recomendaciones sobre la
  plataforma están en el contrato (§11).
* **Aptitud actual:** el 4T puede ser consumido por Desktop **a través de `api`** sin tocar internos. Para registrarlo en
  `engine_platform` sin pérdida de información hace falta el cambio de canal de errores (recomendación 1).

## 12. Estado científico consolidado y riesgos pendientes

| Dimensión | Estado |
|---|---|
| Ecuaciones y acoplamientos | Verificados contra soluciones exactas o independientes en los regímenes de §5; la trayectoria integrada de dos zonas no tiene referencia independiente |
| Conservación | Cierra a 10⁻¹⁴ (integridad de la contabilidad, no exactitud) |
| Solidez | Matriz de estrés de 11 casos periódicos, sin rechazos de paso; la frontera falla de forma explícita fuera de validez |
| Distribución, geometría, resonancia, RPM | Herramientas de barrido y sensibilidad listas; tendencias consistentes con la teoría de ondas en orden, **no en magnitud** (H2) |
| Calibración / validación / predicción | `NOT_PERFORMED` / `NOT_PERFORMED` / `NOT_CLAIMED` |
| Revisión | `SELF_REVIEW` |

Riesgos pendientes, por impacto: (1) ausencia total de datos medidos; (2) Cd(L/D) y su área de referencia dominan el
llenado (S4); (3) trayectoria de dos zonas sin referencia independiente; (4) entrada estrangulada no modelada
(§7.9); (5) H2 sin explicación demostrada; (6) combustión prescrita, sin NO, cinética ni autoignición; (7) sin uniones con
pérdidas; (8) rendimiento de Python (≈ 10 s por ciclo).
