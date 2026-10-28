"""Frozen E2A preparation, bounded execution and pressure-wave analysis.

Uses existing IntegratedEngine2T APIs; never patches solver or model code.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from motorsim.integrated_2t import (IntegratedEngine2T, _solver_dependency_hashes,
    _integrated_scheduled_angles, _json_evidence_equal)
from motorsim.port_connection_v2 import SCHEMA, NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements,default_artifact_root
from scripts.diagnostics.diagnose_integrated_mesh_v1 import refined_configuration

PLAN=ROOT/'results/e2a-exhaust-waves-v1/preparation'
RAW_NAME='e2a-exhaust-waves-v1-20261028'
PROBES=(.04,.25,.55,.80,1.02)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,d):
    Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def variant_b(a):
    """Stretch only the cylindrical header, preserving initial primitives."""
    c=deepcopy(a);factor=103/83
    ex=next(d for d in c['ducts'] if d['id']=='exhaust')['mesh']
    if not math.isclose(ex['faces'][3],.083,abs_tol=1e-14):
        raise ValueError('expected original three-cell 83 mm header')
    ex['faces']=[x*factor if i<=3 else x+.020 for i,x in enumerate(ex['faces'])]
    ex['centers']=[x*factor if i<3 else x+.020 for i,x in enumerate(ex['centers'])]
    ex['volumes']=[v*factor if i<3 else v for i,v in enumerate(ex['volumes'])]
    c['duct_species']['exhaust']=[[x*factor for x in s] if i<3 else s
                                for i,s in enumerate(c['duct_species']['exhaust'])]
    c['geometry_identity']['chamber']['sections'][0]['length_mm']=103.
    c['geometry_identity']['pipe_sections_mm'][0][0]=103.
    for s in c['thermal_system']['surfaces']:
        location=c['thermal_locations'][s['id']]
        if location in ('exhaust:0','exhaust:1','exhaust:2'):
            s['area_m2']*=factor
    return c


def prepare(plan=PLAN):
    check_storage_requirements([(plan,5*1024**2)])
    if plan.exists():raise FileExistsError('preserve frozen preparation')
    source=default_artifact_root()/'port-flow-verification-v1-20261028/candidate'
    source_receipt=load(source/'receipt.json')
    if not source_receipt['numerical_gate']:raise ValueError('source gate failed')
    for name,key in [('configuration.json','configuration_sha256'),
                     ('primary-stages.jsonl.gz','primary_stages_sha256'),
                     ('terminal-checkpoint.json','terminal_checkpoint_sha256')]:
        if sha(source/name)!=source_receipt[key]:raise ValueError('source integrity changed')
    # No numerical product changes since this source was produced.
    changed=subprocess.check_output(['git','diff','--name-only','bd635de','--','motorsim'],cwd=ROOT).decode().strip()
    if changed:raise ValueError('reuse requires unchanged product source')
    a=load(source/'configuration.json');b=variant_b(a)
    if a['geometry_identity'].get('port_connection_model')!=SCHEMA:
        raise ValueError('expected explicit V2, same in both designs')
    if a['geometry_identity'].get('spatial_reconstruction_model'):
        raise ValueError('no spatial scheme switch authorized')
    fresh=IntegratedEngine2T.from_configuration_dict(a)
    if not _json_evidence_equal(fresh.snapshot(),load(source/'initial-checkpoint.json')):
        raise ValueError('source initial physical/configuration identity changed')
    configs={}
    for label,c in [('A44',a),('B44',b)]:
        configs[label]=c
        encoded=json.dumps(c,sort_keys=True).encode()
        configs[label.replace('44','88')]=refined_configuration(c,hashlib.sha256(encoded).hexdigest())
    plan.mkdir(parents=True)
    checks={}
    for name,c in configs.items():
        e=IntegratedEngine2T.from_configuration_dict(c)
        c=e.configuration_dict();configs[name]=c
        write(plan/(name+'.json'),c)
        checks[name]=dict(initial_inventory=e.inventory(),
            cells=sum(len(p['mesh']['volumes']) for p in c['ducts']),
            exhaust_length_m=next(p['mesh']['faces'][-1] for p in c['ducts'] if p['id']=='exhaust'))
    for v in ('A','B'):
        x,y=checks[v+'44']['initial_inventory'],checks[v+'88']['initial_inventory']
        pairs=[(x['mass_kg'],y['mass_kg']),(x['energy_J'],y['energy_J']),*zip(x['species_kg'],y['species_kg'])]
        if max(abs(p-q)/max(abs(p),abs(q),1e-30) for p,q in pairs)>1e-12:
            raise ValueError('refinement changed initial inventories')
    cases=[dict(name='A44-d05',config='A44',step=.5,reuse=True),
           dict(name='B44-d05',config='B44',step=.5,reuse=False),
           dict(name='A88-d05',config='A88',step=.5,reuse=False),
           dict(name='B88-d05',config='B88',step=.5,reuse=False),
           dict(name='A88-d025',config='A88',step=.25,reuse=False),
           dict(name='B88-d025',config='B88',step=.25,reuse=False)]
    manifest=dict(schema='DINO_E2A_FROZEN_PROTOCOL_V1',cases=cases,
        rpm=9000.,target_angle_deg=720.,sample_degrees=.5,probes_m=PROBES,
        probe_width_m=.010,window_phase_deg=[88.,272.],return_window_phase_deg=[150.,272.],
        reference_window_phase_deg=[70.,85.],comparison_cycle=2,
        solver_budget_wall_s=600.,execution_reserve_for_analysis_s=30.,case_budget_s=120.,
        rss_limit_mib=512,artifact_limit_bytes=1024**3,source_directory=str(source),
        source_files={p.name:sha(p) for p in (source/'configuration.json',source/'receipt.json',
            source/'initial-checkpoint.json',source/'terminal-checkpoint.json',source/'primary-stages.jsonl.gz')},
        model='V2_EXPERIMENTAL_FIRST_ORDER_OPEN_END_PLENUM_V2',initial_checks=checks,
        config_hashes={name:sha(plan/(name+'.json')) for name in configs},
        solver_dependency_sha256=_solver_dependency_hashes(),
        diagnostic_sha256=sha(__file__),
        compatibility_exclusions=['Legacy periodic A/B: different port law and initial trajectory',
            'Earlier mesh diagnostics: MUSCL or other model/configuration identity; no reuse as E2A uncertainty'],
        numerical_uncertainty='2*(abs(A88-A44)+abs(B88-B44)+abs(A88half-A88)+abs(B88half-B88))+sampling; empirical safety envelope, not rigorous bound or confidence interval',
        distinction='All controls complete and conservative. Same-sign peak-amplitude delta across three pairs and abs(delta)>envelope. Correlation lag must exceed its envelope, correlation>=.95, unique interior maximum. Otherwise difference not resolved. Reflection causality is a separate qualified claim.',
        scientific_state='TRANSIENT_SYNTHETIC_NOT_PERIODIC_NOT_EXPERIMENTAL_VALIDATION')
    write(plan/'manifest.json',manifest)
    print(json.dumps(dict(cases=len(cases),new_cases=5,reused='A44-d05',checks=checks)))


def frame(e):
    q=e.state['ducts']['exhaust'];g=e.eos.gamma
    w=[(x[0],x[1]/x[0],(g-1)*(x[2]-.5*x[1]**2/x[0])) for x in q]
    pc=[(g-1)*e.state['chambers'][n][1]/e.state['chambers'][n][2] for n in ('cylinder','crankcase')]
    return w,pc


def reuse_frames(source,config):
    """Extract identical physical samples; do not resume or recalculate A44."""
    e=IntegratedEngine2T.from_configuration_dict(config)
    data={0:frame(e)}
    with gzip.open(source/'primary-stages.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            r=json.loads(line);angle=r['angle_end_deg'];k=round(2*angle)
            if abs(angle-k/2)<1e-8:
                s=r['stage_states'][2];g=e.eos.gamma
                data[k]=([(q[0],q[1]/q[0],(g-1)*(q[2]-.5*q[1]**2/q[0])) for q in s['ducts']['exhaust']],
                    [(g-1)*s['chambers'][n][1]/s['chambers'][n][2] for n in ('cylinder','crankcase')])
    if sorted(data)!=list(range(1441)):raise ValueError('source lacks exact common samples')
    return [data[k][0] for k in range(1441)],[data[k][1] for k in range(1441)]


def residuals(e):
    r=e.conservation_report();i=e.initial_inventory
    return dict(mass=abs(r['mass']['residual'])/i['mass_kg'],
        energy=abs(r['energy']['residual'])/(i['energy_J']+sum(abs(v) for k,v in e.ledger.items() if isinstance(v,(float,int)) and k.endswith('_J'))),
        species=max(abs(s['residual']) for s in r['species'].values())/i['mass_kg'])


def execute(plan=PLAN):
    import psutil
    m=load(plan/'manifest.json')
    if sha(__file__)!=m['diagnostic_sha256'] or _solver_dependency_hashes()!=m['solver_dependency_sha256']:
        raise ValueError('frozen producer changed')
    root=default_artifact_root()/RAW_NAME
    preflight=check_storage_requirements([(root,m['artifact_limit_bytes'])])
    if root.exists():raise FileExistsError('one E2A execution only; preserve existing run')
    root.mkdir(parents=True)
    source=Path(m['source_directory'])
    for n,h in m['source_files'].items():
        if sha(source/n)!=h:raise ValueError('reused source changed')
    started=time.perf_counter();results=[];proc=psutil.Process()
    global_stop=started+m['solver_budget_wall_s']-m['execution_reserve_for_analysis_s']
    for case in m['cases']:
        if time.perf_counter()>=global_stop:break
        out=root/case['name'];out.mkdir()
        cfg=load(plan/(case['config']+'.json'))
        if sha(plan/(case['config']+'.json'))!=m['config_hashes'][case['config']]:raise ValueError('frozen config changed')
        e=IntegratedEngine2T.from_configuration_dict(cfg)
        write(out/'configuration.json',cfg)
        initial=e.snapshot();write(out/'checkpoint-000.json',initial)
        case_start=time.perf_counter();solver_s=0.;recipe=[];status='COMPLETE';error=None;peak=0.
        frames=[];chambers=[]
        try:
            if case['reuse']:
                frames,chambers=reuse_frames(source,cfg)
                old=load(source/'receipt.json')
                e.restore(load(source/'terminal-checkpoint.json'))
                original_solver_s=old['compute_s']
            else:
                w,p=frame(e);frames.append(w);chambers.append(p)
                scheduled=sorted(_integrated_scheduled_angles(e,720.))
                while e.crank_angle_unwrapped_deg<720.-1e-9:
                    if time.perf_counter()>=min(global_stop,case_start+m['case_budget_s']):
                        raise TimeoutError('frozen case/global budget reached; no automatic extension')
                    if len(recipe)%20==0:
                        peak=max(peak,proc.memory_info().rss/1024**2)
                        if peak>m['rss_limit_mib']:raise MemoryError('RSS budget reached')
                    a=e.crank_angle_unwrapped_deg
                    targets=[720.,(math.floor((a+1e-9)/case['step'])+1)*case['step']]
                    targets.extend(t for t in scheduled if t>a+1e-9)
                    da=min(targets)-a;rejected=[]
                    for _ in range(25):
                        tick=time.perf_counter()
                        try:r=e.step(da/54000.,da,capture_trace=False)
                        except NoAdmissiblePortState:raise
                        except ValueError as exc:
                            if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                            rejected.append(dict(delta_angle_deg=da,error=str(exc)));da/=2
                        else:break
                        finally:solver_s+=time.perf_counter()-tick
                    else:raise RuntimeError('25 rejected trials')
                    recipe.append(dict(**r,rejected_proposals=rejected))
                    a=e.crank_angle_unwrapped_deg;k=round(a*2)
                    if abs(a-k/2)<1e-8:
                        if len(frames)!=k:raise ValueError('common sampling phase is missing or duplicated')
                        w,p=frame(e);frames.append(w);chambers.append(p)
                    if abs(a%360)<1e-9:
                        e.compact_fast_recipe_cycle()
                        write(out/('checkpoint-%03d.json'%round(a/360)),e.snapshot())
                if len(frames)!=1441:raise ValueError('incomplete common sampling')
                original_solver_s=None
        except Exception as exc:
            status,error='STOPPED',type(exc).__name__+': '+str(exc)
        if e.accepted_steps==0:
            terminal=e.snapshot();kind='NATIVE_CHECKPOINT'
        else:
            terminal=e.fast_recipe_terminal_state();kind='FAST_TERMINAL_PLUS_RECIPE'
        write(out/'terminal.json',terminal);write(out/'recipe.json',recipe)
        np.savez_compressed(out/'fields.npz',angles=np.arange(len(frames))*.5,
            field=np.asarray(frames),chamber_pressures=np.asarray(chambers))
        rr=residuals(e)
        restore_equal=False
        if kind=='NATIVE_CHECKPOINT':
            fresh=IntegratedEngine2T.from_configuration_dict(cfg);fresh.restore(terminal)
            restore_equal=_json_evidence_equal(fresh.snapshot(),terminal)
        result=dict(name=case['name'],status=status,error=error,reused=case['reuse'],
            new_solver_s=solver_s,original_reused_solver_s=original_solver_s,
            wall_s=time.perf_counter()-case_start,terminal_angle_deg=e.crank_angle_unwrapped_deg,
            accepted_steps=len(recipe),peak_rss_mib=peak,normalized_residuals=rr,
            checkpoint_kind=kind,checkpoint_restore_exact=restore_equal,
            gate=status=='COMPLETE' and restore_equal and rr['mass']<=1e-9
                and rr['species']<=1e-9 and rr['energy']<=1e-8,
            hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()})
        write(out/'receipt.json',result);results.append(result)
        write(root/'progress.json',dict(cases=results,elapsed_wall_s=time.perf_counter()-started))
        print(json.dumps({k:result[k] for k in ('name','status','error','wall_s','new_solver_s','peak_rss_mib','gate')}),flush=True)
        if not result['gate']:break
        if sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>m['artifact_limit_bytes']:break
    receipt=dict(schema='DINO_E2A_EXECUTION_V1',cases=results,wall_s=time.perf_counter()-started,
        completed=len(results)==6 and all(r['gate'] for r in results),
        manifest_sha256=sha(plan/'manifest.json'),storage_preflight=preflight,
        analysis_reserve_s=30.,raw_root=str(root),scientific_state=m['scientific_state'])
    write(root/'receipt.json',receipt)
    print(json.dumps(dict(complete=receipt['completed'],wall_s=receipt['wall_s'])))


def overlap_weights(mesh,x,width=.01):
    """Exact frustum-volume weights for a fixed physical sensor window."""
    lo,hi=x-width/2,x+width/2;weights=[]
    for i,(l,r) in enumerate(zip(mesh['faces'],mesh['faces'][1:])):
        a,b=max(l,lo),min(r,hi)
        if b<=a:weights.append(0.);continue
        rl,rr=math.sqrt(mesh['areas'][i]),math.sqrt(mesh['areas'][i+1])
        ra=rl+(rr-rl)*(a-l)/(r-l);rb=rl+(rr-rl)*(b-l)/(r-l)
        weights.append((b-a)*(ra*ra+ra*rb+rb*rb)/3)
    w=np.asarray(weights)
    if w.sum()<=0:raise ValueError('sensor outside physical duct')
    return w/w.sum()


def lag(a,b,max_lag=40):
    """Positive lag means B arrives later; offset-invariant correlation."""
    scores=[]
    for k in range(-max_lag,max_lag+1):
        x,y=(a[-k:],b[:len(b)+k]) if k<0 else (a[:len(a)-k or None],b[k:])
        x=x-x.mean();y=y-y.mean();den=np.linalg.norm(x)*np.linalg.norm(y)
        scores.append(float(np.dot(x,y)/den) if den else -1.)
    j=int(np.argmax(scores));k=j-max_lag;interior=0<j<len(scores)-1
    shift=0.
    if interior:
        z=scores[j-1]-2*scores[j]+scores[j+1]
        if z<0:shift=.5*(scores[j-1]-scores[j+1])/z
    # A second separated maximum is not evidence of a unique transit time.
    alternatives=[scores[i] for i in range(1,len(scores)-1) if abs(i-j)>2
                  and scores[i]>=scores[i-1] and scores[i]>=scores[i+1]]
    unique=not alternatives or scores[j]-max(alternatives)>.01
    return dict(lag_deg=(k+shift)*.5,correlation=scores[j],valid=interior and unique and scores[j]>=.95)


def analyze(plan=PLAN):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    started=time.perf_counter();m=load(plan/'manifest.json');root=default_artifact_root()/RAW_NAME
    execution=load(root/'receipt.json');out=ROOT/'results/e2a-exhaust-waves-v1'
    traces={};metrics={};acoustic={};data={}
    for r in execution['cases']:
        if not r['gate']:continue
        d=root/r['name'];cfg=load(d/'configuration.json');npz=np.load(d/'fields.npz')
        f=npz['field'];angles=npz['angles'];mask=(angles>=360)&(angles<=720)
        phase=angles[mask]-360;f=f[mask];mesh=next(p['mesh'] for p in cfg['ducts'] if p['id']=='exhaust')
        probe=np.stack([np.einsum('i,tij->tj',overlap_weights(mesh,x),f) for x in PROBES],axis=1)
        p=probe[:,:,2];win=(phase>=88)&(phase<=272);base=(phase>=70)&(phase<=85)
        amp=float(np.max(p[win,0])-101325.)
        peak_phase=float(phase[win][np.argmax(p[win,0])]);impulse=float(np.trapezoid(p[win,0]-101325.,phase[win]/54000.))
        traces[r['name']]=(phase,p,probe);data[r['name']]=(f,mesh)
        coarse_indices=np.where(win)[0][::2]
        coarse_impulse=float(np.trapezoid(p[coarse_indices,0]-101325.,phase[coarse_indices]/54000.))
        metrics[r['name']]=dict(amplitude_pa=amp,peak_phase_deg=peak_phase,impulse_pa_s=impulse,
            sampling_amplitude_pa=.5*float(np.max(np.abs(np.diff(p[win,0])))),
            sampling_impulse_pa_s=2*abs(impulse-coarse_impulse))
        reference=probe[base,0].mean(axis=0);rho,u,p0=reference;aa=math.sqrt(1.35*p0/rho)
        dp=probe[:,0,2]-p0;du=probe[:,0,1]-u;dr=probe[:,0,0]/rho
        entropy=np.log(probe[:,0,2]/p0)-1.35*np.log(dr)
        valid=(np.abs(dp)/p0<=.05)&(np.abs(du)/aa<=.05)&(np.abs(dr-1)<=.05)&(np.abs(entropy)<=.01)&(abs(u)/aa<=.3)
        plus=.5*(dp+rho*aa*du);minus=.5*(dp-rho*aa*du)
        ret=(phase>=150)&(phase<=272)
        acoustic[r['name']]=dict(reference_rho_u_p=reference.tolist(),reference_sound_m_s=aa,
            valid_fraction_return=float(valid[ret].mean()),valid=valid,plus=plus,minus=minus,
            return_phase_deg=None,candidate_upstream_peak_phase_deg=None,
            qualification='Linear characteristic projections only where small-perturbation/entropy guards pass; a local upstream component is not a causally identified reflection')
        candidates=np.where(ret&valid)[0]
        if len(candidates):
            k=int(candidates[np.argmax(np.abs(minus[candidates]))])
            if k>0 and k<len(valid)-1 and np.all(valid[k-1:k+2]):
                acoustic[r['name']]['candidate_upstream_peak_phase_deg']=float(phase[k])
    pairs=[('A44-d05','B44-d05'),('A88-d05','B88-d05'),('A88-d025','B88-d025')]
    comparisons=[];decision='DIFERENCIA NO RESUELTA'
    if execution['completed']:
        for a,b in pairs:
            phase,p,_=traces[a];pb=traces[b][1];w=(phase>=88)&(phase<=272)
            comparison=dict(pair=[a,b],delta_amplitude_pa=metrics[b]['amplitude_pa']-metrics[a]['amplitude_pa'],
                delta_peak_phase_deg=metrics[b]['peak_phase_deg']-metrics[a]['peak_phase_deg'],
                delta_impulse_pa_s=metrics[b]['impulse_pa_s']-metrics[a]['impulse_pa_s'],
                trace_L1_difference_pa=float(np.mean(np.abs(pb[w,0]-p[w,0]))),
                trace_L2_difference_pa=float(np.sqrt(np.mean((pb[w,0]-p[w,0])**2))),
                trace_Linf_difference_pa=float(np.max(np.abs(pb[w,0]-p[w,0]))),
                phase_correlation=lag(p[w,0],pb[w,0]))
            comparisons.append(comparison)
        envelopes={}
        for key in ('amplitude_pa','peak_phase_deg','impulse_pa_s'):
            q={n:metrics[n][key] for n in metrics}
            space=abs(q['A88-d05']-q['A44-d05'])+abs(q['B88-d05']-q['B44-d05'])
            temporal=abs(q['A88-d025']-q['A88-d05'])+abs(q['B88-d025']-q['B88-d05'])
            sample=(.5 if key=='peak_phase_deg' else sum(metrics[n]['sampling_'+key]
                for n in ('A88-d025','B88-d025')))
            delta=q['B88-d025']-q['A88-d025'];u=2*(space+temporal)+sample
            signs=[np.sign(metrics[b][key]-metrics[a][key]) for a,b in pairs]
            envelopes[key]=dict(delta=delta,spatial_sensitivity_sum=space,temporal_sensitivity_sum=temporal,
                safety_envelope=u,distinguishable=abs(delta)>u and len(set(signs))==1,
                qualification='Empirical sensitivity envelope; no confidence level or rigorous error bound')
        la=[c['phase_correlation']['lag_deg'] for c in comparisons]
        # Phase envelope also uses individual peak sensitivities, so common
        # phase-error cancellation is not silently assumed.
        lu=max(envelopes['peak_phase_deg']['safety_envelope'],2*(abs(la[1]-la[0])+abs(la[2]-la[1]))+.5)
        phase_pass=all(c['phase_correlation']['valid'] for c in comparisons) and abs(la[2])>lu and len(set(np.sign(la)))==1
        envelopes['correlation_lag_deg']=dict(delta=la[2],safety_envelope=lu,distinguishable=bool(phase_pass))
        if envelopes['amplitude_pa']['distinguishable'] and phase_pass:decision='DIFERENCIA DISTINGUIBLE'
    else:envelopes={}
    fig,axs=plt.subplots(3,1,figsize=(10,10),sharex=True,layout='constrained')
    for a,b,style in [('A44-d05','B44-d05',':'),('A88-d05','B88-d05','--'),('A88-d025','B88-d025','-')]:
        for n,color in [(a,'#1668aa'),(b,'#c33d30')]:
            if n not in traces:continue
            ph,p,_=traces[n];axs[0].plot(ph,p[:,0]/1000,style,color=color,label=n,lw=1.2)
    axs[0].set(ylabel='Presión P1 (kPa)',title='E2A · segundo ciclo transitorio · sonda x=0,040 m')
    axs[0].legend(ncol=3,fontsize=8);axs[0].axhline(101.325,color='gray',lw=.6)
    for a,b,style in [('A44-d05','B44-d05',':'),('A88-d05','B88-d05','--'),('A88-d025','B88-d025','-')]:
        if a in traces and b in traces:
            axs[1].plot(traces[a][0],(traces[b][1][:,0]-traces[a][1][:,0])/1000,style,label=b.split('-')[0],lw=1.2)
    axs[1].set(ylabel='B − A (kPa)');axs[1].legend();axs[1].axhline(0,color='gray',lw=.6)
    if execution['completed']:
        pp={n:t[1][:,0] for n,t in traces.items()}
        band=2*(abs(pp['A88-d05']-pp['A44-d05'])+abs(pp['B88-d05']-pp['B44-d05'])+
            abs(pp['A88-d025']-pp['A88-d05'])+abs(pp['B88-d025']-pp['B88-d05']))/1000
        axs[1].fill_between(traces['A88-d025'][0],-band,band,color='gray',alpha=.18,
            label='Envolvente de sensibilidad, no cota')
        axs[1].legend(fontsize=8)
    for n in ('A88-d025','B88-d025'):
        if n in traces:
            ac=acoustic[n];ph=traces[n][0]
            axs[2].plot(ph,np.where(ac['valid'],ac['plus'],np.nan)/1000,label=n[0]+' π+ válida')
            axs[2].plot(ph,np.where(ac['valid'],ac['minus'],np.nan)/1000,'--',label=n[0]+' π− válida')
    axs[2].set(ylabel='Proyección acústica (kPa)',xlabel='Ángulo de cigüeñal, segundo ciclo (°)',
        title='Componentes sólo bajo hipótesis acústica local; huecos = no separable')
    axs[2].legend(ncol=2,fontsize=8)
    for ax in axs:ax.set_xlim(70,300);ax.grid(alpha=.2)
    fig.savefig(out/'pressure-comparison.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    available=[n for n in ('A88-d025','B88-d025','A88-d05','B88-d05','A44-d05','B44-d05') if n in data]
    preferred=[next((n for n in available if n.startswith(v)),None) for v in ('A','B')]
    if all(preferred):
        vmax=max(float(data[n][0][:,:,2].max()/1000) for n in preferred)
        vmin=min(float(data[n][0][:,:,2].min()/1000) for n in preferred)
        for ax,n in zip(axs,preferred):
            f,mesh=data[n];ph=traces[n][0];edges=np.r_[ph-.25,ph[-1]+.25]
            im=ax.pcolormesh(mesh['faces'],edges,f[:,:,2]/1000,vmin=vmin,vmax=vmax,cmap='RdBu_r',shading='flat')
            for x in PROBES:ax.axvline(x,color='black',ls=':',lw=.5)
            ax.set(xlabel='Distancia física desde lumbrera (m)',ylabel='Ángulo segundo ciclo (°)',title=n+' · celdas reales, sin interpolación',ylim=(70,300))
        fig.colorbar(im,ax=axs,label='Presión (kPa)',shrink=.8)
    fig.savefig(out/'pressure-propagation.png',dpi=170);plt.close(fig)
    with (out/'metrics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['case','amplitude_pa','peak_phase_deg','impulse_pa_s',
            'sampling_amplitude_pa','sampling_impulse_pa_s']);writer.writeheader()
        for n,q in metrics.items():writer.writerow(dict(case=n,**q))
    with (out/'pressure-probes.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['case','phase_deg','probe_x_m','rho_kg_m3','velocity_m_s','pressure_pa'])
        for name,(ph,p,probe) in traces.items():
            for i,angle in enumerate(ph):
                for j,x in enumerate(PROBES):writer.writerow([name,angle,x,*probe[i,j]])
    serial_acoustic={n:{k:v for k,v in d.items() if k not in ('valid','plus','minus')} for n,d in acoustic.items()}
    elapsed=time.perf_counter()-started
    total=execution['wall_s']+elapsed
    if total>600:decision='DIFERENCIA NO RESUELTA'
    result=dict(schema='DINO_E2A_DECISION_V1',decision=decision,metrics=metrics,
        pair_comparisons=comparisons,numerical_envelopes=envelopes,acoustic_qualification=serial_acoustic,
        execution_wall_s=execution['wall_s'],analysis_wall_s=elapsed,total_comparison_wall_s=total,
        budget_pass=total<=600,complete=execution['completed'],raw_artifact_root=str(root),
        source_manifest_sha256=sha(plan/'manifest.json'),execution_receipt_sha256=sha(root/'receipt.json'),
        solver_unchanged=_solver_dependency_hashes()==m['solver_dependency_sha256'],
        scientific_state=m['scientific_state'],review='SELF_REVIEW')
    write(out/'decision.json',result)
    print(json.dumps(dict(decision=decision,total_comparison_wall_s=total,envelopes=envelopes)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','execute','analyze'])
    args=p.parse_args();dict(prepare=prepare,execute=execute,analyze=analyze)[args.mode]()
