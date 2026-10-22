"""Single owner-authorized representative cycle, separate from every A3b run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psutil
from scripts.diagnostics.integrated_solver_verification_a3b_v3 import _build_configuration
from scripts.diagnostics.integrated_solver_verification_a3b_v4 import bounded_process, atomic, watch_parent
from motorsim.engine_configuration import implementation_source_hashes
from motorsim.exploratory_workflow import _advance_cycle, preflight
from motorsim.integrated_2t import (IntegratedEngine2T, make_integrated_cycle_primary,
    audit_integrated_cycle_primary, make_integrated_engineering_output)
from motorsim._evidence_io import canonical_digest, read_primary, write_primary_atomic
from motorsim.mechanical import MechanicalLossModel


def worker(out, deadline, binding):
    process = psutil.Process()
    phase = ['setup']
    peaks, times, samples = {}, {}, []
    stop = threading.Event()
    def monitor():
        while not stop.wait(.02):
            peaks[phase[0]] = max(peaks.get(phase[0], 0), process.memory_info().rss)
    threading.Thread(target=monitor, daemon=True).start()
    def measure(name, action):
        phase[0] = name
        atomic(out/'progress.json', {'phase':name, 'elapsed_s':time.monotonic()-started})
        tick = time.monotonic()
        value = action()
        times[name] = time.monotonic()-tick
        return value
    started, cpu, io = time.monotonic(), time.process_time(), process.io_counters()._asdict()
    built = _build_configuration('T1-A')
    effective = built['effective']
    if (implementation_source_hashes() != binding['source_hashes'] or
            canonical_digest(effective) != binding['effective_sha256']):
        raise ValueError('worker binding changed before solver')
    engine = IntegratedEngine2T.from_configuration_dict(effective['native_configuration'])
    engine.enable_trajectory_spooling()
    start = measure('start_snapshot', lambda: engine.snapshot(streaming=True))
    def progress(row):
        samples.append({**row,'elapsed_s':time.monotonic()-started})
        atomic(out/'progress.json', {'phase':phase[0], 'last':samples[-1]})
    rejected = measure('integration', lambda: _advance_cycle(engine, 1,
        deadline=deadline, memory_limit_mib=3072, progress=progress))
    end = measure('end_snapshot', lambda: engine.snapshot(streaming=True))
    primary = measure('primary', lambda: make_integrated_cycle_primary(engine,start,end,1,
        rejected_trials=rejected,runner_sha256=binding['driver_sha256']))
    audit = measure('audit', lambda: audit_integrated_cycle_primary(primary,
        preserve_precycle_p7_baseline=True))
    if audit.get('recomputed') is not True:
        raise ValueError('independent replay did not pass')
    packed = measure('primary_persistence', lambda: write_primary_atomic(
        out/'cycle-0001.json.gz',primary,maximum_bytes=512*1024**2))
    loaded = measure('primary_reload', lambda: read_primary(out/'cycle-0001.json.gz',
        expected_sha256=packed['primary_sha256']))
    reaudit = measure('reaudit', lambda: audit_integrated_cycle_primary(loaded,
        preserve_precycle_p7_baseline=True))
    if reaudit.get('recomputed') is not True:
        raise ValueError('persisted primary replay failed')
    engineering = measure('engineering', lambda: make_integrated_engineering_output(primary,
        displacement_m3=primary['swept_displacement_m3'],
        mechanical_loss_model=MechanicalLossModel.from_dict(effective['mechanical_loss_model']),
        load=effective['operating_conditions']['load'],periodicity_status='NOT_EVALUATED'))
    atomic(out/'engineering.json', engineering)
    def checkpoint():
        engine.compact_cycle_trace()
        snapshot = engine.snapshot()
        atomic(out/'checkpoint.json', snapshot)
        restored = IntegratedEngine2T.from_configuration_dict(effective['native_configuration'])
        restored.restore(json.loads((out/'checkpoint.json').read_text()))
        if canonical_digest(restored.snapshot()) != canonical_digest(snapshot):
            raise ValueError('checkpoint restore differs')
        return hashlib.sha256((out/'checkpoint.json').read_bytes()).hexdigest()
    checkpoint_sha = measure('checkpoint_write_restore', checkpoint)
    stop.set()
    result = {'decision':'PROCEED_TO_PERIODIC_POINT','cycles_completed':1,
        'periodicity':'NOT_EVALUATED','wall_s':time.monotonic()-started,
        'cpu_s':time.process_time()-cpu,'phase_seconds':times,'phase_peak_rss_bytes':peaks,
        'progress_samples':samples,'io_initial':io,'io_final':process.io_counters()._asdict(),
        'accepted_steps':len(primary['trajectory']),'cfl_rejections':len(rejected),
        'audit':audit,'reaudit':reaudit,'conservation':primary['conservation'],
        'checkpoint_sha256':checkpoint_sha,'checkpoint_restore':'EXACT_CANONICAL_MATCH',
        'primary':packed,'binding':binding}
    atomic(out/'result.json',result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--deadline',type=float)
    args = parser.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        raise ValueError('external artifact root required')
    if args.worker:
        parent = psutil.Process(os.getppid())
        threading.Thread(target=watch_parent,args=(parent.pid,parent.create_time()),daemon=True).start()
        worker(out,args.deadline,json.loads((out/'binding.json').read_text()))
        return
    if psutil.virtual_memory().available < 4096*1024**2:
        raise RuntimeError('ENVIRONMENT_BLOCKED: 4096 MiB free required')
    out.mkdir(parents=True,exist_ok=False)  # no retries/reuse
    built = _build_configuration('T1-A')
    check = preflight(built['variant'],rpm=3000,max_cycles=1,
                      budget_seconds=600,memory_limit_mib=3072)
    if check['total_finite_volume_cells'] != 48 or built['effective']['native_configuration']['max_cfl'] != .4:
        raise ValueError('unexpected representative configuration')
    historical = (Path.home()/'Dino-artifacts/isv1-a3b-fix1-exec-20261020/'
        'integrated-solver-verification-v1/a3b/T1-A/inv01-2aacc2f052/configuration.json')
    old = json.loads(historical.read_text())
    if old['native_configuration'] != built['effective']['native_configuration']:
        raise ValueError('scientific reference configuration changed')
    binding = {'source_hashes':implementation_source_hashes(),
        'effective_sha256':canonical_digest(built['effective']),
        'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'supervisor_sha256':hashlib.sha256((ROOT/'scripts/diagnostics/integrated_solver_verification_a3b_v4.py').read_bytes()).hexdigest(),
        'reference_configuration_sha256':hashlib.sha256(historical.read_bytes()).hexdigest(),
        'scope':'one independent diagnostic; not A3b; no periodicity claim'}
    atomic(out/'binding.json',binding)
    atomic(out/'configuration.json',built['effective'])
    atomic(out/'preflight.json',check)
    if psutil.virtual_memory().available < 4096*1024**2:
        raise RuntimeError('ENVIRONMENT_BLOCKED immediately before launch')
    started = time.monotonic()
    # Ten seconds reserved for termination and durable supervisor closure.
    outcome = bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',
        '--out',str(out),'--deadline',str(started+590)],out/'worker.log',started+590)
    outcome['inclusive_wall_s'] = time.monotonic()-started
    outcome['binding'] = binding
    outcome['budget_s'] = 600
    atomic(out/'supervisor.json',outcome)
    print(json.dumps(outcome))
    if outcome['exit_code'] != 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
