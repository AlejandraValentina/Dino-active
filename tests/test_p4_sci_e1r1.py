import json
from pathlib import Path
from motorsim.periodicity import PeriodicityDetector

def test_detector_live_update_and_json_bools():
    d=PeriodicityDetector(1, {'A':'odd','B':'even'})
    row={'cycle':1,'configuration_hash':'x','scientific_contract_id':'E13-R1','solver':'s','backend':'b','mesh':1,'geometry':'g','rpm':1,'operating_point':'o','cycle_convention':'360','anchor_cycle':1,'branch_map':{'A':'odd','B':'even'}}
    for _ in range(3): d.update(row,lag1={'passed':True},lag2={'passed':False},branch='A')
    assert d.lag1_streak == 3 and d.detected_period == 1
    assert isinstance(d.to_json()['detected_period'], int)

def test_optional_steps_are_unavailable_not_required():
    counts={'rhs':3,'HLLC':2,'HLLE':0,'rejected':0}
    telemetry={'cycle':1,'counts':counts}
    assert telemetry['counts'].get('steps') is None

def test_missing_lag_is_invalid_not_fail():
    d=PeriodicityDetector(1)
    row={'cycle':1,'configuration_hash':'x','scientific_contract_id':'E13-R1','solver':'s','backend':'b','mesh':1,'geometry':'g','rpm':1,'operating_point':'o','cycle_convention':'360','anchor_cycle':1,'branch_map':{'A':'A','B':'B'}}
    r=d.update(row,branch='A')
    assert r['status']=='INVALID' and r['reason']=='MISSING_LAG1'

def test_checkpoint_write_order_uses_terminal_state():
    text=Path('dev_orchestrator/p4_sci_e1r1_runner.py').read_text()
    assert text.index('terminal_state, terminal_pipe') < text.index('save_restart(terminal_state')
