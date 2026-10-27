"""Compare the single declared352 control to preserved176 references."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal
from motorsim.gas1d.eos import IdealGas
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states,norms
from scripts.diagnostics.compare_remap_representation_v1 import restrict_to,profile_metrics
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.diagnostics.material_species_diagnostic_v1 import profile,exact_norms,cell_average_norms


def load(p):return json.loads(p.read_text(encoding='utf-8'))


def analyze(root,previous):
    paths={'176':previous/'p0-176','176-half':previous/'p0-176-timehalf','352':root/'p0-352'}
    configs={n:load(p/'configuration.json') for n,p in paths.items()};frames={n:load(p/'frames.json') for n,p in paths.items()};receipts={n:load(p/'receipt.json') for n,p in paths.items()}
    if any(r['source_checkpoint_sha256']!=receipts['176']['source_checkpoint_sha256'] or r['solver_dependency_sha256']!=receipts['176']['solver_dependency_sha256'] for r in receipts.values()):raise ValueError('incompatible sources')
    coarse=load(previous/'p0-44/configuration.json');result=dict(schema='BOUNDED352_REFINEMENT_COMPARISON_V1',status=receipts['352']['status'],comparisons={},cases={})
    for a,b in [('176','176-half'),('176-half','352'),('176','352')]:
        rows=[];other={f['angle']:f for f in frames[b]}
        for f in frames[a]:
            if f['angle'] not in other:continue
            g=other[f['angle']];rows.append(dict(angle=f['angle'],common44=compare_states(restrict_to(f['state'],configs[a],coarse),restrict_to(g['state'],configs[b],coarse),coarse),
                common176=compare_states(f['state'],restrict_to(g['state'],configs[b],configs[a]),configs[a])))
        result['comparisons'][a+'__'+b]=rows
    for n,p in paths.items():
        r=receipts[n];c=configs[n];f=frames[n];recipe=load(p/'recipe.json');steps=np.array([q['angle_end_deg']-q['angle_start_deg'] for q in recipe])
        record=dict(receipt_sha256=sha(p/'receipt.json'),wall_s=r['wall_s'],initialization=r['initialization'],steps=dict(count=len(steps),median_deg=float(np.median(steps)),max_deg=float(max(steps))),
            profiles=[dict(angle=q['angle'],ducts=profile_metrics(q['state'],c)) for q in f],conservation=r['conservation'])
        if r['status']=='COMPLETE':
            cp=load(p/'terminal-checkpoint.json');engine=IntegratedEngine2T.from_configuration_dict(c);engine.restore(cp)
            if not _json_evidence_equal(engine.state,cp['state']) or not _json_evidence_equal(engine.ledger,cp['ledger']):raise ValueError('restore mismatch')
            balances={}
            for duct in c['ducts']:
                name=duct['id'];vol=np.array(duct['mesh']['volumes']);a=f[0]['state'];b=f[-1]['state'];ends=r['interfaces'][name]
                sdelta=np.array(b['species']['ducts'][name]).sum(axis=0)-np.array(a['species']['ducts'][name]).sum(axis=0)
                sres=sdelta-np.array(ends['left']['net'])+np.array(ends['right']['net'])
                mdelta=float(np.dot(vol,np.array(b['ducts'][name])[:,0]-np.array(a['ducts'][name])[:,0]))
                mflux=sum(ends['left'][k]-ends['right'][k] for k in ('positive_mass','negative_mass'))
                balances[name]=dict(species_residual_kg=sres.tolist(),mass_residual_kg=mdelta-mflux)
            record.update(work_J=r['work_J'],imep_bar=r['imep_bar'],interfaces=r['interfaces'],balances=balances,native_restore_exact=True)
        result['cases'][n]=record
    if result['status']=='COMPLETE':
        gas=IdealGas(**coarse['eos']);mesh=next(d['mesh'] for d in coarse['ducts'] if d['id']=='exhaust');pressure={};cons={}
        for n in ('176-half','352'):
            c=configs[n];state=frames[n][-1]['state'];m=next(d['mesh'] for d in c['ducts'] if d['id']=='exhaust');ratio=len(m['volumes'])//len(mesh['volumes'])
            p=np.array([gas.primitive((*q[:3],q[0]))[2] for q in state['ducts']['exhaust']]);v=np.array(m['volumes'])
            pressure[n]=(p*v).reshape(-1,ratio).sum(axis=1)/np.array(mesh['volumes'])
            q=restrict_to(state,c,coarse)['ducts']['exhaust'];cons[n]=np.array([gas.primitive((*row[:3],row[0]))[2] for row in q])
        result['pressure_mean_projection_check']=dict(direct_mean_pressure=norms((pressure['176-half']-pressure['352'])/np.maximum(pressure['176-half'],pressure['352']),mesh['volumes']),
            pressure_from_conserved_means=norms((cons['176-half']-cons['352'])/np.maximum(cons['176-half'],cons['352']),mesh['volumes']))
        profiles={};initial={};reversed_mass=[]
        for n in ('176-half','352'):
            r=receipts[n];ends=r['interfaces']['exhaust']
            if ends['right']['negative_mass']!=0.:break
            profiles[n]=profile(frames[n][-1]['state'],configs[n],ends['left']['positive_mass']+ends['left']['negative_mass'])
            initial[n]=profile(frames[n][0]['state'],configs[n]);reversed_mass.append(-ends['left']['negative_mass'])
        if len(profiles)==2:
            lower=max(reversed_mass);upper=min(p[0][-1] for p in profiles.values())
            result['retained_material']=dict(interval_kg=[lower,upper],intergrid=exact_norms(profiles['176-half'],profiles['352'],lower,upper),
                original_marker_change={n:exact_norms(initial[n],p,lower,upper) for n,p in profiles.items()},
                original_cell_average_marker_change={n:cell_average_norms(p,initial[n],lower,upper) for n,p in profiles.items()})
    result['qualification']='One transient cycle. No exact solution, periodicity, GCI, model adoption or experimental validation. Primary contrast176-half/352 matches actual time cap; reference temporal176 does not rigorously bound time error352.'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve evidence')
    result=analyze(a.root,a.previous);write(a.output,result);print(json.dumps(dict(status=result['status'],cases={n:{k:c.get(k) for k in ('wall_s','work_J','imep_bar','steps')} for n,c in result['cases'].items()})))
