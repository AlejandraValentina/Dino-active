## ADDED Requirements

### Requirement: P4-C3-R5 approved audit contract
The C3-R5 diagnostic path SHALL preserve the frozen product equations and SHALL
evaluate A, B0, B1 and B2 only from one declared focal acquisition. C3 SHALL
remain `P4_SCI_C3_INCONCLUSIVE` before that acquisition is executed.

#### Scenario: Missing or mixed evidence
- **WHEN** evidence is missing, runtimes differ, or any persisted binary64
  identity differs
- **THEN** the result is `INCONCLUSIVE` and no accidental `PASS` is emitted;
  a physical or semantic contradiction is `FAIL`.

#### Scenario: Solver completion evidence
- **WHEN** `solver_status` is `completed`
- **THEN** the acquisition SHALL contain finite numeric `solver_time` and
  `target_final_time`, with `solver_time >= target_final_time`; missing,
  non-finite, or truncated completion evidence is `INCONCLUSIVE`.
- **WHEN** the solver status explicitly reports a solver failure
- **THEN** the physical result is `FAIL`; timeout or otherwise incomplete
  evidence without an explicit solver failure remains `INCONCLUSIVE`.

#### Scenario: Malformed persisted audit evidence
- **WHEN** persisted A/B0/B1 faces, flux vectors, waves, or related fields are
  missing, short, non-numeric, or otherwise malformed
- **THEN** the audit SHALL return `INCONCLUSIVE` without raising an exception;
  a valid semantic `fallback_reason` contradiction remains `FAIL`.

### Requirement: C3-R5 identity gates
The auditor SHALL select A internally from the same acquisition history as the
first `mass_flux > 0` record whose `sample_time_pre_step` lies in
`[0.5,1.5] * expected_return_time`; external `gate_a`/`return_record` fields
SHALL NOT authorize A. The auditor SHALL consume the same persisted reconstructed
interface pair for the A HLLC/ExactRiemann comparison. B0 SHALL independently reconstruct every
momentum face for both SSPRK2 stages without importing or calling product
`reconstruct()`, and SHALL require exact face and downgrade identity. B1 SHALL
independently evaluate HLLC/HLLE on those literal faces and require exact full
flux-vector, wave and fallback-reason identity. B2 SHALL independently replay
`p_i*(A_R-A_L)`, momentum RHS, both stage updates and
`q_new=0.5*q0+0.5*q2` bitwise at declared checkpoints.

#### Scenario: Diagnostic parity
- **WHEN** A/B0/B1/B2 pass, `0 <= max_global_resid <= 1e-10`, and solver status is
  `completed` under the same runtime and acquisition
- **THEN** the auditor may classify C3 `P4_SCI_C3_PASS`; HLLC-vs-Exact
  magnitudes and control-volume residuals remain diagnostic only.

### Requirement: Puerto ideal conservativo
El camino experimental SHALL usar Aeff=min(Aport,Apipe), Cd1, ley geométrica
existente y un único flujoP3, con pared reflectiva sobre área complementaria.
#### Scenario: Puerto cerrado
- **WHEN** Aeff=0
- **THEN** el intercambio m/E/F es exactamente0 y el tubo ve paredP2.
### Requirement: Gates físicos ordenados
P4 SHALL verificar E01–E05 antes del motor y E06–E11 antes de P4C; E12–E15
requieren conservación, convergencia periódica, comparación y admisibilidad.
#### Scenario: Fallo de contrato o frontera
- **WHEN** hace falta nueva semántica científica
- **THEN** conserva evidencia y detiene los dependientes sin modificarP0/P2/P3.
### Requirement: Conservación y cierre
P4 SHALL conservar ledger combinado, eventos geométricos, CFLporstage,
regresiones históricas y revisión independiente; nunca iniciarP5 automáticamente.
#### Scenario: Prueba costosa
- **WHEN** una prueba supera600s
- **THEN** detiene y perfila antes de nuevas campañas largas.


### Requirement: G2-v2 preregistered horizon delta
The G2-v2 evaluation SHALL preserve every existing E13 metric, threshold, branch,
streak, solver, mesh and physical criterion, changing only the maximum horizon to
400 cycles. The historical max-30 G2 result SHALL remain retained as evidence.

#### Scenario: Frozen decision boundary
- **WHEN** both period-2 branches reach their existing streak contract before cycle 400
- **THEN** evaluation stops at the first qualifying cycle and records PASS
- **WHEN** cycle 400 is reached without convergence
- **THEN** evaluation records FAIL without extending the horizon or changing thresholds
- **WHEN** continuation identity or evidence is invalid/incomplete
- **THEN** evaluation records INCONCLUSIVE without treating the condition as scientific FAIL
