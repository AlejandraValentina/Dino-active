"""Bounded analytical and finite-volume port-law comparison, no RPM campaign."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.coupling import ChamberState, interface_flux
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.exact_riemann_reference_v1 import exact_riemann_v1
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.integrated_2t import DuctPath2T, EngineGeometry2T, IntegratedEngine2T
from motorsim.port_connection_v1 import port_connection_v1, PortDomainError
from motorsim.port_connection_v2 import SCHEMA, port_connection_v2
from scripts.agents.storage_preflight import check_storage_requirements


def chamber(p, t, eos):
    volume = 2e-4
    mass = p * volume / (eos.R*t)
    return ChamberState(mass, p*volume/(eos.gamma-1), .8*mass, volume)


def analytic_state(p0, t0, mach, eos, sign=1., marker=.8):
    """Independent calorically-perfect isentropic station relations."""
    factor = 1+(eos.gamma-1)*mach**2/2
    t, p = t0/factor, p0/factor**(eos.gamma/(eos.gamma-1))
    return p/(eos.R*t), sign*mach*math.sqrt(eos.gamma*eos.R*t), p, marker


def mass_density(p0, t0, mach, eos):
    state = analytic_state(p0, t0, mach, eos)
    return state[0]*state[1]


def solve_pipe_mach(area_ratio, throat_mach, eos, *, supersonic=False):
    """Invert continuity directly; does not use candidate area-Mach helpers."""
    target = area_ratio*mass_density(2e5, 300., throat_mach, eos)
    lo, hi = (1., 30.) if supersonic else (0., 1.)
    for _ in range(110):
        mid = (lo+hi)/2
        value = mass_density(2e5, 300., mid, eos)
        if (value > target) != supersonic:
            hi = mid
        else:
            lo = mid
    return (lo+hi)/2


def matched_case(area_ratio, cd, mt, normal, direction, *, supersonic=False):
    eos = IdealGas()
    ap, at, p0 = 1e-4, 1e-4*area_ratio*cd, 2e5
    mb = solve_pipe_mach(at/ap, mt, eos, supersonic=supersonic)
    if direction == 'chamber_to_pipe':
        t0 = 900.
        c = chamber(p0, t0, eos)
        w = analytic_state(p0, t0, mb, eos, sign=-normal)
    else:
        t0 = 300.
        pt = analytic_state(p0, t0, mt, eos)[2]
        c = chamber(pt*(.6 if mt == 1 else 1.), 900., eos)
        w = analytic_state(p0, t0, mb, eos, sign=normal, marker=.6)
    expected = tuple(ap*f for f in eos.flux(w))
    new = port_connection_v2(c, w, at, ap, normal, eos=eos)
    old = interface_flux(c, w, at, normal, eos=eos)
    stagnant = (c.mass/c.volume, 0., c.thermodynamics(eos)[1], .8)
    left, right = (stagnant, w) if normal == -1 else (w, stagnant)
    exact = tuple(at*f for f in eos.flux(exact_riemann_v1(left, right, eos=eos).sample()))
    error = max(abs(a-b)/abs(b) for a,b in zip(new.flux_x, expected))
    return dict(area_ratio_geometric=area_ratio, cd=cd, effective_area_m2=at,
        throat_mach=mt, pipe_mach=mb, normal=normal, direction=direction,
        supersonic_exit=supersonic, chamber_pressure_pa=c.thermodynamics(eos)[1],
        chamber_temperature_k=c.thermodynamics(eos)[2], pipe_primitive=w,
        expected_flux_x=expected, legacy_flux_x=old.flux_x,
        exact_riemann_flux_x=exact, candidate_flux_x=new.flux_x,
        candidate_branch=new.branch, candidate_max_relative_error=error,
        legacy_mass_ratio=old.flux_x[0]/expected[0],
        exact_riemann_mass_ratio=exact[0]/expected[0],
        legacy_h0_ratio=old.flux_x[2]/old.flux_x[0]/(eos.cp*t0),
        candidate_h0_ratio=new.flux_x[2]/new.flux_x[0]/(eos.cp*t0))


def initial_pressure_cases():
    """Different BC hypotheses: comparisons here are NOT nozzle error tests."""
    eos, rows = IdealGas(), []
    for ratio, ar in itertools.product((1.001, 1.05, 1.5, 2., 5., 10.), (.1, 1.)):
        for reverse in (False, True):
            pc, pi = (1e5, ratio*1e5) if reverse else (ratio*1e5, 1e5)
            c, w = chamber(pc, 300., eos), (pi/(eos.R*300.), 0., pi, .6)
            at, ap = ar*1e-4, 1e-4
            pr = min(pc,pi)/max(pc,pi)
            critical = (2/(eos.gamma+1))**(eos.gamma/(eos.gamma-1))
            mt = 1. if pr <= critical else math.sqrt(
                2/(eos.gamma-1)*(pr**(-(eos.gamma-1)/eos.gamma)-1))
            reference_q = at*mass_density(max(pc,pi),300.,mt,eos)
            old = interface_flux(c,w,at,-1,eos=eos)
            new = port_connection_v2(c,w,at,ap,-1,eos=eos)
            try:
                v1 = port_connection_v1(c,w,at,ap,-1,eos=eos)
                v1_mass, v1_branch = v1.flux_x[0], v1.branch
            except PortDomainError as exc:
                v1_mass, v1_branch = None, str(exc)
            rows.append(dict(chamber_pressure_pa=pc, pipe_pressure_pa=pi,
                effective_area_ratio=ar, initial_pipe_velocity_m_s=0.,
                quiescent_reservoir_reference_abs_mass_kg_s=reference_q,
                legacy_mass_x_kg_s=old.flux_x[0], v1_mass_x_kg_s=v1_mass,
                candidate_mass_x_kg_s=new.flux_x[0],
                v1_branch=v1_branch, candidate_branch=new.branch,
                interpretation='different_physical_boundary_problems_not_equivalence_test'))
    return rows


def finite_fixture(pc, pi, model):
    eos, ap = IdealGas(), 1e-4
    ids = (('intake','intake'), ('primary','transfer'),
           ('secondary','transfer'), ('boost','transfer'), ('exhaust','exhaust'))
    paths = tuple(DuctPath2T(name, uniform_mesh(8,.1,ap),role) for name,role in ids)
    rho = pi/(eos.R*300.)
    sc, sp = (.7,.05,.2,.05), (.1,.05,.7,.15)
    states = {p.id: ((rho,0.,pi,sum(sp[:2])),)*8 for p in paths}
    rc = pc/(eos.R*300.)
    species = {p.id: tuple(tuple(rho*v*y for y in sp) for v in p.mesh.volumes) for p in paths}
    species.update(crankcase=tuple(rc*1e-4*y for y in sc),
                   cylinder=tuple(rc*2e-4*y for y in sc))
    def geometry(_angle):
        return EngineGeometry2T(1e-4,2e-4,0.,0.,0.,(0.,0.,0.),.1*ap)
    identity = dict(fixture='finite-restricted-chamber-duct-v1')
    if model == 'candidate':
        identity['port_connection_model'] = SCHEMA
    return IntegratedEngine2T((rc,0.,pc,sum(sc[:2])), (rc,0.,pc,sum(sc[:2])),
        paths, states, geometry, species=species, eos=eos,
        inlet_boundary=Boundary('wall'), outlet_boundary=Boundary('wall'),
        geometry_identity=identity, reference_rpm=1000., max_cfl=.4)


def finite_run(pc, pi, model):
    start = time.perf_counter()
    e = finite_fixture(pc,pi,model)
    initial = deepcopy(e.state)
    integrals = [0.]*6  # mass, energy, four authoritative species
    for _ in range(50):
        row = e.step(1e-6,.006)
        for faces in row['stage_face_fluxes']:
            face = faces['exhaust']
            values = (face['left'][0],face['left'][2],*face['left_species'])
            for k,value in enumerate(values):
                integrals[k] += .5*row['dt_s']*value
    end = e.state
    delta = [end['chambers']['cylinder'][i]-initial['chambers']['cylinder'][i] for i in (0,1)]
    delta += [end['species']['chambers']['cylinder'][i]-initial['species']['chambers']['cylinder'][i] for i in range(4)]
    initial_scales = [initial['chambers']['cylinder'][0],initial['chambers']['cylinder'][1]]
    initial_scales += list(initial['species']['chambers']['cylinder'])
    exchange_errors = [abs(d+f)/s for d,f,s in zip(delta,integrals,initial_scales)]
    conservation = e.conservation_report()
    scales = e.initial_inventory
    global_error = max(abs(conservation['mass']['residual'])/scales['mass_kg'],
        abs(conservation['energy']['residual'])/scales['energy_J'],
        *(abs(x['residual'])/scales['mass_kg'] for x in conservation['species'].values()))
    snapshot = deepcopy(e.snapshot())
    restored = finite_fixture(pc,pi,model)
    restored.restore(deepcopy(snapshot))
    restored.step(1e-6,.006)
    e.step(1e-6,.006)
    replay = restored.snapshot() == e.snapshot()
    return dict(model=model, chamber_pressure_pa=pc, pipe_pressure_pa=pi,
        horizon_s=50e-6, dt_s=1e-6, cells_per_duct=8, active_connections=1,
        steps=50, compute_wall_s=time.perf_counter()-start,
        signed_chamber_to_pipe_integrals=integrals,
        chamber_inventory_changes=delta, interface_relative_residuals=exchange_errors,
        global_relative_residual=global_error, conservation=conservation,
        checkpoint_restore_next_step_equal=replay, terminal_checkpoint=snapshot,
        gate=max(*exchange_errors,global_error)<=1e-9 and replay)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    preflight = check_storage_requirements([(args.output,10*1024**2)])
    if args.output.exists():
        raise FileExistsError('preserve existing diagnostics; choose a fresh output file')
    start = time.perf_counter()
    rows = [matched_case(ar,cd,mt,n,d) for ar,cd,mt,n,d in itertools.product(
        (.025,.1,.5,1.),(.65,1.),(.01,.3,1.),(-1,1),
        ('chamber_to_pipe','pipe_to_chamber'))]
    rows += [matched_case(ar,1.,1.,n,'chamber_to_pipe',supersonic=True)
             for ar,n in itertools.product((.1,.5),(-1,1))]
    cold = initial_pressure_cases()
    finite = [finite_run(pc,pi,m) for pc,pi,m in itertools.product(
        (1e5,2e5),(1e5,2e5),('legacy','candidate')) if pc != pi]
    maximum = max(r['candidate_max_relative_error'] for r in rows)
    assert time.perf_counter()-start <= 120, 'isolated computation budget exceeded'
    result = dict(schema='DINO_PORT_FLOW_PHYSICS_VERIFICATION_V1',
        reference='analytical_ideal_nozzle_not_experimental_port',
        matched_cases=rows, initial_pressure_cases=cold, finite_volume_cases=finite,
        max_candidate_relative_flux_error=maximum,
        candidate_branches=dict(Counter(r['candidate_branch'] for r in rows)),
        wall_s=time.perf_counter()-start, storage_preflight=preflight,
        gate=maximum<=1e-9 and all(r['gate'] for r in finite),
        source_sha256={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest()
            for q in (Path(__file__),ROOT/'motorsim/coupling.py',
                ROOT/'motorsim/port_connection_v1.py',ROOT/'motorsim/port_connection_v2.py',
                ROOT/'motorsim/integrated_2t.py')}, review='SELF_REVIEW')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(gate=result['gate'],matched_cases=len(rows),
        max_candidate_relative_flux_error=maximum, finite_cases=len(finite),wall_s=result['wall_s'])))
    return 0 if result['gate'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
