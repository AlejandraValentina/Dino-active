# Moving-cell heat conservation correction — SELF_REVIEW

## Demonstrated implementation defect

At a dynamic-reed endpoint, the energy variable is density and the extensive
energy is E = e Vstage, where Vstage = Vreference + swept_area * lift.
The prescribed Newton heat transfer Q = h A (Tgas - Twall) is already watts.
The old density source -Q/Vreference therefore applied -Q Vstage/Vreference
to extensive energy, while the heat ledger recorded Q. This is a first-law
implementation error, not a change to a heat correlation or wall parameters.

An independent difference of otherwise identical thermal/nonthermal RHSs
isolates that term without flow, reed-work or pressure terms. Tests span zero,
0.5 and 1.5 mm lift, with heat entering and leaving the gas. Zero-lift controls
passed before the correction; four moving-source checks and two integrated
conservation checks failed. The source excess was 5% or 15%, exactly the actual
volume increase. For four 1e-7 s steps at 1 mm lift, old energy residuals were
-1.00014e-7 J (250 K wall) and +1.99983e-7 J (400 K wall).

## Correction and verification

Use the actual stage volume from `_duct_cell_volume` in the heat density RHS.
No heat coefficient, temperature, equation, CFL, tolerance or detector changed.
The same helper already defines the moving-cell extensive conversion. Static
cells return their original mesh volume, preserving that numerical operation.
All eight focused independent source/conservation/checkpoint tests now pass;
the post-correction numeric residuals and source checks are recorded in
`moving-cell-heat-receipt-v1.json`. The broader thermal/dynamic-reed integrated
selection passes 15 checks. No power prediction was recalibrated.

The current primary-evidence source identity changes, as required. Historical
checkpoint and result identities remain untouched. A native checkpoint checks
configuration identity, not source identity: the static reference checkpoint
remains restorable with the new source. By contrast the full primary-evidence
auditor binds source hashes and must use the recorded producer to audit historical
rows. No guard is bypassed. Restoring a physical state is not a claim to reproduce
its historical trajectory; in the corrected moving-cell thermal combination a
continuation is new evidence under the corrected source, not an identical replay.
CRV1 rc7 package remains untouched. The preceding A9000 diagnostics use a static
reed and therefore did not activate this erroneous moving-cell combination;
their evidence is retained with the original source hash.

This verifies conservative application of an assigned heat rate. It does not
identify the physical h/Twall values, validate a heat-transfer correlation or
establish real-engine predictive accuracy.
