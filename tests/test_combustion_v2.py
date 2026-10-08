import copy
import math

import pytest

from motorsim.combustion import CombustionProfile, EfficiencyMap, WiebeComponent


def single(**changes):
    component = WiebeComponent(1.0, 40.0, 5.0, 2.0)
    values = dict(components=(component,), ignition_timing_deg=350.0,
                  provenance="SYNTHETIC_ASSUMPTION", efficiency=0.9)
    values.update(changes)
    return CombustionProfile(**values)


def test_single_wiebe_progress_rate_and_burn_angles():
    profile = single()
    half = profile.evaluate(370.0, rpm=6000, load=0.5)
    expected = 0.9 * (1 - math.exp(-5.0 * 0.5**3)) / (1 - math.exp(-5.0))
    assert half["burned_fraction"] == pytest.approx(expected)
    assert half["burn_rate_per_deg"] > 0
    points = profile.ca_points(rpm=6000, load=0.5)
    assert 350 < points["CA10_deg"] < points["CA50_deg"] < points["CA90_deg"] < 390
    assert profile.evaluate(points["CA50_deg"], rpm=6000, load=0.5)[
        "burned_fraction"] == pytest.approx(0.9 * 0.5)


def test_double_wiebe_is_weighted_and_has_delayed_component():
    profile = single(components=(WiebeComponent(0.7, 20.0, 5.0, 1.0),
                                WiebeComponent(0.3, 30.0, 5.0, 1.0, 30.0)))
    at_first_end = profile.evaluate(370.0, rpm=6000, load=0.5)
    assert at_first_end["burned_fraction"] == pytest.approx(0.9 * 0.7)
    final = profile.evaluate(410.0, rpm=6000, load=0.5)
    assert final["burned_fraction"] == pytest.approx(0.9)
    assert final["CA10_deg"] < final["CA50_deg"] < final["CA90_deg"]


def test_efficiency_map_is_bilinear_bounded_and_zero_is_explicit():
    efficiency_map = EfficiencyMap((4000, 8000), (0, 1), ((0.7, 0.8), (0.8, 0.9)))
    profile = single(efficiency=None, efficiency_map=efficiency_map)
    result = profile.evaluate(400.0, rpm=6000, load=0.5)
    assert result["combustion_efficiency"] == pytest.approx(0.8)
    zero = single(efficiency=0.0).evaluate(370.0, rpm=6000, load=0.5)
    assert zero["burned_fraction"] == 0.0
    assert zero["CA50_deg"] is None
    with pytest.raises(ValueError, match="outside"):
        profile.evaluate(370, rpm=9000, load=0.5)


def test_roundtrip_and_output_make_no_chemistry_or_heat_claim():
    profile = single()
    assert CombustionProfile.from_dict(profile.to_dict()) == profile
    result = profile.evaluate(370, rpm=6000, load=0.5)
    assert result["schema"] == "COMBUSTION_MODEL_V2"
    assert "heat_release_j" not in result
    assert "fuel_burned_kg" not in result
    assert "no species conversion" in result["interpretation"]
    malformed = copy.deepcopy(profile.to_dict())
    malformed["schema"] = "P7"
    with pytest.raises(ValueError):
        CombustionProfile.from_dict(malformed)


@pytest.mark.parametrize("component", [
    WiebeComponent(0, 40, 5, 1), WiebeComponent(1, 0, 5, 1),
    WiebeComponent(1, 40, 0, 1), WiebeComponent(1, 40, 5, -1),
    WiebeComponent(1, math.inf, 5, 1), WiebeComponent(True, 40, 5, 1),
])
def test_invalid_wiebe_parameters_rejected(component):
    with pytest.raises(ValueError):
        single(components=(component,)).validate()


def test_invalid_weights_efficiency_and_map_rejected():
    with pytest.raises(ValueError, match="sum to one"):
        single(components=(WiebeComponent(0.5, 40, 5, 1),)).validate()
    with pytest.raises(ValueError):
        single(efficiency=1.01).validate()
    with pytest.raises(ValueError):
        EfficiencyMap((1000, 1000), (0,), ((0.5,), (0.6,))).validate()
    with pytest.raises(ValueError):
        EfficiencyMap((1000,), (0,), ((1.1,),)).validate()
