"""Adaptador exclusivo P0: campaña de producción, sin experimentos ni reparación."""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from .contracts import read_json
from .git_state import snapshot
from motorsim.adaptive import MIN_SUBSTEP, run_adaptive
from motorsim.examples import example_project
from motorsim.performance import indicated_output
from motorsim.project_case import build_project_case
from motorsim.prototype import Monitor, environment, write_json
from motorsim.reference_results import BAND_PA, PROFILE, MODEL_VERSION
from motorsim.rpm_domain import PUBLIC_DOMAINS
from motorsim.simulation import Model, balances_ok

ROOT=Path(__file__).resolve().parents[1]
MAIN_RPMS=tuple(range(2500,15001,500))
STRESS_RPMS=(16000,18000,20000)
HISTORICAL_RPMS=(2500,3000,5000,8000,10000,12000,15000)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def production_hashes():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'motorsim').rglob('*.py'))}


def finite(value):
    if isinstance(value,dict): return all(finite(v) for v in value.values())
    if isinstance(value,(tuple,list)): return all(finite(v) for v in value)
    return math.isfinite(value) if type(value) in (int,float) else True


def point_passed(result):
    if not result['converged'] or not result['cycles'] or not finite(result): return False
    last=result['cycles'][-1]
    if not last['balances_passed'] or not balances_ok(last['discrete'],last['independent']): return False
    for cycle in result['last_two_cycles']:
        for sample in cycle:
            y=sample['state']
            if any(y[i]<=0 or y[i+1]<=0 or not 0<=y[i+2]<=y[i] for i in range(0,12,3)): return False
    return True


def terminal(result):
    if point_passed(result): return 'PASS'
    stop=result['stop']
    if 'paso mínimo' in stop: return 'FAIL_MIN_STEP'
    if 'F fuera de [0,m]' in stop: return 'FAIL_SPECIES_BOUNDS'
    if '60 segundos' in stop: return 'FAIL_TIME_BUDGET'
    return 'FAIL_CONTRACT_OR_NONCONVERGED'


def compare_historical(rpm,document):
    folder='frontera-baja-2t-20260917' if rpm in (2500,3000) else 'rendimiento-dominio-2t-20260917'
    path=ROOT/'results'/folder/f'{rpm}.json'
    old=read_json(path)
    new=json.loads(json.dumps(document,allow_nan=False))
    fields={k:new['result'].get(k)==v for k,v in old['result'].items() if k!='seconds'}
    return dict(rpm=rpm,reference=path.relative_to(ROOT).as_posix(),reference_sha256=sha(path),
        manifest_equal=new['case']==old['case'],fields=fields,
        passed=new['case']==old['case'] and all(fields.values()),ignored_fields=['seconds'])


def execute_point(base,rpm,run_dir):
    started=time.monotonic(); model=Model(replace(base,rpm=rpm),external_band_pa=BAND_PA)
    streak=maximum=0
    def trace(row):
        nonlocal streak,maximum
        streak=0 if row['accepted'] else streak+1
        maximum=max(maximum,streak)
    monitor=Monitor(PROFILE.max_step_deg,time.monotonic(),emit=lambda *a,**k:None)
    result=run_adaptive(PROFILE,monitor,model,trace=trace)
    document=dict(case=model.case.manifest(),result=result)
    relative=f'artifacts/points/{rpm}.json'; path=run_dir/relative
    write_json(path,document)
    last=result['cycles'][-1] if result['cycles'] else None
    passed=point_passed(result)
    indicated=indicated_output(last['W_C_J'],rpm,'2T') if last else None
    row=dict(rpm=rpm,terminal_state=terminal(result),passed=passed,stop_reason=result['stop'],
        completed_cycles=len(result['cycles']),integration_seconds=result['seconds'],
        accepted_steps=result['accepted_steps'],rejected_steps=result['rejected_steps'],
        max_consecutive_rejections=maximum,minimum_step_deg=result['actual_substep_deg']['minimum'],
        W_C_J_per_cycle=last['W_C_J'] if last else None,pmax_Pa=last['p_max_Pa'] if last else None,
        indicated_power_W=indicated['indicated_power_W'] if indicated else None,
        indicated_torque_Nm=indicated['indicated_torque_Nm'] if indicated else None,
        worst_independent_balance=max(v for b in last['independent'].values() for v in b['normalized_m_u_f']) if last else None,
        metrics_status='accepted' if passed else 'diagnostic_only',run_id=run_dir.name,
        manifest_path=relative,scientific_sha256=sha(path),
        classification='MAIN_2T_DOMAIN' if rpm in MAIN_RPMS else 'EXPLORATORY_HIGH_RPM')
    row['wall_seconds']=time.monotonic()-started
    return row,document


def statistics_for(rows):
    result={key:dict(minimum=min(values),maximum=max(values),median=statistics.median(values),mean=statistics.mean(values))
        for key in ('integration_seconds','wall_seconds') if (values:=[r[key] for r in rows])}
    result.update(integration_total=sum(r['integration_seconds'] for r in rows),
        slowest_rpm=max(rows,key=lambda r:r['integration_seconds'])['rpm'],
        most_cycles_rpm=max(rows,key=lambda r:r['completed_cycles'])['rpm'],
        most_rejections_rpm=max(rows,key=lambda r:r['rejected_steps'])['rpm'],
        minimum_step_rpm=min((r for r in rows if r['minimum_step_deg'] is not None),key=lambda r:r['minimum_step_deg'])['rpm'])
    return result


def main_gate(rows,regressions):
    if tuple(r['rpm'] for r in rows)!=MAIN_RPMS or not all(r['passed'] for r in rows): return 'P0_BLOCKED_CONTINUOUS_DOMAIN'
    if tuple(r['rpm'] for r in regressions)!=HISTORICAL_RPMS or not all(r['passed'] for r in regressions): return 'P0_BLOCKED_REGRESSION'
    return 'ELIGIBLE_FOR_REVIEW_AND_FREEZE'


def campaign(run_dir):
    started=time.monotonic(); folder=run_dir/'artifacts'; (folder/'points').mkdir(exist_ok=False)
    write_json(folder/'git-before.json',snapshot(ROOT))
    sources=production_hashes(); base,_=build_project_case(example_project('2t-reference'),rpm=3000)
    data=dict(run_id=run_dir.name,environment=environment(),git_commit=snapshot(ROOT)['commit'],
        model=MODEL_VERSION,case=base.manifest(),profile=asdict(PROFILE),regularization_Pa=BAND_PA,
        minimum_half_step_deg=MIN_SUBSTEP,public_domains=PUBLIC_DOMAINS,warm_start=False,
        source_sha256=sources,rows=[],stress=[],regressions=[],interpretation='Modelo0D, sin ondas, sin escape sintonizado predictivo, sin validación experimental.')
    def checkpoint():
        data['wall_total']=time.monotonic()-started
        write_json(folder/'campaign.json',data)
    for rpm in MAIN_RPMS:
        row,document=execute_point(base,rpm,run_dir); data['rows'].append(row)
        if rpm in HISTORICAL_RPMS: data['regressions'].append(compare_historical(rpm,document))
        checkpoint(); print(json.dumps(row,ensure_ascii=True),flush=True)
    if all(r['passed'] for r in data['rows']):
        for rpm in STRESS_RPMS:
            row,_=execute_point(base,rpm,run_dir); data['stress'].append(row)
            checkpoint(); print(json.dumps(row,ensure_ascii=True),flush=True)
        data['stress_state']='HIGH_RPM_STRESS_20000_PASS' if all(r['passed'] for r in data['stress']) else 'HIGH_RPM_STRESS_LIMIT_OBSERVED'
    else: data['stress_state']='NOT_EXECUTED_MAIN_GATE_FAILED'
    data['scientific_gate']=main_gate(data['rows'],data['regressions'])
    data['continuity']='CONTINUOUS_2T_NUMERICAL_DOMAIN_2500_15000_VERIFIED' if all(r['passed'] for r in data['rows']) else 'P0_BLOCKED_CONTINUOUS_DOMAIN'
    failed=next((r for r in data['rows'] if not r['passed']),None)
    data['first_failure']=failed
    data['last_contiguous_pass_rpm']=None if failed and failed['rpm']==2500 else failed['rpm']-500 if failed else 15000
    data['statistics_main']=statistics_for(data['rows'])
    data['statistics_all']=statistics_for(data['rows']+data['stress'])
    data['production_unchanged']=sources==production_hashes()
    data['no_experimental_imports']=not any(n=='tools' or n.startswith('tools.') for n in sys.modules)
    if all(r['passed'] for r in data['rows']):
        from .p0_plots import render
        render(data['rows'],folder/'diagnostic-plots.png')
    write_json(folder/'regression.json',data['regressions'])
    with (folder/'table.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(data['rows'][0]));writer.writeheader();writer.writerows(data['rows']+data['stress'])
    checkpoint()
    inventory={p.relative_to(run_dir).as_posix():sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    write_json(folder/'inventory.json',inventory)
    checks=dict(main_complete=tuple(r['rpm'] for r in data['rows'])==MAIN_RPMS,
        continuous_domain=all(r['passed'] for r in data['rows']),historical_regression=all(r['passed'] for r in data['regressions']) and len(data['regressions'])==7,
        production_unchanged=data['production_unchanged'],no_experimental_imports=data['no_experimental_imports'],
        artifact_inventory=all(sha(run_dir/name)==value for name,value in inventory.items()))
    write_json(folder/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical' if k in ('continuous_domain','historical_regression') else 'infrastructure') for k,v in checks.items()],
        metrics=dict(main_pass=sum(r['passed'] for r in data['rows']),main_count=len(data['rows']),stress_count=len(data['stress']),
                     integration_total=data['statistics_all']['integration_total'],wall_total=data['wall_total']),scientific_change_required=False))


def checks():
    env=os.environ.copy(); env['QT_QPA_PLATFORM']='offscreen'
    for args in (['discover','-s','tests','-v'],['discover','-s','dev_orchestrator/tests','-t','.','-v']):
        completed=subprocess.run([sys.executable,'-m','unittest',*args],cwd=ROOT,env=env,timeout=240)
        if completed.returncode: return completed.returncode
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--run-dir',type=Path,required=True);parser.add_argument('--checks',action='store_true')
    args=parser.parse_args()
    if args.checks: raise SystemExit(checks())
    campaign(args.run_dir.resolve())
