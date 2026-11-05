"""Read-only adversarial scientific/API probes for the frozen Dino 4T revisions.

Default execution performs configuration/contract probes only. The two explicitly
selected runtime probes are bounded negative tests, not periodicity campaigns.
No out_dir is passed to the solver and no historical artifact is changed.

Examples (use an environment containing the repository dependencies):
  python independent-science-probes.py --repo PATH
  python independent-science-probes.py --repo PATH --runtime false-periodicity
  python independent-science-probes.py --repo PATH --runtime warm-state

The runtime numbers in the companion review were observed before this script was
persisted; persistence did not rerun the solver. Wall-time probes are intentionally
machine-dependent; phase loss, not a particular crank angle, is the assertion.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode=True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--runtime',choices=('none','false-periodicity','warm-state'),default='none')
    args=parser.parse_args()
    repo=args.repo.resolve()
    sys.path.insert(0,str(repo));os.chdir(repo)
    from motorsim.dino4t import api,config,studies
    from motorsim.dino4t.runner import resolved_models,run_operating_point
    from motorsim.desktop.four_stroke_comparison import build_comparison

    results={'review':'INDEPENDENT_REVIEW','mode':args.runtime,'configuration':{}}
    base=config.load(config.EXAMPLE_PATH)
    mutations=[
        ('fractional_valve_count',lambda c:c['intake_valve'].update(count=1.9)),
        ('boolean_valve_count',lambda c:c['intake_valve'].update(count=True)),
        ('nan_friction',lambda c:c['friction'].update(a_pa=float('nan'))),
        ('negative_friction',lambda c:c['friction'].update(a_pa=-1e8)),
        ('nested_unknown_lift',lambda c:c['intake_valve']['lift'].update(typo_ignored=42)),
        ('globally_known_unread',lambda c:c['numerics'].update(bore_mm=123)),
        ('bad_section_type',lambda c:c.update(geometry=None)),
        ('bad_cd_nan',lambda c:c['intake_valve']['discharge_coefficient']['forward'].__setitem__(0,float('nan'))),
    ]
    for name,mutate in mutations:
        c=copy.deepcopy(base);mutate(c)
        try:
            checked=api.validate(c)
            results['configuration'][name]={k:checked[k] for k in ('valid','issues','unknown_keys')}
        except Exception as exc:
            results['configuration'][name]={'raised':type(exc).__name__,'message':str(exc)}
    missing_default=copy.deepcopy(base);missing_default['combustion'].pop('zone_model',None)
    results['default_model_discovery']={
        'valid':api.validate(missing_default)['valid'],
        'advertised':api.capabilities()['default_models']['cylinder'],
        'selected_when_omitted':resolved_models(missing_default)['cylinder'],
    }

    # Existing real result files are only read. Mutations below are adversarial
    # in-memory test fixtures, never additional scientific results or evidence.
    comparison_path=repo/'results/dino4t-ab-engineering-v1/runs/comparison.json'
    if comparison_path.is_file():
        original=json.loads(comparison_path.read_text(encoding='utf-8'))
        def read_artifact(endpoint,name):
            original_path=Path(endpoint[name])
            if original_path.is_file():return original_path
            # Relocated clean worktrees can recover the committed run artifacts.
            local=repo/'results/dino4t-ab-engineering-v1/runs/runs'/endpoint['run_id']/'artifacts'
            return local/({'summary_path':'summary.json','config_path':'config_resolved.json','trace_path':'trace_last_cycle.csv'}[name])
        def make_pair():
            endpoints=[]
            for endpoint in original['endpoints']:
                endpoints.append({
                    'summary':json.loads(read_artifact(endpoint,'summary_path').read_text(encoding='utf-8')),
                    'config':json.loads(read_artifact(endpoint,'config_path').read_text(encoding='utf-8')),
                    'meta':{'api':endpoint['api'],'result_sha256':endpoint['result_sha256']},
                    'reference':{k:endpoint[k] for k in ('run_id','variant_id','config_sha256','result_sha256')},
                    'trace_sha256':endpoint['trace_sha256'],
                })
            return endpoints
        def rebind(endpoint):
            digest=hashlib.sha256(json.dumps(endpoint['summary']).encode()).hexdigest()
            endpoint['meta']['result_sha256']=digest;endpoint['reference']['result_sha256']=digest
        results['semantic_adversarial_fixtures']={}
        for kind in ('zero_cycles_bad_conservation','rpm_mismatch','model_mismatch'):
            a,b=make_pair()
            for endpoint in (a,b):
                if kind=='zero_cycles_bad_conservation':
                    endpoint['summary']['cycles_run']=0
                    endpoint['summary']['periodicity']['history']=[]
                    endpoint['summary']['conservation']['max_relative_closure']={'mass':1.0,'energy':1.0,'elements':1.0}
                elif kind=='rpm_mismatch':endpoint['summary']['operating_point']['rpm']=7000.0
                else:endpoint['summary']['models']['valve_boundary']='QUASI_STEADY_RESTRICTION_V1'
                rebind(endpoint)
            try:
                accepted=build_comparison(a,b)
                results['semantic_adversarial_fixtures'][kind]={
                    'api_check':api.check_summary(a['summary']),'classification':accepted['classification'],
                    'reported_rpm':accepted['operating_point']['rpm'],'config_rpm':a['config']['operating_point']['rpm'],
                    'reported_model':accepted['models']['valve_boundary'],'config_restriction':a['config']['numerics']['restriction_model'],
                }
            except Exception as exc:results['semantic_adversarial_fixtures'][kind]={'raised':type(exc).__name__,'message':str(exc)}
        claims_fixture=make_pair()[0]['summary']
        claims_fixture['claims'].update(experimental_validation='PERFORMED',predictive_capability='CLAIMED')
        claims_fixture['validation_evidence']={'unverified':'arbitrary nonempty object'}
        results['untyped_validation_evidence_claim_guard']=api.check_summary(claims_fixture)

    # Contract-only stub: explicitly not a numerical simulation.
    def nonperiodic_stub(*unused_args,**unused_kwargs):
        return {'summary':{'status':'completed','termination':'requested_cycles',
            'periodicity':{'status':'NOT_CONVERGED'},'final_cycle':{'imep_net_bar':10.0}},'result':{'state':None}}
    previous_runner=studies.run_operating_point;studies.run_operating_point=nonperiodic_stub
    try:results['nonperiodic_sensitivity_contract_stub']=studies.sensitivity(base,
        parameters=['friction_A'],indicators=['imep_net_bar'],max_cycles=1)
    finally:studies.run_operating_point=previous_runner

    if args.runtime=='false-periodicity':
        c=copy.deepcopy(base);c['numerics']['dx_mm']=30.0;c['numerics']['periodicity']['consecutive']=0
        output=api.run(c,max_cycles=1,wall_limit_s=30.0)
        summary=output.get('summary') or {}
        results['runtime_false_periodicity']={'validation':api.validate(c),'ok':output['ok'],'error':output['error'],
            **{k:summary.get(k) for k in ('status','termination','periodicity','cycles_run','wall_seconds')}}
    elif args.runtime=='warm-state':
        c=copy.deepcopy(base);c['numerics']['dx_mm']=30.0;c['combustion']['zone_model']='single_zone'
        output=run_operating_point(c,max_cycles=1,wall_limit_s=0.03)
        internal=output['result'];engine=output['engine'];state=internal['state'];theta=internal['theta']
        actual_p=float(engine.cylinder.gas(state['cyl'],theta)[0].p)
        restart_p=float(engine.cylinder.gas(state['cyl'],engine.theta_start)[0].p)
        next_output=run_operating_point(c,max_cycles=1,wall_limit_s=0.000001,initial_state=state)
        results['runtime_warm_state']={'status':output['summary']['status'],
            'termination':output['summary']['termination'],'cycles':output['summary']['cycles_run'],
            'theta_returned_by_engine':float(theta),'theta_start':float(engine.theta_start),'state_keys':list(state),
            'p_at_actual_Pa':actual_p,'p_if_reset_to_start_Pa':restart_p,
            'continuation_warm_start':next_output['summary']['warm_start'],
            'continuation_theta':float(next_output['result']['theta'])}
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
