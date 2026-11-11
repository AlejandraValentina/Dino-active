# Integración controlada F0/F1 + CP0–CP2

Rama: `integration/dino-frontend-commercial-v1`.
Worktree nuevo: `dino-frontend-commercial-v1`, en E:.
Base: main `f97469b`; frontend aceptado en fuente `9b7392e`.

## Conflicto operativo

Único conflicto textual: `program-status.json`. El análisis a tres bandas contra
`d44305c` encontró cuatro claves divergentes: cola, progreso, objetivo y gate.
No hubo tareas compartidas con cambios semánticos contradictorios en ambos padres.
Se preservaron 577 tareas heredadas mediante unión por ID y cambios descendientes;
se conservaron los registros distintos de progreso y ambos objetivos/gates padre.
Se registró un objetivo nuevo de integración con ocho tareas. Los doce blockers
científicos heredados siguen fuera del alcance; el frontend no aporta sus datos
faltantes ni autoriza campañas postergadas.

Evidencia: `results/frontend-commercial-integration-v1/state-consolidation.json`.
Los padres del merge conservan los archivos originales completos. No se eligió
automáticamente una de las dos colas ni se reescribieron estados científicos.

## Estrategia de verificación

Regresión focal de frontend + CP0–CP2, contratos protegidos y reproducción
diferencial de fallos generales heredados. No se presenta un conjunto focal como
una suite general verde. Recorridos reales independientes de las tres familias
en fuente y en candidato empaquetado. Licencias de prueba usan secretos efímeros
en memoria y claves públicas inyectadas sólo en la aceptación; no son licencias
comerciales emitidas ni cambian las claves del producto.

Los recibos finales distinguirán fuente, ejecutable, regresión general, UAT humano
y validación científica. La integración y el candidato no se publican ni se
fusionan a main durante esta tarea.
