# Design

Use `motorsim.duct_network` with `gas1d.mesh.segments_mesh` and `coupling.interface_flux`. Port orientation is explicit and zero area is an exact closed interface.
# P5-C bounded integrated topology

The integration is a single deterministic SSPRK2-style update over the existing
P5-B finite intake/transfer topology plus one finite exhaust path. Interface
fluxes are resolved once per stage and recorded in a ledger. The acceptance bank
is short-horizon (closed ports, partial paths, full topology, backflow, restart,
and replay); it does not infer P4 acceptance or periodic convergence.

P4 dependency is explicit: every exhaust result is tagged `CONDITIONAL_ON_P4`.
The implementation reuses `p5b`, `exhaust_port`, `gas1d` and the frozen EOS/Riemann
components; no alternate physics or P6 species semantics are introduced.
