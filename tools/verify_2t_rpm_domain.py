"""Fase A autorizada: ocho puntos independientes, sin habilitar el dominio público.

Invocar desde la raíz: python -m tools.verify_2t_rpm_domain --output <carpeta nueva>.
No cambia ecuaciones, perfil, estado inicial ni criterios. Solo reemplaza RPM
en el caso canónico ya construido; evidencia de investigación, no formato GUI.
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import time

from motorsim.adaptive import run_adaptive
from motorsim.examples import example_project
from motorsim.performance import indicated_output
from motorsim.project_case import build_project_case
from motorsim.prototype import Monitor, environment, write_json
from motorsim.reference_results import BAND_PA, PROFILE
from motorsim.rpm_domain import validate_candidate_2t_rpm
from motorsim.simulation import Model

RPMS = (1000, 2000, 3000, 5000, 8000, 10000, 12000, 15000)


def run(folder):
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    base, _ = build_project_case(example_project('2t-reference'), rpm=3000)
    sources = ['simulation.py', 'simulation_case.py', 'adaptive.py']
    metadata = dict(environment=environment(), profile=asdict(PROFILE), band_Pa=BAND_PA,
        classification='CANDIDATE_2T_DOMAIN', public_range_enabled=False,
        source_sha256={name: hashlib.sha256((Path('motorsim')/name).read_bytes()).hexdigest()
                       for name in sources}, rows=[])
    write_json(folder/'campaign.json', metadata)
    for rpm in RPMS:
        validate_candidate_2t_rpm(rpm)
        model = Model(replace(base, rpm=rpm), external_band_pa=BAND_PA)
        monitor = Monitor(PROFILE.max_step_deg, time.monotonic(), emit=lambda *a, **k: None)
        try:
            result = run_adaptive(PROFILE, monitor, model)
        except Exception as exc:
            result = dict(converged=False, cycles=[], stop=f'{type(exc).__name__}: {exc}',
                          seconds=time.monotonic()-monitor.start)
        write_json(folder/f'{rpm}.json', dict(case=model.case.manifest(), result=result))
        last = result['cycles'][-1] if result['cycles'] else None
        row = dict(rpm=rpm, converged=result['converged'], cycles=len(result['cycles']),
            integration_seconds=result['seconds'], stop=result['stop'],
            minimum_substep_deg=result.get('actual_substep_deg', {}).get('minimum'),
            last_complete_cycle=last,
            indicated=indicated_output(last['W_C_J'], rpm, '2T') if last else None)
        # Un resultado parcial se conserva, pero no cuenta como punto acreditado.
        row['passed'] = bool(result['converged'] and last and last['balances_passed'])
        metadata['rows'].append(row)
        metadata['wall_seconds'] = time.monotonic()-started
        write_json(folder/'campaign.json', metadata)
        print(json.dumps({k:v for k,v in row.items() if k!='last_complete_cycle'}, ensure_ascii=True), flush=True)
    metadata['decision'] = 'GO' if all(r['passed'] for r in metadata['rows']) else 'BLOCKED'
    write_json(folder/'campaign.json', metadata)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
