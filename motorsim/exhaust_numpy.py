"""NumPy backend: frozen SSPRK2 control flow, batch scalar-equivalent algebra.
Reference: motorsim.exhaust1d; no in-place updates of cached cell arrays.
"""
from math import fsum, isfinite
import numpy as np
from .exhaust_batch import Kernel,primitive as batch_primitive,hllc as batch_hllc
import time
from .exhaust1d import port_flux,IdealGas,InvalidState,Boundary,hllc_flux,reconstruct,cfl_step,event_step

class CachedMesh:
    def __init__(self,mesh):
        self.n=mesh.n;self.faces=mesh.faces;self.centers=mesh.centers
        self.areas=mesh.areas;self.volumes=mesh.volumes;self.widths=mesh.widths
        self.as_dict=mesh.as_dict

def solve_exhaust(mesh,initial,system,end,*,eos=None,cfl=.4,exterior=None,sensors=(),wall_limit=600.,numeric_backend=None,capture_conservation=False):
    kernel_class=Kernel;primitive_fn=batch_primitive;hllc_fn=batch_hllc
    if numeric_backend is not None:
        kernel_class=numeric_backend.Kernel;primitive_fn=numeric_backend.primitive;hllc_fn=numeric_backend.hllc
    eos=eos or IdealGas();exterior=exterior or Boundary('nonreflecting',state=(100000/(eos.R*300),0.,100000.,0.))
    mesh=CachedMesh(mesh)
    kernel=kernel_class(mesh,eos);fallback_faces=[];downgrade_cells=[];inventory_cache={}
    cache={}
    start=time.monotonic();q=np.array(initial,dtype=np.float64);z=list(system.initial)
    events=system.events(mesh.areas[0],end);event_index=0;t=0.
    counts=dict(rhs=0,HLLC=0,HLLE=0,characteristic=0,rejected=0,downgrades=0)
    # R5 fused buffers (single allocation, reused per RHS) - enabled only for R5 fused backend
    use_fused = numeric_backend is not None and getattr(numeric_backend, 'FUSED_ENABLED', False) and hasattr(numeric_backend, 'fused_interior') and exterior.kind == 'nonreflecting'
    if use_fused:
        n = mesh.n
        w_buf = np.empty((n,4), dtype=np.float64)
        lf_buf = np.empty((n,4), dtype=np.float64)
        rf_buf = np.empty((n,4), dtype=np.float64)
        flux_interior_buf = np.empty((n-1,4), dtype=np.float64)
        speeds_interior_buf = np.empty((n-1,3), dtype=np.float64)
        codes_buf = np.empty(n-1, dtype=np.int64)
        bad_buf = np.empty(n, dtype=np.bool_)
        # exterior primitive for fused hi calculation
        if exterior.state is not None:
            ext_state_arr = np.array(exterior.state, dtype=np.float64)
        else:
            ext_state_arr = np.array((exterior.p0/(eos.R*exterior.T0), 0., exterior.p0, exterior.Y0), dtype=np.float64)
        volumes_np = np.array(kernel.volumes, dtype=np.float64)
        # dl etc already 2D (n,1)
    def primitive(cells):
        key=id(cells)
        if key in cache and cache[key][0] is cells:return cache[key][1]
        rows=primitive_fn(cells,kernel.volumes,eos)
        if len(cache)>=4:del cache[next(iter(cache))]
        cache[key]=(cells,rows)
        return rows
    def validate(cells,state,when):system.validate(state,when,eos);return primitive(cells)
    def inventory(cells,state):
        key=id(cells)
        if key not in inventory_cache or inventory_cache[key][0] is not cells:
            values=[fsum(cells[:,j]) for j in (0,2,3)]
            if len(inventory_cache)>=4:del inventory_cache[next(iter(inventory_cache))]
            inventory_cache[key]=(cells,values)
        return [fsum(state[k::3])+v for k,v in enumerate(inventory_cache[key][1])]
    w=validate(q,z,t);initial_inventory=inventory(q,z);scale=(initial_inventory[0],initial_inventory[1],initial_inventory[0])
    sensor_indices=[min(range(mesh.n),key=lambda i:abs(mesh.centers[i]-x)) for x in sensors]
    def rhs(cells,state,when):
        if use_fused:
            counts['rhs']+=1
            # 0D validation (chamber) before fused primitive
            system.validate(state,when,eos)
            try:
                numeric_backend.fused_interior(cells, volumes_np, kernel.dl, kernel.dr, kernel.left_offset, kernel.right_offset, eos.gamma, eos.R, ext_state_arr, w_buf, lf_buf, rf_buf, bad_buf, flux_interior_buf, speeds_interior_buf, codes_buf)
            except ValueError as exc:
                raise InvalidState(str(exc))
            ws = w_buf
            left = lf_buf
            right = rf_buf
            down = np.flatnonzero(bad_buf).tolist()
            counts['downgrades']+=len(down)
            if down:
                downgrade_cells.append(dict(rhs=counts['rhs'],time=when,cells=down))
            ch=system.chamber(state,when);ch.thermodynamics(eos)
            port=port_flux(ch,tuple(left[0].tolist()),system.area(when),mesh.areas[0],eos=eos)
            counts['HLLC']+=port['HLLC'];counts['HLLE']+=port['HLLE']
            if port['HLLE']:fallback_faces.append(dict(rhs=counts['rhs'],time=when,face=0,reason='frozen_port_HLLE',evaluations=port['HLLE']))
            flux=np.empty((mesh.n+1,4));speeds=np.empty(mesh.n+1)
            flux[0]=port['flux'];speeds[0]=max(abs(port['speeds'][0]),abs(port['speeds'][2]))
            # handle interior HLLC fallback via reference for exact equivalence
            reasons = {}
            fallback_speeds = {}
            f_interior = flux_interior_buf
            s_interior = speeds_interior_buf
            for idx in np.flatnonzero(codes_buf):
                left_t = tuple(rf_buf[idx].tolist())
                right_t = tuple(lf_buf[idx+1].tolist())
                f0, s0, r0 = hllc_flux(left_t, right_t, eos)
                f_interior[idx] = f0
                # s0 is tuple (sl, sm, sr) where sm may be None
                s_interior[idx,0] = s0[0]
                s_interior[idx,1] = np.nan if s0[1] is None else s0[1]
                s_interior[idx,2] = s0[2]
                if r0:
                    reasons[int(idx)] = r0
                    fallback_speeds[int(idx)] = s0
            # Now counts: HLLE = len(reasons) where reason string exists, HLLC = n-1 - len(reasons)
            # For fused, we need to count similarly to original: only those with reason string count as HLLE
            counts['HLLE']+=len(reasons);counts['HLLC']+=mesh.n-1-len(reasons)
            for i,reason in reasons.items():
                fallback_faces.append(dict(rhs=counts['rhs'],time=when,face=i+1,reason=reason,speeds=fallback_speeds[i]))
            flux[1:-1]=kernel.areas[1:-1,None]*f_interior;speeds[1:-1]=np.maximum(np.abs(s_interior[:,0]),np.abs(s_interior[:,2]))
            exterior_face=tuple(right[-1].tolist())
            f,s,reason=exterior.flux(exterior_face,1,eos)
            if exterior.kind in ('wall','fixed','outflow'):counts['HLLE' if reason else 'HLLC']+=1
            else:counts['characteristic']+=1
            if reason:fallback_faces.append(dict(rhs=counts['rhs'],time=when,face=mesh.n,reason=reason,speeds=s))
            flux[-1]=tuple(mesh.areas[-1]*v for v in f);speeds[-1]=max(abs(s[0]),abs(s[2]))
            limit,_,unit=kernel.cfl(ws,speeds,cfl)
            dq=flux[:-1]-flux[1:];dq[:,1]+=ws[:,2]*kernel.area_delta
            dz,external,terms=system.source(state,when,eos)
            for k in range(3):dz[3*system.cylinder+k]+=port['exchange'][k];external[k]-=flux[-1][(0,2,3)[k]]
            boundary_state=exterior.face_state(exterior_face,1,eos)
            return dict(dq=dq,dz=dz,external=external,terms=terms,port=port,limit=limit,unit=unit,
                        trace=dict(time=when,angle=system.angle(when),area=port['area'],chamber=list(state),volume=ch.volume,
                        pressure=ch.thermodynamics(eos)[1],pipe_face=left[0].tolist(),exchange=port['exchange'],
                        outlet=boundary_state,open_reaction=port['open_reaction'],closed_reaction=port['closed_reaction']))
        counts['rhs']+=1;ws=validate(cells,state,when)
        left,right,down=kernel.reconstruct(ws,(Boundary('outflow'),exterior));counts['downgrades']+=len(down)
        if down:downgrade_cells.append(dict(rhs=counts['rhs'],time=when,cells=down))
        ch=system.chamber(state,when);ch.thermodynamics(eos)
        port=port_flux(ch,tuple(left[0].tolist()),system.area(when),mesh.areas[0],eos=eos)
        counts['HLLC']+=port['HLLC'];counts['HLLE']+=port['HLLE']
        if port['HLLE']:fallback_faces.append(dict(rhs=counts['rhs'],time=when,face=0,reason='frozen_port_HLLE',evaluations=port['HLLE']))
        flux=np.empty((mesh.n+1,4));speeds=np.empty(mesh.n+1)
        flux[0]=port['flux'];speeds[0]=max(abs(port['speeds'][0]),abs(port['speeds'][2]))
        f,s,reasons,fallback_speeds=hllc_fn(right[:-1],left[1:],eos)
        counts['HLLE']+=len(reasons);counts['HLLC']+=mesh.n-1-len(reasons)
        for i,reason in reasons.items():fallback_faces.append(dict(rhs=counts['rhs'],time=when,face=i+1,reason=reason,speeds=fallback_speeds[i]))
        flux[1:-1]=kernel.areas[1:-1,None]*f;speeds[1:-1]=np.maximum(np.abs(s[:,0]),np.abs(s[:,2]))
        exterior_face=tuple(right[-1].tolist())
        f,s,reason=exterior.flux(exterior_face,1,eos)
        if exterior.kind in ('wall','fixed','outflow'):counts['HLLE' if reason else 'HLLC']+=1
        else:counts['characteristic']+=1
        if reason:fallback_faces.append(dict(rhs=counts['rhs'],time=when,face=mesh.n,reason=reason,speeds=s))
        flux[-1]=tuple(mesh.areas[-1]*v for v in f);speeds[-1]=max(abs(s[0]),abs(s[2]))
        limit,_,unit=kernel.cfl(ws,speeds,cfl)
        dq=flux[:-1]-flux[1:];dq[:,1]+=ws[:,2]*kernel.area_delta
        dz,external,terms=system.source(state,when,eos)
        for k in range(3):dz[3*system.cylinder+k]+=port['exchange'][k];external[k]-=flux[-1][(0,2,3)[k]]
        boundary_state=exterior.face_state(exterior_face,1,eos)
        return dict(dq=dq,dz=dz,external=external,terms=terms,port=port,limit=limit,unit=unit,
                    trace=dict(time=when,angle=system.angle(when),area=port['area'],chamber=list(state),volume=ch.volume,
                    pressure=ch.thermodynamics(eos)[1],pipe_face=left[0].tolist(),exchange=port['exchange'],
                    outlet=boundary_state,open_reaction=port['open_reaction'],closed_reaction=port['closed_reaction']))
    def advance(cells,state,op,dt):return cells+dt*op['dq'],[a+dt*b for a,b in zip(state,op['dz'])]
    history=[];stages=[];snapshots=[];conservation_history=[];external=[0.]*3;port_integral=[0.]*3;rejections={};hit_events=[]
    def extremes(rows):
        return dict(rho=float(np.min(rows[:,0])),p=float(np.min(rows[:,2])),T=float(np.min(rows[:,2]/(rows[:,0]*eos.R))),
            Y_min=float(np.min(rows[:,3])),Y_max=float(np.max(rows[:,3])))
    extrema=extremes(w)
    def observe(cells,state,when):
        rows=validate(cells,state,when)
        for key,value in extremes(rows).items():extrema[key]=(max if key=='Y_max' else min)(extrema[key],value)
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
                    qnew=.5*q+.5*q2;znew=[.5*a+.5*b for a,b in zip(z,z2)]
                    validate(qnew,znew,t+dt);break
                except (ValueError,OverflowError,ZeroDivisionError) as exc:
                    counts['rejected']+=1;key=str(exc);rejections[key]=rejections.get(key,0)+1
                    if retry==12:raise InvalidState('joint_retries_exhausted: '+key)
                    dt*=.5
            inv0=inventory(q,z);inv1=inventory(q1,z1);inv2=inventory(q2,z2)
            stage_residues=[]
            for a,b,op in ((inv0,inv1,op0),(inv1,inv2,op1)):
                residue=max(abs(bv-av-dt*ev)/sv for av,bv,ev,sv in zip(a,b,op['external'],scale))
                stage_residues.append(residue)
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
        if capture_conservation:
            # Durable primary terms for an independent finite-volume balance audit.
            # These diagnostics do not participate in the numerical update.
            conservation_history.append(dict(
                time_start=t-dt, time_end=t, dt=dt,
                inventory_start=inv0, inventory_stage1=inv1, inventory_stage2=inv2,
                inventory_accepted=inv,
                external_rate_stage_a=list(op0['external']),
                external_rate_stage_b=list(op1['external']),
                cumulative_external=external.copy(),
                stage_residuals=stage_residues, global_residual=res))
        ch=system.chamber(z,t);rho,p,T,Y=ch.thermodynamics(eos)
        history.append(dict(time=t,angle=system.angle(t),dt=dt,chamber=z.copy(),cylinder=(p,T,ch.mass,Y),area=system.area(t),
            sensors=[(w[i][2],w[i][1],w[i][1]/eos.sound_speed(w[i]),w[i][3]) for i in sensor_indices],
            port_pressure=op1['trace']['pipe_face'][2],port_Mach=op1['trace']['pipe_face'][1]/eos.sound_speed(op1['trace']['pipe_face']),
            exchange=[.5*(op0['port']['exchange'][k]+op1['port']['exchange'][k]) for k in range(3)],
            external=external.copy(),port_integral=port_integral.copy(),inventory=inv,residual=res))
        stages.append(dict(dt=dt,limits=[op0['limit'],op1['limit']],traces=[op0['trace'],op1['trace']]))
        if t>=next_snapshot:
            snapshots.append(dict(time=t,angle=system.angle(t),primitive=w.tolist()));next_snapshot+=end/8
    result=dict(status=status,reason=reason,time=t,wall_seconds=time.monotonic()-start,cells=q.tolist(),state=z,primitive=primitive(q).tolist(),
        initial_inventory=initial_inventory,final_inventory=inventory(q,z),external=external,port_integral=port_integral,
        max_global_residual=max_global_residual,max_stage_residual=max_stage_residual,max_CFL=max_CFL,extrema=extrema,
        counts=counts,rejections=rejections,events=events,hit_events=hit_events,history=history,stages=stages,snapshots=snapshots,
        sensor_positions=[mesh.centers[i] for i in sensor_indices],mesh=mesh.as_dict(),
        batch_observability=dict(HLLE_faces=fallback_faces,MUSCL_downgrade_cells=downgrade_cells))
    if capture_conservation:
        result["conservation_history"] = conservation_history
    return result
