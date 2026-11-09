## Context
C05 depende de C01–C04 y debe preservar la historia de `main`, la rama A/B y
las correcciones ya archivadas. En esta rama `main` es ancestro de `HEAD`, la
rama A/B y la auditoría también lo son; la integración controlada es un
fast-forward, no un merge con conflictos. Los bordes que quedaban abiertos son
F03, F15, F16 y A2-03.

## Decisions
### 1. F03 — continuación segura, no reinicio exacto
`DINO4T_STATE_CONTEXT_V1` conserva `state`, `theta_deg`, `phase_deg`,
`cycles_completed`, `model_id`, `config_sha256`, `topology_sha256` y
`complete_cycle`. Sólo se acepta una frontera de ciclo 720°. Misma
configuración produce `continuation`; configuración distinta con topología
idéntica produce `warm_start`; topología incompatible se rechaza. El resumen
declara `exact_restart_claim=NOT_SUPPORTED`. La equivalencia se verifica a
nivel de roundoff en frontera de ciclo, no como reinicio exacto arbitrario.

### 2. F15 — ciclo de vida Qt determinista
`QRunnable` usa `setAutoDelete(False)` y un token por corrida; las señales
tardías se ignoran. `FourStrokeContext` reserva un único slot de ejecución y
bloquea mutaciones mientras corre. `shutdown()` cancela, espera y elimina el
request temporal; el cierre no destruye widgets con callbacks pendientes y no
deja `MotorSimWorker.exe` huérfano.

### 3. F16 — receipt terminal
`finalize_acceptance` espera el proceso, exige exit code 0, ejecuta el chequeo
final de hilos/procesos y sólo entonces escribe `acceptance.json` PASS. Error,
timeout, worker huérfano o cierre incompleto se conservan como
`acceptance-failure.json` / `acceptance-incomplete.json`; nunca como PASS.

### 4. A2-03 — curva 4T 0D vinculada y portable
La referencia de curva guarda `series_id`, `series_sha256`, `project_sha256`,
estado, modelo, RPM y una ruta relativa `curves/<series_id>/series.json`. La
serie se copia junto al proyecto guardado. `project_sha256` excluye las
referencias, por lo que adjuntar una curva no cambia la identidad del
proyecto. La evaluación distingue `FRESH_COMPLETE`, `FRESH_PARTIAL`,
`STALE_PROJECT`, `STALE_IN_PROGRESS`, `UNAVAILABLE`, `CORRUPT` y
`UNBOUND_PROJECT`. Una serie parcial conserva sus puntos y estados; sólo los
puntos convergidos se grafican. El proyecto nativo
`DINO_DESKTOP_ENGINE_PROJECT_4T_V1` no acepta `curve_references`.

### 5. C05 — integración controlada
Secuencia verificada: `main 5e4ba4d` → A/B `8b371e2` → auditoría `353e3f0` →
P1 `05b7a82` → C01/C03 `2fc8d70` → C02/C04 `fa81e9c` → C05 prep
(`668b20b`, `fd43f73`, `d1fbce7`, `f93714b`, `edba678`, `fb48277`,
`0b9e137`, `8be8196`, `ffc89b3`, `b92b744` y el commit de registro). La
integración es fast-forward y conserva todas las historias. No se ejecuta
merge, push ni build en esta etapa. La aceptación Windows empaquetada requiere
una autorización y un candidato nuevos; el paquete A/B previo no se
reinterpreta como prueba de estos cambios.

## Alternatives considered
- **Permitir cualquier `initial_state` y confiar en las formas de los arrays:**
  se descarta; no distingue fase, modelo ni configuración.
- **Implementar un checkpoint serializable y declarar reinicio exacto:** se
  descarta por alcance y por falta de evidencia de equivalencia bit a bit.
- **Guardar rutas absolutas a la raíz de artefactos:** se descarta por
  portabilidad y por F12; se copia la serie junto al proyecto.
- **Publicar PASS tras `terminate()` sin `wait`:** se descarta por F16.

## Risks / Trade-offs
- La copia de la serie agrega I/O y un límite de 128 MiB; no se borran
  artefactos históricos.
- `warm_start` entre configuraciones distintas es una etiqueta explícita, no
  una equivalencia exacta.
- La aceptación Windows y el build quedan pendientes; el cierre de C05 prep es
  sólo a nivel fuente y regresión local.
- No se modifican física, tolerancias, contratos P0–P9 ni evidencia histórica.
