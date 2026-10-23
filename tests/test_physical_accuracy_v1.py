"""L0 arithmetic and provenance checks for an offline assessment, no solver."""
import json
from pathlib import Path

import pytest

from scripts.diagnostics.physical_accuracy_v1 import analyze, sampled_pdv


@pytest.fixture
def balance():
    return json.loads((Path(__file__).resolve().parents[1]/'results/physical-accuracy-v1/balance.json').read_text())


def test_scope_and_no_validation_claim(balance):
    assert len(balance['points']) == 6
    assert balance['solver_steps_executed'] == 0
    assert balance['reference_run_executed'] is False


def test_two_stroke_work_and_mep(balance):
    for p in balance['points']:
        brake_work = p['brake_W']*60/p['rpm']
        assert brake_work == pytest.approx(p['cylinder_work_J']+p['crankcase_work_J']-p['friction_work_J'])
        assert p['imep_bar']-p['net_piston_mep_bar'] == pytest.approx(-p['crankcase_work_J']/0.00012462823720496853/1e5)
        assert p['net_piston_mep_bar']-p['bmep_bar'] == pytest.approx(.85)


def test_dry_air_normalization(balance):
    for p in balance['points']:
        assert p['dry_air_delivery_ratio_gross'] == pytest.approx(p['gross_intake_air_mg']/p['reference_dry_air_mg'])
        assert p['charging_efficiency_dry_air'] == pytest.approx(p['trapped_air_mg']/p['reference_dry_air_mg'])
        assert p['net_intake_air_mg'] == pytest.approx(p['gross_intake_air_mg']-p['reverse_intake_air_mg'])


def test_oxygen_and_heat(balance):
    for p in balance['points']:
        assert p['fuel_burned_mg'] <= p['oxygen_limited_fuel_mg']
        assert p['heat_released_J'] == pytest.approx(p['fuel_burned_mg']*1e-6*43e6*.85)
        assert p['afr_trapped'] == pytest.approx(p['trapped_air_mg']/p['trapped_fuel_mg'])


def test_energy_and_audit_qualification(balance):
    for p in balance['points']:
        assert abs(p['energy_balance_residual_J']) < 1e-8
        assert p['independent_audit'] == 'NOT_PERFORMED'
        assert p['burned_residual_fraction'] > .5


def test_reject_modified_source_hash(tmp_path):
    r = tmp_path/'receipt.json'
    r.write_text(json.dumps({'source_hashes':{'motorsim.thermal':'0'*64},'points':[]}))
    with pytest.raises(ValueError,match='source hash mismatch'):
        analyze(r)


def test_constant_pressure_pdv_is_zero():
    native={'slider_crank':{'crankcase':{'stroke_mm':50.6,'rod_length_mm':110.,'bore_mm':56.}}}
    samples=[{'angle_deg':a,'pressures_Pa':{'cylinder':101325.},'areas_m2':{'exhaust':0.}} for a in range(361)]
    p = sampled_pdv(samples,native)
    assert p['total_J'] == pytest.approx(0.,abs=1e-12)
    assert p['exhaust_open_J'] == 0.
