"""Small reproducible domain/conservation diagnostic; no integrated engine run."""
import argparse
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.coupling import ChamberState
from motorsim.gas1d.eos import IdealGas
from motorsim.port_connection_v1 import port_connection_v1, PortDomainError
from scripts.agents.storage_preflight import check_storage_requirements


def minimum_counterexample():
    """Analytic inverse of the Euler compression wave, independent root bound.

    Inputs are legitimate subsonic interior data. The unsupported branch is a
    missing candidate regime, not a negative pressure or a failed iteration.
    """
    e = IdealGas(gamma=1.35)
    pc, pi, tc, ti, ap, at = 5e5, 1e5, 300., 300., 1e-4, 5e-5
    rhoi = pi/(e.R*ti)
    wi = -.8*math.sqrt(e.gamma*e.R*ti)
    tcrit = tc*2/(e.gamma+1)
    pcrit = pc*(2/(e.gamma+1))**(e.gamma/(e.gamma-1))
    vcrit = math.sqrt(e.gamma*e.R*tcrit)
    qcrit = at*pcrit/(e.R*tcrit)*vcrit

    def acoustic_pressure(v):
        # f=v+wi>0. f^2*(p+B)=A*(p-pi)^2.
        f = v+wi
        a = 2/((e.gamma+1)*rhoi)
        b = (e.gamma-1)/(e.gamma+1)*pi
        delta = (f*f+math.sqrt(f**4+4*a*f*f*(pi+b)))/(2*a)
        return pi+delta

    p_limit = acoustic_pressure(vcrit)
    q_limit = ap*p_limit/(e.R*tcrit)*vcrit
    # Demonstrate what mass/energy/acoustic closure alone would request if
    # the subsonic domain restriction were removed. This is NOT adopted.
    lo, hi = vcrit, math.sqrt(2*e.cp*tc)*.999
    for _ in range(100):
        v = (lo+hi)/2
        t = tc-v*v/(2*e.cp)
        q = ap*acoustic_pressure(v)*v/(e.R*t)
        if q > qcrit:
            hi = v
        else:
            lo = v
    v = (lo+hi)/2
    t = tc-v*v/(2*e.cp)
    return dict(gamma=e.gamma, chamber_pressure_pa=pc, pipe_pressure_pa=pi,
                chamber_temperature_k=tc, pipe_temperature_k=ti,
                pipe_interior_outward_mach=-.8, effective_area_ratio=at/ap,
                throat_required_mass_kg_s=qcrit,
                compatible_subsonic_pipe_max_mass_kg_s=q_limit,
                demand_capacity_ratio=qcrit/q_limit,
                sonic_limit_pipe_pressure_pa=p_limit,
                unconstrained_bulk_mach=v/math.sqrt(e.gamma*e.R*t),
                explanation="Sonic-throat demand exceeds every subsonic pipe state on the candidate acoustic/energy branch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    preflight = check_storage_requirements([(output.parent, 5*1024**2)])
    counts = collections.Counter()
    failures = []
    max_mass, max_energy = 0., 0.
    for gamma, ratio, ar, tc, ti, mi in itertools.product(
            (1.2,1.35,1.4), (.5,.9,1.,1.1,2.,5.,20.), (.01,.1,.5,1.),
            (300.,900.), (300.,900.), (-.8,0.,.8)):
        e = IdealGas(gamma=gamma)
        pc, pi, ap = ratio*1e5, 1e5, 1e-4
        rho = pi/(e.R*ti)
        u = mi*math.sqrt(gamma*e.R*ti)
        rhoc = pc/(e.R*tc)
        c = ChamberState(rhoc, pc/(gamma-1), .8*rhoc, 1.)
        try:
            x = port_connection_v1(c, (rho,u,pi,.6), ar*ap, ap, 1, eos=e)
        except PortDomainError as error:
            failures.append(dict(gamma=gamma, chamber_pipe_pressure_ratio=ratio,
                                 effective_area_ratio=ar, chamber_temperature_k=tc,
                                 pipe_temperature_k=ti, interior_outward_mach=mi,
                                 error=str(error)))
            continue
        counts[x.branch] += 1
        rb, ub, pb, _ = x.boundary_state
        temp = pb/(rb*e.R)
        q = x.outward[0]
        if q:
            h0 = e.cp*tc if q < 0 else e.cp*temp+ub*ub/2
            max_energy = max(max_energy, abs(x.outward[2]/q/h0-1))
            tt = (tc if q < 0 else h0/e.cp)/(1+(gamma-1)*x.throat_mach**2/2)
            qt = ar*ap*x.throat_pressure_pa/(e.R*tt)*x.throat_mach*math.sqrt(gamma*e.R*tt)
            max_mass = max(max_mass, abs(abs(q)/qt-1))
    receipt = dict(schema='DINO_PORT_CONNECTION_DOMAIN_V1',
                   status='ADOPTION_BLOCKED_DOMAIN' if failures else 'PASS_DOMAIN',
                   configurations=sum(counts.values())+len(failures),
                   supported=sum(counts.values()), unsupported=len(failures),
                   branches=dict(counts), unsupported_states=failures,
                   max_relative_mass_residual_supported=max_mass,
                   max_relative_energy_residual_supported=max_energy,
                   counterexample=minimum_counterexample(), storage_preflight=preflight,
                   source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                       for p in ('motorsim/port_connection_v1.py',
                                 'motorsim/port_restriction_v1.py',
                                 'scripts/diagnostics/verify_port_connection_v1.py')},
                   integrated_model_enabled=False, engine_simulations=0,
                   qualification='Numerical candidate only; domain failures are not waived by passing unit tests')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('status','configurations','supported','unsupported',
                     'max_relative_mass_residual_supported','max_relative_energy_residual_supported',
                     'counterexample')}, indent=2))


if __name__ == '__main__':
    main()
