# DINO_DESKTOP_UX_REDESIGN_PROPOSAL

Auditoría independiente de UX/UI de la aplicación de escritorio Dino 2T (`Dino2T.exe`, `motorsim/desktop/`).

- **Commit inspeccionado:** `f2b651757df676d1efed736af73db1bdb9875616`. El HEAD avanzó 2 commits sobre `7fb3b7a`. Los dos commits nuevos sólo tocan la cola de objetivos y no cambian `motorsim/desktop/`.
- **Alcance:** lectura completa de `motorsim/desktop/*.py` (≈1 000 líneas), `dino_desktop.py`, el empaquetado y las APIs de backend que la UI consume. Lectura parcial de la UI heredada (`window.py`, `ui.py`, `workspaces.py`). Se tomaron 15 capturas reales con la plataforma Qt nativa de Windows (`widget.grab()`, PySide6 6.10.1).
- **Sin modificaciones** de código, física, contratos ni archivos del repositorio. No se ejecutó ninguna simulación. Sí se re-auditaron 5 corridas EXPLORATORY ya existentes (lectura y replay de auditoría, 74 s) para ver la pantalla de resultados con datos reales.
- Capturas en `%TEMP%\dino_ux\*.png`.

---

## 1. Diagnóstico: problemas de UX más importantes

Ordenados por impacto en el uso real. La columna "Evidencia" distingue lo **[V] visto** en captura, lo **[C] deducido del código** y lo **[M] medido**.

| # | Problema | Evidencia | Impacto |
|---|---|---|---|
| 1 | **Comparar dos escapes es casi imposible desde la UI.** "Comparar ejecuciones EXPLORATORY…" abre `QFileDialog.getOpenFileNames` y pide elegir `result.json`. Cada corrida guarda el suyo en una carpeta propia (`<root>/exploratory-workflow-v1/<proyecto>/<run_id>/result.json`), y el diálogo nativo de Windows no permite seleccionar archivos de carpetas distintas. Sólo funciona pegando rutas completas a mano. | [C] `results_page.py:47`, estructura en `E:\Dino-artifacts` | Bloquea el caso de uso central (H) |
| 2 | **No se sabe qué variante se está editando.** La variante activa sólo se elige en "Proyecto" (3.ª pestaña). "Motor" y "Escape" editan la variante activa sin mostrarla. | [V] `1b_escape_variante.png`, [C] `context.py:16` | Ediciones aplicadas a la variante equivocada |
| 3 | **"Crear / actualizar variante de escape" siempre crea una variante nueva** ("Escape N") a partir de la que esté activa, nunca actualiza la existente. Hay además dos caminos que crean variantes: "Duplicar motor base" en Proyecto y este botón. Ninguno permite poner o cambiar el nombre, ni borrar. | [C] `exhaust_page.py:99-106`, `project_page.py:22-26` | Proliferación de variantes sin nombre y encadenadas |
| 4 | **Los resultados "por defecto" no son del proyecto.** Al abrir la app, Resultados carga automáticamente un reporte IMPL2 histórico desde una ruta absoluta fija (`E:\Dino-artifacts\…impl2-full-rpm-sweep-30-points.json`) y muestra curvas A_PRIME_MESH_0 / B_PRIME_MESH_0. El usuario las confunde con sus resultados. | [V] `4_Resultados.png`, [C] `services.py:16` | Riesgo semántico: evidencia histórica presentada como propia |
| 5 | **Una simulación de 1 ciclo nunca da potencia, par ni BMEP**, y la UI no lo anticipa. El valor por defecto es 1 ciclo. Las métricas de desempeño exigen "an accepted periodic cycle" y el detector de periodicidad exige una racha de 3 comparaciones (≥4 ciclos). Resultado: gráfico principal vacío ("Sin valores válidos para graficar"). | [V] `4b_resultados_exploratory.png`, [M] las 5 corridas tienen `BMEP/brake_power = UNDEFINED`, motivo "Performance requires an accepted periodic cycle." | El usuario no obtiene la respuesta que buscaba y no sabe por qué |
| 6 | **Resultados no entra en pantalla.** A 1360×900 el bloque de trazas queda recortado (el gráfico de presión mide ≈40 px) y los widgets se solapan. No hay scroll ni splitters. | [V] `4c_resultados_punto.png` | Las trazas de presión y onda, lo más útil del escape, son ilegibles |
| 7 | **Bug visual en el editor de escape:** hay 10 `QComboBox` para 5 filas. Los combos huérfanos se dibujan sobre la columna "Ø entrada" (1360 px) o "Provenance" (980 px). | [V] `1_Escape.png`, `m1_escape_error_min.png`, [M] `findChildren(QComboBox)=10` | Parece un campo editable más; confunde |
| 8 | **Continuidad de diámetros manual.** El backend exige que el Ø de salida de una sección sea igual al Ø de entrada de la siguiente. La tabla pide los dos por separado, así que cambiar un diámetro siempre produce primero un error "discontinuous". | [C] `engine_variants.py:93` | Error garantizado en la edición más común |
| 9 | **El motor a tamaño mínimo es inutilizable.** A 980×680 las tablas de lumbreras y pérdidas colapsan a 0 filas visibles y los campos de combustión se solapan. A 1360×900 las tablas muestran ≈1 fila. | [V] `m0_motor_min.png`, `0_Motor.png` | La distribución, central en un 2T, queda oculta |
| 10 | **Distribución sólo en mm, sin grados ni diagrama.** El preparador piensa en apertura y duración (°). El backend ya calcula ángulos (`TwoStrokePortSet.event_angles`, `area_at`), pero la UI no los muestra. | [C] `engine_page.py:41-44` | Hay que convertir de cabeza; los errores de lumbrera no se entienden |
| 11 | **Mensajes de error crudos.** Ej.: "ProjectError: inlet-window: Fuera del modelo: no existe un intervalo de cierre alrededor de PMI (d >= S)." No resalta ningún campo ni sugiere qué cambiar. | [M] texto real tras carrera = 1 mm | Bloqueos incomprensibles |
| 12 | **Enums y hashes como lenguaje de interfaz.** `EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED`, `VALIDATED_NO_SOLVER_STEPS`, `NOT_REPORTED`, rutas JSON `/native_configuration/ducts/4/mesh/faces/2`, hashes SHA-256 de 64 caracteres en primer plano. | [V] todas las capturas | Ruido; lo importante no se distingue de la trazabilidad |
| 13 | **Formato numérico inconsistente.** Los spinboxes usan coma y 5 decimales ("3000,00000 rpm", "56,00000"); las tablas usan punto ("80.0") y parsean con `float()`, así que escribir "80,5" en una tabla falla. | [V] `0_Motor.png`, `1_Escape.png`, [C] `exhaust_page.py:73` | Errores de tipeo frecuentes en es_UY |
| 14 | **Salida de simulación = log de texto + volcado JSON.** No hay barra de progreso, ni avance vs presupuesto, ni tarjeta de resultado, ni botón "ver resultados". | [C] `execution_page.py:155-161` | No se sabe si va bien ni qué hacer después |
| 15 | **Importar 5 corridas tarda 74 s** (re-auditoría de primarios) con sólo un texto "Verificando artifacts…", sin barra de progreso y sin cancelación. | [M] | Parece colgado |
| 16 | **Gráficos sin ejes legibles:** sin marcas ni valores en Y, X sólo como "RPM 1300 — 5000", sin leyenda vinculada al color, sin hover, zoom ni cursor. La "leyenda" de trazas es un párrafo de texto. | [V] `4_Resultados.png`, `4c…png` | No se pueden leer valores |
| 17 | **Perfil de escape distorsionado y sin cotas.** Las escalas X e Y son independientes, sin nombres de sección ni cotas, sin superposición de variantes ni edición directa. | [V] `1_Escape.png`, [C] `exhaust_page.py:22-25` | No sirve para "ver" el diseño ni comparar |
| 18 | **No hay pantalla de inicio, proyectos recientes ni nombre de proyecto editable.** "Nuevo" crea `dino-<nombre de la carpeta de trabajo>` desde Fixture A, sin preguntar. `project_id` y `display_name` no se pueden editar. | [C] `app.py:83` | No se entiende por dónde empezar |
| 19 | **Dos raíces de artifacts distintas.** Simulación usa `~\Dino-artifacts`; Resultados usa `E:\Dino-artifacts`. | [V] `3b…png` vs `4_Resultados.png` | Las corridas propias no aparecen donde se buscan |
| 20 | **Dos aplicaciones en el mismo paquete** (`MotorSim.exe` y `Dino2T.exe`), con estilos, navegación y alcance distintos. | [C] `packaging/MotorSim.spec`, [V] `legacy_motorsim.png` | Confusión sobre cuál usar |
| 21 | **Parámetros duplicados o sin efecto mezclados con los editables:** "Régimen de referencia" (Motor) vs "RPM" (Simulación) con rangos distintos (30 000 vs 10 000); AFR deshabilitado en primer plano; "Coordenada de carga del mapa MEP" sin contexto. | [V] `0_Motor.png` | Duda sobre qué controla la simulación |
| 22 | **Las variantes son copias completas.** Cambiar el motor base después de duplicar no se propaga, y la UI no lo advierte. | [C] `project_page.py:25` | Comparaciones donde difiere más que el escape, sin saberlo |

**Respuesta a las preguntas de evaluación:**

- *¿Por dónde empezar?* No se entiende. Abre en "Motor" con un motor sintético ya cargado, sin explicar de dónde sale.
- *¿Crear motor nuevo?* Sólo como copia de Fixture A, sin decirlo antes, y sin cilindrada visible (Fixture A tiene 123,2 cm³).
- *¿Qué parámetros ingresar?* Mezcla editables, metadatos y deshabilitados al mismo nivel.
- *¿Modificar el escape?* Posible, pero con error de continuidad garantizado y sin saber qué variante se toca.
- *¿Ejecutar?* Sí; es la pantalla más clara. Pero no anticipa que 1 ciclo no da desempeño.
- *¿Exploratorio vs verificado?* El texto está, pero es denso. Falta un indicador persistente de modo.
- *¿Por qué está bloqueado?* El preflight lo dice en una línea técnica; no indica el campo culpable.
- *¿Interpretar resultados?* Difícil: el gráfico queda vacío, las trazas recortadas y los estados en inglés técnico.
- *¿Comparar dos escapes?* Prácticamente inviable (ver #1).

## 2. Fortalezas que vale la pena conservar

1. **Semántica fail-closed y honesta:** validación completa al aplicar, preflight en vivo, "Preflight FAIL-CLOSED", huecos sin interpolación, separación EXPLORATORY/VERIFIED, `NOT_CLAIMED`. Es un activo diferencial; el rediseño debe hacerlo *más visible*, no esconderlo.
2. **`DesktopContext` como fuente única** con señal `changed` y estado `dirty`: buen núcleo de "documento". Se conserva y se amplía.
3. **Tareas en segundo plano cancelables** (`services.run_background`, `cancel_event`, checkpoint/resume, `waitForDone` al cerrar).
4. **Escrituras atómicas** (export, solicitud) y confirmación explícita previa a la ejecución, con presupuesto, memoria y celdas.
5. **`CurvePlot` preserva huecos** y permite seleccionar un punto. Base correcta para extender.
6. **Detalle por punto** (auditoría, hashes, hard gates): trazabilidad útil para el modo avanzado.
7. **Tema oscuro coherente** y atajos estándar (Ctrl+N/O/S).
8. **La UI heredada (`motorsim/ui.py`, `workspaces.py`) ya resolvió varias cosas:** navegación agrupada (`Navigation` con grupos), `Panel`, `Badge` con estados, `ValidationMessage`, `NumericUnit`, `PropertyTable`, `Columns`/`SimulationColumns` responsivos y `QScrollArea` por página. La captura `legacy_motorsim.png` muestra un resumen con "Preparación y estado" y "Ir a simulación →", que es exactamente el patrón que le falta a Dino 2T. **Reutilizarlos, no reinventarlos.**

## 3. Propuesta de estructura general

### 3.1 Evaluación de las 5 secciones sugeridas

La lista Proyectos / Motor / Escape / Simulación / Resultados describe bien *qué hay*, pero tratarla como 5 pestañas pares repite el problema actual: la **variante** queda como un detalle de una pestaña, cuando es el objeto central del trabajo (comparar escapes = comparar variantes).

**Recomendación: banco de trabajo centrado en variantes**, con el patrón habitual de CAE (árbol de modelo + área de trabajo + inspector):

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ Archivo  Editar  Variante  Simulación  Ver  Ayuda                                     │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ◧ Proyecto: Mi 125 · ● Variante activa: [Escape +20 mm ▾] · EXPLORATORIO · Guardado ✓│  ← barra de contexto fija
├───────────────┬───────────────────────────────────────────────────────┬──────────────┤
│ PROYECTO      │  [ Motor ][ Escape ][ Simular ][ Resultados ]          │ ESTADO       │
│ ▸ Inicio      │                                                       │ Variante     │
│ VARIANTES     │                                                       │  Escape+20mm │
│ ● Base        │            área de trabajo del modo elegido            │ Difiere del  │
│ ● Escape orig │                                                       │ base en:     │
│ ● Escape +20  │                                                       │  difusor L   │
│ + Nueva…      │                                                       │ Validez ✓    │
│ CORRIDAS      │                                                       │ Preflight ✓  │
│ ✓ orig·3000   │                                                       │ 13 celdas    │
│ ✓ +20·3000    │                                                       │ ─────────    │
│ ⟳ +20·4000 42%│                                                       │ Corrida act. │
│ COMPARACIONES │                                                       │ ▓▓▓▓░ 42 %   │
│ ⇄ orig vs +20 │                                                       │              │
└───────────────┴───────────────────────────────────────────────────────┴──────────────┘
```

- **Árbol izquierdo (Explorador del proyecto):** Inicio · Variantes · Corridas · Comparaciones · Evidencia histórica (colapsada). Seleccionar una variante la activa. Seleccionar una corrida abre Resultados. Seleccionar una comparación abre Comparar.
- **Pestañas de modo** sobre la variante activa: Motor · Escape · Simular · Resultados. "Comparar" es un modo propio, que se abre desde el árbol o con el botón "Comparar…".
- **Inspector derecho (colapsable):** estado de la variante (válida, pendiente de aplicar, difiere del base en…), preflight, corrida activa con progreso. Siempre visible; responde "¿por qué está bloqueado?".
- **Barra de contexto fija:** proyecto, variante activa (selector), modo EXPLORATORIO, guardado/modificado. Resuelve #2.

Esta estructura **absorbe** la pantalla "Proyecto" actual: la lista de variantes pasa al árbol y el diff pasa a Comparar e inspector. Mantiene las 5 funciones pedidas, pero ordenadas por el flujo real.

### 3.2 Uso habitual vs avanzado

Regla única en toda la app: **lo habitual a la vista; la trazabilidad a un clic.**

- Habitual: cotas, unidades, estado en palabras ("Periodicidad no identificada"), métricas, gráficos.
- Avanzado (sección plegable "Detalles científicos" o pestaña "Trazabilidad"): hashes, provenance, enums originales, hard gates, conservación, malla 1/2/4, run ID, artifact root, RSS, fuel snapshot.
- `Ver → Mostrar detalles científicos` (persistido en QSettings) expande todas esas secciones de una vez para el usuario experto.

## 4. Diseño de las pantallas principales

### 4.1 Inicio

```
┌ Inicio ─────────────────────────────────────────────────────────────────────┐
│  Dino 2T · simulador 0D/1D de motores de dos tiempos                         │
│                                                                              │
│  [ + Nuevo proyecto… ]  [ Abrir… ]  [ Abrir ejemplo: comparación de escapes ]│
│                                                                              │
│  Recientes                                   Cómo leer los resultados        │
│  ▸ Mi 125 · 3 variantes · 2 corridas · hoy   ■ EXPLORATORIO: provisional,    │
│  ▸ dino-exhaust-comparison-starter · ayer      sin claim de validación.      │
│                                              □ VERIFICADO: no disponible      │
│  Este proyecto está listo para:               todavía (requiere contrato,    │
│  ✓ Motor válido  ✓ 2 variantes  ○ Sin corridas  preregistro y autorización). │
│  [ Ir a Simular → ]                          ⚠ Plantilla sintética: no es    │
│                                                 un motor medido.             │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Asistente "Nuevo proyecto"** (QWizard, 2 pasos):

1. Nombre del proyecto (→ `project_id` saneado) y plantilla. Única opción hoy: **"Fixture A — sintético (56 × 50 mm, 123 cm³)"**, rotulada como tal.
2. Geometría principal: Ø, carrera, biela, con **cilindrada calculada en vivo** y un ayudante opcional "cilindrada objetivo → carrera". Se aplica con el mismo `EnginePage.apply` actual.

### 4.2 Motor

```
┌ Motor · variante: Base ─────────────────────────────── [Descartar] [Aplicar ✓] ┐
│ ┌ Geometría básica ──────────────┐ ┌ Derivados (solo lectura) ──────────────┐ │
│ │ Diámetro        54,00  mm      │ │ Cilindrada           124,8 cm³         │ │
│ │ Carrera         54,50  mm      │ │ Relación S/D         1,01              │ │
│ │ Biela          100,00  mm      │ │ Vel. media pistón    5,45 m/s @3000    │ │
│ │ Vol. cárter PMI 80,0   cm³     │ │ Relación cárter      ...               │ │
│ │ Compresión geom. 8,00  :1      │ └────────────────────────────────────────┘ │
│ └────────────────────────────────┘                                            │
│ ┌ Distribución ──────────────────────────────────────────────────────────────┐ │
│ │ Lumbrera     Rol      Borde sup.  Altura  Ancho  Cd    Abre   Cierra  Dur. │ │
│ │ exhaust      escape   28,0 mm     22,0    40,0  0,80  98°    262°   164°  │ │
│ │ transfer…    transf.  ...                              ...                 │ │
│ │ ┌ Diagrama de área efectiva vs ángulo (0–360°) ────────────────────────────┐│ │
│ │ │  escape ▁▂▅█████▅▂▁ ; transfer ▁▃██▃▁ ; PMI/PMS marcados                 ││ │
│ │ └──────────────────────────────────────────────────────────────────────────┘│ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│ ▸ Combustión (supuesto sintético)    ▸ Pérdidas mecánicas    ▸ Detalles científ.│
└─────────────────────────────────────────────────────────────────────────────────┘
```

- Página con `QScrollArea` y paneles `Panel` (de `ui.py`). Las tablas tienen alto mínimo igual al número real de filas (resuelve #9).
- **Grados de distribución derivados**, de sólo lectura, con `TwoStrokePortSet.event_angles()`. **Diagrama** de área vs ángulo con `area_at()`. Ambas son APIs existentes; no es física nueva. Se recalculan en vivo sobre el borrador, sin aplicar.
- Spinboxes con decimales por magnitud (mm: 2; rpm: 0; Cd: 3; razón: 2), unidad como sufijo y locale consistente (#13).
- "Régimen de referencia" se mueve a Simular como valor inicial de RPM (#21). AFR y "coordenada de carga" pasan a "Detalles científicos", con su nota actual.
- Barra de cambios pendientes ("3 cambios sin aplicar"); al aplicar, cada error se ubica en su campo (ver 4.8).

### 4.3 Diseñador de escape

```
┌ Escape · variante: Escape +20 mm ──── diferencias vs Escape original: difusor L +20 mm ┐
│ [Superponer: Escape original ▾]  [◉ Escala real ○ Radial ×3]   [Guardar en esta variante] │
│                                                                [Guardar como nueva…]     │
│ ┌ Perfil ──────────────────────────────────────────────────────────────────────────────┐ │
│ │        header │  diffuser   │   belly   │   baffle    │ stinger                      │ │
│ │  Ø20 ════════╲             ┌───────────┐             ╱════════ Ø16                   │ │
│ │               ╲───────────╱  Ø52       ╲───────────╱                                 │ │
│ │  (contorno fantasma punteado = Escape original)                                      │ │
│ │  0      80          280          380           550        670 mm                     │ │
│ └──────────────────────────────────────────────────────────────────────────────────────┘ │
│ Estaciones (Ø)                      Tramos                                               │
│  #  Posición   Ø (mm)               Tramo     Tipo         Longitud (mm)  Conicidad       │
│  0  0          20,0                 header    header        80,0           0°             │
│  1  80         20,0                 diffuser  diffuser     200,0  (+20)    4,9°           │
│  2  280        52,0                 belly     belly        100,0           0°             │
│  3  380        52,0                 baffle    baffle_cone  170,0          −6,0°           │
│  4  550        16,0                 stinger   stinger      120,0           0°             │
│  5  670        16,0                                                                       │
│ Total 670 mm · Ø máx 52 mm · Volumen 0,59 L          ▸ Malla numérica (1/2/4 por tramo)  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Edición por estaciones:** N+1 diámetros y N longitudes. La continuidad queda garantizada por construcción (#8). En la UI se convierte al formato `sections` actual de `replace_escape_sections`, sin cambiar el backend.
- **Restricciones reales del backend, explícitas:** número de tramos fijo (`state remapping is unsupported`); tipos limitados a `header/diffuser/belly/baffle_cone/stinger/linear`; perfil axisimétrico cónico-lineal. **No ofrecer** agregar ni quitar tramos, ni formas curvas.
- **Perfil a escala real** por defecto, con opción de exagerar lo radial (rotulada). Cotas, nombres de tramo, conicidad y volumen calculados en la UI. **Superposición** de otra variante. Arrastrar estaciones (Ø vertical, posición horizontal) como mejora P3.
- **Dos acciones claras:** "Guardar en esta variante" (reemplaza la variante activa) y "Guardar como nueva variante…" (pide nombre; parte de la activa) (#3).
- Malla 1/2/4 en "Malla numérica", plegada, con su aviso. Resúmenes de área, volumen y caras en m² y m³ sólo en "Detalles científicos".
- Bug #7 corregido.

### 4.4 Simular

```
┌ Simular · variante: Escape +20 mm ─────────────────────────────── EXPLORATORIO ┐
│ ┌ Condición ────────────────────┐  ┌ Qué vas a obtener ─────────────────────────┐ │
│ │ Régimen        3000 rpm       │  │ ○ Prueba rápida  1 ciclo                    │ │
│ │ Ciclos máx.    20             │  │   → presiones y ondas; SIN potencia/BMEP    │ │
│ │ Presupuesto    600 s          │  │ ◉ Buscar ciclo periódico  hasta 20 ciclos   │ │
│ │ ▸ Avanzado (memoria, root, ID)│  │   → potencia/BMEP sólo si se identifica     │ │
│ └───────────────────────────────┘  │     periodicidad (≥4 ciclos)                │ │
│ Preflight ✓ 13 celdas · combustible sintético · estimado ≈ 9 min (último: 26 s/c)│ │
│                                       [ Simular… ]                              │ │
│ ┌ Corrida en curso ──────────────────────────────────────────────────────────────┐ │
│ │ Ciclo 7/20  ▓▓▓▓▓▓▓░░░░░░░  · 183 s / 600 s ▓▓▓▓░░░░ · RSS 412/1024 MiB         │ │
│ │ Periodicidad: evaluando (racha 1/3)                          [ Cancelar ]       │ │
│ └────────────────────────────────────────────────────────────────────────────────┘ │
│ Historial de corridas de este proyecto                                            │
│  ✓ Escape original · 3000 · 1 ciclo · periodicidad no identificada · [Ver] [⇄]    │
│  ⏸ Escape +20 · 4000 · 7/20 · cancelada (checkpoint) · [Reanudar]                 │
└───────────────────────────────────────────────────────────────────────────────────┘
```

- **Presets de horizonte**, con la consecuencia en palabras (#5). La estimación usa `elapsed_seconds/cycles_completed` de corridas previas y se rotula "estimación".
- **Barra de progreso** por ciclo, por tiempo vs presupuesto y por RSS, con los datos que ya emite `progress` (#14). La racha de periodicidad sólo se muestra si el callback la expone hoy; si no, queda fuera (no inventar).
- Al terminar, **tarjeta de resultado** en lenguaje claro y botones "Ver resultados" / "Comparar con…", que abren sin diálogo de archivos.
- **Historial:** escaneo de sólo lectura de `<root>/exploratory-workflow-v1/<project_id>/*/run.json|result.json`. Reanudar desde la fila; el Run ID queda en Avanzado.
- La confirmación explícita de ejecución se mantiene, con el mismo texto resumido y mejor formato.
- "VERIFIED": un botón deshabilitado con candado y tooltip "requiere contrato, preregistro y autorización coincidentes", en vez de prosa permanente.
- Artifact root único en `Preferencias` (QSettings), compartido con Resultados (#19).

### 4.5 Resultados (una corrida)

```
┌ Resultados · Escape +20 mm · 3000 rpm · ciclo 1 ───────────────────────────────────┐
│ ⚠ EXPLORATORIO · Periodicidad no identificada · Auditoría ✓ · Sin validación exper. │
│   Potencia, par y BMEP no disponibles: requieren un ciclo periódico aceptado.        │
│   [Simular más ciclos con esta condición →]                                         │
│ ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐                 │
│ │p máx     │∠ p máx   │Aire atrap│Combust.  │AFR       │Potencia  │                 │
│ │21,5 bar  │360,0°    │47,0 mg   │6,38 mg/s │62,7      │  —  ⓘ    │                 │
│ └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘                 │
│ [ Presión cilindro ][ Ondas en escape ][ Flujo en escape ][ Tabla de métricas ][ Trazab.]│
│ ┌──────────────────────────────────────────────────────────────────────────────────┐│
│ │ bar                                                                               ││
│ │ 20 ┤            ╭╮                                                                ││
│ │ 10 ┤          ╭─╯╰─╮               cursor: 372,5° · 18,3 bar                       ││
│ │  0 ┼──────────╯────╰───────────────────────────────────────────────────            ││
│ │    0      90     180     270     360    (° cigüeñal; PMS/PMI y apert./cierre      ││
│ │                                         de lumbreras marcados)                    ││
│ └──────────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────┘
```

- **Banner de estado** traducido (ver tabla de presentación, §8.3) con la causa y la acción siguiente.
- **Tarjetas KPI** sólo con métricas `DEFINED`. Las `UNDEFINED` muestran "—" y un ⓘ con el `reason` real del backend.
- **"Ondas en escape":** selector de celda rotulado con tramo y posición ("celda 2 · belly · x 0,26–0,36 m"), y además un **diagrama x–θ** (mapa de color de presión por celda vs ángulo). Los datos ya existen: todas las celdas comparten los ángulos de la traza. Es la visualización clásica para afinar escapes 2T. Se dibuja sólo con valores muestreados, sin interpolar: celdas como bandas discretas.
- "Tabla de métricas": todas las `cycle_metrics` con estado, unidad y motivo.
- "Trazabilidad": el actual `details` (hashes, hard gates, conservación).
- Uso de `QSplitter` o pestañas: nada se recorta (#6).
- Reportes IMPL2 históricos: **fuera** de esta pantalla. Pasan a "Evidencia histórica" en el árbol, con banner propio, y **no se cargan al iniciar** (#4).

### 4.6 Comparar

```
┌ Comparar ─────────────────────────────────────────────────────────────────────────┐
│ A: [Escape original · 3000 rpm · c1 ▾]  B: [Escape +20 mm · 3000 rpm · c1 ▾]  [⇆] │
│ Diferencias de configuración: difusor longitud 180 → 200 mm (único cambio) ✓       │
│ ⚠ Mismo régimen ✓ · mismo nº de ciclo ✓ · ambas EXPLORATORIO · sin periodicidad    │
│ ┌ Geometría superpuesta ───────────────┐ ┌ Métricas ───────────────────────────────┐│
│ │ A ── / B ┄┄                          │ │ Métrica     A        B        Δ    estado ││
│ └──────────────────────────────────────┘ │ p máx       21,48    21,52   +0,2%  def. ││
│ ┌ Presión escape · celda 2 (belly) ────────────────────────────────────────────────┐│
│ │ A ── B ┄┄  · [Mostrar B−A] (sólo en ángulos comunes exactos)                      ││
│ └───────────────────────────────────────────────────────────────────────────────────┘│
│ Barrido (si hay varias rpm): curvas por variante con huecos donde no hay valor.    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

- Corridas elegidas **del historial**, nunca del explorador de archivos (#1). "Importar corrida externa…" sólo como acción secundaria, con una carpeta por vez.
- Diff de configuración **en términos de ingeniería**: mapear rutas conocidas a nombres (tramo, cota, unidad). Las rutas JSON crudas van a "Detalles". El aviso de que difieren más que el escape resuelve #22.
- Advertencias de comparabilidad: régimen, ciclo, periodicidad y modo.
- Diferencia B−A sólo en ángulos idénticos, coherente con la regla actual "ángulos comunes exactos · sin interpolación".

### 4.7 Dirección visual

| Aspecto | Propuesta |
|---|---|
| Tema | Oscuro por defecto (ya existe y es coherente) **más un tema claro** para informes, proyector y luz diurna. Una sola hoja QSS parametrizada por tokens (`theme.py`). |
| Paleta | Neutros pizarra, un único acento azul (#2b9bd7 ≈ actual) para acción primaria y selección. Colores de estado **sólo semánticos**: ámbar = exploratorio/provisional, verde = auditoría/validez OK, rojo = error/bloqueo, gris = no evaluado/no disponible. Nunca color solo: siempre ícono + texto. |
| Tipografía | Segoe UI 10 pt cuerpo, 9 pt secundario, 13–15 pt títulos de página (hoy 22 pt: demasiado). Números de tablas, hashes e IDs en monoespaciada (Cascadia Mono/Consolas) con cifras tabulares, alineados a la derecha. |
| Espaciado | Grilla de 8 px; márgenes de página 16 px; paneles con cabecera (patrón `Panel` heredado). |
| Formularios | Etiqueta – valor – unidad en 3 columnas alineadas; decimales por magnitud; borde rojo e ícono en el campo inválido con mensaje debajo (`ValidationMessage`); los campos sin efecto en el solver no se muestran en modo habitual. |
| Tablas | `QTableView` + modelo, con delegados `QDoubleSpinBox` (rango, unidad, locale). Celdas de sólo lectura con fondo atenuado. Provenance como ícono con tooltip, no como columna. Alto mínimo = filas reales. |
| Gráficos | Ejes con marcas y valores, unidad en el título del eje, leyenda vinculada al color, cursor con lectura, zoom/pan con rueda o arrastre (reset con doble clic), marcadores de PMS/PMI y de apertura/cierre de lumbreras, export PNG y SVG. Se mantienen los huecos. Paleta de series apta para daltonismo y estilos de línea distintos para A/B. |
| Errores | Plantilla de 3 líneas: **qué pasó** (humano) · **dónde** (campo resaltado) · **cómo corregir**; "Detalle técnico" plegable con el mensaje original. |
| Progreso | Barras determinadas (ciclos, tiempo, memoria), indicador en el árbol y en la barra de estado, y notificación al terminar si la ventana no tiene foco. Importaciones largas: barra con "corrida k de n" y cancelación. |
| Densidad | Modo habitual "cómodo"; `Ver → Detalles científicos` añade la capa experta. |

### 4.8 Mensajes de error: ejemplos de reescritura

| Mensaje actual | Propuesto |
|---|---|
| `ProjectError: inlet-window: Fuera del modelo: no existe un intervalo de cierre alrededor de PMI (d >= S).` | **La lumbrera de admisión queda fuera de la carrera.** Su borde (64 mm) supera la carrera (1 mm). → Aumentá la carrera o bajá el borde de la lumbrera. *(Detalle técnico ▸)* |
| `ValueError: escape section 1 is discontinuous` | (Desaparece con la edición por estaciones.) |
| `Fila 2: longitudes y diámetros deben ser números finitos` | **Longitud del difusor inválida.** Ingresá un número mayor que 0 (p. ej. 180,0). (Campo resaltado.) |
| `Preflight FAIL-CLOSED: …` | **No se puede simular todavía:** \<causa traducida\>. → \<acción\>. *(Detalle ▸)* |

Implementación: `desktop/messages.py` con un mapeo **por patrones de mensajes conocidos** y respaldo al texto original. No se cambia ningún mensaje del backend.

## 5. Flujo completo de utilización (A–H)

| Paso | Hoy (fricción) | Propuesto |
|---|---|---|
| **A. Crear motor 125 cc** | Archivo › Nuevo crea `dino-<carpeta>` desde Fixture A sin preguntar; no se ve la cilindrada (123,2 cm³); no se puede renombrar el proyecto. | Inicio › Nuevo proyecto… › nombre "Mi 125" › plantilla Fixture A (sintética, rotulada) › Ø 54 × carrera 54,5 → **124,8 cm³** en vivo › Crear. |
| **B. Geometría y distribución** | Spinboxes de 5 decimales; tabla de lumbreras de 1 fila visible, sólo en mm; error "d >= S" sin guía si la carrera choca con las lumbreras. | Motor: geometría con derivados; distribución con grados abrir/cerrar/duración y diagrama, recalculados en vivo; error ubicado en la lumbrera con sugerencia. Aplicar. |
| **C. Escape original** | El escape del base existe pero no está nombrado; para "fijarlo" como variante hay que usar "Crear / actualizar", que genera "Escape N" sin nombre elegido. | Árbol › Variantes › "Base" › Duplicar como… "Escape original". Escape: revisar cotas a escala. |
| **D. Duplicar y modificar** | Dos caminos ("Duplicar motor base" en Proyecto / botón en Escape) con resultados distintos; no se ve qué variante se edita; cambiar un Ø da error de continuidad; el botón dice "actualizar" pero crea otra. | Clic derecho en "Escape original" › Duplicar como… "Escape +20 mm" (queda activa en la barra de contexto) › en Escape cambiar la longitud del difusor 180 → 200 › Guardar en esta variante. Superponer "Escape original" para verlo. |
| **E. Condición** | RPM en Simulación y otro "régimen de referencia" en Motor; horizonte por defecto 1 ciclo sin advertencia. | Simular: 3000 rpm (inicial = régimen de referencia), preset "Buscar ciclo periódico", estimación de duración. **Hoy la condición es: régimen y horizonte de ciclos, a plena carga del modelo; no hay mariposa ni AFR operativos** (se dice así). |
| **F. Ejecutar exploratoria** | Diálogo de confirmación correcto; luego log de texto y JSON crudo. | Confirmación resumida → progreso visual → tarjeta de resultado → "Ver resultados". Repetir para la otra variante (selector en la barra de contexto). |
| **G. Consultar resultados** | Hay que ir a Resultados, abrir un diálogo, navegar hasta `result.json`, esperar ~15 s por corrida sin progreso; gráfico vacío; trazas recortadas; la pantalla abre mostrando curvas IMPL2 ajenas. | Clic en la corrida (árbol o historial) → banner de estado + KPI + presión + ondas x–θ. Re-auditoría con progreso, en caché **en memoria** durante la sesión. |
| **H. Comparar ambas** | Prácticamente imposible (archivos en carpetas distintas). | Seleccionar ambas corridas › Comparar (o botón ⇄ en el historial) → diff de configuración "difusor +20 mm", geometrías superpuestas, trazas A/B y Δ en ángulos comunes, métricas lado a lado con estados. |

## 6. Mejoras de gráficos y del diseñador de escape (resumen)

**Gráficos**

1. Extender `CurvePlot` a un `PlotWidget` propio: ejes con marcas "agradables" (1-2-5), leyenda, cursor de lectura, zoom/pan, marcadores verticales (PMS, PMI, eventos de lumbrera), export PNG/SVG (`QSvgGenerator` está en PySide6) y estilos de línea por serie. Se conserva la semántica de huecos.
2. `WaveMap`: mapa de calor x–θ con `QImage` para presión por celda; escala de color secuencial con barra de valores; celdas como bandas (sin interpolación espacial).
3. Pequeños múltiplos para barridos de RPM cuando existan varios puntos.
4. **No agregar dependencias** (pyqtgraph arrastraría numpy, que no está en `requirements.txt`, con impacto en empaquetado y licencias). QtCharts está disponible en PySide6, pero no cubre mapas de calor ni el control de huecos; el widget propio es más simple y coherente.

**Diseñador de escape**

1. Edición por estaciones (continuidad por construcción).
2. Perfil a escala real, cotas, nombres, conicidad, volumen total y por tramo (cálculo geométrico de UI).
3. Superposición de otra variante y resaltado de los tramos que cambian.
4. Selección sincronizada tabla ↔ perfil (clic en un tramo lo selecciona en la tabla).
5. P3: arrastrar estaciones sobre el perfil (con snap a 0,5 mm), deshacer/rehacer (`QUndoStack`).
6. Malla 1/2/4 como opción avanzada, visualizada como subdivisiones sólo cuando se despliega.
7. Restricciones del solver comunicadas, no simuladas: número fijo de tramos y tipos fijos.

## 7. Priorización de cambios

| Prioridad | Cambio | Esfuerzo | Ganancia |
|---|---|---|---|
| **P0** (bugs y riesgos semánticos) | Combos duplicados (#7) · no autocargar el reporte IMPL2 ni usar rutas absolutas (#4) · root de artifacts único (#19) · botón de escape que dice "actualizar" (#3) | S | Alta |
| **P0** | Barra de contexto con **variante activa** visible y seleccionable en todas las páginas (#2) | S | Muy alta |
| **P1** | Historial de corridas + "Ver" / "Comparar" sin diálogo de archivos (#1) | M | Muy alta |
| **P1** | Resultados sin recortes (scroll/splitter/pestañas), banner de estado, KPI con motivo de `UNDEFINED` (#5, #6) | M | Muy alta |
| **P1** | Presets de horizonte con consecuencia explícita y barra de progreso (#5, #14, #15) | S–M | Alta |
| **P1** | Escape por estaciones (#8) | M | Alta |
| **P2** | Nueva navegación (árbol + modos + inspector) y pantalla Inicio, asistente de proyecto, nombre editable (#18) | L | Alta |
| **P2** | Motor: scroll, derivados, grados y diagrama de distribución, decimales/locale (#9, #10, #13, #21) | M | Alta |
| **P2** | `PlotWidget` con ejes, leyenda y cursor; vista de ondas x–θ (#16) | M | Alta |
| **P2** | Mensajes traducidos y capa de presentación de enums (#11, #12) | M | Media-alta |
| **P3** | Comparar completo (diff en términos de ingeniería, Δ) (#22) | M | Alta |
| **P3** | Perfil interactivo, superposición, deshacer/rehacer; tema claro; preferencias; atajos | M–L | Media |
| **P3** | Unificar o retirar `MotorSim.exe` del paquete orientado a 2T (#20) | S (decisión) | Media |

## 8. Plan de implementación para Codex

### 8.0 Reglas para el implementador

- **No tocar backend ni contratos:** `engine_configuration`, `engine_project`, `engine_variants`, `exhaust_mesh_v1`, `exploratory_workflow`, `engine_results` y el resto de `motorsim/` fuera de `desktop/`. Sólo se *consumen* sus APIs públicas.
- **Conservar las garantías** que hoy prueban `tests/test_dino_desktop.py`: validación completa al aplicar, fail-closed, huecos sin interpolación, confirmación explícita antes de ejecutar, VERIFIED no disponible, separación histórico/exploratorio y cancelación al cerrar. Los tests acceden a `window.pages[i]` y a atributos (`controls`, `ports`, `losses`, `apply`, `table`, `plot`, `details`…). Al reestructurar: o mantener un shim (`window.pages` y nombres de atributos) o actualizar los tests **preservando cada aserción semántica**. Nunca relajarlas.
- Cada fase con tests L0 y **capturas de humo** (script `grab()` a 980×680, 1360×900 y 1920×1080, con fixture de proyecto ejemplo) para detectar solapamientos.
- Todo el texto nuevo de estado debe derivar de campos del backend. Nada de inventar estados ni presentar lo sintético como validado.

### 8.1 Componentes: conservar / reorganizar / reemplazar

| Componente actual | Decisión |
|---|---|
| `DesktopContext` | **Conservar** y ampliar: `active_variant` con señal propia `variant_changed`; métodos `duplicate_variant(src,name)`, `rename_variant`, `delete_variant`, `set_project_name`, todos con `validate_project`. La UI deja de mutar `project['variants']` directamente (hoy lo hacen `project_page` y `exhaust_page`). |
| `services.run_background` / `BackgroundTask` | **Conservar**; añadir una señal de progreso genérica para importaciones (k/n). |
| `DinoDesktopWindow` (shell) | **Reemplazar** el `QListWidget` de navegación por `ProjectExplorer` (`QTreeView` + modelo) + `QTabBar` de modos + `InspectorPanel` + `ContextBar`. Conservar menús, acciones, guardado, `closeEvent` y QSettings. |
| `EnginePage` | **Reorganizar**: `QScrollArea` + `Panel`s; mantener `apply()` y su lógica íntegra; añadir `DerivedGeometryPanel` y `PortTimingPanel` (usa `TwoStrokePortSet.event_angles/area_at`). |
| `ExhaustPage` / `ExhaustProfile` | **Reemplazar la tabla** por `StationTable` + `SegmentTable` (modelo único que produce `sections`); **reescribir** `ExhaustProfile` (escala real, cotas, superposición). Conservar `_draft()` y la ruta `refine_exhaust_configuration`. |
| `ProjectPage` | **Retirar** como página; repartir en `ProjectExplorer` (variantes), Inicio (info del proyecto) y Comparar (diff). |
| `ExecutionPage` | **Reorganizar**: conservar `_preflight`, `start_run`, `cancel_run`, confirmación y `save_request`; añadir presets, `RunProgressPanel`, `RunResultCard` y `RunHistoryView`. |
| `ResultsPage` | **Dividir** en `RunResultsPage` (una corrida) y `ComparePage`; mover IMPL2 a `HistoricalEvidencePage`. Conservar `show_point` como pestaña "Trazabilidad" y `export_csv`. |
| `CurvePlot` | **Extender** a `PlotWidget` (misma interfaz `set_series`, `pointSelected`) para no romper llamadas; añadir `WaveMap`. |
| `ui.py` heredado (`Panel`, `Badge`, `ValidationMessage`, `NumericUnit`, `PropertyTable`, `Columns`) | **Reutilizar**, moviéndolo o importándolo desde `desktop/widgets/`. `workspaces.Navigation` sirve de referencia para el árbol agrupado. |
| QSS embebido en `app.py` | **Reemplazar** por `desktop/theme.py` (tokens + oscuro/claro). |

### 8.2 Archivos nuevos propuestos (todos en `motorsim/desktop/`)

```
theme.py              tokens de color/tipografía, QSS oscuro y claro
presentation.py       enums del backend → (texto ES, severidad, ícono, explicación); formateo numérico por magnitud
messages.py           traducción de errores conocidos → (qué, dónde=campo, cómo); respaldo al original
run_history.py        escaneo de sólo lectura de <root>/exploratory-workflow-v1/<project_id>/*; sin re-auditar hasta abrir
widgets/context_bar.py    proyecto · variante activa (QComboBox) · modo · guardado
widgets/explorer.py       QTreeView del proyecto (variantes, corridas, comparaciones, evidencia histórica)
widgets/inspector.py      validez, diff vs base, preflight, corrida activa
widgets/plot.py           PlotWidget (evolución de CurvePlot) + WaveMap
widgets/exhaust_editor.py StationTable, SegmentTable, ExhaustProfile v2
widgets/numeric.py        delegados QDoubleSpinBox con locale/unidad/decimales
pages/home.py · pages/engine.py · pages/exhaust.py · pages/simulate.py · pages/run_results.py · pages/compare.py · pages/historical.py
```

### 8.3 Tabla de presentación (ejemplo de `presentation.py`)

| Valor backend | Texto | Severidad |
|---|---|---|
| `EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED` | Exploratoria completa · periodicidad no identificada | ámbar |
| `EXPLORATORY_COMPLETE_PERIODICITY_OBSERVED` | Exploratoria completa · periodicidad observada (no es aprobación científica) | ámbar |
| `NOT_EVALUATED` | No evaluado | gris |
| `PERIOD_1` | Periodicidad de 1 ciclo observada | ámbar |
| `NUMERICAL_INVALID` | Numéricamente inválido | rojo |
| `VALIDATED_NO_SOLVER_STEPS` | Configuración válida (sin ejecutar el solver) | verde |
| `SYNTHETIC_UNVALIDATED` | Datos sintéticos · sin validación experimental | ámbar |
| `NOT_CLAIMED` | Sin claim científico | gris |
| `UNDEFINED` + reason | — (ⓘ reason) | gris |

Los valores originales siguen visibles en "Detalles científicos" y en el tooltip.

### 8.4 Fases (cada una se puede commitear por separado)

1. **Fase 0. Correcciones (P0), sin cambiar la estructura.**
   - `exhaust_page.refresh`: `removeCellWidget` antes de recrear, o delegado combo.
   - `ResultsPage`: no autocargar `DEFAULT_REPORT`; quitar el default `E:\`.
   - `artifact_root` desde QSettings, compartido.
   - Escape: dos botones (guardar en la actual / como nueva con nombre).
   - `QScrollArea` en cada página y alto mínimo de tablas.
   - `ContextBar` con selector de variante en la ventana actual.
   - Tests de regresión para combos (n = filas), sin autoload y variante visible.
2. **Fase 1. Simulación y resultados utilizables (P1).**
   - `run_history.py`, `RunHistoryView`, "Ver" / "Comparar" desde el historial.
   - Presets de horizonte y `RunProgressPanel`.
   - `RunResultCard`.
   - Resultados con `QSplitter` y pestañas, banner, KPI, `presentation.py`.
   - Progreso k/n en la re-auditoría y caché en memoria por `result_sha256` durante la sesión.
3. **Fase 2. Escape por estaciones (P1).** `exhaust_editor.py`, perfil a escala con cotas y superposición. Tests: la ida y vuelta estaciones ↔ `sections` es idéntica a la tabla actual en el fixture; la continuidad siempre se cumple.
4. **Fase 3. Nueva navegación (P2).** `explorer.py`, `inspector.py`, `home.py`, asistente de proyecto, `theme.py`. `ProjectPage` sale. Shim `window.pages` o tests actualizados.
5. **Fase 4. Motor y gráficos (P2).** Derivados, distribución en grados y diagrama, delegados numéricos, `PlotWidget` con ejes, leyenda y cursor, `WaveMap`, `messages.py`.
6. **Fase 5. Comparar y pulido (P3).** `ComparePage` con diff de ingeniería y Δ, `historical.py`, tema claro, `QUndoStack`, arrastre en el perfil, preferencias, atajos (`Ctrl+1..5` modos, `F5` simular, `Esc` cancelar con confirmación).

### 8.5 Decisiones que no corresponden a Codex (consultar al dueño)

- **Cola de varias corridas con una sola confirmación** (p. ej. 2 variantes × 2 rpm). El texto actual de `save_request` exige "a separate explicit in-app confirmation … for any EXPLORATORY run". Agruparlas cambia esa política. Hasta decidirlo: una confirmación por corrida.
- **Caché persistente de importaciones auditadas.** Evitaría los ~15 s por corrida, pero cambia qué se considera "re-auditado". Hasta decidirlo: caché sólo en memoria.
- **Propagar cambios del base a variantes.** Hoy las variantes son instantáneas completas. Ofrecer propagación es una política de modelo. Hasta decidirlo: sólo advertir las diferencias.
- **Futuro de `MotorSim.exe`** dentro del mismo paquete.

## 9. Limitaciones y supuestos que requieren verificación visual

- **Qué se vio:** 15 capturas generadas con un script que crea `DinoDesktopWindow`, carga `examples/projects/dino-2t-exhaust-comparison.dino2t.json` y cambia de página por código, en la plataforma Qt nativa de Windows. **No es un recorrido manual:** no se verificaron hover, tooltips, foco de teclado, menús desplegados ni la experiencia con mouse.
- **Qué no se vio:** los diálogos (confirmación de ejecución: sólo su texto; selector de archivos; mapa de pérdidas; `QMessageBox`), una **corrida en curso** (no se ejecutó el solver, por instrucción), el ejecutable empaquetado (se usó el código fuente con PySide6 6.10.1; `requirements.txt` fija 6.11.2), escalas de pantalla de 125 %/150 % y monitores 4K.
- **Pantalla Simulación** a 980×680: capturada, no revisada en detalle.
- **#1 (selección entre carpetas)** se deduce del código y del comportamiento estándar del diálogo nativo de Windows; conviene confirmarlo a mano.
- **#7 (combos duplicados)** se midió en la secuencia "ventana nueva → abrir proyecto", que reproduce "Abrir…". Conviene confirmarlo con la app abierta a mano.
- **Los 74 s de importación** se midieron en esta máquina con 5 corridas de 1 ciclo; escalan con ciclos y celdas.
- **Datos que los wireframes suponen y conviene verificar:** que el callback `progress` no expone hoy la racha de periodicidad (sólo ciclo, ángulo y RSS; si es así, no mostrarla); que todos los canales de traza de celdas comparten los mismos ángulos (sugerido por "ángulos comunes exactos"); y que los grados de lumbrera de `event_angles` son los adecuados para mostrar (en `effective_profile` devuelve nudos del perfil, no apertura/cierre).
- **Los valores de los wireframes** (124,8 cm³, 98°, 21,5 bar, etc.) son ilustrativos, salvo los citados como medidos.
- No se ejecutó el protocolo de sesión de `AGENTS.md` (`program_status.py promote/log`) porque esta auditoría es de sólo lectura y no forma parte de `CURRENT_OBJECTIVE`. `program-status.json` no se tocó.
