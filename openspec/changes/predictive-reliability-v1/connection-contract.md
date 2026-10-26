# Adiabatic port connection STANDARD_V1 — candidate contract

This contract precedes implementation and numerical evaluation. It is a new
candidate, never an amendment to P3's frozen equal-section Riemann connection.
The quiescent-volume restriction reference has passed its preregistered gate.

## Physical stations and signs

Chamber c has pc,Tc and zero representative velocity. A geometric aperture with
Cd has effective throat At=Cd*A. The duct section is Ap>=At. Keep those sections
distinct. Effective area is supplied once by the existing geometry. Normal n
points OUT of the duct: w=n*u>0 is pipe-to-chamber outflow.

The interior primitive provides an acoustic wave curve: wb(p)=wi-f(p;Wi),
where f is the exact ideal-gas shock/rarefaction pressure curve. For a rarefaction,
f=2ai/(gamma-1)*[(p/pi)^((gamma-1)/(2gamma))-1]; for a compression,
f=(p-pi)*sqrt(2/((gamma+1)*rhoi)/(p+(gamma-1)/(gamma+1)*pi)). This replaces
neither the interior HLLC nor its tests. Inflow has a contact with distinct donor
entropy; outflow uses the interior shock/rarefaction star density.

## Pipe outflow

Use pipe boundary density from its wave curve. Its total temperature is
T0b=Tb+wb^2/(2cp) and total pressure p0b=pb*(T0b/Tb)^(gamma/(gamma-1)).
Match Ap*rhob*wb to At times the independently verified restriction flux with
donor p0b,T0b and receiver chamber pressure pc. No pressure recovery is assigned
inside the well-mixed chamber. Apply the sonic throat constraint, and require
the duct-side state to be subsonic or sonic. Chamber receives mdot*cp*T0b.

## Pipe inflow

Contraction c->throat is isentropic and adiabatic: Tt=Tc/(1+(gamma-1)Mt^2/2),
pt=pc*(Tt/Tc)^(gamma/(gamma-1)), vt=Mt*sqrt(gamma*R*Tt), Q=At*rhot*vt.
For subsonic throat flow, model throat->duct as a separated adiabatic expansion
with pressure pt on the surrounding stationary annulus. Conserve mass, total
enthalpy cp*Tc, and axial momentum:

    Q = Ap*rhob*vb
    Tb = Tc-vb^2/(2cp)
    pb = pt+Q*(vt-vb)/Ap

These imply beta*Q*vb^2-(Ap*pt+Q*vt)*vb+Q*R*Tc=0 with
beta=(gamma+1)/(2gamma). Select the subsonic root, then match wb(pb)=-vb.
At=Ap is the isentropic full-section limit without a fictitious area step.

At Mt=1 the throat is sonic. Q and chamber total enthalpy are fixed; solve duct
mass, energy and acoustic compatibility. Do not force the subsonic pressure-
recovery equation on an underexpanded choked jet. Reject no-root or entropy-
decreasing states. The full-section sonic inflow limit prescribes the sonic
state; an outgoing acoustic condition cannot overdetermine a sonic inlet.

## Output and domain

Return a full duct-face Euler momentum flux Ap*(rhob*ub^2+pb), shared signed mass
and energy flux and donor species. The old blocked-area pressure addition must
NOT be applied again. The chamber has no resolved axial momentum; the reaction
is external and stationary. Energy is never independently replaced by m*cv*T.

Closed aperture is an impermeable stationary wall. Equal pressures and zero
velocity give exact zero mass/energy/species flux even at unequal temperatures.
Unsupported supersonic interior states fail closed with an explicit domain error;
no positivity clipping, flux caps chosen to raise power, or silent legacy fallback.
No port-specific Cd calibration or experimental accuracy claim is introduced.

## Fixed acceptance

- Full-area subsonic isentropic input M=0.001,0.01,0.1,0.3,0.8: match all Euler
  flux components to relative 1e-8; exact rest and closed-aperture limits.
- Subsonic and sonic throat regimes in both directions at At/Ap=0.01,0.1,0.5,1;
  gamma=1.2,1.35,1.4; chamber/pipe temperatures 300/900 K and reversed.
- For every supported result, independent mass/energy closure <=1e-9 relative;
  duct Mach<=1 plus roundoff, throat Mach<=1 plus roundoff, positive rho/p/T;
  contraction is isentropic and expansion cannot decrease entropy.
- Reverse orientation must transform mass/energy signs and retain momentum.
- At=Ap versus At/Ap approaching 1 and Mt approaching 1 must have continuous
  physical flux within 1e-6 relative under matched nearby states. If this fails,
  stop connection adoption and present the incompatibility before dependent work.
- Only after these gates: integrate behind a new explicit physical-model identity,
  verify conservation/restart and keep the historical route selectable.

Sources: own ideal-gas conservation derivation; NASA mass-flow reference;
Thompson & Yoon 2020 DOI 10.1155/2020/6787408 for station separation and regime
structure. The exact wave-curve/expansion combination is a Dino candidate closure,
not a claim of reproducing that paper's full numerical method.
