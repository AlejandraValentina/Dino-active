"""Offline P4A/B snapshot kernel replay plus accepted P0/P2/P3 receipts."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from motorsim.exhaust_batch import Kernel,hllc,primitive
from motorsim.gas1d.mesh import Mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.second_order import reconstruct
from .p4_regression import run as historical
from .p4_r1e import verify
from .p2_campaign import ROOT,sha,write


def run(folder):
    folder=Path(folder);art=folder/'artifacts';art.mkdir(parents=True,exist_ok=True)
    historical(folder/'historical');eos=IdealGas();cases=[]
    for phase in ('p4a','p4b'):
        for path in sorted((ROOT/f'results/p4-exhaust-20260918/{phase}/artifacts/cases').glob('*.gz')):
            row=json.loads(gzip.decompress(path.read_bytes()));r=row['result'];m=r['mesh']
            mesh=Mesh(*(tuple(m[k]) for k in ('faces','areas','volumes','centers')));kernel=Kernel(mesh,eos)
            bc=(Boundary('outflow'),Boundary('nonreflecting',state=(100000/(287*300),0.,100000.,0.)))
            replayed=faces=0;fallbacks=0
            for shot in r['snapshots']+[dict(primitive=r['primitive'])]:
                w=shot['primitive'];a,b,d=reconstruct(mesh,w,bc,eos);x,y,z=kernel.reconstruct(np.array(w),bc)
                np.testing.assert_array_equal(x,a);np.testing.assert_array_equal(y,b)
                if z!=d:raise AssertionError('MUSCL downgrade mismatch')
                f,s,reason,_=hllc(y[:-1],x[1:],eos)
                for i in range(mesh.n-1):
                    expected,sp,rs=hllc_flux(b[i],a[i+1],eos)
                    np.testing.assert_array_equal(f[i],expected);np.testing.assert_array_equal(s[i],sp)
                    if reason.get(i)!=rs:raise AssertionError('HLLE reason mismatch')
                conserved=np.array([eos.conservative(tuple(t)) for t in w])*kernel.volumes[:,None]
                expected=[eos.primitive(tuple(q/v for q in cell)) for cell,v in zip(conserved.tolist(),mesh.volumes)]
                np.testing.assert_array_equal(primitive(conserved,kernel.volumes,eos),expected)
                replayed+=1;faces+=mesh.n-1;fallbacks+=len(reason)
            cases.append(dict(phase=phase,name=path.name,source_sha256=sha(path),snapshots_and_final=replayed,
                face_comparisons=faces,HLLE_faces=fallbacks,exact=True,original_checks=row['checks']))
    old=json.loads((folder/'historical/artifacts/regression.json').read_text(encoding='utf-8'))
    receipt=json.loads((ROOT/'docs/gasdynamic/p4_r3_acceptance.json').read_text(encoding='utf-8'))
    checks=dict(P4A_replay=sum(c['phase']=='p4a' for c in cases)==3,
        P4B_replay=sum(c['phase']=='p4b' for c in cases)==16,original_individual_checks=all(all(c['original_checks'].values()) for c in cases),
        historical=all(old['checks'].values()),frozen=verify(),R3_reference=all(sha(ROOT/p)==h for p,h in receipt['frozen'].items()))
    write(art/'regression.json',dict(checks=checks,cases=cases,new_campaign_integrations=0,
        scope='All saved P4A/B snapshots and final primitive arrays; kernel replay, not repeat physical campaigns. Historical R2 gates remain accepted.'))
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason='Exact offline kernel replay and frozen receipts') for k,v in checks.items()],metrics=dict(cases=len(cases)),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);run(p.parse_args().run_dir)
