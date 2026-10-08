## ADDED Requirements
### Requirement: Configuración 4T independiente y persistente
El sistema SHALL conservar las entradas comunes y específicas 2T/4T independientes,
permitir válvulas incompletas sin valores inventados y guardar JSON v6 leyendo v1–v5.
SHALL implementar los dominios, seno cuadrado, área limitada y cruce periódico
analítico definidos en design.md, sin transformar texto inválido en ausencia.
#### Scenario: Proyecto antiguo o cambio de ciclo
- **WHEN** se abre v1–v5 o se alterna 2T/4T
- **THEN** conserva sus datos históricos y no inventa válvulas ni copia conductos 2T.
#### Scenario: Eventos geométricos
- **WHEN** existen entradas válidas
- **THEN** muestra eventos, alzada, área y cruce con período 720°, extremos exactos.
### Requirement: Modelo y aceptación numérica fijados
El sistema SHALL ejecutar el modelo aprobado I/C/E de design.md, nueve estados
m/U/F, cuatro enlaces, calor 350–390 una vez por 720°, sin K ni trabajo ficticio.
SHALL conservar perfiles, balances, convergencia, sensibilidad y presupuestos allí
especificados; auditar cada paso aceptado y preservar intentos/evidencia.
#### Scenario: Puertas numéricas
- **WHEN** A100 cumple, luego B100/C100 y su sensibilidad, y después C50/banda
- **THEN** continúa automáticamente la integración y protocolo acotado autorizado.
#### Scenario: Fallo previo
- **WHEN** falla una condición necesaria
- **THEN** no ejecuta dependientes ni cambia criterios; diagnostica y continúa lo independiente.
### Requirement: Integración compatible tras aprobación
El sistema SHALL reutilizar el proceso único, cancelación, snapshot, resultados,
comparación y barrido 2500–3500 de 2–5 puntos; declarar ciclo y rechazar comparación
2T/4T. Los resultados 4T contienen 1441 muestras por ciclo completo, sin W_K.
SHALL conservar lectura histórica y declaración externa de trabajo por 360/720°.
#### Scenario: Resultado y procedencia
- **WHEN** se calcula, cancela, falla, edita o reabre
- **THEN** conserva procedencia, protege el trabajo y no presenta curvas obsoletas como éxito.
### Requirement: Evidencia acotada y separada
El sistema SHALL registrar pruebas rápidas, ejecuciones numéricas, inspección Windows
150 % y aceptación manual separadas, dentro de hasta doce ejecuciones previstas y
720 segundos conjuntos; no atribuir validación experimental a casos sintéticos.
#### Scenario: Cierre del bloque
- **WHEN** se entrega el trabajo
- **THEN** informa evidencia, pendientes y commits locales, sin publicar ni archivar.

### Requirement: Aceptación numérica R2 explícita y trazable
El sistema SHALL preservar R1 y datos originales; evaluar R2 según la dispersión,
escalas y puertas definidas en la revisión R2 de design.md, sin confundir estabilidad
práctica con monotonía ni validación experimental.
#### Scenario: Reevaluación y continuación autorizada
- **WHEN** A/B/C conservados cumplen R2 y luego C50 cumple la comprobación de banda
- **THEN** habilita la integración 4T y continúa el protocolo con presupuesto acumulado.
#### Scenario: Datos incompletos o balances fallidos
- **WHEN** falta evidencia obligatoria o falla una condición conservada
- **THEN** no aprueba R2 aunque las diferencias entre perfiles sean pequeñas.
