"""Read-only mass-label analysis, no solver modification.

For a source-free duct a(x,t)=integral_left^x rho*A dx - integral_0^t
mass_flux_left dt is a material label. Compare marker fractions in this
coordinate to separate compression/displacement from numerical mixing.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write


def profile(state,config,injected_mass=0.):
    mesh=next(p['mesh'] for p in config['ducts'] if p['id']=='exhaust')
    masses=np.array(mesh['volumes'])*np.array(state['ducts']['exhaust'])[:,0]
    edges=np.r_[0.,np.cumsum(masses)]-injected_mass
    fractions=np.array(state['species']['ducts']['exhaust'])/masses[:,None]
    return edges,fractions


def exact_norms(a,b,lower,upper):
    if not max(a[0][0],b[0][0])<=lower<upper<=min(a[0][-1],b[0][-1]):raise ValueError('nonoverlapping material interval')
    edges=np.unique(np.r_[lower,upper,a[0][(a[0]>lower)&(a[0]<upper)],b[0][(b[0]>lower)&(b[0]<upper)]])
    mid=(edges[1:]+edges[:-1])/2;weights=np.diff(edges)/(upper-lower)
    ya=a[1][np.searchsorted(a[0],mid,side='right')-1];yb=b[1][np.searchsorted(b[0],mid,side='right')-1]
    delta=np.abs(ya-yb)
    return {label:dict(L1=float(np.dot(weights,delta[:,k])),L2=float(np.sqrt(np.dot(weights,delta[:,k]**2))),Linf=float(max(delta[:,k])))
        for k,label in enumerate(('fresh','fuel','residual','burned'))}


def cell_average_norms(actual,initial,lower,upper):
    """Compare cell means to exact averages of the initial marker in mass label.

    Exclude cells crossing retained-window edges; report covered interval so
    differences in included physical mass are explicit.
    """
    selected=[i for i in range(len(actual[1])) if actual[0][i]>=lower and actual[0][i+1]<=upper]
    if not selected:raise ValueError('no complete retained cells')
    deltas=[];weights=[]
    for i in selected:
        lo,hi=actual[0][i:i+2];widths=np.maximum(0.,np.minimum(initial[0][1:],hi)-np.maximum(initial[0][:-1],lo))
        expected=np.dot(widths,initial[1])/(hi-lo)
        deltas.append(abs(actual[1][i]-expected));weights.append(hi-lo)
    weights=np.array(weights)/sum(weights);delta=np.array(deltas)
    return dict(covered_interval_kg=[float(actual[0][selected[0]]),float(actual[0][selected[-1]+1])],cells=len(selected),
        norms={label:dict(L1=float(np.dot(weights,delta[:,k])),L2=float(np.sqrt(np.dot(weights,delta[:,k]**2))),Linf=float(max(delta[:,k])))
               for k,label in enumerate(('fresh','fuel','residual','burned'))})


def analyze(root,reference):
    paths={'44':root/'p0-44','88':reference,'176':root/'p0-176'}
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    final={};initial={};reversals={};hashes={}
    for name,path in paths.items():
        config=load(path/'configuration.json');frames=load(path/'frames.json');r=load(path/'receipt.json')
        if r['status']!='COMPLETE':raise ValueError('incomplete reference')
        ends=r['interfaces']['exhaust']
        if ends['right']['negative_mass']!=0.:raise ValueError('retained-material proof requires no outlet inflow')
        inflow=ends['left']['positive_mass']+ends['left']['negative_mass']
        final[name]=profile(frames[-1]['state'],config,inflow);initial[name]=profile(frames[0]['state'],config)
        reversals[name]=-ends['left']['negative_mass'];hashes[name]=sha(path/'receipt.json')
    # Any initial material above the total gross leftward discharge cannot
    # have left/re-entered there, even if the unrecorded cumulative minimum
    # occurs between phase samples. No rightward re-entry in any SSP stage.
    lower=max(reversals.values());upper=min(p[0][-1] for p in final.values())
    retained={name:exact_norms(initial[name],state,lower,upper) for name,state in final.items()}
    all_lower=max(p[0][0] for p in final.values());all_upper=upper
    return dict(schema='SOURCE_FREE_DUCT_MATERIAL_LABEL_DIAGNOSTIC_V1',reference_sha256=hashes,
        retained_original_material_interval_kg=[lower,upper],common_interval_including_injected_gas_kg=[all_lower,all_upper],
        retained_original_marker_change=retained,
        retained_cell_average_marker_change={name:cell_average_norms(state,initial[name],lower,upper) for name,state in final.items()},
        intergrid_retained={a+'__'+b:exact_norms(final[a],final[b],lower,upper) for a,b in [('44','88'),('88','176')]},
        intergrid_including_injected={a+'__'+b:exact_norms(final[a],final[b],all_lower,all_upper) for a,b in [('44','88'),('88','176')]},
        qualification='Exact integrals of piecewise-constant diagnostic fields in mass label, not an exact Euler solution. Retained source markers have no physical reaction/mixing in this model. Differences include discretization. Injected/re-entered markers can differ through cylinder donor histories; do not treat their differences as pure transport error.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve diagnostic')
    result=analyze(a.root,a.reference);write(a.output,result);print(json.dumps(result))
