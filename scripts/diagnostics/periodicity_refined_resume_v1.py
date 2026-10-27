"""One same-grid88 continuation with exact recovery of the saved partial36."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_json_evidence_equal
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load,run
from scripts.diagnostics.relative_cycle_observations_v1 import relative_observations
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha


def prepare_resume(root):
    base=root/'periodic88-pilot-v1';source=base/'run';manifest=load(base/'manifest.json')
    def bound(name):
        if sha(source/name)!=manifest['files']['run/'+name]:raise ValueError('source88 evidence changed')
        return load(source/name)
    config=bound('configuration.json');cp=bound('checkpoint-absolute-035.json');earlier=bound('checkpoint-absolute-034.json')
    detector_state=bound('detector.json');receipt=bound('receipt.json');partial=bound('terminal-state.json');bound('recipe.json');bound('cycles.json')
    if receipt['source_solver_sha256']!=_solver_dependency_hashes() or receipt['configuration_sha256']!=sha(source/'configuration.json'):raise ValueError('same-grid source/model differs')
    if partial['schema']!='FAST_RECIPE_V1_TERMINAL_STATE' or not 12600.<partial['crank_angle_unwrapped_deg']<12960.:raise ValueError('source partial is not declared36 interval')
    engine=IntegratedEngine2T.from_configuration_dict(config);engine.restore(cp)
    if not _json_evidence_equal(engine.snapshot(),cp):raise ValueError('native35 restore differs')
    detector=PeriodicDetectorV2(detector_state)
    if len(detector.history)!=5 or detector.detected_period is not None:raise ValueError('source detector not relative5 transient')
    record,_=relative_observations(engine,earlier,cp,30)
    if not _json_evidence_equal(record,detector.history[-1]):raise ValueError('source detector observation differs')
    info=dict(kind='SAME_88_SIMULATION_RESUME_WITH_VERIFIED_PARTIAL_REPLAY',origin_absolute_cycle=30,first_detector_cycle_index=6,
        source_native_checkpoint_sha256=sha(source/'checkpoint-absolute-035.json'),source_detector_sha256=sha(source/'detector.json'),
        source_partial_path=str(source/'terminal-state.json'),source_partial_sha256=sha(source/'terminal-state.json'),
        source_partial_recipe_path=str(source/'recipe.json'),source_partial_recipe_sha256=sha(source/'recipe.json'),
        source_previous_cycles_path=str(source/'cycles.json'),segment_start_angle_deg=engine.crank_angle_unwrapped_deg)
    return engine,config,detector,info


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.root,a.output,source_preparer=prepare_resume,first_absolute=36,last_absolute=39,solver_budget=220,admission_budget=240,
        schema='REFINED88_PERIODICITY_RESUME_WINDOW2_V1'))
