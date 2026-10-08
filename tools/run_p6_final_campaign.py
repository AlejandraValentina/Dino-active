"""Bounded, reproducible P6 physical campaign and independent ledgers."""
import json
from pathlib import Path
from math import fsum

from motorsim.p5c import make_p5c_fixture, make_p5c_full_fixture
from motorsim.p6_species import P6IntegratedSystem, SPECIES


def set_mixtures(system):
    system.species['crankcase'][0] = (.55, .05, .25, .15)
    system.species['cylinder'][0] = (.20, .20, .30, .30)
    for name, values in {
        'intake': [(.70, .10, .10, .10), (.60, .10, .20, .10), (.50, .20, .20, .10)],
        'tr1': [(.70, .20, .05, .05), (.40, .30, .20, .10), (.20, .20, .30, .30)],
        'tr2': [(.10, .30, .20, .40), (.20, .20, .30, .30), (.30, .10, .20, .40)],
        'exhaust': [(.10, .10, .30, .50), (.20, .10, .20, .50), (.30, .10, .20, .40)],
    }.items():
        for cell, value in zip(system.species[name], values[:len(system.species[name])]):
            cell[:] if False else None
            # Compatibility view is intentionally used only at initialization;
            # step() migrates it once into authoritative species_mass.
            system.species[name][system.species[name].index(cell)] = value


def run_case(factory, angles, *, cells=3, configure=None):
    system = P6IntegratedSystem(factory(cells=cells), capture_trace=True)
    if configure:
        configure(system)
    set_mixtures(system)
    system._sync_manual_views()
    rows = []
    for angle in angles:
        before = system.inventory_snapshot()['global']
        trace_start = len(system.external_flux_trace)
        result = system.step(1e-7, angle=angle)
        after = system.inventory_snapshot()['global']
        external = [0.0] * 4
        for trace in system.external_flux_trace[trace_start:]:
            incoming = trace['atmosphere_intake']['species_flux']
            outgoing = trace['exhaust_atmosphere']['species_flux']
            for i, name in enumerate(SPECIES):
                external[i] += 0.5e-7 * (incoming[name] - outgoing[name])
        measured = tuple(after[name + '_mass'] - before[name + '_mass'] for name in SPECIES)
        rows.append({'before': before, 'after': after,
                     'measured': measured, 'external': tuple(external),
                     'residual': tuple(a-b for a,b in zip(measured, external)),
                     'result': result})
    return system, rows


def summarize(rows):
    initial = rows[0]['before']; final = rows[-1]['after']
    ext = tuple(fsum(row['external'][i] for row in rows) for i in range(4))
    measured = tuple(final[name + '_mass'] - initial[name + '_mass'] for name in SPECIES)
    residual = tuple(a-b for a,b in zip(measured, ext))
    worst = max((abs(x) for row in rows for x in row['residual']), default=0.0)
    return {'initial': initial, 'final': final, 'external': ext,
            'measured_change': measured, 'cumulative_residual': residual,
            'worst_per_step_residual': worst}


def transport_counters(system):
    tr1 = tr2 = short = 0.0
    for stage in system.verification_trace:
        for item in stage['interfaces']:
            value = item['gas_mass_flux'] * sum(
                item['donor_species_fractions'][name] for name in ('fresh_air', 'fuel'))
            if item['interface_name'] == 'tr1<->cylinder' and value > 0:
                tr1 += 0.5e-7 * value
            if item['interface_name'] == 'tr2<->cylinder' and value > 0:
                tr2 += 0.5e-7 * value
            if item['interface_name'] == 'cylinder<->exhaust' and value > 0:
                short += 0.5e-7 * value
    return {'fresh_delivery_TR1_trace': tr1, 'fresh_delivery_TR2_trace': tr2,
            'fresh_delivery_total_trace': tr1 + tr2,
            'fresh_delivery_TR1_counter': system.fresh_delivered_tr1,
            'fresh_delivery_TR2_counter': system.fresh_delivered_tr2,
            'fresh_delivery_total_counter': system.fresh_delivered,
            'short_circuit_trace': short,
            'short_circuit_counter': system.fresh_short_circuit}


def main():
    def f05_configure(system):
        system.gas.core.cylinder.primitive = (1.0, 0.0, 90000.0, 0.2)
    f05_system, f05_rows = run_case(lambda **kw: make_p5c_fixture(port_area=0.0, **kw),
                                    [150.0, 150.01, 150.02], cells=3,
                                    configure=f05_configure)
    # Forward and reverse exhaust are separate physical initializations.
    def f06_configure(system):
        system.gas.core.cylinder.primitive = (1.0, 0.0, 140000.0, 0.2)
    f06_system, f06_rows = run_case(lambda **kw: make_p5c_fixture(port_area=1e-4, **kw),
                                    [0.0, 0.01], cells=3, configure=f06_configure)
    def reverse_configure(system):
        system.gas.core.cylinder.primitive = (1.0, 0.0, 90000.0, 0.2)
        for cell in system.gas.exhaust.cells:
            cell.conservative = system.gas.eos.conservative((1.0, 0.0, 140000.0, 0.8))
    f06_reverse_system, f06_reverse_rows = run_case(
        lambda **kw: make_p5c_fixture(port_area=1e-4, **kw), [0.0, 0.01],
        cells=3, configure=reverse_configure)
    f07_system, f07_rows = run_case(make_p5c_full_fixture,
                                    [300.0, 150.0, 150.01, 300.01, 150.02], cells=3)
    f07 = summarize(f07_rows)
    local = []
    for component, data in f07_system.inventory_snapshot()['components'].items():
        for index, cell in enumerate(data['cells']):
            local.append((abs(cell['species_sum_minus_gas_mass']), component, index))
    worst_local = max(local, default=(0.0, None, None))
    output = {
        'f05': {'summary': summarize(f05_rows),
                'trace': f05_system.verification_trace,
                'counters': transport_counters(f05_system)},
        'f06': {'summary': summarize(f06_rows),
                'trace': f06_system.verification_trace,
                'counters': transport_counters(f06_system),
                'reverse': {'trace': f06_reverse_system.verification_trace,
                            'summary': summarize(f06_reverse_rows),
                            'counters': transport_counters(f06_reverse_system)}},
        'f07': {'summary': f07,
                'external_trace': f07_system.external_flux_trace,
                'worst_local_species_sum_error': worst_local[0],
                'worst_local_species_sum_location': [worst_local[1], worst_local[2]],
                'gas_mass_initial': f07['initial']['gas_mass'],
                'gas_mass_final': f07['final']['gas_mass'],
                'gas_mass_residual': (f07['final']['gas_mass'] - f07['initial']['gas_mass']
                                      - sum(sum(row['external']) for row in f07_rows))},
        'tests': 'campaign executed by repository Python',
    }
    out = Path('results/p6-species-20260925/final-campaign.json')
    out.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'f07': f07}, indent=2))


if __name__ == '__main__':
    main()
