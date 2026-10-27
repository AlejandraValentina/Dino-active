"""Algebraic sensitivity of saved material-label comparison to subcell markers."""
import argparse
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.material_species_diagnostic_v1 import profile
from scripts.diagnostics.periodic88_material_labels_v1 import analyze as source_analysis
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def bounded_slopes(edges,means):
    """Shared limiter preserves four-component closure and original mass means.

    Diagnostic reconstruction in mass coordinate, not the solver limiter.
    No assumed exterior data: endpoint slopes are zero.
    """
    edges=np.asarray(edges);means=np.asarray(means);mid=.5*(edges[:-1]+edges[1:]);slopes=np.zeros_like(means)
    for i in range(1,len(means)-1):
        gradient=(means[i+1]-means[i-1])/(mid[i+1]-mid[i-1]);gradient[-1]=-sum(gradient[:-1])
        lower=np.maximum(0.,np.minimum.reduce(means[i-1:i+2]));upper=np.minimum(1.,np.maximum.reduce(means[i-1:i+2]));theta=1.
        for face in (edges[i],edges[i+1]):
            delta=gradient*(face-mid[i])
            for k in range(4):
                if delta[k]>0:theta=min(theta,max(0.,(upper[k]-means[i,k])/delta[k]))
                elif delta[k]<0:theta=min(theta,max(0.,(lower[k]-means[i,k])/delta[k]))
        slopes[i]=theta*gradient
    return slopes


def average(edges,means,slopes,lower,upper):
    if not edges[0]<=lower<upper<=edges[-1]:raise ValueError('interval outside initial material')
    mid=.5*(edges[:-1]+edges[1:]);result=np.zeros(4)
    for i in range(len(means)):
        lo=max(lower,edges[i]);hi=min(upper,edges[i+1])
        if hi>lo:result+=(hi-lo)*means[i]+.5*((hi-mid[i])**2-(lo-mid[i])**2)*slopes[i]
    return result/(upper-lower)


def norms(delta,weights):
    weights=np.asarray(weights)/sum(weights);delta=abs(np.asarray(delta))
    return {name:dict(L1=float(np.dot(weights,delta[:,k])),L2=float(np.sqrt(np.dot(weights,delta[:,k]**2))),Linf=float(max(delta[:,k]))) for k,name in enumerate(('fresh','fuel','residual','burned'))}


def analyze(root):
    base=source_analysis(root);src=root/'periodic88-window2-v1/run';config=load(src/'configuration.json')
    initial=profile(load(src/'checkpoint-absolute-038.json')['state'],config);flux=load(root/'periodic88-front-flux-v1/run/receipt.json')['interfaces']['exhaust']
    final=profile(load(src/'checkpoint-absolute-039.json')['state'],config,flux['left']['gas_net'][0]);edges,means=initial
    slopes=bounded_slopes(edges,means);zero=np.zeros_like(slopes)
    preservation=max(float(max(abs(average(edges,means,slopes,edges[i],edges[i+1])-means[i]))) for i in range(len(means)))
    mids=.5*(edges[:-1]+edges[1:]);faces=np.array([means+slopes*(edges[:-1]-mids)[:,None],means+slopes*(edges[1:]-mids)[:,None]])
    if preservation>1e-12 or faces.min()<-1e-12 or faces.max()>1+1e-12 or np.max(abs(faces.sum(axis=2)-1))>1e-12:raise ValueError('initial diagnostic reconstruction inadmissible')
    regions=[('all_retained',base['all_retained'])]+[(str(r['original_position_bin_m']),r['comparison']) for r in base['regions'] if 'comparison' in r];rows=[]
    for name,region in regions:
        selected=region['final_cell_indices'];weights=[];p0=[];p1=[];actual=[]
        for i in selected:
            lo,hi=final[0][i:i+2];weights.append(hi-lo);p0.append(average(edges,means,zero,lo,hi));p1.append(average(edges,means,slopes,lo,hi));actual.append(final[1][i])
        p0,p1,actual=map(np.asarray,(p0,p1,actual))
        rows.append(dict(region=name,cells=len(selected),material_mass_kg=float(sum(weights)),P0_reference_marker_change=norms(actual-p0,weights),
            P1_reference_marker_change=norms(actual-p1,weights),P1_vs_P0_reference_change=norms(p1-p0,weights)))
    return dict(schema='PERIODIC88_MATERIAL_REFERENCE_SENSITIVITY_V1',solver_steps=0,regions=rows,
        initial_cell_mean_preservation_max_abs=preservation,initial_reconstructed_face_min=float(faces.min()),initial_reconstructed_face_max=float(faces.max()),
        initial_reconstructed_face_species_closure_max_abs=float(np.max(abs(faces.sum(axis=2)-1))),
        source_checkpoint_sha256=base['source_checkpoint_sha256'],source_flux_receipt_sha256=base['source_flux_receipt_sha256'],runner_sha256=sha(Path(__file__)),
        qualification='Diagnostic initial subcell reference only; same conservative marker means. Does not change MUSCL, solver, checkpoints, detector or physics. P0/P1 agreement is not a bound on unresolved subcell structure or exact Euler error.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve diagnostic')
    preflight=check_storage_requirements([(a.output,256*1024)]);r=analyze(a.root);r['storage_preflight']=preflight
    a.output.parent.mkdir(parents=True,exist_ok=True);write(a.output,r);print([(v['region'],v['P0_reference_marker_change']['burned']['L1'],v['P1_reference_marker_change']['burned']['L1']) for v in r['regions']])
