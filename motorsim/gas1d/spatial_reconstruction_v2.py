"""Opt-in one-sided physical endpoint traces; V1 interiors stay unchanged."""
from math import fsum,nextafter,ulp

from .spatial_reconstruction_v1 import reconstruct_v1,minmod,ReconstructedCellsV1
from .eos import InvalidState

SCHEMA='MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2'


def _endpoint_slope(values,x,face_outer,face_inner,*,species=False):
    a,b,c=values
    d0,d1=x[1]-x[0],x[2]-x[1]
    slopes=[]
    for v0,v1,v2 in zip(a,b,c):
        s0,s1=(v1-v0)/d0,(v2-v1)/d1
        derivative=(2*d0+d1)/(d0+d1)*s0-d0/(d0+d1)*s1
        slopes.append(minmod(1.5*s0,derivative,1.5*s1))
    if species:
        pivot=max(range(4),key=lambda i:a[i])
        slopes[pivot]=-fsum(s for i,s in enumerate(slopes) if i!=pivot)
    theta=1.;limited=False
    for k,(v,s) in enumerate(zip(a,slopes)):
        # Inner face is bounded by adjacent cell means. The outer face is an
        # extrapolation, so that interval must not incorrectly force zero slope.
        delta=(face_inner-x[0])*s
        lo,hi=min(a[k],b[k]),max(a[k],b[k])
        if delta>0:bound=(hi-v)/delta
        elif delta<0:bound=(lo-v)/delta
        else:bound=1.
        if bound<theta:theta=bound;limited=True
        for face in (face_outer,face_inner):
            delta=(face-x[0])*s
            if species:
                bound=((1-v)/delta if delta>0 else -v/delta if delta<0 else 1.)
                if bound<theta:theta=bound;limited=True
            elif k in (0,2) and delta<0 and -delta>=v:
                theta=min(theta,-v/delta);limited=True
    if limited and theta>0:
        theta=nextafter(nextafter(theta,0.),0.)
    return tuple(theta*s for s in slopes)


def reconstruct_v2(mesh,primitives,fractions,*,eos,periodic=False):
    base=reconstruct_v1(mesh,primitives,fractions,eos=eos,periodic=periodic)
    if periodic or mesh.n<3:return base
    gas_l,gas_r=list(base.left),list(base.right)
    y_l,y_r=list(base.species_left),list(base.species_right)
    for i,neighbors,orientation,outer,inner in (
            (0,(0,1,2),1,mesh.faces[0],mesh.faces[1]),
            (mesh.n-1,(mesh.n-1,mesh.n-2,mesh.n-3),-1,mesh.faces[-1],mesh.faces[-2])):
        x=[orientation*mesh.centers[j] for j in neighbors]
        gas=[primitives[j][:3] for j in neighbors]
        mix=[fractions[j] for j in neighbors]
        sg=_endpoint_slope(gas,x,orientation*outer,orientation*inner)
        sy=_endpoint_slope(mix,x,orientation*outer,orientation*inner,species=True)
        for face,output,composition in ((mesh.faces[i],gas_l,y_l),(mesh.faces[i+1],gas_r,y_r)):
            offset=orientation*(face-mesh.centers[i])
            w=tuple(v+offset*s for v,s in zip(gas[0],sg))+(primitives[i][3],)
            y=tuple(v+offset*s for v,s in zip(mix[0],sy))
            # Reuse V1 validation of rho/p and simplex, never change cell means.
            eos.validate(w)
            if any(v<0 or v>1 for v in y) or abs(fsum(y)-1)>32*ulp(1.):
                raise InvalidState('reconstructed boundary species outside simplex')
            output[i],composition[i]=w,y
    return ReconstructedCellsV1(tuple(gas_l),tuple(gas_r),tuple(y_l),tuple(y_r))
