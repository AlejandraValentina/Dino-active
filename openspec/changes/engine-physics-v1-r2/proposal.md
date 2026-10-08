# ENGINE_PHYSICS_V1_R2

This change is an explicit superseding offline gate for `ENGINE_PHYSICS_V1`.
The historical `ENGINE_PHYSICS_V1` gate remains `FAIL_TERMINAL` and is not
edited or reclassified. R2 does not represent a new physical campaign: it
reuses the four accepted periodic primary cycles already produced under the
same solver, models, fixtures, meshes, fuel, combustion, thermal model,
mechanical losses, RPMs, detector, thresholds and convergence streak.

The only changed layer is derived output/accounting semantics. R2 consumes the
corrected `SCAVENGING_PARTITION_CONSERVATION_V1` contract and the exact
periodic cycles A′3000 @ 73, A′4000 @ 88, B′3000 @ 34 and B′4000 @ 38.

Technical criteria are satisfied by the offline artifact, but the administrative
gate remains `REVIEW` until `EP-R2-EXTERNAL-REVIEW` is completed. No new campaign,
R3, KT100 work or full RPM sweep is authorized by this change.
