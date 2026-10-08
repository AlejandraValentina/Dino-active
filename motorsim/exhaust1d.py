"""Experimental P4 joint SSPRK2 path; accepted P0/P2/P3 modules stay frozen."""
from math import fsum, isfinite
import time
from .coupling import ChamberState
from .exhaust_port import port_flux
from .gas1d.eos import IdealGas, InvalidState
from .gas1d.boundary import Boundary
from .gas1d.riemann import hllc_flux
from .gas1d.second_order import reconstruct
from .gas1d.solver import cfl_step, event_step


class Bench:
    cylinder=0
    def __init__(self,chamber,port,rpm=3000,start_angle=0):
        self.initial=[chamber.mass,chamber.internal_energy,chamber.fresh_mass]
        self.volume=chamber.volume;self.port=port;self.rate=6*rpm;self.start_angle=start_angle
    def angle(self,t):return self.start_angle+self.rate*t
    def chamber(self,z,t):return ChamberState(*z,self.volume)
    def source(self,z,t,eos):return [0.]*3,[0.]*3,dict(work=0.,heat=0.,burn=0.)
    def validate(self,z,t,eos):self.chamber(z,t).thermodynamics(eos)
    def area(self,t):return self.port.area(self.angle(t))
    def events(self,area,end):
        return sorted(set([(360*k+a-self.start_angle)/self.rate for k in range(int(self.angle(end)//360)+2) for a in self.port.events(area) if 0<(360*k+a-self.start_angle)/self.rate<=end]+[end]))


def solve_exhaust(mesh,initial,system,end,*,eos=None,cfl=.4,exterior=None,sensors=(),wall_limit=600.):
    eos=eos or IdealGas();exterior=exterior or Boundary('nonreflecting',state=(100000/(eos.R*300),0.,100000.,0.))
    start=time.monotonic();q=[tuple(row) for row in initial];z=list(system.initial)
    events=system.events(mesh.areas[0],end);event_index=0;t=0.
    counts=dict(rhs=0,HLLC=0,HLLE=0,characteristic=0,rejected=0,downgrades=0)
    def primitive(cells):return [eos.primitive(tuple(x/v for x in row)) for row,v in zip(cells,mesh.volumes)]
    def validate(cells,state,when):system.validate(state,when,eos);return primitive(cells)
    def inventory(cells,state):return [fsum(state[k::3])+fsum(row[j] for row in cells) for k,j in enumerate((0,2,3))]
    w=validate(q,z,t);initial_inventory=inventory(q,z);scale=(initial_inventory[0],initial_inventory[1],initial_inventory[0])
    sensor_indices=[min(range(mesh.n),key=lambda i:abs(mesh.centers[i]-x)) for x in sensors]
    def rhs(cells,state,when):
        counts['rhs']+=1;ws=validate(cells,state,when)
        left,right,down=reconstruct(mesh,ws,(Boundary('outflow'),exterior),eos);counts['downgrades']+=len(down)
        ch=system.chamber(state,when);ch.thermodynamics(eos)
        port=port_flux(ch,left[0],system.area(when),mesh.areas[0],eos=eos)
        counts['HLLC']+=port['HLLC'];counts['HLLE']+=port['HLLE']
        flux=[port['flux']];speeds=[max(abs(port['speeds'][0]),abs(port['speeds'][2]))]
        for i in range(mesh.n-1):
            f,s,reason=hllc_flux(right[i],left[i+1],eos);counts['HLLE' if reason else 'HLLC']+=1
            flux.append(tuple(mesh.areas[i+1]*v for v in f));speeds.append(max(abs(s[0]),abs(s[2])))
        f,s,reason=exterior.flux(right[-1],1,eos)
        if exterior.kind in ('wall','fixed','outflow'):counts['HLLE' if reason else 'HLLC']+=1
        else:counts['characteristic']+=1
        flux.append(tuple(mesh.areas[-1]*v for v in f));speeds.append(max(abs(s[0]),abs(s[2])))
        limit,_,unit=cfl_step(mesh,ws,speeds,eos,cfl)
        dq=[tuple(flux[i][k]-flux[i+1][k]+(ws[i][2]*(mesh.areas[i+1]-mesh.areas[i]) if k==1 else 0.) for k in range(4)) for i in range(mesh.n)]
        dz,external,terms=system.source(state,when,eos)
        for k in range(3):dz[3*system.cylinder+k]+=port['exchange'][k];external[k]-=flux[-1][(0,2,3)[k]]
        boundary_state=exterior.face_state(right[-1],1,eos)
        return dict(dq=dq,dz=dz,external=external,terms=terms,port=port,limit=limit,unit=unit,
                    trace=dict(time=when,angle=system.angle(when),area=port['area'],chamber=list(state),volume=ch.volume,
                    pressure=ch.thermodynamics(eos)[1],pipe_face=left[0],exchange=port['exchange'],
                    outlet=boundary_state,open_reaction=port['open_reaction'],closed_reaction=port['closed_reaction']))
    def advance(cells,state,op,dt):return [tuple(a+dt*b for a,b in zip(row,dr)) for row,dr in zip(cells,op['dq'])],[a+dt*b for a,b in zip(state,op['dz'])]
    history=[];stages=[];snapshots=[];external=[0.]*3;port_integral=[0.]*3;rejections={};hit_events=[]
    extrema=dict(rho=min(row[0] for row in w),p=min(row[2] for row in w),T=min(row[2]/(row[0]*eos.R) for row in w),Y_min=min(row[3] for row in w),Y_max=max(row[3] for row in w))
    def observe(cells,state,when):
        rows=validate(cells,state,when)
        for key,value in (('rho',min(x[0] for x in rows)),('p',min(x[2] for x in rows)),('T',min(x[2]/(x[0]*eos.R) for x in rows)),('Y_min',min(x[3] for x in rows))):extrema[key]=min(extrema[key],value)
        extrema['Y_max']=max(extrema['Y_max'],max(x[3] for x in rows))
        return rows
    status='completed';reason='final_time';max_stage_residual=0.;max_global_residual=0.;max_CFL=0.;next_snapshot=0
    while t<end:
        if time.monotonic()-start>wall_limit:status='failed_infrastructure';reason='wall_timeout';break
        try:
            op0=rhs(q,z,t);target=events[event_index];dt=event_step(op0['limit'],target-t)
            for retry in range(13):
                if dt<1e-12 or t+dt==t:raise InvalidState('dt_below_min')
                try:
                    q1,z1=advance(q,z,op0,dt);validate(q1,z1,t+dt);op1=rhs(q1,z1,t+dt)
                    if dt>op1['limit']:raise InvalidState('stage_CFL')
                    q2,z2=advance(q1,z1,op1,dt);validate(q2,z2,t+2*dt)
                    qnew=[tuple(.5*a+.5*b for a,b in zip(x,y)) for x,y in zip(q,q2)];znew=[.5*a+.5*b for a,b in zip(z,z2)]
                    validate(qnew,znew,t+dt);break
                except (ValueError,OverflowError,ZeroDivisionError) as exc:
                    counts['rejected']+=1;key=str(exc);rejections[key]=rejections.get(key,0)+1
                    if retry==12:raise InvalidState('joint_retries_exhausted: '+key)
                    dt*=.5
            for qa,za,qb,zb,op in ((q,z,q1,z1,op0),(q1,z1,q2,z2,op1)):
                residue=max(abs(b-a-dt*e)/s for a,b,e,s in zip(inventory(qa,za),inventory(qb,zb),op['external'],scale))
                max_stage_residual=max(max_stage_residual,residue);max_CFL=max(max_CFL,dt/op['unit'])
            observe(q1,z1,t+dt);observe(q2,z2,t+2*dt);w=observe(qnew,znew,t+dt)
        except (ValueError,OverflowError,ZeroDivisionError) as exc:status='failed_numerical';reason=str(exc);break
        for k in range(3):
            external[k]+=dt*.5*(op0['external'][k]+op1['external'][k])
            port_integral[k]+=dt*.5*(op0['port']['exchange'][k]+op1['port']['exchange'][k])
        q,z=qnew,znew;t+=dt
        if t>=target:
            t=target;hit_events.append(t);event_index+=1
        inv=inventory(q,z);res=[(a-b-e)/s for a,b,e,s in zip(inv,initial_inventory,external,scale)];max_global_residual=max(max_global_residual,max(map(abs,res)))
        ch=system.chamber(z,t);rho,p,T,Y=ch.thermodynamics(eos)
        history.append(dict(time=t,angle=system.angle(t),dt=dt,chamber=z.copy(),cylinder=(p,T,ch.mass,Y),area=system.area(t),
            sensors=[(w[i][2],w[i][1],w[i][1]/eos.sound_speed(w[i]),w[i][3]) for i in sensor_indices],
            port_pressure=op1['trace']['pipe_face'][2],port_Mach=op1['trace']['pipe_face'][1]/eos.sound_speed(op1['trace']['pipe_face']),
            exchange=[.5*(op0['port']['exchange'][k]+op1['port']['exchange'][k]) for k in range(3)],
            external=external.copy(),port_integral=port_integral.copy(),inventory=inv,residual=res))
        stages.append(dict(dt=dt,limits=[op0['limit'],op1['limit']],traces=[op0['trace'],op1['trace']]))
        if t>=next_snapshot:
            snapshots.append(dict(time=t,angle=system.angle(t),primitive=w));next_snapshot+=end/8
    return dict(status=status,reason=reason,time=t,wall_seconds=time.monotonic()-start,cells=q,state=z,primitive=primitive(q),
        initial_inventory=initial_inventory,final_inventory=inventory(q,z),external=external,port_integral=port_integral,
        max_global_residual=max_global_residual,max_stage_residual=max_stage_residual,max_CFL=max_CFL,extrema=extrema,
        counts=counts,rejections=rejections,events=events,hit_events=hit_events,history=history,stages=stages,snapshots=snapshots,
        sensor_positions=[mesh.centers[i] for i in sensor_indices],mesh=mesh.as_dict())
