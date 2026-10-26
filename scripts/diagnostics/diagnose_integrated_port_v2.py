"""Preregistered two-cycle independently initialized integrated diagnostic."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import (IntegratedEngine2T, _integrated_scheduled_angles,
                                   _json_evidence_equal)
from motorsim.port_connection_v2 import SCHEMA, NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def run(output,model,step_degrees):
    preflight = check_storage_requirements([(output,100*1024**2)])
    if output.exists():
        raise FileExistsError('diagnostic output must be new; preserve earlier attempts')
    receipt_path = ROOT/'results/periodic-rpm-curves-v1/receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    selected = [p for p in receipt['points'] if p['variant']=='A_original' and p['rpm']==9000]
    if len(selected)!=1:
        raise ValueError('exact A9000 reference not found')
    source = Path(selected[0]['result']).parent/'native-configuration.json'
    # Bind the native configuration through the original invocation manifest.
    manifests = list(source.parent.glob('invocation-*/manifest.json'))
    manifest_path = next(p for p in manifests if sha(p)==selected[0]['manifest_sha256'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if sha(source)!=manifest['bindings']['configuration_file_sha256']:
        raise ValueError('source configuration hash mismatch')
    config = json.loads(source.read_text(encoding='utf-8'))
    if model=='nozzle':
        config['geometry_identity']['port_connection_model']=SCHEMA
        config['base_configuration_schema']=config['schema']
        config['schema']='MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V7'
    e = IntegratedEngine2T.from_configuration_dict(config)
    output.mkdir(parents=True)
    write(output/'configuration.json',e.configuration_dict())
    write(output/'initial-checkpoint.json',e.snapshot())
    start = time.perf_counter()
    compute_s = 0.
    schedules = sorted(_integrated_scheduled_angles(e,720.))
    counts,rejects = Counter(),Counter()
    maxima = dict(cylinder_pressure_pa=0.,crankcase_pressure_pa=0.,exhaust_pressure_pa=0.,
                  interior_port_mach=0.,boundary_port_mach=0.)
    flux_integrals = Counter()
    samples,steps = [],0
    status,error = 'COMPLETE',None
    checkpoint_hashes = []
    try:
        with gzip.open(output/'primary-stages.jsonl.gz','wt',encoding='utf-8',compresslevel=3) as log:
            while e.crank_angle_unwrapped_deg < 720.-1e-9:
                if time.perf_counter()-start>=240 or steps>=10000:
                    raise TimeoutError('declared diagnostic computation/step budget reached')
                if (output/'primary-stages.jsonl.gz').stat().st_size>95*1024**2:
                    raise TimeoutError('declared durable-artifact budget reached')
                angle = e.crank_angle_unwrapped_deg
                targets = [720.,(math.floor((angle+1e-9)/step_degrees)+1)*step_degrees]
                targets += [a for a in schedules if a>angle+1e-9]
                delta = min(targets)-angle
                for attempt in range(25):
                    tick = time.perf_counter()
                    try:
                        row=e.step(delta/(6*9000),delta)
                    except NoAdmissiblePortState:
                        compute_s += time.perf_counter()-tick
                        raise
                    except ValueError as exc:
                        compute_s += time.perf_counter()-tick
                        if not any(text in str(exc) for text in (
                            'CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):
                            raise
                        rejects[str(exc).split(':')[0]]+=1
                        delta *= .5
                    else:
                        compute_s += time.perf_counter()-tick
                        break
                else:
                    raise RuntimeError('25 rejected trials without admissible step')
                for stage,faces in enumerate(row['stage_face_fluxes']):
                    state = row['stage_states'][stage]
                    for name in ('cylinder','crankcase'):
                        q=state['chambers'][name]
                        maxima[name+'_pressure_pa']=max(maxima[name+'_pressure_pa'],(e.eos.gamma-1)*q[1]/q[2])
                    for path in e.ducts:
                        face=faces[path.id]
                        if path.role=='exhaust':
                            for q in state['ducts'][path.id]:
                                maxima['exhaust_pressure_pa']=max(maxima['exhaust_pressure_pa'],e._primitive(q)[2])
                        endpoints = ['right'] if path.role=='intake' else (['left','right'] if path.role=='transfer' else ['left'])
                        for side in endpoints:
                            flux_integrals[f'{path.id}:{side}:mass_kg']+=.5*row['dt_s']*face[side][0]
                        for port in face.get('port_connection_states',{}).values():
                            x=port['exchange'];counts[x['branch']]+=1
                            for label,w in [('interior',port['interior_primitive']),('boundary',x['boundary_state'])]:
                                maxima[label+'_port_mach']=max(maxima[label+'_port_mach'],abs(w[1])/e.eos.sound_speed(w))
                log.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
                steps+=1
                if abs(e.crank_angle_unwrapped_deg%360)<1e-9:
                    samples.append(dict(angle_deg=e.crank_angle_unwrapped_deg,
                        inventory=e.inventory(),ledger=deepcopy(e.ledger),conservation=e.conservation_report()))
                    e.compact_cycle_trace()
                    snapshot=e.snapshot()
                    path=output/f'checkpoint-{int(e.crank_angle_unwrapped_deg)}.json'
                    write(path,snapshot)
                    checkpoint_hashes.append(dict(path=path.name,sha256=sha(path)))
                    restored=IntegratedEngine2T.from_configuration_dict(config)
                    restored.restore(json.loads(path.read_text(encoding='utf-8')))
                    if (not _json_evidence_equal(restored.state,e.state) or
                            not _json_evidence_equal(restored.ledger,e.ledger)):
                        raise AssertionError('checkpoint state/ledger mismatch')
    except Exception as exc:
        status,error='STOPPED',f'{type(exc).__name__}: {exc}'
    snapshot=e.snapshot()
    write(output/'terminal-checkpoint.json',snapshot)
    replay_equal=False
    if status=='COMPLETE':
        a,b=e,IntegratedEngine2T.from_configuration_dict(config)
        b.restore(deepcopy(snapshot))
        a.step(1e-9,.000054);b.step(1e-9,.000054)
        replay_equal=a.snapshot()==b.snapshot()
        e.restore(deepcopy(snapshot))
    report=e.conservation_report()
    scales=dict(mass=e.initial_inventory['mass_kg']+abs(e.ledger['external_mass_kg']),
        energy=e.initial_inventory['energy_J']+sum(abs(v) for k,v in e.ledger.items() if
            isinstance(v,(float,int)) and k.endswith('_J')))
    normalized=dict(mass=abs(report['mass']['residual'])/scales['mass'],
        energy=abs(report['energy']['residual'])/scales['energy'],
        species=max(abs(r['residual']) for r in report['species'].values())/scales['mass'])
    result=dict(schema='DINO_INTEGRATED_PORT_V2_DIAGNOSTIC',status=status,error=error,
        model=model,step_degrees=step_degrees,terminal_angle_deg=e.crank_angle_unwrapped_deg,
        accepted_steps=steps,rejections=dict(rejects),wall_s=time.perf_counter()-start,
        compute_s=compute_s,branches=dict(counts),maxima=maxima,
        mass_flux_integrals=dict(flux_integrals),cycles=samples,final_state=e.state,
        final_ledger=e.ledger,conservation=report,normalized_residuals=normalized,
        checkpoint_restore_and_next_step_equal=replay_equal,checkpoints=checkpoint_hashes,
        configuration_sha256=sha(output/'configuration.json'),source_configuration_sha256=sha(source),
        primary_stages_sha256=sha(output/'primary-stages.jsonl.gz'),
        terminal_checkpoint_sha256=sha(output/'terminal-checkpoint.json'),
        storage_preflight=preflight,scientific_state='TRANSIENT_ENGINEERING_DIAGNOSTIC',
        experimental_validation=False,review='SELF_REVIEW')
    result['numerical_gate']=bool(status=='COMPLETE' and replay_equal and
        normalized['mass']<=1e-9 and normalized['species']<=1e-9 and normalized['energy']<=1e-8)
    write(output/'receipt.json',result)
    print(json.dumps({k:result[k] for k in ('status','error','terminal_angle_deg','accepted_steps','wall_s','compute_s','normalized_residuals','numerical_gate')},indent=2))
    return 0 if result['numerical_gate'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',choices=['legacy','nozzle'],required=True)
    p.add_argument('--step-degrees',type=float,choices=[.5,.25],required=True)
    args=p.parse_args()
    raise SystemExit(run(args.output,args.model,args.step_degrees))
