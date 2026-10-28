"""Bounded E2B: independent frozen E2A cases, existing detector and primary audit."""
from __future__ import annotations
import argparse
from collections import Counter
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from motorsim.integrated_2t import (IntegratedEngine2T,_solver_dependency_hashes,
    _integrated_scheduled_angles,_integrated_nominal_step_end,_json_evidence_equal,
    make_integrated_cycle_primary,audit_integrated_cycle_primary,
    make_integrated_engineering_output,_validated_last_port_close_species)
from motorsim.reference_harness.convergence import PeriodicDetectorV2,THRESHOLDS,STREAK
from motorsim.mechanical import MechanicalLossModel
from motorsim.port_connection_v2 import NoAdmissiblePortState
from motorsim._evidence_io import write_primary_atomic
from scripts.agents.storage_preflight import check_storage_requirements,default_artifact_root
from scripts.diagnostics.checkpoint_periodicity_indicators_v1 import cycle_observations
from scripts.diagnostics.periodic_primary_audit_v1 import primary_observation_record
from scripts.diagnostics.periodic88_front_flux_v1 import empty_totals,accumulate,serial
from scripts.diagnostics.e2a_exhaust_waves_v1 import frame

OUT=ROOT/'results/e2b-periodic-ab-v1'
PLAN=OUT/'manifest.json'
RAW_NAME='e2b-periodic-ab-v1-20261028'


def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
    p=Path(p);temporary=p.with_name(p.name+'.partial')
    temporary.write_text(json.dumps(d,allow_nan=False,ensure_ascii=False)+'\n',encoding='utf-8')
    temporary.replace(p)


def bound_periodic_output(primary,detector,mechanical):
    """Bind derived output to the actual detector; preserve scientific primary."""
    if detector.classification not in ('PERIOD_1','PERIOD_2'):
        raise ValueError('no accepted detector classification')
    snapshot=detector.snapshot()
    digest=hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':'),
        allow_nan=False).encode()).hexdigest()
    record=dict(primary,periodicity_evidence=dict(status=detector.classification,
        configuration_hash=primary['configuration_hash'],terminal_cycle=primary['cycle_index'],
        detector_sha256=digest))
    return make_integrated_engineering_output(record,mechanical_loss_model=mechanical,
        periodicity_status=detector.classification)


def estimate(times,reference_cycles=30):
    rate=max(15.,max(times))
    return dict(rate_planning_s_per_cycle=rate,measured_s_per_cycle=times,
        A_observed_reference_cycles=reference_cycles,B_cycles_known=False,
        B_planning_range_not_probability=[reference_cycles,2*reference_cycles],
        nominal_AB_solver_s=rate*3*reference_cycles,
        maximum_cycles_each=100,maximum_AB_solver_estimate_s=rate*200,
        primary_audits_reserve_s=1500.,verification_reserve_s=250.,other_reserve_s=650.,
        conservative_total_s=rate*200+1500+250+650,budget_s=5400.,
        feasible=rate*200+1500+250+650<=5400.)


def performance(cp0,cp1,displacement,mechanical):
    cylinder=-(cp1['ledger']['cylinder_work_J']-cp0['ledger']['cylinder_work_J'])
    crankcase=-(cp1['ledger']['crankcase_work_J']-cp0['ledger']['crankcase_work_J'])
    result=mechanical.evaluate_2t_net_piston_work(net_piston_gas_work_j=cylinder+crankcase,
        displacement_m3=displacement,rpm=9000.,load=0.)
    return dict(cylinder_indicated_work_j=cylinder,crankcase_gas_work_j=crankcase,
        net_piston_gas_work_j=cylinder+crankcase,indicated_power_w=cylinder*150.,
        indicated_torque_nm=cylinder/(2*math.pi),imep_pa=cylinder/displacement,
        brake_work_j=result['brake_work_j'],brake_power_w=result['brake_power_w'],
        brake_torque_nm=result['brake_torque_nm'],bmep_pa=result['brake_mep_pa'])


def prepare():
    began=time.perf_counter()
    if OUT.exists():raise FileExistsError('preserve prior E2B')
    old=ROOT/'results/e2-spatial-waves-v1';manifest=load(old/'preparation/manifest.json')
    configs={v:'results/e2-spatial-waves-v1/preparation/'+v+'44.json' for v in ('A','B')}
    for v,p in configs.items():
        if sha(ROOT/p)!=manifest['config_hashes'][v+'44']:raise ValueError('E2A configuration changed')
    reference=ROOT/'results/predictive-reliability-v1/spatial-boundary-v2-engine/configuration.json'
    if load(reference)!=load(ROOT/configs['A']):raise ValueError('cost/convergence reference is not same configuration')
    audited=load(ROOT/'results/predictive-reliability-v1/periodic-primary-audit-v1/reconstruction/receipt.json')
    if not audited['periodicity_audited'] or audited['detector']['converged_cycle']!=30:raise ValueError('reference not periodic30')
    execution=load(old/'execution-receipt.json')
    times=[r['new_solver_s']/2 for r in execution['cases'] if r['name'] in ('A44-d05','B44-d05')]
    times.append(load(ROOT/'results/predictive-reliability-v1/periodicity-extension-v2/run/receipt.json')['timing_seconds']['solver']/6)
    viability=estimate(times)
    fixture=ROOT/'configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json'
    losses=load(fixture)['base_engine']['mechanical_loss_model'];MechanicalLossModel.from_dict(losses)
    raw=default_artifact_root()/RAW_NAME
    preflight=check_storage_requirements([(OUT,16*1024**2),(raw,2*1024**3)])
    OUT.mkdir(parents=True)
    dependencies=['scripts/diagnostics/e2b_periodic_ab_v1.py',
        'scripts/diagnostics/checkpoint_periodicity_indicators_v1.py',
        'scripts/diagnostics/periodic_primary_audit_v1.py','scripts/diagnostics/periodic88_front_flux_v1.py',
        'motorsim/reference_harness/convergence.py','motorsim/mechanical.py',
        'tests/test_e2b_periodic_ab_v1.py']
    m=dict(schema='DINO_E2B_PROTOCOL_V1',configurations=configs,
        configuration_sha256={v:sha(ROOT/p) for v,p in configs.items()},
        dependency_sha256={p:sha(ROOT/p) for p in dependencies},solver_dependency_sha256=_solver_dependency_hashes(),
        viability=viability,budget_wall_s=5400.,simulation_limit_s_each=1600.,audit_limit_s=1500.,
        audit_cycle_admission_s=120.,maximum_cycles_each=100,rss_limit_mib=1024,artifact_limit_bytes=2*1024**3,
        mechanical_loss_model=losses,mechanical_source=fixture.relative_to(ROOT).as_posix(),mechanical_source_sha256=sha(fixture),
        thresholds=THRESHOLDS,streak=STREAK,grid_total_cells=44,exhaust_cells=31,rpm=9000.,
        nominal_step_deg=.5,reference_configuration_sha256=sha(reference),
        reference_audit_sha256=sha(ROOT/'results/predictive-reliability-v1/periodic-primary-audit-v1/reconstruction/receipt.json'),
        uncertainty='No qualified periodic power mesh/time uncertainty; if both converge, exploratory only. Never use transient P1 envelopes as power uncertainty.',
        independent_initialization=True,warm_start=False,storage_preflight=preflight,
        numerical_executions_planned=2,raw_root_relative=RAW_NAME,
        verification_tests=['tests/test_e2b_periodic_ab_v1.py','tests/test_integrated_spatial_v2.py',
            'tests/test_spatial_reconstruction_v2.py','tests/test_spatial_boundary_v2_adversarial.py'],
        prior_regression_command=load(ROOT/'results/port-flow-verification-v1/runlogs/p4-p8-regression.summary.json')['command'],
        historical_artifact_root=load(old/'artifact-resolution.json')['root'],
        scientific_state='SYNTHETIC_ENGINE;NUMERICAL_VERIFICATION;NO_EXPERIMENTAL_VALIDATION',review='SELF_REVIEW')
    m['preparation_wall_s']=time.perf_counter()-began
    write(PLAN,m)
    print(json.dumps(dict(feasible=viability['feasible'],estimate=viability)))


def validate(m):
    for p,h in m['dependency_sha256'].items():
        if sha(ROOT/p)!=h:raise ValueError('frozen dependency changed: '+p)
    for v,p in m['configurations'].items():
        if sha(ROOT/p)!=m['configuration_sha256'][v]:raise ValueError('frozen configuration changed')
    if _solver_dependency_hashes()!=m['solver_dependency_sha256']:raise ValueError('solver changed')
    if THRESHOLDS!=m['thresholds'] or STREAK!=m['streak']:raise ValueError('criteria changed')


def verify():
    m=load(PLAN);validate(m)
    if (OUT/'verification.json').exists():raise FileExistsError('one verification invocation')
    start=time.perf_counter()
    env=dict(os.environ,DINO_ARTIFACT_ROOT=m['historical_artifact_root'])
    reports=[]
    for name,command in [('focal',[sys.executable,'-m','pytest','-q',*m['verification_tests']]),
                         ('p4-p8',m['prior_regression_command'])]:
        remaining=250-(time.perf_counter()-start)
        if remaining<=0:break
        run=subprocess.run([sys.executable,'scripts/agents/run_logged.py','--name',name,'--out',str(OUT/'runlogs'),
            '--timeout',str(max(1,remaining)),'--',*command],cwd=ROOT,env=env,capture_output=True,text=True)
        reports.append(load(OUT/'runlogs'/(name+'.summary.json')))
        if run.returncode:break
    result=dict(passed=len(reports)==2 and all(r['exit_code']==0 for r in reports),
        wall_s=time.perf_counter()-start,reports=reports)
    write(OUT/'verification.json',result)
    print(json.dumps(dict(passed=result['passed'],wall_s=result['wall_s'])))
    if not result['passed']:raise SystemExit(1)


def simulate(v,m,raw,global_stop):
    import psutil
    proc=psutil.Process();cfg=load(ROOT/m['configurations'][v]);e=IntegratedEngine2T.from_configuration_dict(cfg)
    d=raw/v;d.mkdir();write(d/'configuration.json',cfg)
    previous=e.snapshot();write(d/'checkpoint-000.json',previous)
    detector=PeriodicDetectorV2();cycles=[];start=time.perf_counter();solver_s=0.;status='E2B_NO_CONVERGIDO';error=None;peak=0.
    mechanical=MechanicalLossModel.from_dict(m['mechanical_loss_model']);displacement=cfg['geometry_identity']['displacement_cc']*1e-6
    schedule=_integrated_scheduled_angles(e,360.*m['maximum_cycles_each']);recipe=[]
    try:
        for cycle in range(1,m['maximum_cycles_each']+1):
            recipe=[];tick_cycle=time.perf_counter()
            while e.crank_angle_unwrapped_deg<360.*cycle-1e-9:
                if time.perf_counter()>=min(global_stop,start+m['simulation_limit_s_each']):raise TimeoutError('finite campaign limit')
                peak=max(peak,proc.memory_info().rss/1024**2)
                if peak>m['rss_limit_mib']:raise MemoryError('RSS limit')
                delta=min(360.*cycle,_integrated_nominal_step_end(e,e.crank_angle_unwrapped_deg,360.*m['maximum_cycles_each'],schedule))-e.crank_angle_unwrapped_deg
                rejected=[]
                for _ in range(25):
                    t=time.perf_counter()
                    try:row=e.step(delta/54000.,delta,capture_trace=False)
                    except NoAdmissiblePortState:raise
                    except ValueError as exc:
                        if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                        rejected.append(dict(step_deg=delta,error=str(exc)));delta*=.5
                    else:break
                    finally:solver_s+=time.perf_counter()-t
                else:raise RuntimeError('25 rejected proposals')
                recipe.append(dict(**row,accepted_delta_deg=delta,rejected_proposals=rejected))
            e.compact_fast_recipe_cycle();cp=e.snapshot();write(d/f'checkpoint-{cycle:03}.json',cp)
            write(d/f'recipe-{cycle:03}.json',recipe)
            fresh=IntegratedEngine2T.from_configuration_dict(cfg);fresh.restore(cp)
            if not _json_evidence_equal(fresh.snapshot(),cp):raise ValueError('native checkpoint restore differs')
            outcome=detector.update(cycle_observations(e,previous,cp,cycle))
            comparison=outcome['outcomes'].get('lag1',{});values=[x['value']/x['threshold'] for x in comparison.get('metrics',{}).values()]
            conservation=e.conservation_report();mass=e.initial_inventory['mass_kg'];energy=e.initial_inventory['energy_J']
            balances=dict(mass=abs(conservation['mass']['residual'])/mass,
                species=max(abs(x['residual']) for x in conservation['species'].values())/mass,
                energy=abs(conservation['energy']['residual'])/max(energy,abs(conservation['energy']['final'])))
            if balances['mass']>1e-9 or balances['species']>1e-9 or balances['energy']>1e-8:raise ValueError('conservation gate failed')
            cycles.append(dict(cycle=cycle,wall_s=time.perf_counter()-tick_cycle,
                maximum_ratio=max(values) if values else None,p90=float(np.quantile(values,.9)) if values else None,
                median=float(np.median(values)) if values else None,failed=sum(x>1 for x in values),
                detector_outcome=outcome,performance=performance(previous,cp,displacement,mechanical),balances=balances,
                checkpoint_restore_exact=True,recipe_steps=len(recipe)))
            write(d/'cycles.json',cycles);write(d/'detector.json',detector.snapshot())
            write(raw/'progress.json',dict(phase='SIMULATION',variant=v,cycle=cycle,
                maximum_ratio=cycles[-1]['maximum_ratio'],failed=cycles[-1]['failed'],
                period=detector.detected_period,variant_wall_s=time.perf_counter()-start))
            previous=cp
            if detector.detected_period is not None:status='PERIOD_DETECTED_REQUIRES_PRIMARY_VERIFICATION';break
    except TimeoutError as exc:error=str(exc)
    except Exception as exc:status='E2B_DEFECTO';error=type(exc).__name__+': '+str(exc)
    if e.accepted_steps:
        write(d/'partial-recipe.json',recipe);write(d/'partial-terminal.json',e.fast_recipe_terminal_state())
    result=dict(variant=v,status=status,error=error,completed_cycles=len(cycles),detected_period=detector.detected_period,
        converged_cycle=detector.converged_cycle,wall_s=time.perf_counter()-start,solver_s=solver_s,
        peak_rss_mib=peak,initialization='INDEPENDENT_CONFIG_AT_ZERO;NO_WARM_START',
        configuration_sha256=sha(d/'configuration.json'))
    write(d/'simulation-receipt.json',result);print(json.dumps(result),flush=True)
    return result


def audit_variant(v,simulation,m,raw,global_stop,audit_stop):
    cfg=load(ROOT/m['configurations'][v]);d=raw/v;n=simulation['converged_cycle'];period=simulation['detected_period']
    count=4 if period==1 else 8;first=n-count+1
    saved=load(d/'detector.json');detector=PeriodicDetectorV2()
    for record in saved['history'][:first-1]:detector.update(record)
    mechanical=MechanicalLossModel.from_dict(m['mechanical_loss_model']);records=[];start=time.perf_counter()
    for cycle in range(first,n+1):
        if min(global_stop,audit_stop)-time.perf_counter()<m['audit_cycle_admission_s']:
            raise TimeoutError('insufficient remaining audit/global reserve for one primary cycle')
        tick=time.perf_counter();e=IntegratedEngine2T.from_configuration_dict(cfg)
        cp0=load(d/f'checkpoint-{cycle-1:03}.json');expected=load(d/f'checkpoint-{cycle:03}.json');e.restore(cp0)
        spool=d/f'audit-{cycle:03}';spool.mkdir();e.enable_trajectory_spooling(spool)
        recipe=load(d/f'recipe-{cycle:03}.json');rejections=[];totals=empty_totals([p.id for p in e.ducts])
        frames=[];chambers=[];w,p=frame(e);frames.append(w);chambers.append(p)
        for row in recipe:
            if time.perf_counter()>=min(global_stop,audit_stop,tick+m['audit_cycle_admission_s']):raise TimeoutError('audit-cycle budget reached')
            for attempt in row['rejected_proposals']:
                da=attempt['step_deg']
                try:e.step(da/54000.,da,capture_trace=True)
                except ValueError as exc:
                    if str(exc)!=attempt['error']:raise ValueError('rejected trial differs') from exc
                    rejections.append(dict(angle_deg=row['angle_start_deg'],attempted_step_deg=da,reason=str(exc)))
                else:raise ValueError('rejected trial unexpectedly accepted')
            r=e.step(row['dt_s'],row['accepted_delta_deg'],capture_trace=True)
            if not all(_json_evidence_equal(r[k],z) for k,z in row.items() if k not in ('rejected_proposals','accepted_delta_deg')):raise ValueError('accepted recipe differs')
            for faces in r['stage_face_fluxes']:accumulate(totals,faces,.5*row['dt_s'])
            phase=e.crank_angle_unwrapped_deg-360.*(cycle-1);k=round(phase*2)
            if abs(phase-k/2)<1e-8:
                if k!=len(frames):raise ValueError('common pressure phase gap')
                w,p=frame(e);frames.append(w);chambers.append(p)
        end=e.snapshot(streaming=True)
        for key in ('state','ledger','time_s','angle_deg','fuel_combustion','p7'):
            if not _json_evidence_equal(end.get(key),expected.get(key)):raise ValueError('primary replay physical/event mismatch: '+key)
        primary=make_integrated_cycle_primary(e,cp0,end,cycle,rejected_trials=rejections,runner_sha256=sha(__file__))
        file=d/f'primary-{cycle:03}.json.gz';exported=write_primary_atomic(file,primary,maximum_bytes=128*1024**2)
        audit=audit_integrated_cycle_primary(primary,preserve_precycle_p7_baseline=True)
        if audit['status']!='PASS':raise ValueError('primary audit failed')
        outcome=detector.update(primary_observation_record(primary))
        if cycle>n-period:
            output=bound_periodic_output(primary,detector,mechanical)
            write(d/f'engineering-{cycle:03}.json',output)
            angle,species,role=_validated_last_port_close_species(primary,primary['port_closure_snapshots']['snapshots'])
            charge=dict(phase_deg=angle-360*(cycle-1),closure_role=role,fresh_air_kg=species[0],fuel_kg=species[1],
                total_kg=sum(species),fresh_charge_kg=species[0]+species[1],
                nonfresh_burned_plus_residual_fraction=(species[2]+species[3])/sum(species),
                initial_residual_label_fraction=species[2]/sum(species))
            write(d/f'charge-{cycle:03}.json',charge);write(d/f'interfaces-{cycle:03}.json',serial(totals))
            np.savez_compressed(d/f'waves-{cycle:03}.npz',phase_deg=np.arange(len(frames))*.5,field=frames,chamber_pressures=chambers)
        entry=dict(cycle=cycle,audit=audit,periodicity_outcome=outcome,wall_s=time.perf_counter()-tick,
            primary_sha256=sha(file),export=exported,replay_exact=True)
        write(d/f'audit-{cycle:03}.json',entry);records.append(entry)
        write(raw/'progress.json',dict(phase='PRIMARY_AUDIT',variant=v,cycle=cycle,wall_s=time.perf_counter()-start))
        del primary,end,e;gc.collect()
    if detector.detected_period!=period or detector.converged_cycle!=n:raise ValueError('primary detector differs from native detection')
    result=dict(variant=v,period=period,converged_cycle=n,status='PASS',wall_s=time.perf_counter()-start,
        audited_cycles=[r['cycle'] for r in records],detector=detector.snapshot(),primary_replay_exact=True)
    write(d/'audit-receipt.json',result)
    print(json.dumps({k:result[k] for k in ('variant','status','period','converged_cycle','wall_s')}),flush=True)
    return result


def execute():
    m=load(PLAN);validate(m);verification=load(OUT/'verification.json')
    if not m['viability']['feasible']:raise ValueError('E2B_NO_VIABLE: do not run')
    if not verification['passed']:raise ValueError('verification failed')
    raw=default_artifact_root()/RAW_NAME
    preflight=check_storage_requirements([(raw,m['artifact_limit_bytes'])])
    if raw.exists():raise FileExistsError('one independent A/B campaign')
    raw.mkdir();start=time.perf_counter();prior=verification['wall_s']+m['preparation_wall_s']
    stop=start+m['budget_wall_s']-prior-150;simulations=[];audits=[];error=None;classification='E2B_NO_CONVERGIDO'
    try:
        for v in ('A','B'):
            simulations.append(simulate(v,m,raw,stop))
            if simulations[-1]['status']=='E2B_DEFECTO':raise ValueError(simulations[-1]['error'])
        if all(r['detected_period'] is not None for r in simulations):
            audit_stop=min(stop,time.perf_counter()+m['audit_limit_s'])
            for r in simulations:audits.append(audit_variant(r['variant'],r,m,raw,stop,audit_stop))
            classification='E2B_PERIÓDICO_EXPLORATORIO'
    except TimeoutError as exc:error=str(exc)
    except Exception as exc:classification='E2B_DEFECTO';error=type(exc).__name__+': '+str(exc)
    result=dict(schema='DINO_E2B_EXECUTION_V1',classification=classification,error=error,simulations=simulations,
        audited_variants=[a['variant'] for a in audits],wall_s=time.perf_counter()-start,
        prior_charged_s=prior,cumulative_wall_s=prior+time.perf_counter()-start,
        storage_preflight=preflight,manifest_sha256=sha(PLAN),raw_root=str(raw),
        power_difference_numerically_qualified=False,experimental_validation=False,
        solver_dependency_sha256=_solver_dependency_hashes())
    write(raw/'receipt.json',result);write(OUT/'execution-receipt.json',result)
    print(json.dumps({k:result[k] for k in ('classification','error','wall_s','cumulative_wall_s')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','verify','execute']);a=p.parse_args()
    {'prepare':prepare,'verify':verify,'execute':execute}[a.mode]()
