"""P1 MUSCL primitive minmod and SSP-RK2; isolated from frozen first-order."""
from bisect import bisect_right
from math import fsum, isfinite
import time
from .eos import IdealGas, InvalidState
from .riemann import hllc_flux
from .solver import inventories, cfl_step, event_step


def minmod(a, b):
    if a == 0 or b == 0 or (a > 0) != (b > 0):
        return 0.
    return a if abs(a) <= abs(b) else b


def reconstruct(mesh, states, boundaries, eos):
    """Two-sided primitive gradients on actual centroids, all-component downgrade."""
    periodic = boundaries == 'periodic'
    length = mesh.faces[-1] - mesh.faces[0]
    left_faces, right_faces, downgraded = [], [], []
    for i, (x, w) in enumerate(zip(mesh.centers, states)):
        if i:
            xl, wl = mesh.centers[i-1], states[i-1]
        elif periodic:
            xl, wl = mesh.centers[-1]-length, states[-1]
        else:
            xl = 2*mesh.faces[0]-x
            wl = boundaries[0].face_state(w, -1, eos)
        if i+1 < mesh.n:
            xr, wr = mesh.centers[i+1], states[i+1]
        elif periodic:
            xr, wr = mesh.centers[0]+length, states[0]
        else:
            xr = 2*mesh.faces[-1]-x
            wr = boundaries[1].face_state(w, 1, eos)
        slope = [minmod((v-l)/(x-xl), (r-v)/(xr-x)) for l,v,r in zip(wl,w,wr)]
        left = tuple(v+s*(mesh.faces[i]-x) for v,s in zip(w,slope))
        right = tuple(v+s*(mesh.faces[i+1]-x) for v,s in zip(w,slope))
        try:
            eos.validate(left); eos.validate(right)
        except (InvalidState, OverflowError):
            left = right = w
            downgraded.append(i)
        left_faces.append(left); right_faces.append(right)
    return left_faces, right_faces, downgraded


def solve(mesh, initial, final_time, boundaries, *, eos=None, cfl=.4,
          sample_interval=None, sensor=None, wall_limit=120., progress=None):
    eos=eos or IdealGas(); started=time.monotonic()
    cells=[tuple(q) for q in initial]
    if len(cells)!=mesh.n or not isfinite(final_time) or final_time<=0:
        raise ValueError('Invalid initial mesh/time')
    def primitive(c):
        return [eos.primitive(tuple(x/v for x in q)) for q,v in zip(c,mesh.volumes)]
    states=primitive(cells)
    periodic=boundaries=='periodic'
    if periodic and mesh.areas[0]!=mesh.areas[-1]:raise ValueError('Periodic areas differ')
    initial_inventory=inventories(cells)
    initial_abs=[fsum(abs(c[k]) for c in cells) for k in range(4)]
    a0=eos.sound_speed(states[0])
    scales=[initial_inventory[0],initial_inventory[0]*a0,initial_inventory[2],initial_inventory[0]]
    boundary_int=[0.]*4;source_int=[0.]*4;boundary_abs=[0.]*4;source_abs=[0.]*4
    hllc_count=0;characteristic_count=0;fallbacks={};fallback_records=[]
    downgrade_count=0;downgrade_records=[];rhs_count=0
    step=0;t=0.;attempt=0;rejections=0;rejection_reasons={}
    history=[];stage_history=[];signals=[];minimum_dt=None;maximum_dt=0.;max_cfl=0.
    sample_number=1;next_sample=sample_interval
    def extreme(ws):
        return [min(w[0] for w in ws),min(w[2] for w in ws),
                min(w[2]/(w[0]*eos.R) for w in ws),min(w[3] for w in ws),
                max(w[3] for w in ws),max(abs(w[1])/eos.sound_speed(w) for w in ws)]
    extrema=extreme(states)
    def merge_extreme(target, values):
        return [min(a,b) if k<4 else max(a,b) for k,(a,b) in enumerate(zip(target,values))]
    def operator(ws, stage):
        nonlocal hllc_count,characteristic_count,downgrade_count,rhs_count
        rhs_count+=1
        lf,rf,down=reconstruct(mesh,ws,boundaries,eos)
        downgrade_count+=len(down)
        for i in down:
            if len(downgrade_records)<100:
                downgrade_records.append(dict(step=step,attempt=attempt,stage=stage,cell=i,reason='inadmissible_reconstructed_face'))
        def counted(left,right,face):
            nonlocal hllc_count
            item=hllc_flux(left,right,eos)
            if item[2]:
                fallbacks[item[2]]=fallbacks.get(item[2],0)+1
                if len(fallback_records)<100:
                    fallback_records.append(dict(step=step,attempt=attempt,stage=stage,face=face,
                        reason=item[2],left=left,right=right,speeds=item[1]))
            else:hllc_count+=1
            return item
        data=[counted(rf[i],lf[i+1],i+1) for i in range(mesh.n-1)]
        if periodic:
            shared=counted(rf[-1],lf[0],0);data=[shared,*data,shared]
        else:
            exterior=[]
            for bc,w,normal,face in ((boundaries[0],lf[0],-1,0),(boundaries[1],rf[-1],1,mesh.n)):
                if bc.kind in ('wall','fixed','outflow'):
                    ghost=bc.face_state(w,normal,eos)
                    item=counted(ghost,w,face) if normal==-1 else counted(w,ghost,face)
                    if bc.kind=='wall':item=((0.,item[0][1],0.,0.),item[1],item[2])
                else:
                    item=bc.flux(w,normal,eos);characteristic_count+=1
                exterior.append(item)
            data=[exterior[0],*data,exterior[1]]
        flux=[tuple(a*x for x in d[0]) for a,d in zip(mesh.areas,data)]
        speeds=[max(abs(d[1][0]),abs(d[1][2])) for d in data]
        limit,limiting,unit=cfl_step(mesh,ws,speeds,eos,cfl)
        source=[w[2]*(mesh.areas[i+1]-mesh.areas[i]) for i,w in enumerate(ws)]
        rhs=[tuple(flux[i][k]-flux[i+1][k]+(source[i] if k==1 else 0.) for k in range(4)) for i in range(mesh.n)]
        return rhs,flux,source,limit,limiting,unit
    def observe_sensor():
        if sensor is not None:
            j=max(0,min(mesh.n-2,bisect_right(mesh.centers,sensor)-1))
            xl,xr=mesh.centers[j:j+2]
            signals.append([t,states[j][2]+(states[j+1][2]-states[j][2])*(sensor-xl)/(xr-xl)])
    observe_sensor();status='completed';reason='final_time';fluxes=[]
    while t<final_time:
        if time.monotonic()-started>wall_limit:status='failed_infrastructure';reason='wall_timeout';break
        try:
            attempt=0
            rhs0,f0,s0,limit0,limiting0,unit0=operator(states,0)
            remaining=final_time-t
            if next_sample is not None:remaining=min(remaining,next_sample-t)
            dt=event_step(limit0,remaining)
            for attempt in range(13):
                if dt<1e-12 or t+dt==t:
                    if final_time-t<=16*2.220446049250313e-16*max(1.,abs(final_time)):
                        t=final_time;dt=0.;break
                    raise InvalidState('dt_below_min')
                try:
                    stage1=[tuple(v+dt*d for v,d in zip(q,rhs)) for q,rhs in zip(cells,rhs0)]
                    w1=primitive(stage1)
                    rhs1,f1,s1,limit1,limiting1,unit1=operator(w1,1)
                    if dt>limit1:raise InvalidState('stage_CFL_exceeded')
                    stage2=[tuple(v+dt*d for v,d in zip(q,rhs)) for q,rhs in zip(stage1,rhs1)]
                    w2=primitive(stage2)
                    candidate=[tuple(.5*v+.5*z for v,z in zip(q,r)) for q,r in zip(cells,stage2)]
                    new_states=primitive(candidate)
                    break
                except (InvalidState,OverflowError,ZeroDivisionError) as exc:
                    rejections+=1;key=str(exc);rejection_reasons[key]=rejection_reasons.get(key,0)+1
                    if attempt==12:raise InvalidState('admissibility_or_CFL_retries_exhausted: '+key)
                    dt/=2
            if dt==0:break
        except (InvalidState,OverflowError,ZeroDivisionError) as exc:
            status='failed_numerical';reason=str(exc);break
        # No stage ledgers were committed during retries. All accepted weights are 1/2.
        prior=inventories(cells);inventory1=inventories(stage1);inventory2=inventories(stage2)
        stage_residuals=[]
        for inv_before,inv_after,flux,source in ((prior,inventory1,f0,s0),(inventory1,inventory2,f1,s1)):
            residue=[inv_after[k]-inv_before[k]+dt*(flux[-1][k]-flux[0][k])-(dt*fsum(source) if k==1 else 0.) for k in range(4)]
            normalized=[abs(residue[k])/max(initial_abs[k],scales[k],dt*(abs(flux[-1][k])+abs(flux[0][k])),dt*fsum(abs(x) for x in source) if k==1 else 0.) for k in range(4)]
            stage_residuals.append(normalized)
        cells=candidate;states=new_states;t+=dt;step+=1
        minimum_dt=dt if minimum_dt is None else min(minimum_dt,dt);maximum_dt=max(maximum_dt,dt)
        max_cfl=max(max_cfl,dt/unit0,dt/unit1)
        for k in range(4):
            boundary_int[k]+=.5*dt*((f0[-1][k]-f0[0][k])+(f1[-1][k]-f1[0][k]))
            boundary_abs[k]+=.5*dt*(abs(f0[-1][k])+abs(f0[0][k])+abs(f1[-1][k])+abs(f1[0][k]))
        source_int[1]+=.5*dt*(fsum(s0)+fsum(s1))
        source_abs[1]+=.5*dt*(fsum(abs(s) for s in s0)+fsum(abs(s) for s in s1))
        inventory=inventories(cells)
        residual=[inventory[k]-initial_inventory[k]+boundary_int[k]-source_int[k] for k in range(4)]
        normalized=[abs(residual[k])/max(initial_abs[k],boundary_abs[k],source_abs[k],scales[k]) for k in range(4)]
        extrema=merge_extreme(extrema,extreme(w1));extrema=merge_extreme(extrema,extreme(w2));extrema=merge_extreme(extrema,extreme(states))
        history.append(dict(step=step,time=t,dt=dt,max_CFL=max(dt/unit0,dt/unit1),cell_limiting_dt=limiting0,
                            inventory=inventory,boundary=list(boundary_int),source=list(source_int),residual=residual,normalized=normalized))
        stage_history.append(dict(step=step,stage1_normalized=stage_residuals[0],stage2_normalized=stage_residuals[1],
                                  stage1_CFL=dt/unit0,stage2_CFL=dt/unit1,stage2_limiting_cell=limiting1,
                                  accepted_dt=dt,stage1_dt_limit=limit0,stage2_dt_limit=limit1,
                                  stage1_extrema=extreme(w1),stage2_extrema=extreme(w2)))
        fluxes=[tuple(.5*a+.5*b for a,b in zip(x,y)) for x,y in zip(f0,f1)]
        if next_sample is not None and t>=next_sample-4e-16:
            observe_sensor();sample_number+=1;next_sample=sample_number*sample_interval
        if progress and step%200==0:progress(step,t)
    return dict(status=status,reason=reason,time=t,steps=step,wall_seconds=time.monotonic()-started,
                cells=cells,primitive=states,temperature=[w[2]/(w[0]*eos.R) for w in states],
                Mach=[w[1]/eos.sound_speed(w) for w in states],face_fluxes=fluxes,
                initial_inventory=initial_inventory,final_inventory=inventories(cells),
                boundary_flux_integral=boundary_int,source_integral=source_int,ledger=history,sensors=signals,
                minimum_dt=minimum_dt,maximum_dt=maximum_dt,max_CFL=max_cfl,rejected_steps=rejections,
                rejection_reasons=rejection_reasons,extrema=dict(zip(('min_rho','min_p','min_T','min_Y','max_Y','max_Mach'),extrema)),
                hllc_flux_count=hllc_count,hlle_fallback_count=sum(fallbacks.values()),fallback_reason=fallbacks,
                characteristic_flux_count=characteristic_count,riemann_flux_count=hllc_count+sum(fallbacks.values()),
                fallback_records=fallback_records,fallback_records_truncated=sum(fallbacks.values())>100,
                downgrade_count=downgrade_count,downgrade_records=downgrade_records,
                downgrade_records_truncated=downgrade_count>100,rhs_count=rhs_count,stage_ledger=stage_history,
                method='MUSCL_SSPRK2')
