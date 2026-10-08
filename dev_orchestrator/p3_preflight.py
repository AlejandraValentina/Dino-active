"""P3 frozen-reservoir compatibility gate. Stops before dependent integration."""
import argparse
from dataclasses import asdict
import json
from math import sqrt
from pathlib import Path
import time

from motorsim.coupling import ChamberState, prescribed_reservoir_flux as interface_flux
from motorsim.gas1d.eos import IdealGas, InvalidState
from .p2_campaign import ROOT, sha, write
from .p1_r5_close import close as verify_p2_offline


def run(run_dir):
    started = time.monotonic()
    art = Path(run_dir) / 'artifacts'
    art.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((ROOT/'docs/gasdynamic/p2_human_acceptance.json').read_text(encoding='utf-8'))
    frozen = all(sha(ROOT/p)==h for p,h in receipt['frozen_core_and_contract_sha256'].items())
    accepted = receipt['status']=='P2_HUMAN_ACCEPTED' and receipt['actor']=='usuaria' and sha(ROOT/receipt['original_evidence'])==receipt['original_evidence_sha256']
    if not frozen or not accepted:
        raise ValueError('P2 acceptance or frozen baseline mismatch')
    # Regression is offline: it reads existing P2/P0 arrays, never integrates.
    verify_p2_offline(art/'p2-regression')
    regression = json.loads((art/'p2-regression/artifacts/closure.json').read_text(encoding='utf-8'))
    eos = IdealGas()
    mass = 100000/(eos.R*300)*.01
    chamber = ChamberState(mass,100000*.01/(eos.gamma-1),.8*mass,.01)
    rows=[]
    for normal in (-1,1):
        for temperature in (299.,300.,301.):
            for w in (-.001,-.000001,-.000000001,0.,.000000001,.000001,.001):
                interior=(100000/(eos.R*temperature),normal*w,100000.,.2)
                eos.validate(interior)
                row=dict(normal=normal,T_pipe=temperature,w_normal=w,interior=interior)
                try:
                    value=interface_flux(chamber,interior,.01,normal,eos=eos)
                    row.update(status='DEFINED',face=list(value.face_state),outward=list(value.outward),donor=value.donor,
                               increments=value.increments(1e-5))
                    if value.outward[0]:
                        row['transported_H']=value.outward[2]/value.outward[0]
                        row['transported_Y']=value.outward[3]/value.outward[0]
                except InvalidState as exc:
                    row.update(status='NO_CONSISTENT_BRANCH',error=str(exc))
                rows.append(row)
    # Analytic one-sided limit, derived from the contractual characteristic/enthalpy equations.
    h0=eos.cp*300
    limits=[]
    for temperature in (299.,300.,301.):
        jp=2*sqrt(eos.gamma*eos.R*temperature)/(eos.gamma-1)
        jrest=2*sqrt((eos.gamma-1)*h0)/(eos.gamma-1)
        discriminant=4*(eos.gamma+1)*h0-2*(eos.gamma-1)*jp*jp
        wroot=((eos.gamma-1)*jp-sqrt(discriminant))/(eos.gamma+1)
        limits.append(dict(T_pipe=temperature,J_plus_at_rest=jp,J_rest_reservoir=jrest,
                           limiting_algebraic_root=wroot,admissible_inflow_root_exists=jp<=jrest))
    missing=any(r['status']=='NO_CONSISTENT_BRANCH' for r in rows)
    checks=dict(P2_HUMAN_ACCEPTED=accepted,P2_frozen=frozen,
                P2_regression=all(regression['checks'].values()),
                P0_regression=regression['checks']['P0_regression'],
                reservoir_branch_exists_for_admissible_reversal=not missing)
    result=dict(state='P3_BLOCKED_BACKFLOW' if missing else 'P3_PREFLIGHT_REQUIRES_REVIEW',
                gate='SCIENTIFIC_CHANGE_REQUIRED' if missing else 'REVIEW_REQUIRED',
                checks=checks,rows=rows,analytic_limits=limits,chamber=asdict(chamber),
                reason='Frozen P1 reservoir equations have no consistent branch at admissible near-rest reversal with different entropy.' if missing else None,
                new_integrations=0,wall_seconds=time.monotonic()-started,
                matrix={f'C{i:02}':dict(status='BLOCKED' if i==4 else 'NOT_RUN',reason='P3A compatibility gate precedes coupled time integration') for i in range(1,13)},
                P3A='BLOCKED',P3B='NOT_STARTED',P3C='NOT_STARTED',P4='NOT_STARTED',
                frozen_sha256=receipt['frozen_core_and_contract_sha256'])
    write(art/'preflight.json',result)
    write(art/'result.json',dict(checks=[dict(id=k,passed=bool(ok),kind='numerical',reason=result['state']) for k,ok in checks.items()],
        metrics=dict(evaluations=len(rows),new_integrations=0,wall_seconds=result['wall_seconds']),scientific_change_required=missing))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',type=Path,required=True)
    run(parser.parse_args().run_dir)
