# Prioridades posteriores a CRV1

Commercial Readiness V1 permanece congelada como la baseline funcional TRIAL rc7 aceptada el 2026-10-26. El orden conserva la prioridad acordada. Performance V2 fue autorizado explícitamente después de esta nota y queda registrado como objetivo vigente; las prioridades posteriores no se inician automáticamente.

1. **Rendimiento práctico (objetivo autorizado: Performance V2).** Reducir el tiempo necesario para obtener curvas periódicas con medición y perfiles reproducibles, sin cambiar ecuaciones físicas ni degradar precisión, CFL, tolerancias o criterios de aceptación. Empezar por diagnóstico de cuellos de botella y objetivos de rendimiento acotados; optimizar solo preservando equivalencia numérica demostrable.
2. **Precisión física (condicional).** Reanudar la calibración/validación del IAME X30 únicamente al recibir los parámetros geométricos indispensables del cárter: volumen libre con ángulo de referencia y fronteras/inclusiones claramente definidas, con fuente y trazabilidad. No sustituirlos por supuestos arbitrarios ni ejecutar el punto X30 antes de aceptar esos datos y reactivar el objetivo.
3. **Madurez comercial (según evidencia de uso).** Abordar problemas funcionales demostrados por usuarios de Dino Desktop, de manera acotada y sin reconstruir CRV1. No abrir mejoras de interfaz por anticipado.

La campaña completa RPM permanece aplazada y no es la prioridad actual; sus resultados existentes y clasificaciones se conservan. La evidencia científica y los gates históricos no se reescriben por esta decisión administrativa.

## Baseline CRV1 aceptada

La identidad, commits, hash del paquete, recorrido funcional, regresiones y limitaciones están registrados en [la ficha de baseline](../releases/dino-commercial-readiness-v1-baseline.md) y en el [recibo de aceptación](../../results/dino-commercial-readiness-v1/acceptance/receipt.json). La baseline es funcional TRIAL, no una validación experimental, predictiva, científica ni comercial.

## Control de almacenamiento

El preflight fail-closed forma parte de los entry points de build Windows (`packaging/build_windows.py`) y de la campaña RPM (`scripts/full_rpm_sweep_v1_campaign.py`). Se verifica antes de crear outputs o escribir procedencia de campaña. Los artefactos e históricos existentes no se limpian ni trasladan como parte de este registro.
