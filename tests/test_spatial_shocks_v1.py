import math

import pytest

from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.exact_riemann_reference_v1 import exact_riemann_v1
from scripts.diagnostics.verify_spatial_reconstruction_v1 import advance


def test_sod_shock_positive_species_conservation_and_exact_shock_speed():
    e=IdealGas(gamma=1.4);m=uniform_mesh(160,1.,1.)
    gas=[];species=[]
    for x in m.centers:
        w=(1.,0.,1.,1.) if x<.5 else (.125,0.,.1,0.)
        gas.append(e.conservative(w)[:3])
        species.append((w[0],0.,0.,0.) if x<.5 else (0.,0.,0.,w[0]))
    initial=[math.fsum(q[k]/m.n for q in gas) for k in (0,2)]
    initial_species=[math.fsum(s[k]/m.n for s in species) for k in range(4)]
    t=0.
    while t<.1:
        speed=max(abs(q[1]/q[0])+e.sound_speed(e.primitive((*q,q[0]))) for q in gas)
        dt=min(.1-t,.2/(m.n*speed))
        gas,species=advance(m,gas,species,e,'muscl',dt,periodic=False)
        t+=dt
    states=[e.primitive((*q,q[0])) for q in gas]
    assert min(w[0] for w in states)>0 and min(w[2] for w in states)>0
    assert min(v for s in species for v in s)>=0
    final=[math.fsum(q[k]/m.n for q in gas) for k in (0,2)]
    final_species=[math.fsum(s[k]/m.n for s in species) for k in range(4)]
    assert final==pytest.approx(initial,abs=1e-11)
    assert final_species==pytest.approx(initial_species,abs=1e-11)
    exact=exact_riemann_v1((1.,0.,1.,1.),(.125,0.,.1,0.),eos=e)
    shock=.5+t*exact.right_speeds[-1]
    threshold=(exact.right_star[0]+.125)/2
    measured=max(x for x,w in zip(m.centers,states) if w[0]>threshold)
    assert abs(measured-shock)<4/m.n
    pressure_error=sum(abs(w[2]-exact.sample((x-.5)/t)[2])/m.n for x,w in zip(m.centers,states))
    assert pressure_error<.03


def test_stationary_contact_and_pure_species_do_not_diffuse():
    e=IdealGas(gamma=1.4);m=uniform_mesh(8,1.,1.)
    gas=[e.conservative((1. if i<4 else .1,0.,1.,1.))[:3] for i in range(8)]
    species=[(q[0],0.,0.,0.) if i<4 else (0.,0.,0.,q[0]) for i,q in enumerate(gas)]
    q,s=advance(m,gas,species,e,'muscl',.001,periodic=False)
    assert q==gas and s==species
