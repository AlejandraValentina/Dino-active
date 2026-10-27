"""Read-only material-label marker changes from the measured existing39 replay."""
import argparse
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.material_species_diagnostic_v1 import profile,exact_norms,cell_average_norms
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def retained_interval(initial_mass,left_negative_mass,right_positive_mass):
    """Safe original labels under arbitrary reversals at BOTH ends.

    a_left=-F_left(t) <= total gross leftward discharge;
    a_right=M0-F_right(t) >= M0-total gross rightward discharge.
    Material strictly between these bounds never crosses either boundary.
    """
    if initial_mass<=0 or left_negative_mass>0 or right_positive_mass<0:raise ValueError('invalid signed gross flow')
    lower=-left_negative_mass;upper=initial_mass-right_positive_mass
    if not 0<=lower<upper<=initial_mass:raise ValueError('no guaranteed retained original interval')
    return lower,upper


def matched_cell_comparison(initial,final,lower,upper):
    """Both norms use identical final cells/mass weights; no norm subtraction."""
    selected=[i for i in range(len(final[1])) if final[0][i]>=lower and final[0][i+1]<=upper]
    if not selected:raise ValueError('no complete retained cells')
    weights=np.array([final[0][i+1]-final[0][i] for i in selected]);weights/=sum(weights)
    delta=abs(final[1][selected]-initial[1][selected])
    eulerian={label:dict(L1=float(np.dot(weights,delta[:,k])),L2=float(np.sqrt(np.dot(weights,delta[:,k]**2))),Linf=float(max(delta[:,k]))) for k,label in enumerate(('fresh','fuel','residual','burned'))}
    material=cell_average_norms(final,initial,lower,upper)
    return dict(final_cell_indices=selected,material_aligned_cell_means=material,same_physical_cell_unaligned_marker_difference=eulerian,
        qualification='Mass-weighted marker differences, not volume-weighted periodicity errors. Alignment uses a piecewise-constant initial marker reconstructed from cell averages; residual includes numerical transport, subcell representation and approximate gas evolution. It is not an exact Euler error or pure physical mixing.')


def analyze(root):
    source=root/'periodic88-window2-v1';m=load(source/'manifest.json')
    def bound(name):
        if sha(source/name)!=m['files'][name]:raise ValueError('source changed')
        return load(source/name)
    config=bound('run/configuration.json');a=bound('run/checkpoint-absolute-038.json');b=bound('run/checkpoint-absolute-039.json')
    audit=root/'periodic88-front-flux-v1';am=load(audit/'manifest.json')
    if sha(audit/'run/receipt.json')!=am['files']['run/receipt.json']:raise ValueError('flux measurement changed')
    r=load(audit/'run/receipt.json')
    if r['status']!='PASS' or r['terminal_native_checkpoint_exact'] is not True or r['source_manifest_sha256']!=sha(source/'manifest.json'):raise ValueError('incompatible replay')
    flux=r['interfaces']['exhaust'];initial=profile(a['state'],config);final=profile(b['state'],config,flux['left']['gas_net'][0])
    lower,upper=retained_interval(initial[0][-1],flux['left']['gas_negative'][0],flux['right']['gas_positive'][0])
    result=dict(schema='PERIODIC88_RETAINED_MATERIAL_LABELS_V1',solver_steps=0,source_flux_receipt_sha256=sha(audit/'run/receipt.json'),
        source_checkpoint_sha256=[sha(source/'run/checkpoint-absolute-038.json'),sha(source/'run/checkpoint-absolute-039.json')],
        material_coordinate='a(x,t)=integral_left^x rho A dx - integral_start^t mass_flux_left dt',
        retained_original_interval_kg=[float(lower),float(upper)],retained_original_mass_fraction=float((upper-lower)/initial[0][-1]),
        all_retained=matched_cell_comparison(initial,final,lower,upper),piecewise_constant_pointwise_norms=exact_norms(initial,final,lower,upper),regions=[])
    mesh=next(p['mesh'] for p in config['ducts'] if p['id']=='exhaust');x=np.asarray(mesh['centers'])
    for lo,hi in ((0.,.2),(.2,.4),(.4,.8),(.8,mesh['faces'][-1])):
        indices=np.where((x>=lo)&(x<hi))[0]
        low=max(initial[0][indices[0]],lower);high=min(initial[0][indices[-1]+1],upper)
        row=dict(original_position_bin_m=[lo,hi],guaranteed_label_interval_kg=[float(low),float(high)])
        if low<high:
            try:row['comparison']=matched_cell_comparison(initial,final,low,high)
            except ValueError as exc:row['not_evaluated']=str(exc)
        else:row['not_evaluated']='no guaranteed retained material in this original-position bin'
        result['regions'].append(row)
    result['qualification']='No new simulation. Retention bounds account conservatively for gross reversals at both ends. Original-position bins identify where material began, not its final x. No reaction occurs in the duct; do not infer molecular mixing, a solver defect or an asymptotic spatial order from these finite-resolution differences.'
    result['runner_sha256']=sha(Path(__file__))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve diagnostic')
    preflight=check_storage_requirements([(a.output,256*1024)])
    r=analyze(a.root);r['storage_preflight']=preflight;a.output.parent.mkdir(parents=True,exist_ok=True)
    write(a.output,r);print({'retained_fraction':r['retained_original_mass_fraction'],'burned_cell_average_norms':r['all_retained']['material_aligned_cell_means']['norms']['burned']})
