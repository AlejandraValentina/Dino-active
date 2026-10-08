# Proposal: engine physics v1

## Intent

Deliver one auditable production path with explicit, versioned engineering
models for fuel, combustion, scavenging, heat transfer, mechanical losses and
derived outputs. The frozen R2 closure remains the reference baseline; this
change adds capability without rewriting or rerunning it.

## Acceptance

Two materially distinct synthetic configurations are each exercised at two
distinct RPM operating points through `IntegratedEngine2T`. Each point must
produce a durable result with real periodicity evaluation or an explicit
terminal classification, physical validity gates, conservation receipts,
runtime, model versions and provenance. The phase gate is
`ENGINE_PHYSICS_V1_PASS` only when all four points satisfy the contracted hard
gates and evidence requirements.

## Non-goals

No dynamic reed, carburetor, ANCAP or commercial-fuel claim, KT100, CFD
scavenging, resonance, oil chemistry, knock, emissions, multicylinder,
forced-induction, GPU/LTS/GUI work, full RPM sweep, P9 experimental validation,
or changes to frozen closure fixtures and thresholds.

