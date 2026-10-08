"""Calorically perfect ideal gas. Primitive order: rho, u, p, Y."""
from dataclasses import dataclass
from math import isfinite, ulp, sqrt


class InvalidState(ValueError):
    pass


@dataclass(frozen=True)
class IdealGas:
    R: float = 287.0
    gamma: float = 1.35

    def __post_init__(self):
        if not isfinite(self.R) or not isfinite(self.gamma) or self.R<=0 or self.gamma<=1:
            raise InvalidState('Invalid EOS')

    @property
    def cv(self): return self.R/(self.gamma-1)

    @property
    def cp(self): return self.gamma*self.cv

    def validate(self, w):
        r,u,p,y=w
        if not all(isfinite(v) for v in w) or r<=0 or p<=0 or not 0<=y<=1:
            raise InvalidState('rho/p/Y inadmissible')
        temperature=p/(r*self.R)
        if not isfinite(temperature) or temperature<=0: raise InvalidState('T inadmissible')
        return w

    def conservative(self, w):
        r,u,p,y=self.validate(w)
        q=(r,r*u,p/(self.gamma-1)+0.5*r*u*u,r*y)
        if not all(isfinite(v) for v in q): raise InvalidState('Nonfinite conserved state')
        return q

    def primitive(self, q):
        r,m,e,z=q
        if not all(isfinite(v) for v in q) or r<=0 or not 0<=z<=r:
            raise InvalidState('Conserved rho/species inadmissible')
        u=m/r;p=(self.gamma-1)*(e-0.5*m*u)
        return self.validate((r,u,p,z/r))

    def primitive_with_mass_fraction_roundoff(self, q, *, ulps=8):
        """Convert a passive ``rho*Y`` state with a bounded upper-bound ULP drift.

        P5's legacy passive scalar is updated alongside the authoritative P6
        species inventory. Independent float64 accumulation can put rho*Y a
        few representable numbers above rho for pure-fresh gas. This adapter
        accepts only that machine-roundoff envelope and derives Y=1 for the
        primitive view; it does not mutate or rewrite the conservative state.
        The strict ``primitive`` contract remains unchanged for other callers.
        """
        if type(ulps) is not int or ulps < 0:
            raise ValueError("ulps must be a nonnegative integer")
        try:
            r, m, energy, z = q
        except Exception as error:
            raise InvalidState("Conserved rho/species inadmissible") from error
        if (not all(isfinite(value) for value in q) or r <= 0.0 or z < 0.0):
            raise InvalidState("Conserved rho/species inadmissible")
        if z > r:
            tolerance = ulps * ulp(r)
            if z - r > tolerance:
                raise InvalidState("Conserved rho/species inadmissible")
            z = r
        return self.primitive((r, m, energy, z))

    def sound_speed(self,w): return sqrt(self.gamma*w[2]/w[0])

    def flux(self,w):
        r,u,p,y=w;m=r*u
        return (m,m*u+p,u*(self.gamma*p/(self.gamma-1)+0.5*r*u*u),m*y)
