# Two-stroke v1 closure

MotorSim has reusable gas-dynamic, four-pseudo-species, thermal, mechanical,
and evidence components, but no accepted integrated 2T v1 gate. Historical
fixtures A/C are invalid for such a claim: they start depressurized and use
legacy/open boundary behavior; P7 is prescribed bookkeeping heat, not
fuel-coupled chemistry. This change defines a finite, auditable single-cylinder
2T closure contract and the minimum new versioned capability required to
qualify two distinct synthetic fixtures.

The gate is limited to one-cylinder 2T engine-cycle simulation. P4–P9 and their
historical evidence remain unchanged. KT100, dynamic reed, the existing
extensible Fuel Library, and all listed advanced product features are outside
the closure claim. Existing fuel/P7/reed components remain available under
their existing identities and are not silently reinterpreted.

Success requires frozen `FIXTURE_A_PRIME` and `FIXTURE_B_PRIME` definitions,
pre-registered mesh and campaign contracts, independently auditable primary
evidence, and all acceptance gates in the companion specification. Otherwise
the terminal result must state the exact failed or incomplete gates without
extending a horizon or relaxing a criterion.
