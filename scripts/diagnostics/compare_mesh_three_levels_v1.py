"""Offline nested-mesh sensitivity; fitted order is not certified uncertainty."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.gas1d.eos import IdealGas
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.diagnose_integrated_mesh_v1 import (
    read_bound_reference,refined_configuration,restrict_state,sha,write)
from scripts.diagnostics.compare_integrated_port_v2 import terminal_differences


def scalar_trend(coarse,medium,fine):
    values=[coarse,medium,fine]
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
        raise ValueError('finite scalar observations required')
    d0,d1=medium-coarse,fine-medium
    scale=max(abs(x) for x in values)
    resolution=64*math.ulp(scale)
    result=dict(values=values,medium_minus_coarse=d0,fine_minus_medium=d1,
        resolution_indicator=resolution,ratio=None,fitted_order=None,
        conditional_extrapolation=None,certified_uncertainty=None)
    if abs(d0)<=resolution or abs(d1)<=resolution:
        result['classification']='RESOLUTION_LIMITED_OR_UNRESOLVED'
        return result
    ratio=d1/d0
    result['ratio']=ratio
    if ratio<=0:
        result['classification']=('OSCILLATORY_DECREASING' if abs(ratio)<1 else
                                  'OSCILLATORY_NONDECREASING')
    elif ratio>=1:
        result['classification']='MONOTONIC_NONDECREASING'
    else:
        result['classification']='MONOTONIC_DECREASING'
        p=-math.log(ratio)/math.log(2.)
        result['fitted_order']=p
        # Use expm1 to avoid cancellation for an observed order near zero.
        result['conditional_extrapolation']=fine+d1/math.expm1(p*math.log(2.))
    return result


def quantities(receipt):
    ledger=receipt['final_ledger'];state=receipt['final_state']
    report=receipt['conservation']
    q=dict(cylinder_work_out_J=-ledger['cylinder_work_J'],
        crankcase_work_out_J=-ledger['crankcase_work_J'],
        net_indicated_work_out_J=-(ledger['cylinder_work_J']+ledger['crankcase_work_J']),
        combustion_heat_J=ledger['fuel_combustion_heat_added_J'],
        heat_to_wall_J=ledger['heat_to_wall_J'],fresh_delivered_kg=ledger['fresh_delivered_kg'],
        fresh_short_circuit_kg=ledger['fresh_short_circuit_kg'],
        fuel_delivered_kg=ledger['fuel_delivered_kg'],fuel_short_circuit_kg=ledger['fuel_short_circuited_kg'],
        global_mass_kg=report['mass']['final'],global_energy_J=report['energy']['final'])
    for name,s in report['species'].items():q['global_species_'+name+'_kg']=s['final']
    for name,chamber in state['chambers'].items():
        q[name+'_mass_kg']=chamber[0];q[name+'_internal_energy_J']=chamber[1]
        for i,mass in enumerate(state['species']['chambers'][name]):
            q[f'{name}_species_{i}_kg']=mass
    return q


def compare(directories):
    refs=[read_bound_reference(p) for p in directories]
    receipts=[x[0] for x in refs]
    configs=[json.loads(x[1].read_text(encoding='utf-8')) for x in refs]
    for i in range(2):
        expected=refined_configuration(configs[i],sha(refs[i][1]))
        if expected!=configs[i+1]:raise ValueError('not the same conservative initial-configuration family')
    counts=[sum(len(p['mesh']['volumes']) for p in c['ducts']) for c in configs]
    if counts[1]!=2*counts[0] or counts[2]!=2*counts[1]:
        raise ValueError('factor-two nested grids required')
    values=[quantities(r) for r in receipts]
    trends={key:scalar_trend(*(v[key] for v in values)) for key in values[0]}
    # Compare every field on the same original coarse control volumes, in the
    # same norms as the preceding two-level diagnostic (including all species).
    mid=restrict_state(receipts[1]['final_state'],configs[1],configs[0])
    fine_on_mid=restrict_state(receipts[2]['final_state'],configs[2],configs[1])
    fine=restrict_state(fine_on_mid,configs[1],configs[0])
    eos=IdealGas(**configs[0]['eos'])
    e0=terminal_differences(receipts[0]['final_state'],mid,eos)
    e1=terminal_differences(mid,fine,eos)
    a,b=dict((key,error) for error,key in e0),dict((key,error) for error,key in e1)
    fields={key:dict(coarse_medium=a[key],medium_fine=b[key],
        difference_decreased=b[key]<a[key]) for key in a}
    return dict(schema='DINO_MESH_THREE_LEVEL_ANALYSIS_V1',review='SELF_REVIEW',
        counts=counts,phase_deg=720.,quantities=trends,
        classifications=dict(Counter(t['classification'] for t in trends.values())),
        projected_fields=fields,largest_medium_fine=e1[:15],
        fields_decreasing=sum(x['difference_decreased'] for x in fields.values()),
        fields_compared=len(fields),source_receipts={str(p):sha(p/'receipt.json') for p in directories},
        analysis_runner_sha256=sha(Path(__file__)),
        mesh_independence_demonstrated=False,certified_uncertainty=None,
        temporal_error_separated=False,experimental_validation=False,
        qualification='Two-revolution transient with original adaptive CFL/rejections. Fitted orders are conditional, not proof of asymptotic convergence or periodic power accuracy.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--levels',type=Path,nargs=3,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    check_storage_requirements([(args.output,1024**2)])
    if args.output.exists():raise FileExistsError('preserve previous analysis')
    result=compare(args.levels)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    write(args.output,result)
    print(json.dumps({k:result[k] for k in ('counts','classifications','fields_decreasing','fields_compared','mesh_independence_demonstrated')},indent=2))
