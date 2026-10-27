import math
import pytest
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from scripts.diagnostics.pulsating_outlet_control_v1 import reversal,gaussian_average


def test_exact_gaussian_cell_average_is_additive_under_refinement():
    assert gaussian_average(.2,.4,.35)==pytest.approx((gaussian_average(.2,.3,.35)+gaussian_average(.3,.4,.35))/2,abs=1e-15)


def test_successive_reversals_use_inflow_stagnation_enthalpy():
    rows=reversal();signs={1 if r['mass_flux']>0 else -1 for r in rows if abs(r['mass_flux'])>1e-10}
    assert signs=={-1,1}
    assert max(r['inflow_enthalpy_error'] for r in rows)<1e-12
    for r in rows:
        if abs(r['mass_flux'])>1e-10:assert r['reservoir_donor']==(r['mass_flux']<0)
    assert max(abs(r['mass_flux']) for r in rows[:3])<2e-11


def test_outgoing_total_enthalpy_retains_actual_interior_temperature():
    e=IdealGas(gamma=1.4,R=1.);b=OpenEndPlenumV2Boundary(p0=1,T0=1)
    r=b.resolve((.8,.1,1.,1.),1,e);flux=e.flux(r.state)
    assert not r.reservoir_donor
    assert flux[2]/flux[0]==pytest.approx(e.cp/ .8+.5*.1**2,rel=1e-13)
