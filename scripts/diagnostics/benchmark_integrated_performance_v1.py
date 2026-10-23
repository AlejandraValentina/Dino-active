"""Bounded A/B9000 comparison using the existing engineering point runner.

One invocation, three cycles, conventional diagnostics/checkpoints. An explicit
source root permits the immutable detached baseline to run in its own process.
No X30, full RPM sweep, warm-start transfer or historical resume is performed.
"""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    source = args.source_root.resolve()
    sys.path.insert(0, str(source))
    from motorsim import engineering_point as point
    if Path(point.__file__).resolve().parent.parent != source:
        raise RuntimeError('Unexpected source package selected')
    native = json.loads(args.config.read_text())
    if native['reference_rpm'] != 9000:
        raise ValueError('Diagnostic scope is existing 9000 RPM input only')
    output = args.output.resolve()
    limits = point.parser().parse_args([
        '--config', str(args.config.resolve()), '--output', str(output),
        '--rpm', '9000', '--max-cycles', '3', '--wall-seconds', '180',
        '--memory-mib', '512', '--mechanical-loss', 'standard-v1'])
    started, cpu = time.perf_counter(), time.process_time()
    profile = cProfile.Profile() if args.profile else None
    if profile:
        profile.enable()
    code = point.run(limits)
    if profile:
        profile.disable()
    elapsed, cpu_s = time.perf_counter()-started, time.process_time()-cpu
    if code:
        raise RuntimeError('Point failed; preserve artifacts for diagnosis')
    manifest = json.loads((output/'manifest.json').read_text())
    if manifest['cycles_completed'] != 3 or manifest['failure']:
        raise RuntimeError('Diagnostic did not complete three cycles')
    report = dict(source_root=str(source), config_sha256=hashlib.sha256(args.config.read_bytes()).hexdigest(),
                  wall_s=elapsed, cpu_s=cpu_s, profiled=bool(profile),
                  cycles=3, status=manifest['status'],
                  source_files_sha256={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source.joinpath('motorsim').rglob('*.py')})
    if profile:
        profile.dump_stats(str(output/'cpu.prof'))
        stats = pstats.Stats(profile)
        report['profile_total_self_s'] = stats.total_tt
        report['functions'] = sorted([
            dict(file=f, line=l, name=n, calls=v[1], self_s=v[2], cumulative_s=v[3])
            for (f,l,n),v in stats.stats.items()], key=lambda x:x['self_s'], reverse=True)
    point.atomic(output/'benchmark.json', report)
    print(json.dumps({k:report[k] for k in ('wall_s','cpu_s','cycles','profiled')}))


if __name__ == '__main__':
    main()
