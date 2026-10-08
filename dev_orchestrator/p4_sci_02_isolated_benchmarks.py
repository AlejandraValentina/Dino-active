"""Assemble isolated benchmark evidence; no motor campaign."""
import json,time
from pathlib import Path
from dev_orchestrator.p4_waves import wave
OUT=Path('results/p4-sci-02-isolated-benchmarks-20260923');OUT.mkdir(parents=True,exist_ok=True)
def main():
    cases=[]
    for n in (50,100,200):
        t=time.perf_counter();r=wave('chain',n=n,cfl=.4,rpm=3000);cases.append({'N':r['inputs']['actual_cells'],'dx_target':.75/n,'status':r['status'],'metrics':r['metrics'],'checks':r['checks'],'wall_seconds':time.perf_counter()-t})
    (OUT/'reference_audit.json').write_text(json.dumps({'internal_sources':['docs/gasdynamic/p4c_hybrid.md','docs/gasdynamic/p4_r1_observables.md','docs/gasdynamic/p4_r9_sensor_metric_audit.md'],'reference_gap':['no quantitative accepted reflection/transmission amplitude reference','no isolated G2 boundary return reference'],'status':'REFERENCE_GAP'},indent=2))
    (OUT/'geometry_benchmark.json').write_text(json.dumps({'case':'chain variable-area duct only','motor':False,'port':False,'coupling':False,'cases':cases},indent=2))
    (OUT/'geometry_refinement.json').write_text(json.dumps({'N':[c['N'] for c in cases],'arrival':[c['metrics']['arrival'] for c in cases],'pressure_integral':[c['metrics']['pressure_integral'] for c in cases],'conservation':[c['checks']['conservation'] for c in cases],'interpretation':'bounded numerical sensitivity; no external reference error available'},indent=2))
    (OUT/'area_source_balance.json').write_text(json.dumps({'formula':'p_i*(A[i+1]-A[i])','expansion_sign':'positive area delta','contraction_sign':'negative area delta','double_counting':'not found in code audit','status':'NO_DEFECT_IDENTIFIED'},indent=2))
    (OUT/'boundary_benchmark.json').write_text(json.dumps({'case':'existing straight-duct wave evidence','new_motor':False,'status':'UNRESOLVED','reason':'no quantitative nonreflecting-boundary reference threshold'},indent=2))
    (OUT/'boundary_reflection.json').write_text(json.dumps({'metric':'reflection_ratio=reflected/incidence','measured':'not accepted as benchmark because separation/reference window is not contractually calibrated','status':'REFERENCE_GAP'},indent=2))
    (OUT/'coupling_benchmark.json').write_text(json.dumps({'case':'code-level interface audit plus existing conservation evidence','isolated_run':False,'status':'UNRESOLVED','reason':'no cheap isolated return-wave fixture with reference result'},indent=2))
    (OUT/'coupling_balance.json').write_text(json.dumps({'global_conservation':'PASS in existing P4 cycles','local_return_wave':'not isolated','status':'UNRESOLVED'},indent=2))
    (OUT/'hypothesis_update.json').write_text(json.dumps({'geometry_source':'P4_SCI_GEOMETRY_SOURCE_UNRESOLVED','boundary':'P4_SCI_BOUNDARY_UNRESOLVED','coupling':'P4_SCI_COUPLING_RETURN_UNRESOLVED','integrated':'P4_SCI_REFERENCE_GAP_BLOCKS_DECISION'},indent=2))
    (OUT/'runtime.json').write_text(json.dumps({'geometry_cases':3,'wall_seconds':sum(c['wall_seconds'] for c in cases),'motor_campaign':False},indent=2))
    (OUT/'decision.json').write_text(json.dumps({'classification':'P4_SCI_REFERENCE_GAP_BLOCKS_DECISION','p4_pass':False,'p5_started':False,'solver_motor_executed':False},indent=2))
if __name__=='__main__':main()
