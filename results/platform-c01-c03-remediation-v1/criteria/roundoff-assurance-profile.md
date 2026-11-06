# Prospective result-assurance admission profile

`DINO4T_ROUNDOFF_ASSURANCE_PROFILE_V1` reuses the exact strict `< 1e-12`
maximum relative mass/energy/element closure bound already asserted in
`tests/test_dino4t_engine.py:41-45` and `tests/test_dino4t_stage2.py:132,193`.
This profile is fixed before its decisive post-remediation tests. It changes
neither the periodicity detector nor any calculated value or physical equation.

It is an application admission profile for the registered native engineering
assurance scope, not a previously established universal V1 numerical guarantee
or predictive accuracy target. A result outside the profile retains its raw
status, data, hashes and history, but receives `INELIGIBLE_INTEGRITY`. Extending
admission to a different justified error/roundoff scope requires a new recorded
profile; it is not done after observing a desired result.

The result validator also recomputes the existing native postprocessing
identities (work/IMEP, FMEP at actual p_max and piston speed, net IMEP minus FMEP,
4T power and torque) with the existing identity-test tolerance 1e-12. Signed
finite coefficients are accepted when their actual loss is valid; loss is
never clamped. This checks internal data consistency, not model validity.
