"""Hash-bound historical survey, no solver steps or checkpoint restoration."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.coupling import ChamberState
from motorsim.port_connection_v1 import port_connection_v1, PortDomainError
from motorsim.reed import static_area
from scripts.agents.storage_preflight import check_storage_requirements


def read_verified(path, expected):
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f"historical artifact hash mismatch: {path}")
    return json.loads(data)


def endpoint_coverage(samples):
    """Require actual endpoint primitives, not scalar chamber pressures."""
    return bool(samples) and all(
        isinstance(sample.get('duct_endpoint_primitives'), dict)
        and bool(sample['duct_endpoint_primitives'])
        and all(isinstance(w, (list, tuple)) and len(w) == 4
                for w in sample['duct_endpoint_primitives'].values())
        for sample in samples)


def survey(receipt_path):
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    points = []
    for record in receipt['points']:
        point = Path(record['result']).parent
        read_verified(Path(record['result']), record['result_sha256'])
        candidates = list(point.glob('invocation-*/manifest.json'))
        matched = [p for p in candidates if hashlib.sha256(p.read_bytes()).hexdigest() == record['manifest_sha256']]
        if len(matched) != 1:
            raise ValueError('cannot identify exactly one bound historical manifest')
        manifest_path = matched[0]
        manifest = read_verified(manifest_path, record['manifest_sha256'])
        checkpoint_path = manifest_path.parent / manifest['checkpoint_artifact']
        checkpoint = read_verified(checkpoint_path, record['checkpoint_sha256'])
        configuration = read_verified(point/'native-configuration.json',
            manifest['bindings']['configuration_file_sha256'])
        # Construction resolves serialized geometry only. We never call restore
        # or step, and never overwrite source bindings to make old states resume.
        engine = IntegratedEngine2T.from_configuration_dict(configuration)
        snapshot = checkpoint['engine_snapshot']
        state = snapshot['state']
        angle = snapshot['crank_angle_unwrapped_deg']
        g = engine._geometry(angle, record['rpm'])
        chambers = {}
        for name, (mass, energy, volume) in state['chambers'].items():
            species = state['species']['chambers'][name]
            chambers[name] = ChamberState(mass, energy, mass*sum(species[:2])/sum(species), volume)
        rows = []
        for path in engine.ducts:
            if path.role == 'intake':
                w = engine._primitive(state['ducts'][path.id][-1])
                pc = chambers['crankcase'].thermodynamics(engine.eos)[1]
                area = min(g.intake_area_m2, path.mesh.areas[-1],
                           static_area(engine.reed_petals, w[2]-pc)) if engine.reed_petals else min(g.intake_area_m2,path.mesh.areas[-1])
                endpoints = [('right','crankcase',-1,1,area)]
            elif path.role == 'exhaust':
                endpoints = [('left','cylinder',0,-1,min(g.exhaust_area_m2,path.mesh.areas[0]))]
            else:
                index = next(i for i,p in enumerate(engine.transfers) if p.id == path.id)
                area = g.transfer_areas_m2[index]
                left = path.mesh.areas[0] if engine.gas_exchange_model else min(area,path.mesh.areas[0])
                endpoints = [('left','crankcase',0,-1,left),('right','cylinder',-1,1,min(area,path.mesh.areas[-1]))]
            for side, name, index, normal, area in endpoints:
                w = engine._primitive(state['ducts'][path.id][index])
                ap = path.mesh.areas[0 if side=='left' else -1]
                c = chambers[name]
                _,pc,tc,_ = c.thermodynamics(engine.eos)
                row = dict(duct=path.id,side=side,chamber=name,
                           chamber_pressure_pa=pc,chamber_temperature_k=tc,
                           pipe_pressure_pa=w[2],pipe_temperature_k=w[2]/(w[0]*engine.eos.R),
                           pipe_outward_mach=normal*w[1]/engine.eos.sound_speed(w),
                           effective_area_ratio=area/ap)
                try:
                    x = port_connection_v1(c,w,area,ap,normal,eos=engine.eos)
                    row.update(candidate_v1_status='SUPPORTED',branch=x.branch)
                except PortDomainError as error:
                    row.update(candidate_v1_status='UNSUPPORTED',error=str(error))
                rows.append(row)
        cycle = manifest['cycles'][-1]
        diagnostic_path = manifest_path.parent/f"cycle-{cycle['cycle']:03d}-diagnostics.json"
        diagnostic = read_verified(diagnostic_path,cycle['diagnostic_artifact_sha256'])
        points.append(dict(variant=record['variant'],rpm=record['rpm'],
            checkpoint=str(checkpoint_path),checkpoint_sha256=record['checkpoint_sha256'],
            configuration_sha256=manifest['bindings']['configuration_file_sha256'],
            cycle=cycle['cycle'],angle_deg=angle,phase_deg=angle%360,ports=rows,
            diagnostic_samples=len(diagnostic['samples']),
            diagnostic_has_endpoint_density_velocity_temperature=endpoint_coverage(diagnostic['samples']),
            diagnostic_sample_fields=sorted(diagnostic['samples'][0]) if diagnostic['samples'] else [],
            checkpoint_trace_steps=len(snapshot['trace'])))
    rows = [row for point in points for row in point['ports']]
    return dict(schema='DINO_HISTORICAL_PORT_SURVEY_V1',
        source_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        points=points,checkpoint_ports=len(rows),
        open_ports=sum(row['effective_area_ratio']>0 for row in rows),
        unsupported_checkpoint_ports=sum(row['candidate_v1_status']=='UNSUPPORTED' for row in rows),
        intra_cycle_regime_coverage=('ENDPOINT_STATES_PRESENT' if all(
            point['diagnostic_has_endpoint_density_velocity_temperature'] for point in points)
            else 'INDETERMINATE_MISSING_ENDPOINT_STATES'),
        conclusion='No inference of absence during blowdown: preserved diagnostics lack instantaneous endpoint density and velocity; checkpoints provide cycle-boundary states only.',
        physical_steps=0,source_artifacts_modified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipt',type=Path,default=ROOT/'results/periodic-rpm-curves-v1/receipt.json')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    preflight=check_storage_requirements([(args.output.parent,5*1024**2)])
    result=survey(args.receipt)
    result['storage_preflight']=preflight
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('points','storage_preflight')},indent=2))


if __name__=='__main__':main()
