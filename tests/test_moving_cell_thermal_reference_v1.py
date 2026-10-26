"""Independent extensive first-law reference for heat at a moving reed cell."""
from copy import deepcopy

import pytest

from motorsim.gas1d.mesh import uniform_mesh
from motorsim.integrated_2t import DynamicReedBinding2T
from motorsim.reed import ReedPetal, ReedState
from motorsim.reed_coupling import HingedFlapGeometryV1
from motorsim.thermal import ThermalSurface, ThermalSystem
from test_integrated_2t import _case


def thermal_case(lift,wall_temperature,with_heat=True):
    mesh=uniform_mesh(2,.02,1e-4)
    petal=ReedPetal('heat-reference',.001,.0001,.01,10.,.01,.002,.8,
                    'SYNTHETIC_ASSUMPTION')
    geometry=HingedFlapGeometryV1('heat-reference','1','SYNTHETIC_ASSUMPTION',
                                .01,.02,mesh.volumes[-1],.00015,.002,.8)
    binding=DynamicReedBinding2T('intake',geometry,petal,ReedState(lift,0.))
    wall=ThermalSurface('moving-wall','transfer_walls',.001,50.,
                        'SYNTHETIC_ASSUMPTION',wall_temperature)
    return _case(crankcase_pressure=101325.,cylinder_pressure=101325.,
        duct_pressure=101325.,intake_area=1e-5,transfer_area=0.,exhaust_area=0.,
        dynamic_reed_binding=binding,
        thermal_system=ThermalSystem((wall,)) if with_heat else None,
        thermal_locations={'moving-wall':'intake:1'} if with_heat else None)


@pytest.mark.parametrize('lift',[0.,.0005,.0015])
@pytest.mark.parametrize('wall_temperature',[250.,400.])
def test_actual_extensive_source_equals_negative_newton_heat_at_every_lift(lift,wall_temperature):
    hot,cold=thermal_case(lift,wall_temperature),thermal_case(lift,wall_temperature,False)
    # This state comparison excludes heat from every other mechanical term.
    assert hot.state==cold.state
    a=hot._assemble(hot.state,0.,10000.)
    b=cold._assemble(cold.state,0.,10000.)
    path=next(p for p in hot.ducts if p.id=='intake')
    q=hot.state['ducts']['intake'][1]
    rho,u,p,_=hot._primitive(q)
    gas_temperature=p/(rho*hot.eos.R)
    expected_heat=50.*.001*(gas_temperature-wall_temperature)
    # V = V0 + swept_area*lift, independently of the source implementation.
    volume=path.mesh.volumes[1]+hot.dynamic_reed_binding.geometry.swept_volume_area_m2*lift
    actual=(a['q']['ducts']['intake'][1][2]-b['q']['ducts']['intake'][1][2])*volume
    assert a['thermal_rates']['moving-wall']==pytest.approx(expected_heat,rel=1e-14)
    assert actual==pytest.approx(-expected_heat,rel=1e-10,abs=1e-12)
    assert (a['dynamic_duct_cell']['extensive_rate'][2]-
            b['dynamic_duct_cell']['extensive_rate'][2])==pytest.approx(-expected_heat,rel=1e-10,abs=1e-12)


@pytest.mark.parametrize('wall_temperature',[250.,400.])
def test_ssprk_heat_ledger_conservation_and_checkpoint_restart(wall_temperature):
    a,b=thermal_case(.001,wall_temperature),thermal_case(.001,wall_temperature)
    for _ in range(4):a.step(1e-7,.0006)
    report=a.conservation_report()
    assert abs(report['energy']['residual'])<2e-11
    assert abs(report['mass']['residual'])<1e-14
    assert max(abs(s['residual']) for s in report['species'].values())<1e-14
    b.restore(deepcopy(a.snapshot()))
    a.step(1e-7,.0006);b.step(1e-7,.0006)
    assert a.snapshot()==b.snapshot()


def test_static_case_native_checkpoint_retains_configuration_compatibility():
    import json
    from pathlib import Path
    from motorsim.integrated_2t import IntegratedEngine2T
    root=Path('results/predictive-reliability-v1/spatial-muscl-coarse')
    config=json.loads((root/'configuration.json').read_text(encoding='utf-8'))
    checkpoint=json.loads((root/'terminal-checkpoint.json').read_text(encoding='utf-8'))
    engine=IntegratedEngine2T.from_configuration_dict(config)
    engine.restore(checkpoint)
    assert engine.snapshot()==checkpoint
