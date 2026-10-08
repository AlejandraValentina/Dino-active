## Decisiones
Documentos normativos en docs/gasdynamic: mathematical, numerical, verification
y manifest v1. Ecuaciones y tests no se convierten en runtime. El manifest enlaza
por hash los documentos y preserva el inventario de producción actual.

P0_HUMAN_ACCEPTED se registra mediante recibo posterior vinculado a evidencia y
baseline. Una copia derivada identifica explícitamente la aceptación y cambia
solo execution_status a COMPLETED para el contrato de dependencia existente.
No editar baseline ni evidencia original. d2932da ya amplió el rango público
2T por autorización separada; P1 no revierte ese cambio.

P1 requiere dependencia P0 PASS aceptada, max_repair_attempts=0 y human_gate.
P2–P9 deshabilitadas. El reviewer local no acredita ciencia: revisión externa
read-only vinculada al hash de evidencia y documentos; preservar resultado
inicial del stub y reevaluar gate explícitamente, sin ejecutar de nuevo tests
numéricos ni continuar automáticamente. No modificar runner genérico.

Guardas de hashes/estructura comprueban contrato, no precisión del futuro solver.
Revisión independiente examina matemáticas y criterios. Toda decisión científica
no resuelta bloquea. Registrar T01–T12 solo como especificados, nunca aprobados.
