"""Read-only spatial/temporal/material comparison of the pre-opening cases."""
import argparse
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load
from scripts.diagnostics.material_species_diagnostic_v1 import profile,exact_norms,cell_average_norms
from scripts.diagnostics.periodic88_material_labels_v1 import retained_interval
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states,norms
from scripts.diagnostics.compare_remap_representation_v1 import restrict_to
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write


def pressure_averages(state,source,target):
    """Separate volume-average pressure from pressure of filtered conserved q.

    The latter includes unresolved kinetic variance. Neither is pointwise
    pressure at the parent center; both definitions are reported explicitly.
    """
    result={};paths={p['id']:p for p in source['ducts']};gamma=source['eos']['gamma']
    for parent in target['ducts']:
        name=parent['id'];child=paths[name];v=np.asarray(child['mesh']['volumes']);vt=np.asarray(parent['mesh']['volumes']);q=np.asarray(state['ducts'][name]);n=len(vt)
        if len(v)%n:raise ValueError('non-nested pressure projection')
        ratio=len(v)//n
        if not np.allclose(child['mesh']['faces'][::ratio],parent['mesh']['faces'],rtol=0,atol=1e-14) or not np.allclose(v.reshape(n,ratio).sum(axis=1),vt,rtol=1e-12,atol=0):raise ValueError('pressure physical volumes differ')
        pressure=(gamma-1)*(q[:,2]-.5*q[:,1]**2/q[:,0])
        mean=(pressure*v).reshape(n,ratio).sum(axis=1)/vt
        qb=(q[:,:3]*v[:,None]).reshape(n,ratio,3).sum(axis=1)/vt[:,None]
        filtered=(gamma-1)*(qb[:,2]-.5*qb[:,1]**2/qb[:,0])
        result[name]=(mean,filtered-mean)
    return result


def common_material_bins(a,b,root_edges,lower,upper):
    """Weak cell-average comparison on identical original material volumes.

    No snapping, discarded intervals or tolerance relaxation. All material
    mass is integrated. Pointwise norms are retained separately.
    """
    edges=np.r_[lower,root_edges[(root_edges>lower)&(root_edges<upper)],upper]
    if not max(a[0][0],b[0][0])<=lower<upper<=min(a[0][-1],b[0][-1]):raise ValueError('common material bins outside retained states')
    def means(p):
        return np.array([np.dot(np.maximum(0.,np.minimum(p[0][1:],hi)-np.maximum(p[0][:-1],lo)),p[1])/(hi-lo) for lo,hi in zip(edges[:-1],edges[1:])])
    delta=means(a)-means(b);weights=np.diff(edges)
    return dict(cells=len(weights),covered_interval_kg=[float(lower),float(upper)],
        norms={label:norms(delta[:,k],weights) for k,label in enumerate(('fresh','fuel','residual','burned'))})


def matched_phases(a,b,ca,cb,target):
    if len(a)!=len(b):raise ValueError('phase count differs')
    rows=[]
    for fa,fb in zip(a,b):
        if fa['angle']!=fb['angle']:raise ValueError('physical phase differs')
        pa,pb=pressure_averages(fa['state'],ca,target),pressure_averages(fb['state'],cb,target)
        averaged={}
        for path in target['ducts']:
            name=path['id'];ma,ba=pa[name];mb,bb=pb[name];v=path['mesh']['volumes']
            averaged[name]=dict(direct_volume_mean_relative_difference=norms((ma-mb)/np.maximum(ma,mb),v),
                conserved_filter_pressure_bias_a=norms(ba/ma,v),conserved_filter_pressure_bias_b=norms(bb/mb,v))
        rows.append(dict(phase_deg=fa['angle']-13680.,fields=compare_states(restrict_to(fa['state'],ca,target),restrict_to(fb['state'],cb,target),target),pressure_volume_average=averaged))
    return rows


def analyze(root):
    out=root/'preopen-wave-transport-run-v1/run';run=load(out/'receipt.json')
    manifest=load(out.parent/'input-manifest.json')
    for name,expected in manifest['files'].items():
        if sha(out.parent/name)!=expected:raise ValueError('completed input evidence differs: '+name)
    names=[c['name'] for c in run['cases'] if c['status']=='COMPLETE']
    required=['p0-88','p0-176','p0-352','p0-176-timehalf']
    if not all(n in names for n in required):raise ValueError('spatial/temporal cases incomplete')
    receipts={n:load(out/n/'receipt.json') for n in names};configs={n:load(out/n/'configuration.json') for n in names}
    frames={n:load(out/n/'frames.json') for n in names};coarse=configs['p0-88'];initial={};final={};intervals=[]
    for n in names:
        f=receipts[n]['interfaces']['exhaust'];initial[n]=profile(frames[n][0]['state'],configs[n]);final[n]=profile(frames[n][-1]['state'],configs[n],f['left']['gas_net'][0])
        if f['left']['gas_net'][0]!=0. or f['left']['gas_positive'][0]!=0. or f['left']['gas_negative'][0]!=0.:raise ValueError('closed exhaust isolation failed')
        intervals.append(retained_interval(initial[n][0][-1],f['left']['gas_negative'][0],f['right']['gas_positive'][0]))
    lower=max(t[0] for t in intervals);upper=min(t[1] for t in intervals);cases={}
    for n in names:
        r=receipts[n];f=r['interfaces']['exhaust'];steps=[row['angle_end_deg']-row['angle_start_deg'] for row in load(out/n/'recipe.json')]
        material=[]
        for frame in frames[n]:
            p=profile(frame['state'],configs[n]) # F_left is identically zero by stage guard.
            material.append(dict(phase_deg=frame['angle']-13680.,common_original88_material_bin_change=common_material_bins(initial[n],p,initial['p0-88'][0],lower,upper),piecewise_constant_marker_change=exact_norms(initial[n],p,lower,upper),
                marker_cell_average_change=cell_average_norms(p,initial[n],lower,upper)))
        # Fixed label windows correspond to original88 material, not final x.
        mesh=next(p['mesh'] for p in coarse['ducts'] if p['id']=='exhaust');x=np.asarray(mesh['centers']);regions=[]
        for lo,hi in ((0.,.2),(.2,.4),(.4,.8),(.8,mesh['faces'][-1])):
            indices=np.where((x>=lo)&(x<hi))[0];left=max(lower,initial['p0-88'][0][indices[0]]);right=min(upper,initial['p0-88'][0][indices[-1]+1])
            row=dict(original88_position_bin_m=[lo,hi],material_interval_kg=[float(left),float(right)])
            if left<right:
                try:row['cell_average_change']=cell_average_norms(final[n],initial[n],left,right)
                except ValueError as exc:row['not_evaluated']=str(exc)
            else:row['not_evaluated']='no safe retained material'
            regions.append(row)
        cases[n]=dict(wall_s=r['wall_s'],steps=r['accepted_steps'],rejected_proposals=r['rejected_proposals'],
            actual_step_degrees=dict(minimum=min(steps),median=float(np.median(steps)),maximum=max(steps)),
            outlet=dict(gross_out_kg=f['right']['gas_positive'][0],gross_in_kg=-f['right']['gas_negative'][0],net_kg=f['right']['gas_net'][0],
                net_species_kg=f['right']['species_net'],net_total_energy_J=f['right']['gas_net'][2]),
            phase_material_marker_change=material,material_regions=regions,
            initial_vs_final_eulerian_fields=compare_states(frames[n][0]['state'],frames[n][-1]['state'],configs[n]),
            max_cell_balance_residual=r['exhaust_cell_balances']['maximum_normalized_residual'],partial_arc_work_J=r['partial_arc_work_J'],
            receipt_sha256=sha(out/n/'receipt.json'))
    pairs=[('spatial88_176','p0-88','p0-176'),('spatial176_352','p0-176','p0-352'),('temporal176','p0-176','p0-176-timehalf')]
    if 'p1-176' in names:pairs.append(('initial_representation176','p0-176','p1-176'))
    comparisons={}
    for label,a,b in pairs:
        comparisons[label]=dict(common88=matched_phases(frames[a],frames[b],configs[a],configs[b],coarse),
            material_final_common_original88_bins=common_material_bins(final[a],final[b],initial['p0-88'][0],lower,upper),
            material_initial_common_original88_bins=common_material_bins(initial[a],initial[b],initial['p0-88'][0],lower,upper),
            material_final_common_interval=exact_norms(final[a],final[b],lower,upper),
            initial_material_common_interval=exact_norms(initial[a],initial[b],lower,upper),
            outlet_gross_out_difference_kg=cases[b]['outlet']['gross_out_kg']-cases[a]['outlet']['gross_out_kg'],
            outlet_gross_out_relative_difference=abs(cases[b]['outlet']['gross_out_kg']-cases[a]['outlet']['gross_out_kg'])/max(cases[a]['outlet']['gross_out_kg'],cases[b]['outlet']['gross_out_kg']))
    reference=load(root/'preopen-wave-transport-v1/preparation-verified/receipt.json')['original_recorded_reference']
    original=[row['frame'] for row in reference];computed=[f for f in frames['p0-88'] if f['angle'] in [row['frame']['angle'] for row in reference]]
    original_flux=load(root/'periodic88-front-flux-v1/run/receipt.json')
    gross_original=sum(w['interfaces']['exhaust']['right']['gas_positive'][0] for w in original_flux['phase_windows'] if w['phase_end_deg']<=60.)
    original_comparison=dict(fields=matched_phases(original,computed,coarse,coarse,coarse),
        original_outlet_gross_out_kg=gross_original,refined_time_outlet_gross_out_kg=cases['p0-88']['outlet']['gross_out_kg'])
    return dict(schema='PREOPEN_WAVE_TRANSPORT_ANALYSIS_V2_COMMON_MATERIAL_BINS',run_status=run['status'],run_wall_s=run['wall_s'],cases=cases,comparisons=comparisons,
        original88_vs_reduced_step=original_comparison,input_manifest_sha256=sha(out.parent/'input-manifest.json'),common_retained_material_interval_kg=[float(lower),float(upper)],
        common_retained_fraction=float((upper-lower)/initial['p0-88'][0][-1]),solver_steps=0,runner_sha256=sha(Path(__file__)),
        qualification='Finite transient window of recorded39, source-free markers in exhaust, no new periodic cycle. Material norms include subcell/gas evolution errors; complete-cell coverage differs and is reported. No periodic mesh independence, asymptotic order, GCI or experimental claim.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve analysis')
    r=analyze(a.root);write(a.output,r);print({n:dict(out_mg=c['outlet']['gross_out_kg']*1e6,burned_L1=c['phase_material_marker_change'][-1]['marker_cell_average_change']['norms']['burned']['L1']) for n,c in r['cases'].items()})
