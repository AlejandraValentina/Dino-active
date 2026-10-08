"""Frozen P1 verification cases for P2A; no changes to gates based on outcomes."""
from math import sin,pi,exp,sqrt,fsum,log2
from .eos import IdealGas
from .mesh import uniform_mesh,smooth_mesh,segments_mesh
from .boundary import Boundary
from .reference import ExactRiemann,cell_integrals,primitives
from .solver import solve
from .contact import density_contact

EOS=IdealGas();P0=100000.;T0=300.;RHO=P0/(EOS.R*T0);A0=sqrt(EOS.gamma*EOS.R*T0)
BASE=(RHO,0.,P0,.3)


def norms(actual,reference,volumes,scale):
    diff=[abs(a-b) for a,b in zip(actual,reference)];volume=fsum(volumes)
    return dict(L1=fsum(v*d for v,d in zip(volumes,diff))/(volume*scale),
                L2=sqrt(fsum(v*d*d for v,d in zip(volumes,diff))/volume)/scale,
                Linf=max(diff)/scale)


def fields_errors(actual,ref,mesh,scales):
    return {name:norms([w[k] for w in actual],[w[k] for w in ref],mesh.volumes,scales[k])
            for k,name in enumerate(('rho','u','p','Y'))}


def pulse(x,center=.25):
    dp=1e-4*P0*exp(-((x-center)/.04)**2)
    return RHO+dp/A0**2,dp/(RHO*A0),P0+dp,.3


def contact(x,u=.2*A0,shift=0.,pure=None):
    inner=.2<=((x-shift)%1.)<.4
    return (2*RHO if inner else RHO),u,P0,(float(inner) if pure is None else pure)


def contact_breaks(shift):return sorted({0.,1.,shift%1.,(.2+shift)%1.,(.4+shift)%1.})


def totals(mach=.2):
    factor=1+(EOS.gamma-1)*mach*mach/2
    return P0*factor**(EOS.gamma/(EOS.gamma-1)),T0*factor


def nozzle(area):
    g=EOS.gamma
    def ratio(m):return (2/(g+1)*(1+(g-1)*m*m/2))**((g+1)/(2*(g-1)))/m
    star=area(0.)/ratio(.2)
    def state(x):
        target=area(x)/star;lo=1e-8;hi=1.
        for _ in range(60):
            m=(lo+hi)/2
            if ratio(m)>target:lo=m
            else:hi=m
        m=(lo+hi)/2;factor=1+(g-1)*m*m/2
        temp=T0/factor;pressure=P0/factor**(g/(g-1));rho=pressure/(EOS.R*temp)
        return rho,m*sqrt(g*EOS.R*temp),pressure,.3
    return state


def definition(name):
    """Each name identifies an independent subcase. No warm-start or cached results."""
    tokens=name.split('_');test=tokens[0];kind=tokens[1] if len(tokens)>1 else ''
    n=400;cfl=.4;eos=EOS;mesh=uniform_mesh(n);area=lambda x:.01
    initial=lambda x:BASE;reference=initial;breaks=[];refbreaks=[];end=1/A0;bc='periodic';exact=None;sensor=None;interval=None
    if test=='T01':
        n=100;mesh=uniform_mesh(n);u=0. if kind=='rest' else .2*A0
        initial=reference=lambda x:(RHO,u,P0,.3)
    elif test in ('T02','T12') and kind in ('sod','expansion'):
        eos=IdealGas(1.,1.4);mesh=uniform_mesh(400,area=1.);area=lambda x:1.
        left,right=((1.,0.,1.,1.),(.125,0.,.1,0.)) if kind=='sod' else ((1.,-2.,.4,0.),(1.,2.,.4,1.))
        end=.2 if kind=='sod' else .1
        initial=lambda x:left if x<.5 else right
        exact=ExactRiemann(left,right,eos);reference=lambda x:exact.sample((x-.5)/end)
        breaks=[.5];refbreaks=exact.breaks(end);bc=(Boundary('fixed',state=left),Boundary('fixed',state=right))
        if len(tokens)>2:cfl=float(tokens[2])
    elif test in ('T03','T04','T05'):
        n=800;mesh=uniform_mesh(n);center=.25 if test=='T03' else .3
        initial=lambda x:pulse(x,center);end=(.45 if test=='T03' else 1.15)/A0
        reference=lambda x:pulse(x-A0*end,center)
        bc=(Boundary('nonreflecting',state=BASE),
            Boundary('nonreflecting',state=BASE) if test=='T03' else Boundary('wall' if test=='T04' else 'ideal_open_pressure_release'))
        if test in ('T04','T05'):sensor=.7;interval=.001/A0
        if kind:cfl=float(kind)
    elif test in ('T06','T09','T12') and kind in ('contact','reverse','pure0','pure1'):
        u=(-.2 if kind=='reverse' else .2)*A0;pure=0. if kind=='pure0' else (1. if kind=='pure1' else None)
        end=.5/abs(u);initial=lambda x:contact(x,u,pure=pure)
        reference=lambda x:contact(x,u,u*end,pure=pure)
        breaks=contact_breaks(0.);refbreaks=contact_breaks(u*end)
    elif test=='T07':
        n=200;mesh=uniform_mesh(n);end=.5/A0
        if kind=='periodic':initial=lambda x:contact(x);breaks=contact_breaks(0.)
        elif kind=='closed':initial=pulse;bc=(Boundary('wall'),Boundary('wall'))
        else:
            initial=lambda x:(RHO,.2*A0,P0,.3);pt,tt=totals()
            bc=(Boundary('reservoir',p0=pt,T0=tt),Boundary('reservoir',p0=P0,T0=T0))
        reference=initial
    elif test=='T08' or (test=='T12' and kind=='frustum'):
        geom=tokens[1] if test=='T08' else 'frustum'
        mode=tokens[2] if test=='T08' else 'rest'
        n=int(tokens[3]);y=.3 if test=='T08' else float(tokens[2])
        if geom=='smooth':mesh=smooth_mesh(n);area=lambda x:.01*(1+.2*sin(pi*x)**2)
        elif geom=='frustum':
            mesh=segments_mesh([dict(length=1000,start_diameter=100,end_diameter=120)],1/n)
            area=lambda x:pi*(.1+.02*x)**2/4
        else:mesh=uniform_mesh(n)
        if mode=='rest':
            initial=reference=lambda x:(RHO,0.,P0,y);bc=(Boundary('wall'),Boundary('wall'))
        else:
            initial=reference=nozzle(area)
            bc=(Boundary('reservoir',p0=P0,T0=T0),Boundary('reservoir',p0=reference(1.)[2],T0=T0))
    elif test=='T09' and kind in ('inleft','inright'):
        u=(.2 if kind=='inleft' else -.2)*A0;end=.25/abs(u)
        initial=lambda x:(RHO,u,P0,.2)
        reference=lambda x:(RHO,u,P0,.8 if (x<.25 if u>0 else x>.75) else .2)
        refbreaks=[.25 if u>0 else .75]
        pt,tt=totals();inlet=Boundary('reservoir',p0=pt,T0=tt,Y0=.8);outlet=Boundary('reservoir',p0=P0,T0=T0,Y0=.2)
        bc=(inlet,outlet) if u>0 else (outlet,inlet)
    elif test=='T10':
        n=int(kind);mesh=uniform_mesh(n);u=.2*A0;end=1/u
        initial=reference=lambda x:(RHO*(1+.1*sin(2*pi*x)),u,P0,.5+.2*sin(2*pi*x))
    else:raise ValueError('Unknown case '+name)
    return dict(name=name,test=test,mesh=mesh,area=area,eos=eos,initial=initial,reference=reference,
                breaks=breaks,refbreaks=refbreaks,end=end,bc=bc,cfl=cfl,exact=exact,sensor=sensor,interval=interval)


def case_names():
    names=['T01_rest','T01_moving','T02_sod','T03','T04','T05','T06_contact',
           'T07_periodic','T07_closed','T07_open']
    # Static equilibrium before nozzle flow, all geometries and all meshes.
    names += [f'T08_{g}_{mode}_{n}' for mode in ('rest','flow') for g in ('constant','smooth','frustum') for n in (100,200,400)]
    names += ['T09_contact','T09_reverse','T09_inleft','T09_inright']
    names += [f'T10_{n}' for n in (100,200,400,800)]
    names += [f'T02_sod_{cfl}' for cfl in (.2,.4,.6)]+[f'T03_{cfl}' for cfl in (.2,.4,.6)]
    names += ['T12_expansion','T12_contact','T12_pure0','T12_pure1']
    names += [f'T12_frustum_{y}_{n}' for y in (0,1) for n in (100,200,400)]
    return names


def measure(case,result,reference,initial):
    mesh=case['mesh'];eos=case['eos'];name=case['name'];test=case['test']
    checks={};metrics={}
    def require(key,value,limit):metrics[key]=value;checks[key]=value<=limit
    checks['completed']=result['status']=='completed'
    require('worst_ledger',max((max(x['normalized']) for x in result['ledger']),default=0.),1e-10)
    if not checks['completed']:return metrics,checks
    scales=(RHO,A0,P0,1.) if eos==EOS else (1.,1.,1.,1.)
    actual=result['primitive'];ref=primitives(mesh,reference,eos)
    errors=fields_errors(actual,ref,mesh,scales);metrics['errors']=errors
    if test=='T01' or ('_rest_' in name) or (test=='T12' and '_frustum_' in name):
        for field in ('rho','u','p'):require(field+'_Linf',errors[field]['Linf'],1e-12)
        if test=='T01':
            require('Y_Linf',errors['Y']['Linf'],1e-12)
            temp=norms(result['temperature'],[w[2]/(w[0]*eos.R) for w in ref],mesh.volumes,T0)
            require('T_Linf',temp['Linf'],1e-12)
    elif test=='T02' or name=='T12_expansion':
        for field in (('rho','p','u') if test=='T02' else ('rho','p')):
            require(field+'_L1',errors[field]['L1'],.03 if test=='T02' else .05)
            if test=='T02':require(field+'_L2',errors[field]['L2'],.08)
        exact=case['exact'];metrics['reference_root_residual']=exact.residual
        if test=='T02':
            shock=.5+exact.waves[1][0]*case['end'];contact_pos=.5+exact.ustar*case['end'];dx=1/mesh.n
            for field,k,position in (('shock',2,shock),('contact',3,contact_pos)):
                candidates=[i for i in range(mesh.n-1) if abs((mesh.centers[i]+mesh.centers[i+1])/2-position)<=.05]
                i=max(candidates,key=lambda i:abs(actual[i+1][k]-actual[i][k])/(mesh.centers[i+1]-mesh.centers[i]))
                measured=(mesh.centers[i]+mesh.centers[i+1])/2;metrics[field+'_position']=measured;metrics[field+'_exact']=position
                if field=='contact':
                    metrics['contact_Y_gradient_position']=measured
                    ys=[w[3] for w in actual];xs=mesh.centers
                    crossings=[x for x,y in zip(xs,ys) if y==.5]
                    crossings += [x+(.5-y)*(xx-x)/(yy-y) for x,xx,y,yy in zip(xs,xs[1:],ys,ys[1:]) if (y-.5)*(yy-.5)<0]
                    if len(crossings)==1 and not any(a==b==.5 for a,b in zip(ys,ys[1:])):
                        center=crossings[0];metrics['contact_Y_half_position']=center
                        pairs=[((xs[i]+xs[i+1])/2,abs(ys[i+1]-ys[i])) for i in range(mesh.n-1) if abs((xs[i]+xs[i+1])/2-center)<=.05]
                        metrics['contact_Y_centroid_position']=fsum(x*w for x,w in pairs)/fsum(w for x,w in pairs)
                    detection=density_contact(mesh.centers,[w[:3] for w in actual],eos.gamma)
                    metrics['contact_detector']=detection['status']
                    checks['contact_unique']=detection['status']=='UNIQUE'
                    if not checks['contact_unique']:
                        checks['contact_position_error']=False
                        continue
                    measured=detection['position'];metrics['contact_position']=measured
                require(field+'_position_error',abs(measured-position),2*dx)
            left,right=sorted(.5+s*case['end'] for s in exact.waves[0])
            indices=[i for i,x in enumerate(mesh.centers) if left+3*dx<x<right-3*dx and abs(x-contact_pos)>3*dx and abs(x-shock)>3*dx]
            require('rarefaction_Linf',max(abs(actual[i][k]-ref[i][k]) for i in indices for k in (0,1,2)),.05)
    elif test=='T03':
        dp=[w[2]-P0 for w in actual];refdp=[w[2]-P0 for w in ref]
        error=norms(dp,refdp,mesh.volumes,1e-4*P0)
        require('pressure_L1',error['L1'],.025);require('pressure_L2',error['L2'],.08)
        initial_p=primitives(mesh,initial,eos)
        def center(ws,expected):
            pairs=[(x,abs(w[2]-P0)*v) for x,w,v in zip(mesh.centers,ws,mesh.volumes) if abs(x-expected)<=.15]
            den=fsum(v for x,v in pairs)
            if den<=0:raise ValueError('No acoustic signal')
            return fsum(x*v for x,v in pairs)/den
        speed=(center(actual,.25+A0*case['end'])-center(initial_p,.25))/case['end'];metrics['speed']=speed
        require('speed_relative_error',abs(speed/A0-1),.01)
        amplitude=max(dp);metrics['amplitude']=amplitude;metrics['amplitude_ratio']=amplitude/max(refdp)
        checks['amplitude_ratio']=.65<=metrics['amplitude_ratio']<=1.05
    elif test in ('T04','T05'):
        incident=[(t*A0,p-P0) for t,p in result['sensors'] if .30<=t*A0<=.50]
        reflected=[(t*A0,p-P0) for t,p in result['sensors'] if .90<=t*A0<=1.10]
        inc=max(p for t,p in incident);peak_t,amplitude=max(reflected,key=lambda pair:abs(pair[1]))
        coefficient=amplitude/max(abs(inc),1e-8*P0)
        metrics.update(incident_amplitude=inc,reflected_amplitude=amplitude,reflection_coefficient=coefficient,peak_time_scaled=peak_t)
        checks['incident_signal']=inc>=.5*1e-4*P0
        require('reflection_error',abs(coefficient-(1 if test=='T04' else -1)),.30)
        require('peak_time_error',abs(peak_t-1.),.02)
        if test=='T05':checks['negative_reflection']=amplitude<0
    elif test in ('T06','T09','T12'):
        opened='_inleft' in name or '_inright' in name
        require('Y_L1',errors['Y']['L1'],.04 if opened else .06)
        if not opened:require('rho_L1_halfscale',errors['rho']['L1']/2,.04)
        require('p_Linf',errors['p']['Linf'],1e-10);require('u_Linf',errors['u']['Linf'],1e-10)
        if opened:
            flux=result['face_fluxes'][0 if '_inleft' in name else -1]
            require('donor_relative_error',abs(flux[3]-.8*flux[0])/max(RHO*A0*.01,abs(flux[0])),1e-12)
            checks['flow_sign']=flux[0]>0 if '_inleft' in name else flux[0]<0
    elif test=='T08':
        if mesh.n==400:
            for field in ('rho','u','p'):require(field+'_L1',errors[field]['L1'],.01)
    elif test=='T10':
        density=norms([c[0]/v for c,v in zip(result['cells'],mesh.volumes)],[c[0]/v for c,v in zip(reference,mesh.volumes)],mesh.volumes,RHO)
        fresh=norms([c[3]/v for c,v in zip(result['cells'],mesh.volumes)],[c[3]/v for c,v in zip(reference,mesh.volumes)],mesh.volumes,RHO)
        metrics.update(density_L1=density['L1'],fresh_L1=fresh['L1'])
    return metrics,checks


def run_case(name,wall_limit=120.,progress=None):
    case=definition(name);mesh=case['mesh'];eos=case['eos']
    initial=cell_integrals(mesh,case['initial'],eos,case['area'],case['breaks'])
    reference=cell_integrals(mesh,case['reference'],eos,case['area'],case['refbreaks'])
    result=solve(mesh,initial,case['end'],case['bc'],eos=eos,cfl=case['cfl'],sensor=case['sensor'],
                 sample_interval=case['interval'],wall_limit=wall_limit,progress=progress)
    metrics,checks=measure(case,result,reference,initial)
    return dict(name=name,status='PASS' if all(checks.values()) else 'FAIL',checks=checks,metrics=metrics,
                configuration=dict(N=mesh.n,CFL=case['cfl'],R=eos.R,gamma=eos.gamma,final_time=case['end'],
                                   boundaries='periodic' if case['bc']=='periodic' else [b.__dict__ for b in case['bc']],method='FIRST_ORDER'),
                mesh=mesh.as_dict(),initial=initial,reference=reference,result=result)


def aggregate(records):
    by={r['name']:r for r in records};rows={f'T{i:02}':dict(status='PASS',checks={}) for i in range(1,13)}
    for r in records:
        test='T11' if r['name'].startswith(('T02_sod_','T03_')) else r['name'][:3]
        rows[test]['checks'][r['name']]=r['status']=='PASS'
    def comparison(test,key,ok,value):rows[test]['checks'][key]=ok;rows[test].setdefault('metrics',{})[key]=value
    for geom in ('constant','smooth','frustum'):
        for n,m in ((100,200),(200,400)):
            a=by[f'T08_{geom}_flow_{n}'];b=by[f'T08_{geom}_flow_{m}']
            if a['status']=='PASS' and b['status']=='PASS':
                for field in ('rho','u','p'):
                    old=a['metrics']['errors'][field]['L1'];new=b['metrics']['errors'][field]['L1']
                    comparison('T08',f'{geom}_{n}_{m}_{field}',new<=old+1e-12,dict(coarse=old,fine=new))
    for n,m in ((100,200),(200,400),(400,800)):
        a=by[f'T10_{n}'];b=by[f'T10_{m}']
        if a['status']=='PASS' and b['status']=='PASS':
            for field in ('density_L1','fresh_L1'):
                old=a['metrics'][field];new=b['metrics'][field]
                order=None if old<1e-12 and new<1e-12 else log2(old/new)
                comparison('T10',f'order_{n}_{m}_{field}',order is None or order>=.7,order)
    for cfl in (.4,.6):
        ref=by['T02_sod_0.2'];r=by[f'T02_sod_{cfl}']
        if ref['status']=='PASS' and r['status']=='PASS':
            for k,field in enumerate(('rho','u','p')):
                value=norms([w[k] for w in r['result']['primitive']],[w[k] for w in ref['result']['primitive']],r['mesh']['volumes'],1.)['L1']
                comparison('T11',f'Sod_{cfl}_{field}',value<=.015,value)
        ref=by['T03_0.2'];r=by[f'T03_{cfl}']
        if ref['status']=='PASS' and r['status']=='PASS':
            speed=abs(r['metrics']['speed']-ref['metrics']['speed'])/A0
            amplitude=abs(r['metrics']['amplitude']-ref['metrics']['amplitude'])/(1e-4*P0)
            comparison('T11',f'pulse_{cfl}_speed',speed<=.005,speed)
            comparison('T11',f'pulse_{cfl}_amplitude',amplitude<=.08,amplitude)
    for row in rows.values():row['status']='PASS' if row['checks'] and all(row['checks'].values()) else 'FAIL'
    return rows
