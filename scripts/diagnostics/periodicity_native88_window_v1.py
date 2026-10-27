"""Native same88 recovery after measured existing39 front/flux diagnosis."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_json_evidence_equal
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load,run
from scripts.diagnostics.relative_cycle_observations_v1 import relative_observations
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write


def prepare_native39(root):
    source=root/'periodic88-window2-v1';manifest=load(source/'manifest.json')
    def bound(name):
        if sha(source/name)!=manifest['files'][name]:raise ValueError('source39 evidence changed')
        return load(source/name)
    config=bound('run/configuration.json');previous=bound('run/checkpoint-absolute-038.json');cp=bound('run/checkpoint-absolute-039.json')
    receipt=bound('run/receipt.json');state=bound('run/detector.json');cycles=bound('run/cycles.json')
    if receipt['source_solver_sha256']!=_solver_dependency_hashes() or receipt['terminal_state_kind']!='NATIVE_CHECKPOINT' or receipt['absolute_terminal_angle']!=14040.:raise ValueError('native39 model/terminal mismatch')
    audit=root/'periodic88-front-flux-v1';am=load(audit/'manifest.json')
    if sha(audit/'run/receipt.json')!=am['files']['run/receipt.json']:raise ValueError('front flux evidence changed')
    ar=load(audit/'run/receipt.json')
    if ar['status']!='PASS' or ar['terminal_native_checkpoint_exact'] is not True or ar['solver_dependency_sha256']!=_solver_dependency_hashes() or ar['source_checkpoint_sha256']!=sha(source/'run/checkpoint-absolute-038.json') or ar['source_manifest_sha256']!=sha(source/'manifest.json'):raise ValueError('measured39 replay not compatible')
    engine=IntegratedEngine2T.from_configuration_dict(config);engine.restore(cp)
    if not _json_evidence_equal(engine.snapshot(),cp):raise ValueError('native39 roundtrip differs')
    detector=PeriodicDetectorV2(state)
    if len(detector.history)!=9 or detector.detected_period is not None or not _json_evidence_equal(detector.snapshot(),state):raise ValueError('expected original transient9 detector')
    record,_=relative_observations(engine,previous,cp,30)
    if not _json_evidence_equal(record,detector.history[-1]):raise ValueError('detector last observation differs')
    old=root/'periodic88-pilot-v1';oldmanifest=load(old/'manifest.json')
    if sha(old/'run/cycles.json')!=oldmanifest['files']['run/cycles.json']:raise ValueError('previous resource history changed')
    prior=load(old/'run/cycles.json')+cycles
    if [c['cycle'] for c in prior]!=list(range(1,10)):raise ValueError('resource history not contiguous')
    info=dict(kind='SAME_88_SIMULATION_NATIVE39_RESUME',origin_absolute_cycle=30,first_detector_cycle_index=10,
        source_native_checkpoint_sha256=sha(source/'run/checkpoint-absolute-039.json'),source_detector_sha256=sha(source/'run/detector.json'),
        source_front_flux_receipt_sha256=sha(audit/'run/receipt.json'),source_previous_cycles_paths=[str(old/'run/cycles.json'),str(source/'run/cycles.json')],
        source_previous_cycles_sha256=[sha(old/'run/cycles.json'),sha(source/'run/cycles.json')],segment_start_angle_deg=engine.crank_angle_unwrapped_deg)
    return engine,config,detector,info


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    if a.prepare_only:
        if a.output.exists():raise FileExistsError('preserve preparation')
        e,c,d,info=prepare_native39(a.root);write(a.output,dict(status='PASS',solver_steps=0,crank_angle_deg=e.crank_angle_unwrapped_deg,detector_history=len(d.history),provenance=info,source_sha256=sha(Path(__file__)),solver_dependency_sha256=_solver_dependency_hashes()))
    else:raise SystemExit(run(a.root,a.output,source_preparer=prepare_native39,first_absolute=40,last_absolute=43,solver_budget=210,admission_budget=230,schema='REFINED88_NATIVE39_WINDOW3_V1'))
