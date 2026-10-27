"""Correct only the wrapper's record tag using immutable audited primaries."""
import argparse
import gc
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim._evidence_io import read_primary
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.diagnostics.periodic_primary_audit_v1 import load,primary_observation_record
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def reconstruct(root,out):
    check_storage_requirements([(out,4*1024**2),(Path(tempfile.gettempdir()),128*1024**2)])
    if out.exists():raise FileExistsError('preserve original and any prior reconstruction')
    audit_root=root/'periodic-primary-audit-v1';manifest=load(audit_root/'manifest-original.json')
    def bound(relative):
        path=audit_root/relative
        if sha(path)!=manifest['files'][relative]:raise ValueError('original audit evidence changed')
        return load(path)
    original=bound('run/receipt.json')
    if original['cycles']!=[27,28,29,30]:raise ValueError('four completed primary audits required')
    artifacts=Path(original['durable_artifact_root']).resolve();entries=[]
    for cycle in (27,28,29,30):
        entry=bound(f'run/cycle-{cycle:03}-audit.json')
        path=(artifacts/entry['artifact_name']).resolve()
        if path.parent!=artifacts or entry['status']!='PASS' or entry['audit']['status']!='PASS' or not entry['audit']['recomputed'] or sha(path)!=entry['compressed_sha256']:
            raise ValueError('missing or changed audited primary')
        entries.append((entry,path))
    detector=PeriodicDetectorV2()
    for record in original['detector']['history'][:26]:detector.update(record)
    started=time.perf_counter();out.mkdir(parents=True);comparisons=[]
    for entry,path in entries:
        if time.perf_counter()-started>90:raise TimeoutError('read-only reconstruction budget')
        primary=read_primary(path,expected_sha256=entry['primary_sha256'])
        if primary['cycle_index']!=entry['cycle'] or primary['evidence_binding']['trajectory_sha256']!=entry['audit']['trajectory_sha256']:raise ValueError('primary/audit binding differs')
        outcome=detector.update(primary_observation_record(primary));comparisons.append(dict(cycle=entry['cycle'],data_contract=primary['contract'],outcome=outcome))
        del primary;gc.collect()
    status='PASS' if detector.detected_period==1 and detector.converged_cycle==30 else 'FAIL'
    result=dict(schema='AUDITED_PERIODICITY_RECONSTRUCTION_V1',status=status,wall_s=time.perf_counter()-started,
        original_audit_receipt_sha256=sha(audit_root/'run/receipt.json'),original_failure_preserved=True,
        defect='New diagnostic wrapper used detector V2 tag for V1 cycle-data records; frozen comparator correctly rejected identity.',
        correction='Preserve primary data contract; V2 remains the detector implementation. No numerical or threshold change.',
        source_primary_compressed_sha256={str(e['cycle']):e['compressed_sha256'] for e,p in entries},
        comparisons=comparisons,detector=detector.snapshot(),periodicity_audited=(status=='PASS'),
        solver_steps=0,new_simulation_cycles=0,mesh_independence=False,experimental_validation=False,review='SELF_REVIEW')
    write(out/'receipt.json',result);print({k:result[k] for k in ('status','wall_s','periodicity_audited','solver_steps')})
    return 0 if status=='PASS' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();raise SystemExit(reconstruct(a.root,a.output))
