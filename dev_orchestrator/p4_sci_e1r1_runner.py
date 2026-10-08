"""Contractual E1-R1 recovery runner; one variable (dx=.002), live E13 state."""
import gzip,json,time,os
from pathlib import Path
from motorsim.exhaust_geometry import exhaust_mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.hybrid_fast import run_cycle
from motorsim.periodicity import compare_cycles,PeriodicityDetector
from motorsim.checkpoint import save_restart,save_full_debug,load_restart
from dev_orchestrator.p4_hybrid import prepare,checks
from dev_orchestrator.p4_waves import segments

OUT=Path('results/p4-sci-e1r1-g2-resolution-20260923'); CONTROL=Path('results/p4-sci-e1-g2-resolution-20260923')
def atomic(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)); os.replace(tmp,path)
def enrich(r,n,mesh):
    r['cycle']=n; r.update(configuration_hash='p4-sci-e1-g2-dx002',scientific_contract_id='E13-R1',solver='NUMBA_FUSED',backend='NUMBA_FUSED',mesh=mesh.n,geometry='chain',rpm=3000,operating_point='G2',cycle_convention='360',anchor_cycle=1,branch_map={'A':'odd','B':'even'}); return r
def telemetry(rows):
    out=[]
    for r in rows:
        counts=[s['result'].get('counts',{}) for s in r['segments']]
        out.append({'cycle':r['cycle'],'work':r['work_indicated_J'],'complete':r['complete'],'wall_seconds':r['cycle_wall_seconds'],'rhs':sum(c.get('rhs',0) for c in counts),'HLLC':sum(c.get('HLLC',0) for c in counts),'HLLE':sum(c.get('HLLE',0) for c in counts),'rejected':sum(c.get('rejected',0) for c in counts),'steps':None})
    return out
def main():
    OUT.mkdir(parents=True,exist_ok=True); model,_,_,state0=prepare('chain'); mesh=exhaust_mesh(segments('chain'),.002); eos=IdealGas(); p,T,Y=model.case.initial_pty[3]; U=eos.conservative((p/(eos.R*T),0.,p,Y)); pipe=[tuple(v*x for x in U) for v in mesh.volumes]; state=list(state0)
    atomic(OUT/'configuration.json',{'dx_target':.002,'N':mesh.n,'backend':'NUMBA_FUSED','cfl':.4,'rpm':3000,'workers':1,'geometry':'chain','single_changed_variable':'dx_target','hypothesis':'H_NUM_RESOLUTION','prediction':'branch B lag2 sensor_max materially reduces'})
    atomic(OUT/'mesh_summary.json',{'N':mesh.n,'width_min':min(mesh.widths),'width_max':max(mesh.widths),'volume_sum':sum(mesh.volumes)})
    rows=[]; trace=[]; detector=PeriodicityDetector(1,{'A':'odd','B':'even'}); started=time.perf_counter(); repro=[]; detected=None
    for n in range(1,31):
        initial=state[6]; row=enrich(run_cycle(mesh,pipe,state,180+360*(n-1),backend='NUMBA_FUSED',cfl=.4),n,mesh); row['initial_cylinder_mass']=initial; row['checks']=checks(row)
        if not row['checks'].get('conservation') or not row['checks'].get('positive'):
            atomic(OUT/'decision.json',{'classification':'P4_SCI_E1R1_NUMERICAL_REGRESSION','cycle':n}); break
        lag1=compare_cycles(rows[-1],row) if rows else {'status':'INVALID','reason':'MISSING_LAG1','passed':False}; lag2=compare_cycles(rows[-2],row) if len(rows)>=2 else {'status':'INVALID','reason':'MISSING_LAG2','passed':False}; branch='A' if n%2 else 'B'; result=detector.update(row,lag1=lag1,lag2=lag2,branch=branch)
        entry={'cycle':n,'branch':branch,'lag1_status':'PASS' if lag1.get('passed') else ('INVALID' if lag1.get('status')=='INVALID' else 'FAIL'),'lag1_sensor_max':lag1.get('sensor_max'),'lag2_status':'PASS' if lag2.get('passed') else ('INVALID' if lag2.get('status')=='INVALID' else 'FAIL'),'lag2_sensor_max':lag2.get('sensor_max'),'branch_A_streak':detector.branch_A_streak,'branch_B_streak':detector.branch_B_streak,'lag1_streak':detector.lag1_streak,'detected_period':detector.detected_period,'converged_cycle':detector.converged_cycle,'periodicity_status':('CONVERGED_PERIOD'+str(detector.detected_period) if detector.detected_period else 'NOT_CONVERGED'),'should_stop':detector.detected_period is not None,'invalid_reason':result.get('reason'),'conservation':True,'admissibility':True,'wall_seconds':row['cycle_wall_seconds']}
        trace.append(entry); rows.append(row); atomic(OUT/f'summary_cycle{n:02}.json',{'cycle':n,'complete':row['complete'],'work':row['work_indicated_J'],'history':row['history'],'checks':row['checks'],'periodicity':entry})
        atomic(OUT/'periodicity_trace.json',trace); atomic(OUT/'cycle_metrics.json',telemetry(rows))
        # Persist the terminal state of this cycle, after advancing the live chain.
        terminal_state, terminal_pipe = row['state'], row['cells']
        if n in (5,10,15,20,25,30): save_restart(terminal_state,terminal_pipe,n,row['end'],{'backend':'NUMBA_FUSED','cfl':.4,'config_hash':'p4-sci-e1-g2-dx002'},OUT/f'restart_cycle{n:02}',detector=detector)
        if n in (20,25,30): save_full_debug(row,OUT/f'full_cycle{n:02}.json.gz')
        cdir=CONTROL/f'restart_cycle{n:02}'
        if n in (5,10,15,20,25,30) and cdir.exists():
            oldmeta,oldstate,oldcells=load_restart(cdir); repro.append({'cycle':n,'state_max_abs_diff':max(abs(a-b) for a,b in zip(state,oldstate)) if len(state)==len(oldstate) else None,'mesh_shape_equal':len(pipe)==len(oldcells),'control_used_as_input':False})
        if entry['should_stop']: detected=detector.detected_period; break
        state,pipe=row['state'],row['cells']
    final=trace[-1] if trace else {}; classification='P4_SCI_E1R1_NUMERICAL_REGRESSION' if not rows or not rows[-1]['checks'].get('conservation') else ('P4_SCI_E1R1_CONVERGED' if detected else 'P4_SCI_E1_RESOLUTION_HYPOTHESIS_WEAKENED')
    atomic(OUT/'runtime.json',{'cycles_executed':len(rows),'wall_seconds':time.perf_counter()-started,'N':mesh.n}); atomic(OUT/'restart_audit.json',{'checkpoints':[5,10,15,20,25,30],'detector_state_persisted':True,'baseline_restart_used':False}); atomic(OUT/'reproducibility_against_e1.json',repro); atomic(OUT/'baseline_vs_refined.json',{'baseline_sensor_last3':[.0897298,.0683317,.0290580],'refined_trace_available':True,'primary_metric':'branch-B lag2 sensor_max'}); atomic(OUT/'branch_b_comparison.json',{'trace':[x for x in trace if x['branch']=='B']}); atomic(OUT/'hypothesis_assessment.json',{'classification':classification,'mesh_convergence_not_claimed':True}); atomic(OUT/'decision.json',{'classification':classification,'detected_period':detected,'lag1_final':final.get('lag1_streak',0),'branch_A_final':final.get('branch_A_streak',0),'branch_B_final':final.get('branch_B_streak',0),'p4_pass':False,'p5_started':False})
if __name__=='__main__':main()
