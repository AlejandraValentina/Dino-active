# Design

The preparation is exactly two unmeasured 180->900 cycles with P7 disabled and
zero prescribed heat/burn. The physical gas and species state is preserved,
then the angle is rebased 900->180 and measurement histories, ledgers and
counters are reset. A test proves volume, volume-rate and port-area equality and
that the rebase does not change the physical state.

One shared `build_event_cuts` builder is used by preparation, measured execution
and restart continuation. It repeats authoritative `Model(case).events` as
`phase + 360*k` over the whole absolute interval. The measured and restart paths
also cut exactly at P7 350/390 and at the restart probe 370; preparation has no
P7 cuts because P7 is disabled. No fixed-angle stepping is used.

The measured window is exactly one 360-degree cycle and one P7 event. Every run
uses `omega_deg_s = 6 * rpm`, `t_cycle = 60 / rpm`, CFL 0.4 and the complete
atmosphere-intake-crankcase-transfer-cylinder-exhaust-atmosphere topology.
P7 source hooks are zero outside 350..390. The accepted P7 heat ledger is
reconciled to the gas accounting record without changing the burn law.

Global residuals use stored-topology external exchange = intake into the stored
system minus exhaust outflow; internal interfaces cancel. Energy closure also
includes accepted P7 heat and both chamber `-p*dV` terms. Nonzero residuals are
reported and gated; they are not hidden by tolerance changes.

The evidence records `steady_state=false`,
`periodic_convergence=NOT_GRANTED_BY_P4`,
`metric_semantics=BOUNDED_TRANSIENT_INDICATED`, `conditional_on_p4=true`,
`experimental_validation=NOT_PERFORMED`, and
`independent_review=INDEPENDENT_REVIEW_PENDING`. P4 remains blocked and P9
remains stopped.
