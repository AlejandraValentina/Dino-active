# P8 wide-RPM indicated performance

## Human authorization

On 2026-09-27 the supervisor authorizes only the P8 correction in this change.
P4 remains `BLOCKED / NOT_GRANTED`; P9, experimental validation, publication,
packaging and supervisor infrastructure remain unauthorized.

## Scope

Each integer anchor 2500, 5000, 8000, 11000 and 15000 rpm executes exactly two
deterministic, unmeasured preparation cycles from 180 to 900 degrees with the
frozen P5-C/P6 topology and P7 disabled. The state is then rebased from 900 to
180 only because geometry is exactly periodic, accounting is reset, and exactly
one 360-degree measured cycle from 180 to 540 runs with P7 enabled.

Preparation is a fixed transient, not periodic convergence or a steady-state
claim. Evidence retains `steady_state=false`,
`periodic_convergence=NOT_GRANTED_BY_P4`, `conditional_on_p4=true`,
`experimental_validation=NOT_PERFORMED` and
`independent_review=INDEPENDENT_REVIEW_PENDING`.
