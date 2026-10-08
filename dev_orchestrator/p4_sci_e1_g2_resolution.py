"""Pre-registered, single-variable G2 resolution experiment (dx=.002)."""
import gzip,json,time
from pathlib import Path
from motorsim.exhaust_geometry import exhaust_mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.hybrid_fast import run_cycle
from motorsim.periodicity import compare_cycles
from motorsim.checkpoint import save_restart, save_full_debug
from dev_orchestrator.p4_hybrid import prepare,checks
from dev_orchestrator.p4_waves import segments

OUT=Path('results/p4-sci-e1-g2-resolution-20260923'); OUT.mkdir(parents=True,exist_ok=True)
def enrich(r,n,mesh):
    r['cycle']=n; r.update(configuration_hash='p4-sci-e1-g2-dx002',scientific_contract_id='E13-R1',solver='NUMBA_FUSED',backend='NUMBA_FUSED',mesh=mesh.n,geometry='chain',rpm=3000,operating_point='G2',cycle_convention='360',anchor_cycle=1,branch_map={'A':'odd','B':'even'})
    return r
def main():
    model,_,_,state0=prepare('chain'); mesh=exhaust_mesh(segments('chain'),.002); eos=IdealGas()
    p,T,Y=model.case.initial_pty[3]; U=eos.conservative((p/(eos.R*T),0.,p,Y)); pipe=[tuple(v*x for x in U) for v in mesh.volumes]; state=list(state0)
    (OUT/'configuration.json').write_text(json.dumps({'dx_target':.002,'backend':'NUMBA_FUSED','cfl':.4,'rpm':3000,'workers':1,'geometry':'chain','segments':[s.__dict__ for s in segments('chain')],'single_changed_variable':'dx_target','hypothesis':'H_NUM_RESOLUTION','prediction':'branch B lag2 sensor_max materially reduces'},indent=2))
    (OUT/'mesh_summary.json').write_text(json.dumps({'N':mesh.n,'faces':list(mesh.faces),'width_min':min(mesh.widths),'width_max':max(mesh.widths),'volumes_sum':sum(mesh.volumes)},indent=2))
    rows=[]; trace=[]; prev=None; start=time.perf_counter(); detected=None
    for n in range(1,31):
        t0=time.perf_counter(); initial=state[6]; row=run_cycle(mesh,pipe,state,180+360*(n-1),backend='NUMBA_FUSED',cfl=.4); row['initial_cylinder_mass']=initial; row=enrich(row,n,mesh); row['checks']=checks(row)
        if not all((row['checks'].get('conservation'),row['checks'].get('positive'))):
            (OUT/'decision.json').write_text(json.dumps({'classification':'P4_SCI_E1_NUMERICAL_REGRESSION','cycle':n},indent=2)); break
        lag1=compare_cycles(prev,row) if prev else {'status':'INVALID','reason':'MISSING_LAG1','passed':False}
        lag2=compare_cycles(rows[-2],row) if len(rows)>=2 else {'status':'INVALID','reason':'MISSING_LAG2','passed':False}
        branch='A' if n%2 else 'B'; trace.append({'cycle':n,'lag1_status':'PASS' if lag1.get('passed') else ('INVALID' if lag1.get('status')=='INVALID' else 'FAIL'),'lag1_sensor_max':lag1.get('sensor_max'),'lag2_status':'PASS' if lag2.get('passed') else ('INVALID' if lag2.get('status')=='INVALID' else 'FAIL'),'lag2_sensor_max':lag2.get('sensor_max'),'branch':branch,'conservation':True,'admissibility':True,'wall_seconds':row['cycle_wall_seconds']})
        rows.append(row); prev=row; state=row['state']; pipe=row['cells']
        if n in (5,10,15,20,25,30): save_restart(state,pipe,n,row['end'],{'backend':'NUMBA_FUSED','cfl':.4,'config_hash':'p4-sci-e1-g2-dx002'},OUT/f'restart_cycle{n:02}')
        if n in (20,25,30): save_full_debug(row,OUT/f'full_cycle{n:02}.json.gz')
    # Reconstruct streaks from trace, relative branches.
    a=b=lag1s=0
    for x in trace:
        lag1s=lag1s+1 if x['lag1_status']=='PASS' else 0
        key='lag2_status';
        if x['branch']=='A': a=a+1 if x[key]=='PASS' else 0
        else: b=b+1 if x[key]=='PASS' else 0
        x.update(lag1_streak=lag1s,branch_A_streak=a,branch_B_streak=b,detected_period=1 if lag1s>=3 else (2 if a>=3 and b>=3 else None),should_stop=lag1s>=3 or (a>=3 and b>=3))
    if trace and any(x['should_stop'] for x in trace): detected=next(x['detected_period'] for x in trace if x['should_stop'])
    else: detected=None
    (OUT/'cycle_metrics.json').write_text(json.dumps([{'cycle':r['cycle'],'work':r['work_indicated_J'],'wall_seconds':r['cycle_wall_seconds'],'complete':r['complete'],'steps':sum(s['result']['steps'] for s in r['segments']),'rhs':sum(s['result']['counts']['rhs'] for s in r['segments']),'HLLC':sum(s['result']['counts']['HLLC'] for s in r['segments']),'HLLE':sum(s['result']['counts']['HLLE'] for s in r['segments'])} for r in rows],indent=2))
    (OUT/'periodicity_trace.json').write_text(json.dumps(trace,indent=2)); (OUT/'runtime.json').write_text(json.dumps({'cycles':len(rows),'wall_seconds':time.perf_counter()-start,'N':mesh.n},indent=2)); (OUT/'restart_audit.json').write_text(json.dumps({'checkpoints':[5,10,15,20,25,30],'mesh_N':mesh.n,'detector_state':'trace persisted','baseline_restart_used':False},indent=2))
    final=trace[-1] if trace else {}; (OUT/'decision.json').write_text(json.dumps({'classification':'P4_SCI_E1_RESOLUTION_HYPOTHESIS_STRONGLY_SUPPORTED' if detected else 'P4_SCI_E1_RESOLUTION_HYPOTHESIS_WEAKENED','detected_period':detected,'converged_cycle':next((x['cycle'] for x in trace if x['detected_period']),None),'lag1_final':final.get('lag1_streak',0),'branch_A_final':final.get('branch_A_streak',0),'branch_B_final':final.get('branch_B_streak',0),'p4_pass':False,'p5_started':False},indent=2))
if __name__=='__main__':main()
