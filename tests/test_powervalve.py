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
