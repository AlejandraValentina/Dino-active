## ADDED Requirements
### Requirement: Campaña autocontenida de producción
P0 SHALL ejecutar los26RPM de2500 a15000 cada500 desde arranques independientes,
con solver/perfil/regularización/tolerancias/límites actuales. SHALL registrar
estados, muestras, balances, pasos, rechazos, ciclos, tiempos, derivados y hashes.
#### Scenario: Falla de un punto
- **WHEN** algún punto principal no aprueba el contrato existente
- **THEN** conserva evidencia diagnostic_only, ejecuta los demás puntos principales,
  no ejecuta stress y termina P0_BLOCKED_CONTINUOUS_DOMAIN sin modificar producción.
### Requirement: Regresión y freeze condicionado
P0 SHALL comparar exactamente históricos2500/3000/5000/8000/10000/12000/15000
excluyendo únicamente tiempo. SHALL requerir26PASS, regresiones, evidencia,
scope limpio y reviewer independiente PASS para P0_PASS_BASELINE_FROZEN.
#### Scenario: Gate aprobado
- **WHEN** se acreditan todas las condiciones
- **THEN** genera baseline Markdown/JSON NUMERICALLY_VERIFIED_BASELINE,
  mantiene WAITING_HUMAN_APPROVAL y detiene antes de P1, sin cambiar rango público.
### Requirement: Stress exploratorio separado
P0 SHALL ejecutar16000/18000/20000 solo si26puntos principalesPASS.
#### Scenario: Límite exploratorio
- **WHEN** falla un punto de stress
- **THEN** registra HIGH_RPM_STRESS_LIMIT_OBSERVED sin invalidar automáticamente
  el dominio principal ni corregir física o contrato.
