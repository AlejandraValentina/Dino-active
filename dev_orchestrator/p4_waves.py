"""P4B weak-wave geometry fixtures, independent timing and convergence gates."""
import argparse,gzip,json
from math import exp,fsum,sqrt
from pathlib import Path
from motorsim.project import DuctSegment
from motorsim.exhaust_geometry import exhaust_mesh
from motorsim.exhaust_port import ExhaustPort
from motorsim.exhaust1d import Bench,solve_exhaust
from motorsim.simulation_case import geometry
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.reference import cell_integrals
from motorsim.coupling import ChamberState
from .p4_bench import checks,case as blowdown
from .p2_campaign import ROOT,sha,write

EOS=IdealGas();P=100000.;T=300.;RHO=P/(EOS.R*T);SPEED=sqrt(EOS.gamma*EOS.R*T);Z=RHO*SPEED
EPS=100.;XC=.08;SIGMA=.015;SENSOR=.05;END=.003


def segments(label):
    def s(l,a,b):return DuctSegment('',l,a,b)
    if label=='straight':return (s(750,20,20),)
    if label=='diffuser':return (s(200,20,20),s(150,20,40),s(400,40,40))
    if label=='converger':return (s(200,20,20),s(150,20,10),s(400,10,10))
    h=300 if label in ('long','equal_volume') else 200
    tail=100 if label=='equal_volume' else 200
    return (s(h,20,20),s(150,20,40),s(50,40,40),s(150,40,20),s(tail,20,20))


def crossing(times,values,threshold):
    for i in range(1,len(times)):
        if values[i-1]<threshold<=values[i]:
            return times[i-1]+(times[i]-times[i-1])*(threshold-values[i-1])/(values[i]-values[i-1])
    return None


def wave(label,n=100,cfl=.4,rpm=3000):
    seg=segments(label);mesh=exhaust_mesh(seg,.75/n)
    def primitive(x):
        dp=EPS*exp(-((x-XC)/SIGMA)**2)
        return RHO+dp/SPEED**2,dp/Z,P+dp,.2
    # Integrate each frustum's linearly varying diameter independently.
    def area(x):
        at=0.
        for s in seg:
            length=s.length_mm*.001
            if x<=at+length:
                d=(s.start_diameter_mm+(s.end_diameter_mm-s.start_diameter_mm)*(x-at)/length)*.001
                return 3.141592653589793*d*d/4
            at+=length
        raise ValueError('Reference outside duct')
    q=cell_integrals(mesh,primitive,EOS,area)
    ch=ChamberState(RHO*.0001,P*.0001/(EOS.gamma-1),.2*RHO*.0001,.0001)
    system=Bench(ch,ExhaustPort.from_project(geometry()),rpm=rpm,start_angle=180)
    r=solve_exhaust(mesh,q,system,END,cfl=cfl,sensors=(SENSOR,.15,.45))
    times=[h['time'] for h in r['history']];signal=[.5*(h['sensors'][0][0]-P-Z*h['sensors'][0][1]) for h in r['history']]
    h=.3 if label in ('long','equal_volume') else .2
    expected=(2*h-XC-r['sensor_positions'][0])/SPEED
    window=[(t,v) for t,v in zip(times,signal) if expected-3*SIGMA/SPEED<t<expected+.3/SPEED]
    sign=1 if label=='converger' else -1
    arrival=crossing([t for t,v in window],[sign*v for t,v in window],.01*EPS)
    metric=dict(arrival=arrival,expected_center_return=expected,negative=min(v for t,v in window),positive=max(v for t,v in window),
        pressure_integral=sum(row['dt']*abs(value) for row,value in zip(r['history'],signal)),mass_exchange=r['port_integral'][0],
        arrival_angle=system.angle(arrival) if arrival is not None else None,closing_angle=system.port.events(mesh.areas[0])[-2],
        volume=fsum(mesh.volumes),signal_peak=max(abs(v) for t,v in window))
    c=checks(r)
    if label=='straight':c['weak_unwanted_reflection']=metric['signal_peak']<=.025*EPS
    else:
        c['reflection_sign']=(metric['positive'] if sign>0 else -metric['negative'])>.01*EPS
        c['return_timing']=arrival is not None and abs(arrival-expected)<=3*SIGMA/SPEED+2*max(mesh.widths)/SPEED
    return dict(name=f'{label}_N{n}_CFL{cfl}_RPM{rpm}',inputs=dict(label=label,N=n,actual_cells=mesh.n,CFL=cfl,RPM=rpm,end=END,epsilon=EPS),
        metrics=metric,checks=c,status='PASS' if all(c.values()) else 'FAIL',result=r)


def campaign(run_dir):
    art=Path(run_dir)/'artifacts';(art/'cases').mkdir(parents=True)
    receipt=json.loads((ROOT/'results/p4-exhaust-20260918/p4a-reviewed.json').read_text(encoding='utf-8'))
    if receipt['state']!='P4A_PASS' or receipt['integrator_sha256']!=sha(ROOT/'motorsim/exhaust1d.py'):raise ValueError('P4A gate mismatch')
    rows=[];inventory={}
    jobs=[('wave',label,100,.4,3000) for label in ('straight','diffuser','converger','chain','long','equal_volume')]
    jobs += [('wave','chain',100,.4,rpm) for rpm in (2500,3500)]
    jobs += [('wave','diffuser',n,.4,3000) for n in (200,400)]
    jobs += [('wave','diffuser',100,cfl,3000) for cfl in (.2,.6)]
    jobs += [('blowdown','blowdown',n,.4,3000) for n in (200,400)]
    jobs += [('blowdown','blowdown',100,cfl,3000) for cfl in (.2,.6)]
    for kind,label,n,cfl,rpm in jobs:
        print('START',kind,label,n,cfl,rpm,flush=True)
        r=wave(label,n,cfl,rpm) if kind=='wave' else blowdown(label,n,cfl)
        rows.append(r);path=art/'cases'/(r['name']+'.json.gz');path.write_bytes(gzip.compress(json.dumps(r,allow_nan=False,separators=(',',':')).encode(),mtime=0));inventory[path.name]=sha(path);write(art/'inventory.json',inventory)
        print('END',r['name'],r['status'],r['result']['wall_seconds'],r['metrics'],flush=True)
        if r['status']!='PASS':break
    # Every aggregate is reported, including a partial bank, without claiming unrun gates.
    lookup={r['name']:r for r in rows};aggregate={}
    def get(label,n=100,cfl=.4,rpm=3000):return lookup.get(f'{label}_N{n}_CFL{cfl}_RPM{rpm}')
    if all(get(x) for x in ('chain','long','equal_volume')):
        a,b,c=[get(x)['metrics'] for x in ('chain','long','equal_volume')]
        delta=2*.1/SPEED;tolerance=3*(.75/100)/SPEED
        aggregate['E10_length']=all(m['arrival'] is not None and abs(m['arrival']-a['arrival']-delta)<=tolerance for m in (b,c)) and abs(c['volume']-a['volume'])<=1e-12*a['volume']
    if all(get('chain',rpm=r) for r in (2500,3000,3500)):
        vals=[get('chain',rpm=r)['metrics'] for r in (2500,3000,3500)]
        aggregate['E11_RPM']=all(a['arrival_angle']<b['arrival_angle'] for a,b in zip(vals,vals[1:])) and max(v['arrival'] for v in vals)-min(v['arrival'] for v in vals)<=2*(.75/100)/SPEED
    refinements={}
    baseline=ROOT/'results/p4-exhaust-20260918/p4a/artifacts/cases/blowdown_N100_CFL0.4.json.gz'
    old=json.loads(gzip.decompress(baseline.read_bytes()))
    history=old['result']['history'];times=[r['time'] for r in history]
    arrivals=[crossing(times,[r['sensors'][i][0] for r in history],102000.) for i in (0,1)]
    speeds=[w[1]+EOS.sound_speed(w) for shot in old['result']['snapshots'] for w in shot['primitive']]
    positive=[v for v in speeds if v>0]
    distance=old['result']['sensor_positions'][1]-old['result']['sensor_positions'][0]
    allowance=2*.006/SPEED
    timing=dict(arrivals=arrivals,local_characteristic_range=[min(positive),max(positive)],distance=distance,
                lower=distance/max(positive)-allowance,upper=distance/min(positive)+allowance)
    aggregate['wave_arrival']=all(v is not None for v in arrivals) and timing['lower']<=arrivals[1]-arrivals[0]<=timing['upper']
    for label in ('diffuser','blowdown'):
        selected=[get(label,n) if label=='diffuser' else (old if n==100 else lookup.get(f'blowdown_N{n}_CFL0.4')) for n in (100,200,400)]
        if all(selected):
            refinements[label]={}
            for key in ('arrival','pressure_integral','mass_exchange'):
                v=[r['metrics'][key] for r in selected]
                refinements[label][key]=dict(values=v,decreasing=v[0] is not None and abs(v[2]-v[1])<abs(v[1]-v[0]))
            aggregate['refinement_'+label]=all(x['decreasing'] for x in refinements[label].values())
    sensitivity={}
    for label in ('diffuser','blowdown'):
        selected=[get(label,cfl=c) if label=='diffuser' else (old if c==.4 else lookup.get(f'blowdown_N100_CFL{c}')) for c in (.2,.4,.6)]
        if all(selected):
            # Fixed 2.5% normalized spread on pressure/time/mass metrics; no R5 change.
            sensitivity[label]={key:(max(r['metrics'][key] for r in selected)-min(r['metrics'][key] for r in selected))/max(abs(r['metrics'][key]) for r in selected) for key in ('arrival','pressure_integral','mass_exchange')}
            aggregate['CFL_'+label]=all(v<=.025 for v in sensitivity[label].values())
    passed=len(rows)==len(jobs) and all(r['status']=='PASS' for r in rows) and len(aggregate)==7 and all(aggregate.values())
    write(art/'summary.json',dict(state='P4B_READY_FOR_REVIEW' if passed else 'P4_BLOCKED_WAVE_PHYSICS',passed=passed,aggregate=aggregate,refinement=refinements,sensitivity=sensitivity,
        wave_arrival=timing,cases=[{k:v for k,v in r.items() if k!='result'}|dict(runtime=r['result']['wall_seconds'],reason=r['result']['reason'],residual=r['result']['max_global_residual']) for r in rows]))
    write(art/'result.json',dict(checks=[dict(id='P4B',passed=passed,kind='numerical',reason='E06-E11 geometry and refinement')],metrics=dict(cases=len(rows)),scientific_change_required=not passed))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);campaign(p.parse_args().run_dir)
