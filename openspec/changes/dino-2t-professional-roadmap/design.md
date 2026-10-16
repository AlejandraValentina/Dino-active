# Diseño propuesto: DINO 2T hacia simulador profesional

## Orden y dependencias

1. **Confianza física y numérica.** Resolver primero verificación del modelo y del método, incluida la independencia espacial/temporal del escape y la periodicidad donde se pretendan métricas de ciclo. Mantener separadas verificación, plausibilidad y validación experimental. Definir claims por dominio y límites conocidos.
2. **Curvas RPM.** Reutilizar el runner convencional IMPL2 y sus checkpoints, aislamiento, hashes y auditoría. Antes de una campaña, resolver blockers científicos de la Etapa 1, fijar configuración/fuel/AFR/pérdidas explícitos, preregistro, workers y presupuesto global. Reportar cada punto con clasificación; no rellenar huecos.
3. **Diseño integrado y diagnóstico.** Reutilizar editores, variantes y comparación existentes. Enlazar diagnósticos sólo a señales efectivamente generadas por el solver y a diferencias reproducibles; las hipótesis deben rotularse como tales.
4. **Exploración/optimización y preparación comercial.** Reutilizar importación de mediciones, workflow, resultados y empaquetado. Añadir optimizador versionado, función objetivo/restricciones declaradas, partición ajuste-validación independiente, incertidumbre y trazabilidad. No afirmar exactitud comercial sin validación suficiente.

## Dependencias transversales

- Identidad inmutable de configuración, solver, modelos, evidencia y artifacts por implementación.
- Clasificaciones explícitas para convergencia, periodicidad, no convergencia, invalidez y métricas no definidas.
- Checkpoint/restart compatible y auditabilidad independiente.
- Presupuesto agregado y plan de reanudación para cualquier campaña.
- Separación entre resultados sintéticos/exploratorios y mediciones experimentales.
- Ningún cambio a gates o tolerancias históricos para obtener aceptación.

## Camino mínimo hacia una curva HP/torque calculada

1. Resolver la aceptación del runner/implementación y de la identidad IMPL2 sin reutilizar artifacts v1 incompatibles.
2. Definir un rango acotado, configuración única, WOT, combustible, AFR y modelo mecánico explícitos; registrar preregistro y presupuesto.
3. Demostrar que el modelo numérico aplicable puede sostener una solución periódica y suficientemente independiente de resolución para el claim elegido. La evidencia actual de escape no lo demuestra.
4. Ejecutar cada RPM autorizado con el pipeline convencional, auditoría independiente y conservación; publicar torque/potencia sólo si el contrato los define y los puntos pasan sus condiciones. Marcar fallos y puntos ausentes como tales.
5. Presentar la serie como **curva de predicción de ingeniería** con identidad, supuestos e incertidumbre. Para llamarla validada experimentalmente, comparar con un dinamómetro trazable en puntos no usados para calibración.

Los receipts históricos hacen que esta ruta sea un plan, no una afirmación de readiness actual: V1 está PARTIAL, la campaña IMPL2 no fue iniciada en su receipt de readiness y la convergencia de malla del escape sigue sin establecerse.

## Gates futuros propuestos

- **Etapa 1:** matriz de verificación analítica/referencia por subsistema; balances y replay dentro de tolerancias justificadas; periodicidad evaluada donde corresponda; estudio espacial y temporal separados; límites, identidades y fallos persistidos. Validación experimental se reporta aparte y sólo con dataset trazable.
- **Etapa 2:** contrato/preregistro por campaña; preflight de todas las configuraciones; todos los puntos clasificados y auditados; resultados derivados sólo de ciclos aceptados; manifest reproducible con hashes, recursos y costos. Una curva puede cerrar como parcial si hay puntos fallidos, pero no como completa.
- **Etapa 3:** cambios de diseño propagados hasta la configuración nativa; comparaciones bajo condiciones controladas; diagnósticos ligados a observables y repetibilidad; ninguna explicación heurística se presenta como hecho demostrado.
- **Etapa 4:** optimización determinista/reproducible con constraints explícitos; persistencia de candidatos y corridas origen; calibración y evaluación en conjuntos separados; incertidumbre y extrapolaciones documentadas; paquete reproducible. Claim comercial sujeto a validación externa apropiada.

## Esfuerzo relativo

| Etapa | Esfuerzo | Motivo principal |
|---|---|---|
| 1. Confianza física | Muy alto | Resolver validez numérica y alcance físico; la malla/convergencia del escape es un blocker medido. |
| 2. Curvas RPM | Medio-alto | Infraestructura ya existe, pero hacen falta readiness científica, presupuesto global, campaña autorizada y puntos válidos. |
| 3. Diagnóstico | Medio | UI y sensibilidad acotada existen; falta sostener conclusiones causales con resultados aceptados. |
| 4. Optimización/comercial | Alto | Optimizador, calibración identificable, incertidumbre y validación independiente no están cerrados como capacidad integrada. |

## Riesgos y controles

- Confundir conservación con exactitud física: exigir verificación/validación separadas.
- Interpretar periodicidad como validación: reportar ambas por separado.
- Ajustar el modelo al mismo dataset usado para aceptación: reservar datos independientes.
- Modelos de combustión/pérdidas sintéticos: conservar provenance y restringir claims.
- Reutilizar artifacts de otra identidad: rechazo fail-closed por hashes.
- Proyección de runtime basada en microbenchmark: etiquetar estimados y limitar invocaciones.
- Convertir puntos faltantes en curvas continuas: conservar gaps y no interpolar.
