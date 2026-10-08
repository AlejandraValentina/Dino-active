"""Serial float64 HLLC adaptation; numerical reference retained independently."""
import numpy as np
from math import sqrt,isfinite
from numba import njit
from .gas1d.eos import InvalidState
from .gas1d.riemann import hllc_flux as reference_hllc

@njit(cache=True, fastmath=False, parallel=False)
def validate(w,R):
    r,u,p,y=w
    if not (np.isfinite(w).all() and r>0 and p>0 and 0<=y<=1):
        raise ValueError('rho/p/Y inadmissible')
    T=p/(r*R)
    if not isfinite(T) or T<=0:raise ValueError('Temperature inadmissible')

@njit(cache=True, fastmath=False, parallel=False)
def flux(w,gamma):
    r,u,p,y=w;m=r*u
    return np.array([m,m*u+p,u*(gamma*p/(gamma-1)+.5*r*u*u),m*y])

@njit(cache=True, fastmath=False, parallel=False)
def conservative(w,gamma):
    r,u,p,y=w
    return np.array([r,r*u,p/(gamma-1)+.5*r*u*u,r*y])

@njit(cache=True, fastmath=False, parallel=False)
def estimate_wave_speeds(left,right,gamma,R):
    rl,ul,pl,_=left;rr,ur,pr,_=right
    al=sqrt(gamma*left[2]/left[0]);ar=sqrt(gamma*right[2]/right[0])
    wl=sqrt(rl);wr=sqrt(rr);g=gamma
    hl=g*pl/((g-1)*rl)+ul*ul/2;hr=g*pr/((g-1)*rr)+ur*ur/2
    u=(wl*ul+wr*ur)/(wl+wr);h=(wl*hl+wr*hr)/(wl+wr)
    a2=(g-1)*(h-u*u/2)
    if not isfinite(a2) or a2<=0: raise ValueError('Invalid Roe speed')
    a=sqrt(a2)
    sl=min(ul-al,ur-ar,u-a);sr=max(ul+al,ur+ar,u+a)
    if not isfinite(sl) or not isfinite(sr) or sl>=sr: raise ValueError('Invalid wave bounds')
    return sl,sr


@njit(cache=True, fastmath=False, parallel=False)
def hlle_flux(left,right,gamma,R,speeds):
    sl,sr=speeds
    fl=flux(left,gamma);fr=flux(right,gamma)
    if sl>=0:return fl
    if sr<=0:return fr
    ql=conservative(left,gamma);qr=conservative(right,gamma)
    return np.array([(sr*fl[k]-sl*fr[k]+sl*sr*(qr[k]-ql[k]))/(sr-sl) for k in range(4)])


@njit(cache=True, fastmath=False, parallel=False)
def hllc_flux(left,right,gamma,R):
    """Return (flux, (SL,SM,SR), fallback_reason). No in-place state changes."""
    validate(left,R);validate(right,R)
    sl,sr=estimate_wave_speeds(left,right,gamma,R)
    rl,ul,pl,yl=left;rr,ur,pr,yr=right
    if np.all(left==right):return flux(left,gamma),(sl,ul,sr),0
    fl=flux(left,gamma);fr=flux(right,gamma)
    if sl>=0:return fl,(sl,ul,sr),0
    if sr<=0:return fr,(sl,ur,sr),0
    denominator=rl*(sl-ul)-rr*(sr-ur)
    reason=0;sm=0
    if denominator==0 or not isfinite(denominator):reason=1
    else:
        sm=(pr-pl+rl*ul*(sl-ul)-rr*ur*(sr-ur))/denominator
        if not isfinite(sm) or not sl<sm<sr:reason=2
    stars=[]
    if reason == 0:
        for w,s in ((left,sl),(right,sr)):
            r,u,p,y=w
            if s==sm or s==u:reason=3;break
            rs=r*(s-u)/(s-sm);ps=p+r*(s-u)*(sm-u)
            es=p/((gamma-1)*r)+u*u/2+(sm-u)*(sm+p/(r*(s-u)))
            if not (isfinite(rs) and isfinite(ps) and isfinite(es)) or rs<=0 or ps<=0 or es-sm*sm/2<=0:
                reason=4;break
            stars.append((rs,rs*sm,rs*es,rs*y))
    if reason:
        return hlle_flux(left,right,gamma,R,(sl,sr)),(sl,sm,sr),reason
    w,s,star,f=(left,sl,stars[0],fl) if sm>=0 else (right,sr,stars[1],fr)
    q=conservative(w,gamma)
    out=np.array([f[k]+s*(star[k]-q[k]) for k in range(4)])
    # F_mass*=rho*u+S*(rho*-rho)=rho*SM by Rankine-Hugoniot.
    # The product preserves SM's sign without subtracting nearly equal states.
    # Species shares this same mass flux and the same HLLC contact-wave donor.
    mass=star[0]*sm
    return np.array([mass,out[1],out[2],mass*w[3]]),(sl,sm,sr),0

@njit(cache=True, fastmath=False, parallel=False)
def faces(left,right,gamma,R):
    n=len(left);out=np.empty((n,4));speeds=np.empty((n,3));codes=np.zeros(n,np.int64)
    for i in range(n):
        f,s,c=hllc_flux(left[i],right[i],gamma,R)
        out[i]=f;speeds[i]=s;codes[i]=c
    return out,speeds,codes

def hllc(left,right,eos):
    try:out,speeds,codes=faces(left,right,eos.gamma,eos.R)
    except ValueError as exc:raise InvalidState(str(exc)) from exc
    reasons={};fallback={}
    # Preserve reference exceptional semantics, including undefined SM.
    for i in np.flatnonzero(codes):
        f,s,r=reference_hllc(tuple(left[i]),tuple(right[i]),eos)
        out[i]=f;speeds[i]=(s[0],np.nan if s[1] is None else s[1],s[2])
        if r:reasons[int(i)]=r;fallback[int(i)]=s
    return out,speeds,reasons,fallback


@njit(cache=True, fastmath=False, parallel=False)
def primitive_numeric(cells,volumes,gamma,R):
    w=np.empty_like(cells)
    for i in range(len(cells)):
        r,m,e,z=cells[i]/volumes[i]
        if not (isfinite(r) and isfinite(m) and isfinite(e) and isfinite(z) and r>0 and 0<=z<=r):
            raise ValueError('Conserved rho/species inadmissible')
        u=m/r;p=(gamma-1)*(e-.5*m*u)
        w[i]=r,u,p,z/r
        validate(w[i],R)
    return w

def primitive(cells,volumes,eos):
    try:return primitive_numeric(cells,volumes,eos.gamma,eos.R)
    except ValueError as exc:raise InvalidState(str(exc)) from exc

@njit(cache=True, fastmath=False, parallel=False)
def admissible(w,R):
    r,u,p,y=w
    if not (np.isfinite(w).all() and r>0 and p>0 and 0<=y<=1):return False
    T=p/(r*R)
    return isfinite(T) and T>0

@njit(cache=True, fastmath=False, parallel=False)
def reconstruct_numeric(w,lo,hi,dl,dr,left_offset,right_offset,R):
    n=len(w);lf=np.empty_like(w);rf=np.empty_like(w);bad=np.zeros(n,np.bool_)
    for i in range(n):
        for k in range(4):
            l=lo[k] if i==0 else w[i-1,k];r=hi[k] if i==n-1 else w[i+1,k]
            a=(w[i,k]-l)/dl[i,0];b=(r-w[i,k])/dr[i,0]
            slope=0. if a==0 or b==0 or (a>0)!=(b>0) else (a if abs(a)<=abs(b) else b)
            lf[i,k]=w[i,k]+slope*left_offset[i,0];rf[i,k]=w[i,k]+slope*right_offset[i,0]
        if not (admissible(lf[i],R) and admissible(rf[i],R)):
            lf[i]=w[i];rf[i]=w[i];bad[i]=True
    return lf,rf,bad

# R5 fused in-place helpers: single Python->Numba crossing for B+C+D
@njit(cache=True, fastmath=False, parallel=False)
def primitive_inplace(cells, volumes, gamma, R, w_out):
    n = cells.shape[0]
    for i in range(n):
        r = cells[i,0] / volumes[i]
        m = cells[i,1] / volumes[i]
        e = cells[i,2] / volumes[i]
        z = cells[i,3] / volumes[i]
        if not (isfinite(r) and isfinite(m) and isfinite(e) and isfinite(z) and r>0 and 0 <= z <= r):
            raise ValueError('Conserved rho/species inadmissible')
        u = m / r
        p = (gamma - 1.0) * (e - 0.5 * m * u)
        y = z / r
        if not (isfinite(r) and isfinite(u) and isfinite(p) and isfinite(y) and r>0 and p>0 and 0 <= y <= 1):
            raise ValueError('rho/p/Y inadmissible')
        T = p / (r * R)
        if not isfinite(T) or T <= 0:
            raise ValueError('Temperature inadmissible')
        w_out[i,0] = r
        w_out[i,1] = u
        w_out[i,2] = p
        w_out[i,3] = y

@njit(cache=True, fastmath=False, parallel=False)
def reconstruct_inplace(w, lo, hi, dl, dr, left_offset, right_offset, R, lf_out, rf_out, bad_out):
    n = w.shape[0]
    for i in range(n):
        for k in range(4):
            l = lo[k] if i==0 else w[i-1, k]
            r_ = hi[k] if i==n-1 else w[i+1, k]
            a = (w[i,k] - l) / dl[i,0]
            b = (r_ - w[i,k]) / dr[i,0]
            slope = 0. if a==0 or b==0 or (a>0)!=(b>0) else (a if abs(a) <= abs(b) else b)
            lf_out[i,k] = w[i,k] + slope * left_offset[i,0]
            rf_out[i,k] = w[i,k] + slope * right_offset[i,0]
        ok_lf = np.isfinite(lf_out[i]).all() and lf_out[i,0]>0 and lf_out[i,2]>0 and 0 <= lf_out[i,3] <= 1
        if ok_lf:
            T = lf_out[i,2] / (lf_out[i,0] * R)
            ok_lf = isfinite(T) and T>0
        ok_rf = np.isfinite(rf_out[i]).all() and rf_out[i,0]>0 and rf_out[i,2]>0 and 0 <= rf_out[i,3] <= 1
        if ok_rf:
            T = rf_out[i,2] / (rf_out[i,0] * R)
            ok_rf = isfinite(T) and T>0
        if not (ok_lf and ok_rf):
            lf_out[i,0] = w[i,0]; lf_out[i,1] = w[i,1]; lf_out[i,2] = w[i,2]; lf_out[i,3] = w[i,3]
            rf_out[i,0] = w[i,0]; rf_out[i,1] = w[i,1]; rf_out[i,2] = w[i,2]; rf_out[i,3] = w[i,3]
            bad_out[i] = True
        else:
            bad_out[i] = False

@njit(cache=True, fastmath=False, parallel=False)
def fused_interior(cells, volumes, dl, dr, left_offset, right_offset, gamma, R, ext_state,
                   w_out, lf_out, rf_out, bad_out, flux_out, speeds_out, codes_out):
    # B primitive
    n = cells.shape[0]
    for i in range(n):
        r = cells[i,0] / volumes[i]
        m = cells[i,1] / volumes[i]
        e = cells[i,2] / volumes[i]
        z = cells[i,3] / volumes[i]
        if not (isfinite(r) and isfinite(m) and isfinite(e) and isfinite(z) and r>0 and 0 <= z <= r):
            raise ValueError('Conserved rho/species inadmissible')
        u = m / r
        p = (gamma - 1.0) * (e - 0.5 * m * u)
        y = z / r
        if not (isfinite(r) and isfinite(u) and isfinite(p) and isfinite(y) and r>0 and p>0 and 0 <= y <= 1):
            raise ValueError('rho/p/Y inadmissible')
        T = p / (r * R)
        if not isfinite(T) or T <= 0:
            raise ValueError('Temperature inadmissible')
        w_out[i,0]=r; w_out[i,1]=u; w_out[i,2]=p; w_out[i,3]=y
    # compute boundary ghost states for MUSCL: left outflow = w[0], right nonreflecting from w[-1] and ext_state
    # lo = w[0]
    lo0 = w_out[0,0]; lo1 = w_out[0,1]; lo2 = w_out[0,2]; lo3 = w_out[0,3]
    # hi via nonreflecting characteristic
    r_int = w_out[n-1,0]; u_int = w_out[n-1,1]; p_int = w_out[n-1,2]; y_int = w_out[n-1,3]
    a_int = sqrt(gamma*p_int/r_int)
    w_n = u_int # normal =1
    # quick check if supersonic outflow: hi = interior
    # replicate Boundary.face_state for nonreflecting
    # ext_state is (rho_ext, 0, p_ext, Y_ext)
    rho_ext = ext_state[0]; p_ext = ext_state[2]; y_ext = ext_state[3]
    # compute hi
    hi0 = 0; hi1 = 0; hi2 = 0; hi3 = 0
    if w_n >= a_int:
        hi0 = r_int; hi1 = u_int; hi2 = p_int; hi3 = y_int
    elif w_n <= -a_int:
        hi0 = rho_ext; hi1 = 0.0; hi2 = p_ext; hi3 = y_ext
    else:
        jp = w_n + 2*a_int/(gamma-1)
        ki = p_int / (r_int**gamma)
        # ext values
        a_ext = sqrt(gamma*p_ext/rho_ext)
        ke = p_ext / (rho_ext**gamma)
        jm = -2*a_ext/(gamma-1)  # base u=0
        wb = (jp + jm)*0.5
        ab = (gamma-1)*(jp - jm)*0.25
        if ab <= 0:
            raise ValueError('Nonpositive characteristic sound speed')
        k = ki if wb >= 0 else ke
        rb = (ab*ab/(gamma*k))**(1.0/(gamma-1))
        pb = k * (rb**gamma)
        yb = y_int if wb >=0 else y_ext
        hi0 = rb; hi1 = wb; hi2 = pb; hi3 = yb
        # validate
        if not (isfinite(hi0) and isfinite(hi1) and isfinite(hi2) and isfinite(hi3) and hi0>0 and hi2>0 and 0 <= hi3 <=1):
            raise ValueError('rho/p/Y inadmissible')
        T = hi2/(hi0*R)
        if not isfinite(T) or T <=0:
            raise ValueError('Temperature inadmissible')
    # C reconstruct using lo/hi computed above
    for i in range(n):
        for k in range(4):
            if k==0:
                l = lo0 if i==0 else w_out[i-1,0]
                r_ = hi0 if i==n-1 else w_out[i+1,0]
            elif k==1:
                l = lo1 if i==0 else w_out[i-1,1]
                r_ = hi1 if i==n-1 else w_out[i+1,1]
            elif k==2:
                l = lo2 if i==0 else w_out[i-1,2]
                r_ = hi2 if i==n-1 else w_out[i+1,2]
            else:
                l = lo3 if i==0 else w_out[i-1,3]
                r_ = hi3 if i==n-1 else w_out[i+1,3]
            a = (w_out[i,k] - l) / dl[i,0]
            b = (r_ - w_out[i,k]) / dr[i,0]
            slope = 0. if a==0 or b==0 or (a>0)!=(b>0) else (a if abs(a) <= abs(b) else b)
            lf_out[i,k] = w_out[i,k] + slope * left_offset[i,0]
            rf_out[i,k] = w_out[i,k] + slope * right_offset[i,0]
        ok_lf = np.isfinite(lf_out[i]).all() and lf_out[i,0]>0 and lf_out[i,2]>0 and 0 <= lf_out[i,3] <= 1
        if ok_lf:
            T = lf_out[i,2] / (lf_out[i,0] * R)
            ok_lf = isfinite(T) and T>0
        ok_rf = np.isfinite(rf_out[i]).all() and rf_out[i,0]>0 and rf_out[i,2]>0 and 0 <= rf_out[i,3] <= 1
        if ok_rf:
            T = rf_out[i,2] / (rf_out[i,0] * R)
            ok_rf = isfinite(T) and T>0
        if not (ok_lf and ok_rf):
            lf_out[i,0]=w_out[i,0]; lf_out[i,1]=w_out[i,1]; lf_out[i,2]=w_out[i,2]; lf_out[i,3]=w_out[i,3]
            rf_out[i,0]=w_out[i,0]; rf_out[i,1]=w_out[i,1]; rf_out[i,2]=w_out[i,2]; rf_out[i,3]=w_out[i,3]
            bad_out[i]=True
        else:
            bad_out[i]=False
    # D interior HLLC
    for i in range(n-1):
        # left = rf[i], right = lf[i+1]
        l0 = rf_out[i,0]; l1 = rf_out[i,1]; l2 = rf_out[i,2]; l3 = rf_out[i,3]
        r0 = lf_out[i+1,0]; r1 = lf_out[i+1,1]; r2 = lf_out[i+1,2]; r3 = lf_out[i+1,3]
        # validate
        if not (isfinite(l0) and isfinite(l1) and isfinite(l2) and isfinite(l3) and l0>0 and l2>0 and 0 <= l3 <= 1):
            raise ValueError('rho/p/Y inadmissible')
        T = l2/(l0*R)
        if not isfinite(T) or T <=0:
            raise ValueError('Temperature inadmissible')
        if not (isfinite(r0) and isfinite(r1) and isfinite(r2) and isfinite(r3) and r0>0 and r2>0 and 0 <= r3 <= 1):
            raise ValueError('rho/p/Y inadmissible')
        T = r2/(r0*R)
        if not isfinite(T) or T <=0:
            raise ValueError('Temperature inadmissible')
        al = sqrt(gamma*l2/l0); ar = sqrt(gamma*r2/r0)
        wl = sqrt(l0); wr = sqrt(r0)
        g = gamma
        hl = g*l2/((g-1)*l0) + l1*l1*0.5
        hr = g*r2/((g-1)*r0) + r1*r1*0.5
        u_roe = (wl*l1 + wr*r1)/(wl+wr)
        h_roe = (wl*hl + wr*hr)/(wl+wr)
        a2 = (g-1)*(h_roe - u_roe*u_roe*0.5)
        if not isfinite(a2) or a2 <=0:
            raise ValueError('Invalid Roe speed')
        a = sqrt(a2)
        sl = l1 - al
        tmp = r1 - ar
        if tmp < sl: sl = tmp
        tmp_u = u_roe - a
        if tmp_u < sl: sl = tmp_u
        sr = l1 + al
        tmp = r1 + ar
        if tmp > sr: sr = tmp
        tmp_u = u_roe + a
        if tmp_u > sr: sr = tmp_u
        if not isfinite(sl) or not isfinite(sr) or sl >= sr:
            raise ValueError('Invalid wave bounds')
        equal = (l0==r0 and l1==r1 and l2==r2 and l3==r3)
        if equal:
            m = l0*l1
            flux_out[i,0]=m
            flux_out[i,1]=m*l1+l2
            flux_out[i,2]=l1*(g*l2/(g-1)+0.5*l0*l1*l1)
            flux_out[i,3]=m*l3
            speeds_out[i,0]=sl; speeds_out[i,1]=l1; speeds_out[i,2]=sr
            codes_out[i]=0
            continue
        fl0 = l0*l1
        fl1 = l0*l1*l1 + l2
        fl2 = l1*(g*l2/(g-1)+0.5*l0*l1*l1)
        fl3 = l0*l1*l3
        fr0 = r0*r1
        fr1 = r0*r1*r1 + r2
        fr2 = r1*(g*r2/(g-1)+0.5*r0*r1*r1)
        fr3 = r0*r1*r3
        if sl >=0:
            flux_out[i,0]=fl0; flux_out[i,1]=fl1; flux_out[i,2]=fl2; flux_out[i,3]=fl3
            speeds_out[i,0]=sl; speeds_out[i,1]=l1; speeds_out[i,2]=sr
            codes_out[i]=0
            continue
        if sr <=0:
            flux_out[i,0]=fr0; flux_out[i,1]=fr1; flux_out[i,2]=fr2; flux_out[i,3]=fr3
            speeds_out[i,0]=sl; speeds_out[i,1]=r1; speeds_out[i,2]=sr
            codes_out[i]=0
            continue
        denominator = l0*(sl - l1) - r0*(sr - r1)
        reason = 0
        sm = 0.0
        if denominator ==0 or not isfinite(denominator):
            reason = 1
        else:
            sm = (r2 - l2 + l0*l1*(sl - l1) - r0*r1*(sr - r1))/denominator
            if not isfinite(sm) or not (sl < sm < sr):
                reason = 2
        if reason==0:
            # left star
            if sl == sm or sl == l1:
                reason = 3
            else:
                rs = l0*(sl - l1)/(sl - sm)
                ps = l2 + l0*(sl - l1)*(sm - l1)
                es = l2/((g-1)*l0) + l1*l1*0.5 + (sm - l1)*(sm + l2/(l0*(sl - l1)))
                if not (isfinite(rs) and isfinite(ps) and isfinite(es)) or rs <=0 or ps <=0 or es - sm*sm*0.5 <=0:
                    reason = 4
                else:
                    rs_l = rs; es_l = es
                    if sr == sm or sr == r1:
                        reason = 3
                    else:
                        rs = r0*(sr - r1)/(sr - sm)
                        ps = r2 + r0*(sr - r1)*(sm - r1)
                        es = r2/((g-1)*r0) + r1*r1*0.5 + (sm - r1)*(sm + r2/(r0*(sr - r1)))
                        if not (isfinite(rs) and isfinite(ps) and isfinite(es)) or rs <=0 or ps <=0 or es - sm*sm*0.5 <=0:
                            reason = 4
                        else:
                            rs_r = rs; es_r = es
                            if sm >=0:
                                star_r = rs_l; star_m = rs_l*sm; star_e = rs_l*es_l; star_y = rs_l*l3
                                q0 = l0; q1 = l0*l1; q2 = l2/(g-1)+0.5*l0*l1*l1; q3=l0*l3
                                flux_out[i,0]=fl0 + sl*(star_r - q0)
                                flux_out[i,1]=fl1 + sl*(star_m - q1)
                                flux_out[i,2]=fl2 + sl*(star_e - q2)
                                flux_out[i,3]=fl3 + sl*(star_y - q3)
                                mass = star_r*sm
                                flux_out[i,0]=mass
                                flux_out[i,3]=mass*l3
                                speeds_out[i,0]=sl; speeds_out[i,1]=sm; speeds_out[i,2]=sr
                                codes_out[i]=0
                                continue
                            else:
                                star_r = rs_r; star_m = rs_r*sm; star_e = rs_r*es_r; star_y = rs_r*r3
                                q0 = r0; q1 = r0*r1; q2 = r2/(g-1)+0.5*r0*r1*r1; q3=r0*r3
                                flux_out[i,0]=fr0 + sr*(star_r - q0)
                                flux_out[i,1]=fr1 + sr*(star_m - q1)
                                flux_out[i,2]=fr2 + sr*(star_e - q2)
                                flux_out[i,3]=fr3 + sr*(star_y - q3)
                                mass = star_r*sm
                                flux_out[i,0]=mass
                                flux_out[i,3]=mass*r3
                                speeds_out[i,0]=sl; speeds_out[i,1]=sm; speeds_out[i,2]=sr
                                codes_out[i]=0
                                continue
        # fallback HLLE
        if sl >=0:
            flux_out[i,0]=fl0; flux_out[i,1]=fl1; flux_out[i,2]=fl2; flux_out[i,3]=fl3
        elif sr <=0:
            flux_out[i,0]=fr0; flux_out[i,1]=fr1; flux_out[i,2]=fr2; flux_out[i,3]=fr3
        else:
            ql0=l0; ql1=l0*l1; ql2=l2/(g-1)+0.5*l0*l1*l1; ql3=l0*l3
            qr0=r0; qr1=r0*r1; qr2=r2/(g-1)+0.5*r0*r1*r1; qr3=r0*r3
            inv=1.0/(sr - sl)
            flux_out[i,0]=(sr*fl0 - sl*fr0 + sl*sr*(qr0 - ql0))*inv
            flux_out[i,1]=(sr*fl1 - sl*fr1 + sl*sr*(qr1 - ql1))*inv
            flux_out[i,2]=(sr*fl2 - sl*fr2 + sl*sr*(qr2 - ql2))*inv
            flux_out[i,3]=(sr*fl3 - sl*fr3 + sl*sr*(qr3 - ql3))*inv
        speeds_out[i,0]=sl; speeds_out[i,1]=sm; speeds_out[i,2]=sr
        codes_out[i]=reason if reason!=0 else 1

from .exhaust_batch import Kernel as ReferenceKernel
class Kernel(ReferenceKernel):
    def reconstruct(self,w,boundaries):
        lo=boundaries[0].face_state(tuple(w[0].tolist()),-1,self.eos)
        hi=boundaries[1].face_state(tuple(w[-1].tolist()),1,self.eos)
        a,b,bad=reconstruct_numeric(w,np.array(lo),np.array(hi),self.dl,self.dr,self.left_offset,self.right_offset,self.eos.R)
        return a,b,np.flatnonzero(bad).tolist()

# R5 fused interior is available but disabled by default for R4 equivalence baseline
FUSED_ENABLED = False

def solve_exhaust(*args,**kwargs):
    from .exhaust_numpy import solve_exhaust as reference
    import sys
    return reference(*args,numeric_backend=sys.modules[__name__],**kwargs)
