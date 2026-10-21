"""Bounded synthetic engine fixture benchmark, never an A3b continuation.

Legacy mode restores only the previous evidence allocation algorithms in this
process. Both modes execute the same current physical implementation and bind
its real source hashes. Outputs are engineering measurements, not gate data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
import threading
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import motorsim.integrated_2t as integrated


def legacy_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['legacy', 'optimized'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'legacy':
        integrated._evidence_sha256 = legacy_hash
        integrated._json_evidence_equal = lambda a, b: integrated._jsonify(a) == integrated._jsonify(b)
    fixture = runpy.run_path(str(ROOT / 'tests/test_integrated_2t.py'))
    combustion = fixture['FuelCoupledCombustionV1'](
        (fixture['WiebeComponent'](1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.01)
    engine = fixture['_internal_cycle_fixture'](
        fuel_coupled_combustion=combustion, open_end_plenum_v2=True)
    proc = psutil.Process()
    stop = threading.Event()
    peak = [proc.memory_info().rss]
    phase = ['setup']
    phase_peaks = {}
    def monitor():
        while not stop.wait(.01):
            rss = proc.memory_info().rss
            peak[0] = max(peak[0], rss)
            phase_peaks[phase[0]] = max(phase_peaks.get(phase[0], 0), rss)
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    began = time.perf_counter()
    cpu = time.process_time()
    rows = []
    for cycle in (1, 2):
        phase[0] = f'{cycle}:start_snapshot'
        start = engine.snapshot()
        rss_start = proc.memory_info().rss
        mark = time.perf_counter()
        phase[0] = f'{cycle}:advance'
        fixture['_advance_cycle_fixture'](engine, cycle * 360.0)
        advance_s = time.perf_counter() - mark
        steps = engine.accepted_steps - start['accepted_steps']
        rss_advance = proc.memory_info().rss
        mark = time.perf_counter()
        phase[0] = f'{cycle}:end_snapshot'
        end = engine.snapshot()
        snapshot_s = time.perf_counter() - mark
        mark = time.perf_counter()
        phase[0] = f'{cycle}:make'
        primary = integrated.make_integrated_cycle_primary(engine, start, end, cycle)
        make_s = time.perf_counter() - mark
        mark = time.perf_counter()
        phase[0] = f'{cycle}:audit'
        audit = integrated.audit_integrated_cycle_primary(primary, preserve_precycle_p7_baseline=True)
        audit_s = time.perf_counter() - mark
        phase[0] = f'{cycle}:measurement_serialization'
        rows.append({'cycle': cycle, 'steps': steps, 'advance_s': advance_s,
            'seconds_per_step': advance_s / steps, 'steps_per_second': steps / advance_s,
            'snapshot_s': snapshot_s, 'make_s': make_s, 'audit_s': audit_s,
            'rss_start': rss_start, 'rss_after_advance': rss_advance,
            'rss_growth_per_step': (rss_advance-rss_start)/steps,
            'primary_sha256': legacy_hash(primary), 'audit': audit,
            'conservation': primary['conservation']})
        del start, end, primary, audit
    stop.set()
    thread.join()
    full = proc.memory_full_info()
    result = {'scope': 'SYNTHETIC_ASSUMPTION small engine fixture, two cycles; not T1-B/C',
        'mode': args.mode, 'wall_s': time.perf_counter()-began,
        'cpu_s': time.process_time()-cpu, 'sampled_peak_rss_bytes': peak[0],
        'sampled_phase_peak_rss_bytes': phase_peaks,
        'final_rss_bytes': full.rss, 'final_private_uss_bytes': getattr(full, 'uss', None),
        'cycles': rows, 'parent_process':'No simulation parent; run_logged launcher excluded from worker RSS'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'cycles'}))


if __name__ == '__main__':
    main()
