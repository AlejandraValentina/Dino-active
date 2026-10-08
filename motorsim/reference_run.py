"""Ejecución individual de referencia o copia de proyecto, sin Qt."""
import argparse
import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import threading
import time

from .adaptive import run_adaptive, PROFILES
from .simulation import Model
from .prototype import Monitor, environment, memory_mib
from .reference_results import (BAND_PA, PROFILE, new_output_path, reference_inputs, save_result,
                                validated_model, project_inputs)
from .project import Project


def emit(data):
    print(json.dumps(data, ensure_ascii=True, allow_nan=False), flush=True)


def execute(folder, cancelled, report=emit, *, inputs=None):
    setup_started = time.monotonic()
    inputs = reference_inputs() if inputs is None else inputs
    model, profile = validated_model(inputs)
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    setup_seconds = started-setup_started
    monitor = Monitor(profile.max_step_deg, started, cancelled.is_set, emit=lambda *a, **k: None)
    last = started-1
    def progress(cycle, angle, rhs, completed=False):
        nonlocal last
        monitor(cycle, angle, rhs, completed)
        now = time.monotonic()
        if completed or now-last >= .5:
            report(dict(event='progress', cycle=cycle, completed_cycles=cycle if completed else cycle-1,
                        seconds=now-started, rhs=rhs, calculation_MiB=monitor.peak_mib))
            last = now
    try:
        with (folder/'attempts.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                'angle_deg', 'proposed_deg', 'substep_deg', 'error', 'worst', 'accepted', 'cause', 'rhs'])
            writer.writeheader()
            result = run_adaptive(profile, progress, model, trace=writer.writerow)
        status = 'converged' if result['converged'] else 'not_converged'
        if cancelled.is_set():
            status = 'cancelled'
            result['converged'] = False
            result['stop'] = 'cancelación solicitada'
    except Exception as exc:
        status = 'error'
        result = dict(profile=asdict(profile), converged=False, cycles=[], last_two_cycles=[],
                      partial=None, seconds=time.monotonic()-started, stop=f'{type(exc).__name__}: {exc}')
    result['peak_process_MiB'] = max(monitor.peak_mib, memory_mib())
    timings = save_result(folder, result, status, inputs, environment(),
                          timing_context=dict(setup_seconds=setup_seconds,started=setup_started))
    report(dict(event='finished', status=status, manifest=str((folder/'manifest.json').resolve()),
                timings=timings))
    return 0 if status == 'converged' else (130 if status == 'cancelled' else 2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--cycle',choices=('2T','4T'),default='2T',help='Ciclo del caso fijo de referencia.')
    parser.add_argument('--control-stdin', action='store_true', help='Control cooperativo por pipe: cancel + salto de línea.')
    parser.add_argument('--project-input', type=Path, help='Copia de entradas efectivas, comprobada nuevamente en el hijo.')
    parser.add_argument('--profile-c-check', action='store_true', help='Contraste de consola C/100 Pa; solo con copia de proyecto.')
    parser.add_argument('--sweep-input', type=Path, help='Copia común y lista acotada de RPM; ejecución secuencial.')
    args = parser.parse_args(argv)
    cancelled = threading.Event()
    def control():
        # os.read evita el bloqueo del búfer Python al terminar un hilo daemon.
        buffer = b''
        try:
            while not cancelled.is_set():
                chunk = os.read(0, 1024)
                if not chunk:  # El padre desapareció/cerró el canal: no seguir huérfano.
                    cancelled.set()
                    return
                buffer = (buffer+chunk)[-1024:]
                if b'cancel\n' in buffer:
                    cancelled.set()
        except OSError:
            cancelled.set()
    if args.control_stdin:
        threading.Thread(target=control, daemon=True).start()
    previous = signal.signal(signal.SIGINT, lambda *a: cancelled.set())
    try:
        inputs = reference_inputs(args.cycle)
        if args.sweep_input:
            if args.project_input or args.profile_c_check:raise ValueError('El barrido usa solo perfil B y una copia común.')
            if args.sweep_input.stat().st_size>2*1024*1024:raise ValueError('Copia de barrido demasiado grande.')
            from .sweep import execute_sweep
            return execute_sweep(args.output or new_output_path(),cancelled,emit,
                                 json.loads(args.sweep_input.read_text(encoding='utf-8')))
        if args.profile_c_check and not args.project_input:
            raise ValueError('El contraste C requiere --project-input.')
        if args.project_input:
            if args.project_input.stat().st_size > 16*1024*1024:
                raise ValueError('Copia de entradas demasiado grande.')
            inputs = json.loads(args.project_input.read_text(encoding='utf-8'))
            validated_model(inputs)
            if 'origin' not in inputs:
                raise ValueError('Se requiere una copia de proyecto.')
            if args.profile_c_check:
                inputs = project_inputs(Project.from_dict(inputs['project_snapshot']), inputs['origin'], PROFILES[2],
                                        rpm=inputs.get('operating_point', {}).get('rpm'))
        return execute(args.output or new_output_path(), cancelled, inputs=inputs)
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, RuntimeError) as exc:
        emit(dict(event='error', message=str(exc)))
        return 2
    finally:
        signal.signal(signal.SIGINT, previous)


if __name__ == '__main__':
    raise SystemExit(main())
