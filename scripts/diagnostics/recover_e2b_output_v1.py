"""Finish the interrupted E2B diagnostic; no fresh simulations or new cycles."""
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from motorsim._evidence_io import read_primary
from scripts.diagnostics.e2b_periodic_ab_v1 import (
    OUT,PLAN,RAW_NAME,load,write,sha,default_artifact_root,check_storage_requirements,
    PeriodicDetectorV2,MechanicalLossModel,primary_observation_record,
    audit_integrated_cycle_primary,bound_periodic_output,empty_totals,accumulate,serial,
    _validated_last_port_close_species,audit_variant,_solver_dependency_hashes)


def state_frame(state,gamma):
    q=state['ducts']['exhaust']
    return ([(x[0],x[1]/x[0],(gamma-1)*(x[2]-.5*x[1]**2/x[0])) for x in q],
        [(gamma-1)*state['chambers'][n][1]/state['chambers'][n][2] for n in ('cylinder','crankcase')])


def main():
    began=time.perf_counter();raw=default_artifact_root()/RAW_NAME
    old=load(OUT/'execution-attempt1-receipt.json');m=load(PLAN)
    recovery=load(OUT/'recovery-manifest.json')
    for path,digest in recovery['files'].items():
        if sha(ROOT/path)!=digest:raise ValueError('recovery prerequisite changed: '+path)
    if old['solver_dependency_sha256']!=_solver_dependency_hashes():raise ValueError('solver changed')
    if (raw/'recovery-receipt.json').exists():raise FileExistsError('single recovery only')
    preflight=check_storage_requirements([(raw,512*1024**2)])
    prior=old['cumulative_wall_s']+load(OUT/'recovery-verification.json')['wall_s']
    stop=began+5400-prior-150;d=raw/'A';detector=PeriodicDetectorV2()
    saved=load(d/'detector.json')
    for row in saved['history'][:26]:detector.update(row)
    records=[]
    for cycle in range(27,31):
        primary=read_primary(d/f'primary-{cycle:03}.json.gz')
        outcome=detector.update(primary_observation_record(primary))
        if cycle<30:
            entry=load(d/f'audit-{cycle:03}.json')
            if entry['audit']['status']!='PASS':raise ValueError('persisted audit failed')
        else:
            tick=time.perf_counter()
            audit=audit_integrated_cycle_primary(primary,preserve_precycle_p7_baseline=True)
            if audit['status']!='PASS':raise ValueError('existing A30 primary audit failed')
            if detector.detected_period!=1 or detector.converged_cycle!=30:raise ValueError('A detector differs')
            mechanical=MechanicalLossModel.from_dict(m['mechanical_loss_model'])
            write(d/'engineering-030.json',bound_periodic_output(primary,detector,mechanical))
            angle,species,role=_validated_last_port_close_species(primary,primary['port_closure_snapshots']['snapshots'])
            write(d/'charge-030.json',dict(phase_deg=angle-360*29,closure_role=role,
                fresh_air_kg=species[0],fuel_kg=species[1],total_kg=sum(species),
                fresh_charge_kg=species[0]+species[1],
                nonfresh_burned_plus_residual_fraction=(species[2]+species[3])/sum(species),
                initial_residual_label_fraction=species[2]/sum(species)))
            cfg=load(d/'configuration.json');gamma=cfg['eos']['gamma']
            initial=load(d/'checkpoint-029.json')['state']
            frames=[];chambers=[];w,p=state_frame(initial,gamma);frames.append(w);chambers.append(p)
            totals=empty_totals([p['id'] for p in cfg['ducts']])
            for row in primary['trajectory']:
                for faces in row['stage_face_fluxes']:accumulate(totals,faces,.5*row['dt_s'])
                phase=row['angle_end_deg']-360*29;k=round(phase*2)
                if abs(phase-k/2)<1e-8:
                    if k!=len(frames):raise ValueError('existing primary phase gap')
                    w,p=state_frame(row['stage_states'][2],gamma);frames.append(w);chambers.append(p)
            if len(frames)!=721:raise ValueError('incomplete existing primary')
            write(d/'interfaces-030.json',serial(totals))
            np.savez_compressed(d/'waves-030.npz',phase_deg=np.arange(721)*.5,field=frames,chamber_pressures=chambers)
            entry=dict(cycle=30,audit=audit,periodicity_outcome=outcome,wall_s=time.perf_counter()-tick,
                primary_sha256=sha(d/'primary-030.json.gz'),replay_exact=True,
                recovery='existing canonical primary; no integrated replay')
            write(d/'audit-030.json',entry)
        records.append(entry);del primary;gc.collect()
    write(d/'audit-receipt.json',dict(variant='A',period=1,converged_cycle=30,status='PASS',
        audited_cycles=[27,28,29,30],detector=detector.snapshot(),primary_replay_exact=True,
        recovery='A27-29 persisted audits; A30 existing primary re-audited without integrated simulation'))
    b=next(s for s in old['simulations'] if s['variant']=='B')
    audit_variant('B',b,m,raw,stop,min(stop,time.perf_counter()+m['audit_limit_s']))
    result=dict(old,classification='E2B_PERIÓDICO_EXPLORATORIO',error=None,
        audited_variants=['A','B'],wall_s=time.perf_counter()-began,
        prior_charged_s=prior,cumulative_wall_s=prior+time.perf_counter()-began,
        recovery_storage_preflight=preflight,original_attempt_sha256=sha(OUT/'execution-attempt1-receipt.json'),
        wrapper_defect='missing actual detector binding in derived engineering exporter; no physical solver defect',
        recovery_manifest_sha256=sha(OUT/'recovery-manifest.json'),fresh_simulations_repeated=0)
    write(raw/'recovery-receipt.json',result);write(OUT/'recovery-receipt.json',result)
    # receipt.json is the current summary; immutable attempt1 preserved separately.
    write(raw/'receipt-attempt1.json',old);write(raw/'receipt.json',result)
    write(OUT/'execution-receipt.json',result)
    print(json.dumps(dict(classification=result['classification'],cumulative_wall_s=result['cumulative_wall_s'])))


if __name__=='__main__':main()
