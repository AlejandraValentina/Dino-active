import pytest
from scripts.diagnostics.analyze_periodic88_pilot_v1 import phase_frames


def test_same_phase_uses_accepted_state_not_runge_kutta_predictor():
    primary=dict(cycle_start_deg=10440.,start_state={'marker':0},trajectory=[dict(angle_end_deg=10440.+p,stage_states=[{}, {'wrong_predictor':True},{'marker':p}]) for p in range(30,361,30)])
    frames=phase_frames(primary)
    assert frames[0]==dict(phase=0.,state={'marker':0})
    assert frames[-1]==dict(phase=360.,state={'marker':360})
    assert all('wrong_predictor' not in f['state'] for f in frames)


def test_missing_phase_is_rejected_not_interpolated():
    primary=dict(cycle_start_deg=0.,start_state={},trajectory=[])
    with pytest.raises(ValueError,match='incomplete'):phase_frames(primary)


def test_join_rejects_noncontiguous_segment(monkeypatch,tmp_path):
    from scripts.diagnostics import analyze_periodic88_pilot_v1 as module
    def load(path):
        if path.name=='configuration.json':return {'same':'config'}
        if path.name=='receipt.json':return {'status':'TRANSIENT_AT_BUDGET'}
        if path.name=='cycles.json':return [{'cycle':2,'absolute_cycle':32}]
        raise AssertionError(path)
    monkeypatch.setattr(module,'load',load)
    with pytest.raises(ValueError,match='cycle continuity'):module.joined_cycles(tmp_path,[])
