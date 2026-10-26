"""Physical comparison of preregistered first-order/MUSCL engine diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.gas1d.eos import IdealGas
from scripts.diagnostics.compare_integrated_port_v2 import terminal_differences
from scripts.agents.storage_preflight import check_storage_requirements


def compare(root):
    names=['spatial-first-order-reference','spatial-muscl-coarse','spatial-muscl-refined']
    receipts=[json.loads((root/name/'receipt.json').read_text(encoding='utf-8')) for name in names]
    configs=[json.loads((root/name/'configuration.json').read_text(encoding='utf-8')) for name in names]
    canonical=[]
    for c in configs:
        c=json.loads(json.dumps(c))
        c['schema']=c.pop('base_configuration_schema',c['schema'])
        c['geometry_identity'].pop('spatial_reconstruction_model',None)
        canonical.append(c)
    if canonical[0]!=canonical[1] or canonical[1]!=canonical[2]:
        raise ValueError('unauthorized input difference beyond spatial capability')
    if any(r['terminal_angle_deg']!=720. for r in receipts):
        raise ValueError('terminal phases differ')
    reference=json.loads((root/'integrated-nozzle-final/receipt.json').read_text(encoding='utf-8'))
    unchanged=(reference['final_state']==receipts[0]['final_state'] and
               reference['final_ledger']==receipts[0]['final_ledger'])
    e=IdealGas(**configs[0]['eos'])
    errors=terminal_differences(receipts[1]['final_state'],receipts[2]['final_state'],e)
    physical={}
    for name,r in zip(names,receipts):
        ledger=r['final_ledger']
        physical[name]=dict(cylinder_work_out_J=-ledger['cylinder_work_J'],
            crankcase_work_out_J=-ledger['crankcase_work_J'],
            net_indicated_work_out_J=-ledger['cylinder_work_J']-ledger['crankcase_work_J'],
            fuel_combustion_heat_J=ledger['fuel_combustion_heat_added_J'],
            cylinder_species_kg=r['final_state']['species']['chambers']['cylinder'],
            maxima=r['maxima'],rejections=r['rejections'],compute_s=r['compute_s'],
            wall_s=r['wall_s'],accepted_steps=r['accepted_steps'],
            mass_flux_integrals=r['mass_flux_integrals'])
    return dict(schema='DINO_INTEGRATED_SPATIAL_V1_COMPARISON',
        numerical_gate=all(r['numerical_gate'] for r in receipts),
        temporal_gate=errors[0][0]<=.01,disabled_reconstruction_is_bit_identical=unchanged,
        maximum_normalized_time_difference=errors[0][0],largest_time_differences=errors[:12],
        source_receipts={name:hashlib.sha256((root/name/'receipt.json').read_bytes()).hexdigest() for name in names},
        physical_comparison=physical,scientific_state='TRANSIENT_NOT_PERIODIC_POWER',
        experimental_validation=False,mesh_independence_claimed=False,review='SELF_REVIEW')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT/'results/predictive-reliability-v1')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    check_storage_requirements([(args.output.parent,1024**2)])
    result=compare(args.root)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('numerical_gate','temporal_gate',
        'disabled_reconstruction_is_bit_identical','maximum_normalized_time_difference')},indent=2))
