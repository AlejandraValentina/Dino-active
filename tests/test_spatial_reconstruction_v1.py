import math
import random

import pytest

from motorsim.gas1d.eos import IdealGas,InvalidState
from motorsim.gas1d.mesh import uniform_mesh,smooth_mesh
from motorsim.gas1d.spatial_reconstruction_v1 import reconstruct_v1
from scripts.diagnostics.verify_spatial_reconstruction_v1 import entropy_cell,run_case


@pytest.mark.parametrize('periodic',[False,True])
def test_constant_and_absent_species_are_preserved_exactly(periodic):
    m=uniform_mesh(8);w=[(1.,0.,1e5,1.)]*8;y=[(1.,0.,0.,0.)]*8
    r=reconstruct_v1(m,w,y,eos=IdealGas(),periodic=periodic)
    assert r.left==r.right==tuple(w)
    assert r.species_left==r.species_right==tuple(y)


def test_nonuniform_volume_centroids_reconstruct_linear_fields():
    m=smooth_mesh(12)
    w=[(1+.2*x,.1*x,1e5+100*x,1.) for x in m.centers]
    y=[(.4+.1*x,.2-.1*x,.3,.1) for x in m.centers]
    r=reconstruct_v1(m,w,y,eos=IdealGas())
    for i in range(1,m.n-1):
        for f,out in [(m.faces[i],r.left[i]),(m.faces[i+1],r.right[i])]:
            assert out==pytest.approx((1+.2*f,.1*f,1e5+100*f,1.),rel=1e-12)
    assert r.left[0]==w[0] and r.right[-1]==w[-1]


@pytest.mark.parametrize('seed',range(20))
def test_randomized_positive_simplex_and_neighbor_bounds(seed):
    rng=random.Random(seed);m=smooth_mesh(9)
    w=[(10**rng.uniform(-5,2),rng.uniform(-100,100),10**rng.uniform(-4,6),1.) for _ in m.centers]
    ys=[[10**rng.uniform(-20,0) for _ in range(4)] for _ in m.centers]
    y=[tuple(v/sum(row) for v in row) for row in ys]
    r=reconstruct_v1(m,w,y,eos=IdealGas())
    for i in range(m.n):
        for row in (r.left[i],r.right[i]):
            for k in range(3):
                bounds=[v[k] for v in w[max(0,i-1):min(m.n,i+2)]]
                assert min(bounds)<=row[k]<=max(bounds)
        for row in (r.species_left[i],r.species_right[i]):
            assert min(row)>=0 and max(row)<=1
            assert sum(row)==pytest.approx(1.,abs=32*math.ulp(1.))


def test_passive_composition_does_not_change_gas_reconstruction():
    m=uniform_mesh(16)
    w=[(1+.2*math.sin(2*math.pi*x),1.,1e5,1.) for x in m.centers]
    smooth=[(.4+.1*math.sin(2*math.pi*x),.2,.3,.1-.1*math.sin(2*math.pi*x)) for x in m.centers]
    pure=[(1.,0.,0.,0.)]*m.n
    a=reconstruct_v1(m,w,smooth,eos=IdealGas(),periodic=True)
    b=reconstruct_v1(m,w,pure,eos=IdealGas(),periodic=True)
    assert a.left==b.left and a.right==b.right


@pytest.mark.parametrize('bad',[(.5,.5,-1e-3,.001),(.2,.2,.2,.2),(math.nan,0.,0.,1.)])
def test_invalid_simplex_is_not_clipped(bad):
    with pytest.raises(InvalidState):
        reconstruct_v1(uniform_mesh(3),[(1.,0.,1e5,1.)]*3,[bad]*3,eos=IdealGas())


def test_analytic_species_cell_average_matches_independent_quadrature():
    a,b,t=.16,.23,.07
    rho,ys=entropy_cell(a,b,t)
    n=10000
    expected=[0.]*5
    for i in range(n):
        x=a+(b-a)*(i+.5)/n-t
        r=1+.2*math.sin(2*math.pi*x);c=math.cos(2*math.pi*x)
        y=(.4+.1*c,.2,.3-.05*c,.1-.05*c)
        expected[0]+=r/n
        for j in range(4):expected[j+1]+=r*y[j]/n
    assert (rho,*ys)==pytest.approx(expected,rel=1e-10)


def test_actual_gas_and_species_error_improves_at_equal_mesh():
    old=run_case(80,'entropy','legacy');new=run_case(80,'entropy','muscl')
    assert new['rho_L1']<old['rho_L1']/5
    assert new['species_L1']<old['species_L1']/5
    assert new['conservation_abs']<1e-11
