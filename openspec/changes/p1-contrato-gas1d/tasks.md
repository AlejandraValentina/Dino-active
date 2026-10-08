## P1 contractual
- [x] Leer orden, preservar cambios ajenos y registrar aceptación P0 separada.
- [x] Definir matemáticas, numérica, BC, interfaces y T01–T12; consultar fuentes.
- [x] Crear manifest y checks contractuales sin solver.
- [x] Revisar contrato independientemente y resolver defectos concretos.
- [x] Ejecutar P1 mediante orquestador con dependencia aceptada y cero reparaciones.
- [x] Validar OpenSpec y registrar evidencia/gate/commits sin P2 ni archivo.

T01–T12 permanecen especificados, no ejecutados. La eliminación previa de
redme.txt es ajena y se conserva. No hay campaña 0D ni solver 1D nuevo.

Revisión independiente de solo lectura: PASS contractual; se corrigió la fuente
MUSCL para preservar exactamente p_i ΔA también en área suave y se precisaron
referencias desde conservadas en todos los contactos. Se explicitó p* HLLC.
11 pruebas de contrato aprobaron; no son T01–T12 ni una campaña física.
El recibo de aceptación P0 y su copia derivada conservan datos científicos.

## Resultado de ejecución
**P1_PASS_CONTRACT_READY / WAITING_HUMAN_APPROVAL**.
Run: `20260917T162700-P1-3b9e685fa1f4`; fuente ejecutada `ca3532b`,
contrato/implementación documental `5b6b62f`. Una ejecución, cero reparaciones,
11 pruebas PASS (0,131 s), cinco checks PASS, cero errores/violaciones de alcance.
Aceptación P0 comprobada antes de ejecutar; P2–P9 deshabilitadas.

El stub inicial devolvió BLOCKED exclusivamente por review_not_approved.
Revisión real `/root/p1_review`, independiente/read-only, vinculada a evidencia
SHA256 `68fdebaf29aebcb5184f0ef94884d1d096d50ced320d5dce4acaed05a8ebe6e5`
y seis hashes del inventario, aprobó el contrato corregido. El cierre explícito
conserva evidencia/summary originales y reevalúa el mismo gate sin reejecutar fase.
Evidencia seleccionada en `results/p1-contrato-gas1d-20260917/`; originales en
`dev_orchestrator/runs/20260917T162700-P1-3b9e685fa1f4/` (ignorados por Git).

OpenSpec estricto aprobado. Autorrevisión de alcance adicional, separada de
la revisión científica independiente. No se ejecutaron pruebas físicas, solver,
UI ni inspección visual Windows porque el cambio es contractual. Baseline P0 y
39 archivos Python de producción conservan hashes. El estado del manifest
CONTRACT_PENDING_REVIEW representa la instantánea entregada al revisor; el
resultado posterior autoritativo está en artifacts/p1-decision.json y evidence.json.

Pendiente únicamente aceptación humana de P1 antes de autorizar implementación.
T01–T12 son requisitos futuros, no tests ejecutados. No archivar ni iniciar P2.
Commit de evidencia contiene este registro; no publicar. redme.txt sigue ajeno.

## Aceptación humana posterior — 17/09/2026
P1_HUMAN_ACCEPTED por orden explícita de la usuaria. Recibo separado en
`docs/gasdynamic/p1_human_acceptance.json`, con hashes del contrato congelado.
No modifica los documentos ni evidencia de P1. Autoriza únicamente P2 con
P2B condicionado; ninguna autorización P3.
