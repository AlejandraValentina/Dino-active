"""Replay recorded accepted steps and offline-audit cycle 2; no new trajectory."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import (IntegratedEngine2T, _json_evidence_equal,
    _integrated_nominal_step_end,_integrated_scheduled_angles,
    make_integrated_cycle_primary,audit_integrated_cycle_primary)
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(directory,output):
    directory=directory.resolve()
    output=output.resolve()
    check_storage_requirements([(output.parent,1024**2)])
    receipt=json.loads((directory/'receipt.json').read_text(encoding='utf-8'))
    source=directory/'primary-stages.jsonl.gz'
    if digest(source)!=receipt['primary_stages_sha256']:
        raise ValueError('primary stream hash mismatch')
    for name in ('configuration.json','terminal-checkpoint.json'):
        key='configuration_sha256' if name=='configuration.json' else 'terminal_checkpoint_sha256'
        if digest(directory/name)!=receipt[key]:
            raise ValueError(f'{name} hash mismatch')
    path=directory/'checkpoint-360.json'
    bound=next(p for p in receipt['checkpoints'] if p['path']==path.name)
    if digest(path)!=bound['sha256']:
        raise ValueError('cycle start checkpoint hash mismatch')
    start=json.loads(path.read_text(encoding='utf-8'))
    engine=IntegratedEngine2T.from_configuration_dict(json.loads(
        (directory/'configuration.json').read_text(encoding='utf-8')))
    engine.restore(start)
    began=time.perf_counter()
    count=0
    rejections=[]
    scheduled=_integrated_scheduled_angles(engine,720.)
    with gzip.open(source,'rt',encoding='utf-8') as handle:
        for line in handle:
            row=json.loads(line)
            if row['angle_start_deg']<360.:
                continue
            if time.perf_counter()-began>=240:
                raise TimeoutError('replay budget reached; no automatic extension')
            angle=row['angle_start_deg']
            proposed=_integrated_nominal_step_end(engine,angle,720.,scheduled)-angle
            # Reproduce actual rejected proposals too. The original summary
            # only counted them; this invocation records its own exact errors.
            # An unexpectedly accepted proposal is a replay failure, not a
            # reason to fabricate a missing rejection or roll back a state.
            for attempt in range(25):
                try:
                    same_step=abs(proposed-(row['angle_end_deg']-angle))<=4*math.ulp(max(abs(angle),1.))
                    dt=row['dt_s'] if same_step else proposed/(6*row['rpm'])
                    new=engine.step(dt,proposed)
                except NoAdmissiblePortState:
                    raise
                except ValueError as exc:
                    if not any(text in str(exc) for text in (
                        'CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):
                        raise
                    rejections.append(dict(angle_deg=angle,attempted_step_deg=proposed,reason=str(exc)))
                    proposed*=.5
                else:
                    break
            else:
                raise RuntimeError('25 rejected replay proposals')
            if not _json_evidence_equal(new,row):
                raise AssertionError(f'replay mismatch at {row["angle_start_deg"]}')
            count+=1
    expected=json.loads((directory/'terminal-checkpoint.json').read_text(encoding='utf-8'))
    if (not _json_evidence_equal(engine.state,expected['state']) or
            not _json_evidence_equal(engine.ledger,expected['ledger'])):
        raise AssertionError('terminal replay does not match recorded diagnostic')
    end=engine.snapshot()
    primary=make_integrated_cycle_primary(engine,start,end,2,rejected_trials=rejections,
        runner_sha256=digest(Path(__file__)))
    audit=audit_integrated_cycle_primary(primary)
    # Retain source stream plus bindings, not a second copy of the trajectory.
    result=dict(schema='DINO_PORT_V2_CYCLE_REPLAY_AUDIT',
        status='PASS',replayed_accepted_steps=count,wall_s=time.perf_counter()-began,
        rejection_scope='ACTUAL_NOMINAL_AND_RETRY_REPLAY_PROPOSALS_THIS_INVOCATION',
        rejected_trials=rejections,
        source_directory=str(directory.relative_to(ROOT)),
        source_primary_stream_sha256=digest(source),
        source_receipt_sha256=digest(directory/'receipt.json'),
        evidence_binding=primary['evidence_binding'],conservation=primary['conservation'],
        audit=audit,experimental_validation=False,review='SELF_REVIEW')
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','replayed_accepted_steps','wall_s')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    replay(args.directory,args.output)
