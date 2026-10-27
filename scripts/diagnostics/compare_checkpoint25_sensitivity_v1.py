"""Volume-weighted, phase-matched numerical differences, not exact errors."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.gas1d.eos import IdealGas
from scripts.diagnostics.diagnose_integrated_mesh_v1 import restrict_state,sha,write


def norms(values,weights):
    a=np.abs(values);w=np.array(weights)/sum(weights)
    return dict(L1=float(np.dot(a,w)),L2=float(np.sqrt(np.dot(a*a,w))),Linf=float(max(a)))


def compare_states(a,b,config):
    e=IdealGas(**config['eos']);result={}
    for path in config['ducts']:
        name=path['id'];v=path['mesh']['volumes']
        wa=np.array([e.primitive((*q[:3],q[0]))[:3] for q in a['ducts'][name]])
        wb=np.array([e.primitive((*q[:3],q[0]))[:3] for q in b['ducts'][name]])
        sa=np.array(a['species']['ducts'][name]);sb=np.array(b['species']['ducts'][name])
        ya=sa/sa.sum(axis=1)[:,None];yb=sb/sb.sum(axis=1)[:,None]
        metrics={'density_relative':(wa[:,0]-wb[:,0])/np.maximum(wa[:,0],wb[:,0]),'pressure_relative':(wa[:,2]-wb[:,2])/np.maximum(wa[:,2],wb[:,2]),
                 'velocity_over_sound':(wa[:,1]-wb[:,1])/np.sqrt(e.gamma*np.maximum(wa[:,2]/wa[:,0],wb[:,2]/wb[:,0]))}
        for k,key in enumerate(('fresh','fuel','residual','burned')):metrics[key+'_absolute_fraction']=ya[:,k]-yb[:,k]
        result[name]={key:norms(d,v) for key,d in metrics.items()}
    return result


def run(root):
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    names=['coarse05','coarse025','fine025']+(['fine05'] if (root/'fine05/receipt.json').exists() else [])
    if (root/'fine0125/receipt.json').exists():names.append('fine0125')
    configs={n:load(root/n/'configuration.json') for n in names}
    frames={n:load(root/n/'frames.json') for n in names};receipts={n:load(root/n/'receipt.json') for n in names}
    if any(r['status']!='COMPLETE' for r in receipts.values()):raise ValueError('incomplete case')
    if any(r['source_checkpoint_sha256']!=receipts['coarse05']['source_checkpoint_sha256'] or
           r['solver_dependency_sha256']!=receipts['coarse05']['solver_dependency_sha256'] for r in receipts.values()):
        raise ValueError('different source state or solver dependency')
    result=dict(schema='DINO_CHECKPOINT25_SENSITIVITY_COMPARISON_V1',comparisons={},receipts_sha256={n:sha(root/n/'receipt.json') for n in names})
    pairs=[('temporal44','coarse05','coarse025'),('spatial_at025','coarse025','fine025')]
    if 'fine05' in names:pairs += [('CFL_collapsed_cap_contrast88','fine05','fine025'),('spatial_at05','coarse05','fine05')]
    if 'fine0125' in names:pairs += [('temporal88_actual_halving','fine025','fine0125')]
    for label,na,nb in pairs:
        rows=[]
        for a,b in zip(frames[na],frames[nb]):
            if a['angle']!=b['angle']:raise ValueError('phase mismatch')
            state=restrict_state(b['state'],configs[nb],configs[na]) if len(b['state']['ducts']['exhaust'])!=len(a['state']['ducts']['exhaust']) else b['state']
            rows.append(dict(angle=a['angle'],fields=compare_states(a['state'],state,configs[na])))
        fluxes={}
        for name,ends in receipts[na]['interfaces'].items():
            fluxes[name]={side:{key:dict(a=ends[side][key],b=receipts[nb]['interfaces'][name][side][key],absolute_difference=abs(ends[side][key]-receipts[nb]['interfaces'][name][side][key])) for key in ('positive_mass','negative_mass')} for side in ('left','right')}
        result['comparisons'][label]=dict(phases=rows,work_difference_J=receipts[nb]['work_J']-receipts[na]['work_J'],
            work_relative_difference=abs(receipts[nb]['work_J']-receipts[na]['work_J'])/max(abs(receipts[na]['work_J']),abs(receipts[nb]['work_J'])),
            imep_difference_bar=receipts[nb]['imep_bar']-receipts[na]['imep_bar'],interface_gross_mass_differences=fluxes,
            final_inventory_a=receipts[na]['final_inventory'],final_inventory_b=receipts[nb]['final_inventory'])
    f=frames['coarse025']
    result['same_mesh_one_cycle_evolution']=compare_states(f[0]['state'],f[-1]['state'],configs['coarse025'])
    result['qualification']='Differences include truncation and remap-induced adjustment; neither transient solution is an exact reference. No periodicity or mesh independence.'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve comparison')
    r=run(a.root);write(a.output,r)
    print(json.dumps({k:dict(work_rel=v['work_relative_difference'],exhaust_final=v['phases'][-1]['fields']['exhaust']) for k,v in r['comparisons'].items()}))
