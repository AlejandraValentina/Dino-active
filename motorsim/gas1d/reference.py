"""Independent analytical verification references, not called by the FV solver.

Euler shock/rarefaction relations: Toro, 3rd ed. (2009), ch. 4;
https://www.clawpack.org/riemann_book/html/Euler.html . No HLLC imports.
"""
from math import sqrt,fsum


class ExactRiemann:
    def __init__(self,left,right,eos):
        self.left=left;self.right=right;self.eos=eos;g=eos.gamma
        al=eos.sound_speed(left);ar=eos.sound_speed(right)
        if right[1]-left[1]>=2*(al+ar)/(g-1):raise ValueError('Reference vacuum not supported')
        def f(p,w):
            r,u,pk,y=w
            if p>pk:return (p-pk)*sqrt(2/((g+1)*r)/(p+(g-1)/(g+1)*pk))
            return 2*sqrt(g*pk/r)/(g-1)*((p/pk)**((g-1)/(2*g))-1)
        def residual(p):return f(p,left)+f(p,right)+right[1]-left[1]
        low=0.;high=max(left[2],right[2])
        for _ in range(100):
            if residual(high)>=0:break
            high*=2
        else:raise ValueError('Reference pressure bracket failed')
        scale=al+ar+abs(left[1])+abs(right[1]);pstar=None
        for _ in range(200):
            mid=(low+high)/2;res=residual(mid)
            if abs(res)<=1e-13*scale:pstar=mid;break
            if res>0:high=mid
            else:low=mid
        if pstar is None:raise ValueError('Reference pressure residual failed')
        self.pstar=pstar;self.ustar=(left[1]+right[1]+f(pstar,right)-f(pstar,left))/2
        self.residual=abs(residual(pstar))/scale;self.waves=[]
        for side,w,a in ((-1,left,al),(1,right,ar)):
            r,u,p,y=w
            if pstar>p:
                s=u+side*a*sqrt((g+1)/(2*g)*pstar/p+(g-1)/(2*g));self.waves.append((s,s))
            else:
                astar=a*(pstar/p)**((g-1)/(2*g))
                self.waves.append((u+side*a,self.ustar+side*astar))

    def sample(self,xi):
        g=self.eos.gamma;s=-1 if xi<=self.ustar else 1
        w=self.left if s==-1 else self.right;r,u,p,y=w;a=sqrt(g*p/r)
        head,tail=self.waves[0 if s==-1 else 1]
        if s*xi>=s*head:return w
        if self.pstar>p:
            b=(g-1)/(g+1);ratio=self.pstar/p
            return r*(ratio+b)/(b*ratio+1),self.ustar,self.pstar,y
        if s*xi<=s*tail:return r*(self.pstar/p)**(1/g),self.ustar,self.pstar,y
        # Within an isentropic rarefaction fan, u+s*a=xi.
        uf=2/(g+1)*(-s*a+(g-1)*u/2+xi)
        af=2/(g+1)*(a+s*(g-1)*(xi-u)/2)
        return r*(af/a)**(2/(g-1)),uf,p*(af/a)**(2*g/(g-1)),y

    def breaks(self,t):
        return sorted(set([.5+self.ustar*t,*[.5+s*t for pair in self.waves for s in pair]]))


# Gauss-Legendre 4, with subdivision estimate. Endpoints are not sampled,
# so split discontinuities do not contaminate quadrature on adjacent intervals.
NODES=(-.8611363115940526,-.3399810435848563,.3399810435848563,.8611363115940526)
WEIGHTS=(.3478548451374538,.6521451548625461,.6521451548625461,.3478548451374538)


def integrate(function,left,right,depth=0):
    def gauss(a,b):
        h=(b-a)/2;mid=(b+a)/2;rows=[function(mid+h*x) for x in NODES]
        return tuple(h*fsum(weight*row[k] for weight,row in zip(WEIGHTS,rows)) for k in range(4))
    whole=gauss(left,right);mid=(left+right)/2
    a=gauss(left,mid);b=gauss(mid,right);split=tuple(x+y for x,y in zip(a,b))
    if all(abs(x-y)<=1e-11*max(abs(x),abs(y),1e-30) for x,y in zip(whole,split)):return split
    if depth>=20:raise ValueError('Reference quadrature not converged')
    a=integrate(function,left,mid,depth+1);b=integrate(function,mid,right,depth+1)
    return tuple(x+y for x,y in zip(a,b))


def cell_integrals(mesh,primitive,eos,area,breaks=()):
    def integrand(x):return tuple(v*area(x) for v in eos.conservative(primitive(x)))
    cells=[]
    for left,right in zip(mesh.faces,mesh.faces[1:]):
        bounds=[left,*sorted(x for x in breaks if left<x<right),right]
        parts=[integrate(integrand,a,b) for a,b in zip(bounds,bounds[1:])]
        cells.append(tuple(fsum(part[k] for part in parts) for k in range(4)))
    return cells


def primitives(mesh,cells,eos):
    return [eos.primitive(tuple(x/v for x in c)) for c,v in zip(cells,mesh.volumes)]
