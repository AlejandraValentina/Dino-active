from copy import deepcopy
import math
from pathlib import Path
import pytest
from scripts.diagnostics.localize_mesh_sensitivity_v1 import analyze,load,sha,verify_geometry
from scripts.diagnostics.diagnose_integrated_mesh_v1 import restrict_state

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'
A=ROOT/'spatial-boundary-v2-engine'
B=ROOT/'endpoint-mesh88-v2'


def test_same_volume_projection_preserves_every_euler_integral_and_species():
    ca,cb=load(A/'configuration.json'),load(B/'configuration.json')
    s=load(B/'checkpoint-720.json')['state'];r=restrict_state(s,cb,ca)
    for a,b in zip(ca['ducts'],cb['ducts']):
        name=a['id']
        for k in range(4):
            before=math.fsum(q[k]*v for q,v in zip(s['ducts'][name],b['mesh']['volumes']))
            after=math.fsum(q[k]*v for q,v in zip(r['ducts'][name],a['mesh']['volumes']))
            assert after==pytest.approx(before,rel=2e-15,abs=1e-25)
            assert math.fsum(x[k] for x in r['species']['ducts'][name])==pytest.approx(math.fsum(x[k] for x in s['species']['ducts'][name]),rel=2e-15,abs=1e-25)


def test_geometry_guard_rejects_shifted_face_despite_same_cell_count():
    ca,cb=load(A/'configuration.json'),load(B/'configuration.json')
    cb=deepcopy(cb);cb['ducts'][-1]['mesh']['faces'][2]+=1e-5
    with pytest.raises(ValueError,match='exact conservative'):verify_geometry(ca,cb,sha(A/'configuration.json'))


def test_known_maximum_is_interior_density_and_not_work():
    r=analyze(A,B)
    assert r['phases'][0]['maximum_difference']<2e-15
    top=r['phases'][-1]['ranked'][0]
    assert top['metric']=='exhaust/4/density'
    assert top['location']['endpoint_cell'] is False
    assert top['location']['fine_children']==[8,9]
