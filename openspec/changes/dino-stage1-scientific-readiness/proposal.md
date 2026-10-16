# Propuesta: DINO_STAGE1_SCIENTIFIC_READINESS

## Estado y dependencia

Owner-approved para ejecutarse **después** de cerrar `DINO_DESKTOP_V3_1_VISUAL_PARITY`. No es el objetivo operativo actual. La evidencia V3.1 empaquetada debe completarse primero.

## Alcance

Abordar de forma focalizada las brechas científicas existentes de independencia de malla, periodicidad, conservación y consistencia de performance; luego preparar el contrato y el preflight de una curva RPM. Reutilizar modelos, pruebas, artifacts y runners ya existentes. Cualquier diagnóstico numérico nuevo debe tener configuración, identidad, presupuesto y criterio de clasificación explícitos antes de ejecutarse.

## Límites

No alterar baselines ni evidencia histórica, no relajar criterios para obtener PASS y no iniciar FULL_RPM_SWEEP ni campañas extensas. Los cambios del solver sólo podrían entrar como una identidad nueva, con regresiones y provenance. No se declara validación experimental sin datos independientes. No se inicia Etapa 2, 3 o 4 como objetivo general.

## Criterio

Cerrar como `VERIFIED`, `PARTIAL` o `BLOCKED` según evidencia: convergencia de malla y periodicidad deben medirse, no inferirse; conservación y consistencia deben superar contratos existentes; sweep readiness debe conservar gaps, hashes, presupuesto y autorización por separado de cualquier ejecución.
