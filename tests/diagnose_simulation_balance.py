"""Diagnóstico fijo de la vuelta 30 de 0.5°, no otra serie ni checkpoint.

Ejecutar desde la raíz: python -m tests.diagnose_simulation_balance
Lee exclusivamente la evidencia de 5482160. No modifica el núcleo ni sus entradas.
"""
from dataclasses import replace
import csv
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch

from motorsim import simulation as sim
from motorsim.prototype import Monitor, environment, memory_mib, write_json

SOURCE = Path('results/simulacion-2t/viabilidad-20260915')
OUTPUT = Path('results/simulacion-2t/diagnostico-20260915')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.iterdir()) if p.is_file()}


def repetition(cycle):
    c = cycle['convergence']
    return (all(c.get(key, float('inf')) <= limit for key, limit in
                (('m_relative', .002), ('U_relative', .002), ('Y_absolute', .002),
                 ('W_relative', .005), ('p_curve_relative', .005))))


def inspect_existing():
    results, last, curves = [], [], []
    for step in (.5, .25, .125):
        recorded = read_json(SOURCE/f'step-{step:g}-summary.json')
        cycles = recorded['cycles']
        count = 0
        first_three = None
        for cycle in cycles:
            count = count+1 if cycle['cycle'] >= 5 and repetition(cycle) else 0
            if count >= 3 and first_three is None:
                first_three = cycle['cycle']
        c = cycles[-1]
        # Reconstrucción usando SOLO el CSV común, para contrastar con el auditor
        # original que realmente procesó todos los pasos aceptados.
        with (SOURCE/f'step-{step:g}-last-two.csv').open(encoding='utf-8') as stream:
            rows = [r for r in csv.DictReader(stream) if int(r['cycle']) == 30]
        snapshots, states = [], []
        for row in rows:
            snapshots.append((
                [tuple(float(row[f'{cv}_{k}']) for k in ('p_Pa', 'T_K', 'Y')) for cv in sim.CV],
                [float(row[f'{cv}_V_m3']) for cv in sim.CV],
                [tuple(float(row[f'link{j}_{k}']) for k in ('q_kg_s', 'H_W', 'F_kg_s')) for j in range(6)]))
            states.append([float(row[f'{cv}_{k}']) for cv in sim.CV for k in ('m_kg', 'U_J', 'F_kg')])
        ledger = [0.]*sim.SIZE
        for i in range(len(rows)-1):
            dt = (float(rows[i+1]['angle_deg'])-float(rows[i]['angle_deg']))/18000
            db = float(rows[i+1]['converted_kg'])-float(rows[i]['converted_kg'])
            inc = sim.independent_increment(snapshots[i], snapshots[i+1], dt, 800000*db, db)
            ledger = [a+b for a, b in zip(ledger, inc)]
        results.append(dict(step=step, first_three_repetitive_cycles_end=first_three,
            last_repetition=repetition(c), last_metrics=c['convergence'],
            balance_passed_cycles=sum(v['balances_passed'] for v in cycles),
            full_convergence=recorded['converged'], audit_every_accepted_step=c['independent'],
            audit_csv_half_degree=sim.audit(states[0], states[-1], ledger),
            csv_nodes=len(rows), csv_strictly_increasing=all(float(b['angle_deg']) > float(a['angle_deg'])
                                                           for a, b in zip(rows, rows[1:]))))
        last.append(c)
        curves.append([s[0][2][0] for s in snapshots])
    # Diagnóstico de diferencias aunque la precondición formal de convergencia falla.
    a, b, c = last
    def difference(x, y, cx, cy, pressure_scale):
        return dict(W_relative=abs(x['W_C_J']-y['W_C_J'])/max(abs(x['W_C_J']), abs(y['W_C_J']), 1),
            p_max_relative=abs(x['p_max_Pa']-y['p_max_Pa'])/pressure_scale,
            curve_relative=max(abs(p-q) for p, q in zip(cx, cy))/pressure_scale,
            Y_absolute=[abs(p-q) for p, q in zip(x['Y'], y['Y'])],
            links_relative=[abs(p-q)/max(abs(p), abs(q), 1e-7)
                            for p, q in zip(x['net_link_mass_kg'], y['net_link_mass_kg'])])
    sensitivity = dict(formal_passed=False, diagnostic_only=True,
        coarse=difference(a, b, curves[0], curves[1], b['p_max_Pa']),
        fine=difference(b, c, curves[1], curves[2], c['p_max_Pa']))
    return dict(resolutions=results, sensitivity=sensitivity)


def replay_cycle():
    baseline = read_json(SOURCE/'step-0.5-summary.json')['cycles']
    seed = baseline[28]['state']
    class RecordedStart(sim.Model):
        def __init__(self):
            super().__init__()
            self.case = replace(self.case, initial_angle_deg=10620.)
            self.latest = None

        def initial_state(self):
            return seed[:] + [0.]*(sim.SIZE-12)

        def evaluate(self, angle, y, heat=None):
            derivative, snapshot = super().evaluate(angle, y, heat)
            self.latest = dict(angle=angle, state=y.copy(), snapshot=snapshot)
            return derivative, snapshot

    model = RecordedStart()
    original_rk4, original_increment = sim.rk4, sim.independent_increment
    attempts, accepted = [], []
    current = None
    def traced_rk4(t, state, dt, rhs, project):
        nonlocal current
        current = dict(dt=dt, stages=[], rejected=False)
        attempts.append(current)
        def trace_rhs(t, y):
            derivative = rhs(t, y)
            current['stages'].append(model.latest)
            return derivative
        try:
            return original_rk4(t, state, dt, trace_rhs, project)
        except sim.InvalidStage:
            current['rejected'] = True
            raise

    def traced_increment(left, right, dt, q, b):
        inc = original_increment(left, right, dt, q, b)
        first, final = current['stages'][0], model.latest
        current['end'] = final
        current['independent'] = inc
        current['integrator'] = [a-z for a, z in zip(final['state'], first['state'])]
        assert dt == current['dt']
        assert left == first['snapshot'] and right == final['snapshot']
        accepted.append(current)
        return inc

    start = time.monotonic()
    budget = Monitor(.5, start)
    def one_cycle(cycle, angle, rhs_count, completed=False):
        budget(cycle, angle, rhs_count, completed)
        if completed:
            raise sim.StopCalculation('diagnóstico: una única vuelta reconstruida')
    with patch.object(sim, 'rk4', traced_rk4), patch.object(sim, 'independent_increment', traced_increment):
        result = sim.run_resolution(.5, one_cycle, model)
    if len(result['cycles']) != 1:
        raise RuntimeError(result['stop'])
    current_cycle = result['cycles'][0]
    assert current_cycle['state'] == baseline[29]['state'], 'Replay distinto de la trayectoria original'
    assert current_cycle['independent'] == baseline[29]['independent'], 'Auditoría no reproducida'
    bins = {}
    for record in accepted:
        phase = record['stages'][0]['angle']-10440
        lo = 180+30*int((phase-180)//30)
        key = f'{lo}-{lo+30}'
        bucket = bins.setdefault(key, dict(steps=0, dt=0., integrator=[0.]*sim.SIZE,
                                          independent=[0.]*sim.SIZE,
                                          start=record['stages'][0]['state'][:12]))
        bucket['steps'] += 1
        bucket['dt'] += record['dt']
        bucket['end'] = record['end']['state'][:12]
        for name in ('integrator', 'independent'):
            bucket[name] = [a+b for a, b in zip(bucket[name], record[name])]
    for bucket in bins.values():
        bucket['inventory_delta_m_U_F'] = [a-b for a, b in zip(bucket['end'], bucket['start'])]
        bucket['discrete_balance'] = sim.audit(bucket['start'], bucket['end'], bucket['integrator'])
        bucket['independent_balance'] = sim.audit(bucket['start'], bucket['end'], bucket['independent'])
        bucket['link_discrepancy_m_H_F'] = [
            [bucket['integrator'][12+3*j+k]-bucket['independent'][12+3*j+k] for k in range(3)]
            for j in range(6)]
    examples = []
    for record in accepted:
        angle = record['stages'][0]['angle']-10440
        if angle in (200., 300., 400., 500.):
            examples.append(record)
    continuous = all(a['end']['angle'] == b['stages'][0]['angle'] for a, b in zip(accepted, accepted[1:]))
    return dict(seconds=time.monotonic()-start, peak_MiB=memory_mib(),
        completed_cycles=1, same_final_state_and_audit_as_original=True,
        accepted_steps=len(accepted), rejected_attempts=sum(r['rejected'] for r in attempts),
        contiguous_steps=continuous, total_dt=sum(r['dt'] for r in accepted),
        nonuniform_steps=sum(abs(r['dt']*18000-.5) > 1e-9 for r in accepted),
        intervals=bins, stage_examples=examples, rhs=result['rhs_evaluations']), accepted


def inspect_closed_interval(accepted):
    """Solo 300–300.5°: mismo arranque, RK4 con uno o cuatro pasos.

    E está aislado del cilindro: p>=p_res, salida hacia equilibrio y Y constante
    son referencias analíticas. No se usa este ensayo como serie ni corrección.
    """
    record = next(r for r in accepted if r['stages'][0]['angle'] == 10740.)
    angle = 10740.
    initial = record['stages'][0]['state'][:12]+[0.]*(sim.SIZE-12)
    model = sim.Model()
    initial_snapshot = model.evaluate(angle, initial)[1]
    e0 = initial_snapshot[0][3]
    assert e0[0] > model.case.reservoirs_pty[1][0]
    assert model.geometry(angle)[2][4] == model.geometry(angle+.5)[2][4] == 0.
    results = []
    started = time.monotonic()
    budget = Monitor(.5, started)
    for parts in (1, 4):
        y = initial.copy()
        snapshot = initial_snapshot
        independent = [0.]*sim.SIZE
        stages = []
        for j in range(parts):
            budget(1, angle+j*.5/parts, len(stages))
            a, dt = angle+j*.5/parts, .5/parts/18000
            def rhs(t, stage):
                dy, snap = model.evaluate(a+t*18000, stage)
                stages.append(dict(angle=a+t*18000, E_p_T_Y=snap[0][3], flow=snap[2][5]))
                return dy
            y = sim.rk4(0., y, dt, rhs)
            next_snapshot = model.evaluate(a+.5/parts, y)[1]
            inc = sim.independent_increment(snapshot, next_snapshot, dt, 0., 0.)
            independent = [x+z for x, z in zip(independent, inc)]
            snapshot = next_snapshot
        if parts == 1:
            assert y[:12] == record['end']['state'][:12]
        results.append(dict(parts=parts, max_step_deg=.5/parts,
            E_initial_m_U_F=initial[9:12], E_final_m_U_F=y[9:12],
            E_delta_m_U_F=[v-u for v, u in zip(y[9:12], initial[9:12])],
            E_initial_p_T_Y=e0, E_final_p_T_Y=snapshot[0][3],
            E_Y_error=snapshot[0][3][2]-e0[2],
            link5_integrator_m_H_F=y[27:30], link5_independent_m_H_F=independent[27:30],
            stage_observations=stages, discrete=sim.audit(initial, y, y)['E'],
            independent=sim.audit(initial, y, independent)['E']))
    return dict(interval_deg=[300., 300.5], seconds=time.monotonic()-started,
                peak_MiB=memory_mib(), analytic_reference='E sin calor/trabajo ni conexión al cilindro: '
                'p desciende a 100000 Pa sin cruzar; Y_E se conserva en salida homogénea.',
                results=results, official_series=False, method_modified=False)


def inspect_trace(accepted):
    """Verifica el registro sin volver a integrar ni usar RK como otra auditoría."""
    max_weight_error = [0.]*3
    max_donor_error = [0., 0.]
    max_time_error = 0.
    wrong_signs = 0
    for record in accepted:
        a = record['stages'][0]['angle']
        h = record['dt']*18000
        expected_times = (a, a+h/2, a+h/2, a+h)
        max_time_error = max(max_time_error, abs(record['end']['angle']-a-h),
                            *(abs(s['angle']-t) for s, t in zip(record['stages'], expected_times)))
        for j in range(6):
            for k in range(3):
                values = [s['snapshot'][2][j][k] for s in record['stages']]
                weighted = record['dt']*(values[0]+2*values[1]+2*values[2]+values[3])/6
                max_weight_error[k] = max(max_weight_error[k], abs(weighted-record['integrator'][12+3*j+k]))
        for s in record['stages']+[record['end']]:
            nodes, volumes, flows = s['snapshot']
            ends = (((100000., 300., 1.), nodes[0]), (nodes[0], nodes[1]),
                    (nodes[1], nodes[2]), (nodes[1], nodes[2]),
                    (nodes[2], nodes[3]), (nodes[3], (100000., 500., 0.)))
            for (left, right), (q, enthalpy, fresh) in zip(ends, flows):
                if q:
                    wrong_signs += int((q > 0) != (left[0] > right[0]))
                    donor = left if q > 0 else right
                    max_donor_error[0] = max(max_donor_error[0], abs(enthalpy/q-1107*donor[1])/(1107*donor[1]))
                    max_donor_error[1] = max(max_donor_error[1], abs(fresh/q-donor[2]))
                else:
                    assert enthalpy == fresh == 0.
    return dict(max_RK_weight_difference_kg_J_kg=max_weight_error,
        max_stage_time_difference_deg=max_time_error, wrong_flow_signs=wrong_signs,
        max_donor_h_relative_and_Y_absolute=max_donor_error,
        description='Comprobación de implementación de pesos/signos/tiempos; '
                    'NO es la auditoría independiente de conservación.')


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    before = hashes()
    existing = inspect_existing()
    replay, accepted = replay_cycle()
    write_json(OUTPUT/'closed-interval.json', inspect_closed_interval(accepted))
    write_json(OUTPUT/'trace-checks.json', inspect_trace(accepted))
    write_json(OUTPUT/'accepted-steps.json', accepted)
    after = hashes()
    assert before == after, 'Cambió evidencia original'
    write_json(OUTPUT/'diagnosis.json', dict(source=str(SOURCE), source_sha256=before,
        original_files_unchanged=True, environment=environment(), existing=existing, replay=replay))
    print(json.dumps({k: v for k, v in replay.items() if k not in ('intervals', 'stage_examples')}, indent=2))


if __name__ == '__main__':
    main()
