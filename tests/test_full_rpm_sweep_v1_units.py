import pytest

from scripts.correct_full_rpm_sweep_v1_units_v2 import (
    correct_point_units,
    kw_to_w,
    power_w_from_torque,
    w_to_kw,
)


@pytest.mark.parametrize("power_kw", [-0.003932550795849058, 0.1537797278319094])
def test_watt_kilowatt_conversion_round_trip(power_kw):
    power_w = kw_to_w(power_kw)
    assert power_w == pytest.approx(power_kw * 1000.0, rel=0.0, abs=1e-12)
    assert w_to_kw(power_w) == pytest.approx(power_kw, rel=0.0, abs=1e-15)


@pytest.mark.parametrize(
    "power_kw,torque_nm",
    [(-0.003932550795849058, -0.009388273471790168),
     (0.1537797278319094, 0.3671220574766204)],
)
def test_brake_power_matches_torque_identity(power_kw, torque_nm):
    power_w = kw_to_w(power_kw)
    assert power_w == pytest.approx(
        power_w_from_torque(torque_nm, 4000.0), rel=2e-10, abs=1e-10)


def test_report_v2_names_converted_power_and_torque_units_explicitly():
    row = {
        "variant_id": "B_PRIME_MESH_0", "rpm": 4000,
        "brake_power": 0.1537797278319094,
        "brake_power_status": "DEFINED",
        "brake_torque": 0.3671220574766204,
        "brake_torque_status": "DEFINED",
        "BMEP": 18.730717218194922, "BMEP_status": "DEFINED",
    }
    corrected = correct_point_units(row)
    assert "brake_power" not in corrected
    assert corrected["brake_power_kW"] == row["brake_power"]
    assert corrected["brake_power_W"] == pytest.approx(153.7797278319094)
    assert corrected["brake_torque_Nm"] == row["brake_torque"]
    assert corrected["BMEP_kPa"] == row["BMEP"]


def test_power_identity_rejects_invalid_rpm():
    with pytest.raises(ValueError, match="RPM positive"):
        power_w_from_torque(1.0, 0.0)
