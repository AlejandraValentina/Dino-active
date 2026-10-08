import copy
import math

import pytest

from motorsim.thermal import ThermalSurface, ThermalSystem, WallTemperatureMap


def system_with_map():
    wall_map = WallTemperatureMap(
        rpm=(1000.0, 2000.0), load=(0.0, 1.0),
        temperature_K=((300.0, 400.0), (500.0, 600.0)),
    )
    return ThermalSystem((
        ThermalSurface("cylinder", "cylinder_wall", 2.0, 10.0,
                       "SYNTHETIC_ASSUMPTION", wall_map=wall_map),
        ThermalSurface("head", "cylinder_head", 0.01, 2.0,
                       "DOCUMENTED", wall_temperature_K=300.0),
    ))


def test_wall_map_bilinear_interpolation_and_no_extrapolation():
    wall_map = system_with_map().surfaces[0].wall_map
    assert wall_map.at(1500.0, 0.5) == pytest.approx(450.0)
    assert wall_map.at(1000.0, 0.0) == 300.0
    with pytest.raises(ValueError, match="outside"):
        wall_map.at(2500.0, 0.5)


def test_constant_h_per_cycle_energy_ledger_and_signed_heat():
    system = ThermalSystem((
        ThermalSurface("cylinder", "cylinder_wall", 2.0, 10.0,
                       "SYNTHETIC_ASSUMPTION", wall_temperature_K=300.0),
        ThermalSurface("head", "cylinder_head", 0.01, 2.0,
                       "DOCUMENTED", wall_temperature_K=300.0),
    ))
    result = system.cycle_ledger((
        {"angle_deg": 0.0, "gas_temperature_K": {"cylinder": 400.0, "head": 200.0}},
        {"angle_deg": 360.0, "gas_temperature_K": {"cylinder": 400.0, "head": 200.0}},
    ), rpm=60.0, load=0.5)
    assert result["heat_to_wall_j_by_surface"]["cylinder"] == pytest.approx(2000.0)
    assert result["heat_to_wall_j_by_surface"]["head"] == pytest.approx(-2.0)
    assert result["heat_to_wall_total_j"] == pytest.approx(1998.0)
    assert result["gas_heat_loss_j"] == result["heat_to_wall_total_j"]


def test_config_roundtrip_preserves_maps_and_explicit_coefficients():
    system = system_with_map()
    restored = ThermalSystem.from_dict(system.to_dict())
    assert restored == system
    bad = copy.deepcopy(system.to_dict())
    bad["correlation"] = "HIDDEN_FIT"
    with pytest.raises(ValueError):
        ThermalSystem.from_dict(bad)


@pytest.mark.parametrize("change", [
    lambda data: data.update(area_m2=True),
    lambda data: data.update(heat_transfer_w_m2k=-1.0),
    lambda data: data.update(wall_temperature_K=math.nan),
    lambda data: data.update(provenance="MEASURED"),
])
def test_invalid_surface_values_are_rejected(change):
    data = ThermalSurface("x", "crankcase", 1.0, 1.0,
                          "DOCUMENTED", wall_temperature_K=300.0).to_dict()
    change(data)
    with pytest.raises(ValueError):
        ThermalSurface.from_dict(data)


def test_cycle_requires_complete_ordered_full_span_samples():
    system = system_with_map()
    valid = {"cylinder": 400.0, "head": 400.0}
    with pytest.raises(ValueError, match="increase strictly"):
        system.cycle_ledger(({"angle_deg": 0, "gas_temperature_K": valid},
                             {"angle_deg": 0, "gas_temperature_K": valid}),
                            rpm=1000, load=0.5)
    with pytest.raises(ValueError, match="exactly one"):
        system.cycle_ledger(({"angle_deg": 0, "gas_temperature_K": valid},
                             {"angle_deg": 359, "gas_temperature_K": valid}),
                            rpm=1000, load=0.5)
    incomplete = {"cylinder": 400.0}
    with pytest.raises(ValueError, match="every configured"):
        system.cycle_ledger(({"angle_deg": 0, "gas_temperature_K": incomplete},
                             {"angle_deg": 360, "gas_temperature_K": incomplete}),
                            rpm=1000, load=0.5)


def test_cycle_rejects_nonfinite_and_map_axis_reversals():
    system = system_with_map()
    valid = {"cylinder": 400.0, "head": 400.0}
    with pytest.raises(ValueError):
        system.cycle_ledger(({"angle_deg": 0, "gas_temperature_K": valid},
                             {"angle_deg": math.inf, "gas_temperature_K": valid}),
                            rpm=1000, load=0.5)
    with pytest.raises(ValueError, match="increase strictly"):
        WallTemperatureMap((1000, 1000), (0,), ((300,), (400,))).validate()
