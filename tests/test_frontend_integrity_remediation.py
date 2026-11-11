"""Application integrity regressions. Synthetic fixtures are not simulation evidence."""
import hashlib
import json
import os
import pytest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication,QMessageBox
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_project import project_from_example,create_project
from motorsim.desktop.four_stroke_desktop import FourStrokeConfigEditor,FourStrokeSimulation
from motorsim.desktop.four_stroke_artifacts import assess_run_reference
from motorsim.desktop.project_bundles import write_project_bundle,import_bundle,inspect_bundle
from c01_c03_fixtures import endpoint_factory

APP=QApplication.instance() or QApplication([])


def test_imported_context_normalizes_path(tmp_path):
    context=DesktopContext(project_from_example('path-test'))
    context.replace_project(context.project,str(tmp_path/'imported.json'))
    assert context.path==tmp_path/'imported.json'
    assert isinstance(context.path,Path)


def test_native_draft_survives_unrelated_context_refresh():
    context=DesktopContext(project_from_example('draft-test'))
    editor=FourStrokeConfigEditor(context)
    original=context.engine()['geometry']['bore_mm']
    editor.tables['geometry'].item(1,1).setText('87')
    context.changed.emit()  # e.g. publication of a run reference
    assert editor.tables['geometry'].item(1,1).text()=='87'
    assert context.engine()['geometry']['bore_mm']==original
    editor.close()


def test_pending_draft_cancel_blocks_real_execution_command(tmp_path,monkeypatch):
    monkeypatch.setenv('DINO_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    context=DesktopContext(project_from_example('draft-submit'))
    editor=FourStrokeConfigEditor(context)
    editor.tables['geometry'].item(1,1).setText('87')
    simulation=FourStrokeSimulation(context)
    submitted=[]
    monkeypatch.setattr(simulation.thread_pool,'start',lambda task:submitted.append(task))
    monkeypatch.setattr(QMessageBox,'exec',lambda *_:QMessageBox.StandardButton.Cancel)
    try:
        simulation.execute()
        assert submitted==[], 'an unapplied draft must not silently submit the old configuration'
        assert simulation.task is None
    finally:
        simulation.task=None
        editor.close();simulation.close()


def test_save_native_imported_str_path_and_io_error(tmp_path,monkeypatch):
    monkeypatch.setenv('DINO_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    window=DinoDesktopWindow()
    context=window.native_four_stroke.context
    path=tmp_path/'native.json'
    context.replace_project(context.project,str(path))
    context.dirty=True
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:warnings.append(args))
    try:
        assert window._save_native_project()
        before=path.read_bytes()
        context.dirty=True
        import motorsim.desktop.app as application
        monkeypatch.setattr(application,'save_project',lambda *_:(_ for _ in ()).throw(PermissionError('read only')))
        assert not window._save_native_project()
        assert context.dirty and path.read_bytes()==before
        assert warnings
    finally:
        for ctx in (window.context,window.four_stroke_context,context):ctx.dirty=False
        window.close();APP.processEvents()


def native_endpoint(tmp_path):
    endpoint=endpoint_factory(tmp_path/'source')('A')
    return endpoint,create_project('synthetic-test',endpoint['config'],run_references=[endpoint['reference']])


def test_native_bundle_preserves_transitive_bytes_without_original_root(tmp_path,monkeypatch):
    endpoint,project=native_endpoint(tmp_path)
    original=assess_run_reference(endpoint['reference'])
    metadata=Path(endpoint['reference']['run_manifest_path']).read_bytes()
    source=write_project_bundle(tmp_path/'portable.zip',project,family='4T_native')
    imported=import_bundle(source,tmp_path/'destination')
    ref=imported['project']['run_references'][0]
    actual_read=Path.read_bytes
    def isolated_read(path):
        if not path.resolve().is_relative_to((tmp_path/'destination').resolve()):
            raise FileNotFoundError('original root deliberately unavailable')
        return actual_read(path)
    monkeypatch.setattr(Path,'read_bytes',isolated_read)
    observed=assess_run_reference(ref)
    assert observed.verified,observed.issues
    assert observed.snapshot['metadata_raw']==metadata
    assert observed.snapshot['manifest_raw']==original.snapshot['manifest_raw']
    assert observed.snapshot['raw']==original.snapshot['raw']
    assert observed.summary['claims']==original.summary['claims']


def test_incomplete_native_bundle_is_explicitly_partial(tmp_path):
    endpoint,project=native_endpoint(tmp_path)
    assessment=assess_run_reference(endpoint['reference'])
    assessment.snapshot['paths']['config'].unlink()  # this test's new temporary fixture only
    source=write_project_bundle(tmp_path/'partial.zip',project,family='4T_native')
    manifest,_=inspect_bundle(source)
    assert manifest['availability']=='PARTIAL'
    assert manifest['warnings']
    imported=import_bundle(source,tmp_path/'partial-destination')
    assert imported['availability']=='PARTIAL'
    assert not assess_run_reference(imported['project']['run_references'][0]).verified


def test_bundle_import_never_overwrites_existing_destination(tmp_path):
    from motorsim.desktop.services import new_design_project
    source=write_project_bundle(tmp_path/'project.zip',new_design_project('new'),family='2T')
    destination=tmp_path/'original';destination.mkdir()
    original=destination/'project.json';original.write_bytes(b'owner original')
    with pytest.raises(FileExistsError):import_bundle(source,destination)
    assert original.read_bytes()==b'owner original'


@pytest.mark.parametrize('name',['../outside.json','C:/outside.json','x/../../outside.json'])
def test_bundle_members_cannot_escape_import_root(name):
    from motorsim.desktop.project_bundles import _safe_member
    with pytest.raises(ValueError):_safe_member(name)


def test_legacy_metadata_relocation_does_not_promote(tmp_path):
    import shutil
    from motorsim.desktop.four_stroke_project import load_example
    source=tmp_path/'legacy'/'artifacts';source.mkdir(parents=True)
    original=Path('results/dino4t-stage2-v1/example/8000rpm')
    for name in ['summary.json','config_resolved.json','trace_last_cycle.csv']:
        shutil.copy2(original/name,source/name)
    summary=json.loads((source/'summary.json').read_bytes())
    config=json.loads((source/'config_resolved.json').read_bytes())
    meta={'schema':'DINO4T_DESKTOP_RUN_V1','config_path':str(source/'config_resolved.json')}
    (source.parent/'run.json').write_text(json.dumps(meta),encoding='utf-8')
    ref=dict(run_id='legacy',path=str(source/'summary.json'),result_sha256=hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),config_sha256=summary['config_sha256'],status=summary['status'],periodicity_status=summary['periodicity']['status'],variant_id='')
    project=create_project('legacy',config,run_references=[ref])
    bundle=write_project_bundle(tmp_path/'legacy.zip',project,family='4T_native')
    result=import_bundle(bundle,tmp_path/'relocated')
    assessment=assess_run_reference(result['project']['run_references'][0])
    assert assessment.classification=='LEGACY_UNVERIFIED'
    assert result['legacy_reference_count']==1
    assert not assessment.verified
