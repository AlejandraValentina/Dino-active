## Trabajo autorizado
- [x] Comprobar Git y separación de dev_orchestrator; preservar redme.txt.
- [x] Documentar algoritmo y contraejemplo de límite superior antes de producción.
- [x] Implementar candidato aislado y microcasos inferiores/superiores.
- [x] Tests específicos, suite completa y OpenSpec estricto.
- [x] Campaña baja, magnitudes y comparación exacta3000/performance.
- [ ] Alta RPM únicamente si aprueba el gate bajo: NO habilitada, candidato rechazado.
- [x] Revisión independiente y decisión REJECT_CANDIDATE.
- [x] Registrar entrega en commit separado de dev_orchestrator, sin publicar.

## Resultado del 17/09/2026
**REJECT_CANDIDATE**. No promover a producción. No ampliar rango ni construir
candidata, no regularizar donor ni iniciar 1D. Dev_orchestrator intacto.
La reducción conservativa resuelve los microcasos y permite converger1750/2000,
pero no cumple baja intervención histórica: no basta el cambio final pequeño.
1000 alcanza16ciclos/60s sin converger y balance independiente0,200333%;1500
falla mínimo sin completar ciclo. No se cumple exactamente el resultadoB de la
orden (1000 ya no se detiene por mínimo). No atribuir únicamente donor switch
a la falta de convergencia1000 sin una investigación posterior autorizada.

Evidencia: `results/positividad-transporte-2t-20260917/`. summary.md contiene tabla
completa; campaign.json métricas, tiempos y parada; comparison.json diferencias
por ciclo y muestras; JSON individuales preservan resultados completos y los
JSONL todas las activaciones por enlace/ángulo/ciclo/RPM/etapa.
Las correcciones acumulan subetapas e intentos rechazados; no son masa neta
alterada de la trayectoria aceptada. No se ejecutó alta RPM porque no aprobó gate.

Microestado real2000: base F_C=0, candidato original=-9,523239929231602e-18kg;
limitado0, corrección de flujo de esa misma magnitud. Microestado real1750:
F_I supera m_I por1ulp; corregido antes de evaluar, modificando flujo entrante
en4,768129017417847e-21kg, alpha0,9999999999061989. m/U exactamente iguales.
Tests incluyen contraejemplo de límite superior inviable con solo reducciones;
rechaza explícitamente, sin recortar estado ni afirmar garantía universal.

Regresión3000: baseline nuevo reproduce TODOS los campos científicos del
histórico, manifest incluido (excluye únicamente tiempo). El candidato conserva
manifest y10ciclos, pero5activaciones en ciclo1, suma4,1933716701948405e-11kg,
máxima4,129454236572099e-11kg, alpha mínimo0. Máxima corrección equivale a
7,6175e8 veces el mayor ulp de masas en las muestras finales: no es redondeo.
W pasa16,49050751206088→16,490507412073466J (delta−9,99874e-8J);
pmax1331530,846070603→1331530,8434957908Pa (delta−0,002574812Pa).
1442muestras alineadas: máximas diferencias de W1,28923e-7J y de Q2,84540e-7J.
Se conservan comparaciones completas sin reemplazar expected ni históricos.
También cambia2250: deltaW7,66535e-7J;2500:1,06737e-6J;2750:−5,57458e-7J.
No se afirma deriva macroscópica: el rechazo se basa en el criterio explícito
de intervención limitada a redondeo y falta de aprobación integral de campaña.

Conservación discreta de fresca global: peor residuo absoluto en ciclos
completos de toda campaña3,10353e-18kg, descontando Bdot y contornos.3000:
peor residuo normalizado de fresca entre volúmenes del último ciclo
1,59889e-15 (baseline3,01067e-15); balance independiente0,000445747%.
1000 NO supera balance independiente0,1% al acabar presupuesto; no se relaja.
No hubo rechazos no físicos con candidato; los estados construidos cumplen
límites estrictos y Model conserva su validación original. No se modificó m/U
en el limiter; la trayectoria posterior sí puede variar y está cuantificada.

Performance3000, medición secuencial sin otra campaña concurrente:
integración13,375→15,015s (+12,26%); wall13,656→15,250s (+11,67%).
No es benchmark estadístico de CPU ni se atribuye precisión de microbenchmark.
Integración total baseline+ocho puntos170,577s; límites originales por punto
60s/30ciclos/2MRHS/512MiB, B/100Pa y mínimo0,001° sin cambios.

Comprobaciones: suite completa307tests/89,924s aprobada (Qt offscreen, no
inspección Windows);16tests focales finales/1,551s aprobados;OpenSpec1.3.1
estricto aprobado. La suite completa incluía15tests nuevos; el16.º cubre solo
la comparación JSON corregida y se ejecutó en el subset final, sin repetir
campañas. Comparación inicial confundía tuplas con listas persistidas: se
corrigieron flags leyendo JSON guardados, sin alterar resultados ni reintegrar.
El log de consola original conserva esos flags iniciales; comparison.json y
campaign.json corregido son la comparación válida.

Autorrevisión del diff separada de revisión independiente focal de solo lectura:
sin defecto matemático reproducible;14tests repetidos por revisor antes del
test adicional de RK completo y el de representación JSON. El mismo revisor
comprobó evidencia y respaldó rechazo; no se abrió otra revisión general.
No aceptación manual ni validación experimental atribuida. Sin archivar.
