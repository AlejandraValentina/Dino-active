"""Focal geometry/UI contracts. No scientific campaign in tests."""
from copy import deepcopy
from pathlib import Path
import json
import hashlib

import pytest
from motorsim.engine_project import load_project,save_project
from motorsim.engine_variants import partitioned_escape_counts,stretch_partitioned_escape,escape_sections

PROJECT=Path(__file__).resolve().parents[1]/'configs/reference_cases/functional_reed_125cc_v1.dino.json'


def test_length_edit_retains_topology_primitives_and_other_physics():
    base=load_project(PROJECT)['base_engine'];before=deepcopy(base)
    sections=escape_sections(base);sections[0]['length_mm']+=20
    edited=stretch_partitioned_escape(base,sections)
    assert base==before
    assert partitioned_escape_counts(edited)==[3,5,6,2,2,6,7]
    a=base['native_configuration'];b=edited['native_configuration']
    assert a['initial_duct_states']==b['initial_duct_states']
    assert base['mechanical_loss_model']==edited['mechanical_loss_model']
    for key in a:
        if key not in {'ducts','duct_species','geometry_identity'}:assert a[key]==b[key],key
    for da,db in zip(a['ducts'],b['ducts']):
        if da['id']!='exhaust':assert da==db
        else:
            assert len(db['mesh']['volumes'])==31
            assert db['mesh']['areas']==da['mesh']['areas']
            assert db['mesh']['faces'][-1]-da['mesh']['faces'][-1]==pytest.approx(.02)
            for i,(v,w) in enumerate(zip(da['mesh']['volumes'],db['mesh']['volumes'])):
                assert [m/w for m in b['duct_species']['exhaust'][i]]==pytest.approx([m/v for m in a['duct_species']['exhaust'][i]])


def test_partitioned_edit_rejects_unrecognized_geometry_and_diameter_edit():
    base=load_project(PROJECT)['base_engine'];sections=escape_sections(base)
    sections[0]['outlet_diameter_mm']+=1
    with pytest.raises(ValueError,match='length edits only'):stretch_partitioned_escape(base,sections)
    sections=escape_sections(base);sections[0]['length_mm']=0
    with pytest.raises(ValueError,match='positive'):stretch_partitioned_escape(base,sections)


def test_desktop_edit_and_save_recover_comparison(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QAbstractItemView
    from PySide6.QtCore import QItemSelectionModel
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.exhaust_page import ExhaustPage
    from motorsim.desktop.widgets.run_history import RunHistoryWidget
    app=QApplication.instance() or QApplication([])
    context=DesktopContext(load_project(PROJECT));context.duplicate_variant(None,'B_header_plus20')
    page=ExhaustPage(context)
    assert page._counts(context.engine())==[3,5,6,2,2,6,7]
    page.table.item(0,1).setText('103.0')
    assert page.save_current(),page.diff.text()
    assert escape_sections(context.engine())[0]['length_mm']==103
    assert len(next(d for d in context.engine()['native_configuration']['ducts'] if d['id']=='exhaust')['mesh']['volumes'])==31
    widget=RunHistoryWidget(context,tmp_path)
    paths=[]
    for name in ['a','b']:
        path=tmp_path/(name+'.json');path.write_text(json.dumps(dict(bindings=dict(project_id=context.project['project_id']))));paths.append(str(path))
    widget.entries=[dict(result_path=p) for p in paths]
    monkeypatch.setattr(widget,'_selected',lambda:[0,1])
    assert widget.save_comparison()
    saved=tmp_path/'project.json';save_project(saved,context.project)
    context.replace_project(load_project(saved),saved)
    recovered=[];widget.open_runs.connect(recovered.append)
    assert widget.restore_comparison() and recovered[-1]==paths
    Path(paths[0]).write_text('{}')
    assert not widget.restore_comparison()
    page.close();widget.close()


def test_engineering_sweep_nested_checkpoint_reuse(monkeypatch,tmp_path):
    import motorsim.power_curve_sweep as sweep
    from test_power_curve_sweep import _patch_sweep,_kwargs
    _patch_sweep(monkeypatch,tmp_path,[])
    calls=[]
    def real_schema_fixture(document,**kw):
        calls.append(kw['rpm']);rpm=kw['rpm'];root=tmp_path/'artifacts'/'exploratory-workflow-v1'/kw['project_id']/kw['run_id']
        (root/'invocation-001').mkdir(parents=True)
        cp=b'checkpoint';(root/'invocation-001/checkpoint.json').write_bytes(cp)
        result=dict(schema='DINO_ENGINEERING_RUN_V1',bindings=dict(identity_sha256=f'rpm-{rpm}',configuration_sha256=f'config-{rpm}'))
        raw=json.dumps(result).encode();sha=hashlib.sha256(raw).hexdigest();(root/'result.json').write_bytes(raw)
        cp_sha=hashlib.sha256(cp).hexdigest()
        (root/'run.json').write_text(json.dumps(dict(result,result_sha256=sha,checkpoint_artifact='invocation-001/checkpoint.json',checkpoint_sha256=cp_sha)))
        return dict(result,status='COMPLETE',classification='MAX_CYCLES_NONCONVERGED',periodicity='NOT_CONVERGED',artifact_directory=str(root),result_sha256=sha,checkpoint_sha256=cp_sha)
    monkeypatch.setattr(sweep,'run_exploratory',real_schema_fixture)
    monkeypatch.setattr('motorsim.engineering_workflow.import_desktop_runs',lambda paths:dict(points=[dict(audit_status='NOT_PERFORMED')]))
    kw=_kwargs(tmp_path);first=sweep.run_power_curve({},**kw);second=sweep.run_power_curve({},**kw,resume=True)
    assert calls==[3000,4000]
    assert first['curve_availability']=='EXPLORATORY_CURVE_PARTIAL'
    assert all(r['resume_audit']=='INTEGRITY_VERIFIED_NOT_INDEPENDENT_AUDIT' for r in second['points'])
    manifest=Path(second['points'][0]['run_directory'])/'run.json';m=json.loads(manifest.read_text());m['checkpoint_artifact']='../escape.json';manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='checkpoint path'):sweep.run_power_curve({},**kw,resume=True)
