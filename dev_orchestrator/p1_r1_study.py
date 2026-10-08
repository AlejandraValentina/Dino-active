"""P1_R1_SCIENTIFIC_AMENDMENT: observational study; never changes the solver."""
import argparse
import gzip
import json
from math import fsum, isfinite
from pathlib import Path

from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.reference import cell_integrals, primitives
from motorsim.gas1d.solver import solve
from motorsim.gas1d.verification import definition, fields_errors
from .p2_campaign import invariants, sha, write, ROOT


def half_crossing(xs, ys):
    """No exact solution argument, clipping, tolerance, or best-crossing choice."""
    if len(xs) != len(ys) or len(xs) < 2 or not all(isfinite(v) for v in (*xs, *ys)):
        raise ValueError('Invalid profile')
    if any(b <= a for a, b in zip(xs, xs[1:])):
        raise ValueError('Unordered centers')
    if any(a == b == .5 for a, b in zip(ys, ys[1:])):
        return None, 'plateau_at_half'
    found = [x for x, y in zip(xs, ys) if y == .5]
    found += [x + (.5-y)*(xx-x)/(yy-y)
              for x, xx, y, yy in zip(xs, xs[1:], ys, ys[1:])
              if (y-.5)*(yy-.5) < 0]
    return (found[0], 'unique') if len(found) == 1 else (None, f'crossings={len(found)}')


def estimators(xs, ws, exact):
    """A unchanged; B blind; C/D fixed +/- .05 around B, diagnostic only.

    D uses density gradients, but shares B's support window: field-independent,
    NOT an independently localized contact. The window excludes the Sod shock.
    """
    ys = [w[3] for w in ws]
    faces = [(a+b)/2 for a, b in zip(xs, xs[1:])]
    dy = [abs(b-a)/(xx-x) for x, xx, a, b in zip(xs, xs[1:], ys, ys[1:])]
    legacy = [i for i, x in enumerate(faces) if abs(x-exact) <= .05]
    a = faces[max(legacy, key=lambda i: dy[i])]
    b, uniqueness = half_crossing(xs, ys)
    c = d = None
    monotone = False
    if b is not None:
        local = [i for i, x in enumerate(faces) if abs(x-b) <= .05]
        weights = [abs(ys[i+1]-ys[i]) for i in local]
        c = fsum(faces[i]*w for i, w in zip(local, weights))/fsum(weights)
        drho = [abs(ws[i+1][0]-ws[i][0])/(xs[i+1]-xs[i]) for i in local]
        d = faces[local[max(range(len(local)), key=lambda j: drho[j])]]
        # Both selected cases are descending Y contacts. No numerical tolerance.
        monotone = all(ys[i+1] <= ys[i] for i in local)
    return dict(A=a, B=b, C=c, D=d, unique_crossing=uniqueness,
                local_monotone=monotone, diagnostic_half_window=.05)


def run_study(run_dir):
    art = run_dir/'artifacts'
    (art/'cases').mkdir()
    checks = invariants()
    if not all(checks.values()):
        raise ValueError(f'Precondition failure {checks}')
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'motorsim/gas1d').glob('*.py')}
    rows = []
    for kind in ('sod', 'pure_contact'):
        for n in (200, 400, 800, 1600):
            case = definition('T02_sod')
            mesh = case['mesh'] = uniform_mesh(n, area=1.)
            if kind == 'pure_contact':
                # Independent translating contact; fixed a priori, no acoustic waves.
                left, right = (1., 1., 1., 1.), (2., 1., 1., 0.)
                case.update(initial=lambda x: left if x < .25 else right,
                            reference=lambda x: left if x < .5 else right,
                            breaks=[.25], refbreaks=[.5], end=.25,
                            bc=(Boundary('fixed', state=left), Boundary('fixed', state=right)))
            exact = .5 if kind == 'pure_contact' else .5+case['exact'].ustar*case['end']
            initial = cell_integrals(mesh, case['initial'], case['eos'], case['area'], case['breaks'])
            reference = cell_integrals(mesh, case['reference'], case['eos'], case['area'], case['refbreaks'])
            print(f'START {kind} N={n}', flush=True)
            result = solve(mesh, initial, case['end'], case['bc'], eos=case['eos'], cfl=.4, wall_limit=180.)
            if result['status'] != 'completed':
                write(art/'failed-case.json', result)
                raise RuntimeError(f'{kind} {n}: {result["status"]}: {result["reason"]}')
            estimates = estimators(mesh.centers, result['primitive'], exact)
            errors = fields_errors(result['primitive'], primitives(mesh, reference, case['eos']), mesh, (1., 1., 1., 1.))
            row = dict(case=kind, N=n, dx=1/n, exact=exact, estimators=estimates,
                       absolute_error={k: abs(estimates[k]-exact) if estimates[k] is not None else None for k in 'ABCD'},
                       error_dx={k: abs(estimates[k]-exact)*n if estimates[k] is not None else None for k in 'ABCD'},
                       errors=errors, worst_ledger=max(max(s['normalized']) for s in result['ledger']),
                       hlle=result['hlle_fallback_count'], wall_seconds=result['wall_seconds'],
                       steps=result['steps'], max_CFL=result['max_CFL'], extrema=result['extrema'])
            record = dict(summary=row, mesh=mesh.as_dict(), initial=initial, reference=reference, result=result,
                          configuration=dict(CFL=.4, R=case['eos'].R, gamma=case['eos'].gamma, final_time=case['end'],
                                             boundaries=[b.__dict__ for b in case['bc']], method='FIRST_ORDER_HLLC_FE'))
            target = art/'cases'/f'{kind}-{n}.json.gz'
            target.write_bytes(gzip.compress(json.dumps(record, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
            rows.append(row)
            write(art/'checkpoint.json', dict(rows=rows))
            print(f'END {kind} N={n} B_error_dx={row["error_dx"]["B"]} wall={row["wall_seconds"]}', flush=True)
    checks.update(invariants())
    checks['gas1d_unchanged'] = all(sha(ROOT/p) == h for p, h in sources.items())
    checks['complete_study'] = len(rows) == 8
    checks['unique_monotone'] = all(r['estimators']['unique_crossing'] == 'unique' and r['estimators']['local_monotone'] for r in rows)
    checks['B_converges'] = all(all(a > b for a, b in zip(errs, errs[1:])) for errs in
                              [[r['absolute_error']['B'] for r in rows if r['case'] == kind] for kind in ('sod', 'pure_contact')])
    contractual = next(r for r in rows if r['case'] == 'sod' and r['N'] == 400)
    checks['contact_accuracy'] = contractual['error_dx']['B'] <= 2
    state = 'P1_R1_PASS' if all(checks.values()) else 'P1_R1_CONTACT_ACCURACY_UNRESOLVED'
    summary = dict(stage='P1_R1_SCIENTIFIC_AMENDMENT', state=state, checks=checks, rows=rows,
                   gas1d_sha256=sources, scientific_diff=[], contract='1D_CONTRACT_V1_UNCHANGED',
                   note='No R1 adopted; P2 stays gated. Raw HLLE counters retained; HLLC counters not certified.')
    write(art/'study.json', summary)
    write(art/'result.json', dict(checks=[dict(id=k, passed=v, kind='numerical', reason=state) for k, v in checks.items()],
                                metrics=dict(cases=len(rows)), scientific_change_required=False))
    write(art/'inventory.json', {p.relative_to(run_dir).as_posix(): sha(p) for p in art.rglob('*') if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    run_study(parser.parse_args().run_dir)
