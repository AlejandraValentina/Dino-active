"""Read-only normalized per-observable trends, not a periodicity detector."""
from collections import defaultdict
import json
import numpy as np
from pathlib import Path


def group(key):
    if key.startswith('ducts.exhaust'):return 'exhaust'
    if key.startswith('ducts.'):return 'other_ducts'
    if key.startswith('global_species'):return 'global_species'
    return 'chambers_and_integrals'


def analyze(cycles):
    rows=[]
    for c in cycles:
        lags={}
        for lag,comparison in [('lag1',c['comparison']),('lag2',c['detector_outcome']['outcomes'].get('lag2',{}))]:
            buckets=defaultdict(list)
            for key,v in comparison.get('metrics',{}).items():
                ratio=v['value']/v['threshold'];buckets[group(key)].append(ratio);buckets['all'].append(ratio)
            lags[lag]={k:dict(median=float(np.median(v)),p90=float(np.quantile(v,.9)),p99=float(np.quantile(v,.99)),maximum=max(v),rms=float(np.sqrt(np.mean(np.array(v)**2))),failed=sum(x>1 for x in v),count=len(v)) for k,v in buckets.items()}
        rows.append(dict(cycle=c['cycle'],work_J=c['cylinder_work_J'],lags=lags))
    trends=[]
    for key,last in cycles[-1]['comparison']['metrics'].items():
        samples=[(c['cycle'],c['comparison']['metrics'][key]['value']/last['threshold']) for c in cycles if key in c['comparison']['metrics']]
        recent=samples[-4:];slope=float(np.polyfit([x[0] for x in recent],[x[1] for x in recent],1)[0])
        # Descriptive 5% change band, not a solver acceptance threshold.
        change=(recent[-1][1]-recent[0][1])/max(recent[0][1],1.)
        label='improving' if change<-.05 else 'worsening' if change>.05 else 'stable'
        trends.append(dict(observable=key,group=group(key),last_ratio=samples[-1][1],failed=not last['passed'],recent_slope_per_cycle=slope,recent_relative_change=change,trend=label,history=samples))
    return dict(schema='DINO_PERIODICITY_TRENDS_V1',cycles=rows,observables=trends,
        qualification='Magnitude/threshold ratios and descriptive trends; not a replacement detector or extrapolation to periodicity.')
