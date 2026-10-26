import json
import math
from pathlib import Path

import pytest

from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.spatial_reconstruction_v1 import SCHEMA
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.port_connection_v2 import SCHEMA as PORT_SCHEMA
from test_integrated_2t import _case


def case(spatial=True):
    identity={'fixture':'spatial-wave-static-v1','port_connection_model':PORT_SCHEMA}
    if spatial:identity['spatial_reconstruction_model']=SCHEMA
    mesh=uniform_mesh(8,.02,1e-4)
    states=[(1.1768*(1+.1*math.sin(2*math.pi*x/.02)),20.,101325.,1.) for x in mesh.centers]
    species=[]
    for w,x,volume in zip(states,mesh.centers,mesh.volumes):
        y=.6+.1*math.cos(2*math.pi*x/.02)
        mass=w[0]*volume
        species.append((mass*y,0.,mass*(1-y),0.))
    return _case(geometry_identity=identity,exhaust_mesh=mesh,
        exhaust_initial_states=states,duct_species={'exhaust':species},exhaust_area=0.)


def test_muscl_is_selected_in_both_stages_with_conservation_and_distinct_result():
    old,new=case(False),case(True)
    assert new.geometry_sha256!=old.geometry_sha256
    old.step(1e-8,.00006);new.step(1e-8,.00006)
    assert old.state!=new.state
    for e in (old,new):
        report=e.conservation_report()
        assert abs(report['mass']['residual'])<1e-15
        assert abs(report['energy']['residual'])<1e-10
        assert max(abs(v['residual']) for v in report['species'].values())<1e-15


def test_same_model_restart_is_exact_and_cross_model_restore_is_rejected():
    a,b=case(),case()
    a.step(1e-8,.00006)
    saved=json.loads(json.dumps(a.snapshot()))
    b.restore(saved)
    a.step(1e-8,.00006);b.step(1e-8,.00006)
    assert a.snapshot()==b.snapshot()
    with pytest.raises(ValueError):case(False).restore(saved)


def test_spatial_selection_is_immutable_and_unknown_model_is_not_ignored():
    e=case()
    e.spatial_reconstruction_model=None
    with pytest.raises(ValueError,match='changed after construction'):
        e.step(1e-8,.00006)
    with pytest.raises(ValueError,match='spatial_reconstruction_model'):
        _case(geometry_identity={'spatial_reconstruction_model':'unsupported'})


@pytest.mark.parametrize('with_port',[False,True])
def test_config_v8_recreates_and_resumes_real_supported_geometry(with_port):
    receipt=json.loads(Path('results/periodic-rpm-curves-v1/receipt.json').read_text(encoding='utf-8'))
    path=Path(receipt['points'][0]['result']).parent/'native-configuration.json'
    if not path.exists():pytest.skip('external historical input not present')
    c=json.loads(path.read_text(encoding='utf-8'))
    c['geometry_identity']['spatial_reconstruction_model']=SCHEMA
    if with_port:c['geometry_identity']['port_connection_model']=PORT_SCHEMA
    with pytest.raises(ValueError,match='requires configuration schema'):
        IntegratedEngine2T.from_configuration_dict(c)
    c['base_configuration_schema']=c['schema']
    c['schema']='MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V8'
    a=IntegratedEngine2T.from_configuration_dict(c)
    b=IntegratedEngine2T.from_configuration_dict(a.configuration_dict())
    assert a.configuration_json()==b.configuration_json()
    a.step(1e-8,.00054)
    b.restore(json.loads(json.dumps(a.snapshot())))
    a.step(1e-8,.00054);b.step(1e-8,.00054)
    assert a.snapshot()==b.snapshot()
