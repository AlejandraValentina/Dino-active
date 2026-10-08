"""Offline branch identity reinterpretation for E1; no solver execution."""
import json,statistics
from pathlib import Path
OUT=Path('results/p4-sci-e1r2-branch-invariant-20260923');OUT.mkdir(parents=True,exist_ok=True)
base={'A':[.0009643634490156208,.00027234513860523396,.0001577184022186247], 'B':[.08972982705497642,.06833171258716575,.02905798383046952]}
ref={'A':[.06596640257081504,.0640032192195528,.02351622368912625], 'B':[.0001501194546968328,.0000812186555296173,.00007146677140950643]}
def stats(v): return {'min':min(v),'max':max(v),'median':statistics.median(v),'last3':v[-3:],'last5':v[-5:]}
closed={'baseline':'A','refined':'B'}; non={'baseline':'B','refined':'A'}
non_b=base['B']; non_r=ref['A']; ratios=[x/y for x,y in zip(non_r,non_b)]
(OUT/'decision.json').write_text(json.dumps({'classification':'P4_SCI_E1_PHASE_SWAP_CONFIRMED','third_resolution':'THIRD_RESOLUTION_NOT_YET_JUSTIFIED','solver_executed':False,'p4_pass':False,'p5_started':False},indent=2))
(OUT/'branch_identity_audit.json').write_text(json.dumps({'within_run':'A/B relative to anchor; valid for E13','cross_mesh':'not guaranteed physical identity','baseline_anchor':'cycle1 odd/even','refined_anchor':'cycle1 odd/even','conclusion':'labels are not cross-mesh identities'},indent=2))
(OUT/'labeled_comparison.json').write_text(json.dumps({'baseline_B':base['B'],'refined_B':ref['B'],'ratios_refined_over_baseline':[x/y for x,y in zip(ref['B'],base['B'])],'interpretation':'large reduction under B label motivated original E1-R1 classification'},indent=2))
(OUT/'branch_invariant_comparison.json').write_text(json.dumps({'mapping':{'baseline_closed':'A','baseline_nonclosed':'B','refined_closed':'B','refined_nonclosed':'A'},'closed_baseline':base['A'],'closed_refined':ref['B'],'nonclosed_baseline':non_b,'nonclosed_refined':non_r,'nonclosed_ratios':ratios,'nonclosed_summary':{'mean':statistics.mean(ratios),'median':statistics.median(ratios),'min':min(ratios),'max':max(ratios)}},indent=2))
(OUT/'worst_branch_trace.json').write_text(json.dumps({'pairs':['25/26','27/28','29/30'],'baseline':[max(base['A'][i],base['B'][i]) for i in range(3)],'refined':[max(ref['A'][i],ref['B'][i]) for i in range(3)],'interpretation':'terminal worst branch remains materially similar in scale'},indent=2))
(OUT/'best_branch_trace.json').write_text(json.dumps({'pairs':['25/26','27/28','29/30'],'baseline':[min(base['A'][i],base['B'][i]) for i in range(3)],'refined':[min(ref['A'][i],ref['B'][i]) for i in range(3)]},indent=2))
(OUT/'state_matching.json').write_text(json.dumps({'mapping_AA_BB':'UNRESOLVED','mapping_AB_BA':'UNRESOLVED','reason':'full equivalent branch state/work/cylinder/port arrays are not retained for all terminal pairs','no_sensor_only_decision':True},indent=2))
(OUT/'phase_swap_assessment.json').write_text(json.dumps({'H_PHASE_SWAP':'SUPPORTED','evidence':'closed branch changes A→B while nonclosed changes B→A','caveat':'state-based cross-mesh matching unavailable; global equivalence not proven'},indent=2))
(OUT/'resolution_hypothesis_reassessment.json').write_text(json.dumps({'H1_resolution_changes_solution':'SUPPORTED','H2_insufficient_resolution_causes_E13_failure':'UNPROVEN','reason':'one branch remains open after relabeling; E13 requires both branches'},indent=2))
(OUT/'third_resolution_decision.json').write_text(json.dumps({'decision':'THIRD_RESOLUTION_NOT_YET_JUSTIFIED','candidate_metric':'worst_branch_lag2_sensor_max plus both-branch E13 outcome','reason':'first resolve cross-mesh state identity and checkpoint instrumentation'},indent=2))
