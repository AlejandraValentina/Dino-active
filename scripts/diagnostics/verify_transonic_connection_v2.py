"""Bounded algebraic verification; no integrated engine simulation."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.coupling import ChamberState
from motorsim.gas1d.eos import IdealGas
from motorsim.port_connection_v1 import port_connection_v1, PortDomainError
from motorsim.port_connection_v2 import port_connection_v2
from scripts.agents.storage_preflight import check_storage_requirements


def verify():
    counts = Counter()
    recovered = []
    failures = []
    residuals = dict(mass=0., energy=0., acoustic_velocity_m_s=0.)
    for g,pr,ar,tc,ti,mi in itertools.product(
        (1.2,1.35,1.4),(.5,.9,1.,1.1,2.,5.,20.),(.01,.1,.5,1.),
        (300.,900.),(300.,900.),(-.8,0.,.8)):
        e = IdealGas(gamma=g)
        pc,pi,ap = pr*1e5,1e5,1e-4
        rc,rho = pc/(e.R*tc),pi/(e.R*ti)
        c = ChamberState(rc,pc/(g-1),.8*rc,1.)
        state = (rho,mi*math.sqrt(g*e.R*ti),pi,.6)
        inputs = dict(gamma=g,chamber_pipe_pressure_ratio=pr,
            effective_area_ratio=ar,chamber_temperature_k=tc,
            pipe_temperature_k=ti,pipe_outward_mach=mi)
        old_failed = False
        try:
            port_connection_v1(c,state,ar*ap,ap,1,eos=e)
        except PortDomainError:
            old_failed = True
        try:
            x = port_connection_v2(c,state,ar*ap,ap,1,eos=e)
            counts[x.branch] += 1
            mass = x.outward[0]
            if mass < 0:
                residuals['energy'] = max(residuals['energy'],
                    abs(x.outward[2]/mass/(e.cp*tc)-1))
                if x.boundary_total_pressure_pa > pc*(1+1e-10):
                    raise AssertionError('donor entropy decreases')
            if x.branch.startswith('INFLOW_CHOKED'):
                # Direct analytic critical-flow formula, not model helpers.
                expected = ar*ap*pc/math.sqrt(e.R*tc)*math.sqrt(g)*(
                    2/(g+1))**((g+1)/(2*(g-1)))
                residuals['mass'] = max(residuals['mass'],abs(-mass/expected-1))
            if x.acoustic_velocity_residual_m_s is not None:
                residuals['acoustic_velocity_m_s'] = max(residuals['acoustic_velocity_m_s'],
                    abs(x.acoustic_velocity_residual_m_s))
            if x.causality_rightmost_speed_m_s is not None:
                assert x.causality_rightmost_speed_m_s <= 1e-7
            if old_failed:
                recovered.append(dict(**inputs,branch=x.branch,
                    face_outward_mach=x.boundary_state[1]/e.sound_speed(x.boundary_state),
                    mass_kg_s=mass,rightmost_wave_speed_m_s=x.causality_rightmost_speed_m_s))
        except Exception as error:
            failures.append(dict(**inputs,error=f'{type(error).__name__}: {error}'))
    assert sum(counts.values())+len(failures) == 1008
    return dict(schema='DINO_TRANSONIC_CONNECTION_V2_ALGEBRAIC_VERIFICATION',
        total=1008,supported=sum(counts.values()),failures=failures,
        branches=dict(counts),maximum_residuals=residuals,
        old_unsupported_recovered=len(recovered),recovered_cases=recovered,
        physical_steps=0,experimental_validation=False,
        closure='EQUIVALENT_IDEAL_NOZZLE_NOT_SEPARATED_EXPANSION')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    preflight = check_storage_requirements([(args.output.parent,5*1024**2)])
    result = verify()
    sources = ['motorsim/port_connection_v2.py',
        'motorsim/gas1d/exact_riemann_reference_v1.py',
        'tests/test_transonic_connection_v2.py',
        'openspec/changes/predictive-reliability-v1/transonic-contract-v2.md',
        'scripts/diagnostics/verify_transonic_connection_v2.py']
    result['sha256'] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    result['storage_preflight'] = preflight
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('recovered_cases','sha256','storage_preflight')},indent=2))
    if result['failures']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
