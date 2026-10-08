"""Float64 batching of frozen Euler/MUSCL/HLLC algebra; scalar exceptional faces.

No compiled backend. Scalar EOS, boundaries and HLLC remain the reference.
All exceptional HLLC faces delegate to that reference, including HLLE reasons.
"""
import numpy as np
from .gas1d.eos import InvalidState
from .gas1d.riemann import hllc_flux


def valid(w,eos):
    with np.errstate(all='ignore'):
        T=w[:,2]/(w[:,0]*eos.R)
    return np.isfinite(w).all(axis=1)&(w[:,0]>0)&(w[:,2]>0)&(w[:,3]>=0)&(w[:,3]<=1)&np.isfinite(T)&(T>0)


def primitive(cells,volumes,eos):
    q=cells/volumes[:,None];r,m,e,z=q.T
    if not (np.isfinite(q).all() and (r>0).all() and (z>=0).all() and (z<=r).all()):raise InvalidState('Conserved rho/species inadmissible')
    u=m/r;p=(eos.gamma-1)*(e-.5*m*u)
    w=np.column_stack((r,u,p,z/r))
    if not valid(w,eos).all():raise InvalidState('rho/p/Y inadmissible')
    return w


def flux(w,eos):
    r,u,p,y=w.T;m=r*u
    return np.column_stack((m,m*u+p,u*(eos.gamma*p/(eos.gamma-1)+.5*r*u*u),m*y))


def conservative(w,eos):
    r,u,p,y=w.T
    return np.column_stack((r,r*u,p/(eos.gamma-1)+.5*r*u*u,r*y))


def hllc(left,right,eos):
    if not (valid(left,eos).all() and valid(right,eos).all()):raise InvalidState('rho/p/Y inadmissible')
    rl,ul,pl,yl=left.T;rr,ur,pr,yr=right.T;g=eos.gamma
    al=np.sqrt(g*pl/rl);ar=np.sqrt(g*pr/rr);wl=np.sqrt(rl);wr=np.sqrt(rr)
    hl=g*pl/((g-1)*rl)+ul*ul/2;hr=g*pr/((g-1)*rr)+ur*ur/2
    u=(wl*ul+wr*ur)/(wl+wr);h=(wl*hl+wr*hr)/(wl+wr);a2=(g-1)*(h-u*u/2)
    if not (np.isfinite(a2).all() and (a2>0).all()):raise InvalidState('Invalid Roe speed')
    a=np.sqrt(a2);sl=np.minimum(np.minimum(ul-al,ur-ar),u-a);sr=np.maximum(np.maximum(ul+al,ur+ar),u+a)
    if not (np.isfinite(sl).all() and np.isfinite(sr).all() and (sl<sr).all()):raise InvalidState('Invalid wave bounds')
    fl=flux(left,eos);fr=flux(right,eos)
    equal=(left==right).all(axis=1);positive=sl>=0;negative=sr<=0
    result=np.where((equal|positive)[:,None],fl,fr);sm=np.where(equal|positive,ul,ur)
    active=~(equal|positive|negative)
    # Speculative vector arithmetic is never accepted on an exceptional face.
    # The exact frozen branch and its fallback reason are evaluated there below.
    with np.errstate(all='ignore'):
        den=rl*(sl-ul)-rr*(sr-ur)
        contact=(pr-pl+rl*ul*(sl-ul)-rr*ur*(sr-ur))/den
        good=active&np.isfinite(den)&(den!=0)&np.isfinite(contact)&(sl<contact)&(contact<sr)
        stars=[]
        for w,s in ((left,sl),(right,sr)):
            r,v,p,y=w.T
            rs=r*(s-v)/(s-contact);ps=p+r*(s-v)*(contact-v)
            es=p/((g-1)*r)+v*v/2+(contact-v)*(contact+p/(r*(s-v)))
            good &= (s!=contact)&(s!=v)&np.isfinite(rs)&np.isfinite(ps)&np.isfinite(es)&(rs>0)&(ps>0)&(es-contact*contact/2>0)
            stars.append(np.column_stack((rs,rs*contact,rs*es,rs*y)))
        choose=contact>=0
        star=np.where(choose[:,None],stars[0],stars[1]);state=np.where(choose[:,None],left,right)
        speed=np.where(choose,sl,sr);baseflux=np.where(choose[:,None],fl,fr)
        conserved=conservative(state,eos)
        good &= np.isfinite(conserved).all(axis=1)
        out=baseflux+speed[:,None]*(star-conserved)
        mass=star[:,0]*contact;out[:,0]=mass;out[:,3]=mass*state[:,3]
    result[good]=out[good];sm[good]=contact[good]
    reasons={};fallback_speeds={}
    for i in np.flatnonzero(active&~good):
        f,s,reason=hllc_flux(tuple(left[i].tolist()),tuple(right[i].tolist()),eos)
        result[i]=f;sm[i]=np.nan if s[1] is None else s[1]
        if reason:reasons[int(i)]=reason;fallback_speeds[int(i)]=s
    return result,np.column_stack((sl,sm,sr)),reasons,fallback_speeds


class Kernel:
    def __init__(self,mesh,eos):
        self.eos=eos;self.mesh=mesh
        self.volumes=np.array(mesh.volumes);self.areas=np.array(mesh.areas);self.widths=np.array(mesh.widths)
        x=np.array(mesh.centers);f=np.array(mesh.faces)
        xl=np.r_[2*f[0]-x[0],x[:-1]];xr=np.r_[x[1:],2*f[-1]-x[-1]]
        self.dl=(x-xl)[:,None];self.dr=(xr-x)[:,None]
        self.left_offset=(f[:-1]-x)[:,None];self.right_offset=(f[1:]-x)[:,None]
        self.area_delta=self.areas[1:]-self.areas[:-1]

    def reconstruct(self,w,boundaries):
        lo=boundaries[0].face_state(tuple(w[0].tolist()),-1,self.eos)
        hi=boundaries[1].face_state(tuple(w[-1].tolist()),1,self.eos)
        left=np.vstack((lo,w[:-1]));right=np.vstack((w[1:],hi))
        a=(w-left)/self.dl;b=(right-w)/self.dr
        slope=np.where((a==0)|(b==0)|((a>0)!=(b>0)),0.,np.where(np.abs(a)<=np.abs(b),a,b))
        lf=w+slope*self.left_offset;rf=w+slope*self.right_offset
        bad=~(valid(lf,self.eos)&valid(rf,self.eos));lf[bad]=w[bad];rf[bad]=w[bad]
        return lf,rf,np.flatnonzero(bad).tolist()

    def cfl(self,w,speeds,cfl):
        if not np.isfinite(cfl) or not 0<cfl<=.6:raise ValueError('Contractual CFL outside (0,.6]')
        limits=np.minimum(self.widths/(np.abs(w[:,1])+np.sqrt(self.eos.gamma*w[:,2]/w[:,0])),
            2*self.volumes/(self.areas[:-1]*speeds[:-1]+self.areas[1:]*speeds[1:]))
        index=int(np.argmin(limits));unit=float(limits[index])
        return cfl*unit,index,unit
