import math

import pytest

from motorsim.crankcase import CrankcaseGeometry, crankcase_link_flux


def geometry(**changes):
    values = dict(bore_mm=50.0, stroke_mm=50.0, rod_length_mm=100.0,
                  volume_bdc_cm3=250.0, provenance="SYNTHETIC_ASSUMPTION")
    values.update(changes)
    return CrankcaseGeometry(**values)


def test_crankcase_volumes_compression_ratio_and_cycle_endpoints():
    case = geometry()
    swept = math.pi * 0.05**2 * 0.05 / 4
    assert case.displacement_m3 == pytest.approx(swept)
    assert case.volume_m3(0.0) == pytest.approx(case.volume_tdc_m3)
    assert case.volume_m3(180.0) == pytest.approx(case.volume_bdc_m3)
    assert case.volume_m3(360.0) == pytest.approx(case.volume_tdc_m3)
    assert case.compression_ratio == pytest.approx((250.0 + swept * 1e6) / 250.0)
    assert case.volume_rate_m3_s(0, 6000) == pytest.approx(0.0, abs=1e-15)
    assert case.volume_rate_m3_s(180, 6000) == pytest.approx(0.0, abs=1e-15)


def test_crankcase_volume_rate_matches_finite_difference():
    case = geometry()
    rpm, angle, epsilon = 6000.0, 83.0, 1e-4
    seconds_per_degree = 1 / (6 * rpm)
    before = case.volume_m3(angle - epsilon)
    after = case.volume_m3(angle + epsilon)
    finite_difference = (after - before) / (2 * epsilon * seconds_per_degree)
    assert case.volume_rate_m3_s(angle, rpm) == pytest.approx(finite_difference, rel=1e-6)


def test_geometry_restart_roundtrip_and_bad_dimensions():
    case = geometry()
    assert CrankcaseGeometry.from_dict(case.to_dict()) == case
    with pytest.raises(ValueError):
        geometry(rod_length_mm=25).validate()
    with pytest.raises(ValueError):
        geometry(volume_bdc_cm3=0).validate()
    with pytest.raises(ValueError):
        geometry(stroke_mm=True).validate()


def test_bidirectional_links_use_resolved_donor_composition():
    high = (150_000.0, 300.0, 0.8)
    low = (100_000.0, 300.0, 0.1)
    outward = crankcase_link_flux(high, low, 1e-5, discharge_coefficient=0.7)
    inward = crankcase_link_flux(low, high, 1e-5, discharge_coefficient=0.7)
    assert outward[0] > 0 and outward[2] > 0
    assert inward[0] < 0 and inward[2] < 0
    assert crankcase_link_flux(high, low, 0.0, discharge_coefficient=0.7) == (0, 0, 0)


@pytest.mark.parametrize("left,right,area,cd", [
    ((1e5, 300, 0.5), (1e5, 300, 0.5), True, 0.7),
    ((1e5, 300, 0.5), (1e5, 300, 0.5), -1e-4, 0.7),
    ((1e5, 300, 0.5), (1e5, 300, 0.5), 1e-4, 1.1),
    ((1e5, math.nan, 0.5), (1e5, 300, 0.5), 1e-4, 0.7),
])
def test_invalid_link_data_rejected(left, right, area, cd):
    with pytest.raises(ValueError):
        crankcase_link_flux(left, right, area, discharge_coefficient=cd)
