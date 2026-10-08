"""P2A isolated verification campaign. Never imports/calls the 0D integrator."""
import argparse
import gzip
import hashlib
import json
import time
from pathlib import Path
from motorsim.gas1d.verification import case_names,run_case,aggregate
from .contracts import read_json,inside
from .git_state import snapshot

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p,data):
    Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def invariants():
    m=read_json(ROOT/'docs/gasdynamic/1d_contract_v1.json')
    production=all(sha(inside(ROOT,p))==h for p,h in m['production_snapshot'].items())
    baseline=all(sha(inside(ROOT,p))==h for p,h in m['baseline_reference'].items())
    receipt=read_json(ROOT/'docs/gasdynamic/p1_human_acceptance.json')
    frozen=all(sha(inside(ROOT,p))==h for p,h in receipt['frozen_contract_sha256'].items())
    original=read_json(inside(ROOT,receipt['original_evidence']))
    accepted=(receipt['actor']=='usuaria' and receipt['status']=='P1_HUMAN_ACCEPTED' and original['gate']=='PASS'
              and sha(inside(ROOT,receipt['original_evidence']))==receipt['original_evidence_sha256'])
    p0=read_json(ROOT/'docs/gasdynamic/p0_human_acceptance.json')
    accepted &= p0['status']=='P0_HUMAN_ACCEPTED' and sha(inside(ROOT,p0['original_evidence']))==p0['original_evidence_sha256']
    # Historical P0 output hashes, no re-integration.
    folder=ROOT/'results/p0-baseline-0d-20260917'
    for p,h in read_json(folder/'artifacts/inventory.json').items():baseline &= sha(inside(folder,p))==h
    return dict(baseline_intact=production and baseline,contract_frozen=frozen,dependencies_accepted=accepted)


def plot(record,path):
    """Standalone SVG of measured fields vs independent reference; no product UI."""
    from html import escape
    from motorsim.gas1d.eos import IdealGas
    eos=IdealGas(record['configuration']['R'],record['configuration']['gamma'])
    xs=record['mesh']['centers'];vol=record['mesh']['volumes']
    actual=record['result']['primitive'];ref=[eos.primitive(tuple(v/a for v in q)) for q,a in zip(record['reference'],vol)]
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="820" viewBox="0 0 1100 820">',
           '<rect width="1100" height="820" fill="white"/>',f'<text x="35" y="25" font-family="sans-serif" font-size="18">{escape(record["name"])} — numerical verification, FIRST_ORDER</text>']
    for k,title in enumerate(('Density','Velocity','Pressure','Fresh fraction')):
        x0=65+(k%2)*530;y0=65+(k//2)*360;w=450;h=270
        ys=[v[k] for v in actual]+[v[k] for v in ref];low=min(ys);high=max(ys);span=high-low or max(abs(high),1.)*.01
        low-=span*.05;high+=span*.05
        parts.append(f'<text x="{x0}" y="{y0-10}" font-family="sans-serif">{title} [{low:.6g}, {high:.6g}]</text>')
        parts.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="none" stroke="#999"/>')
        for rows,color in ((ref,'#e67e22'),(actual,'#1768ac')):
            points=' '.join(f'{x0+(x-xs[0])/(xs[-1]-xs[0])*w:.3f},{y0+h-(v[k]-low)/(high-low)*h:.3f}' for x,v in zip(xs,rows))
            parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x0}" y="{y0+h+20}" font-family="sans-serif">x [m or case units]: {xs[0]:.4g}–{xs[-1]:.4g}</text>')
    parts.append('<text x="65" y="800" font-family="sans-serif">Blue: numerical. Orange: independent reference. Not experimental validation.</text></svg>')
    path.write_text('\n'.join(parts),encoding='utf-8')


def campaign(run_dir, r3=False):
    started=time.monotonic();art=run_dir/'artifacts';(art/'cases').mkdir();(art/'plots').mkdir()
    write(art/'git-before.json',snapshot(ROOT))
    checks=invariants()
    if r3:
        receipt=read_json(ROOT/'results/p1-r3-fronteras-20260918/reviewed-evidence.json')
        checks['r3_reviewed']=receipt['gate']=='PASS' and receipt['review']['kind']=='independent'
        boundary=read_json(ROOT/'results/p1-r3-fronteras-20260918/boundary-attempt-2/artifacts/boundary-summary.json')
        checks['r3_contract_intact']=boundary['contract_sha256']==sha(ROOT/'docs/gasdynamic/1d_contract_v1_r3.json')
    if not all(checks.values()):raise ValueError('Precondition/hash failure: '+str(checks))
    records=[];case_hashes={}
    names=case_names()
    if r3:
        names.remove('T02_sod_0.2');names.insert(0,'T02_sod_0.2')
    for name in names:
        print('START '+name,flush=True)
        try:
            record=run_case(name,wall_limit=240. if name=='T10_800' else 120.,progress=lambda step,t:print(f'PROGRESS {name} step={step} t={t:.8g}',flush=True) if step%2000==0 else None)
        except Exception as exc:
            record=dict(name=name,status='FAIL',checks={'reference_or_execution':False},metrics={},
                        error=type(exc).__name__+': '+str(exc),result={'status':'failed_infrastructure','wall_seconds':0.})
        raw=json.dumps(record,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
        target=art/'cases'/f'{name}.json.gz';target.write_bytes(gzip.compress(raw,mtime=0))
        case_hashes[target.relative_to(run_dir).as_posix()]=sha(target)
        records.append(record)
        write(art/'checkpoint.json',dict(completed=len(records),latest=name,status=record['status'],hashes=case_hashes))
        print(f"END {name} {record['status']} {record['result']['wall_seconds']:.3f}s "+str([k for k,v in record['checks'].items() if not v]),flush=True)
        if name.startswith(('T02','T03')) and 'primitive' in record['result']:
            plot(record,art/'plots'/f'{name}.svg')
    matrix=aggregate(records)
    checks.update(invariants());checks['P2A']=all(row['status']=='PASS' for row in matrix.values())
    infrastructure=any(r['result']['status']=='failed_infrastructure' for r in records)
    state='P2A_READY_FOR_INDEPENDENT_REVIEW' if checks['P2A'] else 'P2_BLOCKED_FIRST_ORDER'
    if not checks['baseline_intact']:state='P2_BLOCKED_BASELINE_REGRESSION'
    if infrastructure:state='FAILED_INFRASTRUCTURE'
    summary=dict(state=state,P2B='NOT_IMPLEMENTED_GATED_BY_P2A',matrix=matrix,
                 cases=[{k:v for k,v in r.items() if k not in ('result','initial','reference','mesh')} |
                        dict(runtime={k:r['result'].get(k) for k in ('status','reason','steps','wall_seconds','minimum_dt','max_CFL','rejected_steps','extrema','hllc_flux_count','hlle_fallback_count','characteristic_flux_count','riemann_flux_count','fallback_reason')}) for r in records],
                 wall_seconds=time.monotonic()-started,checks=checks,run_id=run_dir.name,
                 source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'motorsim/gas1d').glob('*.py')},
                 contract_sha256=sha(ROOT/('docs/gasdynamic/1d_contract_v1_r3.json' if r3 else 'docs/gasdynamic/1d_contract_v1.json')),
                 contract_revision='1D_CONTRACT_V1_R3' if r3 else '1D_CONTRACT_V1',repair_attempt=3 if r3 else 0,
                 note='First order only. P2B and P3 not executed. Physical validation not claimed.')
    write(art/'p2a-summary.json',summary)
    inventory={p.relative_to(run_dir).as_posix():sha(p) for p in art.rglob('*') if p.is_file() and p.name!='inventory.json'}
    write(art/'inventory.json',inventory)
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical' if k=='P2A' else 'infrastructure',reason=state if k=='P2A' else 'Hash/acceptance check') for k,v in checks.items()],
        metrics=dict(cases=len(records),passed_cases=sum(r['status']=='PASS' for r in records),wall_seconds=summary['wall_seconds']),scientific_change_required=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--r3',action='store_true')
    args=parser.parse_args();campaign(args.run_dir,args.r3)
