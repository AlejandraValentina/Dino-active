"""Shared axial faces, exact frustum volumes and volume centroids; SI internally."""
from dataclasses import dataclass
from math import ceil, pi, sin, cos, isfinite


@dataclass(frozen=True)
class Mesh:
    faces: tuple
    areas: tuple
    volumes: tuple
    centers: tuple

    def __post_init__(self):
        n=len(self.volumes)
        if n<1 or len(self.faces)!=n+1 or len(self.areas)!=n+1 or len(self.centers)!=n:
            raise ValueError('Invalid mesh dimensions')
        if not all(isfinite(v) for seq in (self.faces,self.areas,self.volumes,self.centers) for v in seq):
            raise ValueError('Nonfinite geometry')
        if min(self.areas)<=0 or min(self.volumes)<=0: raise ValueError('Nonpositive geometry')
        if any(not self.faces[i]<self.centers[i]<self.faces[i+1] for i in range(n)):
            raise ValueError('Invalid face/centroid ordering')

    @property
    def n(self): return len(self.volumes)

    @property
    def widths(self): return tuple(b-a for a,b in zip(self.faces,self.faces[1:]))

    def as_dict(self):
        return {k:list(getattr(self,k)) for k in ('faces','areas','volumes','centers')}


def segments_mesh(segments, dx_target):
    """Segments use existing length/start_diameter/end_diameter names in mm."""
    if not isfinite(dx_target) or dx_target<=0: raise ValueError('dx_target must be positive metres')
    faces=[0.];areas=[];volumes=[];centers=[];previous=None
    for seg in segments:
        length,d0,d1=(float(seg[k])*0.001 for k in ('length','start_diameter','end_diameter'))
        if not all(isfinite(v) and v>0 for v in (length,d0,d1)): raise ValueError('Invalid segment')
        if previous is not None:
            if abs(d0-previous)>1e-12+1e-12*max(d0,previous): raise ValueError('Discontinuous area')
            d0=previous
        count=ceil(length/dx_target);base=faces[-1]
        if not areas:areas.append(pi*d0*d0/4)
        for i in range(count):
            left=base+length*i/count;right=base+length*(i+1)/count;h=right-left
            dl=d0+(d1-d0)*i/count;dr=d0+(d1-d0)*(i+1)/count;k=(dr-dl)/h
            v=pi*h*(dl*dl+dl*dr+dr*dr)/12
            moment=pi/4*(dl*dl*h*h/2+2*dl*k*h**3/3+k*k*h**4/4)
            volumes.append(v);centers.append(left+moment/v)
            faces.append(right);areas.append(pi*dr*dr/4)
        previous=d1
    return Mesh(tuple(faces),tuple(areas),tuple(volumes),tuple(centers))


def uniform_mesh(n, length=1., area=.01):
    if type(n) is not int or n<=0 or length<=0 or area<=0: raise ValueError('Invalid uniform mesh')
    faces=tuple(length*i/n for i in range(n+1))
    return Mesh(faces,(area,)*(n+1),tuple(area*(b-a) for a,b in zip(faces,faces[1:])),
                tuple((a+b)/2 for a,b in zip(faces,faces[1:])))


def smooth_mesh(n):
    """Analytical geometry exclusively needed by contractual T08: L=1 metre."""
    faces=tuple(i/n for i in range(n+1));k=2*pi
    def integral(x):return .011*x-.001*sin(k*x)/k
    def moment(x):return .011*x*x/2-.001*(x*sin(k*x)/k+cos(k*x)/(k*k))
    volumes=tuple(integral(b)-integral(a) for a,b in zip(faces,faces[1:]))
    centers=tuple((moment(b)-moment(a))/v for a,b,v in zip(faces,faces[1:],volumes))
    return Mesh(faces,tuple(.01*(1+.2*sin(pi*x)**2) for x in faces),volumes,centers)
