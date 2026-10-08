"""Reevaluate preserved solutions with the precommitted P1-R2 observable."""
import argparse
import gzip
import json
from pathlib import Path
from motorsim.gas1d.contact import density_contact
from .p2_campaign import invariants, sha, write, ROOT


def study(run_dir):
    source = ROOT/'results/p1-r1-contacto-20260917'
    checks = invariants()
    checks['input_inventory'] = all(sha(source/p)==h for p,h in json.loads((source/'artifacts/closure-inventory.json').read_text()).items())
    old = json.loads((source/'artifacts/study.json').read_text())
    checks['original_gas1d_unchanged'] = all(sha(ROOT/p)==h for p,h in old['gas1d_sha256'].items())
    if not all(checks.values()):
        raise ValueError('Preservation preconditions failed')
    rows = []
    for previous in old['rows']:
        rel = f"artifacts/cases/{previous['case']}-{previous['N']}.json.gz"
        raw = json.loads(gzip.decompress((source/rel).read_bytes()))
        hydro = [w[:3] for w in raw['result']['primitive']]
        found = density_contact(raw['mesh']['centers'], hydro, raw['configuration']['gamma'])
        position = found['position']
        error = None if position is None else abs(position-previous['exact'])
        # The reference is consumed only after detection, for error reporting.
        row = dict(previous, detector=found, detected=position, error_abs=error,
                   D_error_dx=None if error is None else error/previous['dx'],
                   source_file=(source/rel).relative_to(ROOT).as_posix(), source_sha256=sha(source/rel))
        rows.append(row)
        print(previous['case'], previous['N'], found['status'], row['D_error_dx'], flush=True)
    checks['unique'] = all(r['detector']['status']=='UNIQUE' for r in rows)
    checks['accuracy'] = all(r['D_error_dx'] is not None and r['D_error_dx']<=2 for r in rows)
    checks['convergence'] = checks['unique'] and all(all(a>=b for a,b in zip(errors,errors[1:])) for errors in
        [[r['error_abs'] for r in rows if r['case']==kind] for kind in ('sod','pure_contact')])
    state = 'P1_R2_PASS_CONTACT_OBSERVABLE' if all(checks.values()) else 'P1_R2_CONTACT_ACCURACY_UNRESOLVED'
    summary = dict(stage='P1_R2',state=state,review_required=True,checks=checks,rows=rows,
                   detector_sha256=sha(ROOT/'motorsim/gas1d/contact.py'),
                   note='Precommitted detector. Reused unchanged arrays, no new integration; review needed before adoption.')
    art=run_dir/'artifacts';write(art/'study.json',summary)
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason=state) for k,v in checks.items()],
                                metrics=dict(cases=len(rows)),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    study(p.parse_args().run_dir)
