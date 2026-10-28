"""Frozen E2A inputs remain physical controls; these tests take no solver steps."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.gas1d.spatial_reconstruction_v2 import SCHEMA
from scripts.diagnostics.e2_spatial_waves_v1 import lag, overlap_weights
from test_e2a_exhaust_waves_v1 import (
    test_positive_lag_means_later_b_and_is_offset_invariant,
    test_flat_signal_cannot_define_wave_phase,
    test_physical_sensor_weights_conserve_a_constant_field_on_both_grids,
    test_exact_overlap_integrates_variable_frustum_area,
)


@pytest.mark.parametrize('name',['A44','B44','A88','B88'])
def test_only_explicit_spatial_capability_changes(name):
    root=Path('results')
    old=json.loads((root/'e2a-exhaust-waves-v1/preparation'/f'{name}.json').read_text())
    new=json.loads((root/'e2-spatial-waves-v1/preparation'/f'{name}.json').read_text())
    assert new['geometry_identity']['spatial_reconstruction_model']==SCHEMA
    e=IntegratedEngine2T.from_configuration_dict(new)
    assert e.configuration_dict()==new
    stripped=deepcopy(new);stripped['schema']=old['schema']
    del stripped['geometry_identity']['spatial_reconstruction_model']
    assert stripped==old
    prior=IntegratedEngine2T.from_configuration_dict(old)
    assert e.state==prior.state
    assert e.inventory()==prior.inventory()
