## Why
Las etapas RK4 2T pueden intentar transportar fresca desde un inventario base
nulo o superar F=m. Evaluar una corrección conservativa sin cambiar física,
tolerancias, mínimo, controlador, dominio público ni resultados aceptados.
## What Changes
Prototipo numérico opt-in y pruebas antes de decidir integración en producción.
Instrumentación, microcasos, campaña baja y comparación histórica; alta RPM
solo si aprueba el gate bajo. Sin candidata Windows ni cambios de dev_orchestrator.
## Capabilities
### New Capabilities
- `positividad-transporte-2t`: evaluación de limitación conservativa por etapa.
### Modified Capabilities
## Impact
Herramientas experimentales, tests y evidencia. Producción únicamente tras gate.
