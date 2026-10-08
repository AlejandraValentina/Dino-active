## ADDED Requirements
### Requirement: Conservación e invariantes por etapa
El candidato SHALL limitar flujos de especie, nunca recortar estados; SHALL
aplicar cada flujo interno con signos opuestos, mantener m/U, donor y dirección
de q, y comprobar 0 <= F <= m antes de evaluar estados. SHALL conservar Bdot
analítico, tolerancias, dt_min, RK4 y regularización exterior actuales.
#### Scenario: Inventario agotado
- **WHEN** salidas simultáneas exceden el inventario disponible
- **THEN** se limitan conservativamente antes de construir la etapa o se rechaza
  explícitamente la etapa si el candidato no puede garantizar sus invariantes.
### Requirement: Gate científico y evidencia
El candidato SHALL acreditar microcasos, conservación, regresión histórica3000,
magnitud de intervención y campaña1000/1500/1750/2000/2250/2500/2750/3000.
SHALL ejecutar alta5000/8000/10000/12000/15000 solo tras aprobar campaña baja.
SHALL rechazar deriva apreciable o pérdida de conservación, sin cambiar expected.
#### Scenario: Falta de aprobación
- **WHEN** falla un criterio obligatorio
- **THEN** no se integra el candidato ni se amplía dominio ni se genera paquete;
  se conserva evidencia y se comunica REJECT_CANDIDATE o SCIENTIFIC_CHANGE_REQUIRED.
