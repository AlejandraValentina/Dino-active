"""Read-only cycle indicators from bound native checkpoints, no solver steps.

These are L1 checkpoint-derived observations, never audited primary records.
The production comparator and its thresholds are used without modification.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal
from motorsim.reference_harness.convergence import CONTRACT,PeriodicDetectorV2,THRESHOLDS
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.diagnose_integrated_mesh_v1 import read_bound_reference,sha,write


def cycle_observations(engine,start,end,index):
    if (start['crank_angle_unwrapped_deg']!=360.*(index-1) or
            end['crank_angle_unwrapped_deg']!=360.*index or
            start['angle_deg']!=end['angle_deg'] or
            start['configuration_identity']!=end['configuration_identity']):
        raise ValueError('native cycle phases/configurations do not match')
    if engine.dynamic_reed_binding is not None:
        raise ValueError('static diagnostic only')
    state=end['state'];eos=engine.eos
    initial,final=engine.inventory(start['state']),engine.inventory(state)
    chambers={}
    for name in ('cylinder','crankcase'):
        mass,energy,volume=state['chambers'][name]
        chambers[name]=dict(mass_kg=mass,total_energy_J=energy,
            pressure_Pa=(eos.gamma-1)*energy/volume,temperature_K=energy/(mass*eos.cv))
    ducts={}
    for path in engine.ducts:
        rows=[]
        for i,(q,s) in enumerate(zip(state['ducts'][path.id],state['species']['ducts'][path.id])):
            rho,u,p,_=engine._primitive(q)
            volume=path.mesh.volumes[i]
            rows.append(dict(mass_kg=rho*volume,total_energy_J=q[2]*volume,
                pressure_Pa=p,temperature_K=p/(rho*eos.R),
                species_mass_fractions=[v/sum(s) for v in s],
                velocity_over_sound_speed=u/eos.sound_speed((rho,u,p,1.))))
        ducts[path.id]=rows
    a,b=start['ledger'],end['ledger']
    delta=lambda key:b[key]-a[key]
    obs=dict(chambers=chambers,ducts=ducts,global_species_kg=list(final['species_kg']),
        cycle_start_total_mass_kg=initial['mass_kg'],cycle_start_total_energy_J=initial['energy_J'],
        work_J=-delta('cylinder_work_J'),fresh_delivery_kg=delta('fresh_delivered_kg'),
        fresh_short_circuit_kg=delta('fresh_short_circuit_kg'),
        p7_burned_produced_kg=b['p7_source_species_kg'][3]-a['p7_source_species_kg'][3],
        p7_heat_J=delta('p7_heat_added_J'))
    return dict(contract=CONTRACT,cycle_index=index,
        configuration_hash=end['configuration_identity']['configuration_sha256'],observables=obs)


def diagnose(directory):
    reference,config_path,terminal=read_bound_reference(directory)
    config=json.loads(config_path.read_text(encoding='utf-8'))
    engine=IntegratedEngine2T.from_configuration_dict(config)
    initial=json.loads((directory/'initial-checkpoint.json').read_text(encoding='utf-8'))
    if not _json_evidence_equal(initial,engine.snapshot()):
        raise ValueError('initial checkpoint does not match independently reconstructed configuration')
    p=directory/'checkpoint-360.json'
    entry=next(x for x in reference['checkpoints'] if x['path']==p.name)
    if sha(p)!=entry['sha256']:raise ValueError('cycle-1 checkpoint hash mismatch')
    middle=json.loads(p.read_text(encoding='utf-8'))
    for snapshot in (initial,middle,terminal):engine.restore(snapshot)
    records=[cycle_observations(engine,a,b,i) for i,(a,b) in enumerate(
        ((initial,middle),(middle,terminal)),1)]
    detector=PeriodicDetectorV2()
    for record in records:outcome=detector.update(record)
    comparison=outcome['outcomes']['lag1']
    if comparison['status']=='INVALID':raise ValueError(comparison['reason'])
    failed={key:value for key,value in comparison['metrics'].items() if not value['passed']}
    components=Counter('exhaust' if key.startswith('ducts.exhaust') else
        'other_ducts' if key.startswith('ducts.') else
        'global_species' if key.startswith('global_species.') else 'chambers_or_cycle_integrals'
        for key in failed)
    largest=sorted(((v['value']/v['threshold'],key) for key,v in failed.items()),reverse=True)[:12]
    return dict(schema='DINO_CHECKPOINT_PERIODICITY_INDICATORS_V1',review='SELF_REVIEW',
        evidence_level='L1_NATIVE_CHECKPOINT_DERIVED_NOT_AUDITED_PRIMARY',solver_steps=0,
        receipt_sha256=sha(directory/'receipt.json'),configuration_sha256=sha(config_path),
        cycle1_checkpoint_sha256=sha(p),initial_checkpoint_sha256=sha(directory/'initial-checkpoint.json'),
        comparison=comparison,failed_count=len(failed),checked_count=len(comparison['metrics']),
        failed_components=dict(components),largest_threshold_ratios=largest,
        detector_state=detector.snapshot(),thresholds=deepcopy(THRESHOLDS),
        periodicity_demonstrated=False,experimental_validation=False,
        qualification='Two complete cycles cannot establish required streak or period-2. Failure shows continuing transient, not solver instability or multiple periodic attractors.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--levels',nargs='+',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    check_storage_requirements([(args.output,2*1024**2)])
    if args.output.exists():raise FileExistsError('preserve earlier evidence')
    result={str(level):diagnose(level) for level in args.levels}
    write(args.output,result)
    print(json.dumps({k:{n:v[n] for n in ('failed_count','checked_count','failed_components','periodicity_demonstrated')} for k,v in result.items()},indent=2))
