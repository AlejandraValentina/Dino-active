"""R1 interface-only gate, before any finite-volume coupled integration."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time
from motorsim.coupling import ChamberState, interface_flux
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.riemann import hllc_flux
from .p2_campaign import ROOT, sha, write
from .p1_r5_close import close as regression


def chamber(p=100000., T=300., Y=.8, V=.01):
    eos=IdealGas();m=p*V/(eos.R*T)
    return ChamberState(m,p*V/(eos.gamma-1),Y*m,V)


def run(run_dir):
    art=Path(run_dir)/'artifacts';art.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();eos=IdealGas();rows=[];contacts=[];directions=[]
    for n in (-1,1):
        for T in (299.,300.,301.):
            for u in (-.1,-.01,-.001,-.0001,-.00001,0.,.00001,.0001,.001,.01,.1):
                pipe=(100000/(eos.R*T),u,100000.,.2)
                f=interface_flux(chamber(),pipe,.01,n,eos=eos)
                rows.append(dict(normal=n,T_pipe=T,u=u,**asdict(f)))
            f=interface_flux(chamber(Y=.3),(100000/(eos.R*T),0.,100000.,.3),.01,n,eos=eos)
            contacts.append(dict(normal=n,T_pipe=T,**asdict(f)))
        for p in (80000.,120000.):
            f=interface_flux(chamber(p), (100000/(eos.R*300),0.,100000.,.2),.01,n,eos=eos)
            directions.append(dict(normal=n,p_chamber=p,**asdict(f),increments=f.increments(1e-5)))
    checks={'C00':all(all(r['outward'][k]==0 for k in (0,2,3)) for r in contacts)}
    continuity={}
    for n in (-1,1):
        for T in (299.,300.,301.):
            for sign in (-1,1):
                seq=[next(r for r in rows if r['normal']==n and r['T_pipe']==T and r['u']==sign*epsilon) for epsilon in (.1,.01,.001,.0001,.00001)]
                for k,label in ((0,'mass'),(2,'energy'),(3,'species')):
                    vals=[abs(r['outward'][k]) for r in seq]
                    continuity[f'{n}_{T}_{sign}_{label}']=dict(values=vals,passed=all(b<a for a,b in zip(vals,vals[1:])))
    checks['C00B']=all(v['passed'] for v in continuity.values()) and all(all(r['outward'][k]==0 for k in (0,2,3)) for r in rows if r['u']==0.)
    checks['forward_reverse']=all((r['outward'][0]<0)==(r['p_chamber']>100000) for r in directions)
    checks['species']=all(abs(r['outward'][3]-r['outward'][0]*(.8 if r['outward'][0]<0 else .2))<=1e-12*max(abs(r['outward'][0]),1.) for r in directions)
    checks['shared_energy']=all(r['increments']['chamber'][1]==-r['increments']['pipe'][1] and r['increments']['chamber'][1]==1e-5*r['outward'][2] for r in directions)
    receipt=json.loads((ROOT/'docs/gasdynamic/p2_human_acceptance.json').read_text(encoding='utf-8'))
    checks['P2_frozen']=all(sha(ROOT/p)==h for p,h in receipt['frozen_core_and_contract_sha256'].items())
    regression(art/'p2-regression')
    reg=json.loads((art/'p2-regression/artifacts/closure.json').read_text(encoding='utf-8'))
    checks['P2_regression']=all(reg['checks'].values());checks['P0_regression']=reg['checks']['P0_regression']
    summary=dict(state='P3_R1_READY_FOR_REVIEW' if all(checks.values()) else 'P3_R1_COUPLING_UNRESOLVED',checks=checks,
        rows=rows,contacts=contacts,directions=directions,continuity=continuity,
        HLLC=sum(r['fallback_reason'] is None for r in rows+contacts+directions),
        HLLE=sum(r['fallback_reason'] is not None for r in rows+contacts+directions),
        wall_seconds=time.monotonic()-start,new_integrations=0)
    write(art/'r1.json',summary)
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason=summary['state']) for k,v in checks.items()],metrics=dict(wall_seconds=summary['wall_seconds'],new_integrations=0),scientific_change_required=not all(checks.values())))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    run(p.parse_args().run_dir)
