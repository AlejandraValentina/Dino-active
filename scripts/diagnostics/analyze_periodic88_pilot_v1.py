"""Phase-matched transient88 evolution against the audited periodic44 case."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim._evidence_io import read_primary
from motorsim.integrated_2t import _json_evidence_equal
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load
from scripts.diagnostics.compare_remap_representation_v1 import restrict_to,profile_metrics
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states


def phase_frames(primary):
    origin=primary['cycle_start_deg'];frames=[dict(phase=0.,state=primary['start_state'])]
    for row in primary['trajectory']:
        phase=row['angle_end_deg']-origin
        if abs(phase-round(phase/30.)*30.)<1e-9:
            frames.append(dict(phase=phase,state=row['stage_states'][2]))
    if [f['phase'] for f in frames]!=[float(x) for x in range(0,361,30)]:raise ValueError('reference phase samples incomplete')
    return frames


def groups(comparison):
    result=defaultdict(list)
    for key,value in comparison.get('metrics',{}).items():
        region='exhaust' if key.startswith('ducts.exhaust') else 'other_ducts' if key.startswith('ducts.') else 'global_species' if key.startswith('global_species') else 'chambers_and_integrals'
        kind='composition' if '.species.' in key else key.rsplit('.',1)[-1]
        result[region+':'+kind].append(value['value']/value['threshold'])
    return {name:dict(maximum=max(values),p90=float(np.quantile(values,.9)),failed=sum(x>1 for x in values),count=len(values)) for name,values in result.items()}


def joined_cycles(pilot,additional):
    config=load(pilot/'configuration.json');items=[];segments=[];last=None
    for path in [pilot]+list(additional):
        receipt=load(path/'receipt.json')
        if receipt['status']=='ERROR':raise ValueError('pilot execution error must be diagnosed first')
        if load(path/'configuration.json')!=config:raise ValueError('additional segment configuration differs')
        cycles=load(path/'cycles.json')
        if last is not None and cycles:
            initial=load(path/'initial-checkpoint.json')
            if not _json_evidence_equal(initial,last):raise ValueError('segment native continuity differs')
            if receipt.get('source_partial_replay_verified') is not True:raise ValueError('partial recovery not verified')
        for cycle in cycles:
            if cycle['cycle']!=len(items)+1 or cycle['absolute_cycle']!=30+cycle['cycle']:raise ValueError('segment cycle continuity differs')
            items.append((cycle,path))
        if cycles:last=load(path/f"checkpoint-absolute-{cycles[-1]['absolute_cycle']:03}.json")
        segments.append(dict(path=path.as_posix(),status=receipt['status'],receipt_sha256=sha(path/'receipt.json')))
    return items,segments


def analyze(root,additional_segments=()):
    pilot=root/'periodic88-pilot-v1/run';audit=root/'periodic-primary-audit-v1'
    items,segments=joined_cycles(pilot,additional_segments);cycles=[c for c,p in items]
    fine=load(pilot/'configuration.json');coarse=load(root/'spatial-boundary-v2-engine/configuration.json')
    manifest=load(audit/'manifest.json');entry=load(audit/'run/cycle-030-audit.json')
    if sha(audit/'run/cycle-030-audit.json')!=manifest['files']['run/cycle-030-audit.json']:raise ValueError('audit reference changed')
    source=load(audit/'run/receipt.json');path=Path(source['durable_artifact_root'])/entry['artifact_name']
    if sha(path)!=entry['compressed_sha256']:raise ValueError('primary reference changed')
    primary=read_primary(path,expected_sha256=entry['primary_sha256']);reference=phase_frames(primary)
    initial=load(pilot/'initial-checkpoint.json');source_cp=load(root/'periodicity-cycle30-control-v1/run/checkpoint-030.json')
    records=[];previous=None
    for cycle,directory in items:
        frames=load(directory/f"frames-absolute-{cycle['absolute_cycle']:03}.json");rows=[];lag=[]
        if len(frames)!=len(reference):raise ValueError('phase count differs')
        for i,(frame,ref) in enumerate(zip(frames,reference)):
            phase=frame['angle']-360.*(cycle['absolute_cycle']-1)
            if phase!=ref['phase']:raise ValueError('phase mismatch')
            rows.append(dict(phase=phase,fields=compare_states(ref['state'],restrict_to(frame['state'],fine,coarse),coarse)))
            if previous is not None:lag.append(dict(phase=phase,fields=compare_states(previous[i]['state'],frame['state'],fine)))
        comparison=cycle['comparison'];metrics=comparison.get('metrics',{})
        ledgers=[frames[0]['ledger'],frames[-1]['ledger']]
        phase300=next(f for f in frames if f['angle']-360.*(cycle['absolute_cycle']-1)==300.)
        heat=ledgers[1]['fuel_combustion_heat_added_J']-ledgers[0]['fuel_combustion_heat_added_J']
        burned_fuel=-(ledgers[1]['fuel_combustion_source_species_kg'][1]-ledgers[0]['fuel_combustion_source_species_kg'][1])
        chemistry=dict(chemical_heat_J=heat,fuel_burned_kg=burned_fuel,
            cylinder_composition_at_phase300_kg=phase300['state']['species']['chambers']['cylinder'],
            qualification='Same phase300 sample, not an interpolated exhaust-close measurement. Whole-cycle heat can include portions of combustion events straddling TDC.')
        worst=sorted((dict(observable=k,ratio=v['value']/v['threshold'],value=v['value'],threshold=v['threshold']) for k,v in metrics.items()),key=lambda r:r['ratio'],reverse=True)[:15]
        records.append(dict(relative_cycle=cycle['cycle'],absolute_cycle=cycle['absolute_cycle'],statistics=cycle['statistics'],groups=groups(comparison),worst=worst,
            work_J=cycle['work_J'],imep_bar=cycle['imep_bar'],work_difference_vs44_J=cycle['work_J']-primary['observables']['work_J'],
            combustion_and_trapped_composition=chemistry,
            coarse44_reference_phase_comparison=rows,same88_previous_cycle_phase_comparison=lag,
            exhaust_profile=profile_metrics(frames[-1]['state'],fine)['exhaust'],conservation=cycle['conservation']))
        previous=frames
    trends=[]
    valid=[c for c in cycles if c['statistics'] is not None]
    if valid:
        for key,last in valid[-1]['comparison']['metrics'].items():
            values=[c['comparison']['metrics'][key]['value']/last['threshold'] for c in valid]
            change=(values[-1]-values[0])/max(values[0],1.)
            trends.append(dict(observable=key,first_ratio=values[0],last_ratio=values[-1],trend='improving' if change<-.05 else 'worsening' if change>.05 else 'stable'))
    return dict(schema='PERIODIC88_PHASE_EVOLUTION_ANALYSIS_V1',pilot_status=segments[-1]['status'],input_segments=segments,source_primary_sha256=entry['primary_sha256'],cycles=records,trends=trends,
        reference_phase_frames=reference,reference44_coupled_combustion=primary['observables']['fuel_coupled_combustion'],
        initial_transfer_common_volume_difference=compare_states(source_cp['state'],restrict_to(initial['state'],fine,coarse),coarse),
        coarse_periodic_reference_start_end_difference=compare_states(primary['start_state'],primary['terminal_state'],coarse),
        qualification='88 pilot is a different-mesh transient until independently detected and audited. Reference44 is periodic by its existing endpoint/integral contract, not an exact solution. Phase-zero transfer uses source end30, while the reference curve is actual29->30; source periodic residual is reported separately. No mesh independence or experimental claim.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--additional-segment',type=Path,action='append',default=[]);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve analysis')
    result=analyze(a.root,a.additional_segment);write(a.output,result);print({c['relative_cycle']:c['statistics'] for c in result['cycles']})
