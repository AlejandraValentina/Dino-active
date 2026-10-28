# E1.0 — evidencia de la ley de lumbreras

**Estado:** candidato V2 con soporte numérico dentro de su dominio ensayado; ley de pérdidas real no identificada. Disposición: **mantener V2 experimental y opt-in**. No cambia rc7, el default legacy ni MUSCL.

## Evidencia reutilizada

- La revisión de flujo decide **CORREGIR** el uso del Riemann escalado como ley general de restricción cámara–garganta–conducto. No encontró defecto en HLLC interior ni doble aplicación de Cd.
- La V2 de tobera ideal equivalente pasó 1008 estados algebraicos en siete ramas. La comparación de ingeniería ya registrada incluye 100 estados analíticos compatibles y cuatro casos dinámicos; error relativo máximo de flujo `6.636728122871094e-13`, con conservación y replay registrados.
- V1 soportó 971 de 1008 estados y conserva 37 estados no soportados; sigue `ADOPTION_BLOCKED_DOMAIN` y deshabilitada en el modelo integrado.
- La referencia de restricción quiescente registra 1029 pruebas, pero su contrato no incluye momento del conducto ni compatibilidad acústica.
- El A/B de escape existente cerró como **DIFERENCIA NO RESUELTA**. La referencia A9000 es un derivado funcional y no una medición del mismo motor.

## Alcance y límite

Las pruebas sustentan consistencia matemática, conservación y comportamiento numérico de contratos idealizados. No identifican Cd/pérdidas de un puerto real, separación de chorro ni respuesta pulsante medida. Tampoco respaldan potencia absoluta, independencia de malla, validación experimental o predicción de cambio de diseño.

Por tanto, se conserva V2 como candidato experimental opt-in; V1 no se promueve; rc7/default legacy y MUSCL permanecen intactos. La identificación física requiere datos medidos de flujo de la geometría pertinente; la validación del motor requiere además entradas completas del mismo motor, salidas independientes e incertidumbre defendible. El bloqueo X30 y la falta de datos completos persisten.

## Proveniencia

Las huellas SHA-256 de los siete artefactos fuente y los mismos hallazgos estructurados constan en [port-law-evidence-matrix-v1.json](port-law-evidence-matrix-v1.json). Las pruebas citadas son los conteos archivados en los recibos originales; esta entrega documental no repitió campañas ni suites históricas.
