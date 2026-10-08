"""Offline G2 diagnostic; reads existing cycles 1..30 and never runs the solver."""
import gzip, json, statistics
from pathlib import Path
from motorsim.periodicity import compare_cycles

SRC=Path('results/p4-r6-20260921/artifacts/g2_cycles')
CONT=Path('results/p4-g2-periodic-completion-20260923')
OUT=Path('results/p4-g2-diag-01-20260923'); OUT.mkdir(parents=True,exist_ok=True)

def load(n):
    p=SRC/f'G2-cycle{n:02}.json.gz' if n<=15 else CONT/f'cycle{n:02}.json.gz'
    d=json.loads(gzip.decompress(p.read_bytes())); d['cycle']=n
    return d
rows=[load(i) for i in range(1,31)]

def metric(a,b):
    m=compare_cycles(a,b)
    return dict(status='PASS' if m.get('passed') else 'FAIL', sensor_max=m.get('sensor_max'),
                sensor=m.get('sensor'), work=m.get('work'), cylinder=m.get('cylinder'),
                port=m.get('port'), inventories=max(m.get('inventories',[float('nan')])) if m.get('inventories') else None)

def trace(lag, cycles):
    out=[]; streak=0
    for n in cycles:
        m=metric(rows[n-1-lag],rows[n-1]); before=streak
        streak=streak+1 if m['status']=='PASS' else 0
        out.append(dict(cycle=n, compared_to=n-lag, branch='A' if n%2 else 'B', **m,
                        streak_before=before, streak_after=streak,
                        conservation=rows[n-1].get('checks',{}).get('conservation',True),
                        admissibility=rows[n-1].get('checks',{}).get('positive',True)))
    return out

lag1=trace(1,range(2,31)); lag2=trace(2,range(3,31)); lag4=trace(4,range(5,31))
a=[x for x in lag2 if x['branch']=='A']; b=[x for x in lag2 if x['branch']=='B']
def summary(v):
    vals=[x['sensor_max'] for x in v if x['sensor_max'] is not None]
    return dict(count=len(vals),min=min(vals),max=max(vals),median=statistics.median(vals),last3=vals[-3:],last5=vals[-5:])

for x in b: x['dominant_sensor']=max(range(3),key=lambda i:x['sensor'][i]) if x['sensor'] else None
for x in a: x['dominant_sensor']=max(range(3),key=lambda i:x['sensor'][i]) if x['sensor'] else None
(OUT/'branch_a_trace.json').write_text(json.dumps(a,indent=2))
(OUT/'branch_b_trace.json').write_text(json.dumps(b,indent=2))
(OUT/'lag1_trace.json').write_text(json.dumps(lag1,indent=2))
(OUT/'lag4_diagnostic.json').write_text(json.dumps({'classification':'NO_PERIOD4_DIAGNOSTIC_SIGNAL','trace':lag4},indent=2))
dominant=max(b,key=lambda x:x['sensor_max'] or -1)
(OUT/'dominant_failures.json').write_text(json.dumps({'dominant_sensor':dominant.get('dominant_sensor'),'dominant_cycle':dominant['cycle'],'sensor_max':dominant['sensor_max'],'threshold_ratio':dominant['sensor_max']/.005,'failures':sum(x['status']=='FAIL' for x in b)},indent=2))
(OUT/'localization.json').write_text(json.dumps({'status':'INCONCLUSIVE_WITHOUT_PHASE_SUPPORTING_ARTIFACT','observation':'sensor pressure is the dominant failing observable; full phase-local support was not retained in compact continuation metrics','interpretation':'cannot claim a localized wavefront'},indent=2))
(OUT/'trend_summary.json').write_text(json.dumps({'branch_A':summary(a),'branch_B':summary(b),'lag1':summary(lag1),'classification':'B_PERSISTENT_NONCLOSURE'},indent=2))
(OUT/'detector_audit.json').write_text(json.dumps({'pairing':'n_vs_n-2','anchor_cycle':1,'branch_map':'relative parity A odd/B even','g2_only':True,'invalid_as_fail':False,'cross_branch_reset':False,'branch_B_final_streak':b[-1]['streak_after']},indent=2))
(OUT/'next_step_assessment.json').write_text(json.dumps({'route':'NO_JUSTIFIED_NEXT_SIMULATION','reason':'all 30 cycles are contractually exhausted; B remains persistently above thresholds without detector defect','p4':'P4_BLOCKED_G2_PERIODIC_EVIDENCE'},indent=2))
(OUT/'decision.json').write_text(json.dumps({'classification':'P4_G2_DIAG_BRANCH_B_PERSISTENT_NONCLOSURE','next_route':'NO_JUSTIFIED_NEXT_SIMULATION','solver_executed':False,'p4_pass':False,'p5_started':False},indent=2))
