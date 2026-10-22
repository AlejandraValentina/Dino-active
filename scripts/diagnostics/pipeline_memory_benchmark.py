"""One small synthetic cycle, complete evidence pipeline; never an A3b run.

Pair legacy/streaming at the same fixture CFL. CFL is a diagnostic scale only,
never a mutation of a preregistered engine, threshold or historical artifact.
"""
import argparse
import gzip
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
from motorsim.integrated_2t import (IntegratedEngine2T, make_integrated_cycle_primary,
    audit_integrated_cycle_primary, make_integrated_engineering_output)
from motorsim._evidence_io import canonical_digest, write_primary_atomic, read_primary
from motorsim.mechanical import MechanicalLossModel, LossTerm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pipeline', choices=['legacy', 'streaming'], required=True)
    parser.add_argument('--fixture-cfl', type=float, choices=[.4, .2, .1], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = runpy.run_path(str(ROOT/'tests/test_integrated_2t.py'))
    combustion = fixture['FuelCoupledCombustionV1'](
        (fixture['WiebeComponent'](1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.01)
    config = fixture['_internal_cycle_fixture'](fuel_coupled_combustion=combustion,
        open_end_plenum_v2=True).configuration_dict()
    config['max_cfl'] = args.fixture_cfl
    engine = IntegratedEngine2T.from_configuration_dict(config)
    streaming = args.pipeline == 'streaming'
    if streaming:
        engine.enable_trajectory_spooling()
    process = psutil.Process()
    stopped = threading.Event()
    phase = ['setup']
    peaks = {}
    total_peak = [process.memory_info().rss]
    samples = []
    def monitor():
        while not stopped.wait(.01):
            rss = process.memory_info().rss
            total_peak[0] = max(total_peak[0], rss)
            peaks[phase[0]] = max(peaks.get(phase[0], 0), rss)
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    times = {}
    def measured(name, operation):
        phase[0] = name
        started = time.perf_counter()
        result = operation()
        times[name] = time.perf_counter()-started
        return result
    started, cpu = time.perf_counter(), time.process_time()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    primary_path = args.output.with_suffix('.primary.json.gz')
    start = measured('start_snapshot', lambda: engine.snapshot(streaming=streaming))
    def advance():
        for boundary in (60., 120., 180., 240., 300., 360.):
            fixture['_advance_cycle_fixture'](engine, boundary)
            samples.append({'angle': boundary, 'steps': engine.accepted_steps,
                'rss_bytes': process.memory_info().rss})
    measured('integration', advance)
    end = measured('end_snapshot', lambda: engine.snapshot(streaming=streaming))
    primary = measured('primary', lambda: make_integrated_cycle_primary(engine, start, end, 1))
    audit = measured('audit', lambda: audit_integrated_cycle_primary(primary,
        preserve_precycle_p7_baseline=True))
    if streaming:
        persisted = measured('write', lambda: write_primary_atomic(primary_path, primary,
            maximum_bytes=64*1024*1024))
    else:
        def legacy_write():
            payload = (json.dumps(primary, sort_keys=True, separators=(',', ':'),
                                 allow_nan=False)+'\n').encode()
            packed = gzip.compress(payload, compresslevel=6, mtime=0)
            import os
            with primary_path.open('wb') as output:
                output.write(packed)
                output.flush()
                os.fsync(output.fileno())
            return {'primary_sha256': hashlib.sha256(payload).hexdigest(),
                    'compressed_bytes': len(packed)}
        persisted = measured('write', legacy_write)
    loss = MechanicalLossModel((LossTerm('synthetic-ring','piston_ring',
        'SYNTHETIC_ASSUMPTION',mep_pa=1200.0),))
    engineering = measured('engineering', lambda: make_integrated_engineering_output(primary,
        displacement_m3=primary.get('swept_displacement_m3'),
        mechanical_loss_model=loss, load=1.0, periodicity_status='NOT_EVALUATED'))
    if streaming:
        loaded = measured('read', lambda: read_primary(primary_path,
            expected_sha256=persisted['primary_sha256']))
    else:
        loaded = measured('read', lambda: json.loads(gzip.decompress(primary_path.read_bytes())))
    reaudit = measured('reaudit', lambda: audit_integrated_cycle_primary(loaded,
        preserve_precycle_p7_baseline=True))
    # Same conventional compact restart state; no trajectory references escape.
    engine.compact_cycle_trace()
    checkpoint = measured('checkpoint', lambda: engine.snapshot())
    checkpoint_path = args.output.with_suffix('.checkpoint.json')
    checkpoint_path.write_text(json.dumps(checkpoint,sort_keys=True,separators=(',',':'))+'\n')
    stopped.set()
    thread.join()
    elapsed = time.perf_counter()-started
    assert audit['recomputed'] and reaudit['recomputed']
    result = {'scope':'SYNTHETIC_ASSUMPTION small integrated engine; not T1-A/B/C',
        'pipeline':args.pipeline,'fixture_cfl':args.fixture_cfl,
        'cells':sum(len(v) for v in engine.state['ducts'].values()),
        'accepted_steps':len(primary['trajectory']), 'rejected_steps':len(primary['rejected_trials']),
        'wall_s':elapsed,'cpu_s':time.process_time()-cpu,
        'phase_seconds':times,'phase_peak_rss_bytes':peaks,'peak_rss_bytes':total_peak[0],
        'integration_samples':samples,'primary_sha256':persisted['primary_sha256'],
        'artifact_bytes':persisted['compressed_bytes'],
        'checkpoint_sha256':hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        'conservation':primary['conservation'],'audit':audit,'reaudit':reaudit,
        'engineering_sha256':canonical_digest(engineering),
        'remaining_linear_data':'offset index, rejection log and engineering waveform arrays',
        'rss_measurement':'10 ms sampled worker RSS; other tests may run on host'}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['audit','reaudit','integration_samples']}))


if __name__ == '__main__':
    main()
