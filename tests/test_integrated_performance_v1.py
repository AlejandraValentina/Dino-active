"""Focused safeguards for stage-local thermal evaluation, not a new model."""
import math

import pytest

from motorsim.integrated_2t import _thermal_heat_rate_v2 as validated_surface_heat_rate
from motorsim.thermal import ThermalSurface, ThermalSystem, WallTemperatureMap
from test_integrated_2t import _case


def surface(**kwargs):
    return ThermalSurface('wall', 'cylinder_wall', .008902016943212037, 500.,
                          'SYNTHETIC_ASSUMPTION', **kwargs)


@pytest.mark.parametrize('temperature', [1., 290., 473., 850., 2200.])
def test_same_float_fixed_heat(temperature):
    s = surface(wall_temperature_K=473.)
    system = ThermalSystem((s,))
    system.validate()
    assert validated_surface_heat_rate(s, temperature, 9000., 1.) == system.heat_rate_w(s.id, temperature, 9000., 1.)


def test_same_float_mapped_heat_and_domain_guard():
    mapping = WallTemperatureMap((8000.,10000.),(0.,1.),((350.,420.),(400.,500.)))
    s = surface(wall_map=mapping)
    system = ThermalSystem((s,))
    system.validate()
    assert validated_surface_heat_rate(s, 777., 9000., .5) == system.heat_rate_w(s.id,777.,9000.,.5)
    with pytest.raises(ValueError,match='outside'):
        validated_surface_heat_rate(s,777.,12000.,.5)


@pytest.mark.parametrize('temperature', [0., -1., math.nan, math.inf, True])
def test_invalid_gas_temperature_rejected(temperature):
    with pytest.raises(ValueError):
        validated_surface_heat_rate(surface(wall_temperature_K=473.),temperature,9000.,1.)


def test_all_surfaces_validated_once_each_stage(monkeypatch):
    surfaces = tuple(ThermalSurface(str(i),'cylinder_wall',.00001,100.,
        'SYNTHETIC_ASSUMPTION',wall_temperature_K=290.) for i in range(4))
    thermal = ThermalSystem(surfaces)
    engine = _case(thermal_system=thermal,thermal_locations={s.id:'cylinder' for s in surfaces})
    calls = []
    original = ThermalSystem.validate
    def observed(self):
        calls.append(self)
        return original(self)
    monkeypatch.setattr(ThermalSystem,'validate',observed)
    engine.step(1e-8,.01)
    assert len(calls) == 2
    assert abs(engine.conservation_report()['energy']['residual']) < 1e-10


def test_invalid_surface_mutation_remains_fail_closed():
    s = surface(wall_temperature_K=473.)
    thermal = ThermalSystem((s,))
    engine = _case(thermal_system=thermal,thermal_locations={s.id:'cylinder'})
    from copy import deepcopy
    before = deepcopy(engine.state)
    object.__setattr__(s,'area_m2',-1.)
    with pytest.raises(ValueError):
        engine.step(1e-8,.01)
    assert engine.state == before
    assert engine.accepted_steps == 0


def test_overridden_system_heat_law_keeps_legacy_entry_point():
    class CustomThermal(ThermalSystem):
        def heat_rate_w(self,*args):
            return 0.
    s = surface(wall_temperature_K=290.)
    thermal = CustomThermal((s,))
    engine = _case(thermal_system=thermal,thermal_locations={s.id:'cylinder'})
    assert engine.step(1e-8,.01)['heat_to_wall_J'] == 0.
