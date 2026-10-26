from copy import deepcopy
import json

import pytest

from motorsim.integrated_2t import IntegratedEngine2T, _port_face_flux, _solver_dependency_hashes
from motorsim.port_connection_v2 import SCHEMA
from test_integrated_2t import _case


def case(**kwargs):
    return _case(geometry_identity={'fixture':'three-transfer-static-volume-v1',
        'port_connection_model':SCHEMA},**kwargs)


def test_selection_is_explicit_hashed_and_immutable():
    old = _case()
    new = case()
    assert old.port_connection_model is None
    assert new.geometry_sha256 != old.geometry_sha256
    assert new.configuration_identity != old.configuration_identity
    new.port_connection_model = None
    with pytest.raises(ValueError,match='changed after construction'):
        new.step(1e-8,.0001)
    with pytest.raises(ValueError,match='port_connection_model'):
        _case(geometry_identity={'port_connection_model':'not-a-valid-model'})
    assert 'motorsim.port_connection_v2' in _solver_dependency_hashes()
    assert 'motorsim.gas1d.exact_riemann_reference_v1' in _solver_dependency_hashes()


def test_all_eight_ports_have_complete_stage_evidence_and_shared_conservation():
    e = case(exhaust_area=1e-5,intake_area=1e-5,cylinder_pressure=2e5)
    trace = e.step(1e-8,.00006)
    assert trace
    # The engine trace keeps both SSPRK stage dictionaries; locate actual
    # endpoint evidence without relying on a derived cycle summary.
    encoded = json.dumps(trace)
    assert encoded.count('port_connection_states') == 10
    assert encoded.count('chamber_thermodynamics') == 16
    report = e.conservation_report()
    assert abs(report['mass']['residual']) < 1e-15
    assert abs(report['energy']['residual']) < 1e-10
    for r in report['species'].values():
        assert abs(r['residual']) < 1e-15


def test_full_face_pressure_is_not_counted_twice():
    e = case(exhaust_area=1e-5)
    c = e._chamber_state(e.state['chambers']['cylinder'],
                         e.state['species']['chambers']['cylinder'])
    w = e._primitive(e.state['ducts']['exhaust'][0])
    exchange = e._port_exchange(c,w,1e-5,1e-4,-1)
    assert _port_face_flux(exchange,w,1e-4,1e-5) == exchange.flux_x[:3]
    with pytest.raises(ValueError,match='area differs'):
        _port_face_flux(exchange,w,2e-4,1e-5)


def test_checkpoint_replay_and_cross_model_rejection():
    a,b = case(exhaust_area=1e-5),case(exhaust_area=1e-5)
    a.step(1e-8,.00006)
    saved = json.loads(json.dumps(a.snapshot()))
    b.restore(deepcopy(saved))
    a.step(1e-8,.00006)
    b.step(1e-8,.00006)
    assert a.state == b.state
    assert a.conservation_report() == b.conservation_report()
    assert a.snapshot() == b.snapshot()
    old = _case(exhaust_area=1e-5)
    with pytest.raises(ValueError):
        old.restore(saved)


def test_model_selection_survives_supported_configuration_roundtrip():
    # Use a real serialized geometric contract: anonymous test callbacks are
    # deliberately not eligible for configuration re-creation.
    from pathlib import Path
    receipt = json.loads(Path('results/periodic-rpm-curves-v1/receipt.json').read_text(encoding='utf-8'))
    path = Path(receipt['points'][0]['result']).parent/'native-configuration.json'
    if not path.exists():
        pytest.skip('external historical native configuration is unavailable')
    config = json.loads(path.read_text(encoding='utf-8'))
    config['geometry_identity']['port_connection_model'] = SCHEMA
    with pytest.raises(ValueError,match='requires configuration schema V7'):
        IntegratedEngine2T.from_configuration_dict(config)
    config['base_configuration_schema']=config['schema']
    config['schema']='MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V7'
    engine = IntegratedEngine2T.from_configuration_dict(config)
    restored = IntegratedEngine2T.from_configuration_dict(engine.configuration_dict())
    assert restored.port_connection_model == SCHEMA
    assert restored.configuration_json() == engine.configuration_json()
    assert restored.configuration_dict()['schema']==config['schema']
    engine.step(1e-8,.00054)
    restored.restore(json.loads(json.dumps(engine.snapshot())))
    engine.step(1e-8,.00054)
    restored.step(1e-8,.00054)
    assert engine.snapshot()==restored.snapshot()


@pytest.mark.parametrize('commit,version',[
    ('fc27542155840cdadbcc2b591ae5cd8e99031899',7),
    ('fc27542155840cdadbcc2b591ae5cd8e99031899',8),('cd610b2',8)])
def test_frozen_reader_rejects_new_config_instead_of_ignoring_physics(tmp_path,commit,version):
    import importlib.util
    import subprocess
    import sys
    source=subprocess.run(['git','show',commit+':motorsim/integrated_2t.py'],
        check=True,capture_output=True,encoding='utf-8').stdout
    path=tmp_path/'rc7_integrated_reference.py'
    path.write_text(source,encoding='utf-8')
    name='motorsim._rc7_readonly_reference'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    try:
        spec.loader.exec_module(module)
        with pytest.raises(ValueError,match='configuration schema is invalid'):
            module.IntegratedEngine2T.from_configuration_dict({
                'schema':f'MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V{version}'})
    finally:
        del sys.modules[name]
