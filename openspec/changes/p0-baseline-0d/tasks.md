## P0
- [x] Leer orden, comprobar Git y preservar eliminación ajena redme.txt.
- [x] Configurar únicamente P0 y probar adaptador/contratos sin integrar física.
- [x] Registrar commit fuente y ejecutar P0 real: tests y26RPM completos.
- [x] Comprobar regresiones, tiempos, balances y continuidad de la malla.
- [x] Ejecutar stress y gráficos solo si26PASS.
- [x] Revisión independiente mediante contrato reviewer, verificar scope y gate.
- [x] Freeze Markdown/JSON solo si gate aprueba; conservar human approval pendiente.
- [x] Registrar evidencia contractual y entrega separada; detenerse sin P1.

## Resultado del 17/09/2026
**P0_PASS_BASELINE_FROZEN**, gate PASS, execution_status WAITING_HUMAN_APPROVAL.
Fuente de campaña:43c23b4d14bc723b5732d132bfab484d1c85a725.
Run real:20260917T151222-P0-e7c30e109458, invocado con
`.\.venv\Scripts\python.exe -m dev_orchestrator.runners.run_phase P0`.
Un intento, cero reintentos/reparaciones automáticas y sin encadenamiento.

26/26 principales PASS, cero fallos ni RPM omitidas. Malla2500:500:15000
CONTINUOUS_2T_NUMERICAL_DOMAIN_2500_15000_VERIFIED. La etiqueta acredita esa
malla; no es una prueba matemática de cada RPM real intermedio.
Stress independiente posterior:16000/18000/20000 PASS (14/15/16ciclos),
HIGH_RPM_STRESS_20000_PASS. Exploratorio; público2500–3500 intacto.
Siete regresiones2500/3000/5000/8000/10000/12000/15000 exactamente iguales:
manifest y todos los campos científicos salvo seconds, incluyendo ciclos,
muestras, balances, W, presión, estado terminal y estadísticas del controlador.

La tabla completa incluye W/pmax/potencia/par, ciclos, pasos, rechazos y tiempos:
`results/p0-baseline-0d-20260917/table.md` y `artifacts/table.csv`.
En ese directorio, las rutas manifest_path del baseline son relativas a la raíz
de la evidencia seleccionada (artifacts/points/...). Los JSON conservan precisión
completa, independiente del redondeo de la tabla Markdown.
Baseline:docs/baselines/0d_2t_baseline_v1.md y0d_2t_baseline_v1.json.
Estado NUMERICALLY_VERIFIED_BASELINE; no validación física ni aceptación humana.

Balance independiente peor de los últimos ciclos convergidos principales:
0,0006649575645223834% a2500RPM, bajo contrato0,1%. Se conserva el contrato de
convergencia y sus últimos tres ciclos; rechazos internos no son estados inválidos
aceptados. Fuente de invariantes/criterios es producción, sin relajar validadores.
Mínimo medio paso observado0,0010027931348304264° a10500RPM; contrato0,001°.
Más rechazos197 a2500RPM. Más ciclos principales14 (14500/15000).
Punto principal más lento14500:19,094s de integración.

Integración principal397,580s. Por punto mínimo11,891/máximo19,094/
mediana14,7735/media15,29153846s. Wall por punto principal:
12,156/19,360/15,0315/15,54696154s, en ese mismo orden.
Integración total con stress458,861s; checkpoint wall de campaña471,391s;
subprocess completo472,344s (incluye cierre/inventario). Por punto, incluyendo
stress, integración mínimo11,891/máximo21,719/mediana15,906/media15,82279310s.
Punto más lento global20000:21,719s y16ciclos. No objetivo temporal nuevo.

## Comprobación y revisión
P0 ejecutó317tests MotorSim/107,747s y25tests orquestador/38,863s, todos PASS;
incluye regresiones4T existentes sin nueva campaña4T. Qt offscreen no acredita
inspección de la aplicación Windows. OpenSpec1.3.1 estricto PASS.
Revisión independiente de solo lectura por /root/review_rc2_hardening:
26+3puntos,7regresiones exactas,34hashes del inventario, producción intacta e
interpretación limitada. No ejecutó campañas ni escribió archivos. Contrato
reviewer almacenado en artifacts/independent-review.json, separado del primer
reviewer_unavailable del runner, preservado en pre-review-evidence.json.

Hallazgo concreto corregido: un fallo después de crear documentos baseline podía
impedir cerrar otra vez. El finalizador ahora prevalida destinos y protege TODO
el cierre; rollback restaura evidencia inicial y solo retira documentos nuevos
propios, sin descartar cambios concurrentes.11tests focales finales/1,707s PASS,
incluida inyección de fallo Git tras creación y recuperación explícita sin solver.
El primer test de inyección necesitó normalizar la ruta temporal Windows; log
fallido y log final se conservan separadamente, sin modificar expected científicos.

Las correcciones se aplicaron después de terminar la campaña: finalizador,
registro de fuente SegoeUI para gráficos offscreen y tests. Se declararon SOLO
esos archivos y la configuración P0 en el alcance del cierre autorizado. Se
preservan phase-at-execution.json y phase-at-closure.json; closure_scope rechaza
cualquier cambio de checks/criterios u otra ampliación (incluido motorsim/).
No se repitió la campaña. Scope final sin violaciones; los siete paths modificados
durante cierre están detallados en closure-scope.json, incluidos los dos baseline.
La eliminación previa de redme.txt permanece ajena y fuera de los commits.

Inspección visual del agente: gráfico inicial ilegible por fuente offscreen;
regenerado desde datos guardados como diagnostic-plots-readable.png, con ocho
gráficos legibles. Original conservado por hashes; no presentar como figura final.
Sin cambios de datos ni nueva integración. No es inspección visual de UI productiva.

Se versionó selección contractual (evidence/summary, logs, índices, resultados,
review y freeze), no todo runs/ automáticamente. Copia y hashes comprobados.
El finalizador ejecutado produjo PASS/WAITING_HUMAN_APPROVAL; aceptación manual
pendiente. No cambios de producción, limiter, formatos, física o tolerancias;
sin ampliar dominio público, sin candidata, sin archivo y sin iniciar P1.

## Aceptación posterior — 17/09/2026
La usuaria acepta expresamente P0: **P0_HUMAN_ACCEPTED**. Registro vinculado
por hashes en docs/gasdynamic/p0_human_acceptance.json, sin modificar baseline
ni evidencia original. No cambia la clasificación NUMERICALLY_VERIFIED_BASELINE.
Autoriza únicamente P1 contractual; no P2. La ampliación pública 2T de d2932da
fue una autorización separada posterior a la fotografía congelada de P0.
