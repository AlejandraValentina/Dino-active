import copy
from motorsim.periodicity import PeriodicityDetector, compare_cycles


def _row(cycle, ident='x'):
    h=[{'angle':0.,'p_cyl':1.,'sensors_p_u_M_Y':[[1.],[1.],[1.]]},
       {'angle':360.,'p_cyl':1.,'sensors_p_u_M_Y':[[1.],[1.],[1.]]}]
    return dict(cycle=cycle, begin=0., history=h, state=[1.]*9,
                cells=[[1.,1.,1.,1.]], work_indicated_J=1.,
                port_integral=[1.], initial_cylinder_mass=1.,
                configuration_hash=ident, scientific_contract_id='e13', solver='s',
                backend='b', mesh='m', geometry='g', rpm=1, operating_point='o',
                cycle_convention='c', anchor_cycle=50, branch_map={'A':'A','B':'B'})


def test_period1_precedence_and_three_passes():
    d=PeriodicityDetector(50)
    r=_row(51)
    for _ in range(3): assert d.update(r, lag1={'passed':True})['passed']
    assert d.detected_period == 1


def test_period2_independent_branches_and_invalid_reset():
    d=PeriodicityDetector(50)
    for _ in range(3): d.update(_row(52), lag1={'passed':False}, lag2={'passed':True}, branch='A')
    assert d.branch_A_streak == 3 and d.branch_B_streak == 0
    d.update(_row(54), lag1={'passed':False}, lag2={'status':'INVALID','passed':False}, branch='A')
    assert d.branch_A_streak == 0 and d.branch_B_streak == 0


def test_identity_mismatch_is_invalid():
    d=PeriodicityDetector(50)
    d.update(_row(51), lag1={'passed':True})
    bad=_row(52, 'other')
    assert d.update(bad, lag1={'passed':True})['status'] == 'INVALID'


def test_compare_cycles_contract_vector():
    a,b=_row(1),_row(2)
    m=compare_cycles(a,b)
    assert m['passed'] is True and m['sensor_max'] == 0


def test_restart_state_json_roundtrip():
    d=PeriodicityDetector(50, {'A':'first','B':'second'})
    d.lag1_streak=2; d.branch_A_streak=1
    restored=PeriodicityDetector.from_json(d.to_json())
    assert restored.to_json() == d.to_json()
