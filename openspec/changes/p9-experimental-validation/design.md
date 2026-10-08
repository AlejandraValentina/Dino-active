# Diseño — P9 v1.0

El contrato fuente es `docs/gasdynamic/p9_v1_user_contract_20261001.md`,
MotorSim P9 v1.0 proporcionado por la usuaria el 2026-10-01 (SHA-256
`104a8e6b587af8e6c7fa6f1eb6c1fc2e68979e5fa3d6ebb644d7914795f1b168`). Esta
transcripción preserva sus gates. No se derivan métricas ni
umbrales de los resultados existentes. La fecha y commit de preregistro se
registran en `results/p9-readiness-20261001/preregistration.json` después de
validar y congelar esta especificación, antes de leer datos experimentales.

La secuencia contractual es: dataset congelado y configuración identificada;
simulación congelada; P9-A para cada punto; alineación por RPM sin corrimiento;
reducción de ambos lados a la misma magnitud indicada; auditoría offline de
evidencia primaria; evaluación de gates y clasificación. Ningún resumen
almacenado constituye autoridad. La información experimental original nunca se
sobrescribe y toda transformación se guarda por separado.

El dataset debe documentar la procedencia y metodología de las magnitudes
derivadas. En particular, el trabajo indicado se define como `∮ p dV`; cuando
se utilice una traza de presión, los datos, la geometría, el cero TDC y el
procesamiento experimental deben permitir reconstruirlo sin alinear contra el
resultado de MotorSim. No se incorpora filtrado, corrección angular o ajuste
post-hoc. Si los metadatos no determinan la operación, el punto queda
INCONCLUSIVE y no se inventa un método tras observar la comparación.

No hay dataset de P9 disponible en el workspace revisado. Por ello este cambio
preregistra el contrato y sus gates; no implementa un adaptador dependiente de
un formato experimental aún desconocido, ejecuta campañas, modifica el solver,
ni hace calibración. Tras recibir datos, cualquier código requerido debe
reconstruir los gates desde evidencia primaria y agregar las pruebas negativas
del contrato.

P8 puede reutilizarse solo como evidencia numérica histórica y referencia de
provenance/configuración. Sus anchors son transitorios sintéticos; no califican
estado periódico ni constituyen observaciones experimentales.
