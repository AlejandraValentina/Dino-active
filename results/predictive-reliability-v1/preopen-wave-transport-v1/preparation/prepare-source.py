"""Prepare conservative initial states for a short recorded39 wave diagnostic."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal,_solver_dependency_hashes
from motorsim.kinematics import piston_position
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load
from scripts.diagnostics.remap_representation_v1 import initialize,project
from scripts.diagnostics.compare_remap_representation_v1 import restrict_to
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def closed_interval(engine):
    binding=engine.port_binding.to_dict();ports=[p for p in binding['port_set']['ports'] if p['role']=='exhaust']
    if not ports or any(p['family']!='rectangular_window' or p['roof_travel_mm']<0. for p in ports):raise ValueError('closed interval proof requires rectangular roofs with nonnegative closing travel')
    geometry=engine.slider_crank.crankcase
    # On0..60deg both sin and cos are nonnegative; slider-crank displacement
    # increases monotonically for validated rod>stroke/2. Maximum is at60.
    travel=piston_position(geometry.stroke_mm,geometry.rod_length_mm,60.)
    # The raised/open roof is a lower bound: validated powervalve position
    # lies in[0,1], so top+travel*position can only close the port further.
    roof=min(p['top_mm'] for p in ports)
    if travel>=roof:raise ValueError('exhaust opens in proposed diagnostic interval')
    samples=[engine._geometry(13680.+a,9000.).exhaust_area_m2 for a in (0.,15.,30.,45.,60.)]
    if any(area!=0. for area in samples):raise ValueError('geometry contradicts closed-roof proof')
    return dict(phase_interval_deg=[0.,60.],maximum_piston_travel_mm=travel,minimum_exhaust_roof_mm=roof,
        geometric_margin_mm=roof-travel,sampled_effective_areas_m2=samples,
        proof='Monotone slider-crank displacement0..60deg remains below every fully raised rectangular exhaust roof; nonnegative validated valve travel only closes further. Actual geometry samples also zero.')


def prepare(root):
    source=root/'periodic88-window2-v1';manifest=load(source/'manifest.json')
    def bound(name):
        if sha(source/name)!=manifest['files'][name]:raise ValueError('source38 evidence changed')
        return load(source/name)
    config=bound('run/configuration.json');cp=bound('run/checkpoint-absolute-038.json');receipt=bound('run/receipt.json')
    frames=bound('run/frames-absolute-039.json')
    if receipt['source_solver_sha256']!=_solver_dependency_hashes():raise ValueError('source model differs')
    e=IntegratedEngine2T.from_configuration_dict(config);e.restore(cp)
    if not _json_evidence_equal(e.snapshot(),cp) or e.crank_angle_unwrapped_deg!=13680.:raise ValueError('source native38 differs')
    proof=closed_interval(e);templates={};details={}
    for name,level,family in (('p0-88',0,'P0'),('p0-176',1,'P0'),('p0-352',2,'P0'),('p1-176',1,'P1')):
        engine,cfg,remap=initialize(config,cp,level,family,sha(source/'run/checkpoint-absolute-038.json'))
        if not _json_evidence_equal(engine.snapshot()['fuel_combustion'],cp['fuel_combustion']):raise ValueError('fuel event history changed')
        restricted=restrict_to(engine.state,cfg,config);matched=compare_states(cp['state'],restricted,config)
        maximum=max(metric['Linf'] for duct in matched.values() for metric in duct.values())
        if maximum>1e-12:raise ValueError('initial common-volume physical fields differ')
        p0,_=project(cp['state'],config,cfg,'P0');subcell=compare_states(p0,engine.state,cfg)
        if family=='P0' and max(m['Linf'] for d in subcell.values() for m in d.values())>1e-12:raise ValueError('P0 physical subcell field differs')
        templates[name]=dict(configuration=cfg,checkpoint=engine.snapshot())
        details[name]=dict(cells=sum(len(p['mesh']['volumes']) for p in cfg['ducts']),remap=remap,
            common_volume_fields=matched,subcell_fields_vs_root_P0=subcell,native_roundtrip_exact=_json_evidence_equal(engine.snapshot(),templates[name]['checkpoint']))
    samples=[dict(phase_deg=a,frame=next(f for f in frames if f['angle']==13680.+a)) for a in (0.,30.,60.)]
    return templates,dict(schema='PREOPEN_WAVE_TRANSPORT_PREPARATION_V1',solver_steps=0,source_absolute_cycle=38,target_recorded_cycle=39,
        source_checkpoint_sha256=sha(source/'run/checkpoint-absolute-038.json'),source_frames_sha256=sha(source/'run/frames-absolute-039.json'),
        source_manifest_sha256=sha(source/'manifest.json'),solver_dependency_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),
        closed_exhaust_proof=proof,initialization=details,original_recorded_reference=samples,
        qualification='Preparation only; no refinement evolution, periodicity, mesh independence or experimental validation. P1 is an admissible unresolved-field hypothesis, not measured truth.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('preserve preparation')
    preflight=check_storage_requirements([(a.output,2*1024**2)]);templates,result=prepare(a.root);a.output.mkdir(parents=True)
    for name,value in templates.items():write(a.output/(name+'-initial.json'),value)
    result['storage_preflight']=preflight;write(a.output/'receipt.json',result)
    print({'status':'PREPARED_ONLY','solver_steps':0,'cells':{k:v['cells'] for k,v in result['initialization'].items()},'closed_margin_mm':result['closed_exhaust_proof']['geometric_margin_mm']})
