"""Ensayo candidato exterior: 100 Pa A/B/C condicional, luego 50 Pa C."""
import argparse
import csv
from datetime import datetime
from pathlib import Path
import signal
import time

from .adaptive import PROFILES, run_adaptive
from .simulation import Model, sensitivity
from .prototype import Monitor, environment, memory_mib, write_json, write_samples


def band_comparison(reference, candidate):
    """Dos soluciones convergidas; umbrales existentes, sin tendencia temporal."""
    if not reference['converged'] or not candidate['converged']:
        return dict(passed=False, reason='Requiere ambas bandas convergidas.')
    # La comparación fina existente aplica los pisos y umbrales originales.
    metrics = sensitivity([reference, reference, candidate])
    return dict(passed=metrics['tolerances_passed'], differences=metrics['fine'],
                meaning='dependencia respecto a la banda, no refinamiento temporal')


def execute(output, cancelled=lambda: False, runner=run_adaptive):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    metadata = environment()
    write_json(output/'environment.json', metadata)
    runs = []

    def run(profile, band, series_start):
        model = Model(external_band_pa=band)
        folder = output/f'band-{band}-profile-{profile.name}'
        folder.mkdir()
        variant = dict(law='external regularized candidate', delta_p_Pa=band,
                       external_links=[0, 5], physically_calibrated=False)
        write_json(folder/'case.json', dict(**model.case.manifest(), variant=variant,
                   initial_state_m_U_F=model.initial_state()[:12]))
        print(f'Variante candidata: banda {band} Pa, perfil {profile.name}', flush=True)
        monitor = Monitor(profile.max_step_deg, series_start, cancelled)
        with (folder/'attempts.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                'angle_deg', 'proposed_deg', 'substep_deg', 'error', 'worst', 'accepted', 'cause', 'rhs'])
            writer.writeheader()
            result = runner(profile, monitor, model, trace=writer.writerow)
        result.update(variant=variant, peak_process_MiB=max(monitor.peak_mib, memory_mib()))
        write_samples(folder/'last-two.csv', result['last_two_cycles'])
        compact = {k: v for k, v in result.items() if k not in ('last_two_cycles', 'partial')}
        if result['partial']:
            write_samples(folder/'partial.csv', [result['partial']['samples']])
            compact['partial'] = {k: v for k, v in result['partial'].items() if k != 'samples'}
        write_json(folder/'summary.json', compact)
        return result

    for profile in PROFILES:
        if cancelled() or time.monotonic()-started >= 180:
            break
        result = run(profile, 100, started)
        runs.append(result)
        if not result['converged']:
            break
    comparison = sensitivity(runs)
    series_seconds = time.monotonic()-started
    extra = None
    dependence = dict(passed=False, reason='Omitida: serie 100 Pa no aprobada.')
    if comparison['passed'] and not cancelled():
        extra = run(PROFILES[2], 50, time.monotonic())
        dependence = band_comparison(runs[-1], extra)
    summary = dict(variant='external regularized candidate', primary_delta_p_Pa=100,
        profiles_executed=[r['profile']['name'] for r in runs],
        profiles_omitted=[p.name for p in PROFILES[len(runs):]],
        sensitivity=comparison, band_dependence=dependence, comparison_50_Pa_executed=extra is not None,
        series_100_Pa_seconds=series_seconds, total_seconds=time.monotonic()-started,
        viability_passed=comparison['passed'] and dependence['passed'], environment=metadata,
        limits=dict(cycles_per_run=30, seconds_per_run=60, series_100_Pa_seconds=180,
                    comparison_50_Pa_seconds=60, process_MiB=512, rhs_per_run=2000000,
                    minimum_substep_deg=.001, max_consecutive_rejections=8,
                    T_K=[100, 4000], p_Pa=[1000, 20000000]))
    write_json(output/'summary.json', summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    output = args.output or Path('results/simulacion-2t')/datetime.now().strftime('regularizado-%Y%m%d-%H%M%S-%f')
    cancelled = False
    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
    previous = signal.signal(signal.SIGINT, cancel)
    try:
        result = execute(output, lambda: cancelled)
        print(result, flush=True)
        return 0 if result['viability_passed'] else (130 if cancelled else 2)
    finally:
        signal.signal(signal.SIGINT, previous)


if __name__ == '__main__':
    raise SystemExit(main())
