import numpy as np
from tests.test_checkpoint_mesh_sensitivity_v1 import fixture
from scripts.diagnostics.compare_remap_representation_v1 import profile_metrics,restrict_to
from scripts.diagnostics.remap_representation_v1 import initialize


def test_profile_inventories_and_empty_crossings_are_explicit():
    c,cp,_,_=fixture();r=profile_metrics(cp['state'],c)
    for name,rows in cp['state']['species']['ducts'].items():
        for k,label in enumerate(('fresh','fuel','residual','burned')):
            np.testing.assert_allclose(r[name]['species'][label]['inventory_kg'],np.array(rows)[:,k].sum(),rtol=1e-15)
    assert r['exhaust']['species']['burned']['crossings_m']['0.9']==[]
    assert r['exhaust']['species']['burned']['max_gradient_per_m']>0


def test_fourfold_common_volume_comparison_preserves_parent_means():
    c,cp,_,ph=fixture();e,f,_=initialize(c,cp,2,'P1',ph)
    a=restrict_to(e.state,f,c)
    for name in a['ducts']:
        np.testing.assert_allclose(a['ducts'][name],cp['state']['ducts'][name],rtol=2e-14,atol=1e-14)
