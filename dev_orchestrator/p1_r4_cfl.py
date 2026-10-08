"""Read-only numerical study of T11; imports the frozen first-order solver."""
import argparse
import copy
import gzip
import json
import math
import time
from pathlib import Path

from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.reference import cell_integrals, primitives
from motorsim.gas1d.solver import solve
from motorsim.gas1d.verification import definition, measure, A0, P0
from .p2_campaign import ROOT, invariants, write, sha


AMPLITUDE = 1e-4 * P0
FROZEN = ROOT / 'results/p1-r4-cfl-20260918/frozen-inputs.json'
HISTORICAL = ROOT / 'results/p1-r3-fronteras-20260918/p2a-attempt-2/artifacts/cases'


def differences(a, b):
    absolute = abs(a - b)
    return dict(absolute_Pa=absolute, normalized=absolute / AMPLITUDE)


def numerical_result(result):
    """Only wall clock time is nondeterministic; do not discard numerical fields."""
    result = copy.deepcopy(result)
    result.pop('wall_seconds')
    return result


def frozen_checks():
    expected = json.loads(FROZEN.read_text(encoding='utf-8'))
    checks = invariants()
    checks['implementation_contracts_frozen'] = all(sha(ROOT / p) == h for p, h in expected.items())
    return checks


def study(run_dir):
    started = time.monotonic()
    art = run_dir / 'artifacts'
    (art / 'cases').mkdir()
    checks = frozen_checks()
    if not all(checks.values()):
        raise ValueError('Frozen input mismatch')
    # Contractual reproduction first, also used as the N800 study row.
    plan = [(800, c) for c in (.2, .4, .6)]
    plan += [(400, c) for c in (.1, .2, .4, .6)] + [(800, .1)]
    plan += [(1600, c) for c in (.1, .2, .4, .6)]
    rows = []
    for n, cfl in plan:
        if time.monotonic() - started > 900:
            raise TimeoutError('Total study budget exhausted, no retry')
        name = f'T03_{cfl}'
        case = definition(name)
        case['mesh'] = uniform_mesh(n)
        mesh, eos = case['mesh'], case['eos']
        initial = cell_integrals(mesh, case['initial'], eos, case['area'], case['breaks'])
        reference = cell_integrals(mesh, case['reference'], eos, case['area'], case['refbreaks'])
        print(f'START N={n} CFL={cfl}', flush=True)
        result = solve(mesh, initial, case['end'], case['bc'], eos=eos, cfl=cfl,
                       sensor=case['sensor'], sample_interval=case['interval'],
                       wall_limit=min(320., 900 - (time.monotonic() - started)),
                       progress=lambda step, t: print(f'PROGRESS N={n} CFL={cfl} step={step} t={t:.9g}', flush=True) if step % 2000 == 0 else None)
        metrics, parent_checks = measure(case, result, reference, initial)
        ext = result['extrema']
        stable = (result['status'] == 'completed' and metrics['worst_ledger'] <= 1e-10
                  and all(math.isfinite(v) for v in ext.values())
                  and min(ext[k] for k in ('min_rho', 'min_p', 'min_T')) > 0
                  and 0 <= ext['min_Y'] <= ext['max_Y'] <= 1)
        deterministic = None
        historical_sha = None
        if n == 800 and cfl in (.2, .4, .6):
            old_path = HISTORICAL / f'{name}.json.gz'
            old = json.loads(gzip.decompress(old_path.read_bytes()))
            historical_sha = sha(old_path)
            # JSON round trip normalizes tuple/list representations, not numbers.
            deterministic = (json.loads(json.dumps(numerical_result(result))) == numerical_result(old['result'])
                             and json.loads(json.dumps(initial)) == old['initial']
                             and json.loads(json.dumps(reference)) == old['reference']
                             and metrics == old['metrics'] and parent_checks == old['checks'])
        amplitude = metrics.get('amplitude')
        ref_amplitude = max(w[2] - P0 for w in primitives(mesh, reference, eos))
        modified_equation = AMPLITUDE / math.sqrt(1 + 2 * A0 * mesh.widths[0] * (1-cfl) * case['end'] / .04**2)
        row = dict(N=n, dx=1/n, CFL=cfl, amplitude_Pa=amplitude,
                   analytical_discrete_amplitude_Pa=ref_amplitude,
                   modified_equation_prediction_Pa=modified_equation,
                   analytical_amplitude_error=abs(amplitude-ref_amplitude)/AMPLITUDE if amplitude is not None else None,
                   stability=stable, parent_checks=parent_checks, parent_metrics=metrics,
                   deterministic=deterministic, historical_sha256=historical_sha,
                   steps=result['steps'], dt_min=result['minimum_dt'],
                   dt_max=max((s['dt'] for s in result['ledger']), default=None),
                   max_CFL=result['max_CFL'], minima=ext, rejected_steps=result['rejected_steps'],
                   worst_residual_components=[max((s['normalized'][k] for s in result['ledger']), default=0.) for k in range(4)],
                   hllc_flux_count=result['hllc_flux_count'], hlle_fallback_count=result['hlle_fallback_count'],
                   characteristic_flux_count=result['characteristic_flux_count'],
                   runtime=result['wall_seconds'], status=result['status'], reason=result['reason'])
        record = dict(row=row, mesh=mesh.as_dict(), initial=initial, reference=reference,
                      result=result, configuration=dict(N=n,CFL=cfl,final_time=case['end'],
                      boundaries=[b.__dict__ for b in case['bc']],R=eos.R,gamma=eos.gamma))
        target = art / 'cases' / f'T03-N{n}-C{cfl}.json.gz'
        target.write_bytes(gzip.compress(json.dumps(record,allow_nan=False,separators=(',',':')).encode(),mtime=0))
        rows.append(row)
        write(art/'checkpoint.json', dict(rows=rows))
        print(f'END N={n} CFL={cfl} {result["status"]} A={amplitude} stable={stable} deterministic={deterministic}', flush=True)
        if result['status'] != 'completed':
            break
    comparisons = []
    for n in (400,800,1600):
        values = {r['CFL']:r['amplitude_Pa'] for r in rows if r['N']==n and r['amplitude_Pa'] is not None}
        for a,b in ((.2,.4),(.4,.6),(.2,.6),(.1,.2),(.1,.4),(.1,.6)):
            if a in values and b in values:
                comparisons.append(dict(N=n,CFL_a=a,CFL_b=b,**differences(values[a],values[b])))
    checks.update(frozen_checks())
    checks['complete_matrix'] = len(rows)==12 and all(r['status']=='completed' for r in rows)
    checks['deterministic_reproduction'] = len([r for r in rows if r['deterministic'] is True])==3
    checks['stability_conservation'] = all(r['stability'] for r in rows)
    summary = dict(state='STUDY_READY_FOR_INDEPENDENT_REVIEW' if all(checks.values()) else 'STUDY_BLOCKED',
                   rows=rows,comparisons=comparisons,checks=checks,wall_seconds=time.monotonic()-started,
                   frozen_manifest_sha256=sha(FROZEN),note='No revised threshold or P2A approval. Parent checks at N400 diagnostic only. CFL0.1 not exact Euler.')
    write(art/'study.json',summary)
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason='Frozen study, no revised scientific gate') for k,v in checks.items()],
                               metrics=dict(cases=len(rows)),scientific_change_required=False))
    write(art/'inventory.json',{p.relative_to(run_dir).as_posix():sha(p) for p in art.rglob('*') if p.is_file() and p.name!='inventory.json'})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    study(parser.parse_args().run_dir)
