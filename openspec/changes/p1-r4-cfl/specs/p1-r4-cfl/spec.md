## ADDED Requirements
### Requirement: Congelación y métrica
El estudio SHALL preservar implementación y contratos anteriores y documentar
A=max(p_i-p0), diferencia absoluta dividida por10Pa y origen práctico de0,08.
#### Scenario: Reproducción contractual
- **WHEN** se repite N800 con los tres CFL originales
- **THEN** compara resultados deterministas excluyendo solo runtime.
### Requirement: Refinamiento independiente
El estudio SHALL ejecutar N400/800/1600 con los tresCFL y referencia diagnóstica0,1,
con igualtiempo, registrando conservación, admisibilidad, costes y comparaciones.
#### Scenario: Diferencia de amplitud
- **WHEN** cambia la amplitud sin pérdida de admisibilidad
- **THEN** registra sensibilidad sin llamarla por sí sola inestabilidad.
### Requirement: Revisión condicionada
Una enmienda R4 SHALL requerir evidencia convergente, límite cuantitativo justificado
y revisión independiente; SHALL preservar los contratos anteriores y no ajustar0,08
solo para aprobar elresultado observado.
#### Scenario: Tendencia no convergente
- **WHEN** la sensibilidad no disminuye o CFL0,6 cambia de límite
- **THEN** emite estado no acreditado y conservaP2Abloqueado sinP2B/P3.
