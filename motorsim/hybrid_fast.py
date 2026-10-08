"""Optimized orchestration; SCALAR_REFERENCE remains hybrid_exhaust.run_cycle.
The cycle bookkeeping below is the reference code with cached adapters selected.
"""
from math import fsum
from functools import lru_cache
import time
from .simulation import burn_fraction
from .gas1d.eos import IdealGas
from .gas1d.boundary import Boundary
from .hybrid_exhaust import PATH,LegacySources as ReferenceSources,HybridSystem as ReferenceSystem
from .exhaust_fast import solve_exhaust

class LegacySources(ReferenceSources):
    @lru_cache(maxsize=128)
    def geometry(self,angle):return super().geometry(angle)

class HybridSystem(ReferenceSystem):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self._evaluated={}
    def evaluate(self,state,t):
        key=(tuple(state),t)
        if key not in self._evaluated:
            result=super().evaluate(state,t)
            if len(self._evaluated)>=8:del self._evaluated[next(iter(self._evaluated))]
            self._evaluated[key]=result
        return self._evaluated[key]

def run_cycle(mesh,pipe,state,begin=180.,*,case=None,wall_limit=600.,sensors=(.1,.3,.5),backend='STRUCTURAL',cfl=0.4,capture_conservation=False):
    """Three accepted segments preserve the legacy closed analytical burn law."""
    if backend=='SCALAR_REFERENCE':
        from .hybrid_exhaust import run_cycle as reference
        return reference(mesh,pipe,state,begin,case=case,wall_limit=wall_limit,sensors=sensors)
    solver=solve_exhaust
    if backend in ('NUMPY','NUMPY_REFERENCE'):
        from .exhaust_numpy import solve_exhaust as solver
    elif backend=='NUMBA_EXPERIMENTAL':
        from .exhaust_numba import solve_exhaust as solver
    elif backend in ('NUMBA_FUSED','NUMBA_R5_FUSED','NUMBA_R5'):
        from .exhaust_numba_fused import solve_exhaust as solver
    elif backend!='STRUCTURAL':raise ValueError('Unknown hybrid backend')
    model=LegacySources(case);eos=IdealGas(R=model.case.gas_r,gamma=model.case.gamma)
    state=list(state);started=time.monotonic();records=[];rows=[];snapshots=[]
    if (begin-model.case.initial_angle_deg)%360 != 0:
        raise ValueError('Cycle must start at the canonical initial phase')
    heat_start=begin+(model.case.heat_start_deg-begin)%360
    heat_end=heat_start+model.case.heat_duration_deg
    p_ext,T_ext,Y_ext=model.case.reservoirs_pty[1]
    exterior=Boundary('nonreflecting',state=(p_ext/(eos.R*T_ext),0.,p_ext,Y_ext))
    cuts=[begin,heat_start,heat_end,begin+360.]
    work=heat_numeric=burned=0.;external=[0.,0.,0.];exchange=[0.,0.,0.]
    complete=True;reason='final_time';postprocessing_sources=0
    for a,b in zip(cuts,cuts[1:]):
        remaining=wall_limit-(time.monotonic()-started)
        if remaining<=0:complete=False;reason='wall_timeout';break
        system=HybridSystem(model,a,state,heat_start if a==heat_start else None)
        solver_options=dict(eos=eos,cfl=cfl,exterior=exterior,sensors=sensors,
                            wall_limit=remaining)
        if capture_conservation:
            solver_options["capture_conservation"] = True
        r=solver(mesh,pipe,system,(b-a)/model.rate,**solver_options)
        amount=0. if system.heat is None else system.heat[1]*burn_fraction(system.angle(r['time']),heat_start,model.case.heat_duration_deg)
        correction=[0.,0.,amount];physical_final=system.physical(r['state'],r['time'])[:9]
        corrected_external=[v-c for v,c in zip(r['external'],correction)]
        physical_inventory=[v-c for v,c in zip(r['final_inventory'],correction)]
        scales=[r['initial_inventory'][0],r['initial_inventory'][1],r['initial_inventory'][0]]
        balance=[(z-x-f)/scale for z,x,f,scale in zip(physical_inventory,r['initial_inventory'],corrected_external,scales)]
        segment_heat=0.
        for h,stage in zip(r['history'],r['stages']):
            terms=[system.source(t['chamber'],t['time'],eos)[2] for t in stage['traces']]
            postprocessing_sources+=len(terms)
            work+=stage['dt']*.5*fsum(t['work_cylinder'] for t in terms)
            q=stage['dt']*.5*fsum(t['heat'] for t in terms);heat_numeric+=q;segment_heat+=q
            physical=system.physical(h['chamber'],h['time'])[:9]
            chamber=system.chamber(h['chamber'],h['time']);rho,p,T,Y=chamber.thermodynamics(eos)
            flux=h['exchange']
            rows.append(dict(angle=h['angle'],time=(h['angle']-begin)/model.rate,p_cyl=p,T_cyl=T,m_cyl=chamber.mass,Y_cyl=Y,
                A_exhaust=h['area'],p_port=h['port_pressure'],mass_flux_port=flux[0],energy_flux_port=flux[1],species_flux_port=flux[2],
                Mach_port=h['port_Mach'],W_indicated=work,state=physical,sensors_p_u_M_Y=h['sensors']))
        # Exact T from primitive snapshots (not inferred at zero velocity).
        for shot in r['snapshots']:
            values=[]
            for x in sensors:
                i=min(range(mesh.n),key=lambda i:abs(mesh.centers[i]-x));rho,u,p,Y=shot['primitive'][i]
                values.append(dict(x=mesh.centers[i],p=p,u=u,T=p/(rho*eos.R),Y=Y,Mach=u/eos.sound_speed(shot['primitive'][i])))
            snapshots.append(dict(angle=shot['angle'],sensors=values,primitive=shot['primitive']))
        records.append(dict(start_angle=a,end_angle=system.angle(r['time']),result=r,physical_balance=balance,
            analytical_burn=amount,heat_numeric=segment_heat,heat_primitive=model.case.fresh_energy_j_kg*amount,
            heat_quadrature_difference=segment_heat-model.case.fresh_energy_j_kg*amount))
        state=physical_final;pipe=r['cells'];burned+=amount
        external=[a+b for a,b in zip(external,corrected_external)];exchange=[a+b for a,b in zip(exchange,r['port_integral'])]
        if r['status']!='completed':complete=False;reason=r['reason'];break
    initial_inventory=records[0]['result']['initial_inventory'] if records else None
    final_inventory=[fsum(state[k::3])+fsum(row[j] for row in pipe) for k,j in enumerate((0,2,3))]
    global_balance=None if initial_inventory is None else [(b-a-e)/s for a,b,e,s in zip(
        initial_inventory,final_inventory,external,(initial_inventory[0],initial_inventory[1],initial_inventory[0]))]
    return dict(path=PATH,complete=complete,reason=reason,begin=begin,end=rows[-1]['angle'] if rows else begin,
        initial_inventory=initial_inventory,final_inventory=final_inventory,global_balance=global_balance,
        cycle_wall_seconds=time.monotonic()-started,solver_seconds=fsum(s['result']['wall_seconds'] for s in records),
        state=state,cells=pipe,external=external,port_integral=exchange,work_indicated_J=work,
        power_indicated_W=work*model.case.rpm/60,torque_indicated_Nm=work/(2*3.141592653589793),
        heat_numeric=heat_numeric,analytical_burn=burned,history=rows,snapshots=snapshots,segments=records,
        postprocessing_source_evaluations=postprocessing_sources)
