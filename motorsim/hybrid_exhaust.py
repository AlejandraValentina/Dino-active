"""Experimental 2T_0D1D_EXHAUST adapter. Frozen solvers and legacy stay unchanged."""
from math import fsum
import time
from .simulation import Model, StopCalculation, burn_fraction
from .simulation_case import SyntheticCase
from .coupling import ChamberState
from .exhaust_port import ExhaustPort
from .exhaust1d import solve_exhaust
from .gas1d.eos import IdealGas
from .gas1d.boundary import Boundary

PATH='2T_0D1D_EXHAUST'


class LegacySources(Model):
    """Reuse existing I/K/transfers, work and heat; mask replaced exhaust links."""
    def __init__(self,case=None):
        super().__init__(case or SyntheticCase(),external_band_pa=100)

    def geometry(self,angle):
        volumes,dvs,areas=super().geometry(angle)
        return volumes,dvs,(*areas[:4],0.,0.)


class HybridSystem:
    cylinder=2
    def __init__(self,model,start,state,heat_start=None):
        self.model=model;self.start_angle=start;self.rate=model.rate
        self.initial=list(state);self.port=ExhaustPort.from_project(model.case.project_geometry)
        self.dummy=model.initial_state()[9:12]
        self.heat=None if heat_start is None else (heat_start,state[8])

    def angle(self,t):return self.start_angle+self.rate*t

    def physical(self,state,t):
        full=list(state)+self.dummy+[0.]*(self.model.layout.size-12)
        if self.heat is not None:
            if state[8]!=self.initial[8]:raise ValueError('Transformed fresh state changed during closed heat')
            full=self.model.analytic(self.angle(t),full,self.heat)
        return full

    def evaluate(self,state,t):
        angle=self.angle(t)
        if self.heat is not None:
            areas=self.model.geometry(angle)[2]
            if self.port.area(angle)!=0 or any(areas[j] for j in (2,3)):
                raise ValueError('Analytic heat requires all cylinder ports closed')
        try:return self.model.evaluate(angle,self.physical(state,t),self.heat)
        except StopCalculation as exc:raise ValueError(str(exc)) from exc

    def chamber(self,state,t):
        physical=self.physical(state,t)
        return ChamberState(*physical[6:9],self.model.geometry(self.angle(t))[0][2])

    def validate(self,state,t,eos):self.evaluate(state,t)

    def area(self,t):return self.port.area(self.angle(t))

    def source(self,state,t,eos):
        dy,(nodes,volumes,flows)=self.evaluate(state,t);layout=self.model.layout
        work=fsum(dy[layout.work+i] for i in range(3));heat=dy[layout.heat]
        # E is absent. Only exterior-I is external; exhaust exchange is added by P4.
        external=[flows[0][0],flows[0][1]+heat-work,flows[0][2]]
        terms=dict(work_cylinder=dy[layout.work+2],work_total=work,heat=heat,burn_rate=dy[layout.burn])
        return dy[:9],external,terms

    def events(self,area,end):
        phases=set(self.model.events)|set(self.port.events(area))
        return sorted(set([(360*k+a-self.start_angle)/self.rate
            for k in range(int(self.angle(end)//360)+2) for a in phases
            if 0<(360*k+a-self.start_angle)/self.rate<=end]+[end]))


def run_cycle(mesh,pipe,state,begin=180.,*,case=None,wall_limit=600.,sensors=(.1,.3,.5)):
    """Three accepted segments preserve the legacy closed analytical burn law."""
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
        r=solve_exhaust(mesh,pipe,system,(b-a)/model.rate,eos=eos,cfl=.4,exterior=exterior,sensors=sensors,wall_limit=remaining)
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
