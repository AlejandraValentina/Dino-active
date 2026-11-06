## Context
B1.1 ejecuta un único punto 4T con `FourStrokeExecution` y
`reference_run --project-input`. El worker también acepta `--sweep-input` y
`sweep.execute_sweep` ya es genérico: valida `{common_inputs, rpms}`, escribe
`series.json` y usa `reference_results.load_result` para cada punto. La curva
RPM 4T puede reutilizar ese contrato sin crear física ni formatos nuevos.

## Decisions
### 1. Barrido 4T sobre el contrato existente
`FourStrokeCurveExecution` construye `common_inputs` con
`reference_results.project_inputs(project, origin, rpm=rpms[0])`, valida los
RPM con `rpm_domain.validate_rpm(..., '4T')` y `sweep.plan_rpms`, y lanza el
worker con `--sweep-input`. El dominio 4T es 2500–3500 rpm y la serie admite
2–5 puntos, igual que el sweep 2T existente.

### 2. Lectura estricta de la serie
El adaptador lee `series.json` con `sweep.load_sweep`; esa función valida
identidad, hashes, manifiestos v4, estados y suma de tiempos. No se aceptan
series parciales como curvas completas.

### 3. UI acotada y separada
`FourStrokeCurvePage` agrega una tercera pestaña al modo 4T:
- inicio/fin/incremento con validación local;
- botón Calcular/Cancelar y estado del punto actual;
- tabla por RPM con estado, `W_C_J`, `p_max_Pa`, integración y manifiesto;
- gráfico `W_C_J` vs RPM y banner de referencia.

No hay comparación 2T/4T, ni variantes, ni estudios paramétricos en este
change. El proyecto 4T y su schema no cambian.

### 4. Aplicación de borradores
Antes de calcular, el shell aplica Geometría, Válvulas y Conductos con el
mismo criterio que la ejecución individual; un campo inválido bloquea la curva
con el error concreto.

## Alternatives considered
- **Curva en proceso con `execute_sweep`:** bloquea la UI y duplica el
  supervisor del worker. Se descarta.
- **Curva con un solver nuevo:** no aporta y rompe la reutilización del
  manifiesto v4. Se descarta.
- **Incluir variantes/estudios en el mismo change:** requiere decisiones de
  persistencia y contrato que no están en B1.1; se posponen.

## Risks / Trade-offs
- **Presupuesto:** `execute_sweep` acumula hasta 300 s de integración; la UI
  debe mostrar progreso y permitir cancelar.
- **Worker congelado:** si el ejecutable no incluye `reference_run`, el error
  debe ser claro y no producir una curva falsa.
- **Serie parcial:** un punto no convergido detiene la serie; la UI muestra el
  estado real y no completa los puntos restantes.
- **Etiqueta científica:** sigue siendo referencia 0D, sin claim predictivo ni
  validación experimental.

## Compatibility and verification
- 2T/V3, `FourStrokeContext`, proyecto 4T y manifiesto v4 intactos.
- Tests: request del adaptador, evento `sweep_finished`, carga de una serie
  válida/alterada, UI de curva y smoke real de tres puntos 2500/3000/3500.
- Cierre: `openspec validate --strict`, suite focalizada 4T/V3 y regresión de
  escritorio.
