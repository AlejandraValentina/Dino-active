"""P1_R3_BOUNDARY_SEMANTICS_REVIEW: prescribed acoustic tests, no 0D."""
import argparse
import gzip
import json
from pathlib import Path
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.reference import cell_integrals
from motorsim.gas1d.solver import solve
from motorsim.gas1d.verification import definition,measure,BASE,P0,A0
from .p2_campaign import invariants,sha,write,ROOT


def run(run_dir, previous=None):
    art=run_dir/'artifacts';(art/'cases').mkdir()
    checks=invariants()
    if not all(checks.values()):raise ValueError('Preservation failure')
    rows=[]
    for name,n in [('T05',200),('T05',400),('T05',800),('NR01',800)]:
        if previous is not None and name=='T05':
            old=json.loads((previous/'artifacts/boundary-summary.json').read_text(encoding='utf-8'))
            if old['contract_sha256']!=sha(ROOT/'docs/gasdynamic/1d_contract_v1_r3.json'):
                raise ValueError('Reused T05 contract mismatch')
            rel=f'artifacts/cases/{name}-{n}.json.gz';source=previous/rel
            inventory=json.loads((previous/'artifacts/inventory.json').read_text(encoding='utf-8'))
            if sha(source)!=inventory[rel]:raise ValueError('Reused T05 hash mismatch')
            record=json.loads(gzip.decompress(source.read_bytes()))
            if not all(record['summary']['checks'].values()):raise ValueError('Cannot reuse failed T05')
            row=record['summary'];row['reused_from']=str(source);row['source_sha256']=sha(source)
            rows.append(row);(art/'cases'/f'{name}-{n}.json.gz').write_bytes(source.read_bytes())
            continue
        case=definition('T05');case['mesh']=uniform_mesh(n)
        if name=='NR01':
            case['test']='NR01';case['bc']=(Boundary('nonreflecting',state=BASE),Boundary('nonreflecting',state=BASE))
        mesh=case['mesh'];eos=case['eos']
        initial=cell_integrals(mesh,case['initial'],eos,case['area'],case['breaks'])
        reference=cell_integrals(mesh,case['reference'],eos,case['area'],case['refbreaks'])
        print('START',name,n,flush=True)
        result=solve(mesh,initial,case['end'],case['bc'],eos=eos,cfl=case['cfl'],sensor=case['sensor'],sample_interval=case['interval'],wall_limit=120.)
        metrics,criteria=measure(case,result,reference,initial)
        if name=='NR01' and result['status']=='completed':
            incident=[p-P0 for t,p in result['sensors'] if .30<=t*A0<=.50]
            reflected=[(t*A0,p-P0) for t,p in result['sensors'] if .90<=t*A0<=1.10]
            peak,amplitude=max(reflected,key=lambda v:abs(v[1]));inc=max(incident)
            metrics.update(incident_amplitude=inc,reflected_amplitude=amplitude,reflection_coefficient=amplitude/max(abs(inc),1e-8*P0),peak_time_scaled=peak)
            metrics['absolute_reflection']=abs(metrics['reflection_coefficient'])
            criteria['measurable_incident']=inc>=.5*1e-4*P0
        metrics['residual_final']=result['final_inventory'] and result['ledger'][-1]['residual'] if result['ledger'] else None
        metrics['worst_normalized_by_component']=[max((x['normalized'][k] for x in result['ledger']),default=0.) for k in range(4)]
        row=dict(name=name,N=n,checks=criteria,metrics=metrics,role='CONTRACTUAL' if name=='T05' and n==800 else 'DIAGNOSTIC',
                 runtime={k:result[k] for k in ('status','reason','wall_seconds','steps','extrema','hllc_flux_count','hlle_fallback_count','characteristic_flux_count','riemann_flux_count')})
        record=dict(summary=row,mesh=mesh.as_dict(),initial=initial,result=result,
                    configuration=dict(CFL=case['cfl'],R=eos.R,gamma=eos.gamma,final_time=case['end'],sensor=case['sensor'],sample_interval=case['interval'],boundaries=[b.__dict__ for b in case['bc']]))
        (art/'cases'/f'{name}-{n}.json.gz').write_bytes(gzip.compress(json.dumps(record,allow_nan=False,separators=(',',':')).encode(),mtime=0))
        rows.append(row);write(art/'checkpoint.json',dict(rows=rows))
        print('END',name,n,result['status'],metrics.get('reflection_coefficient'),flush=True)
    checks.update(invariants())
    checks['T05']=all(rows[2]['checks'].values())
    checks['mesh_sign']=all(r['runtime']['status']=='completed' and r['metrics'].get('reflection_coefficient',0)<0 for r in rows[:3])
    checks['all_ledgers']=all(r['checks']['worst_ledger'] for r in rows)
    checks['NR01_recorded']=all(rows[3]['checks'].values())
    checks['counter_identity']=all(r['runtime']['riemann_flux_count']==r['runtime']['hllc_flux_count']+r['runtime']['hlle_fallback_count'] for r in rows)
    state='P1_R3_PASS_BOUNDARIES_SEPARATED' if all(checks.values()) else 'P1_R3_BOUNDARY_CONTRACT_UNRESOLVED'
    if any(r['runtime']['status']=='failed_infrastructure' for r in rows):state='FAILED_INFRASTRUCTURE'
    write(art/'boundary-summary.json',dict(state=state,checks=checks,rows=rows,contract_sha256=sha(ROOT/'docs/gasdynamic/1d_contract_v1_r3.json'),note='NR01 has no new reflection threshold; N800 T05 gate unchanged. Independent review required.'))
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason=state) for k,v in checks.items()],metrics=dict(cases=len(rows)),scientific_change_required=False))
    write(art/'inventory.json',{p.relative_to(run_dir).as_posix():sha(p) for p in art.rglob('*') if p.is_file() and p.name!='inventory.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--reuse-t05',type=Path)
    args=parser.parse_args();run(args.run_dir,args.reuse_t05)
