# Diseño de trabajo: Etapa 1 científica

## Secuencia

1. Forensics read-only de receipts, configuraciones, tests y casos reproducibles de escape/ciclo; registrar qué magnitudes pueden compararse y qué límites/modelos son comunes.
2. Preparar un protocolo versionado para malla, periodicidad, balances y performance. Separar errores espaciales, temporales, de contorno, implementación y límites físicos. Usar sólo tolerancias de fuente justificable y no cambiar contratos históricos. Pre-registrar identidad, configuración, outputs, budget, checkpoints y clasificación antes de ejecutar nuevos diagnósticos.
3. Ejecutar sólo verificaciones acotadas permitidas por las especificaciones y el presupuesto operativo vigente. Si el protocolo no cabe en el presupuesto sin reducir resolución o criterios, detenerse y registrar el bloqueo.
4. Preparar el contrato de curva RPM: identidad completa, configuración inmutable, rango/step, WOT, fuel/AFR/loss explícitos, periodicidad y conservación por punto, outputs/unidades, persistencia, recursos, presupuesto y autorización. El contrato/preflight no ejecuta puntos.

## Controles

- Usar artifacts aislados y hashes actuales; rechazar identidades incompatibles.
- Reauditar primarias independientemente; no reemplazar auditoría por asserts del productor.
- No aceptar punto como periódico si la periodicidad no fue evaluada y satisfecha.
- Los outputs indefinidos, no convergentes o inválidos permanecen clasificados y con huecos.
- Las proyecciones de runtime no se presentan como mediciones de campaña.
- Los resultados exploratorios permanecen distintos de resultados verificados/validados.

## Dependencias

`DINO_DESKTOP_V3_1_VISUAL_PARITY` debe completar su gate de paquete antes de que las tareas de este change sean promovidas a READY. La cola durable en `program-status.json` controla la activación y las dependencias.
