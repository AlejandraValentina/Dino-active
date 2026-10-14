# DINO_COMMERCIAL_UX_BENCHMARK_PROPOSAL

Benchmark de UX de Dino 2T frente a simuladores comerciales de motores 2T.

**Para:** el dueño de Dino y Codex (implementador).

**Fecha:** 2026-10-14.

**Modo:** READ-ONLY.
- No se modificó código, física, malla, OpenSpec, `program-status.json` ni evidencia.
- No se ejecutaron simulaciones nuevas.
- Sí se re-importaron (re-auditoría de lectura, 34 s) 2 corridas EXPLORATORY ya existentes para observar Comparación.

---

## 0. Qué se inspeccionó y con qué evidencia

### 0.1 Dino 2T

**Commit inspeccionado:** `3f5ce5b173f8620d96593f921fe6e19f10eb584c`. Coincide con el HEAD de referencia.

**Observación del código fuente:**
- Recorrido del flujo completo por script con la plataforma Qt nativa de Windows.
- Ventana real a 1440×837 (limitada por la pantalla) y a 980×680.
- Proyecto `examples/projects/dino-2t-exhaust-comparison.dino2t.json`.
- Configuración `QSettings` redirigida a un `.ini` temporal para no tocar el registro del usuario.
- Raíz de artifacts: `E:\Dino-artifacts\dino-design-validation-v1`, donde están las 5 corridas reales.

**Ejecutable empaquetado:**
- Se lanzó `dist/MotorSim-0.1.0-rc6-windows-x64-6649d79a-trial-20261014T153220Z/MotorSim/Dino2T.exe`.
- Se capturó su ventana (HWND) y luego se cerró de forma forzada.
- Al arrancar escribe `active_variant/<proyecto>` en el registro del usuario, como en cualquier uso normal.

**Capturas en `%TEMP%\dino_bench\`:**

| Archivo | Contenido |
|---|---|
| `00_nuevo_proyecto_motor.png` | Primera pantalla desde el código fuente, proyecto nuevo |
| `40_packaged_exe.png` | Primera pantalla del `.exe` empaquetado: abre en la última vista usada, aquí Resultados vacío |
| `10..14_*_base.png` | Las 5 vistas con el motor base |
| `21_escape_mod_overlay.png` | Escape de la variante +20 mm con superposición pedida (no aparece; ver bug D2) |
| `22_proyecto_mod.png` | Vista Proyecto con la variante |
| `23_simular_mod_preset24.png` | Preset de 24 ciclos con presupuesto de 60 s |
| `24_resultados_comparacion.png` | Comparación de 2 corridas: gráfico de potencia vacío |
| `25_resultados_traza_escape.png` | Traza de presión en la celda 2 del escape |
| `26_traza_sola.png` | Esa traza aislada |
| `31_escape_980.png`, `34_resultados_980.png` | Escape y Resultados a 980×680 |

**Límite de la inspección:** no fue un uso manual con mouse. No se vieron diálogos abiertos, tooltips, hover ni una corrida en curso.

### 0.2 Herramientas comerciales

No se instaló ni se usó ningún software comercial. **Ninguna función comercial fue "probada personalmente".** Etiquetas usadas:

| Etiqueta | Significado |
|---|---|
| **[MAN]** | Manual oficial |
| **[WEB]** | Sitio del fabricante |
| **[CAP]** | Captura oficial observada (URL en §3) |
| **[VID]** | Sólo la descripción de un video oficial |
| **[INF]** | Inferencia |
| **NO VERIFICADO** | Sin evidencia suficiente |

| Herramienta | Versión y fecha de la evidencia | Calidad de la evidencia |
|---|---|---|
| **EngMod2T** (Vannik) | Dat2T 7.5.0, EngMod2T 6.9.5, Post2T 3.5.4 (news 2024-01-08); sitio actualizado 2025-06-21; 3 videos oficiales de 2025 | Sin manual público. Capturas oficiales abundantes; sólo se leyeron las descripciones de los videos. El diálogo de RPM y ejecución está **NO VERIFICADO**. |
| **MOTA** (Beven Young / IWT) | Producto v8.00 (manual v8, PDF de 2024-06). Todas las capturas son v6.00 (IWT dice que las salidas v8 "appear the same") | Buen manual. Las capturas son de una UI antigua; la UI v8 está **NO VERIFICADA** visualmente. |
| **WaveDyno** | Web app; docs con lastmod 2026-10-14; sin número de versión ni changelog | Docs detalladas con capturas. La app (requiere login) no se abrió. |
| **DynomationTwoStroke** (Motion Software) | Manual v1.10 de 06/2014; programa DOS (©1995–2014) | Manual completo de 50 páginas; 2 capturas oficiales. Es referencia secundaria y de interfaz antigua. |

**Disponibilidad en WaveDyno:**
- **Disponible (plan gratuito):** solver, barridos, cycle analysis, wave diagram, proyectos, comparación y diff contra baseline.
- **Anunciado ("Builder — not available yet"):** batch y barridos paramétricos, PDF de construcción con desarrollos de conos, exports.
- **En desarrollo:** páginas públicas de corridas.
- **Contradicción:** las docs describen la exportación CSV como operativa y la página de precios la lista como Builder. Queda NO VERIFICADO.

**Por qué no se agregó otra herramienta:** las cuatro ya cubren tres generaciones de interfaz (DOS de teclado, formularios Windows de los 90/2000, web moderna por tarjetas) y dos modelos de archivo (archivos sueltos y proyecto en la nube). Una quinta (p. ej. Lotus Engine Simulation o GT-Power, orientados a 4T y OEM) no aporta convenciones específicas del preparador 2T.

---

## 1. Resumen ejecutivo

1. **La hipótesis del dueño es correcta, pero incompleta.**
   - Dino está organizado alrededor del **ciclo de vida de una corrida auditada**: configuración con identidad, preflight, artifact root, run ID, re-auditoría, clasificación.
   - Los cuatro comerciales se organizan alrededor del **motor y sus modificaciones**: componentes, después barrido de RPM, después curva de potencia superpuesta.
   - Esto se ve en la navegación ("Vistas: Motor / Escape / Proyecto / Simulación / Resultados"), en lo que domina cada pantalla (hashes, "Preflight PASS · fuel 23dbb59e…", artifact root, Run ID) y en el lenguaje (EXPLORATORY, primarias, conservación).
2. **Hay una segunda causa que la UI no puede resolver por sí sola: una brecha de capacidad.**
   - El flujo comercial culmina en **curvas de potencia y par vs RPM superpuestas**.
   - Dino corre **un régimen por corrida**, y no hay barrido.
   - Las métricas de potencia, par y BMEP requieren un ciclo periódico aceptado. Ninguna de las 5 corridas reales lo identificó.
   - 1 ciclo dura ≈26 s (13 celdas) y el presupuesto máximo es 600 s, o sea ≈22 ciclos como techo.
   - Resultado: **la pantalla que en un simulador comercial es el centro (dyno chart) en Dino está vacía por diseño** ("Sin valores válidos para graficar").
   - Mientras sea así, la interfaz no debe imitar el centro comercial. Debe poner en el centro **lo que Dino sí entrega hoy**: geometría, distribución, presión del cilindro y ondas del escape a un régimen, comparadas entre variantes. La curva de potencia debe mostrarse como lo que es: un espacio reservado que se llena sólo con puntos periódicos aceptados.
3. **Lo que conviene adoptar** es lo que las cuatro herramientas comparten:
   - escape como tabla de tramos (L, Ø entrada, Ø salida) con perfil dibujado y derivados inmediatos (ángulo de cono, largo total, volumen);
   - distribución en **grados** con mapa de lumbreras;
   - "empezar desde un motor de ejemplo";
   - comparación = **superponer runs con una baseline explícita**;
   - ondas como detalle a un régimen;
   - lo avanzado plegado.
4. **Arquitectura recomendada:** "Banco de puesta a punto" (§8, alternativa B+).
   - Una sola ventana centrada en el motor activo y sus variantes, con Build a la izquierda y Resultados siempre visibles a la derecha.
   - Variantes como configuraciones de ingeniería con diff legible.
   - Correr y ver en el mismo lugar.
   - Lo de Dino (auditoría, provenance, conservación, checkpoints) va a un **cajón de evidencia** a un clic: siempre presente, nunca en el camino.
5. **Hay 4 defectos funcionales de V2 que conviene corregir antes de cualquier rediseño** (§6). Están medidos, no sólo vistos.

---

## 2. Cómo se organiza cada herramienta (síntesis)

### EngMod2T: suite de programas separados
- **Programas.** Dat2T (preprocesador), EngMod2T (solver), Post2T (postprocesador), Batch2T (colas), Movie2T (animación de ondas), MotaToDat2T [WEB]. Ciclo de trabajo: Dat2T → EngMod2T → Post2T → volver a Dat2T [VID].
- **Datos del motor.** Diálogos por componente con Help / Print / Accept / Cancel, uno por archivo de componente (`.inl`, `.trp`, `.tmp`) [CAP].
- **Lumbreras.** Se describen en mm y en paralelo muestran **timing en ° ATDC, duración, área y % del diámetro** [CAP RSA125-ExPort, TrPort]. Hay **mapa de lumbreras desenrollado** [CAP 2T-PortMap] y verificación de STA con potencia alcanzable [CAP 2T-STA].
- **Calculadoras integradas.** Cárter, culata y squish, "Adjust Cylinder Height" con la tabla de timings viejos y nuevos [CAP].
- **Escape.** Tramos (longitud y Ø final) con **esquema acotado**: longitudes, Ø y ángulos por tramo, largo sintonizado, volumen, relación de volúmenes [CAP RSA125-TunedPipe]. Hay diseñador empírico con rangos guiados ("starting point only") [CAP 2T-TunedDesign] y chequeo de tubos demasiado cortos o largos [CAP 2T-PipeCheck].
- **Post2T.** Menú de tipos de gráfico; trazas con líneas de eventos EPO/TPO/BDC; comparación con "Add File" de varios resultados [CAP Post2T-Menu, 2T-TraceResults, RSW_TZ_Power]; también datos de dinamómetro medidos [WEB].

### MOTA: hub de pantallas con estado de completitud
- **Pantalla central DFCU.** Una grilla de botones que abren pantallas de entrada. **Rojo = incompleto, verde = completo y válido**. Los botones de lumbreras y ductos aparecen según la configuración [MAN v8].
- **Validación y guardado.** No se sale de una pantalla con datos fuera de rango y **no se puede guardar un archivo incompleto** [MAN].
- **Lumbreras.** En **grados** (apertura y apertura plena ATDC) más anchos de arco en mm. Herramientas de conversión mm↔°, cuerda↔arco [MAN, CAP user4].
- **Escape.** Tabla de tramos (Ø entrada, Ø salida, L). "**Display Profile**" muestra el esquema con ángulo y volumen por tramo [MAN; sin captura oficial]. Hay un optimizador de cámara (>30 min) [MAN] y desarrollos de conos para fabricar [MAN].
- **Régimen.** Velocidad inicial, incremento y cantidad (hasta 40), más un único régimen para gráficos de ondas [MAN].
- **Ejecución.** Batch de hasta 12 `.dat` [CAP user3].
- **Resultados.** Power/Torque con overlay de hasta 5 adicionales [MAN, CAP power1]. Ondas animadas a lo largo del ducto [CAP wave]. Variables del escape en 4 paneles con EPO/BDC/EPC [CAP ducts].
- **Convergencia.** **La juzga el usuario** leyendo el `.per` (DR vs flujo de escape <1 %) [MAN].

### WaveDyno: web moderna, tarjetas, run history
- **Entrada.** **Asistente de 5 pasos omitibles** que parte de un *archetype* ("125 road race", "125 moto-X"). Al pie, un resumen vivo: cilindrada, B×S, duraciones, "pipe ≈ rpm", warnings [MAN docs, CAP wizard].
- **Estructura.** Pestañas Build (Engine, Ports, Ducts, Combustion) y Run (Setup, Dyno, Cycle analysis, Wave diagram) [MAN docs].
- **Lumbreras.** **Se escriben en grados**. El **Port map** (camisa desenrollada) muestra la profundidad en mm. Hay **diagrama circular de timing**, ventanas por tarjeta y time-area con bandas orientativas [CAP ports-baseline].
- **Escape.** Tarjeta con toggle Straight/Expansion, **perfil vivo**, tabla SECTION/L/Ø in/Ø out con filas nombradas (header, diffuser, belly, baffle, stinger), "+"/"×" por fila, "scale lengths…", "design a pipe…", y badges "843 mm total" y "tuned ≈ 12900 rpm" [CAP getting-started-mx-ducts].
- **Ejecución.** Dyno sweep From/To/Step/Quality con **costo estimado antes de correr**. Los puntos aparecen en la curva a medida que convergen [MAN docs, CAP setup-sweep].
- **Resultados.**
  - **Puntos no convergidos marcados** (círculo hueco con borde rojo: "A flagged point isn't a result") y banner de aviso [MAN docs].
  - Clic en un punto abre su ciclo; **wave diagram x–θ** con silueta del escape, eventos y colorbar [CAP wave-13000].
- **Comparación.** Hasta 8 runs, **baseline explícita**, deltas en tooltip sólo con RPM idéntico, **"Diff run inputs"** campo a campo [CAP overlay, diff].
- **Persistencia.** Proyecto en la nube con guardado implícito [INF].

### DynomationTwoStroke: programa DOS de teclado
- **Pantallas.** Hasta 9 páginas de edición (PgUp/PgDn) con diagramas acotados por letras [MAN p20–41].
- **Motor nuevo.** Sólo a partir de un archivo existente ("There is no direct menu selection to create an empty engine") [MAN p21].
- **Lumbreras.** En **mm** (top/bottom); los timings aparecen sólo como líneas en los gráficos [MAN].
- **Escape.** Tabla de segmentos (L, Ø salida) con **%, MESH ERROR, ángulo** y perfil dibujado [CAP MainScreen3].
- **Ejecución.** Start/Finish/Step RPM; ciclos recomendados 20 [MAN p34]. **Pantalla de cálculo en vivo** con presiones y valores [CAP MainScreen4].
- **Comparación.** Hasta 10 motores; **escalas fijas manuales** "para que las comparaciones sean posibles" [MAN p24–28].
- **Resultados incompletos.** **No se pueden ver** (`.SM2` sólo si la corrida terminó) [MAN p16].

---

## 3. Capturas de referencia (fuentes)

No se reproducen ni se copian. Se citan para consulta.

| Herramienta | URL | Qué muestra | Versión |
|---|---|---|---|
| EngMod2T | https://vannik.co.za/images/RSA125-TunedPipe.jpg | Esquema acotado del escape: L, Ø, ángulos, largo sintonizado, volumen | 2T actual (sitio 2025) |
| EngMod2T | https://vannik.co.za/images/RSA125-ExPort.jpg | Lumbrera de escape: mm + ° ATDC + duración + área | idem |
| EngMod2T | https://vannik.co.za/images/2T-PortMap.jpg | Mapa de lumbreras desenrollado | idem |
| EngMod2T | https://vannik.co.za/images/2T-STA.jpg | STA vs objetivo, potencia alcanzable | idem |
| EngMod2T | https://vannik.co.za/images/2T-CylinderHeight.jpg | Calculadora de altura de cilindro: timings viejos/nuevos | idem |
| EngMod2T | https://vannik.co.za/images/2T-TunedDesign.jpg | Diseñador empírico de escape | idem |
| EngMod2T | https://vannik.co.za/images/2T-PipeCheck.jpg | Chequeo de tubos | idem |
| EngMod2T | https://vannik.co.za/images/Post2T-Menu.jpg, https://vannik.co.za/images/2T-TraceResults.jpg | Post2T: menú y diálogo de trazas | idem |
| EngMod2T | https://vannik.co.za/images/RSW_TZ_Power.jpg, https://vannik.co.za/images/Pressure_RSW_13000rpm.jpg | Potencia superpuesta; presión vs ángulo con eventos | idem |
| MOTA | https://www.bevenyoung.com.au/power1.jpg | Power/Torque con overlay y botonera lateral | v6.00 |
| MOTA | https://www.bevenyoung.com.au/wave.jpg | Animación de ondas en ductos | v6.00 |
| MOTA | https://www.bevenyoung.com.au/ducts.jpg | Variables del escape (4 paneles) | v6.00 |
| MOTA | https://www.bevenyoung.com.au/user2.jpg, https://www.bevenyoung.com.au/user3.jpg, https://www.bevenyoung.com.au/user4.jpg | Menú File, selección de batch, Tools | v6.00 |
| WaveDyno | https://wavedyno.com/images/docs/getting-started-mx-ducts.png | Tarjeta del escape: perfil + tabla + badges | docs 2026-10 |
| WaveDyno | https://wavedyno.com/images/docs/raise-the-exhaust-port-ports-baseline.png | Ports: timing circular, port map, ventanas, time-area | docs 2026-10 |
| WaveDyno | https://wavedyno.com/images/docs/compare-two-pipes-overlay-kw-l1.png | Comparación de curvas con baseline y deltas | docs 2026-10 |
| WaveDyno | https://wavedyno.com/images/docs/compare-two-pipes-wave-13000-baseline-l1.png | Wave diagram x–θ | docs 2026-10 |
| WaveDyno | https://wavedyno.com/images/docs/raise-the-exhaust-port-plus2-diff.png | Diff run inputs | docs 2026-10 |
| WaveDyno | https://wavedyno.com/images/docs/tune-a-moped-pipe-wizard-2-ports.png | Asistente, paso de lumbreras | docs 2026-10 |
| WaveDyno | https://wavedyno.com/images/docs/raise-the-exhaust-port-setup-sweep.png | Dyno sweep + Environment | docs 2026-10 |
| Dynomation | https://www.motionsoftware.com/images/BackOfTwoStrokeWrapperMainScreen3.gif | Pantalla de cámara de expansión + resultados | 1995–2014 |
| Dynomation | https://www.motionsoftware.com/images/BackOfTwoStrokeWrapperMainScreen4.gif | Cálculo en vivo + ondas | 1995–2014 |

---

## 4. Matriz de comparación

Abreviaturas: **EM** = EngMod2T, **MO** = MOTA, **WD** = WaveDyno, **DY** = DynomationTwoStroke. "→ Adoptar/Conservar" es la conclusión de cada fila.

| # | Aspecto | Referencias | Dino V2 hoy (observado) | Parecidos / diferencias | Ventaja Dino | Fricción Dino | → Adoptar / Conservar |
|---|---|---|---|---|---|---|---|
| 1 | Primera pantalla | WD: asistente o el proyecto. MO: menú principal y File › New/Edit [MAN]. DY: menú principal con lista de resultados [MAN]. EM: Dat2T (NO VERIFICADO visualmente) | Fuente: "Configuración del motor" con Fixture A. `.exe`: **la última vista usada** (capturada: Resultados vacío). No hay inicio ni recientes | Todos abren sobre "qué motor"; Dino abre sobre una vista suelta | — | No hay punto de entrada; abrir en una vista vacía | Pantalla de inicio con motor activo, recientes y "Abrir ejemplo 125" |
| 2 | Motor nuevo | Las cuatro parten de **un motor existente o un arquetipo** (DY: "no direct… empty", MO: "easier… edit existing", WD: archetypes, EM: desde cero con soporte de incompletos [VID]) | "Nuevo" crea `dino-<carpeta>` desde Fixture A sintético, sin preguntar | Coinciden en la plantilla; difieren en que Dino no lo anuncia ni deja elegir el nombre al crear | Plantilla rotulada SYNTHETIC | Nombre automático raro; no se ve la cilindrada (123,2 cm³) | Asistente corto tipo WD: nombre, plantilla rotulada, B×S con cilindrada viva |
| 3 | Organización mecánica | EM: diálogos por componente. MO: hub DFCU con estado rojo/verde. WD: pestañas Build con tarjetas. DY: 9 páginas | Una página "Motor" larga: geometría + lumbreras + pérdidas + combustión + hash | Dino ≈ DY (páginas largas); los modernos fragmentan por componente con estado | Validación completa al aplicar | Un bloque sin jerarquía; mezcla editables, metadatos (AFR "no aplicado") y hashes | Tarjetas por componente con **estado de completitud** (idea de MO); lo inerte, fuera |
| 4 | Cilindro y distribución | MO y WD: **grados** como dato primario. EM: mm con ° y duración al lado. DY: mm, ° sólo en los gráficos | Tabla en mm (borde, altura, ancho, Cd, techo); **sin grados ni duración** | Dino = DY (el más antiguo) | — | El preparador piensa en ° de apertura y duración; Dino lo obliga a convertir | Mostrar °ATDC y duración derivados con `event_angles()`, como EM. Edición en ° como en WD: sólo si se valida la inversión mm↔° (decisión técnica, no física nueva) |
| 5 | Gráfica de lumbreras y geometría | EM: port map desenrollado, esquema de transfers. WD: timing circular + port map + time-area | **Ninguna** | Diferencia fuerte | — | Las lumbreras son invisibles | Diagrama de timing (circular o lineal 0–360°) y área vs ángulo con `area_at()`. Port map desenrollado si la geometría alcanza (ancho, altura, borde) |
| 6 | Dimensiones y unidades | Todas: mm de entrada. EM: métrico/imperial lado a lado. WD: kW/hp sólo de display. MO: no admite coma decimal [WEB FAQ] | mm, cm³, °. Spinboxes con 5 decimales y coma; tablas con 3 decimales; la tabla de escape acepta coma o punto | Similar | Acepta coma y punto (MO no) | 5 decimales en mm y rpm; formatos distintos entre spinbox y tabla | Decimales por magnitud; unidad pegada al campo |
| 7 | Escape | **Las cuatro: tabla de tramos (L, Ø) + perfil dibujado + derivados** (ángulo, largo total, volumen; EM: largo sintonizado; DY: %/mesh error; WD: tuned ≈ rpm) | Perfil a escala real con nombres de tramo; **dos tablas** separadas (estaciones con Ø, tramos con L); sin ángulo ni volumen por tramo; largo total sí; volumen total en un texto; cantidad de tramos fija | Coincide la base (tabla + perfil); Dino divide el dato en dos tablas | **Continuidad garantizada** por estaciones (ningún comercial la impone); escala axial = radial | Editar "la cámara" exige mirar dos tablas; faltan ángulos y volumen; no hay "+/×" (límite real del backend) | **Una tabla por tramo** (L · Ø entrada · Ø salida · ángulo · volumen), con Ø de entrada vinculado al Ø de salida del tramo anterior (continuidad conservada), y perfil acotado como el esquema de EM |
| 8 | Variantes | EM, MO, DY: **archivos con otro nombre** (+ notas: MO comment, DY notes). WD: runs dentro del proyecto + restore + diff | Variantes dentro del proyecto: crear, duplicar, renombrar, borrar, en el árbol y en la barra de contexto. "Difiere del base en 11 propiedades" | Dino ≈ WD (proyecto) | Variantes con identidad y padre; borrado protegido | **Dos nombres** para lo mismo (variante "Escape modified +20 mm" / display "Fixture A — sintético · escape length +20 mm"); diff en rutas JSON; "Escape original" idéntica al base (0 diferencias) | Variante = nombre + **diff en lenguaje de ingeniería** ("difusor 180 → 200 mm") + nota libre |
| 9 | RPM y condiciones | MO, DY, WD: **barrido Desde/Hasta/Paso**. MO y EM: ambiente, encendido y AFR por RPM, mariposa. WD: ambiente | **Un régimen por corrida**; sin ambiente, mariposa ni AFR operativo (AFR "metadato no aplicado"); "régimen de referencia" duplicado en Motor | Diferencia de capacidad, no sólo de UI | Honestidad sobre lo que no se usa | El usuario busca un barrido y no existe; dos campos de RPM | No fingir un barrido. Un "punto de prueba" explícito; una serie de puntos sólo si el dueño la autoriza (§9) |
| 10 | Preparar y ejecutar | WD: **estimación de costo antes**, puntos progresivos. DY: pantalla viva con presiones. MO: lista de batch. EM: Batch2T | Formulario con presupuesto, memoria, artifact root, Run ID; "Preflight PASS · … fuel <hash>"; confirmación; salida en log de texto + JSON | Dino ≈ un panel de ingeniero de sistemas | Preflight, límites de recursos, checkpoint, reanudar, cancelar | Datos de infraestructura en primer plano; **el preset de 24 ciclos deja 60 s de presupuesto** (≈2 ciclos posibles); sin progreso visual | Estimación de tiempo (como WD), **presupuesto acoplado al horizonte**, progreso visual, infraestructura en "Avanzado" |
| 11 | Potencia y par | **Centro de todas** (curva vs RPM superpuesta, kW/hp) | Gráfico vs RPM vacío: las 5 corridas no tienen valores (requiere un ciclo periódico aceptado) | Brecha de capacidad | No inventa potencia | La pantalla principal de Resultados es un recuadro vacío | Mostrar la curva sólo con puntos aceptados y, mientras no haya, un estado claro + lo que sí hay |
| 12 | Presión y ondas | EM: trazas con eventos + Movie2T. MO: animación por ducto, 4 paneles. WD: **mapa x–θ** + cycle analysis. DY: vista viva F8 | Traza vs ángulo por "celda N" o "cara N"; **eje Y forzado a 0 Pa** (la onda queda casi plana); sin eventos de lumbrera; sin marcas en Y | Dino tiene los datos (todas las celdas, ángulos exactos) pero los muestra peor que todos | Trazas re-auditadas, sin interpolación | No se lee la onda; "celda 2" no dice qué tramo es | Mapa x–θ discreto por celdas (como WD, sin interpolar), eventos EO/TO/TC/EC, eje Y ajustado, celdas con nombre de tramo |
| 13 | Antes/después | Las cuatro: overlay. WD: **baseline + deltas + diff de inputs** | Historial → elegir 2 → "Comparar 2 corridas" → 34 s de re-auditoría → misma página de Resultados con dos series; sin baseline ni deltas; la superposición en Escape no funciona tras "Abrir" | Dino tiene el overlay; le falta baseline y delta | Re-auditoría de lo comparado | No se ve "qué cambió" ni "cuánto" | Baseline explícita, Δ sólo en ángulos exactos, diff de configuración legible |
| 14 | Proyectos y archivos | EM, MO, DY: archivos sueltos (DY: 8.3, directorios registrados). WD: nube con guardado implícito | Proyecto `.dino2t.json` con variantes; corridas en artifact root (preferencia global); referencias externas | Dino está entre ambos modelos | Proyecto único con identidades; artifacts inmutables | La preferencia global quedó apuntando al **repo** (`E:\dino\Dino-active`), por eso hay un `exploratory-workflow-v1/` sin seguimiento en el repo; las corridas no viven "con" el proyecto | Carpeta de corridas por proyecto, sugerida junto al archivo; la raíz global sólo como avanzado |
| 15 | Errores, avisos, incompletos | DY: un incompleto no se puede ver; errores fatales sin detalle. MO: validador de rango, no guarda incompletos. WD: **puntos marcados** + banner + sugerencia | Clasificaciones explícitas (Terminada · sin periodicidad), motivo por métrica, fail-closed, re-auditoría | Dino ≥ todos en rigor | **Ventaja clara** | Se expresa con enums y párrafos, no con marcas visuales; los errores muestran el texto de la excepción | Adoptar la **gramática visual de WD** (punto hueco + motivo + acción) sobre la clasificación de Dino |
| 16 | Avanzado y científico | WD: secciones "(advanced)" plegadas. DY: mesh fijo "no cambiar". MO: coeficientes en las pantallas. EM: elección de modelo | Malla 1/2/4 plegada; hashes, provenance, fuel hash, artifact root y RSS **visibles en el flujo principal** | Dino pliega lo numérico pero expone la trazabilidad | Trazabilidad total | Ruido en el momento de editar y correr | Cajón de evidencia; hashes fuera de la vista habitual |
| 17 | Navegación y pasos | DY: un programa, ≈8 menús. MO: hub + run + display, ≈9 pasos. EM: 3 programas, ≈10–13 pasos. WD: un espacio, ≈8 pasos | Dos listas de navegación ("Proyecto" + "Vistas") + barra + inspector; **≈22–26 pasos y 6 cambios de vista** en el escenario (§5) | Dino es el más largo | — | Navegación abstracta ("Vistas") y "Proyecto" como vista | Una sola navegación por componente y por fase |
| 18 | Novatos vs expertos | WD: asistente + notas. MO: rojo/verde. DY: "un día para acostumbrarse". EM: tutoriales en video | Textos de aviso largos en cada página; nada guía qué falta | — | Avisos honestos | Tanto texto de advertencia que pierde valor | Avisos cortos, en contexto, con detalle a un clic |

---

## 5. Recorrido del escenario: 125 cc con una cámara 20 mm más larga

Escenario: tramo de cámara 180 → 200 mm, simular, ver el estado, comparar, guardar. En Dino el tramo "diffuser" del fixture mide 180 mm.

| | EngMod2T [INF desde CAP/VID] | MOTA [MAN] | WaveDyno [MAN docs] | Dynomation [MAN] | **Dino V2 hoy [observado]** |
|---|---|---|---|---|---|
| A. Cargar motor | Dat2T › abrir proyecto | File › Edit existing (`R128.dat`) | Abrir proyecto o asistente 125 | Retrieve `.DY2` | Archivo › Abrir… › diálogo › proyecto |
| B. Datos y distribución | Diálogos por componente; timing en ° visible | Botones DFCU; timing en ° | Build tabs; ports en ° con port map | Páginas 1–5; ports en mm | Página Motor; ports en mm, **sin °** |
| C. Ver el escape | Esquema acotado | Display Profile | Tarjeta de escape con perfil | Página 6 con perfil | Vista Escape: perfil + 2 tablas |
| D. 180 → 200 | Editar la longitud del tramo; guardar con otro nombre | Editar la fila; guardar con otro nombre | Editar la celda L | Editar LENGTH; Esc › nuevo nombre | Editar L del tramo "diffuser" › "Guardar como nueva variante…" › nombre |
| E. Preparar | EngMod2T: modelo + barrido (NO VERIFICADO) | Batch con los 2 `.dat` | Setup From/To/Step › Run dyno (con estimación) | Single o Multiple | Simulación: RPM, preset, **subir presupuesto a mano**, Simular › confirmar. **Repetir para la otra variante** (cambiar la variante activa) |
| F. Resultados y estado | Post2T; la convergencia no se muestra | Leer el `.per` y verificar DR <1 % a mano | Curva con puntos marcados | Watch HP en la pantalla viva | Log JSON; luego Resultados: **curva vacía**; clasificación en la tabla |
| G. Comparar | Post2T › Add File ×2 | Overlay › Add | Compare › baseline › deltas; Diff inputs | Tag 2 engines | Historial › Ctrl+clic en 2 filas › Comparar › espera 34 s › scroll › elegir "celda 1" en el combo |
| H. Guardar | Ya en archivos | Ya en archivos | Implícito | Ya en archivos | Archivo › Guardar |
| **Pasos aprox.** | 10–13 | ≈9 + rpm por `.dat` | ≈8 | ≈8 menús / 15–20 teclas | **≈22–26** |
| **Cambios de pantalla** | 3 programas | ≈4 | ≈3 | ≈3 | **6** (Motor, Escape, Simulación ×2, historial, Resultados) |
| **Hay que recordar** | Qué archivo es cuál | Nombres de archivo; regla del 1 % | Qué run es la baseline | Nombres 8.3 | Qué variante está activa al simular; **qué celda corresponde a qué tramo**; que el presupuesto no acompaña al preset; que 1 ciclo no da potencia |
| **Datos ingresados a mano** | L + nombre | L + nombre | L + nombre de run | L + nombre | L + nombre + RPM ×2 + presupuesto ×2 |
| **Riesgo de error** | Sobrescribir la baseline | Rangos validados; convergencia ignorada | Bajo (diff y baseline) | Sobrescribir; MESH ERROR | Corrida cortada por presupuesto; comparar celdas equivocadas; comparar variantes que difieren en más cosas |
| **Interpretación** | Buena (curvas + eventos) | Buena (curvas); convergencia oculta | Muy buena (deltas, flags, mapa x–θ) | Media | **Baja**: curva vacía, traza plana, estados en texto |

### Dino: lo que funciona vs lo que no está validado

- **Funciona hoy:**
  - edición de geometría con validación;
  - variante con nombre;
  - corrida EXPLORATORY a un régimen con auditoría, conservación y checkpoint;
  - historial;
  - comparación de trazas re-auditadas de 2 corridas;
  - guardado del proyecto.
- **No validado o no disponible:**
  - periodicidad (no identificada en ninguna corrida real);
  - potencia, par y BMEP (UNDEFINED);
  - independencia espacial de la malla del escape (no demostrada);
  - validación experimental (pendiente);
  - VERIFIED (no disponible);
  - barrido de RPM (no existe).

La comparación que Dino puede ofrecer hoy es **de comportamiento de ondas y presión a un régimen**, no de desempeño.

---

## 6. Defectos funcionales de V2 medidos durante la inspección

| ID | Defecto | Evidencia | Efecto |
|---|---|---|---|
| D1 | "Superponer" queda con la lista del proyecto anterior. Después de Archivo › Abrir sólo ofrece "Sin superposición" | `overlay_selector` se llena sólo en `ExhaustPage.__init__` (`exhaust_page.py:80-81`). Medido: `['Sin superposición']` tras `_open()` | La comparación visual de escapes no funciona en el flujo real |
| D2 | El resaltado del tramo modificado nunca se activa | `_changed_sections` busca el *nombre* del tramo en la ruta, pero la ruta usa el índice (`…/chamber/sections/1/length_mm`). Medido: `set()` | No se ve qué cambió en la variante |
| D3 | El preset "Observar periodicidad · 24 ciclos" deja el presupuesto en 60 s | `_apply_preset` sólo cambia `cycles`. 1 ciclo real = 26,25 s | La corrida termina por presupuesto tras ≈2 ciclos; el preset promete algo imposible |
| D4 | El eje Y de las trazas fuerza el 0 | `plot.py:34` `ymin=min(0.0,…)` sobre presión absoluta ≈1e5 Pa | La onda del escape se ve casi plana (captura 26) |
| D5 | La preferencia `artifact_root` del usuario apunta al repositorio | `QSettings` real = `E:\dino\Dino-active`; carpeta sin seguimiento `exploratory-workflow-v1/dino-project/…` en el repo | Corridas escritas dentro del árbol git |
| D6 | Claves de pruebas en el registro real del usuario (`active_variant/io-test`, `startup-test`, `ux-small-window`…) | `QSettings.allKeys()` | Los tests escriben en la configuración real; riesgo de estado contaminado |
| D7 | Dos nombres para la misma variante (clave del proyecto vs `display_name`) | Barra de contexto vs inspector (captura 21) | Confusión de identidad |
| D8 | La terminal del IDE del usuario mostraba `Error calling Python override of QWidget::metric()` al lanzar `motorsim.dino_desktop` | Visto en una captura de pantalla incidental; **no diagnosticado** | Posible error de pintura; requiere reproducción |

---

## 7. Diagnóstico: por qué Dino se siente distinto

Separado en las tres capas pedidas.

### 7.1 Modelo mental (la causa principal)

- **Comerciales:** *motor → modificación → barrido → curva → comparar curvas*. La unidad de trabajo es **la modificación de ingeniería**.
- **Dino:** *configuración con identidad → preflight → corrida con run ID en un artifact root → re-auditoría → clasificación*. La unidad de trabajo es **la corrida auditada**.

Evidencia en la UI actual:
- El inspector habla de "propiedades" diferentes.
- Simulación expone presupuesto, RSS, artifact root, Run ID y "Guardar solicitud de revisión".
- El historial lista corridas con columnas Clasificación, Auditoría y Conservación.

**La hipótesis es verdadera en lo esencial.** El matiz es que la mitad del problema no es UI: el eje comercial (curvas vs RPM) todavía no existe como capacidad.

### 7.2 Organización de la información

- **"Proyecto" es una vista al mismo nivel que Motor y Escape**, y además hay un árbol de proyecto y una barra de variante: tres lugares para el mismo concepto.
- **"Vistas" es una abstracción de software;** los comerciales nombran componentes (lumbreras, escape) y fases (correr, resultados).
- **El motor no se ve:** ni una sección, ni un diagrama de timing, ni la cilindrada. EM, WD y DY muestran un dibujo o diagrama antes o junto a la tabla.
- **El escape no es central,** aunque es lo que el escenario modifica. Está en una vista más, con dos tablas.
- **Correr y ver están separados:** Simulación produce un log; los resultados viven en otra vista y se llega por el historial. En WD y DY la curva o las presiones aparecen donde se corre.
- **Trazabilidad expuesta en momentos inadecuados:** el hash de combustible en la línea del preflight; el hash de configuración en Motor y Escape; los párrafos sobre VERIFIED en cada visita a Simulación.
- **No se sabe qué falta para simular.** MOTA lo resuelve con rojo/verde y WD con el resumen del asistente. Dino lo tiene (preflight) pero escrito en una línea técnica y sólo en Simulación.

### 7.3 Aspecto visual (secundario)

- Títulos de 22 pt, 5 decimales y gráficos sin escala en Y.
- El tema oscuro y la densidad no son el problema; WD también es oscuro.

---

## 8. Alternativas de arquitectura

### Alternativa A: estación clásica por componentes (idioma de MOTA, EngMod y Dynomation)

```
┌ Dino 2T · Mi125.dino2t ────────────────────────────────────────────────────────────┐
│ Archivo  Motor  Simular  Resultados  Herramientas  Ayuda                            │
├────────────────────────┬────────────────────────────────────────────────────────────┤
│ MODELO  (estado)       │  ESCAPE · Cámara de expansión                    [Guardar] │
│ ● Configuración   ✓    │  ┌ perfil acotado ─────────────────────────────────────┐   │
│ ● Cilindro        ✓    │  │ Ø20 ═80═╲__200__/ Ø52 ═100═ \__170__/ Ø16 ═120═     │   │
│ ● Lumbreras       ✓    │  │      4,6°            −6,0°        L total 670 mm    │   │
│ ● Cárter          ✓    │  └─────────────────────────────────────────────────────┘   │
│ ● Escape          ●mod │  Tramo     L mm   Ø ent  Ø sal  ángulo  vol cm³           │
│ ● Combustión      ✓    │  header     80    20,0   20,0    0,0°    25               │
│ ● Pérdidas        ✓    │  diffuser  200 ◂  20,0   52,0    9,1°   217               │
│ ─────────────────────  │  belly     100    52,0   52,0    0,0°   212               │
│ CORRIDAS               │  ...                                                      │
│ ▸ Simular…  (F5)       │                                                           │
│ RESULTADOS             │  ▸ Avanzado: malla numérica                               │
│ ▸ Abrir postproceso    │                                                           │
└────────────────────────┴────────────────────────────────────────────────────────────┘
Simular… abre un diálogo (punto, ciclos, estimación). Resultados abre una ventana o
espacio "Post" separado, con overlay de corridas.
```

- **Navegación:** árbol de componentes con estado de completitud (✓ / ● modificado / ✗ incompleto), como el DFCU de MOTA. Variantes como "Guardar como…" del modelo.
- **Editor de motor:** una pantalla por componente; Lumbreras con ° derivados y diagrama de timing.
- **Escape:** como arriba.
- **Simulación:** diálogo modal.
- **Resultados:** espacio "Post" aparte, al estilo Post2T, con "Agregar corrida".
- **Avanzado:** menú Herramientas › Evidencia, Malla, Preferencias.
- **Pros:** familiar para quien viene de MOTA, EM o DY; mapea 1:1 con los componentes del backend; implementación incremental.
- **Contras:** reproduce la separación build/run/post que hoy ya molesta (6 cambios de vista); deja la comparación como tarea de postproceso; con resultados de un solo régimen, el "Post" queda pobre.

### Alternativa B: banco de puesta a punto (idioma de WaveDyno, más Dino)

```
┌ Dino 2T ───────────────────────────────────────────────────────────────────────────────────┐
│ Mi 125 ▾ │ Variante: [Cámara +20 ▾]  vs  Baseline: [Original ▾] │ EXPLORATORIO │ ✓ Guardado │ ⓘ Evidencia │
├──────────────────────────────────────────────┬─────────────────────────────────────────────┤
│ BUILD  [Motor][Lumbreras][Escape][Combustión]│ RESULTADOS de la variante y su baseline      │
│                                              │ ┌ Estado ─────────────────────────────────┐ │
│ ┌ Escape · cámara de expansión ────────────┐ │ │ 3000 rpm · 1 ciclo · auditoría ✓        │ │
│ │ (perfil acotado; baseline punteada)      │ │ │ ◌ Periodicidad no identificada →        │ │
│ │  header│ diffuser +20 │belly│baffle│sting│ │ │   sin potencia/par. [Correr 20 ciclos]  │ │
│ └──────────────────────────────────────────┘ │ └─────────────────────────────────────────┘ │
│ Tramo    L mm   Ø ent  Ø sal  ángulo  vol    │ [Ondas x–θ][Presión escape][Cilindro][Curva]│
│ diffuser 200◂   20,0   52,0   9,1°    217    │ ┌──────────────────────────────────────────┐│
│ ...                                          │ │ θ ↓      mapa de presión por celda       ││
│ Largo total 670 mm (+20) · Vol 590 cm³       │ │ 0°  ░░▒▒▓▓██▓▒░  (variante)              ││
│                                              │ │ 360°            │ (baseline) │ Δ          ││
│ Cambios vs baseline: diffuser L 180 → 200 mm │ └──────────────────────────────────────────┘│
├──────────────────────────────────────────────┴─────────────────────────────────────────────┤
│ PRUEBA  Régimen [3000] rpm · Horizonte [Diagnóstico 1c ▾] ≈ 30 s · [▶ Correr variante] [▶ Correr ambas] │
│ ▓▓▓▓▓▓▓░░░ ciclo 1/1 · 18 s                     Corridas: ✓orig·3000  ✓+20·3000  ◌+20·4000  │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Navegación:** pestañas Build arriba a la izquierda; resultados siempre visibles a la derecha; una barra de prueba abajo. Variante y baseline en la barra superior. Corridas como chips o lista en la barra de prueba.
- **Editor de motor:** tarjetas como WD. "Lumbreras" con diagrama de timing circular o lineal, °ATDC y duración derivados, y área vs ángulo.
- **Escape:** tarjeta con perfil acotado y baseline superpuesta, una tabla de tramos con ángulo y volumen, y la diferencia vs baseline en palabras.
- **Simulación:** la barra de prueba (régimen, horizonte con estimación y presupuesto acoplado, "Correr variante" o "Correr ambas"), con progreso visible. Cuando termina, el panel derecho se actualiza.
- **Resultados:** tarjeta de estado con marca visual y acción sugerida; pestañas Ondas x–θ, Presión escape (con eventos de lumbrera y nombres de tramo), Cilindro, Curva (vacía mientras no haya puntos periódicos, con explicación).
- **Comparación:** siempre contra la baseline elegida. Δ sólo en ángulos exactos. Diff de configuración legible.
- **Avanzado:** botón "ⓘ Evidencia" que abre un cajón con identidades, hashes, provenance, auditoría, conservación, hard gates, artifact root y run ID. Malla numérica dentro de la tarjeta de Escape, plegada.
- **Pros:** une correr y ver; pone el escape en el centro; elimina "Vistas" y "Proyecto" como vistas; la comparación es nativa. Es la convención más reciente y la más cercana a la física de Dino (WD también es quasi-1D FV y marca convergencia).
- **Contras:** pantalla densa a 980×680, que necesita un modo apilado; requiere reorganizar el shell (no el backend).

### Alternativa C (recomendada): B con dos piezas de A

B+ = B, más:
- **el estado de completitud por componente** de A (MOTA DFCU), como insignias en las pestañas Build, que explican "qué falta para simular" usando el preflight;
- un **modo "Post" a pantalla completa** desde el panel de resultados, para el análisis largo (equivalente a Post2T o Powaplot): un botón para maximizar el panel derecho.

A 980×680 el panel de resultados se vuelve una pestaña más: Build | Resultados.

---

## 9. Recomendación final

### 9.1 Por qué B+

| Decisión | Evidencia |
|---|---|
| Resultados junto a la edición | Dynomation muestra presiones en vivo durante el cálculo; WaveDyno pone curva y ciclo junto a Build. El costo actual de Dino son 6 cambios de vista. |
| Escape como tabla + perfil + derivados | Lo hacen las cuatro herramientas. |
| Distribución en grados con diagrama | MOTA y WaveDyno la ingresan en grados; EngMod2T la muestra junto a los mm. Dino es la única con mm sin grados, junto a Dynomation (DOS, 2014). |
| Baseline explícita, deltas y diff de entradas | WaveDyno; MOTA declara que su valor está en comparar ("strength… ability to compare"). |
| Puntos no convergidos marcados visualmente | WaveDyno. Dino tiene mejor clasificación pero peor presentación. |
| Completitud por componente | MOTA DFCU. |

### 9.2 Qué conservar exactamente de Dino UX V2

- `DesktopContext` con `select_variant`, `duplicate_variant`, `rename_variant`, `delete_variant`, `set_project_name`.
- La protección de borrado con referencias.
- La barra de contexto: se convierte en la barra superior con variante y baseline.
- Edición del escape por estaciones como regla interna de continuidad, aunque la vista pase a una tabla por tramo.
- Perfil a escala real; superposición de variantes (corrigiendo D1); malla 1/2/4 plegada con su aviso.
- `run_history.list_project_runs` (índice de sólo lectura).
- `import_exploratory_runs` (re-auditoría) y `run_background` con cancelación.
- Checkpoint, reanudación y confirmación explícita.
- Separación de evidencia histórica IMPL2 (botón explícito, sin autocarga).
- `_state_label` como semilla de la capa de presentación.
- La regla "sin interpolación / huecos visibles".

### 9.3 Qué reorganizar

| Hoy | Mañana |
|---|---|
| Vistas Motor / Escape / Proyecto / Simulación / Resultados + árbol de proyecto + barra | Pestañas Build (Motor, Lumbreras, Escape, Combustión y pérdidas) + panel de Resultados + barra de prueba + selector de variante y baseline |
| Vista "Proyecto" (diff en rutas JSON, botones de variante) | Menú "Variante" (crear, duplicar, renombrar, borrar) + "Cambios vs baseline" en el Build + diff crudo en el cajón de Evidencia |
| Historial dentro de Simulación | Lista de corridas en la barra de prueba (chips) + tabla completa en el cajón o en modo Post |
| Resultados: combo de métrica, lista de variantes, tabla de puntos, trazas, detalles en una sola columna | Tarjeta de estado + pestañas de gráficos; detalle del punto en Evidencia |

### 9.4 Qué eliminar de las pantallas principales

Todo esto va al cajón de Evidencia o a Preferencias:
- hashes de configuración, combustible, resultado y primario;
- artifact root;
- Run ID;
- memoria RSS;
- "Guardar solicitud de revisión";
- texto permanente sobre VERIFIED (queda un botón deshabilitado con candado);
- la explicación de PERIOD_1 en párrafo (pasa a un tooltip del estado);
- la columna Provenance de la tabla de tramos (pasa a un ícono);
- AFR "metadato no aplicado" y "coordenada de carga" cuando no tienen efecto (pasan a la sección avanzada de Combustión y pérdidas).

### 9.5 Controles a rediseñar

- **Tabla de tramos única:** L, Ø ent, Ø sal, ángulo (derivado), volumen (derivado). Editar el Ø de salida de un tramo actualiza el Ø de entrada del siguiente, en la misma estación.
- **Perfil acotado:** cotas de L y Ø, ángulo por tramo, largo total y Δ vs baseline, resaltado del tramo cambiado (D2).
- **Diagrama de distribución:** área efectiva vs ángulo 0–360° por lumbrera, con PMS/PMI y EO/TO/TC/EC, usando `TwoStrokePortSet.area_at`/`event_angles`. En la tabla, columnas derivadas "Abre °ATDC / Cierra / Duración".
- **Barra de prueba:**
  - régimen;
  - horizonte con presupuesto acoplado (D3) y estimación basada en `elapsed_seconds/cycles_completed` de corridas previas de la misma configuración de celdas, rotulada "estimación";
  - progreso por ciclo y por tiempo.
- **Tarjeta de estado del resultado:** ícono, estado traducido, motivo y acción ("Correr más ciclos" precarga el horizonte).
- **Gráficos:**
  - eje Y ajustado a los datos (D4) con marcas;
  - eventos de lumbrera;
  - celdas nombradas por tramo y posición;
  - mapa x–θ discreto (bandas por celda, sin interpolar);
  - Δ variante − baseline sólo en ángulos idénticos.
- **Curva vs RPM:** puntos sólo con métricas DEFINED; los no aceptados, marcados con motivo (gramática de WD). Vacía con explicación y acción mientras no haya puntos.

### 9.6 Interacción motor → escape → simulación → resultados

1. Editar en Build marca la variante como "modificada sin aplicar". Aplicar valida, igual que hoy.
2. El perfil y los derivados se actualizan en vivo.
3. "Correr variante" usa el régimen de la barra.
4. "Correr ambas" encadena variante y baseline al mismo régimen. **Requiere decisión del dueño** (ver 9.8); mientras tanto, hay una confirmación por corrida.
5. Al terminar, el panel de Resultados muestra esa corrida contra la última corrida de la baseline al mismo régimen, si existe. Si no existe, ofrece "Correr baseline a 3000 rpm".
6. Cambiar de variante cambia Build y Resultados a la vez.

### 9.7 Prácticas comerciales que NO conviene reproducir

| Práctica | Herramienta | Por qué no |
|---|---|---|
| Convergencia que juzga el usuario leyendo un texto | MOTA `.per`, Dynomation "watch HP" | Dino ya clasifica; hay que mostrarlo, no delegarlo |
| Ocultar resultados incompletos | Dynomation | Dino debe mostrarlos rotulados; es su ventaja |
| Escalas de gráficos fijas a mano como única forma de comparar | Dynomation | Usar escalas compartidas automáticas entre runs comparados, con bloqueo opcional |
| Prohibir guardar un modelo incompleto | MOTA | El proyecto debe poder guardarse con estado "incompleto" |
| Formularios no redimensionables, nombres 8.3, teclas de función | MOTA, Dynomation | Interfaces antiguas |
| Varios programas separados para pre, solver y post | EngMod2T | Rompe el flujo |
| Asistente que reconstruye el escape al tocar timing o RPM objetivo | WaveDyno | Efecto lateral silencioso |
| Diffs en SI crudo (0.265 → 0.295 m) | WaveDyno | Mostrar mm |
| Generadores empíricos de escape ("design a pipe", "tuned ≈ rpm") y bandas STA o time-area | EM, WD | Son modelos empíricos que **Dino no tiene en su backend**. Agregarlos sería introducir una afirmación física nueva. Sólo podrían entrar como `STANDARD_V1` o `SYNTHETIC_ASSUMPTION` rotulados y con decisión explícita. **No incluirlos en este rediseño.** |
| Mostrar potencia "estimada" sin estado | Varios | Dino no debe dibujar un valor que su contrato marca UNDEFINED |
| Cloud-only con guardado implícito | WaveDyno | Dino es local con guardado explícito más estado "modificado"; conservarlo |

### 9.8 Decisiones que corresponden al dueño (no a Codex)

1. **¿Una confirmación para "Correr ambas" o para una serie de regímenes?** Hoy el contrato de la UI exige "a separate explicit in-app confirmation… for any EXPLORATORY run". Mientras no se decida: una confirmación por corrida.
2. **¿Se habilita una "serie de regímenes" (seudo-barrido) como cola de corridas independientes?** Con 26 s por ciclo y 600 s de techo, el costo y el resultado esperable (sin periodicidad) deben quedar explícitos.
3. **¿Se incorporan ayudas empíricas** (tuned-length, STA, time-area con bandas)? Hoy no; serían física o heurística nueva.
4. **Edición de lumbreras en grados** (inversión ° → mm). Es geometría pura (biela-manivela) y no física nueva, pero cambia la forma en que se ingresa la configuración.

---

## 10. Plan para Codex

### Reglas

- **No tocar:** solver, física, malla, `exploratory_workflow`, `engine_configuration`, `engine_project`, `engine_variants`, `exhaust_mesh_v1`, OpenSpec, `program-status.json`, evidence.
- Todo cambio va en `motorsim/desktop/` y tests.
- Conservar las aserciones semánticas de `tests/test_dino_desktop*.py`: fail-closed, sin interpolación, confirmación, VERIFIED no disponible, separación histórica.
- Los tests deben usar un `QSettings` aislado (D6).
- Cada fase con L0 y capturas de humo a 1360×900 y 980×680.

### Fase 0: correcciones medidas (bajo riesgo, alto impacto)

| Tarea | Criterio de aceptación |
|---|---|
| D1 superposición | Tras abrir otro proyecto con Archivo › Abrir, el combo lista exactamente sus variantes y la superpuesta se dibuja (test: `count == 1 + len(variants)`; captura muestra la línea punteada) |
| D2 resaltado | Con la variante +20 mm, `_changed_sections()` devuelve `{1}` (diffuser) y el perfil lo tiñe |
| D3 presupuesto acoplado | Al elegir un preset de N ciclos, el presupuesto pasa a `min(600, ceil(N × t_ciclo × 1,2))`, con `t_ciclo` de la última corrida con la misma cantidad de celdas o 30 s por defecto. Si no alcanza, aviso "el horizonte no entra en el presupuesto máximo" |
| D4 eje Y | Para trazas vs ángulo, `ymin` y `ymax` = rango de los datos ±5 %; marcas numéricas en Y; test con presión ≈1e5 ± 2e4 que verifica que la amplitud ocupa ≥60 % del alto |
| D5/D6 settings | La raíz por defecto nunca queda dentro de un repositorio git (aviso si se elige); fixture de test con `QSettings` en un directorio temporal |
| D7 nombres | El inspector y la barra muestran el mismo nombre de variante; el `display_name` técnico pasa al cajón |
| Arranque | El `.exe` abre siempre en el Build del último proyecto, o en Inicio si no hay; nunca en un Resultados vacío |

### Fase 1: Build centrado en el motor

| Tarea | Criterio |
|---|---|
| Tarjeta "Cilindro" con derivados (cilindrada, S/D, velocidad media del pistón al régimen de prueba) | 56 × 50 muestra 123,2 cm³; se actualiza al editar sin aplicar |
| Pestaña "Lumbreras": columnas derivadas °ATDC abre / cierra / duración + diagrama área vs ángulo | Valores = `event_angles`; para `effective_profile` se muestra "perfil efectivo" sin inventar apertura y cierre; el diagrama marca PMS, PMI y eventos |
| Pestaña "Escape": tabla única de tramos con ángulo y volumen derivados, continuidad por estación compartida, perfil con cotas y Δ vs baseline | Editar Ø sal del tramo i cambia Ø ent del i+1; el `_draft()` resultante es idéntico al flujo actual para las mismas cotas (test de ida y vuelta) |
| Insignias de completitud por pestaña (✓ / ● modificado / ✗ + motivo del preflight) | Una configuración inválida muestra ✗ en la pestaña que corresponde, con un mensaje humano |
| Decimales por magnitud | mm: 1–2; rpm: 0; Cd: 2; CR: 2 |

### Fase 2: shell "Banco de puesta a punto"

| Tarea | Criterio |
|---|---|
| Barra superior: proyecto, variante, **baseline**, modo, guardado, botón Evidencia | Elegir una baseline persiste por proyecto; el Build muestra "Cambios vs baseline" en mm |
| Reemplazar "Vistas" y la vista "Proyecto" por pestañas Build + panel de Resultados + barra de prueba | Escenario §5 ≤ 12 pasos y ≤ 2 cambios de foco principal, medido con un test que automatiza el flujo |
| Menú Variante (crear, duplicar, renombrar, borrar) reutilizando `DesktopContext` | Mismas protecciones que hoy |
| Cajón de Evidencia: hashes, provenance, auditoría, conservación, gates, artifact root, run ID, historial completo, diff crudo, solicitud de revisión | Nada de eso aparece fuera del cajón en el flujo habitual (test de texto visible) |
| 980×680: el panel de Resultados pasa a pestaña | Sin solapamientos (capturas) |
| Compatibilidad con los tests: `window.pages` como shim o tests migrados | Todas las aserciones semánticas se preservan |

### Fase 3: correr y ver como un solo flujo

| Tarea | Criterio |
|---|---|
| Barra de prueba con régimen, horizonte, estimación, progreso (ciclo/tiempo) y cancelación | Progreso visible durante la corrida; al terminar, Resultados se actualiza sin pasar por el historial |
| Emparejamiento automático con la baseline (misma configuración de la baseline y mismo régimen) | Si existe, se compara sin intervención; si no, se ofrece "Correr baseline" |
| Re-auditoría con progreso k/n y caché en memoria por sesión | La segunda apertura de la misma corrida en la sesión no re-audita; el indicador muestra el avance |
| Tarjeta de estado con gramática visual (marca, estado, motivo, acción) | Una corrida sin periodicidad muestra ◌ "sin potencia/par" con el motivo exacto del backend |

### Fase 4: gráficos de ondas y comparación

| Tarea | Criterio |
|---|---|
| Celdas y caras nombradas por tramo y posición x | El combo muestra "diffuser · x 80–280 mm" |
| Mapa x–θ discreto (`QImage`, bandas por celda, colorbar, eventos) para variante y baseline | Sin interpolación espacial ni temporal (test: el número de bandas = celdas) |
| Δ variante − baseline sólo en ángulos idénticos; si no hay coincidencia exacta, no hay Δ, con aviso | Test con ángulos no coincidentes |
| Curva vs RPM con puntos marcados (huecos y no aceptados) y estado vacío explicativo | Con las 5 corridas reales: estado vacío más acción, no un recuadro mudo |
| Modo Post a pantalla completa | Botón de maximizar y restaurar |

### Fase 5 (sólo con decisión del dueño)

- "Correr ambas" o serie de regímenes con una sola confirmación.
- Edición de lumbreras en grados.
- Ayudas empíricas rotuladas.
- Hoja de construcción (conos), si algún día se decide.

### Priorización

| Fase | Impacto | Complejidad | Riesgo |
|---|---|---|---|
| F0 | Alto | Baja | Bajo |
| F1 | Alto | Media | Bajo (sólo derivados de APIs existentes) |
| F2 | Muy alto | Media-alta | Medio (shell y tests) |
| F3 | Muy alto | Media | Medio |
| F4 | Alto | Media | Bajo |

---

## 11. Limitaciones

- No se usó ningún software comercial. Las afirmaciones comerciales salen de manuales, sitios, capturas y descripciones de videos, con su etiqueta.
- **NO VERIFICADO:**
  - el diálogo de RPM, ejecución y convergencia de EngMod2T;
  - la UI v8 de MOTA (sólo hay capturas v6);
  - la interfaz real de la app de WaveDyno (sólo docs);
  - el estado de la exportación CSV en WaveDyno;
  - el throttle y la carga parcial en WaveDyno;
  - el encendido como entrada en Dynomation.
- Las capturas de MOTA (v6) y Dynomation (DOS, 2014) son interfaces antiguas. Se usaron por sus convenciones de flujo, no por su estética.
- El recorrido de Dino fue por script, más una captura del `.exe`. No se vieron diálogos, tooltips ni una corrida en curso. El conteo de pasos de Dino es por recuento del flujo real; los de los comerciales son reconstrucciones.
- D8 no se diagnosticó.
- Los valores derivados de los wireframes (ángulos 9,1°, volúmenes) son ilustrativos.
- Nada de este informe constituye validación de Dino ni afirma capacidades físicas que Dino no tiene.
