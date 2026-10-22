"""Conservative 0D partial-mixing closure for the integrated 1D engine.

The outlet is a convex combination of perfect mixing and preferential burned
gas displacement. This is a reduced-order limiting-model interpolation, NOT
a calibrated port-direction/CFD model or an identified scavenging curve.
All components remain actual donor inventories; no species source is added.
The common calorically-perfect EOS uses the existing donor enthalpy unchanged.
"""
import math

SCHEMA = "GAS_EXCHANGE_V2"


def validate(model):
    if model is None:
        return None
    if (not isinstance(model,dict) or set(model)!={"schema","intake_control","transfer_crankcase_connection","mixed_outflow_fraction","provenance"}
            or model["schema"]!=SCHEMA or model["intake_control"] not in ("reed","piston_port")
            or model["transfer_crankcase_connection"]!="open_duct_face"
            or model["provenance"]!="SYNTHETIC_ASSUMPTION"):
        raise ValueError("invalid explicit GAS_EXCHANGE_V2 contract")
    x=model["mixed_outflow_fraction"]
    if type(x) not in (float,int) or not math.isfinite(x) or not 0<=x<=1:
        raise ValueError("mixed_outflow_fraction must be explicit in [0,1]")
    return dict(model)


def outlet_species_rate(mass_rate, inventory, dt, mixed_fraction):
    """Bounded mixture/displacement outlet. Positive rate leaves cylinder.

    Returns four nonnegative rates summing to mass_rate, limited by inventory
    over this SSPRK stage. Reverse flow is handled by the original duct donor.
    """
    mass=math.fsum(inventory)
    if mass_rate<=0 or dt is None or dt<=0 or mass<=0:
        raise ValueError("positive outlet rate, inventory and stage dt required")
    cap=[max(0.,x)/dt for x in inventory]
    if mass_rate>math.fsum(cap)*(1+1e-12):
        raise ValueError("inadmissible species mass: outlet exceeds cylinder inventory")
    burned=inventory[2]+inventory[3]
    bulk=[max(0.,x)/mass for x in inventory]
    displaced=[0.,0.,inventory[2]/burned,inventory[3]/burned] if burned>0 else bulk
    desired=[mass_rate*(mixed_fraction*a+(1-mixed_fraction)*b) for a,b in zip(bulk,displaced)]
    rates=[min(a,b) for a,b in zip(desired,cap)]
    # Redistribute any capped demand over remaining donor capacity. This keeps
    # total mass flux exactly the unchanged gas-interface flux.
    missing=max(0.,mass_rate-math.fsum(rates))
    spare=[max(0.,a-b) for a,b in zip(cap,rates)]
    total=math.fsum(spare)
    if missing and total:
        rates=[a+missing*b/total for a,b in zip(rates,spare)]
    return tuple(rates)
