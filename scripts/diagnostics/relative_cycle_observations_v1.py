"""Separate absolute physical clock from a new diagnostic's cycle counter."""
from scripts.diagnostics.checkpoint_periodicity_indicators_v1 import cycle_observations


def relative_observations(engine,start,end,origin_cycle):
    absolute=end.get('cycle')
    if type(origin_cycle) is not int or origin_cycle<0 or type(absolute) is not int or absolute<=origin_cycle:
        raise ValueError('invalid relative cycle origin')
    record=cycle_observations(engine,start,end,absolute)
    local=absolute-origin_cycle
    record['cycle_index']=local
    provenance=dict(absolute_cycle_index=absolute,detector_cycle_index=local,
        origin_absolute_cycle=origin_cycle,start_crank_angle_deg=start['crank_angle_unwrapped_deg'],
        end_crank_angle_deg=end['crank_angle_unwrapped_deg'],
        qualification='Only the new detector counter is relative; physical state, events, clocks, observables and configuration identity are unchanged.')
    return record,provenance
