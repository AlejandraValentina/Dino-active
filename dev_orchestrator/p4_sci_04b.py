"""P4-SCI-04B B2 finite amplitude + C2 finite chamber"""
import math, time, json
from bisect import bisect_right
from pathlib import Path
from math import fsum, isfinite
from motorsim.gas1d.eos import IdealGas, InvalidState
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.second_order import reconstruct
from motorsim.gas1d.solver import cfl_step, event_step, inventories
from motorsim.coupling import ChamberState, interface_flux
from dev_orchestrator.reference.exact_riemann import ExactRiemann

EOS = IdealGas(R=287.0, gamma=1.35)
P0 = 100000.0
T0 = 300.0
RHO0 = P0/(EOS.R*T0)
C0 = math.sqrt(EOS.gamma*P0/RHO0)
Z0 = RHO0*C0

# B2 pre-registered finite amplitude
B2_EPS = 8000.0  # Pa 8% p0, Mach ~0.06 subsonic
B2_SIGMA = 0.025
B2_X0 = 0.30
B2_L_TRUNC = 1.0
B2_L_EXT = 2.0
B2_DIAM_MM = 20.0
B2_AREA = math.pi*(B2_DIAM_MM*0.001)**2/4
B2_SENSOR = 0.80
B2_CFL = 0.4
B2_N_LEVELS = [50,100,200]
B2_T_FINAL = 0.004

# C2 config
C2_AREA = B2_AREA  # fixed aperture equal to duct area
C2_VOLUME = 0.0001
C2_L_DUCT = 0.5
C2_N_DUCT = 100
C2_SENSOR = 0.25  # sensor downstream in duct
C2_T_FINAL = 0.003
C2_CFL_LEVELS = [0.4, 0.2, 0.1]  # temporal refinement, N fixed

def b2_primitive_finite(x):
    dp = B2_EPS*math.exp(-((x-B2_X0)/B2_SIGMA)**2)
    p = P0+dp
    # exact isentropic for pure right-going
    p_rel = p/P0
    g = EOS.gamma
    rho = RHO0 * (p_rel**(1/g))
    # c increase
    c = C0 * (p_rel**((g-1)/(2*g)))
    u = 2*C0/(g-1)*(p_rel**((g-1)/(2*g))-1)
    y=0.2
    return (rho,u,p,y)

def b2_build_initial(mesh, trunc=True):
    cells=[]
    for xm, vol in zip(mesh.centers, mesh.volumes):
        if trunc or xm <= B2_L_TRUNC:
            w = b2_primitive_finite(xm)
        else:
            w = (RHO0,0.0,P0,0.2)
        cells.append(tuple(vol*q for q in EOS.conservative(w)))
    return cells

# Reuse B1 solver but with B2 pulse
# We will import solve_b1_with_sensor from p4_sci_04a and adapt via monkey patch of primitive
from dev_orchestrator.p4_sci_04a import solve_b1_with_sensor as _solve_b1
# But solve_b1 uses its own build_initial via closure; we will create wrapper that calls generic solver

def solve_b2_generic(mesh, initial, boundaries, t_final=B2_T_FINAL, sensor=B2_SENSOR, cfl=B2_CFL):
    # copy of solve_b1_with_sensor but generic
    from motorsim.gas1d.second_order import reconstruct
    eos = EOS
    cells = [tuple(q) for q in initial]
    def primitive(cells_):
        return [eos.primitive(tuple(x/v for x in row)) for row,v in zip(cells_, mesh.volumes)]
    states = primitive(cells)
    initial_inventory = inventories(cells)
    initial_abs = [fsum(abs(c[k]) for c in cells) for k in range(4)]
    a0 = eos.sound_speed(states[0])
    scales = [initial_inventory[0], initial_inventory[0]*a0, initial_inventory[2], initial_inventory[0]]
    boundary_int=[0.]*4; boundary_abs=[0.]*4; source_int=[0.]*4; source_abs=[0.]*4
    import time as _time
    started=_time.monotonic()
    hllc_count=0; characteristic_count=0; fallbacks={}; downgrade_count=0
    step=0; t=0.0; rejections=0; history=[]; sensor_history=[]
    minimum_dt=None; maximum_dt=0.0; max_cfl=0.0
    def extrema(ws):
        return [min(w[0] for w in ws), min(w[2] for w in ws), min(w[2]/(w[0]*eos.R) for w in ws), min(w[3] for w in ws), max(w[3] for w in ws), max(abs(w[1])/eos.sound_speed(w) for w in ws)]
    cur_extrema=extrema(states)
    def operator(ws, stage_idx):
        nonlocal hllc_count, characteristic_count, downgrade_count
        lf, rf, down = reconstruct(mesh, ws, boundaries, eos)
        downgrade_count+=len(down)
        data=[]
        for i in range(mesh.n-1):
            item = hllc_flux(rf[i], lf[i+1], eos)
            data.append(item)
            if item[2]: fallbacks[item[2]]=fallbacks.get(item[2],0)+1
            else: hllc_count+=1
        if boundaries=='periodic':
            shared = hllc_flux(rf[-1], lf[0], eos)
            if shared[2]: fallbacks[shared[2]]=fallbacks.get(shared[2],0)+1
            else: hllc_count+=1
            data=[shared,*data,shared]
        else:
            exterior=[]
            for bc,w,normal,face in ((boundaries[0], lf[0], -1, 0),(boundaries[1], rf[-1], 1, mesh.n)):
                if bc.kind in ('wall','fixed','outflow'):
                    ghost=bc.face_state(w,normal,eos)
                    item = hllc_flux(ghost,w,eos) if normal==-1 else hllc_flux(w,ghost,eos)
                    if bc.kind=='wall': item=((0.,item[0][1],0.,0.),item[1],item[2])
                    if item[2]: fallbacks[item[2]]=fallbacks.get(item[2],0)+1
                    else: hllc_count+=1
                else:
                    item=bc.flux(w,normal,eos); characteristic_count+=1
                exterior.append(item)
            data=[exterior[0],*data,exterior[1]]
        flux=[tuple(a*x for x in d[0]) for a,d in zip(mesh.areas,data)]
        speeds=[max(abs(d[1][0]),abs(d[1][2])) for d in data]
        limit,limiting,unit=cfl_step(mesh,ws,speeds,eos,cfl)
        source=[w[2]*(mesh.areas[i+1]-mesh.areas[i]) for i,w in enumerate(ws)]
        rhs=[tuple(flux[i][k]-flux[i+1][k]+(source[i] if k==1 else 0.) for k in range(4)) for i in range(mesh.n)]
        return rhs,flux,source,limit,limiting,unit,data
    def sensor_sample(ws, time_val):
        if sensor is not None:
            j=max(0,min(mesh.n-2, bisect_right(mesh.centers,sensor)-1))
            xl,xr=mesh.centers[j:j+2]
            wj=ws[j]; wj1=ws[j+1]
            frac=(sensor-xl)/(xr-xl) if xr!=xl else 0
            p=wj[2]+(wj1[2]-wj[2])*frac
            u=wj[1]+(wj1[1]-wj[1])*frac
            # also Mach for B2 metrics
            rho=wj[0]+(wj1[0]-wj[0])*frac
            # compute Mach via sound
            a=math.sqrt(eos.gamma*p/rho)
            mach=abs(u)/a if a!=0 else 0
            sensor_history.append((time_val,p,u,mach))
    sensor_sample(states,t)
    status='completed'; reason='final_time'
    while t < t_final:
        if _time.monotonic()-started>120:
            status='failed_infrastructure'; reason='wall_timeout'; break
        rhs0,f0,s0,limit0,limiting0,unit0,_ = operator(states,0)
        dt=event_step(limit0, t_final-t)
        accepted=False
        for attempt in range(13):
            if dt<1e-12 or t+dt==t:
                if t_final-t<=16*2.22e-16*max(1.,abs(t_final)):
                    t=t_final; accepted=True; dt=0; break
                raise RuntimeError('dt_below_min')
            try:
                stage1=[tuple(v+dt*d for v,d in zip(q,rhs)) for q,rhs in zip(cells,rhs0)]
                w1=primitive(stage1)
                rhs1,f1,s1,limit1,limiting1,unit1,_ = operator(w1,1)
                if dt>limit1: raise ValueError('stage_CFL_exceeded')
                stage2=[tuple(v+dt*d for v,d in zip(q,rhs)) for q,rhs in zip(stage1,rhs1)]
                w2=primitive(stage2)
                candidate=[tuple(0.5*v+0.5*z for v,z in zip(q,r)) for q,r in zip(cells,stage2)]
                new_states=primitive(candidate)
                accepted=True; break
            except Exception as exc:
                rejections+=1
                if attempt==12:
                    status='failed_numerical'; reason=str(exc); accepted=False; break
                dt/=2
        if dt==0: break
        if not accepted:
            if status=='completed': status='failed_numerical'; reason='step_rejected'
            break
        cells=candidate; states=new_states; t+=dt; step+=1
        minimum_dt=dt if minimum_dt is None else min(minimum_dt,dt); maximum_dt=max(maximum_dt,dt); max_cfl=max(max_cfl, dt/unit0, dt/unit1)
        for k in range(4):
            boundary_int[k]+=0.5*dt*((f0[-1][k]-f0[0][k])+(f1[-1][k]-f1[0][k]))
        source_int[1]+=0.5*dt*(fsum(s0)+fsum(s1))
        for k in range(4):
            boundary_abs[k]+=0.5*dt*(abs(f0[-1][k])+abs(f0[0][k])+abs(f1[-1][k])+abs(f1[0][k]))
        source_abs[1]+=0.5*dt*(fsum(abs(s) for s in s0)+fsum(abs(s) for s in s1))
        sensor_sample(states,t)
        cur_extrema=[min(a,b) if i<4 else max(a,b) for i,(a,b) in enumerate(zip(cur_extrema,extrema(w1)))]
        cur_extrema=[min(a,b) if i<4 else max(a,b) for i,(a,b) in enumerate(zip(cur_extrema,extrema(w2)))]
        cur_extrema=[min(a,b) if i<4 else max(a,b) for i,(a,b) in enumerate(zip(cur_extrema,extrema(states)))]
        history.append({"time":t,"dt":dt,"max_CFL":max(dt/unit0,dt/unit1)})
    wall_seconds=_time.monotonic()-started
    final_inventory=inventories(cells)
    residual=[final_inventory[k]-initial_inventory[k]+boundary_int[k]-source_int[k] for k in range(4)]
    normalized=[abs(residual[k])/max(initial_abs[k],boundary_abs[k],source_abs[k],scales[k]) for k in range(4)]
    return {
        "status":status,"reason":reason,"time":t,"steps":step,"wall_seconds":wall_seconds,
        "cells":cells,"primitive":states,"minimum_dt":minimum_dt,"maximum_dt":maximum_dt,"max_CFL":max_cfl,
        "rejected_steps":rejections,"initial_inventory":initial_inventory,"final_inventory":final_inventory,
        "boundary_flux_integral":boundary_int,"source_integral":source_int,"residual":residual,"normalized_residual":normalized,"max_normalized":max(normalized),
        "extrema":dict(zip(("min_rho","min_p","min_T","min_Y","max_Y","max_Mach"),cur_extrema)),
        "sensor_history":sensor_history,"hllc_count":hllc_count,"characteristic_count":characteristic_count,"fallbacks":fallbacks,"history":history,
    }

def b2_compute_characteristics(sensor_history):
    # sensor_history entries (t,p,u,mach)
    # compute L_out/in as before using base Z0, also Mach etc
    outs=[]
    for t,p,u,mach in sensor_history:
        dp=p-P0; du=u
        L_out=du+dp/Z0; L_in=du-dp/Z0
        outs.append((t,L_out,L_in,p,u,mach))
    return outs

def b2_truncated_vs_extended_metrics(char_trunc, char_ext):
    # similar to B1 but now amplitude larger; compute windows
    c0=C0; sigma=B2_SIGMA; sensor=B2_SENSOR; x0=B2_X0; Ltr=B2_L_TRUNC; Lext=B2_L_EXT
    t_out=(sensor-x0)/c0
    t_ref_trunc=((Ltr-x0)+(Ltr-sensor))/c0
    t_ref_ext=((Lext-x0)+(Lext-sensor))/c0
    win_out=(t_out-3*sigma/c0, t_out+3*sigma/c0)
    win_refl=(t_ref_trunc-3*sigma/c0, t_ref_trunc+3*sigma/c0)
    valid_end=t_ref_ext-3*sigma/c0-2*(Ltr/min(B2_N_LEVELS))/c0
    def window_vals(hist, win):
        return [(t,Lo,Li,p,u,m) for t,Lo,Li,p,u,m in hist if win[0]<=t<=win[1]]
    trunc_out=window_vals(char_trunc, win_out)
    trunc_refl=window_vals(char_trunc, win_refl)
    ext_refl=window_vals(char_ext, win_refl)
    def max_abs(vals, idx):
        return max(abs(v[idx]) for v in vals) if vals else 0.0
    amp_out_trunc=max_abs(trunc_out,1)
    amp_in_trunc_refl=max_abs(trunc_refl,2)
    amp_in_ext_refl=max_abs(ext_refl,2)
    eps=1e-12
    refl_ratio_trunc=amp_in_trunc_refl/max(amp_out_trunc,eps)
    refl_ratio_ext=amp_in_ext_refl/max(amp_out_trunc,eps)
    p_refl_trunc=Z0*amp_in_trunc_refl/2
    p_refl_ext=Z0*amp_in_ext_refl/2
    def arrival(hist, thr=100.0): # threshold scaled for finite amplitude: 1% of EPS ~80 Pa
        for i in range(1,len(hist)):
            t0,_,_,p0,_,_=hist[i-1]; t1,_,_,p1,_,_=hist[i]
            if p0 < P0+thr <= p1:
                frac=(P0+thr-p0)/(p1-p0) if p1!=p0 else 0
                return t0+frac*(t1-t0)
        return None
    arr_trunc=arrival(char_trunc, thr=0.01*B2_EPS)
    arr_ext=arrival(char_ext, thr=0.01*B2_EPS)
    # error vs extended max difference in valid window
    # interp ext onto trunc times
    ext_times=[t for t,_,_,_,_,_ in char_ext]
    ext_p=[p for _,_,_,p,_,_ in char_ext]
    ext_u=[u for _,_,_,_,u,_ in char_ext]
    ext_mach=[m for _,_,_,_,_,m in char_ext]
    def interp_ext(tq):
        if tq<=ext_times[0]: return ext_p[0],ext_u[0],ext_mach[0]
        if tq>=ext_times[-1]: return ext_p[-1],ext_u[-1],ext_mach[-1]
        import bisect
        idx=bisect.bisect_left(ext_times,tq)
        t0=ext_times[idx-1]; t1=ext_times[idx]
        frac=(tq-t0)/(t1-t0) if t1!=t0 else 0
        return ext_p[idx-1]+frac*(ext_p[idx]-ext_p[idx-1]), ext_u[idx-1]+frac*(ext_u[idx]-ext_u[idx-1]), ext_mach[idx-1]+frac*(ext_mach[idx]-ext_mach[idx-1])
    err_p=0; err_u=0; err_mach=0; err_Lout=0; err_Lin=0; max_diff=0; sum_sq=0; count=0
    for t,Lo,Li,p,u,m in char_trunc:
        if not (0<=t<=valid_end): continue
        p_e,u_e,m_e=interp_ext(t)
        Lo_e = u_e + (p_e-P0)/Z0
        Li_e = u_e - (p_e-P0)/Z0
        diff_p=abs(p-p_e); diff_u=abs(u-u_e); diff_m=abs(m-m_e); diff_Lo=abs(Lo-Lo_e); diff_Li=abs(Li-Li_e)
        err_p=max(err_p,diff_p); err_u=max(err_u,diff_u); err_mach=max(err_mach,diff_m); err_Lout=max(err_Lout,diff_Lo); err_Lin=max(err_Lin,diff_Li)
        max_diff=max(max_diff,diff_p)
        sum_sq+=diff_p**2; count+=1
    l2 = math.sqrt(sum_sq/count) if count else 0
    # L1 approx mean abs
    # we already have max
    return {
        "t_out":t_out,"t_ref_trunc":t_ref_trunc,"t_ref_ext":t_ref_ext,"valid_end":valid_end,"window_out":win_out,"window_refl":win_refl,
        "amp_out_trunc":amp_out_trunc,"amp_in_trunc_refl":amp_in_trunc_refl,"amp_in_ext_refl":amp_in_ext_refl,
        "reflection_ratio_trunc":refl_ratio_trunc,"reflection_ratio_ext":refl_ratio_ext,"p_reflected_trunc":p_refl_trunc,"p_reflected_ext":p_refl_ext,
        "arrival_trunc":arr_trunc,"arrival_ext":arr_ext,
        "err_vs_ext_p_max":err_p,"err_vs_ext_u_max":err_u,"err_vs_ext_mach_max":err_mach,"err_vs_ext_Lout_max":err_Lout,"err_vs_ext_Lin_max":err_Lin,
        "max_diff":max_diff,"l2_diff_p":l2,"valid_count":count,
    }

def run_b2():
    results=[]
    start_all=time.perf_counter()
    for N in B2_N_LEVELS:
        tic=time.perf_counter()
        mesh_trunc=uniform_mesh(N, length=B2_L_TRUNC, area=B2_AREA)
        N_ext=int(round(N*B2_L_EXT/B2_L_TRUNC))
        mesh_ext=uniform_mesh(N_ext, length=B2_L_EXT, area=B2_AREA)
        init_trunc=b2_build_initial(mesh_trunc, trunc=True)
        init_ext=b2_build_initial(mesh_ext, trunc=False)
        dx_trunc=mesh_trunc.widths[0]; dx_ext=mesh_ext.widths[0]
        left=Boundary('wall')
        right_trunc=Boundary('nonreflecting', p0=P0,T0=T0,Y0=0.2)
        right_ext=Boundary('wall')
        res_trunc=solve_b2_generic(mesh_trunc, init_trunc, (left,right_trunc))
        res_ext=solve_b2_generic(mesh_ext, init_ext, (left,right_ext))
        char_trunc=b2_compute_characteristics(res_trunc["sensor_history"])
        char_ext=b2_compute_characteristics(res_ext["sensor_history"])
        metrics=b2_truncated_vs_extended_metrics(char_trunc, char_ext)
        toc=time.perf_counter()
        results.append({
            "N":N,"N_ext":N_ext,"dx_trunc":dx_trunc,"dx_ext":dx_ext,"CFL":B2_CFL,
            "dt_min_trunc":res_trunc["minimum_dt"],"dt_max_trunc":res_trunc["maximum_dt"],
            "dt_min_ext":res_ext["minimum_dt"],"dt_max_ext":res_ext["maximum_dt"],
            "wall_seconds_trunc":res_trunc["wall_seconds"],"wall_seconds_ext":res_ext["wall_seconds"],"wall_seconds_total":toc-tic,
            "status_trunc":res_trunc["status"],"status_ext":res_ext["status"],"steps_trunc":res_trunc["steps"],"steps_ext":res_ext["steps"],
            "max_normalized_trunc":res_trunc["max_normalized"],"max_normalized_ext":res_ext["max_normalized"],
            "extrema_trunc":res_trunc["extrema"],"extrema_ext":res_ext["extrema"],
            "metrics":metrics,"sensor_count_trunc":len(char_trunc),"sensor_count_ext":len(char_ext),
        })
    total=time.perf_counter()-start_all
    return results, total

# ---------------- C2 ----------------

def c2_chamber_state(p,T,Y,V=C2_VOLUME):
    eos=EOS
    m=p*V/(eos.R*T)
    U=m*eos.cv*T
    fresh=Y*m
    return ChamberState(m,U,fresh,V)

def solve_c2_one(N, cfl, p_chamber, T_chamber, Y_chamber, p_duct, T_duct, Y_duct, t_final=C2_T_FINAL):
    # mesh fixed
    mesh=uniform_mesh(N, length=C2_L_DUCT, area=C2_AREA)
    eos=EOS
    # duct initial uniform
    rho_d=p_duct/(eos.R*T_duct)
    w_duct=(rho_d,0.0,p_duct,Y_duct)
    duct_cells=[tuple(vol*q for q in eos.conservative(w_duct)) for vol in mesh.volumes]
    chamber0=c2_chamber_state(p_chamber, T_chamber, Y_chamber)
    # state chamber as list [mass, U, fresh]
    z0=[chamber0.mass, chamber0.internal_energy, chamber0.fresh_mass]
    volume=C2_VOLUME
    # need primitive helper
    def primitive(cells_):
        return [eos.primitive(tuple(x/v for x in row)) for row,v in zip(cells_, mesh.volumes)]
    states=primitive(duct_cells)
    # initial inventories for conservation
    initial_duct_inventory=inventories(duct_cells)
    initial_chamber_inventory=(z0[0],0.0,z0[1],z0[2]) # not exactly but for total we sum chamber mass/U/fresh plus duct
    # total initial mass = chamber mass + sum duct masses
    # We'll compute total conserved check later
    chamber_hist=[]
    duct_hist=[]
    sensor_idx = min(range(mesh.n), key=lambda i: abs(mesh.centers[i]-C2_SENSOR))
    # storage for interface trace
    interface_hist=[]
    # sensor history
    sensor_hist=[]
    import time as _time
    started=_time.monotonic()
    # helper to get chamber thermodynamics
    def chamber_thermo(z):
        m, U, fresh = z
        rho = m/volume
        p = (eos.gamma-1)*U/volume
        T = U/(m*eos.cv) if m!=0 else 0
        Y = fresh/m if m!=0 else 0
        # validate
        # eos.validate((rho,0.,p,Y))
        return rho,p,T,Y, m, U, fresh
    # initial sensor sample
    # duct states already
    def record(z, cells_, states_, time_val, flux_info=None):
        # chamber
        rho_c,p_c,T_c,Y_c,m_c,U_c,fresh_c = chamber_thermo(z)
        chamber_hist.append((time_val, p_c,T_c,m_c,U_c,Y_c))
        # duct sensor
        w = states_[sensor_idx]
        sensor_hist.append((time_val, w[2], w[1], w[0], w[3], w[1]/eos.sound_speed(w)))
        # first cell
        w0=states_[0]
        duct_hist.append((time_val, w0[2], w0[1], w0[0]))
        if flux_info is not None:
            # flux_info contains interface flux details
            interface_hist.append((time_val, flux_info))
        else:
            # no flux yet
            pass
    record(z0, duct_cells, states, 0.0)
    # define operator that computes RHS for both duct and chamber
    def operator(cells_, z_, time_val):
        ws = primitive(cells_)
        # reconstruct duct
        # boundaries: left is coupling (not wall), right is wall
        # For CFL we need speeds including interface
        # Compute interface flux using ChamberState
        ch_state = ChamberState(z_[0], z_[1], z_[2], volume)
        # duct left face state: use lf[0] from reconstruct with dummy boundaries? We'll reconstruct with outflow left and wall right to get lf/rf but we replace left flux
        # Use reconstruct with (outflow, wall) to get interior reconstruction, but left flux will be overridden
        lf, rf, down = reconstruct(mesh, ws, (Boundary('outflow'), Boundary('wall')), eos)
        # interior fluxes
        interior_data=[]
        for i in range(mesh.n-1):
            f,s,reason = hllc_flux(rf[i], lf[i+1], eos)
            interior_data.append((f,s,reason))
        # left interface flux: chamber vs lf[0] ? Should use lf[0] as duct face state
        # left primitive for HLLC is chamber stagnant vs duct face
        rho_c,p_c,T_c,Y_c,_,_,_ = chamber_thermo(z_)
        left_c = (rho_c, 0.0, p_c, Y_c)
        right_d = lf[0]  # duct face state at left
        # Use normal -1 : left=chamber, right=duct face
        flux_iface, speeds_iface, reason_iface = hllc_flux(left_c, right_d, eos)
        # interface outward = -area*flux_iface (normal -1)
        area=C2_AREA
        flux_iface_scaled = tuple(area*v for v in flux_iface)
        outward = tuple(-v for v in flux_iface_scaled) # -1*area*flux
        # For duct, left face flux is flux_iface_scaled (positive to right)
        flux_left = flux_iface_scaled
        # speeds for CFL: include interface speeds
        speeds=[]
        # interface speed max abs
        speeds.append(max(abs(speeds_iface[0]), abs(speeds_iface[2])))
        for _,s,_ in interior_data:
            speeds.append(max(abs(s[0]), abs(s[2])))
        # right wall: use wall boundary
        w_last = rf[-1]
        ghost = Boundary('wall').face_state(w_last, 1, eos)
        f_wall,s_wall,reason_wall = hllc_flux(w_last, ghost, eos)
        # wall flux per area is (0, p,0,0) but hllc gives flux; we override momentum? Actually wall flux is (0, p_wall,0,0) per hllc logic? In second_order wall flux override, but for our left coupling we already handled.
        # For wall, flux should be (0, f_wall[1],0,0) scaled
        flux_wall = (0.0, f_wall[1]*area, 0.0, 0.0)
        speeds.append(max(abs(s_wall[0]), abs(s_wall[2])))
        # Now flux array for duct: [flux_left, interior fluxes ..., flux_wall]
        flux = [flux_left]
        for f,_,_ in interior_data:
            flux.append(tuple(area*v for v in f))
        flux.append(flux_wall)
        # dq for duct
        source=[ws[i][2]*(mesh.areas[i+1]-mesh.areas[i]) for i in range(mesh.n)]
        dq=[tuple(flux[i][k]-flux[i+1][k]+(source[i] if k==1 else 0.) for k in range(4)) for i in range(mesh.n)]
        # dz for chamber: outward per dt (mass, energy, species) -> chamber gets outward
        # outward is mass/energy/species flux out of pipe; chamber receives outward (positive outward means entering chamber if outward positive? Actually outward = -area*flux, so if flux positive to right, outward negative => chamber loses mass)
        # Chamber increments: d mass/dt = outward[0], dU/dt = outward[2], d fresh/dt = outward[3]
        dz=[outward[0], outward[2], outward[3]]
        # also need external for wall? wall flux is external loss for total system? But total mass conserved with wall (no outflow) so external zero (wall momentum flux not counted for mass/energy)
        # For conservation we consider external flux at right wall is zero mass/energy/species (only momentum)
        # So external mass/energy/species =0
        # limit for CFL
        limit, limiting, unit = cfl_step(mesh, ws, speeds, eos, cfl)
        # cfl_step expects speeds length n+1, we have n+1 (1 interface + n-1 interior +1 wall) = n+1 good
        # need to ensure speeds length matches mesh.n+1 (n=100 -> 101 speeds) we have 1+ (n-1)=n +1 wall = n+1 correct
        # R5 diagnostic capture only.  This is assembled from values already
        # used by the product RHS; it does not feed any product calculation.
        face_states = [{"index": 0, "kind": "interface",
                        "left": list(left_c), "right": list(right_d)}]
        face_riemann = [{"index": 0, "kind": "interface",
                         "flux": list(flux_left), "waves": list(speeds_iface),
                         "reason": reason_iface}]
        for i, (f, s, reason) in enumerate(interior_data, start=1):
            face_states.append({"index": i, "kind": "interior",
                                "left": list(rf[i-1]), "right": list(lf[i])})
            face_riemann.append({"index": i, "kind": "interior",
                                 "flux": list(tuple(area*v for v in f)),
                                 "waves": list(s), "reason": reason})
        face_states.append({"index": mesh.n, "kind": "wall",
                            "left": list(w_last), "right": list(ghost)})
        face_riemann.append({"index": mesh.n, "kind": "wall",
                             "flux": list(flux_wall), "waves": list(s_wall),
                             "reason": reason_wall})
        return {"dq":dq, "dz":dz, "limit":limit, "unit":unit, "limiting":limiting,
                "flux_left":flux_left, "outward":outward,
                "speeds_iface":speeds_iface, "reason":reason_iface,
                "reason_iface":reason_iface, "ws":ws,
                "chamber_p":p_c,
                # Diagnostic inputs only: these are the states actually passed
                # to the two exterior Riemann evaluations in this operator.
                 "external_faces": {
                    "interface": {"left": list(left_c), "right": list(right_d)},
                    "wall": {"left": list(w_last), "right": list(ghost)},
                    # Diagnostic metadata mirrors reconstruct() exactly:
                    # `down` is the only productive downgrade evidence.
                    "reconstruction": {"downgraded_cells": list(down)},
                    "riemann": {
                        "interface": {"speeds": list(speeds_iface),
                                       "reason": reason_iface},
                        "wall": {"speeds": list(s_wall),
                                 "reason": reason_wall},
                     },
                 },
                 "r5_momentum": {
                     "faces": face_states,
                     "riemann": face_riemann,
                     "downgraded_cells": list(down),
                     "source": list(source),
                     "rhs": [row[1] for row in dq],
                 }}
    # time loop SSPRK2
    t=0.0; step=0; rejections=0; history=[]
    # initial operator for limit
    op0=operator(duct_cells, z0, t)
    # inventories for residual
    # initial total inventory: duct + chamber
    def total_inventory(cells_, z_):
        duct_inv=inventories(cells_)
        # chamber contributions: mass, momentum 0, energy U, species fresh
        # total momentum = duct momentum (chamber has no momentum)
        total=[ duct_inv[0]+z_[0], duct_inv[1], duct_inv[2]+z_[1], duct_inv[3]+z_[2] ]
        return total
    initial_total=total_inventory(duct_cells, z0)
    # external flux integrated: only wall mass/energy/species zero, but we track for consistency
    external_int=[0.,0.,0.] # not used
    max_stage_resid=0; max_global_resid=0; max_cfl=0
    # ledger
    cells=duct_cells; z=z0
    while t < t_final:
        if _time.monotonic()-started>120:
            break
        op0=operator(cells, z, t)
        dt=event_step(op0["limit"], t_final-t)
        # Freeze the state used by op0 before attempting/committing this step.
        # stage_a primitives and observed interface fluxes are from op0, so its
        # conservative and chamber states must remain pre-step as well.
        pre_cells = cells
        pre_z = list(z)
        pre_t = t
        # SSPRK2 with chamber
        accepted=False
        for attempt in range(13):
            if dt<1e-12: break
            try:
                # stage1
                cells1=[tuple(a+dt*b for a,b in zip(row,dr)) for row,dr in zip(cells, op0["dq"])]
                z1=[a+dt*b for a,b in zip(z, op0["dz"])]
                # validate chamber
                rho1,p1,T1,Y1,_,_,_ = chamber_thermo(z1)
                eos.validate((rho1,0.,p1,Y1))
                # validate duct
                ws1=primitive(cells1)
                op1=operator(cells1, z1, t+dt)
                if dt>op1["limit"]:
                    raise InvalidState('stage_CFL')
                # stage2
                cells2=[tuple(a+dt*b for a,b in zip(row,dr)) for row,dr in zip(cells1, op1["dq"])]
                z2=[a+dt*b for a,b in zip(z1, op1["dz"])]
                rho2,p2,T2,Y2,_,_,_=chamber_thermo(z2)
                eos.validate((rho2,0.,p2,Y2))
                ws2=primitive(cells2)
                # final combine
                cells_new=[tuple(0.5*a+0.5*b for a,b in zip(row1,row2)) for row1,row2 in zip(cells,cells2)]
                z_new=[0.5*a+0.5*b for a,b in zip(z,z2)]
                # validate final
                rho_n,p_n,T_n,Y_n,_,_,_=chamber_thermo(z_new)
                eos.validate((rho_n,0.,p_n,Y_n))
                ws_new=primitive(cells_new)
                accepted=True
                break
            except Exception as exc:
                rejections+=1
                if attempt==12:
                    raise
                dt/=2
        if not accepted:
            break
        # commit
        cells=cells_new; z=z_new; t+=dt; step+=1
        # record
        rho_c,p_c,T_c,Y_c,_,_,_=chamber_thermo(z)
        sm = op0["speeds_iface"][1] if op0["speeds_iface"][1] is not None else 0.0
        ws=primitive(cells)
        # Diagnostic capture only.  The independent auditor receives the
        # conservative/primitive states and geometry, then recomputes face
        # terms offline and checks exact parity against these persisted
        # product face/source/RHS values; none feed back into the update.
        audit_stages = {
            # interface_flux_observed and mass/energy/species fluxes below are
            # op0/stage_a quantities, all aligned to this pre-step state.
            "stage_a": {"time": pre_t, "dt": dt,
                        "conservative": [list(row) for row in pre_cells],
                        "primitive": [list(w) for w in op0["ws"]],
                        "chamber_state": list(pre_z),
                        "external_faces": op0["external_faces"],
                        "r5_momentum": op0["r5_momentum"]},
            "stage_b": {"time": t, "dt": dt,
                        "conservative": [list(row) for row in cells1],
                        "primitive": [list(w) for w in op1["ws"]],
                        "chamber_state": list(z1),
                        "external_faces": op1["external_faces"],
                        "provisional": [list(row) for row in cells2],
                        "r5_momentum": op1["r5_momentum"]},
            "after": {"conservative": [list(row) for row in cells_new],
                       "primitive": [list(w) for w in ws_new],
                       "chamber_state": list(z_new)},
        }
        interface_info = {
            "p_chamber":op0["chamber_p"],
            "mass_flux":op0["outward"][0],
            "energy_flux":op0["outward"][2],
            "species_flux":op0["outward"][3],
            "velocity_star":sm,
            "chamber_state": list(pre_z),
            "first_cell_state": list(pre_cells[0]),
            "sample_time_pre_step": pre_t,
            "history_record_time_post_step": t,
            "interface_area": C2_AREA,
            "interface_normal": -1.0,
            "interface_flux_observed":list(op0["flux_left"]),
            "observed_flux_source": "op0/stage_a pre-step",
            "mass_energy_species_flux_source": "op0/stage_a pre-step",
            "wave_speed_middle":sm,
            "speeds_iface":list(op0["speeds_iface"]),
            "reason_iface":op0["reason_iface"],
            "audit_stages": audit_stages,
        }
        record(z, cells, ws, t, flux_info=interface_info)
        max_cfl=max(max_cfl, dt/op0["unit"], dt/op1["unit"])
        # global residual
        total=total_inventory(cells, z)
        # external zero mass/energy/species, wall momentum not counted for conservation of mass/energy/species? So residual = total - initial
        resid_mass = total[0]-initial_total[0]
        resid_energy = total[2]-initial_total[2]
        resid_species = total[3]-initial_total[3]
        # normalized by initial mass/energy
        norm_mass = abs(resid_mass)/max(abs(initial_total[0]),1.0)
        norm_energy = abs(resid_energy)/max(abs(initial_total[2]),1.0)
        norm_species = abs(resid_species)/max(abs(initial_total[3]),1.0)
        max_global_resid=max(max_global_resid, norm_mass, norm_energy, norm_species)
    wall_seconds=_time.monotonic()-started
    total_final=total_inventory(cells, z)
    return {
        "status":"completed","time":t,"steps":step,"wall_seconds":wall_seconds,"rejected":rejections,
        "initial_total":initial_total,"final_total":total_final,
        "max_global_resid":max_global_resid,"max_cfl":max_cfl,
        "chamber_history":chamber_hist,"sensor_history":sensor_hist,"duct_history":duct_hist,
        "interface_history":interface_hist,
        "audit_geometry": {"areas": list(mesh.areas), "volumes": list(mesh.volumes),
                            "faces": list(mesh.faces), "centers": list(mesh.centers),
                            "duct_length": C2_L_DUCT, "area_m2": C2_AREA,
                            "chamber_volume": C2_VOLUME},
        "cells":cells,"chamber_state":z, "mesh_n":mesh.n, "dt_min":None, # not tracked per se
    }

def c2_initial_riemann_check(p_ch, T_ch, Y_ch, p_du, T_du, Y_du):
    eos=EOS
    rho_ch = p_ch/(eos.R*T_ch)
    left = (rho_ch,0.,p_ch,Y_ch)
    rho_du = p_du/(eos.R*T_du)
    right = (rho_du,0.,p_du,Y_du)
    # For normal -1 left=chamber right=duct
    ref = ExactRiemann(left,right,eos)
    # productive interface at t0
    ch_state = c2_chamber_state(p_ch,T_ch,Y_ch)
    pipe = (rho_du,0.,p_du,Y_du)
    prod = interface_flux(ch_state, pipe, C2_AREA, -1, eos=eos)
    return {"exact":{"p_star":ref.pstar,"u_star":ref.ustar,"waves":ref.waves,"iface":ref.sample(0.0)},"prod":{"flux":prod.outward,"speeds":prod.wave_speeds,"reason":prod.fallback_reason,"p_star_est":None}}
