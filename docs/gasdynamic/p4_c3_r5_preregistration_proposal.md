# P4-C3-R5 — APPROVED CONTRACT / NO ACQUISITION EXECUTION

Fecha: 2026-09-28
Base técnica: `a6981b73773e3f0e60440a605c39aef83c012d31`
Autoridad aprobatoria: `HEAD 86005373`; aprobación humana explícita: 2026-09-28.

## Estado

C3 permanece `P4_SCI_C3_INCONCLUSIVE` hasta una única adquisición focal R5.
Este documento es ahora el recibo del contrato aprobado: no cambia física,
solver, malla, CFL, criterios aceptados ni resultados históricos. Autoriza la
implementación de instrumentación/auditoría y la revisión técnica posterior,
pero no ejecutar C3-R5 ahora. E13/G2 sigue `NOT_EXECUTED` y P9 `STOPPED`.

El objetivo es fijar antes de cualquier nueva adquisición cómo cerrar las dos
deudas de C3 sin introducir tolerancias post-hoc:

- A: consistencia del retorno frente a la referencia ExactRiemann;
- B: identidad discreta del transporte de momentum durante SSPRK2.

## Autoridad existente reutilizada por A

P1 exige que la referencia Riemann exacta sea independiente del solver
aproximado, con raíz de presión de residuo relativo `<=1e-12`. SCI-04A/C1
documenta además la implementación `ExactRiemann` con residual interno
`<1e-13*scale`.

SCI-03/SCI-04A ya establece que HLLC es aproximado: los errores de magnitud
frente a ExactRiemann se registran, pero no existe una igualdad universal de
flux como gate. C1 fue verificado por dirección correcta, ondas ordenadas,
admisibilidad, ausencia de fallback inesperado y conservación, manteniendo las
diferencias HLLC-vs-Exact como diagnóstico.

## Gate A — retorno cualitativo contra ExactRiemann

A reutilizaría explícitamente la semántica ya verificada por C1 sobre el
snapshot causal de retorno de C3. HLLC auditor y ExactRiemann MUST consumir
exactamente el mismo par de estados de cara reconstruidos y persistidos.

La selección causal R5 se realiza dentro del auditor sobre la misma `history`: se
toma el primer registro con `mass_flux > 0` cuyo `sample_time_pre_step` cae en la
ventana preregistrada `[0.5, 1.5] * expected_return_time`, preservando la regla
de R4. No se acepta un `return_record` externo como autoridad de A.

A PASS requeriría simultáneamente:

1. snapshot de retorno seleccionado por la ventana causal preregistrada;
2. estados de cara finitos y admisibles;
3. referencia ExactRiemann válida bajo el criterio ya autorizado;
4. ondas HLLC y exactas ordenadas bajo su semántica correspondiente;
5. misma dirección de retorno para flujo másico, `SM` HLLC y `u_star` exacto;
6. mismo tratamiento productivo/auditor de fallback, sin fallback inesperado;
7. procedencia durable de estados, flujo productivo y diagnósticos.

Las diferencias de `p_star`, flujo másico, momentum, energía y especie entre
HLLC y ExactRiemann se conservan y reportan, pero son diagnósticas. Esta
propuesta no introduce un límite porcentual ni un error máximo nuevo.

Aplicar la semántica C1 al snapshot de retorno C3 requiere autorización humana
de alcance; no requiere inventar un threshold de magnitud.

## Gate B0 — reconstrucción independiente

B0 se amplía desde las caras exteriores a todas las caras necesarias para el
replay de momentum en ambas etapas SSPRK2. La ruta auditora MUST reconstruir
sin importar ni llamar al `reconstruct()` productivo.

Producción persistiría únicamente evidencia diagnóstica de los estados de cara
realmente usados y la lista real `down`/`downgraded_cells`; no se derivarán
metadatos productivos inexistentes.

B0 PASS requeriría identidad exacta de floats entre:

- estados de cara persistidos por producción;
- estados obtenidos por la reconstrucción auditora;
- `downgraded_cells` productivos y los obtenidos independientemente.

Cualquier diferencia bloquea B1/B2. No existe tolerancia ULP para B0.

## Gate B1 — paridad exacta HLLC/HLLE

Para cada cara usada por el RHS de momentum de stage A y stage B, producción
persistiría como diagnóstico:

- vector completo de flux HLLC/HLLE;
- velocidades de onda;
- `fallback_reason`.

B1 recalcularía esas cantidades mediante `reference/hllc_audit.py`, sobre los
estados B0 literales. La implementación auditora permanece separada del HLLC
productivo.

B1 PASS exige igualdad exacta de los floats del vector de flux, velocidades de
onda y reason. La regla es deliberadamente conservadora: si existe incluso una
diferencia de redondeo, B1 no pasa y C3 continúa inconcluso hasta revisión.

No se permite relajar posteriormente a N ULP porque una corrida haya fallado.
La paridad exacta es una identidad de implementación, no un criterio de
precisión física HLLC-vs-ExactRiemann.

## Gate B2 — replay exacto del momentum SSPRK2

B2 no usaría un threshold físico ni un residual elegido por escala. Una vez que
B0 y B1 acrediten que el auditor reproduce exactamente los inputs y fluxes
productivos, una segunda ruta reproducirá únicamente la ecuación discreta de
momentum.

Para cada celda y ambas etapas se conservarían los inputs diagnósticos mínimos
para localizar una discrepancia, sin alterar el update productivo. El auditor
recalcularía independientemente:

- fuente geométrica `p_i*(A_R-A_L)`;
- RHS de momentum por celda;
- stage 1 `q1 = q0 + dt*rhs0`;
- stage 2 provisional `q2 = q1 + dt*rhs1`;
- combinación final SSPRK2 `q_new = 0.5*q0 + 0.5*q2`.

B2 PASS requiere igualdad bit a bit del momentum por celda en los checkpoints
reproducibles definidos antes de ejecutar. El residual de volumen de control
`observed_delta - predicted_delta` sigue calculándose y guardándose, pero deja
de ser el criterio de aceptación.

Esto evita derivar un bound `gamma_n` incompleto, evita modelar `math.fsum` como
una suma ordinaria y evita ocultar una discrepancia estructural dentro de una
cota de redondeo amplia.

Si la operación productiva y el replay independiente usan aritmética distinta
y por ello no pueden coincidir bit a bit, el gate queda inconcluso; no se
introduce una tolerancia después de observar la diferencia.

## Lógica de decisión propuesta

`P4_SCI_C3_PASS` solo podría existir si, bajo una revisión aprobada del
contrato, todos los siguientes gates están acreditados en una única adquisición
focal:

- retorno causal seleccionado internamente por la regla preregistrada;
- conservación global `0 <= max_global_resid <= 1e-10` bajo el criterio P4/C2 ya
  vigente, `solver_status == completed`, y evidencia finita de
  `solver_time >= target_final_time`;
- A PASS bajo la semántica cualitativa C1 reutilizada;
- B0 PASS por identidad de reconstrucción;
- B1 PASS por paridad exacta HLLC/HLLE;
- B2 PASS por replay exacto SSPRK2 de momentum.

Un FAIL físico/semántico sigue siendo FAIL. Evidencia faltante, truncada o
malformada, diferencia de implementación o imposibilidad de demostrar identidad
permanece INCONCLUSIVE; sólo un fallo explícito del solver se clasifica como
fallo físico de solver. Nada de lo anterior se convierte en PASS mediante
tolerancia posterior.

## Implementación permitida solo después de aprobación

La implementación R5 quedaría limitada a instrumentación y auditoría:

1. ampliar captura diagnóstica de caras/fluxes de stage A y B;
2. ampliar reconstrucción independiente B0 a las caras requeridas;
3. aplicar B1 exact-parity sobre HLLC/HLLE y fallback;
4. implementar replay B2 separado del solver productivo;
5. añadir microtests de independencia, mutación y fallback;
6. revisar que `p4_sci_04b.py` conserve idénticas ecuaciones, CFL y estados;
7. ejecutar solo después una adquisición focal C3-R5 previamente autorizada.

No se modifica la física del motor, no se calibra HLLC y no se reabre P8.

## Recibo de decisión humana — aprobado 2026-09-28

La usuaria aprobó conjuntamente, sin modificar el alcance científico:

1. reutilizar en C3-A la semántica cualitativa ya aceptada de C1;
2. adoptar igualdad bit a bit como gate conservador B0/B1;
3. adoptar replay bit a bit del update de momentum como gate B2;
4. autorizar la instrumentación R5 y, tras revisión técnica, una única corrida
   focal C3 bajo esos criterios congelados.

Hasta la adquisición focal autorizada en una tarea posterior:

- C3 = `P4_SCI_C3_INCONCLUSIVE`;
- P4 = `BLOCKED / NOT_GRANTED`;
- E13/G2 = `NOT_EXECUTED`;
- P9 = `STOPPED / NOT_AUTHORIZED`.

La aprobación no es un resultado de C3 ni autorización para lanzar la adquisición
en esta tarea. Hasta ejecutar esa corrida, C3 se mantiene `INCONCLUSIVE`.

## Vinculación de runtime y evidencia durable

Los gates de identidad bit a bit B0/B1/B2 son deliberadamente dependientes del
runtime declarado por la evidencia: versión de Python, plataforma/arquitectura,
`sys.float_info` y hashes de las implementaciones productiva y auditora. Un
cambio de runtime invalida la reutilización automática del gate; no autoriza
introducir una tolerancia.

Para evitar duplicar arrays completos, la instrumentación MAY persistir una
codificación canónica IEEE-754 binary64 de estados, fluxes y ondas, junto con
conteo y SHA-256. El auditor reconstruye y codifica la misma secuencia. Igualdad
de hash acredita identidad práctica de la secuencia; cualquier diferencia
bloquea el gate. Los estados exteriores seleccionados y métricas físicas siguen
guardándose en forma legible. No existe distancia entre hashes ni equivalencia
aproximada.
