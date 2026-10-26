from copy import deepcopy
import math
import random

import pytest

from motorsim.gas1d.mesh import uniform_mesh,smooth_mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.spatial_reconstruction_v1 import reconstruct_v1
from motorsim.gas1d.spatial_reconstruction_v2 import reconstruct_v2


@pytest.mark.parametrize('mesh',[uniform_mesh(8),smooth_mesh(8)])
def test_endpoint_linear_consistency_and_unchanged_interior(mesh):
    gas=[(1.+.1*x,10.+x,1e5+100*x,1.) for x in mesh.centers]
    mix=[(.5+.1*x,.2,.2-.1*x,.1) for x in mesh.centers]
    before=deepcopy((gas,mix));e=IdealGas()
    a,b=reconstruct_v1(mesh,gas,mix,eos=e),reconstruct_v2(mesh,gas,mix,eos=e)
    assert (gas,mix)==before
    for i in (0,mesh.n-1):
        for face,row,y in ((mesh.faces[i],b.left[i],b.species_left[i]),
                           (mesh.faces[i+1],b.right[i],b.species_right[i])):
            assert row==pytest.approx((1.+.1*face,10.+face,1e5+100*face,1.),rel=1e-13)
            assert y==pytest.approx((.5+.1*face,.2,.2-.1*face,.1),rel=1e-13)
    assert a.left[1:-1]==b.left[1:-1] and a.right[1:-1]==b.right[1:-1]
    assert a.species_left[1:-1]==b.species_left[1:-1]


@pytest.mark.parametrize('n',[1,2])
def test_short_mesh_explicitly_keeps_v1(n):
    m=uniform_mesh(n);w=[(1.,0.,1e5,1.)]*n;y=[(1.,0.,0.,0.)]*n;e=IdealGas()
    assert reconstruct_v2(m,w,y,eos=e)==reconstruct_v1(m,w,y,eos=e)


def test_steep_admissible_states_stay_positive_and_in_species_simplex():
    rng=random.Random(8301);m=uniform_mesh(6);e=IdealGas()
    for _ in range(150):
        w=[(10**rng.uniform(-5,4),rng.uniform(-1000,1000),10**rng.uniform(-2,9),1.) for i in range(6)]
        y=[]
        for i in range(6):
            raw=[rng.random() if rng.random()<.7 else 0. for _ in range(4)]
            if not sum(raw):raw[0]=1.
            y.append(tuple(x/sum(raw) for x in raw))
        r=reconstruct_v2(m,w,y,eos=e)
        for row in (*r.left,*r.right):e.validate(row)
        for row in (*r.species_left,*r.species_right):
            assert min(row)>=0 and max(row)<=1 and math.fsum(row)==pytest.approx(1.,abs=4e-15)


def test_passive_species_do_not_change_boundary_gas_slopes():
    m=uniform_mesh(6);w=[(1.+.1*x,10*x,1e5+200*x,1.) for x in m.centers];e=IdealGas()
    a=reconstruct_v2(m,w,[(1.,0.,0.,0.)]*6,eos=e)
    b=reconstruct_v2(m,w,[(.3,.2,.4,.1)]*6,eos=e)
    assert (a.left,a.right)==(b.left,b.right)
