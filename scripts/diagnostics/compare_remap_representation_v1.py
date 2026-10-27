"""Phase/volume matched analysis of the preregistered representation diagnostic."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states
from scripts.diagnostics.diagnose_integrated_mesh_v1 import restrict_state,sha,write
from motorsim.gas1d.eos import IdealGas


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def profile_metrics(state,config):
    answer={};gas=IdealGas(**config['eos'])
    for path in config['ducts']:
        name=path['id'];mesh=path['mesh'];x=np.array(mesh['centers']);v=np.array(mesh['volumes'])
        s=np.array(state['species']['ducts'][name]);q=np.array(state['ducts'][name]);y=s/s.sum(axis=1)[:,None]
        values={}
        for k,label in enumerate(('fresh','fuel','residual','burned')):
            gradient=np.diff(y[:,k])/np.diff(x);maximum=float(max(abs(gradient)))
            crossings={str(level):[float(x[i]+(level-y[i,k])/(y[i+1,k]-y[i,k])*(x[i+1]-x[i]))
                for i in range(len(x)-1) if (y[i,k]-level)*(y[i+1,k]-level)<0] for level in (.1,.5,.9)}
            values[label]=dict(inventory_kg=float(s[:,k].sum()),centroid_m=float(np.dot(x,s[:,k])/s[:,k].sum()) if s[:,k].sum()>0 else None,
                minimum=float(min(y[:,k])),maximum=float(max(y[:,k])),crossings_m=crossings,
                max_gradient_per_m=maximum,max_gradient_position_m=float((x[np.argmax(abs(gradient))]+x[np.argmax(abs(gradient))+1])/2),
                total_variation=float(sum(abs(np.diff(y[:,k])))),variation_over_peak_gradient_m=float(sum(abs(np.diff(y[:,k])))/maximum) if maximum else None)
        pressure=np.array([gas.primitive((*row[:3],row[0]))[2] for row in q])
        answer[name]=dict(mass_kg=float(np.dot(v,q[:,0])),energy_J=float(np.dot(v,q[:,2])),species=values,
            pressure_volume_mean_Pa=float(np.dot(v,pressure)/sum(v)))
    return answer


def restrict_to(state,source,target):
    ns=len(source['ducts'][-1]['mesh']['volumes']);nt=len(target['ducts'][-1]['mesh']['volumes'])
    if ns==nt:return state
    # Actual stored intermediate configuration avoids assuming equal volumes.
    from scripts.diagnostics.remap_representation_v1 import configurations
    chain=configurations(target,2 if ns==nt*4 else 1)
    result=state
    for k in range(len(chain)-1,0,-1):result=restrict_state(result,chain[k],chain[k-1])
    return result


def analyze(root,reference):
    paths={n:root/n for n in ('p0-44','p1-88','p0-176','p1-176')};paths['p0-88']=reference
    if (root/'p0-176-timehalf/receipt.json').exists():paths['p0-176-timehalf']=root/'p0-176-timehalf'
    configs={n:load(p/'configuration.json') for n,p in paths.items()}
    receipts={n:load(p/'receipt.json') for n,p in paths.items()};frames={n:load(p/'frames.json') for n,p in paths.items()}
    if any(r['status']!='COMPLETE' for r in receipts.values()):raise ValueError('incomplete diagnostic')
    source=receipts['p0-44']
    if any(r['source_checkpoint_sha256']!=source['source_checkpoint_sha256'] or r['solver_dependency_sha256']!=source['solver_dependency_sha256'] for r in receipts.values()):raise ValueError('source mismatch')
    comparisons={}
    pairs=[('p0-44','p0-88'),('p0-88','p0-176'),('p0-44','p1-88'),('p1-88','p1-176'),('p0-88','p1-88'),('p0-176','p1-176')]
    if 'p0-176-timehalf' in paths:pairs.append(('p0-176','p0-176-timehalf'))
    for a,b in pairs:
        phases=[]
        for fa,fb in zip(frames[a],frames[b]):
            if fa['angle']!=fb['angle']:raise ValueError('phase mismatch')
            projected=restrict_to(fb['state'],configs[b],configs[a])
            phases.append(dict(angle=fa['angle'],fields=compare_states(fa['state'],projected,configs[a])))
        comparisons[a+'__'+b]=dict(phases=phases,work_difference_J=receipts[b]['work_J']-receipts[a]['work_J'],
            work_relative_difference=abs(receipts[b]['work_J']-receipts[a]['work_J'])/max(abs(receipts[b]['work_J']),abs(receipts[a]['work_J'])))
    common44={}
    for a,b in [('p0-44','p0-88'),('p0-88','p0-176'),('p0-44','p1-88'),('p1-88','p1-176')]:
        common44[a+'__'+b]=[dict(angle=fa['angle'],fields=compare_states(
            restrict_to(fa['state'],configs[a],configs['p0-44']),
            restrict_to(fb['state'],configs[b],configs['p0-44']),configs['p0-44'])) for fa,fb in zip(frames[a],frames[b])]
    cases={}
    for n,p in paths.items():
        r=receipts[n];recipe=load(p/'recipe.json');steps=np.array([row['angle_end_deg']-row['angle_start_deg'] for row in recipe])
        # recipe field names are checked explicitly; no inferred steps.
        balances={}
        for path in configs[n]['ducts']:
            name=path['id'];v=np.array(path['mesh']['volumes']);a=frames[n][0]['state'];b=frames[n][-1]['state']
            sa=np.array(a['species']['ducts'][name]).sum(axis=0);sb=np.array(b['species']['ducts'][name]).sum(axis=0)
            ends=r['interfaces'][name]
            species_residual=sb-sa-np.array(ends['left']['net'])+np.array(ends['right']['net'])
            delta_mass=float(np.dot(v,np.array(b['ducts'][name])[:,0]-np.array(a['ducts'][name])[:,0]))
            flow_mass=sum(ends['left'][k]-ends['right'][k] for k in ('positive_mass','negative_mass'))
            balances[name]=dict(species_residual_kg=species_residual.tolist(),mass_residual_kg=delta_mass-flow_mass)
        cases[n]=dict(receipt_sha256=sha(p/'receipt.json'),path=p.as_posix(),work_J=r['work_J'],imep_bar=r['imep_bar'],wall_s=r['wall_s'],
            initialization=r['initialization'],interfaces=r['interfaces'],conservation=r['conservation'],initial_inventory=r['initial_inventory'],final_inventory=r['final_inventory'],
            duct_balances=balances,steps=dict(count=len(steps),minimum_deg=float(min(steps)),median_deg=float(np.median(steps)),maximum_deg=float(max(steps))),
            profiles=[dict(angle=f['angle'],ducts=profile_metrics(f['state'],configs[n]),interfaces=f.get('interfaces')) for f in frames[n]])
    return dict(schema='REMAP_REPRESENTATION_COMPARISON_V1',cases=cases,comparisons=comparisons,common44=common44,solver_dependency_sha256=source['solver_dependency_sha256'],
        qualification='Transient differences; P1 is an unresolved-field hypothesis. No periodicity, exact error, asymptotic order, GCI or experimental claim.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve evidence')
    result=analyze(a.root,a.reference);write(a.output,result)
    print(json.dumps({n:dict(work_J=r['work_J'],steps=r['steps'],outlet_kg=r['interfaces']['exhaust']['right']['positive_mass']) for n,r in result['cases'].items()}))
