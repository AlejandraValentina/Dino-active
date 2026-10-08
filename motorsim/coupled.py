"""Isolated finite chamber + left end of a closed Euler pipe, P3 only.

Reuses frozen reconstruction, Riemann, wall and CFL operators. The chamber
participates in the same Euler/SSP-RK2 stages; no production engine coupling.
"""
from math import fsum, isfinite
import time
from .coupling import ChamberState, interface_flux
from .gas1d.eos import IdealGas, InvalidState
from .gas1d.boundary import Boundary
from .gas1d.riemann import hllc_flux
from .gas1d.second_order import reconstruct
from .gas1d.solver import cfl_step, event_step


def solve_coupled(mesh, initial, chamber, final_time, *, method='MUSCL_SSPRK2',
                  eos=None, cfl=.4, volume=None, wall_limit=300.):
    eos=eos or IdealGas();started=time.monotonic()
    if method not in ('FIRST_ORDER','MUSCL_SSPRK2') or not isfinite(final_time) or final_time<=0:
        raise ValueError('Invalid method/time')
    if len(initial)!=mesh.n:raise ValueError('Mesh/state mismatch')
    volume=volume or (lambda t:(chamber.volume,0.))
    cells=[tuple(q) for q in initial];z=(chamber.mass,chamber.internal_energy,chamber.fresh_mass)
    counts=dict(rhs=0,HLLC=0,HLLE=0,downgrades=0,rejected=0);reasons={}
    def chamber_at(state,t):
        v,dv=volume(t)
        if not isfinite(dv):raise InvalidState('Nonfinite volume derivative')
        ch=ChamberState(*state,v);ch.thermodynamics(eos)
        return ch,dv
    def primitives(q):return [eos.primitive(tuple(x/v for x in row)) for row,v in zip(q,mesh.volumes)]
    def total(q,state):return [state[j]+fsum(row[k] for row in q) for j,k in enumerate((0,2,3))]
    def validate(q,state,t):
        w=primitives(q);ch,_=chamber_at(state,t)
        return w,ch
    initial_w,_=validate(cells,z,0.);initial_total=total(cells,z)
    scales=(initial_total[0],initial_total[1],initial_total[0])
    def normalized(residue):return [abs(x)/s for x,s in zip(residue,scales)]
    def counted(item):
        reason=item[2];counts['HLLE' if reason else 'HLLC']+=1
        if reason:reasons[reason]=reasons.get(reason,0)+1
        return item
    wall=Boundary('wall')
    def operator(q,state,t):
        counts['rhs']+=1
        w,ch=validate(q,state,t);rho,p,T,Y=ch.thermodynamics(eos)
        boundaries=(Boundary('fixed',state=(rho,0.,p,Y)),wall)
        if method=='MUSCL_SSPRK2':
            lf,rf,down=reconstruct(mesh,w,boundaries,eos);counts['downgrades']+=len(down)
        else:lf=rf=w
        exchange=interface_flux(ch,lf[0],mesh.areas[0],-1,eos=eos)
        counted((exchange.flux_x,exchange.wave_speeds,exchange.fallback_reason))
        inner=[counted(hllc_flux(rf[i],lf[i+1],eos)) for i in range(mesh.n-1)]
        end=counted(wall.flux(rf[-1],1,eos))
        flux=[exchange.flux_x]+[tuple(mesh.areas[i+1]*x for x in item[0]) for i,item in enumerate(inner)]+[tuple(mesh.areas[-1]*x for x in end[0])]
        waves=[exchange.wave_speeds]+[item[1] for item in inner]+[end[1]]
        limit,_,unit=cfl_step(mesh,w,[max(abs(s[0]),abs(s[2])) for s in waves],eos,cfl)
        source=[row[2]*(mesh.areas[i+1]-mesh.areas[i]) for i,row in enumerate(w)]
        rhs=[tuple(flux[i][k]-flux[i+1][k]+(source[i] if k==1 else 0.) for k in range(4)) for i in range(mesh.n)]
        _,dv=volume(t);work=-p*dv
        rz=(exchange.outward[0],exchange.outward[2]+work,exchange.outward[3])
        diagnostic=dict(time=t,chamber=list(state),volume=ch.volume,pressure=p,pipe_face=list(lf[0]),
            Y_chamber=Y,outward=list(exchange.outward),star_speed=exchange.wave_speeds[1],
            fallback_reason=exchange.fallback_reason,work_rate=work)
        return dict(pipe=rhs,chamber=rz,limit=limit,unit=unit,exchange=exchange,
                    work=work,external=[-flux[-1][k] for k in (0,2,3)],trace=diagnostic)
    def advance(q,state,op,dt):
        return ([tuple(a+dt*b for a,b in zip(row,rhs)) for row,rhs in zip(q,op['pipe'])],
                tuple(a+dt*b for a,b in zip(state,op['chamber'])))
    def expected(op,dt):return [dt*x+(dt*op['work'] if k==1 else 0.) for k,x in enumerate(op['external'])]
    def stage_res(q0,z0,q1,z1,op,dt):
        return normalized([b-a-e for a,b,e in zip(total(q0,z0),total(q1,z1),expected(op,dt))])
    t=0.;ledger=[];stage_ledger=[];traces=[];work=0.;external=[0.]*3;transfer=[0.]*3;impulse=0.;reversals=[];previous_flow=None
    extrema=dict(rho=min(w[0] for w in initial_w),p=min(w[2] for w in initial_w),T=min(w[2]/(w[0]*eos.R) for w in initial_w),Y_min=min(w[3] for w in initial_w),Y_max=max(w[3] for w in initial_w),m=z[0],U=z[1],F_min=z[2],m_minus_F=z[0]-z[2])
    def observe(q,state,when):
        w,_=validate(q,state,when)
        for k,value in (('rho',min(x[0] for x in w)),('p',min(x[2] for x in w)),('T',min(x[2]/(x[0]*eos.R) for x in w)),('Y_min',min(x[3] for x in w)),('m',state[0]),('U',state[1]),('F_min',state[2]),('m_minus_F',state[0]-state[2])):extrema[k]=min(extrema[k],value)
        extrema['Y_max']=max(extrema['Y_max'],max(x[3] for x in w))
    status='completed';reason='final_time'
    while t<final_time:
        if time.monotonic()-started>wall_limit:status='failed_infrastructure';reason='wall_timeout';break
        try:
            op0=operator(cells,z,t);dt=event_step(op0['limit'],final_time-t)
            for retry in range(13):
                if dt<1e-12 or t+dt==t:raise InvalidState('dt_below_min')
                try:
                    q1,z1=advance(cells,z,op0,dt);validate(q1,z1,t+dt)
                    if method=='MUSCL_SSPRK2':
                        op1=operator(q1,z1,t+dt)
                        if dt>op1['limit']:raise InvalidState('stage_CFL_exceeded')
                        q2,z2=advance(q1,z1,op1,dt);validate(q2,z2,t+2*dt)
                        qnew=[tuple(.5*a+.5*b for a,b in zip(aq,bq)) for aq,bq in zip(cells,q2)]
                        znew=tuple(.5*a+.5*b for a,b in zip(z,z2));validate(qnew,znew,t+dt)
                        ops=(op0,op1);weights=(.5,.5)
                    else:qnew,znew=q1,z1;ops=(op0,);weights=(1.,)
                    break
                except (InvalidState,OverflowError,ZeroDivisionError) as exc:
                    counts['rejected']+=1
                    if retry==12:raise InvalidState('joint_retries_exhausted: '+str(exc))
                    dt/=2
            residuals=[stage_res(cells,z,q1,z1,op0,dt)]
            observe(q1,z1,t+dt)
            if method=='MUSCL_SSPRK2':
                residuals.append(stage_res(q1,z1,q2,z2,op1,dt));observe(q2,z2,t+2*dt)
            observe(qnew,znew,t+dt)
        except (InvalidState,OverflowError,ZeroDivisionError) as exc:
            status='failed_numerical';reason=str(exc);break
        average=[sum(weight*op['exchange'].outward[k] for weight,op in zip(weights,ops)) for k in (0,2,3)]
        for weight,op in zip(weights,ops):
            work+=weight*dt*op['work'];impulse+=weight*dt*op['exchange'].outward[1]
            for k in range(3):external[k]+=weight*dt*op['external'][k]
        for k in range(3):transfer[k]+=dt*average[k]
        if previous_flow is not None and average[0]*previous_flow[1]<0:
            ta,fa=previous_flow;tb=t+.5*dt
            reversals.append(dict(bracket=[ta,tb],linear_estimate=ta-fa*(tb-ta)/(average[0]-fa)))
        if average[0]!=0:previous_flow=(t+.5*dt,average[0])
        cells,z=qnew,znew;t+=dt
        inv=total(cells,z);res=[v-v0-external[k]-(work if k==1 else 0.) for k,(v,v0) in enumerate(zip(inv,initial_total))]
        ledger.append(dict(time=t,dt=dt,inventory=inv,initial=initial_total,external=list(external),work_0D=work,residual=res,normalized=normalized(res),chamber=list(z),volume=volume(t)[0],interface_integral=list(transfer),axial_impulse=impulse))
        stage_ledger.append(dict(dt=dt,limits=[op['limit'] for op in ops],normalized=residuals,CFL=[dt/op['unit'] for op in ops]))
        traces.append(dict(time=t,stages=[op['trace'] for op in ops],mean_outward=average))
    return dict(status=status,reason=reason,time=t,wall_seconds=time.monotonic()-started,method=method,
        cells=cells,primitive=primitives(cells),chamber=list(z),volume=volume(t)[0],initial_chamber=[chamber.mass,chamber.internal_energy,chamber.fresh_mass],
        initial_inventory=initial_total,final_inventory=total(cells,z),ledger=ledger,stage_ledger=stage_ledger,traces=traces,
        counts=counts,fallback_reasons=reasons,extrema=extrema,reversals=reversals,steps=len(ledger))
