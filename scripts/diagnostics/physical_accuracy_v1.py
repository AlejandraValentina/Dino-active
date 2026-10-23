"""Offline reduction of existing periodic evidence; never advances the solver."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sampled_pdv(samples, native):
    """Approximate decomposition from persisted 0.5-degree diagnostic samples."""
    g = native['slider_crank']['crankcase']
    r, rod = g['stroke_mm']/2, g['rod_length_mm']
    area = math.pi*g['bore_mm']**2/4*1e-9  # mm^3 to m^3
    def volume_part(a):
        t = math.radians(a % 360)
        return area*(r*(1-math.cos(t))+rod-math.sqrt(rod**2-r**2*math.sin(t)**2))
    total = opened = 0.
    for a,b in zip(samples,samples[1:]):
        work = .5*(a['pressures_Pa']['cylinder']+b['pressures_Pa']['cylinder'])*(volume_part(b['angle_deg'])-volume_part(a['angle_deg']))
        total += work
        if a['areas_m2']['exhaust']>0 or b['areas_m2']['exhaust']>0:
            opened += work
    return {'total_J':total,'exhaust_open_J':opened,'exhaust_closed_J':total-opened,
            'qualification':'Approximate sampled pdV partition; open-port work is not all irreversible pumping loss, and negative compression work is not a loss estimate.'}


def reduce_cycle(summary, native):
    s = summary
    m = s['mechanical_estimate']
    f = s['flow_integrals']
    species = s['closure_snapshots']['exhaust']['cylinder_species_kg']
    fuel = native['fuel_coupled_combustion']['fuel_snapshot']
    reference_air = native['atmosphere'][0] * m['displacement_m3'] / (
        native['eos']['R'] * native['atmosphere'][1])
    gross = f['intake.left.air.out_positive_kg']
    reverse = f['intake.left.air.out_negative_kg']
    transfer_air = sum(f[x+'.right.air.out_positive_kg'] for x in ('primary','secondary','boost'))
    transfer_fuel = sum(f[x+'.right.fuel.out_positive_kg'] for x in ('primary','secondary','boost'))
    cylinder_heat = sum(v for k,v in s['thermal_heat_by_surface_J'].items()
                        if k in ('cylinder-wall','cylinder-head','piston-crown'))
    ledger = s['ledger_delta']
    end_energy = math.fsum(c['total_energy_J'] for c in s['observables']['chambers'].values())
    end_energy += math.fsum(c['total_energy_J'] for cells in s['observables']['ducts'].values() for c in cells)
    delta_u = end_energy - s['observables']['cycle_start_total_energy_J']
    expected_delta = (s['chemical_heat_J'] + ledger['external_energy_J']
                      + ledger['cylinder_work_J'] + ledger['crankcase_work_J']
                      - ledger['heat_to_wall_J'])
    return {
        'cycle':s['cycle'], 'imep_bar':s['imep_Pa']/1e5,
        'net_piston_mep_bar':m['net_piston_mep_pa']/1e5,
        'bmep_bar':m['brake_mep_pa']/1e5, 'HP':m['brake_power_w']/745.6998715822702,
        'torque_Nm':m['brake_torque_nm'], 'brake_W':m['brake_power_w'],
        'cylinder_work_J':s['cylinder_work_J'], 'crankcase_work_J':s['crankcase_work_J'],
        'friction_work_J':sum(m['loss_work_j_by_term'].values()),
        'friction_W':m['mechanical_loss_power_w'], 'fixed_trajectory_zero_friction_HP':m['net_piston_power_w']/745.6998715822702,
        'reference_dry_air_mg':reference_air*1e6,
        'gross_intake_air_mg':gross*1e6, 'reverse_intake_air_mg':reverse*1e6,
        'net_intake_air_mg':(gross-reverse)*1e6,
        'dry_air_delivery_ratio_gross':gross/reference_air,
        'dry_air_delivery_ratio_net':(gross-reverse)/reference_air,
        'charging_efficiency_dry_air':species[0]/reference_air,
        'transfer_gross_air_mg':transfer_air*1e6,
        'trapped_over_transfer_gross_air_ratio':species[0]/transfer_air,
        'trapped_over_net_intake_air_ratio':species[0]/(gross-reverse),
        'trapping_ratio_qualification':'Inventory/flux ratio at periodic operation, not tagged parcel trapping efficiency; trapped inventory includes previous-cycle fresh material.',
        'trapped_air_mg':species[0]*1e6, 'trapped_fuel_mg':species[1]*1e6,
        'burned_residual_fraction':(species[2]+species[3])/sum(species),
        'afr_supplied':s['afr_supplied'], 'afr_trapped':s['afr_trapped'],
        'afr_transfer_gross':transfer_air/transfer_fuel,
        'stoichiometric_afr':fuel['stoichiometric_afr'],
        'fuel_burned_mg':s['fuel_burned_kg']*1e6,
        'burned_over_trapped_fuel_fraction':s['fuel_burned_kg']/species[1],
        'oxygen_limited_fuel_mg':species[0]/fuel['stoichiometric_afr']*1e6,
        'fuel_gross_supplied_mg':f['intake.left.fuel.out_positive_kg']*1e6,
        'fuel_net_supplied_mg':(f['intake.left.fuel.out_positive_kg']-f['intake.left.fuel.out_negative_kg'])*1e6,
        'air_cylinder_exhaust_mg':f['exhaust.left.air.out_positive_kg']*1e6,
        'fuel_cylinder_exhaust_mg':f['exhaust.left.fuel.out_positive_kg']*1e6,
        'heat_released_J':s['chemical_heat_J'],
        'burned_fuel_LHV_J':s['fuel_burned_kg']*fuel['lower_heating_value_j_kg'],
        'cylinder_wall_heat_J':cylinder_heat,
        'total_wall_heat_J':ledger['heat_to_wall_J'],
        'external_energy_net_J':ledger['external_energy_J'],
        'system_delta_U_J':delta_u, 'energy_balance_residual_J':delta_u-expected_delta,
        'conservation_relative':s['conservation']['relative'],
        'pressure_min_max_Pa':s['pressure_min_max_Pa'],
        'ledger_fresh_delivered_mix_mg':ledger['fresh_delivered_kg']*1e6,
        'ledger_overlap_short_circuit_mix_mg':ledger['fresh_short_circuit_kg']*1e6,
        'thermal_model':native['thermal_system']['correlation'],
        'independent_audit':s['conservation']['independent_audit'],
    }


def analyze(receipt_path):
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    verified = {}
    for module, expected in receipt['source_hashes'].items():
        path = Path(*module.split('.')).with_suffix('.py')
        # The historical comparison receipt records UTF-8 text with LF endings.
        normalized = hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
        if normalized != expected:
            raise ValueError('Scientific source hash mismatch: '+str(path))
        verified[str(path)] = {'historical_utf8_lf_sha256':expected,'raw_sha256':sha(path)}
    rows = []
    for p in receipt['points']:
        result = Path(p['result'])
        manifest = result.parent/'invocation-002'/'manifest.json'
        checkpoint = manifest.parent/f"checkpoint-next-{p['next_cycle']:03d}.json"
        for path, expected in [(result,p['result_sha256']), (manifest,p['manifest_sha256']),
                               (checkpoint,p['checkpoint_sha256'])]:
            if sha(path) != expected:
                raise ValueError('Historical artifact hash mismatch: '+str(path))
            verified[str(path)] = expected
        diag = manifest.parent/f"cycle-{p['cycles']:03d}-diagnostics.json"
        native = result.parent/'native-configuration.json'
        persisted = json.loads(manifest.read_text())
        if sha(diag) != persisted['cycles'][-1]['diagnostic_artifact_sha256']:
            raise ValueError('Historical diagnostic hash mismatch: '+str(diag))
        diagnostic = json.loads(diag.read_text())
        configuration = json.loads(native.read_text())
        row = reduce_cycle(diagnostic['summary'],configuration)
        row['sampled_cylinder_pdv'] = sampled_pdv(diagnostic['samples'],configuration)
        row.update(variant=p['variant'],rpm=p['rpm'],periodicity=p['periodicity'])
        for path in (diag,native): verified[str(path)] = sha(path)
        rows.append(row)
    return {'classification':'PHYSICAL_BALANCE_EXPLAINED_EXPERIMENTAL_ACCURACY_NOT_IDENTIFIED',
            'solver_steps_executed':0,'reference_run_executed':False,
            'source_receipt_sha256':sha(receipt_path),'verified_unchanged':verified,'points':rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',default='results/periodic-rpm-curves-v1/receipt.json')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    data = analyze(args.receipt)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'points':len(data['points']),'solver_steps':0,'output':args.output}))
