"""Small partial-horizon trajectory growth measurement; never runs A3b."""
import argparse
import json
from pathlib import Path
import runpy
import sys
import time
import tracemalloc

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trajectory', choices=['list', 'spool'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = runpy.run_path(str(ROOT/'tests/test_integrated_2t.py'))
    engine = fixture['_internal_cycle_fixture'](open_end_plenum_v2=True)
    if args.trajectory == 'spool':
        engine.enable_trajectory_spooling()
    process = psutil.Process()
    rows = []
    tracemalloc.start()
    began = time.perf_counter()
    for angle in [10., 30., 60.]:
        fixture['_advance_cycle_fixture'](engine, angle)
        current, peak = tracemalloc.get_traced_memory()
        rows.append({'angle': angle, 'accepted_steps': engine.accepted_steps,
            'rss_bytes': process.memory_info().rss, 'retained_traced_bytes': current,
            'peak_traced_bytes': peak, 'spool_bytes': getattr(engine.trace, 'storage_bytes', 0),
            'index_bytes': getattr(engine.trace, 'index_bytes', 0)})
    elapsed = time.perf_counter()-began
    tracemalloc.stop()
    from motorsim.integrated_2t import _evidence_sha256
    digest = _evidence_sha256(engine.snapshot())
    result = {'scope':'Small synthetic engine partial horizon 60 degrees, not A3b',
        'trajectory': args.trajectory, 'wall_s_with_tracemalloc': elapsed,
        'snapshot_sha256': digest, 'samples': rows,
        'retained_growth_bytes_per_step': (rows[-1]['retained_traced_bytes']-rows[0]['retained_traced_bytes'])/(rows[-1]['accepted_steps']-rows[0]['accepted_steps'])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
