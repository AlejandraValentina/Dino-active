import math
from copy import deepcopy
from pathlib import Path

import pytest

from motorsim.engine_configuration import validate
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v1 import refine_exhaust_configuration as refine_v1
from motorsim.exhaust_mesh_v1 import _adapter_hash as hash_v1
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration as refine_v2
from motorsim.exhaust_mesh_v2 import _adapter_hash as hash_v2


ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/projects/dino-2t-exhaust-comparison.dino2t.json'


def source_config():
    return load_project(PROJECT)['variants']['Escape original']


def test_v2_supports_1_2_4_8_and_binds_adapter_and_exact_geometry():
    source=source_config()
    for count in (1,2,4,8):
        config=refine_v2(source,[count]*5)
        native=config['native_configuration']
        metadata=native['geometry_identity']['exhaust_mesh_discretization']
        mesh=next(path['mesh'] for path in native['ducts'] if path['id']=='exhaust')
        assert metadata['schema']=='EXHAUST_MESH_V2'
        assert metadata['adapter_sha256']==hash_v2()
        assert metadata['cells_per_section']==[count]*5
        assert len(mesh['volumes'])==count*5
        assert sum(mesh['volumes'])==pytest.approx(
            sum(math.pi*(s['length_mm']*1e-3)*(
                (s['inlet_diameter_mm']*1e-3)**2+
                (s['inlet_diameter_mm']*1e-3)*(s['outlet_diameter_mm']*1e-3)+
                (s['outlet_diameter_mm']*1e-3)**2)/12
                for s in native['geometry_identity']['chamber']['sections']),rel=2e-12)
        validate(config)


def test_v1_and_v2_artifact_identities_are_isolated_and_both_stable():
    source=source_config()
    legacy=refine_v1(source,[2]*5)
    diagnostic=refine_v2(source,[2]*5)
    assert hash_v1()=='f05940a34142a7eeec93b30a560177f909e7521c8c717ec9107ac638e2e474b2'
    assert legacy['native_configuration']['geometry_identity']['exhaust_mesh_discretization']['schema']=='EXHAUST_MESH_V1'
    assert diagnostic['native_configuration']['geometry_identity']['exhaust_mesh_discretization']['schema']=='EXHAUST_MESH_V2'
    assert legacy['native_configuration']['geometry_identity']['exhaust_mesh_discretization']['adapter_sha256']==hash_v1()
    assert diagnostic['native_configuration']['geometry_identity']['exhaust_mesh_discretization']['adapter_sha256']==hash_v2()
    with pytest.raises(ValueError,match='unsupported exhaust mesh identity'):
        refine_v1(diagnostic,[4]*5)
    with pytest.raises(ValueError,match='unsupported exhaust mesh identity'):
        refine_v2(legacy,[4]*5)
    v1_engine=validate(legacy);v2_engine=validate(diagnostic)
    with pytest.raises(ValueError,match='configuration mismatch'):
        v2_engine.restore(v1_engine.snapshot())


def test_v2_conservative_remap_preserves_species_and_is_restart_bound():
    source=source_config()
    coarse=refine_v2(source,[1]*5)
    fine=refine_v2(coarse,[8]*5)
    old=coarse['native_configuration'];new=fine['native_configuration']
    assert sum(sum(cell) for cell in old['duct_species']['exhaust'])==pytest.approx(
        sum(sum(cell) for cell in new['duct_species']['exhaust']),rel=1e-12)
    assert validate(fine).configuration_identity['configuration_sha256'] != \
           validate(coarse).configuration_identity['configuration_sha256']
