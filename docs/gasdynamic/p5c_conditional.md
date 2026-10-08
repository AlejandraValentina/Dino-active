# P5-C bounded integration

P5-C composes the existing P5-B intake/crankcase/transfer/cylinder fixture with
the existing P4 exhaust port and finite duct. It is a bounded verification path,
not a periodic engine campaign. The result is
`P5_C_INTEGRATED_GASDYNAMIC_VERIFIED_CONDITIONAL` and every exhaust-dependent
claim is `CONDITIONAL_ON_P4`.

P4 remains `P4_FINAL_BLOCKED_C3_INCONCLUSIVE`, with acceptance `NOT_GRANTED`.
No P4 threshold, evidence, solver or historical conclusion was changed. The
fixture bank covers closed ports, retained P5-B coupling, exhaust coupling, a
full short update, restart and deterministic replay. Evidence is recorded in
`results/p5c-conditional-20260924/evidence.json`.
