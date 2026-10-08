# Dynamic reed coupling V1 — component implementation record

The implementation follows the preregistration in
[`dynamic_reed_coupling_v1_preregistration.md`](dynamic_reed_coupling_v1_preregistration.md)
and commit `004b1841579497fe0e2273257be0104ccaa4abd2`.

`motorsim.reed_coupling.HingedFlapGeometryV1` validates the versioned linear
flap geometry, curtain-flow law, adjacent swept volumes, synthetic provenance,
and equality between pressure-force and swept-volume area. The independent
`DynamicReedTwoVolumeCouplingV1` advances two finite, well-mixed gas volumes,
four extensive P6 pseudo-species, and one `ReedPetal` in the same SSPRK2 stages.
The existing restriction relation supplies signed mass and donor enthalpy;
four-species fluxes use the actual donor on each stage. Pressure work is
transferred between the gas volumes and petal work, and damping is accumulated
as an explicit external reed heat sink. State and geometry are included in
versioned checkpoints with hashes and consistency gates.

The bounded component verification is `tests/test_reed_coupling.py` (9 tests),
plus `tests/test_reed.py` (17 tests): geometry/schema and mismatch rejection,
zero-lift/fixed point, both flow directions and species donors, mass/species/
energy ledgers, damping, transactional domain rejection, hash-checked exact
restart, configuration drift and existing standalone reed regression. It is a
two-0D-volume component test, not a full engine trajectory or periodic-cycle
campaign.

The `IntegratedEngine2T` binding remains incomplete: its intake endpoint is a
finite-volume duct cell with fixed mesh volume, while the synthetic component
uses two explicit moving adjacent control volumes. A subsequent stage-coherent
binding must declare how the reed displacement changes that endpoint cell's
effective volume, CFL width, species inventory and checkpoint/configuration
identity while preserving the P5-C global SSPRK2 transaction. Until then, the
component result does not claim integrated engine reed verification. It does
not use or qualify KT100 dimensions; no Fixture A/C, KT100, or P4–P8 campaign
was run for this component.

Review was a sequential adversarial self-review by the implementer. No
independent review artifact is claimed.
