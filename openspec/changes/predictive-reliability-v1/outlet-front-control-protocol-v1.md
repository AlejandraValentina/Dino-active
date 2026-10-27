# Three-grid front control, 2026-10-27

Uniform unit-length/unit-area duct; gamma=1.4,R=1,p=u=1. Initial top-hat
species0 on[.5,.75], species2 complement; optional contact rho=1.2 inside,
rho=1 outside. Exact Euler contact/passive translation at t=.35; no reaction.
Compare periodic duct and prescribed left inflow/right reservoir at p0=T0=1.
Use actual HLLC, Boundary and reconstruction V1/V2 functions, SSPRK2 conservative
stages with stage-averaged species and Euler boundary flux ledgers.
32/64/128cells, first-order reference, MUSCL controls and half time-step checks.
dt<=.15/[n*(1+sqrt1.4)]. Global120s and8MiB; preflight before output.
Report exact cell-average errors and conservative adjacent-grid restriction:
L1,L2,Linfinity; crossings10/50/90%, maximum/minimum, species inventory and
integrated boundary transfer. Linfinity need not vanish at a moving discontinuity.
No engine work/IMEP claim from an imposed constant-volume duct; relate those
only to existing separately identified integrated engine data.
Keep profiles for all cases. No production solver change or periodic campaign.
