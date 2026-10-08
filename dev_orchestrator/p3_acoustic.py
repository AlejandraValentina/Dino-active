"""P3C frozen fixtures and independent causal linear acoustic reference."""
import argparse
from dataclasses import asdict
import gzip
import json
from math import cos, erf, exp, fsum, pi, sin, sqrt
from pathlib import Path
from motorsim.coupled import solve_coupled
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.reference import NODES, WEIGHTS, cell_integrals
from .p3_r1 import chamber
from .p3_finite import common_checks, species_audit
from .p2_campaign import ROOT, sha, write

P=100000.; T=300.; A=.0003; V=.0001; L=.3; EPS=1.; XC=.15; SIGMA=.03; END=.0009
EOS=IdealGas(); RHO=P/(EOS.R*T); SPEED=sqrt(EOS.gamma*EOS.R*T); Z=RHO*SPEED
TAU=2*V/(SPEED*A)


def reference_integrals(mesh,t):
    """Independent GL4 composite quadrature, with an absolute scale check.

    Relative-only convergence is ill-defined for nearly cancelling momentum.
    Check two subdivisions against a fixed perturbation momentum scale instead.
    """
    def evaluate(parts):
        cells=[]
        for left,right in zip(mesh.faces,mesh.faces[1:]):
            bounds=[left,*([SPEED*t] if left<SPEED*t<right else []),right];rows=[]
            for lower,upper in zip(bounds,bounds[1:]):
                h=(upper-lower)/parts
                for j in range(parts):
                    middle=lower+(j+.5)*h
                    rows.extend(tuple(h/2*w*A*q for q in EOS.conservative(reference(middle+h/2*x,t))) for x,w in zip(NODES,WEIGHTS))
            cells.append(tuple(fsum(r[k] for r in rows) for k in range(4)))
        return cells
    coarse=evaluate(8);fine=evaluate(16)
    scales=(RHO,EPS/SPEED,P/(EOS.gamma-1),.3*RHO)
    error=max(abs(x-y)/(v*s) for a,b,v in zip(coarse,fine,mesh.volumes) for x,y,s in zip(a,b,scales))
    if error>1e-10:raise ValueError(f'Reference absolute quadrature failed: {error}')
    return fine,error


def chamber_pressure(t):
    if t<=0:return 0.
    b=SIGMA/SPEED; t0=XC/SPEED
    return EPS*b*sqrt(pi)/TAU*exp((t0-t)/TAU+b*b/(4*TAU*TAU))*(erf((t-t0-b*b/(2*TAU))/b)-erf((-t0-b*b/(2*TAU))/b))


def reference(x,t):
    incident=EPS*exp(-((x+SPEED*t-XC)/SIGMA)**2)
    reflected=chamber_pressure(t-x/SPEED)/2
    return RHO+(incident+reflected)/SPEED**2,(reflected-incident)/Z,P+incident+reflected,.3


def volume(t):
    omega=2*pi/.003
    return V*(1+.05*sin(omega*t)),V*.05*omega*cos(omega*t)


def acoustic(n,cfl):
    mesh=uniform_mesh(n,L,A);ch=chamber(P,Y=.3,V=V)
    initial=cell_integrals(mesh,lambda x:reference(x,0),EOS,lambda x:A)
    r=solve_coupled(mesh,initial,ch,END,cfl=cfl,wall_limit=300.)
    final,final_quadrature=reference_integrals(mesh,END)
    exact=[EOS.primitive(tuple(q/v for q in row)) for row,v in zip(final,mesh.volumes)]
    errors={name:sum(abs(w[k]-e[k]) for w,e in zip(r['primitive'],exact))/n/scale for name,k,scale in (('pressure',2,EPS),('velocity',1,EPS/Z))}
    pc=chamber_pressure(END)
    expected=(ch.mass+V/SPEED**2*pc,ch.internal_energy+V/(EOS.gamma-1)*pc,ch.fresh_mass+.3*V/SPEED**2*pc)
    for name,k,scale in (('mass',0,V/SPEED**2*EPS),('energy',1,V/(EOS.gamma-1)*EPS),('species',2,.3*V/SPEED**2*EPS)):
        errors[name]=abs(r['chamber'][k]-expected[k])/scale
    errors['chamber_pressure']=abs((EOS.gamma-1)*r['chamber'][1]/V-P-pc)/EPS
    reflection_error=0.; numerical_peak=0.; exact_peak=0.
    for trace,ledger in zip(r['traces'],r['ledger']):
        for s in trace['stages']:
            # Linear outgoing characteristic at left face, not an imposed BC.
            pr=.5*(-s['outward'][1]/A-P+SPEED*(-s['outward'][0]/A))
            pe=chamber_pressure(s['time'])/2
            reflection_error+=ledger['dt']/len(trace['stages'])*abs(pr-pe)/(EPS*END)
            numerical_peak=max(numerical_peak,pr/EPS);exact_peak=max(exact_peak,pe/EPS)
    errors['reflected_wave']=reflection_error
    checks=common_checks(r)
    checks.update(accuracy=all(v<=.025 for v in errors.values()),species=species_audit(r)<=1e-12,response=0<numerical_peak<1)
    return dict(name=f'acoustic_N{n}_CFL{cfl}',inputs=dict(N=n,CFL=cfl,final_time=END,epsilon=EPS,tau=TAU),quadrature=dict(final_difference_8_16=final_quadrature,scales=[RHO,EPS/SPEED,P/(EOS.gamma-1),.3*RHO]),errors=errors,
        reflection_peak=dict(numerical=numerical_peak,reference=exact_peak),initial=initial,result=r,checks=checks,status='PASS' if all(checks.values()) else 'FAIL')


def variable(method):
    mesh=uniform_mesh(80,L,A);ch=chamber(P,Y=.3,V=V)
    initial=[tuple(x*v for x in EOS.conservative((RHO,0.,P,.3))) for v in mesh.volumes]
    r=solve_coupled(mesh,initial,ch,.003,method=method,volume=volume,wall_limit=300.)
    work=sum(l['dt']/len(t['stages'])*sum(-s['pressure']*volume(s['time'])[1] for s in t['stages']) for t,l in zip(r['traces'],r['ledger']))
    checks=common_checks(r)
    checks['independent_work']=abs(work-r['ledger'][-1]['work_0D'])/r['initial_inventory'][1]<=1e-10
    checks['energy_with_work']=abs(r['final_inventory'][1]-r['initial_inventory'][1]-work)/r['initial_inventory'][1]<=1e-10
    checks['excited']=max(abs(s['pressure']-P) for t in r['traces'] for s in t['stages'])>0
    return dict(name='variable_'+method,inputs=dict(N=80,CFL=.4,method=method,final_time=.003),initial=initial,result=r,
        independent_work=work,checks=checks,status='PASS' if all(checks.values()) else 'FAIL')


def campaign(run_dir):
    art=Path(run_dir)/'artifacts';(art/'cases').mkdir(parents=True)
    receipt=json.loads((ROOT/'results/p3-r1-20260918/p3b-reviewed.json').read_text(encoding='utf-8'))
    if receipt['state']!='P3B_PASS' or receipt['integrator_sha256']!=sha(ROOT/'motorsim/coupled.py'):raise ValueError('P3B gate mismatch')
    records=[];inventory={}
    def save(r):
        records.append(r);p=art/'cases'/(r['name']+'.json.gz')
        p.write_bytes(gzip.compress(json.dumps(r,allow_nan=False,separators=(',',':')).encode(),mtime=0));inventory[p.name]=sha(p)
        write(art/'inventory.json',inventory)
        print(r['name'],r['status'],r['result']['wall_seconds'],r.get('errors',{}),flush=True)
    for method in ('FIRST_ORDER','MUSCL_SSPRK2'):
        previous=ROOT/'results/p3-r1-20260918/p3c-infrastructure/artifacts/cases'/('variable_'+method+'.json.gz')
        inventory_before=json.loads((previous.parent.parent/'inventory.json').read_text(encoding='utf-8'))
        if sha(previous)!=inventory_before[previous.name]:raise ValueError('C08 reuse hash mismatch')
        reused=json.loads(gzip.decompress(previous.read_bytes()));reused['reused_from']=str(previous.relative_to(ROOT));reused['reused_sha256']=sha(previous)
        save(reused)
        if records[-1]['status']!='PASS':break
    if all(r['status']=='PASS' for r in records):
        for cfl in (.2,.4,.6):
            for n in (40,80,160):
                save(acoustic(n,cfl))
                if records[-1]['status']!='PASS':break
            if records[-1]['status']!='PASS':break
    cases={r['name']:r for r in records}; refinement={};sensitivity={}
    if len(records)==11:
        for cfl in (.2,.4,.6):
            rows=[cases[f'acoustic_N{n}_CFL{cfl}'] for n in (40,80,160)]
            refinement[str(cfl)]={k:dict(values=[r['errors'][k] for r in rows],decreasing=all(a['errors'][k]>b['errors'][k] for a,b in zip(rows,rows[1:]))) for k in ('pressure','velocity','mass','energy','species','chamber_pressure')}
        for a,b in ((.2,.4),(.2,.6),(.4,.6)):
            vals=[]
            for n in (40,80,160):
                qa=cases[f'acoustic_N{n}_CFL{a}']['result']['primitive'];qb=cases[f'acoustic_N{n}_CFL{b}']['result']['primitive']
                vals.append(sum(abs(x[2]-y[2]) for x,y in zip(qa,qb))/n/EPS)
            sensitivity[f'{a}/{b}']=dict(values=vals,refined_not_worse=vals[-1]<=vals[0])
    checks=dict(C08=len(records)>=2 and all(r['status']=='PASS' for r in records[:2]),
        C09=len(records)==11 and all(r['checks'].get('accuracy',False) for r in records[2:]),
        C10=bool(refinement) and all(v['decreasing'] for row in refinement.values() for v in row.values()),
        C11=bool(sensitivity) and all(v['refined_not_worse'] for v in sensitivity.values()),
        C12=len(records)==11 and all(r['checks']['positivity'] for r in records))
    passed=all(checks.values()) and all(r['status']=='PASS' for r in records)
    write(art/'summary.json',dict(state='P3C_READY_FOR_REVIEW' if passed else 'P3_BLOCKED_COUPLING',checks=checks,passed=passed,
        refinement=refinement,sensitivity=sensitivity,gaussian_tails=dict(initial_pressure=EPS*exp(-(XC/SIGMA)**2),right_wall_reflection=chamber_pressure(END-L/SPEED)/2),
        cases=[{k:v for k,v in r.items() if k not in ('result','initial')}|dict(runtime=r['result']['wall_seconds'],counts=r['result']['counts'],max_residual=max(max(l['normalized']) for l in r['result']['ledger'])) for r in records]))
    write(art/'result.json',dict(checks=[dict(id='P3C',passed=passed,kind='numerical',reason='Variable-volume and acoustic gates')],metrics=dict(cases=len(records)),scientific_change_required=not passed))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);campaign(p.parse_args().run_dir)
