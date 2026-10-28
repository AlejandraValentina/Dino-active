"""Reduce saved first-order port diagnostics; does not advance the solver."""
import argparse
from collections import defaultdict
from copy import deepcopy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.agents.storage_preflight import check_storage_requirements, default_artifact_root
from motorsim.port_connection_v2 import SCHEMA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reduce_case(folder):
    receipt = json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
    config = json.loads((folder/'configuration.json').read_text(encoding='utf-8'))
    primary = folder/'primary-stages.jsonl.gz'
    assert sha(primary) == receipt['primary_stages_sha256']
    assert sha(folder/'configuration.json') == receipt['configuration_sha256']
    assert sha(folder/'terminal-checkpoint.json') == receipt['terminal_checkpoint_sha256']
    assert receipt['numerical_gate'] and receipt['spatial_model']=='legacy'
    assert receipt['terminal_angle_deg'] == 720.
    flows = defaultdict(lambda: dict(forward_kg=0., reverse_kg=0.,net_kg=0.,
                                    energy_x_j=0.,species_x_kg=[0.]*4))
    trapped = []
    with gzip.open(primary,'rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            for faces in row['stage_face_fluxes']:
                for duct,face in faces.items():
                    for side in ('left','right'):
                        values = face[side]
                        f = flows[duct+':'+side]
                        weight = row['dt_s']/2
                        q = values[0]
                        f['forward_kg'] += weight*max(0.,q)
                        f['reverse_kg'] += weight*max(0.,-q)
                        f['net_kg'] += weight*q
                        f['energy_x_j'] += weight*values[2]
                        for j,v in enumerate(face[side+'_species']):
                            f['species_x_kg'][j] += weight*v
            g0,g1=row['stage_geometry']
            if g0['exhaust_area_m2']>0 and g1['exhaust_area_m2']==0:
                s = row['stage_states'][2]
                q = s['chambers']['cylinder']
                species = s['species']['chambers']['cylinder']
                trapped.append(dict(angle_deg=row['angle_end_deg'],mass_kg=q[0],
                    pressure_pa=(config['eos']['gamma']-1)*q[1]/q[2],
                    fresh_air_kg=species[0],fuel_kg=species[1],
                    burned_fraction=species[2]/q[0],
                    initial_residual_fraction=species[3]/q[0],
                    used_fraction=(species[2]+species[3])/q[0]))
    assert len(trapped)==2, 'need both actual exhaust-closing events'
    return dict(model=receipt['model'],compute_s=receipt['compute_s'],
        wall_s=receipt['wall_s'],accepted_steps=receipt['accepted_steps'],
        rejected_trials=sum(receipt['rejections'].values()),maxima=receipt['maxima'],
        normalized_residuals=receipt['normalized_residuals'],
        restore_next_step_equal=receipt['checkpoint_restore_and_next_step_equal'],
        trapped_at_exhaust_closing=trapped,face_integrals=dict(flows),
        cylinder_work_j=-receipt['final_ledger']['cylinder_work_J'],
        crankcase_work_j=-receipt['final_ledger']['crankcase_work_J'],
        scientific_state='TRANSIENT_NOT_PERIODIC_NOT_VALIDATED',
        source_hashes={name:sha(folder/name) for name in (
            'configuration.json','initial-checkpoint.json','terminal-checkpoint.json',
            'receipt.json','primary-stages.jsonl.gz')}),config


def assert_matched_configurations(old, new):
    """Permit only the explicit, versioned port-model difference."""
    a,b=deepcopy(old),deepcopy(new)
    assert a['geometry_identity'].get('port_connection_model') is None
    assert b['geometry_identity']['port_connection_model']==SCHEMA
    assert b['base_configuration_schema']==a['schema']
    assert b['schema']=='MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V7'
    for c in (a,b):
        assert not c['geometry_identity'].get('spatial_reconstruction_model')
        c.pop('base_configuration_schema',None)
        c.pop('schema')
        c['geometry_identity'].pop('port_connection_model',None)
    assert a==b, 'additional physics or numerical configuration changed'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=default_artifact_root()/'port-flow-verification-v1-20261028')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    check_storage_requirements([(args.output,1024**2)])
    if args.output.exists():
        raise FileExistsError('preserve prior analysis')
    old,oc=reduce_case(args.root/'legacy')
    new,nc=reduce_case(args.root/'candidate')
    assert_matched_configurations(oc,nc)
    initial=[]
    for name in ('legacy','candidate'):
        s=json.loads((args.root/name/'initial-checkpoint.json').read_text(encoding='utf-8'))
        initial.append(s['state'])
    assert initial[0]==initial[1], 'initial physical fields differ'
    assert [x['angle_deg'] for x in old['trapped_at_exhaust_closing']]==[
        x['angle_deg'] for x in new['trapped_at_exhaust_closing']]
    summary=dict(schema='DINO_PORT_FLOW_INTEGRATED_IMPACT_V1',cases=[old,new],
        identical_physics_except_explicit_connection=True,identical_initial_fields=True,
        same_trapped_comparison_phases=True,spatial_order='FIRST_ORDER_LEGACY',
        independent_initialization=True, review='SELF_REVIEW',
        source_hashes={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    columns=['model','location','forward_mg','reverse_mg','net_mg','energy_x_j']
    with args.output.with_suffix('.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for r in (old,new):
            for key,values in r['face_integrals'].items():
                writer.writerow(dict(model=r['model'],location=key,
                    forward_mg=values['forward_kg']*1e6,reverse_mg=values['reverse_kg']*1e6,
                    net_mg=values['net_kg']*1e6,energy_x_j=values['energy_x_j']))
    print(json.dumps(dict(phase_deg=720.,models=[r['model'] for r in (old,new)],
        compute_s=[r['compute_s'] for r in (old,new)],
        trapped_phases=[x['angle_deg'] for x in old['trapped_at_exhaust_closing']]),indent=2))


if __name__=='__main__':
    main()
