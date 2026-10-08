"""Two explicitly authorized integrations; evidence acquisition, not R5 adoption."""
import argparse
import gzip
import json
from pathlib import Path

from .p2b_campaign import run_case, frozen_checks
from .p2b_resume import source_hashes, signature, expected_signature, write
from .p2_campaign import sha


def acquire(run_dir):
    art = Path(run_dir) / 'artifacts'
    (art / 'cases').mkdir(parents=True, exist_ok=False)
    before = source_hashes()
    checks = frozen_checks()
    if not all(checks.values()):
        raise ValueError('Frozen baseline check failed: ' + str(checks))
    records = {}
    for name, n in (('T10_800', None), ('T03_0.2', 1600)):
        print(f'START {name} N={n} timeout=600 evidence only', flush=True)
        record = run_case(name, n=n, wall_limit=600.)
        assert signature(record) == expected_signature(name, n)
        assert source_hashes() == before
        target = art / 'cases' / (record['name'] + '.json.gz')
        target.write_bytes(gzip.compress(json.dumps(record, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        records[record['name']] = dict(path=target.relative_to(Path(run_dir)).as_posix(), sha256=sha(target),
            input_sha256=signature(record), status=record['result']['status'], runtime=record['result']['wall_seconds'],
            role='T10_CONTRACTUAL' if name.startswith('T10') else 'R5_DIAGNOSTIC_EVIDENCE')
        write(art / 'acquisition.json', dict(previous_timeout=300, new_timeout=600,
            reason='infrastructure/runtime completion', source_sha256=before, cases=records,
            R5_adopted=False, P2_accepted=False))
        print('END ' + record['name'] + ' ' + record['result']['status'] + ' ' + str(record['result']['wall_seconds']), flush=True)
    checks.update(frozen_checks())
    checks['solver_unchanged'] = before == source_hashes()
    checks['evidence_complete'] = all(r['status'] == 'completed' for r in records.values())
    write(art / 'result.json', dict(checks=[dict(id=k, passed=v, kind='numerical', reason='Evidence acquisition only, not contract adoption') for k,v in checks.items()],
        metrics=dict(new_integrations=len(records)), scientific_change_required=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    acquire(parser.parse_args().run_dir)
