"""Read-only postprocessing of the single frozen second-order experiment."""
import csv
import json
import math
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts.agents.storage_preflight import default_artifact_root
from scripts.diagnostics.e2_spatial_waves_v1 import load,write,sha,overlap_weights,lag,PROBES


def summarize():
    started=time.perf_counter()
    out=ROOT/'results/e2-spatial-waves-v1'
    base=ROOT/'results/e2a-exhaust-waves-v1'
    raw=default_artifact_root()/'e2-spatial-waves-v1-20261028'
    oldraw=default_artifact_root()/'e2a-exhaust-waves-v1-20261028'
    decision=load(out/'decision.json');old=load(base/'decision.json')
    execution=load(raw/'receipt.json');oldexecution=load(base/'execution-receipt.json')
    verification=load(out/'verification.json')
    regression_path=out/'runlogs/p4-p8-regression.summary.json'
    regression=load(regression_path) if regression_path.exists() else None
    retry_path=out/'runlogs/p4-p8-artifact-retry.summary.json'
    retry=load(retry_path) if retry_path.exists() else None
    resolution=load(out/'artifact-resolution.json') if (out/'artifact-resolution.json').exists() else None
    preservation_pass=regression is None or regression['exit_code']==0
    if regression and retry and resolution:
        expected=['tests/test_p4_g2_v2_recovery.py::'+t for t in resolution['rerun_tests']]
        failed=[line.split(' ',1)[1] for line in regression['tail'] if line.startswith('FAILED ')]
        preservation_pass=(retry['exit_code']==0 and resolution['hashes_verified']
            and set(failed)==set(expected) and all(t in retry['command'] for t in expected)
            and any('3 failed, 298 passed, 3 skipped' in line for line in regression['tail']))
    wrapper_overhead=max(0.,load(out/'runlogs/verification.summary.json')['duration_s']-verification['wall_s'])
    wrapper_overhead+=max(0.,load(out/'runlogs/integrated.summary.json')['duration_s']-execution['wall_s'])
    oldcost=sum(r['original_reused_solver_s'] if r['reused'] else r['new_solver_s']
                for r in oldexecution['cases'])
    newcost=sum(r['new_solver_s'] for r in execution['cases'])
    ratio=newcost/oldcost
    sensitivity={}
    for key,entry in decision['numerical_envelopes'].items():
        if 'spatial_sensitivity_sum' in entry:
            previous=old['numerical_envelopes'][key]['spatial_sensitivity_sum']
            sensitivity[key]=dict(first_order=previous,muscl=entry['spatial_sensitivity_sum'],
                reduction_fraction=1-entry['spatial_sensitivity_sum']/previous if previous else None)
    material=bool(sensitivity and sensitivity['amplitude_pa']['reduction_fraction']>=.30)
    controls=execution['completed'] and verification['passed'] and preservation_pass
    resolved=decision['decision']=='DIFERENCIA DISTINGUIBLE'
    adoption='MANTENER EXPERIMENTAL'
    if (not verification['passed'] or any(r['status']=='COMPLETE' and not r['gate'] for r in execution['cases'])
        or any(r['error'] and r['status']!='COMPLETE' and not r['error'].startswith('TimeoutError')
               for r in execution['cases']) or ratio>3):
        adoption='DESCARTAR'
    elif controls and material and resolved and ratio<=3:
        adoption='ADOPTAR COMO CANDIDATO'
    timing=[];probes=[];signals={}
    for label,root,receipt in [('first_order',oldraw,oldexecution),('muscl_v2',raw,execution)]:
        for r in receipt['cases']:
            if not r['gate']:continue
            d=root/r['name'];cfg=load(d/'configuration.json')
            fields=np.load(d/'fields.npz');angles=fields['angles']
            mask=(angles>=360)&(angles<=720);phase=angles[mask]-360
            mesh=next(p['mesh'] for p in cfg['ducts'] if p['id']=='exhaust')
            p=np.stack([fields['field'][mask,:,2]@overlap_weights(mesh,x) for x in PROBES],axis=1)
            signals[label,r['name']]=(phase,p)
            window=(phase>=88)&(phase<=272)
            for j,x in enumerate(PROBES):
                k=np.argmax(p[window,j]);previous=None
                if j:previous=lag(p[window,j-1],p[window,j])
                probes.append(dict(scheme=label,case=r['name'],probe_x_m=x,
                    amplitude_pa=float(p[window,j].max()-101325.),
                    peak_phase_deg=float(phase[window][k]),
                    previous_probe_correlation_lag_deg=None if previous is None else previous['lag_deg'],
                    previous_probe_correlation_valid=None if previous is None else previous['valid']))
            if label=='muscl_v2':
                recipe=load(d/'recipe.json')
                dt=np.array([x['dt_s'] for x in recipe])
                timing.append(dict(case=r['name'],steps=len(recipe),solver_s=r['new_solver_s'],
                    dt_min_s=float(dt.min()) if len(dt) else None,
                    dt_median_s=float(np.median(dt)) if len(dt) else None,
                    dt_max_s=float(dt.max()) if len(dt) else None,
                    rejected_trials=sum(len(x['rejected_proposals']) for x in recipe)))
    with (out/'propagation-metrics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(probes[0]));writer.writeheader();writer.writerows(probes)
    mesh_errors=[]
    for scheme in ('first_order','muscl_v2'):
        for variant in ('A','B'):
            if (scheme,variant+'88-d05') not in signals:continue
            phase,fine=signals[scheme,variant+'88-d05'];coarse=signals[scheme,variant+'44-d05'][1]
            window=(phase>=88)&(phase<=272)
            for j,x in enumerate(PROBES):
                diff=fine[window,j]-coarse[window,j]
                mesh_errors.append(dict(scheme=scheme,variant=variant,probe_x_m=x,
                    pressure_L1_pa=float(np.mean(abs(diff))),
                    pressure_L2_pa=float(np.sqrt(np.mean(diff**2))),
                    pressure_Linf_pa=float(np.max(abs(diff))),
                    qualification='Difference between physical window observations; not error against exact solution'))
    write(out/'mesh-trace-differences.json',mesh_errors)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for col,variant in enumerate(('A','B')):
        for scheme,style in [('first_order','--'),('muscl_v2','-')]:
            for grid,color in [('44','#888888'),('88','#1668aa')]:
                name=variant+grid+'-d05'
                if (scheme,name) in signals:
                    ph,p=signals[scheme,name]
                    axs[0,col].plot(ph,p[:,0]/1000,style,color=color,label=scheme+' '+grid)
        axs[0,col].set(title=variant+' · misma sonda P1',ylabel='Presión (kPa)',xlabel='Segundo ciclo (°)',xlim=(88,272))
        axs[0,col].legend(fontsize=8);axs[0,col].grid(alpha=.2)
    for model,style in [('legacy','--o'),('muscl','-o')]:
        rows=[r for r in verification['pulse']['cases'] if r['model']==model]
        axs[1,0].loglog([r['n'] for r in rows],[r['pressure_L1'] for r in rows],style,label=model)
    axs[1,0].set(xlabel='Celdas · pulso acústico aislado',ylabel='Error L1 presión (unidades de referencia)')
    axs[1,0].legend();axs[1,0].grid(alpha=.2)
    for scheme,style in [('first_order','--o'),('muscl_v2','-o')]:
        values=[]
        for x in PROBES:
            def amp(n):return next(r['amplitude_pa'] for r in probes if r['scheme']==scheme and r['case']==n and r['probe_x_m']==x)
            try:values.append(sum(abs(amp(v+'88-d05')-amp(v+'44-d05')) for v in ('A','B'))/1000)
            except StopIteration:values.append(float('nan'))
        axs[1,1].plot(PROBES,values,style,label=scheme)
    axs[1,1].set(xlabel='Sonda física (m)',ylabel='Suma sensibilidad espacial amplitud (kPa)')
    axs[1,1].legend();axs[1,1].grid(alpha=.2)
    fig.savefig(out/'first-vs-second-order.png',dpi=160);plt.close(fig)
    # Preserve small receipt in Git; large native checkpoints/arrays stay in artifact root.
    shutil.copyfile(raw/'receipt.json',out/'execution-receipt.json')
    index=[dict(path=p.relative_to(raw).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
           for p in sorted(raw.rglob('*')) if p.is_file()]
    write(out/'artifact-index.json',dict(artifact_root_relative=raw.name,files=index,total_bytes=sum(r['bytes'] for r in index)))
    residuals={k:max(r['normalized_residuals'][k] for r in execution['cases']) for k in ('mass','energy','species')}
    post=time.perf_counter()-started
    cumulative=decision['total_comparison_wall_s']+post+wrapper_overhead+(regression['duration_s'] if regression else 0.)
    cumulative+=(retry['duration_s'] if retry else 0.)+(resolution['charged_extra_io_s'] if resolution else 0.)
    if cumulative>600:adoption='MANTENER EXPERIMENTAL'
    result=dict(schema='DINO_E2_SPATIAL_ADOPTION_V1',adoption=adoption,
        wave_decision=decision['decision'],controls_complete=controls,material_improvement=material,
        spatial_sensitivity=sensitivity,solver_cost_ratio=ratio,solver_s=newcost,
        original_equivalent_solver_s=oldcost,maximum_relative_conservation_residuals=residuals,
        timing=timing,total_charged_wall_s=cumulative,budget_pass=cumulative<=600,
        verification_wall_s=verification['wall_s'],execution_wall_s=execution['wall_s'],
        analysis_wall_s=decision['analysis_wall_s'],postprocessing_wall_s=post,
        measured_launcher_overhead_s=wrapper_overhead,
        p4_p8_regression=regression,
        p4_p8_artifact_retry=retry,preservation_pass=preservation_pass,
        artifact_resolution=resolution,
        artifact_bytes=sum(r['bytes'] for r in index),review='SELF_REVIEW',
        solver_changes=False,implementation='Existing integrated MUSCL boundary V2 explicitly activated in four new versioned configs',
        scientific_state='TRANSIENT_SYNTHETIC;NOT_PERIODIC;NOT_EXPERIMENTALLY_VALIDATED',
        baseline_rc7='UNCHANGED',next_action='STOP;E2B_NOT_STARTED',
        execution_sha256=sha(raw/'receipt.json'),baseline_decision_sha256=sha(base/'decision.json'))
    write(out/'adoption.json',result)
    print(json.dumps({k:result[k] for k in ('adoption','wave_decision','controls_complete',
        'solver_cost_ratio','total_charged_wall_s','budget_pass','preservation_pass')}))


if __name__=='__main__':summarize()
