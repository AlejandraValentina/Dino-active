"""Opt-in primitive MUSCL reconstruction, generalized minmod theta=1.5.

Conservative means are never changed. The gas and passive composition have
independent bounds. Physical endpoint cells retain zero slopes; periodic ghosts
are used only by the explicitly periodic verification problem.
"""
from dataclasses import dataclass
from math import fsum, isfinite, nextafter, ulp

from .eos import InvalidState

SCHEMA='MUSCL_PRIMITIVE_SPECIES_CANDIDATE_V1'


def minmod(a,b,c):
    if a>0 and b>0 and c>0:
        return min(a,b,c)
    if a<0 and b<0 and c<0:
        return max(a,b,c)
    return 0.


def _bounded_slope(mean,neighbor_l,neighbor_r,xl,x,xr,face_l,face_r,*,simplex=False):
    slope=[minmod(1.5*(v-l)/(x-xl),(r-l)/(xr-xl),1.5*(r-v)/(xr-x))
           for l,v,r in zip(neighbor_l,mean,neighbor_r)]
    if simplex:
        pivot=max(range(4),key=lambda i:mean[i])
        slope[pivot]=-fsum(s for i,s in enumerate(slope) if i!=pivot)
    theta=1.
    for k,(v,s) in enumerate(zip(mean,slope)):
        lo,hi=min(neighbor_l[k],v,neighbor_r[k]),max(neighbor_l[k],v,neighbor_r[k])
        for offset in (face_l-x,face_r-x):
            delta=offset*s
            if delta>0:
                theta=min(theta,(hi-v)/delta)
            elif delta<0:
                theta=min(theta,(lo-v)/delta)
    if theta<0 or not isfinite(theta):
        raise InvalidState('invalid reconstruction bound')
    if 0<theta<1:
        # Two inward ULPs cover multiplication and addition at a zero bound.
        theta=nextafter(nextafter(theta,0.),0.)
    return tuple(theta*s for s in slope)


@dataclass(frozen=True)
class ReconstructedCellsV1:
    left: tuple
    right: tuple
    species_left: tuple
    species_right: tuple


def reconstruct_v1(mesh,primitives,fractions,*,eos,periodic=False):
    if type(periodic) is not bool:
        raise InvalidState('periodic reconstruction must be explicit bool')
    n=mesh.n
    if len(primitives)!=n or len(fractions)!=n:
        raise InvalidState('reconstruction dimensions differ from mesh')
    for w,y in zip(primitives,fractions):
        eos.validate(w)
        if (len(y)!=4 or any(not isfinite(v) or v<0 or v>1 for v in y)
                or abs(fsum(y)-1)>32*ulp(1.)):
            raise InvalidState('reconstruction requires admissible four-species fractions')
    gas_l,gas_r,species_l,species_r=[],[],[],[]
    length=mesh.faces[-1]-mesh.faces[0]
    for i,(w,y) in enumerate(zip(primitives,fractions)):
        if n<3 or (not periodic and i in (0,n-1)):
            sl=(0.,0.,0.)
            sy=(0.,0.,0.,0.)
        else:
            l,r=(i-1)%n,(i+1)%n
            xl=mesh.centers[l]-(length if i==0 else 0.)
            xr=mesh.centers[r]+(length if i==n-1 else 0.)
            arguments=(xl,mesh.centers[i],xr,mesh.faces[i],mesh.faces[i+1])
            sl=_bounded_slope(w[:3],primitives[l][:3],primitives[r][:3],*arguments)
            sy=_bounded_slope(y,fractions[l],fractions[r],*arguments,simplex=True)
        for face,gas,species in ((mesh.faces[i],gas_l,species_l),
                                 (mesh.faces[i+1],gas_r,species_r)):
            offset=face-mesh.centers[i]
            state=tuple(v+offset*s for v,s in zip(w[:3],sl))+(w[3],)
            mixture=tuple(v+offset*s for v,s in zip(y,sy))
            eos.validate(state)
            if any(v<0 or v>1 for v in mixture) or abs(fsum(mixture)-1)>32*ulp(1.):
                raise InvalidState('reconstructed species outside simplex')
            gas.append(state)
            species.append(mixture)
    return ReconstructedCellsV1(tuple(gas_l),tuple(gas_r),tuple(species_l),tuple(species_r))
