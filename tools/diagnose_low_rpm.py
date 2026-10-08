"""Observación de frontera 2T; invoca el solver original sin modificarlo.

python -m tools.diagnose_low_rpm --output <carpeta nueva>
La introspección solo lee locales cuando se rechaza un intento. No vuelve a
evaluar RHS durante la integración ni sustituye RK4, error_norm o Stepper.
"""
import argparse
from collections import deque
from dataclasses import asdict, replace
import hashlib
import inspect
import json
import math
from pathlib import Path
import time

from motorsim.adaptive import run_adaptive, MIN_SUBSTEP, step_factor
from motorsim.examples import example_project
from motorsim.performance import indicated_output
from motorsim.project_case import build_project_case
from motorsim.prototype import Monitor, environment, write_json
from motorsim.reference_results import BAND_PA, PROFILE
from motorsim.simulation import Model, InvalidStage, StopCalculation

RPMS = (1500, 1750, 2000, 2250, 2500, 2750, 3000)
ROOT = Path(__file__).resolve().parents[1]


def call_context():
    """Copias de datos, sin conservar frames ni alterar sus objetos."""
    frame = inspect.currentframe().f_back
    context = {}
    try:
        while frame:
            name, loc = frame.f_code.co_name, frame.f_locals
            if name == 'advance':
                context['advance'] = {k: list(loc[k]) if isinstance(loc[k], (list, tuple)) else loc[k]
                    for k in ('angle', 'state', 'event', 'heat', 'h', 'dt', 'failures') if k in loc}
            elif name == 'rk4':
                context['rk4'] = {k: list(loc[k]) if isinstance(loc[k], list) else loc[k]
                    for k in ('t', 'state', 'dt', 'y', 'k1', 'k2', 'k3', 'k4') if k in loc}
            elif name == 'run_adaptive':
                context['cycle'] = loc['cycle']
            frame = frame.f_back
    finally:
        del frame
    return context


class Observation:
    def __init__(self):
        self.streak = self.maximum_streak = 0
        self.first_physical = None
        self.physical_failures = []
        self.rejections = []
        self.tail = deque(maxlen=12)

    def invalid(self, angle, state, heat, error):
        record = dict(angle_deg=angle, state=state.copy(), heat=heat,
                      error=str(error), context=call_context())
        if self.first_physical is None: self.first_physical = record
        self.physical_failures.append(record)

    def trace(self, row):
        self.streak = 0 if row['accepted'] else self.streak+1
        self.maximum_streak = max(self.maximum_streak, self.streak)
        record = dict(row, consecutive_rejections=self.streak)
        # Contexto completo solo al rechazar; no hay evaluaciones adicionales.
        if not row['accepted']:
            frame = inspect.currentframe().f_back
            try:
                loc = frame.f_locals
                record['context'] = call_context()
                if row['cause'] == 'local_error':
                    errors = []
                    for j in range(12):
                        start, full, fine = loc['state'][j], loc['full'][j], loc['fine'][j]
                        atol = PROFILE.atol_energy if j % 3 == 1 else PROFILE.atol_mass
                        scale = atol+PROFILE.rtol*max(abs(start), abs(fine))
                        errors.append(dict(component=f'{Model.layout.cv[j//3]}.{("m","U","F")[j%3]}',
                            start=start, full=full, fine=fine, scale=scale,
                            absolute_estimate=abs(fine-full)/15, normalized=abs(fine-full)/15/scale))
                    record['component_errors'] = errors
                error = row['error'] if row['error'] is not None else math.inf
                factor = .5 if row['cause'] == 'nonphysical' else step_factor(error, rejected=True)
                record['next_requested_full_deg'] = row['proposed_deg']*factor
                record['next_requested_half_deg'] = row['proposed_deg']*factor/2
            finally:
                del frame
            self.rejections.append(record)
        self.tail.append(record)


class ObservedModel(Model):
    def __init__(self, case, observation):
        super().__init__(case, external_band_pa=BAND_PA)
        self.observation = observation

    def evaluate(self, angle, state, heat=None):
        try:
            return super().evaluate(angle, state, heat)
        except (InvalidStage, StopCalculation) as exc:
            self.observation.invalid(angle, state, heat, exc)
            raise


def classification(result):
    if result['converged']: return 'PASS'
    if result['stop'].startswith('paso mínimo'): return 'FAIL_MIN_STEP'
    if 'F fuera de [0,m]: F=-' in result['stop']: return 'FAIL_NEGATIVE_FRESH'
    return 'FAIL_OTHER'


def run(folder):
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    base, _ = build_project_case(example_project('2t-reference'), rpm=3000)
    sources = ('simulation.py', 'simulation_case.py', 'adaptive.py', 'prototype.py', 'rpm_domain.py')
    evidence = dict(environment=environment(), profile=asdict(PROFILE), band_Pa=BAND_PA,
        minimum_half_step_deg=MIN_SUBSTEP, warm_start=False,
        source_sha256={name:hashlib.sha256((ROOT/'motorsim'/name).read_bytes()).hexdigest() for name in sources},
        boundary_rpms=list(RPMS), rows=[])
    for rpm in (1000, *RPMS):
        point_start = time.monotonic()
        observation = Observation()
        model = ObservedModel(replace(base, rpm=rpm), observation)
        monitor = Monitor(PROFILE.max_step_deg, time.monotonic(), emit=lambda *a, **k: None)
        result = run_adaptive(PROFILE, monitor, model, trace=observation.trace)
        last = result['cycles'][-1] if result['cycles'] else None
        dt_deg = result['actual_substep_deg']['minimum']
        row = dict(rpm=rpm, classification=classification(result), converged=result['converged'],
            terminal_reason=result['stop'], complete_cycles=len(result['cycles']),
            integration_seconds=result['seconds'], accepted_half_steps=result['accepted_steps'],
            rejected_attempts=result['rejected_steps'], minimum_accepted_half_deg=dt_deg,
            minimum_accepted_dt_s=dt_deg/model.rate if dt_deg is not None else None,
            max_consecutive_rejections=observation.maximum_streak,
            first_physical_violation=observation.first_physical,
            metrics_kind=('accepted' if result['converged'] else 'diagnostic_last_complete_cycle') if last else None,
            last_complete_cycle=last, indicated=indicated_output(last['W_C_J'],rpm,'2T') if last else None,
            worst_independent=max(v for b in last['independent'].values() for v in b['normalized_m_u_f']) if last else None)
        # Los JSON individuales preservan todos los campos científicos originales.
        write_json(folder/f'{rpm}.json', dict(case=model.case.manifest(), result=result))
        write_json(folder/f'{rpm}-observation.json', dict(first_physical=observation.first_physical,
            physical_failures=observation.physical_failures, rejections=observation.rejections, tail=list(observation.tail)))
        row['wall_seconds'] = time.monotonic()-point_start  # incluye escribir resultado/observación
        evidence['rows'].append(row)
        evidence['wall_seconds'] = time.monotonic()-started
        write_json(folder/'campaign.json', evidence)
        print(json.dumps({k:v for k,v in row.items() if k not in ('first_physical_violation','last_complete_cycle')}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
