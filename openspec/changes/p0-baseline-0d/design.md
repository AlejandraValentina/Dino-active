## Ejecución
`python -m dev_orchestrator.runners.run_phase P0` ejecuta checks existentes y
campaña de producción. El adaptador P0 importa Model/run_adaptive originales;
cada punto construye caso canónico independiente, perfilB,100Pa,min0,001°,
60s/30ciclos/2MRHS/512MiB sin modificaciones. No importar tools experimentales.
26puntos aunque haya fallos; stress solo si26PASS. Sin reintentos ni warm-start.
Timeout de infraestructura2400s cubre29*60s más pruebas/cierre; no sustituye
los límites científicos por punto. Guardar resultados y checkpoint tras cada RPM.
Snapshot Git, hashes de producción, manifiestos y hashes de todos los artefactos.
Históricos2500/3000 desde frontera-baja;5000/8000/10000/12000/15000 desde
rendimiento-dominio. Comparar JSON normalizado, todos los campos salvo seconds.

## Revisión y cierre sin repetir campaña
El reviewer actual no tiene proveedor independiente para P0: el primer cierre
del runner conserva BLOCKED/reviewer_unavailable, sin fingir aprobación. Revisión
externa puntual de solo lectura vinculada a run_id y SHA256 de evidence.json.
El finalizador específico P0 verifica el contrato reviewer, hashes de artefactos,
checks, configuración y snapshot Git antes de reevaluar con el gate existente.
Conserva evidence/summary anteriores y reporte del revisor como artefactos.
No ejecuta solver, tests, reparaciones ni P1. PASS conserva execution_status
WAITING_HUMAN_APPROVAL: freeze numérico autorizado, aceptación humana pendiente.
Documentos baseline se crean solo si gate científico/regresión/revisión/scope
aprueban; no sobrescribir documentos existentes ni modificar producción.

## Alcance e interpretación
Cambios durante ejecución solo en runs ignorados y documentos baseline nuevos.
Contratos y herramientas se registran antes de ejecutar; preservar redme.txt.
La expresión dominio continuo significa malla2500:500:15000 comprobada, NO
una prueba matemática de todos los RPM reales intermedios. Gráficos diagnósticos
si26PASS, sin validación experimental, ondas ni escape sintonizado predictivo.
Stress separado y no vinculante para gate principal; públicos2500–3500 intactos.

## Cierre comprobado
Tras terminar la campaña se corrigió una ruta de error del finalizador y la
fuente de los gráficos. El alcance del cierre declara únicamente esos archivos
P0 y sus tests/configuración, permitidos por la orden. El finalizador contrasta
la definición original del commit de ejecución: solo admite esa ampliación de
paths; ningún cambio de checks o criterios. Ambas definiciones y hashes quedan
en evidencia. No se altera ni se vuelve a ejecutar la campaña para cerrar.
Freeze numérico PASS, con aceptación humana pendiente; detalles medidos en tasks.md.
