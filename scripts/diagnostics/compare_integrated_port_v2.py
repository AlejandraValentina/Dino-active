"""Compare bounded diagnostic receipts without running the engine."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.gas1d.eos import IdealGas
from scripts.agents.storage_preflight import check_storage_requirements


def terminal_differences(a,b,eos):
    """Relative positive states, velocity/sound, absolute species fractions.

    Do not normalize a near-zero momentum or species inventory by itself.
    The fourth legacy Euler entry is a redundant density proxy, not the P6
    authoritative species. Use actual extensive species in the separate map.
    """
    values=[]
    for name,qa in a['chambers'].items():
        qb=b['chambers'][name]
        for i,label in enumerate(('mass','internal_energy','volume')):
            values.append((abs(qa[i]-qb[i])/max(abs(qa[i]),abs(qb[i])),f'{name}/{label}'))
    for name,rows in a['ducts'].items():
        for i,(qa,qb) in enumerate(zip(rows,b['ducts'][name])):
            wa=eos.primitive((*qa[:3],qa[0]));wb=eos.primitive((*qb[:3],qb[0]))
            for k,label in [(0,'density'),(2,'pressure')]:
                values.append((abs(wa[k]-wb[k])/max(wa[k],wb[k]),f'{name}/{i}/{label}'))
            ta,tb=wa[2]/wa[0],wb[2]/wb[0]
            values.append((abs(ta-tb)/max(ta,tb),f'{name}/{i}/temperature'))
            values.append((abs(wa[1]-wb[1])/max(eos.sound_speed(wa),eos.sound_speed(wb)),f'{name}/{i}/velocity_over_sound'))
    def fractions(sa,sb,path):
        for i in range(4):
            values.append((abs(sa[i]/sum(sa)-sb[i]/sum(sb)),f'{path}/fraction/{i}'))
    for name,sa in a['species']['chambers'].items():
        fractions(sa,b['species']['chambers'][name],name)
    for name,rows in a['species']['ducts'].items():
        for i,(sa,sb) in enumerate(zip(rows,b['species']['ducts'][name])):
            fractions(sa,sb,f'{name}/{i}')
    return sorted(values,reverse=True)


def compare(root):
    paths=[root/name/'receipt.json' for name in ('integrated-legacy-observer-fixed',
        'integrated-nozzle-final','integrated-nozzle-refined')]
    old,new,fine=[json.loads(p.read_text(encoding='utf-8')) for p in paths]
    configs=[json.loads((p.parent/'configuration.json').read_text(encoding='utf-8')) for p in paths]
    # Differences in physics are explicit, limited to the selected connection.
    physical=[json.loads(json.dumps(c)) for c in configs]
    for c in physical:
        c['geometry_identity'].pop('port_connection_model',None)
    if physical[0]!=physical[1] or physical[1]!=physical[2]:
        raise ValueError('diagnostic input difference beyond authorized connection')
    if any(r['terminal_angle_deg']!=720. for r in (old,new,fine)):
        raise ValueError('terminal crank phases differ')
    e=IdealGas(**configs[0]['eos'])
    errors=terminal_differences(new['final_state'],fine['final_state'],e)
    changes={}
    for label,r in [('legacy',old),('nozzle_coarse',new),('nozzle_refined',fine)]:
        ledger=r['final_ledger']
        changes[label]=dict(cylinder_work_out_J=-ledger['cylinder_work_J'],
            crankcase_work_out_J=-ledger['crankcase_work_J'],
            net_indicated_work_out_J=-ledger['cylinder_work_J']-ledger['crankcase_work_J'],
            fuel_combustion_heat_J=ledger['fuel_combustion_heat_added_J'],
            cylinder_species_kg=r['final_state']['species']['chambers']['cylinder'],
            maximum_pressures_pa={k:v for k,v in r['maxima'].items() if 'pressure' in k},
            mass_flux_integrals=r['mass_flux_integrals'],
            compute_s=r['compute_s'],wall_s=r['wall_s'],steps=r['accepted_steps'])
    return dict(schema='DINO_INTEGRATED_PORT_V2_COMPARISON',
        numerical_gate=all(r['numerical_gate'] for r in (old,new,fine)),
        temporal_gate=errors[0][0]<=.01,maximum_normalized_time_difference=errors[0][0],
        largest_time_differences=errors[:12],physical_comparison=changes,
        source_receipts={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        phase_deg=0.,terminal_angle_deg=720.,independently_initialized=True,
        scientific_state='TRANSIENT_NOT_PERIODIC_POWER',review='SELF_REVIEW',
        unchanged_CFL_and_periodicity_tolerances=True,experimental_validation=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT/'results/predictive-reliability-v1')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    check_storage_requirements([(args.output.parent,1024**2)])
    result=compare(args.root)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('numerical_gate','temporal_gate','maximum_normalized_time_difference')},indent=2))
