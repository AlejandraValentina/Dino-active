"""Campaña candidata aislada: no altera producción, resultados ni dominio público.

python -m tools.verify_species_positivity --output <carpeta nueva>
La sustitución local de RK4 se restaura al terminar cada punto; uso serial consola.
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch

from motorsim import adaptive
from motorsim.examples import example_project
from motorsim.project_case import build_project_case
from motorsim.prototype import Monitor, environment, write_json
from motorsim.reference_results import PROFILE, BAND_PA
from motorsim.simulation import Model
from tools.stage_species_candidate import LimiterDiagnostics, candidate_rk4
from tools.diagnose_low_rpm import classification

ROOT=Path(__file__).resolve().parents[1]
RPMS=(1000,1500,1750,2000,2250,2500,2750,3000)


def scientific_equal(a,b):
    # La persistencia representa tuplas como listas; comparar la misma forma.
    return json.loads(json.dumps({k:v for k,v in a.items() if k!='seconds'})) == json.loads(json.dumps({k:v for k,v in b.items() if k!='seconds'}))


def execute(base,rpm,folder,candidate):
    started=time.monotonic()
    model=Model(replace(base,rpm=rpm),external_band_pa=BAND_PA)
    label=str(rpm) if candidate else '3000-baseline'
    with (folder/f'{label}-limiter.jsonl').open('x',encoding='utf-8') as stream:
        diag=LimiterDiagnostics(rpm,lambda row:stream.write(json.dumps(row,allow_nan=False)+'\n'))
        def replacement(t,y,dt,rhs,project):
            index=rhs.__code__.co_freevars.index('angle')
            angle=rhs.__closure__[index].cell_contents
            return candidate_rk4(diag,lambda offset:angle+offset*model.rate)(t,y,dt,rhs,project)
        monitor=Monitor(PROFILE.max_step_deg,time.monotonic(),emit=lambda *a,**k:None)
        if candidate:
            with patch.object(adaptive,'rk4',replacement): result=adaptive.run_adaptive(PROFILE,monitor,model)
        else: result=adaptive.run_adaptive(PROFILE,monitor,model)
    last=result['cycles'][-1] if result['cycles'] else None
    status='FAIL_TIME_BUDGET' if result['stop']=='límite de 60 segundos por resolución' else classification(result)
    row=dict(rpm=rpm,candidate=candidate,status=status,stop=result['stop'],
        cycles=len(result['cycles']),minimum_half_step_deg=result['actual_substep_deg']['minimum'],
        rejections=result['rejections_by_cause'],W_C_J=last['W_C_J'] if last else None,
        pmax_Pa=last['p_max_Pa'] if last else None,
        worst_independent=max(v for b in last['independent'].values() for v in b['normalized_m_u_f']) if last else None,
        worst_discrete_fresh=max(abs(b['normalized_m_u_f'][2]) for b in last['discrete'].values()) if last else None,
        integration_seconds=result['seconds'],**diag.metrics())
    historical=json.loads((ROOT/f'results/frontera-baja-2t-20260917/{rpm}.json').read_text(encoding='utf-8'))
    row['manifest_equal']=historical['case']==json.loads(json.dumps(model.case.manifest()))
    row['scientific_exact_equal']=scientific_equal(historical['result'],result)
    old=historical['result']['cycles'][-1] if historical['result']['cycles'] else None
    row['comparison_last_cycle']=None if not old or not last else dict(
        historical_cycle=old['cycle'],candidate_cycle=last['cycle'],
        W_delta_J=last['W_C_J']-old['W_C_J'],pmax_delta_Pa=last['p_max_Pa']-old['p_max_Pa'],
        historical_W_C_J=old['W_C_J'],historical_pmax_Pa=old['p_max_Pa'],
        warning='Diagnóstico; comparar ciclos distintos no acredita sensibilidad.')
    write_json(folder/f'{label}.json',dict(case=model.case.manifest(),result=result))
    row['wall_seconds']=time.monotonic()-started
    return row


def run(folder):
    folder.mkdir(parents=True,exist_ok=False)
    base,_=build_project_case(example_project('2t-reference'),rpm=3000)
    sources=('motorsim/simulation.py','motorsim/adaptive.py','tools/stage_species_candidate.py')
    evidence=dict(environment=environment(),profile=asdict(PROFILE),band_Pa=BAND_PA,
        minimum_half_step_deg=adaptive.MIN_SUBSTEP,warm_start=False,
        source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources},rows=[])
    evidence['baseline']=execute(base,3000,folder,False)
    write_json(folder/'campaign.json',evidence)
    print(json.dumps(evidence['baseline']),flush=True)
    for rpm in RPMS:
        row=execute(base,rpm,folder,True)
        evidence['rows'].append(row)
        write_json(folder/'campaign.json',evidence)
        print(json.dumps(row),flush=True)
    # Gate deliberado: no iniciar alta automáticamente ni integrar candidato.
    return evidence


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
