"""Isolated mathematical boundaries; no 0D coupling or real exhaust radiation."""
from dataclasses import dataclass
from math import sqrt, expm1, log1p, isfinite
from .eos import InvalidState
from .riemann import hllc_flux


@dataclass(frozen=True)
class Boundary:
    kind: str
    state: tuple | None = None
    p0: float = 100000.
    T0: float = 300.
    Y0: float = .3

    def face_state(self, interior, normal, eos):
        eos.validate(interior)
        if self.kind=='fixed':return eos.validate(self.state)
        if self.kind=='outflow':return interior
        r,u,p,y=interior;w=normal*u;a=eos.sound_speed(interior);g=eos.gamma
        if self.kind=='wall':return r,-u,p,y
        if self.kind=='ideal_open_pressure_release':
            # R3 acoustic continuation, not a reservoir/donor switch.
            if not isfinite(self.p0) or self.p0<=0 or abs(w)>=a:
                raise InvalidState('Pressure-release requires positive pressure and subsonic interior')
            ki=p/r**g;rb=(self.p0/ki)**(1/g);ab=sqrt(g*self.p0/rb)
            wb=w-2*a/(g-1)*expm1((g-1)/(2*g)*log1p((self.p0-p)/p))
            if abs(wb)>=ab:raise InvalidState('Pressure-release face outside subsonic acoustic scope')
            return eos.validate((rb,normal*wb,self.p0,y))
        if self.kind not in ('open','nonreflecting','reservoir'): raise ValueError('Unknown boundary')
        if w>=a:return interior
        if w<=-a:
            if self.state is not None:return eos.validate(self.state)
            raise InvalidState('unsupported_supersonic_inlet')
        jp=w+2*a/(g-1);ki=p/r**g
        ext=eos.validate((self.p0/(eos.R*self.T0),0.,self.p0,self.Y0));ke=self.p0/ext[0]**g
        if self.kind=='nonreflecting':
            base=self.state or ext;eos.validate(base)
            ke=base[2]/base[0]**g
            exterior_y=base[3]
            jm=normal*base[1]-2*eos.sound_speed(base)/(g-1)
            wb=(jp+jm)/2;ab=(g-1)*(jp-jm)/4
            if ab<=0:raise InvalidState('Nonpositive characteristic sound speed')
            k=ki if wb>=0 else ke
            rb=(ab*ab/(g*k))**(1/(g-1));pb=k*rb**g
        else:
            exterior_y=self.Y0
            # Try outflow using the prescribed static receiving pressure.
            rb=(self.p0/ki)**(1/g);ab=sqrt(g*self.p0/rb);wb=jp-2*ab/(g-1);pb=self.p0
            if wb<0:
                if self.kind=='open':
                    rb=ext[0];ab=eos.sound_speed(ext);wb=jp-2*ab/(g-1)
                    if wb>0:raise InvalidState('No consistent open-boundary branch')
                else:
                    h0=eos.cp*self.T0;sonic=sqrt(2*(g-1)*h0/(g+1))
                    # Solve w+2*a(w)/(g-1)=J+ for -a<w<=0, bounded bisection.
                    jchoke=-sonic+2*sonic/(g-1);jrest=2*sqrt((g-1)*h0)/(g-1)
                    if jp<=jchoke:wb=-sonic;ab=sonic
                    elif jp>jrest:raise InvalidState('No consistent reservoir inflow branch')
                    else:
                        lo=-sonic;hi=0.
                        for _ in range(60):
                            mid=(lo+hi)/2;am=sqrt((g-1)*(h0-mid*mid/2))
                            if mid+2*am/(g-1)<jp:lo=mid
                            else:hi=mid
                        wb=(lo+hi)/2;ab=sqrt((g-1)*(h0-wb*wb/2))
                    rb=(ab*ab/(g*ke))**(1/(g-1));pb=ke*rb**g
        return eos.validate((rb,normal*wb,pb,y if wb>=0 else exterior_y))

    def flux(self, interior, normal, eos):
        state=self.face_state(interior,normal,eos)
        if self.kind in ('wall','fixed','outflow'):
            left,right=(state,interior) if normal==-1 else (interior,state)
            flux,speeds,reason=hllc_flux(left,right,eos)
            if self.kind=='wall':flux=(0.,flux[1],0.,0.)
            return flux,speeds,reason
        # Characteristics specify the face state itself, not an over-imposed ghost.
        a=eos.sound_speed(state);u=state[1]
        return eos.flux(state),(u-a,u,u+a),None
