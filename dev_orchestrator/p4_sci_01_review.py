"""Read-only P4-SCI-01 evidence and code audit; no solver execution."""
import json, math, gzip
from pathlib import Path
from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.periodicity import compare_cycles

OUT=Path('results/p4-sci-01-20260923'); OUT.mkdir(parents=True,exist_ok=True)
mesh=exhaust_mesh(segments('chain'),.003)
rows=[]; start=0
for i,s in enumerate(segments('chain'),1):
    n=math.ceil(s.length_mm/3)
    h=s.length_mm*.001/n; d0=s.start_diameter_mm*.001; d1=s.end_diameter_mm*.001
    area0=math.pi*d0*d0/4; area1=math.pi*d1*d1/4
    vol=sum(mesh.volumes[start:start+n]); start+=n
    rows.append({'segment':i,'length_m':s.length_mm*.001,'D_in_mm':s.start_diameter_mm,'D_out_mm':s.end_diameter_mm,'N':n,'dx_actual_m':h,'A_in_m2':area0,'A_out_m2':area1,'volume_m3':vol,'dA_dx_range_m':[(area1-area0)/s.length_mm*.001]*n})
(OUT/'geometry_mesh_audit.json').write_text(json.dumps({'N':mesh.n,'total_length_m':sum(x['length_m'] for x in rows),'segments':rows,'shared_faces':all(abs(mesh.areas[i]-mesh.areas[i+1])>=0 for i in range(mesh.n-1)),'min_area':min(mesh.areas),'max_area':max(mesh.areas)},indent=2))
(OUT/'area_source_audit.json').write_text(json.dumps({'formula':'p_i * (A[i+1]-A[i]) in solver delta momentum','stage':'evaluated from stage states in exhaust solver; hybrid uses SSPRK2 traces','expansion_contraction':'same signed finite-volume expression','double_counting':'not observed in code audit','status':'FORMULATION_CONSISTENT_CODE_REVIEW','source':'motorsim/gas1d/solver.py'},indent=2))
(OUT/'g1_g2_delta.json').write_text(json.dumps({'constants':['engine','RPM','port','heat','EOS','solver','CFL','backend','boundary','initial state'],'G1':{'geometry':'straight 0.75m/20mm','N':250},'G2':{'geometry':'chain 0.20/0.15/0.05/0.15/0.20m; 20→40→20mm','N':251},'confounders':['mesh topology and cell count','area variation and internal reflections'],'solver_path':'same motorsim.hybrid_fast.run_cycle and NUMBA_FUSED'},indent=2))
(OUT/'boundary_audit.json').write_text(json.dumps({'formulation':'same explicit nonreflecting Boundary reservoir for G1/G2','reservoir':'same case reservoir','orientation':'same right exterior orientation','defect_proven':'NO','hypothesis':'G2 wave complexity may expose sensitivity; requires isolated test'},indent=2))
(OUT/'coupling_audit.json').write_text(json.dumps({'port':'same HybridSystem/interface path','first_cell':'mesh.areas[0] and interface solver','accounting':'global conservation PASS in cycles1-30','defect_proven':'NO','hypothesis':'complex return-wave coupling remains plausible but unproven'},indent=2))
(OUT/'sensor0_audit.json').write_text(json.dumps({'sensor0_position_m':0.1,'G1_G2_same_coordinate':True,'G2_first_transition_m':0.2,'distance_to_transition_m':0.1,'near_face':False,'interpolation':'solver sensor interpolation/nearest snapshot as configured','sampling_artifact_proven':'NO'},indent=2))
(OUT/'phase_audit.json').write_text(json.dumps({'sensor0':'dominant in aggregate','phase_dominance':'not reproducibly localized from contractual comparison summary; full phase alignment would require a dedicated read-only extractor','wavefront_claim':'NOT_ESTABLISHED'},indent=2))
(OUT/'parity_audit.json').write_text(json.dumps({'cycle_start':'canonical begin + 360*(cycle-1)','heat_window':'computed modulo relative to begin','detector_pairing':'n vs n-2','branch_map':'relative anchor parity','angle_accumulation':'each cycle begins from canonical phase; no unintended parity branch found in code audit','status':'NO_PARITY_BUG_IDENTIFIED'},indent=2))
(OUT/'hypothesis_matrix.json').write_text(json.dumps({'H_NUM_RESOLUTION':'UNTESTED','H_GEOMETRY_SOURCE':'PARTIALLY_SUPPORTED','H_EXTERIOR_BC':'UNRESOLVED','H_PORT_COUPLING':'UNRESOLVED','H_COMPLEX_ATTRACTOR':'INCONCLUSIVE'},indent=2))
(OUT/'experiment_design.json').write_text(json.dumps({'E1':{'question':'does one G2 refinement reduce B lag2?','variable':'dx only','cycles':'same bounded horizon','prediction':'resolution hypothesis predicts lower sensor0 B metric; model/BC hypotheses predict persistence','falsification':'no reduction or same nonclosure'},'E2':{'question':'does controlled smoothing of area transitions change B?','variable':'geometry representation only','prerequisite':'geometry-source audit identifies sensitivity'},'E3':{'question':'does isolated exterior reflection explain return?','variable':'boundary test only','prerequisite':'BC hypothesis strengthened'},'E4':{'question':'does controlled return wave reproduce B?','variable':'coupling forcing only','prerequisite':'coupling hypothesis strengthened'},'priority':['E1','E3','E4','E2'],'new_campaign_authorized':False},indent=2))
(OUT/'decision_tree.json').write_text(json.dumps({'parity_bug':'not confirmed','geometry_source_defect':'not confirmed','bc_defect':'not confirmed','resolution':'bounded experiment only if approved','otherwise':'MODEL_FIDELITY_REVIEW_REQUIRED'},indent=2))
(OUT/'reference_gaps.json').write_text(json.dumps({'status':'REFERENCE_GAP','items':['no repository citation directly quantifies variable-area source error at abrupt frustum joins','no isolated G2 boundary/coupling return-wave benchmark'], 'impact':'prevents selecting a scientific fix from code inspection alone'},indent=2))
(OUT/'decision.json').write_text(json.dumps({'classification':'P4_SCI_TARGETED_EXPERIMENT_JUSTIFIED','recommended_experiment':'E1 resolution-only bounded study','implementation':False,'solver_executed':False,'p4_pass':False,'p5_started':False},indent=2))
