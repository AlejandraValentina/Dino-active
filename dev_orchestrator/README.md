# Dev orchestrator de MotorSim

Infraestructura local de desarrollo, separada del producto. Ejecuta **una fase
explícita**, recopila evidencia y decide un gate. No modifica código por sí misma,
no implementa física y no conecta agentes/modelos externos. No inicia P0/P1/P2,
no encadena fases, no crea commits ni publica. No se distribuye con MotorSim.

Python 3.11 y biblioteca estándar. Se eligió JSON en lugar de YAML porque
PyYAML no está instalado: contratos legibles sin dependencias nuevas. Los
archivos JSON Schema son formales; el validador local implementa únicamente
las keywords usadas y rechaza otras, en vez de ignorarlas. No pretende ser un
validador universal de JSON Schema. Claves duplicadas, números no finitos,
campos desconocidos y estados inventados se rechazan.

## Uso desde la raíz del repositorio

```powershell
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase dummy --dry-run
.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase dummy
.\.venv\Scripts\python.exe -m unittest discover -s dev_orchestrator/tests -v
```

El primer comando solo lee contratos y muestra fase, dependencias, comandos,
alcance y gate esperado. No crea runs ni procesos. El segundo ejecuta un test
unittest real, crea un archivo dentro del run, comprueba SHA256, registra métricas
y usa el reviewer stub local. Debe finalizar PASS. El stub prueba el cableado:
**no equivale a revisión científica independiente ni aceptación manual**.

Cada ejecución real crea `runs/<UTC>-<fase>-<uuid>/` con `evidence.json`,
`summary.md`, `logs/` y `artifacts/`. Runs están ignorados por Git. Una copia
seleccionada y explícita puede versionarse en `examples/`. No hay secretos,
volcado del entorno ni logs grandes dentro de evidence.json.

## Estructura

```text
dev_orchestrator/
  config.json                intérprete actual, timeouts, reintentos, runs, stub
  contracts.py               lectura estricta, schema y coherencia roadmap/fase
  git_state.py               estado inicial, hashes e índice Git, alcance
  roadmap/gasdynamic.json    P0–P9 declarativas + dummy
  phases/*.json              contratos; solo dummy habilitada
  runners/run_phase.py       ejecución de una fase y evidencia parcial
  runners/run_tests.py       subprocess; pytest completo o subset opcional
  runners/process_tree.py    ciclo de vida de procesos/descendientes
  runners/process_host.py    arranque Windows después de asignar Job
  runners/run_review.py      interfaz neutral y stub local
  gates/{policies.json,evaluate.py}
  evidence/build_report.py   JSON validado + resumen
  schemas/*.schema.json      fase, roadmap, config, resultado, revisión, evidencia
  tests/                     fixtures temporales, smoke, regresiones
  runs/                      ignorado; ejecuciones exclusivas
```

Roadmap: P0 Freeze baseline 0D; P1 1D mathematical contract; P2 1D isolated
solver; P3 0D↔1D coupling; P4 1D exhaust; P5 Intake + transfers; P6 Species/
scavenging; P7 Heat/combustion improvements; P8 Wide RPM performance;
P9 Experimental validation. Son declaraciones, no contratos científicos
implementados ni autorización para ejecutarlas. Sus comandos están vacíos y
`enabled=false`; sus paths permitidos están vacíos.

## Contratos y gates

Una fase declara objetivo, dependencias, cambios permitidos/prohibidos,
`allowed_paths`/`forbidden_paths`, comandos, tests/checks/evidencia requerida,
política, límite de reintentos, revisión y human gate. El roadmap debe concordar.
Un path terminado en `/` permite su subárbol; un path sin `/` final permite
exactamente ese archivo. No se admiten rutas absolutas, `..` ni globbing.

Comandos son listas argv, sin shell. `{python}` usa `sys.executable`;
`{run_dir}` apunta al directorio exclusivo del intento. Un comando puede producir
`result_file` relativo a ese directorio, de hasta1MiB, con `checks`, `metrics`
numéricas y `scientific_change_required`. Un comando que completa el reporte
devuelve0; un check numérico fallido se expresa como `passed=false`, no como
un error del runner. Identificadores duplicados se rechazan.

| Gate terminal | Significado |
| --- | --- |
| PASS | Checks/tests requeridos aprobados, evidencia completa, alcance respetado y revisión aprobada. El único stub admitido es el de dummy. |
| BLOCKED | Falla de test/benchmark/criterio numérico, dependencia no aprobada, fase deshabilitada, alcance violado, evidencia incompleta o reintentos agotados. |
| SCIENTIFIC_CHANGE_REQUIRED | Continuar exige un cambio científico/contractual no autorizado. Se detiene sin reparar ni reintentar. |
| FAILED_INFRASTRUCTURE | Runner/entorno/herramienta/archivo/esquema inválido, cancelación o timeout total. |

Una violación de alcance siempre bloquea. Para el resto, precedencia: infraestructura, necesidad científica,
bloqueos, PASS. Se conservan todas las violaciones/errores observados aunque
otro estado tenga precedencia. No se interpreta una excepción como fallo físico.
Archivo requerido ausente es infraestructura; conjunto incompleto por un test
fallido sigue BLOCKED. Timeout de test es BLOCKED; de herramienta/total es
FAILED_INFRASTRUCTURE.

## Límites, cancelación y reparación

Config:30s por comando,120s por fase, máximo3 reparaciones por defecto.
La fase puede fijar límites explícitos dentro del schema. Observación Git tiene
timeout y cierre de evidencia reserva hasta15s adicionales; terminar procesos
admite una espera de cierre de hasta5s. Los límites no se eliminan para aprobar.

Por defecto hay un solo intento. `--retry-failed-checks` permite hasta
`1 + max_repair_attempts` verificaciones (inicial + reintentos). **No hay motor de
reparación ni cambios automáticos de código**. Cada intento registra causa y
estado; usa nuevos artefactos y logs. Al agotar el límite termina BLOCKED.
Alcance violado, infraestructura o cambio científico impiden reintentar.

Ctrl+C o cancelación programática detienen el árbol del comando y escriben
evidencia parcial con `cancelled_by_user`. No hay locks persistentes. En Windows
se usa un Job kill-on-close: un host espera GO antes de crear descendientes,
después de ser asignado al Job. En POSIX se usa una sesión/grupo propio. También
se terminan descendientes residuales si el comando padre sale antes que ellos.
El cierre termina el Job y espera hasta cinco segundos a que no queden procesos
activos antes de liberar el handle.

## Git y alcance

Antes de ejecutar se guardan HEAD, dirty, cambios existentes y untracked. Se
comparan contenido, modo e índice de archivos Git después de **cada comando**
y al cierre. Cambios previos sin alterar no se atribuyen al run; modificar un
archivo ya dirty/untracked se registra como `preexisting_touched` y bloquea,
aunque su path esté permitido. Nunca se restaura, resetea, borra ni limpia el árbol.

Es un control posterior de alcance, **no un sandbox para comandos hostiles**.
Solo ejecutar contratos revisados y autorizados. Los archivos ignorados por Git
no se auditan con ese inventario; los artefactos requeridos sí tienen ruta
resuelta dentro del run, tamaño y hash. No prueba autoría de cambios concurrentes:
registra cambios observados durante la ejecución de forma conservadora.

## Revisión y human approval

- Implementador: puede cambiar solo archivos autorizados, fuera de este runner.
- Revisor: read-only; recibe fase, diff de paths, evidencia y checks requeridos;
  devuelve status/findings/blocking_findings/scientific_change_required/notes.
  No corrige su propio hallazgo. `kind` identifica stub/independent/none.
- Orquestador: verifica evidencia y aplica el gate; no crea una red de agentes.

Una fase aprobada con `human_gate=true` termina con `gate=PASS` y
`execution_status=WAITING_HUMAN_APPROVAL`. Ese estado no es un gate científico
y no sirve como dependencia aprobada. No existe aún un flujo automático de
aprobación humana ni un proveedor externo conectado. Pueden añadirse adaptadores
neutrales después; las credenciales futuras deben venir de un entorno seguro,
nunca de archivos versionados o evidence.json.

Dependencias se suministran explícitamente:
`--dependency P0=ruta/evidence.json`. Deben validar schema, identificar la fase,
tener PASS y COMPLETED. La mera existencia de un archivo no basta.

`python -m dev_orchestrator.runners.run_phase P2 --continue` reconoce la opción,
pero P2 continúa deshabilitada. **Nunca ejecuta la fase siguiente**; solo registra
la intención. Para futuras fases primero se requiere autorización y contrato
científico específico; añadir comandos/checks/evidencia revisados y un reviewer
independiente real. No basta quitar `enabled=false` para obtener PASS.

## Test runner opcional

`run_tests.run_pytest(paths=(), cwd=..., logs=..., timeout=...)` invoca
`[sys.executable, '-m', 'pytest', *paths]` por subprocess. Lista vacía es suite
completa; acepta subset y opciones. Captura stdout/stderr en archivos, exit code,
duración y estado. No usa internals de pytest. Pytest no está instalado en el
entorno comprobado: no es necesario para dummy ni estos tests (usan unittest).
Si se instala en el futuro, debe ser dependencia **de desarrollo**, no runtime.
Su ausencia se identifica como error de entorno.

## Distribución y comprobación

Tests AST comprueban que `motorsim/` no importa esta infraestructura. Los specs
PyInstaller excluyen el módulo en GUI y worker; el ZIP rechaza un árbol que lo
contenga. No se construye una candidata para comprobar estas reglas.
Pruebas de infraestructura cubren los cuatro gates, schema, dependencias,
scope/dirty, timeouts, descendientes, cancelación, reintentos, revisión, evidencia,
dry-run y separación del human gate. Ejemplos de evidencia finales en `examples/`.

Comprobación del 17/09/2026, Windows y Python 3.11.0: 25 tests del orquestador
aprobados (30,971 s), más 22 de rendimiento y 4 de persistencia de MotorSim.
No se ejecutaron campañas físicas ni un build. La revisión independiente puntual
detectó que una cancelación podía ocultar el gate BLOCKED de una violación de
alcance: corregido y cubierto por regresión. Un fallo intermitente de limpieza de
temporales motivó esperar la terminación del Job; las pruebas finales aprobaron.
Esta revisión independiente se distingue del stub local empleado por dummy.
