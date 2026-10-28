"""E2B report from existing checkpoints and audited final-cycle evidence only."""
import csv
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts.agents.storage_preflight import default_artifact_root
from scripts.diagnostics.e2b_periodic_ab_v1 import OUT,RAW_NAME,load,write,sha
from scripts.diagnostics.e2a_exhaust_waves_v1 import PROBES,overlap_weights,lag


def main():
    start=time.perf_counter();raw=default_artifact_root()/RAW_NAME
    execution=load(raw/'receipt.json');manifest=load(OUT/'manifest.json')
    cases={};convergence=[];signals={};interface_rows=[]
    for simulation in execution['simulations']:
        v=simulation['variant'];d=raw/v
        rows=load(d/'cycles.json')
        for r in rows:
            convergence.append(dict(variant=v,cycle=r['cycle'],wall_s=r['wall_s'],
                maximum_ratio=r['maximum_ratio'],p90=r['p90'],median=r['median'],failed=r['failed'],
                indicated_work_j=r['performance']['cylinder_indicated_work_j'],
                brake_power_w=r['performance']['brake_power_w']))
        if v not in execution['audited_variants']:continue
        period=simulation['detected_period'];n=simulation['converged_cycle'];final=rows[-period:]
        perf={key:float(np.mean([r['performance'][key] for r in final])) for key in final[0]['performance']}
        charges=[load(d/f'charge-{c:03}.json') for c in range(n-period+1,n+1)]
        charge={key:float(np.mean([r[key] for r in charges])) for key in charges[0] if isinstance(charges[0][key],(int,float))}
        cfg=load(d/'configuration.json');mesh=next(p['mesh'] for p in cfg['ducts'] if p['id']=='exhaust')
        for cycle in range(n-period+1,n+1):
            fields=np.load(d/f'waves-{cycle:03}.npz');phase=fields['phase_deg']
            if not np.array_equal(phase,np.arange(721)*.5):raise ValueError('pressure phases differ')
            f=fields['field'];p=np.stack([f[:,:,2]@overlap_weights(mesh,x) for x in PROBES],axis=1)
            signals[v,cycle]=dict(phase=phase,pressure=p,field=f,mesh=mesh)
            flows=load(d/f'interfaces-{cycle:03}.json')
            for duct,ends in flows.items():
                for side,totals in ends.items():
                    interface_rows.append(dict(variant=v,cycle=cycle,duct=duct,side=side,
                        positive_mass_kg=totals['gas_positive'][0],
                        negative_mass_magnitude_kg=-totals['gas_negative'][0],
                        net_mass_kg=totals['gas_net'][0],net_energy_j=totals['gas_net'][2]))
        cases[v]=dict(period=period,converged_cycle=n,performance_mean_per_revolution=perf,
            last3_cycle_variation_not_numerical_uncertainty={key:dict(
                minimum=min(r['performance'][key] for r in rows[-3:]),
                maximum=max(r['performance'][key] for r in rows[-3:]))
                for key in ('cylinder_indicated_work_j','brake_work_j','brake_power_w')},
            charge_at_last_port_close_mean=charge,charge_definition=charges[0]['closure_role'],
            final_streak_primary_audited=True,solver_s=simulation['solver_s'],
            wall_s=simulation['wall_s'],peak_rss_mib=simulation['peak_rss_mib'],
            max_relative_conservation_residuals={key:max(r['balances'][key] for r in rows) for key in ('mass','energy','species')},
            mean_last5_s_per_cycle=float(np.mean([r['wall_s'] for r in rows[-5:]])))
    differences={};wave={}
    if set(cases)=={'A','B'}:
        for key,a in cases['A']['performance_mean_per_revolution'].items():
            b=cases['B']['performance_mean_per_revolution'][key]
            differences[key]=dict(A=a,B=b,B_minus_A=b-a,relative_percent=100*(b-a)/abs(a) if a else None,
                numerical_uncertainty=None,numerically_distinguishable=False)
        a=signals['A',cases['A']['converged_cycle']];b=signals['B',cases['B']['converged_cycle']]
        win=(a['phase']>=88)&(a['phase']<=272)
        for j,x in enumerate(PROBES):
            pa,pb=a['pressure'][win,j],b['pressure'][win,j];ph=a['phase'][win]
            wave[str(x)]=dict(A_amplitude_pa=float(pa.max()-101325),B_amplitude_pa=float(pb.max()-101325),
                A_peak_phase_deg=float(ph[pa.argmax()]),B_peak_phase_deg=float(ph[pb.argmax()]),
                correlation=lag(pa,pb),trace_L1_pa=float(np.mean(abs(pb-pa))),
                qualification='Last observed branch if period2; no reflected/incident attribution, no power uncertainty')
    for name,rows in [('cycle-evolution.csv',convergence),('interface-flows.csv',interface_rows)]:
        if not rows:continue
        with (OUT/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(10,7),layout='constrained')
    for v in ('A','B'):
        rows=[r for r in convergence if r['variant']==v]
        if not rows:continue
        axes[0].plot([r['cycle'] for r in rows],[r['indicated_work_j'] for r in rows],label=v)
        axes[1].semilogy([r['cycle'] for r in rows if r['maximum_ratio'] is not None],
            [r['maximum_ratio'] for r in rows if r['maximum_ratio'] is not None],label=v)
    axes[0].set(ylabel='Trabajo indicado (J/ciclo)',title='E2B · arranques independientes · 44 celdas')
    axes[1].set(xlabel='Ciclo propio',ylabel='Máximo error / tolerancia');axes[1].axhline(1,color='black',ls=':')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.savefig(OUT/'periodic-convergence.png',dpi=160);plt.close(fig)
    if signals:
        fig,axes=plt.subplots(3,1,figsize=(10,10),layout='constrained')
        for (v,c),s in signals.items():
            for j in (0,2,4):axes[(0,2,4).index(j)].plot(s['phase'],s['pressure'][:,j]/1000,label=f'{v} ciclo{c}')
        for ax,x in zip(axes,(PROBES[0],PROBES[2],PROBES[4])):
            ax.set(xlabel='Fase de cigüeñal (°)',ylabel='Presión (kPa)',title=f'Sonda x={x:.3f} m');ax.legend();ax.grid(alpha=.2)
        fig.savefig(OUT/'periodic-pressure-ab.png',dpi=160);plt.close(fig)
        fig,axes=plt.subplots(len(cases),1,figsize=(10,4*len(cases)),squeeze=False,layout='constrained')
        vmax=max(s['field'][:,:,2].max()/1000 for s in signals.values());vmin=min(s['field'][:,:,2].min()/1000 for s in signals.values())
        for ax,(v,case) in zip(axes[:,0],cases.items()):
            s=signals[v,case['converged_cycle']];edges=np.r_[s['phase']-.25,360.25]
            im=ax.pcolormesh(s['mesh']['faces'],edges,s['field'][:,:,2]/1000,cmap='RdBu_r',vmin=vmin,vmax=vmax)
            ax.set(xlabel='Posición física desde lumbrera (m)',ylabel='Fase (°)',title=f'{v} · último ciclo observado · malla propia')
        fig.colorbar(im,ax=list(axes[:,0]),label='Presión (kPa)',shrink=.8)
        fig.savefig(OUT/'periodic-propagation-ab.png',dpi=160);plt.close(fig)
    index=[dict(path=p.relative_to(raw).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(raw.rglob('*')) if p.is_file()]
    write(OUT/'artifact-index.json',dict(root_relative=RAW_NAME,total_bytes=sum(r['bytes'] for r in index),files=index))
    post=time.perf_counter()-start
    original=load(OUT/'execution-attempt1-receipt.json')
    launcher=max(0.,load(OUT/'runlogs/execution.summary.json')['duration_s']-original['wall_s'])
    if (OUT/'runlogs/e2b-primary-recovery.summary.json').exists():
        launcher+=max(0.,load(OUT/'runlogs/e2b-primary-recovery.summary.json')['duration_s']-execution['wall_s'])
    total=execution['cumulative_wall_s']+post+max(0.,launcher)
    classification=execution['classification']
    if total>5400 and classification.startswith('E2B_PERIÓDICO'):classification='E2B_NO_CONVERGIDO'
    result=dict(schema='DINO_E2B_DECISION_V1',classification=classification,error=execution['error'],
        variants=cases,performance_differences=differences,pressure_comparison=wave,
        spatial_power_uncertainty='NOT_QUANTIFIED',temporal_power_uncertainty='NOT_QUANTIFIED',
        periodicity_is_not_mesh_independence=True,experimental_validation=False,
        comparison_against_legacy_power=False,model_changed=False,baseline_rc7_unchanged=True,
        cumulative_wall_s=total,budget_s=5400,budget_pass=total<=5400,postprocessing_wall_s=post,
        raw_bytes=sum(r['bytes'] for r in index),review='SELF_REVIEW',evidence_level='L2' if len(cases)==2 else 'L1',
        next_action='STOP;NO_REFINEMENT_OR_LATER_STAGE',manifest_sha256=sha(OUT/'manifest.json'))
    write(OUT/'decision.json',result)
    print(json.dumps({k:result[k] for k in ('classification','cumulative_wall_s','budget_pass','raw_bytes')}))


if __name__=='__main__':main()
