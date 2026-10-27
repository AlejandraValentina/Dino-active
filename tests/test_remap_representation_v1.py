from copy import deepcopy
import numpy as np
import pytest
from tests.test_checkpoint_mesh_sensitivity_v1 import fixture
from scripts.diagnostics.remap_representation_v1 import initialize,project,configurations
from scripts.diagnostics.diagnose_integrated_mesh_v1 import restrict_state
from motorsim.integrated_2t import _json_evidence_equal


@pytest.mark.parametrize('family',['P0','P1'])
@pytest.mark.parametrize('level',[1,2])
def test_conservative_admissible_nested_initialization(family,level):
    c,cp,ch,ph=fixture();saved=deepcopy(cp)
    e,f,info=initialize(c,cp,level,family,ph)
    assert cp==saved
    assert info['inventory_max_relative_error']<2e-14
    assert info['restriction_max_relative_error']<2e-14
    assert _json_evidence_equal(e.snapshot()['fuel_combustion'],cp['fuel_combustion'])
    assert e.crank_angle_unwrapped_deg==9000
    for name,rows in e.state['ducts'].items():
        for q,s in zip(rows,e.state['species']['ducts'][name]):
            assert e._primitive(q)[2]>0
            assert min(s)>=0
    chain=configurations(c,level);restricted=e.state
    for k in range(level,0,-1):restricted=restrict_state(restricted,chain[k],chain[k-1])
    for name in cp['state']['ducts']:
        np.testing.assert_allclose(restricted['species']['ducts'][name],cp['state']['species']['ducts'][name],rtol=2e-14,atol=1e-25)
    with pytest.raises(ValueError,match='configuration mismatch'):e.restore(cp)


def test_direct_root_projection_commutes_with_restriction():
    c,cp,_,_=fixture();chain=configurations(c,2)
    for family in ('P0','P1'):
        fine,_=project(cp['state'],c,chain[2],family)
        medium,_=project(cp['state'],c,chain[1],family)
        r=restrict_state(fine,chain[2],chain[1])
        for n in medium['ducts']:
            np.testing.assert_allclose(r['ducts'][n],medium['ducts'][n],rtol=2e-14,atol=1e-14)
            np.testing.assert_allclose(r['species']['ducts'][n],medium['species']['ducts'][n],rtol=2e-14,atol=1e-25)


def test_linear_field_integrates_at_exact_frustum_centroid():
    c,cp,_,_=fixture();state=deepcopy(cp['state'])
    for path in c['ducts']:
        n=path['id'];mesh=path['mesh']
        for i,(x,v) in enumerate(zip(mesh['centers'],mesh['volumes'])):
            rho=1+.1*x;state['ducts'][n][i]=[rho,2+.2*x,3e5+100*x,rho]
            state['species']['ducts'][n][i]=[rho*v/4]*4
    fine=configurations(c,2)[2];mapped,_=project(state,c,fine,'P1')
    for path in fine['ducts']:
        n=path['id'];nroot=len(state['ducts'][n])
        for j,x in enumerate(path['mesh']['centers']):
            if j//4 in (0,nroot-1):continue
            np.testing.assert_allclose(mapped['ducts'][n][j],[1+.1*x,2+.2*x,3e5+100*x,1+.1*x],rtol=2e-14)
