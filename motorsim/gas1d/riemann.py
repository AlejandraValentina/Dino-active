"""P1 HLLC with complete-vector HLLE fallback; fluxes per unit area."""
from math import sqrt,isfinite
from .eos import InvalidState


def estimate_wave_speeds(left,right,eos):
    rl,ul,pl,_=left;rr,ur,pr,_=right
    al=eos.sound_speed(left);ar=eos.sound_speed(right)
    wl=sqrt(rl);wr=sqrt(rr);g=eos.gamma
    hl=g*pl/((g-1)*rl)+ul*ul/2;hr=g*pr/((g-1)*rr)+ur*ur/2
    u=(wl*ul+wr*ur)/(wl+wr);h=(wl*hl+wr*hr)/(wl+wr)
    a2=(g-1)*(h-u*u/2)
    if not isfinite(a2) or a2<=0: raise InvalidState('Invalid Roe speed')
    a=sqrt(a2)
    sl=min(ul-al,ur-ar,u-a);sr=max(ul+al,ur+ar,u+a)
    if not isfinite(sl) or not isfinite(sr) or sl>=sr: raise InvalidState('Invalid wave bounds')
    return sl,sr


def hlle_flux(left,right,eos,speeds=None):
    sl,sr=speeds or estimate_wave_speeds(left,right,eos)
    fl=eos.flux(left);fr=eos.flux(right)
    if sl>=0:return fl
    if sr<=0:return fr
    ql=eos.conservative(left);qr=eos.conservative(right)
    return tuple((sr*l-sl*r+sl*sr*(b-a))/(sr-sl) for l,r,a,b in zip(fl,fr,ql,qr))


def hllc_flux(left,right,eos):
    """Return (flux, (SL,SM,SR), fallback_reason). No in-place state changes."""
    eos.validate(left);eos.validate(right)
    sl,sr=estimate_wave_speeds(left,right,eos)
    rl,ul,pl,yl=left;rr,ur,pr,yr=right
    if left==right:return eos.flux(left),(sl,ul,sr),None
    fl=eos.flux(left);fr=eos.flux(right)
    if sl>=0:return fl,(sl,ul,sr),None
    if sr<=0:return fr,(sl,ur,sr),None
    denominator=rl*(sl-ul)-rr*(sr-ur)
    reason=None;sm=None
    if denominator==0 or not isfinite(denominator):reason='degenerate_contact_denominator'
    else:
        sm=(pr-pl+rl*ul*(sl-ul)-rr*ur*(sr-ur))/denominator
        if not isfinite(sm) or not sl<sm<sr:reason='unordered_wave_speeds'
    stars=[]
    if reason is None:
        for w,s in ((left,sl),(right,sr)):
            r,u,p,y=w
            if s==sm or s==u:reason='degenerate_star_denominator';break
            rs=r*(s-u)/(s-sm);ps=p+r*(s-u)*(sm-u)
            es=p/((eos.gamma-1)*r)+u*u/2+(sm-u)*(sm+p/(r*(s-u)))
            if not all(isfinite(v) for v in (rs,ps,es)) or rs<=0 or ps<=0 or es-sm*sm/2<=0:
                reason='inadmissible_star';break
            stars.append((rs,rs*sm,rs*es,rs*y))
    if reason:
        return hlle_flux(left,right,eos,(sl,sr)),(sl,sm,sr),reason
    w,s,star,f=(left,sl,stars[0],fl) if sm>=0 else (right,sr,stars[1],fr)
    q=eos.conservative(w)
    flux=tuple(fk+s*(sk-qk) for fk,sk,qk in zip(f,star,q))
    # F_mass*=rho*u+S*(rho*-rho)=rho*SM by Rankine-Hugoniot.
    # The product preserves SM's sign without subtracting nearly equal states.
    # Species shares this same mass flux and the same HLLC contact-wave donor.
    mass=star[0]*sm
    return (mass,flux[1],flux[2],mass*w[3]),(sl,sm,sr),None
