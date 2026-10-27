# Acoustic outlet protocol, 2026-10-27
Before execution: uniform unit duct, gamma1.4,R1, rest rho=p=1. Gaussian
right-travelling pressure pulse amplitude1e-5, center.35,sigma.07. Final t=.8.
Linear open-end reference reflection pressure coefficient-1, velocity+1.
Compare exact cell-average Gaussian incident/reflected fields, phase centroid,
L1/L2/Linf. 32/64/128cells, 128halfstep; original MUSCL V2/HLLC/plenum functions.
120s/8MiB per invocation, preflight. Stage flux mass/energy/species ledgers.
Separate direct boundary algebra through three velocity reversals and nearzero,
including reservoir stagnation enthalpy and signed species donor. Not a proof
of finite-amplitude shock/reversal integration or of transonic port accuracy.
No gate claim from linear reference outside small-amplitude regime.
Integrated pilot conditional on successful conservation/reflection checks:
source-bound same-run cycle2 checkpoint, max10additionalcycles/240s, checkpoint
every revolution, original detector/thresholds. L1 candidate only, not L2 period
or mesh independence. Preserve original model and all evidence. No extension.
