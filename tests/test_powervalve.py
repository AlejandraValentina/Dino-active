import math

import pytest

from motorsim.powervalve import PowerValve
from motorsim.two_stroke_ports import DuctBinding, PortDefinition, TwoStrokePortSet


def main_port(**changes):
    values = dict(id="main-exhaust", name="Escape principal", role="exhaust",
                  feature="main", duct_id="exhaust", family="rectangular_window",
                  discharge_coefficient=0.8, provenance="SYNTHETIC_ASSUMPTION",
                  top_mm=25.0, height_mm=15.0, width_mm=30.0,
                  roof_travel_mm=5.0, roof_position=0.0)
    values.update(changes)
    return PortDefinition(**values)


def setup():
    ports = TwoStrokePortSet(50.0, 100.0,
        (DuctBinding("exhaust", "exhaust"),), (main_port(),))
    valve = PowerValve("pv1", "main-exhaust", (2000.0, 6000.0),
                       (0.0, 1.0), "SYNTHETIC_ASSUMPTION")
    return ports, valve


def test_continuous_rpm_interpolation_and_effective_port_area():
    ports, valve = setup()
    assert valve.at(2000) == 0.0
    assert valve.at(4000) == pytest.approx(0.5)
    assert valve.at(6000) == 1.0
    open_port = valve.apply(ports.ports[0], 2000)
    closed_port = valve.apply(ports.ports[0], 6000)
    assert open_port.roof_position == 0.0
    assert closed_port.roof_position == 1.0
    open_events = ports.event_angles(open_port)
    closed_events = ports.event_angles(closed_port)
    assert open_events[1] != closed_events[1]
    areas_open = [valve.area_at(ports, 2000, angle) for angle in range(361)]
    areas_closed = [valve.area_at(ports, 6000, angle) for angle in range(361)]
    assert sum(areas_closed) < sum(areas_open)
    assert all(closed <= opened for closed, opened in zip(areas_closed, areas_open))


@pytest.mark.parametrize("rpm", [2000.0, 4000.0, 6000.0])
def test_effective_area_matches_independent_slider_crank_window_reference(rpm):
    """Check the movable-roof area against a separately evaluated analytic reference.

    This guards area units, clipping at opening/closing, and the RPM-to-roof
    interpolation without calling either production area helper for expected values.
    """
    ports, valve = setup()
    port = ports.ports[0]
    roof_position = 0.0 if rpm == 2000.0 else 0.5 if rpm == 4000.0 else 1.0
    top = port.top_mm + port.roof_travel_mm * roof_position
    radius = ports.stroke_mm / 2.0
    angles = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 360.0)

    for angle_deg in angles:
        theta = math.radians(angle_deg % 360.0)
        piston_from_tdc_mm = (
            radius * (1.0 - math.cos(theta))
            + ports.rod_length_mm
            - math.sqrt(ports.rod_length_mm**2 - radius**2 * math.sin(theta)**2)
        )
        exposed_height_mm = max(0.0, min(
            port.height_mm, piston_from_tdc_mm - top))
        expected_area_mm2 = (
            port.discharge_coefficient * port.width_mm * exposed_height_mm)
        actual_area_mm2 = valve.area_at(ports, rpm, angle_deg)
        assert actual_area_mm2 == pytest.approx(expected_area_mm2, rel=1e-13, abs=1e-13)


def test_effective_area_opens_closes_and_is_bounded_by_independent_window_geometry():
    ports, valve = setup()
    port = ports.ports[0]
    for rpm in (2000.0, 3000.0, 4000.0, 6000.0):
        samples = [valve.area_at(ports, rpm, angle) for angle in range(361)]
        maximum = port.discharge_coefficient * port.width_mm * port.height_mm
        assert samples[0] == samples[-1] == 0.0
        assert min(samples) >= 0.0
        assert max(samples) <= maximum + 1e-12
        assert max(samples) == pytest.approx(maximum)
        assert samples[90] <= samples[120] <= samples[180]
        assert samples[270] <= samples[240] <= samples[180]


def test_roundtrip_and_rpm_range_rejection():
    _, valve = setup()
    assert PowerValve.from_dict(valve.to_dict()) == valve
    with pytest.raises(ValueError, match="outside"):
        valve.at(7000)
    with pytest.raises(ValueError):
        valve.at(math.nan)


def test_only_configured_movable_main_exhaust_can_be_controlled():
    _, valve = setup()
    with pytest.raises(ValueError, match="configured movable-roof"):
        valve.apply(main_port(id="aux"), 3000)
    with pytest.raises(ValueError, match="movable-roof"):
        valve.apply(main_port(roof_travel_mm=0.0), 3000)
    with pytest.raises(ValueError):
        valve.area_at(TwoStrokePortSet(50, 100, (), ()), 3000, 180)


@pytest.mark.parametrize("rpm,position", [
    ((2000, 2000), (0, 1)), ((2000,), (1.1,)),
    ((True,), (0.5,)), ((2000,), (math.nan,)),
])
def test_invalid_maps_rejected(rpm, position):
    valve = PowerValve("pv", "main", rpm, position, "DOCUMENTED")
    with pytest.raises(ValueError):
        valve.validate()
