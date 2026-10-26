# Endpoint truncation isolated without time integration — SELF_REVIEW

Smooth subsonic isentropic flow in a linear-frustum duct, with total-state
reservoir at the left and exact fixed exterior state at the right. This tests
the instantaneous duct spatial operator; finite 0D chambers are not asserted
steady. Independent area/Mach bisection and Gauss8 volume-weighted conserved
cell averages; Gauss16 agrees to relative 1e-12. No time steps or engine campaigns.

| Cells | Left boundary mass-flux error | Whole-duct normalized mass residual | Interior normalized mass residual |
|---|---:|---:|---:|
| 20 | 0.83818% | 7.35490e-3 | 5.44802e-6 |
| 40 | 0.41788% | 3.67439e-3 | 1.34031e-6 |
| 80 | 0.20864% | 1.83641e-3 | 3.32631e-7 |
| 160 | 0.10424% | 9.18011e-4 | 8.28682e-8 |

Interior mass/energy residual orders approach 2; the complete operator's
mass/momentum/energy residual orders approach 1. Endpoint cells keep zero slopes
and port/external exchange receives endpoint-cell means. These produce O(dx)
boundary flux errors even on a smooth solution. Supplying the exact face state
to the existing nozzle connection yields the exact reference mass flux (within
floating-point roundoff) on every mesh: the boundary **sampling** is limiting
this reference, rather than its connection algebra. Exact analytical fluxes at
all faces, evaluated only as a diagnostic oracle, leave a second-order momentum
source residual; mass/energy residuals are roundoff. No oracle flux replaces any
production flux.

This demonstrates a concrete limitation of the V1 spatial capability. It does
not prove that all slow/nonmonotonic engine mesh sensitivity has this cause:
initial fronts, shocks, limiter activity and time error remain relevant there.

Next correction justified: a new opt-in spatial capability with one-sided,
limited, positive endpoint reconstruction, including the states/compositions
actually supplied to port and external boundaries. Preserve V1 and defaults.
Verify smooth boundary order, positivity/simplex, shocks, shared conservation,
reverse donor, walls, configuration identity and checkpoint restart before
another bounded engine diagnostic. No physical equation or target power change.

Four independent-reference tests pass. Early fixture tests caught an EOS method
name and an orientation mistake in the diagnostic; corrected to `conservative`
and positive-x `flux_x` before recording this result. No solver fix was needed
for those fixture mistakes. Data: `boundary-truncation-reference-v1.json`.
