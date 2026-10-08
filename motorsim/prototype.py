"""Ejecutar únicamente la serie autorizada: python -m motorsim.prototype."""
import argparse
import csv
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import signal
import sys
import time

from .simulation import CV, Model, StopCalculation, run_resolution, sensitivity
from .simulation_case import SyntheticCase
from .adaptive import PROFILES, run_adaptive


def memory_mib():
    """Máximo residente del proceso completo; no solo objetos Python."""
    if os.name == 'nt':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError(ctypes.get_last_error(), 'GetProcessMemoryInfo')
        return counters.PeakWorkingSetSize / 2**20
    import resource
    divisor = 2**20 if sys.platform == 'darwin' else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor


def environment():
    cpu = platform.processor()
    if os.name == 'nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    return dict(utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
                os=platform.platform(), cpu=cpu, logical_cpus=os.cpu_count(),
                machine=platform.machine(), qt_loaded=any(k.startswith('PySide6') for k in sys.modules))


class Monitor:
    def __init__(self, step, series_start, cancelled=lambda: False, emit=print,
                 clock=time.monotonic, memory=memory_mib):
        self.step, self.series_start = step, series_start
        self.cancelled, self.emit, self.clock, self.memory = cancelled, emit, clock, memory
        self.start = self.clock()
        self.last_progress = self.last_memory = self.start
        self.peak_mib = self.memory()

    def __call__(self, cycle, angle, rhs_count, completed=False):
        now = self.clock()
        if self.cancelled():
            raise StopCalculation('cancelación solicitada')
        if now-self.start >= 60:
            raise StopCalculation('límite de 60 segundos por resolución')
        if now-self.series_start >= 180:
            raise StopCalculation('límite de 180 segundos de la serie')
        if now-self.last_memory >= .2 or completed:
            self.peak_mib = max(self.peak_mib, self.memory())
            self.last_memory = now
        if self.peak_mib > 512:
            raise StopCalculation('límite de 512 MiB residentes del proceso')
        if completed or now-self.last_progress >= .5:
            self.emit(f'{self.step:g}° | ciclo {cycle}/30 | ángulo {angle:.3f}° | '
                      f'{now-self.start:.2f} s | {self.peak_mib:.1f} MiB | RHS {rhs_count}'
                      + (' | vuelta completa' if completed else ''), flush=True)
            self.last_progress = now


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def write_samples(path, cycles):
    fields = ['cycle', 'angle_deg', 'time_s', 'W_C_J', 'W_K_J', 'Q_J', 'converted_kg']
    for cv in CV:
        fields.extend(f'{cv}_{unit}' for unit in ('m_kg', 'U_J', 'F_kg', 'p_Pa', 'T_K', 'Y', 'V_m3'))
    for j in range(6):
        fields.extend(f'link{j}_{unit}' for unit in ('q_kg_s', 'H_W', 'F_kg_s', 'direction'))
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for samples in cycles:
            for row in samples:
                flat = {key: row[key] for key in fields[1:7]}
                flat['cycle'] = int((samples[0]['angle_deg']-180)/360)+1
                for i, cv in enumerate(CV):
                    values = (*row['state'][3*i:3*i+3], *row['p_T_Y'][i], row['V_m3'][i])
                    for key, value in zip(('m_kg', 'U_J', 'F_kg', 'p_Pa', 'T_K', 'Y', 'V_m3'), values):
                        flat[f'{cv}_{key}'] = value
                for j, flow in enumerate(row['flows_kg_s_W_kg_s']):
                    for key, value in zip(('q_kg_s', 'H_W', 'F_kg_s'), flow):
                        flat[f'link{j}_{key}'] = value
                    flat[f'link{j}_direction'] = 'forward' if flow[0] > 0 else ('reverse' if flow[0] < 0 else 'closed/equal')
                writer.writerow(flat)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Viabilidad S2T-0D-01: tres resoluciones, sin Qt ni ondas.')
    parser.add_argument('--output', type=Path, help='Directorio nuevo para resultados; no se sobrescribe.')
    args = parser.parse_args(argv)
    output = args.output or Path('results/simulacion-2t') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, exist_ok=False)
    cancelled = False
    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
    previous = signal.signal(signal.SIGINT, cancel)
    started = time.monotonic()
    runs = []
    try:
        case = SyntheticCase()
        model = Model(case)
        write_json(output/'case.json', {**case.manifest(), 'initial_state_m_U_F': model.initial_state()[:12],
                                      'derived_duct_volume_m3': model.duct_volumes, 'derived_throat_m2': model.throats})
        metadata = environment()
        write_json(output/'environment.json', metadata)
        print(f'S2T-0D-01 sintético, 0D sin ondas. Resultados: {output.resolve()}', flush=True)
        for profile in PROFILES:
            step = profile.max_step_deg
            monitor = Monitor(step, started, lambda: cancelled)
            with (output/f'profile-{profile.name}-attempts.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    'angle_deg', 'proposed_deg', 'substep_deg', 'error', 'worst', 'accepted', 'cause', 'rhs'])
                writer.writeheader()
                result = run_adaptive(profile, monitor, model, trace=writer.writerow)
            monitor.peak_mib = max(monitor.peak_mib, memory_mib())
            result['peak_process_MiB'] = monitor.peak_mib
            runs.append(result)
            prefix = f'step-{step:g}'
            write_samples(output/f'{prefix}-last-two.csv', result['last_two_cycles'])
            compact = {k: v for k, v in result.items() if k not in ('last_two_cycles', 'partial')}
            if result['partial']:
                write_samples(output/f'{prefix}-partial.csv', [result['partial']['samples']])
                compact['partial'] = {k: v for k, v in result['partial'].items() if k != 'samples'}
            write_json(output/f'{prefix}-summary.json', compact)
            print(f'{step:g}°: {result["stop"]}; {len(result["cycles"])} ciclos, {result["seconds"]:.3f} s', flush=True)
            if cancelled or time.monotonic()-started >= 180:
                break
        comparison = sensitivity(runs)
        summary = dict(case=case.identifier, method='RK4 step doubling, accepted two half steps, no extrapolation', resolutions=[
            {k: v for k, v in r.items() if k not in ('cycles', 'last_two_cycles', 'partial')}
            | {'completed_cycles': len(r['cycles']), 'last_cycle': r['cycles'][-1] if r['cycles'] else None}
            for r in runs], sensitivity=comparison, viability_passed=comparison['passed'],
            series_seconds=time.monotonic()-started, environment=metadata,
            limits=dict(cycles_per_run=30, seconds_per_run=60, series_seconds=180,
                        process_MiB=512, max_consecutive_rejections=8, minimum_step_deg=.001,
                        rhs_per_run=2000000, T_K=[100, 4000], p_Pa=[1000, 20000000]))
        write_json(output/'summary.json', summary)
        print('Viabilidad acreditada.' if comparison['passed'] else 'Viabilidad NO acreditada. Ver summary.json.', flush=True)
        return 0 if comparison['passed'] else (130 if cancelled else 2)
    finally:
        signal.signal(signal.SIGINT, previous)


if __name__ == '__main__':
    raise SystemExit(main())
