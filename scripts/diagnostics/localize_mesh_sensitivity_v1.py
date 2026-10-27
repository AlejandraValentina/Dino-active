"""Read-only, same-volume and same-phase localization of existing V2 states."""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import Mesh
from motorsim.gas1d.spatial_reconstruction_v2 import reconstruct_v2
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.diagnose_integrated_mesh_v1 import refined_configuration, restrict_state
from scripts.diagnostics.compare_integrated_port_v2 import terminal_differences


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_geometry(coarse, fine, parent_hash):
    if refined_configuration(coarse, parent_hash) != fine:
        raise ValueError('fine configuration is not the exact conservative parent bisection')


def analyze(coarse_dir, fine_dir):
    coarse, fine = [load(p / 'configuration.json') for p in (coarse_dir, fine_dir)]
    verify_geometry(coarse, fine, sha(coarse_dir / 'configuration.json'))
    eos = IdealGas(**coarse['eos'])
    meshes = {p['id']: p['mesh'] for p in coarse['ducts']}
    result = dict(schema='DINO_MESH_LOCALIZATION_V1', solver_steps=0,
                  geometry_exact_bisection_verified=True, review='SELF_REVIEW',
                  phases=[], experimental_validation=False,
                  source_files={}, projection='Volume-weight conserved densities; sum extensive species; then recover primitives')
    receipts = [load(p / 'receipt.json') for p in (coarse_dir, fine_dir)]
    for directory, receipt in zip((coarse_dir, fine_dir), receipts):
        if sha(directory / 'configuration.json') != receipt['configuration_sha256']:
            raise ValueError('configuration hash mismatch')
    for filename in ('initial-checkpoint.json', 'checkpoint-360.json', 'checkpoint-720.json'):
        paths = [p / filename for p in (coarse_dir, fine_dir)]
        a, b = [load(p) for p in paths]
        if a['crank_angle_unwrapped_deg'] != b['crank_angle_unwrapped_deg'] or a['angle_deg'] != b['angle_deg']:
            raise ValueError('different crank phase')
        for path in paths:
            result['source_files'][str(path)] = sha(path)
        projected = restrict_state(b['state'], fine, coarse)
        errors = terminal_differences(a['state'], projected, eos)
        ranked = []
        for error, name in errors[:20]:
            parts = name.split('/')
            location = None
            if parts[0] in meshes:
                i = int(parts[1]); m = meshes[parts[0]]
                location = dict(parent_cell=i, fine_children=[2*i, 2*i+1],
                                interval_m=m['faces'][i:i+2], centroid_m=m['centers'][i],
                                endpoint_cell=i in (0, len(m['volumes'])-1))
            ranked.append(dict(metric=name, normalized_difference=error, location=location))
        totals = {}
        endpoints = {}
        for name, m in meshes.items():
            av = a['state']['ducts'][name]; bv = projected['ducts'][name]
            totals[name] = dict(
                coarse_mass_kg=math.fsum(q[0]*v for q,v in zip(av,m['volumes'])),
                fine_mass_kg=math.fsum(q[0]*v for q,v in zip(bv,m['volumes'])),
                coarse_energy_J=math.fsum(q[2]*v for q,v in zip(av,m['volumes'])),
                fine_energy_J=math.fsum(q[2]*v for q,v in zip(bv,m['volumes'])))
            mesh=Mesh(**{k:tuple(v) for k,v in m.items()})
            primitive=[eos.primitive((*q[:3],q[0])) for q in av]
            fractions=[tuple(v/math.fsum(s) for v in s) for s in a['state']['species']['ducts'][name]]
            traces=reconstruct_v2(mesh,primitive,fractions,eos=eos)
            endpoints[name]=[dict(cell=i, gas_trace_changed=any(trace[k]!=primitive[i][k] for k in range(3)),
                pressure_trace_delta_pa=trace[2]-primitive[i][2])
                for i,trace in ((0,traces.left[0]),(mesh.n-1,traces.right[-1]))]
        density_peak = next(x for x in ranked if x['metric'].endswith('/density')) if any(x['metric'].endswith('/density') for x in ranked) else None
        if density_peak:
            name, index, _ = density_peak['metric'].split('/'); i = int(index)
            m=meshes[name]
            # Diagnostic shift estimate only; never align or replace acceptance errors.
            fields=[]
            for state in (a['state'],projected):
                fields.append([q[0] for q in state['ducts'][name]])
            gradient=(fields[0][min(i+1,len(fields[0])-1)]-fields[0][max(0,i-1)])/(m['centers'][min(i+1,len(fields[0])-1)]-m['centers'][max(0,i-1)])
            density_peak['rho_coarse_kg_m3']=fields[0][i]
            density_peak['rho_fine_projected_kg_m3']=fields[1][i]
            density_peak['linearized_shift_m']=(fields[1][i]-fields[0][i])/gradient if gradient else None
        result['phases'].append(dict(unwrapped_angle_deg=a['crank_angle_unwrapped_deg'],
            maximum_difference=errors[0][0], ranked=ranked, duct_inventories=totals,
            work_out_J=[-x['ledger']['cylinder_work_J'] for x in (a,b)],endpoint_traces=endpoints))
    result['interpretation_limits'] = [
        'Only phases 0,360,720 available in both meshes; no intra-cycle localization established.',
        'Relative positive-state differences, sound-normalized velocity and absolute species fractions use different normalizations.',
        'A linearized spatial shift is a local diagnostic, not proof of pure wave displacement.',
        'No grid-independent reference or periodic power established.']
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coarse',type=Path,required=True);p.add_argument('--fine',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    check_storage_requirements([(args.output,1024**2)])
    if args.output.exists():raise FileExistsError('preserve earlier evidence')
    r=analyze(args.coarse,args.fine)
    args.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps([{'angle':x['unwrapped_angle_deg'],'max':x['maximum_difference'],'top':x['ranked'][0]} for x in r['phases']]))
