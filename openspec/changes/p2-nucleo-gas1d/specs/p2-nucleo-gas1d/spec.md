## ADDED Requirements
### Requirement: Núcleo aislado first-order
P2A SHALL implementar exactamente el contrato P1 congelado: EOS, FV de primer
orden, HLLC con fallback HLLE completo, Euler explícito, CFL global, fuente
de área, especie, BC y ledgers. SHALL conservar baseline y producto existente.
#### Scenario: Estado inválido
- **WHEN** una etapa viola admisibilidad
- **THEN** rechaza la etapa completa con reducción acotada o falla sin clipping.
### Requirement: Verificación contractual
T01–T12 SHALL ejecutarse con IC, BC, referencias y criterios congelados P1.
SHALL registrar arrays, ledgers, errores, CFL, fallbacks, tiempos y refinamiento.
#### Scenario: Criterio incumplido
- **WHEN** una prueba no satisface su umbral
- **THEN** no declara PASS ni modifica el criterio; diagnostica implementación
  y detiene SCIENTIFIC_CHANGE_REQUIRED si requiere cambiar el contrato.
### Requirement: P2B condicionado
MUSCL/minmod y SSP-RK2 SHALL implementarse solo después de P2A PASS con revisión.
#### Scenario: P2A bloqueado
- **WHEN** P2A no aprueba tras reparaciones permitidas o requiere cambio científico
- **THEN** no implementa P2B, no inicia P3 y registra evidencia del bloqueo.
### Requirement: Gate y aceptación
P2 SHALL ejecutarse mediante dev_orchestrator con P0/P1 aceptadas, máximo tres
reparaciones, reviewer independiente y gate humano. P3–P9 SHALL seguir deshabilitadas.
#### Scenario: Núcleo verificado
- **WHEN** P2A/P2B, regresión P0 y revisión aprueban
- **THEN** termina P2_PASS_1D_CORE_VERIFIED / WAITING_HUMAN_APPROVAL sin P3.

### Requirement: Revisión científica R5 de segundo orden
T11 de MUSCL/minmod/SSP-RK2 SHALL aplicar el contrato1D_CONTRACT_V1_R5 adoptado
tras evidencia completa y revisión independiente; FIRST_ORDER SHALL mantenerR4.
SHALL conservar todos los casos, exactitud padre, conservación/admisibilidad y
convergencia del error a referencia. SHALL preservar los fallos históricosR4.
#### Scenario: Evidencia incompleta
- **WHEN** falta un final acústico o Sod, o una comparación obligatoria
- **THEN** T11 no puede aprobar aunque las sensibilidades disponibles cumplan.
#### Scenario: Cierre técnico aprobado
- **WHEN** T01–T12, P0, FIRST_ORDER, alcance y revisión independiente aprueban
- **THEN** registra P2_PASS_1D_CORE_VERIFIED / WAITING_HUMAN_APPROVAL sin aceptarP2 ni iniciarP3.
