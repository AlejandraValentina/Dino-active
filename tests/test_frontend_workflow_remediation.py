import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import desktop_qsettings_isolation
import pytest
from copy import deepcopy
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.new_engine_dialog import NewEngineDialog
from motorsim.desktop.workspace_experience import descriptor
from motorsim.desktop.onboarding import first_steps_status
from motorsim.desktop.four_stroke_project import config_identity
from c01_c03_fixtures import endpoint_factory

APP=QApplication.instance() or QApplication([])

@pytest.fixture
def window(tmp_path,monkeypatch):
    monkeypatch.setenv('DINO_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    w=DinoDesktopWindow()
    yield w
    w.native_four_stroke.editor.discard_draft()
    w.pages[0].discard_draft();w.pages[1].discard_draft()
    w.four_stroke_workspace.refresh(w.four_stroke_context.project)
    w.experience.reference_loaded()
    for context in (w.context,w.native_four_stroke.context,w.four_stroke_context):context.dirty=False
    w.close();APP.processEvents()


def test_header_and_help_follow_active_context(window):
    w=window
    assert descriptor(w)['model']=='2T integrado'
    w.results.dataset=object()
    w.show_native_four_stroke_mode();w.experience.refresh()
    assert '4T nativo' in w.experience.project.text()
    assert not first_steps_status(w)[2]['ok']
    assert w.native_four_stroke.context.project['project_id'] in w.experience.project.text()
    w.show_four_stroke_mode();w.experience.refresh()
    assert 'referencia sintética' in w.experience.project.text()
    assert not first_steps_status(w)[2]['ok']
    assert w.four_stroke_tabs.tabBar().isHidden()
    w.results.dataset=None


def test_physical_form_preserves_precision_until_edit(window):
    editor=window.native_four_stroke.editor;context=editor.context
    before=deepcopy(context.engine());identity=config_identity(before)
    assert not editor.has_pending_changes
    assert editor.apply()
    assert config_identity(context.engine())==identity
    field=editor.fields[('geometry','bore_mm')]
    field.selectAll();QTest.keyClicks(field,'87')
    context.changed.emit()
    assert field.text()=='87' and editor.has_pending_changes
    assert context.engine()==before
    assert editor.apply()
    assert context.engine()['geometry']['bore_mm']==87
    assert not editor.has_pending_changes


def test_reference_apply_all_is_atomic_and_keeps_invalid_draft(window):
    workspace=window.four_stroke_workspace;context=window.four_stroke_context
    original=deepcopy(context.project);undo=deepcopy(context._undo)
    workspace.geometry.bore.setText('88')
    workspace.valves.fields['intake']['seat_mm'].setText('bad')
    assert not workspace.apply_all()
    assert context.project==original and context._undo==undo
    assert workspace.geometry.bore.text()=='88'
    assert workspace.valves.fields['intake']['seat_mm'].text()=='bad'


def test_pending_reference_cancel_blocks_substitution_and_export(window,monkeypatch):
    w=window;w.show_four_stroke_mode()
    w.four_stroke_workspace.geometry.bore.setText('88')
    monkeypatch.setattr(QMessageBox,'exec',lambda *_:QMessageBox.StandardButton.Cancel)
    assert not w._confirm_discard_four_stroke()
    assert w.four_stroke_workspace.geometry.bore.text()=='88'
    from PySide6.QtWidgets import QFileDialog
    calls=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(calls.append(a) or ('','')))
    w.export_project_bundle()
    assert not calls


def test_new_reference_model_is_explicit():
    dialog=NewEngineDialog();dialog.cycle.setCurrentIndex(2);dialog._create()
    assert dialog.project['schema']=='MOTORSIM_4T_REFERENCE_PROJECT_V1'
    assert 'referencia' in dialog.four_info.text().lower()
    dialog.close()


def test_native_comparison_guides_distinct_eligible_pair(window,tmp_path):
    factory=endpoint_factory(tmp_path/'endpoints')
    a=factory('A');b=factory('B')
    from motorsim.desktop.four_stroke_project import create_project
    project=create_project('comparison',a['config'],run_references=[a['reference'],b['reference']])
    window.native_four_stroke.replace_project(project)
    results=window.native_four_stroke.results
    assert not results.compare_button.isEnabled()
    assert 'distintas' in results.compare_status.text()
    results.compare_b.setCurrentIndex(1)
    assert results.compare_button.isEnabled(),results.compare_status.text()
    results.compare()
    assert results.comparison and results.compare_json_button.isEnabled()
    assert 'validadas experimentalmente' in results.compare_status.text()


def test_native_plan_budget_is_explicit(window):
    curve=window.native_four_stroke.curve
    curve.start_rpm.setValue(3000);curve.end_rpm.setValue(4000);curve.step_rpm.setValue(500);curve.wall.setValue(10)
    assert '3 puntos' in curve.plan_preview.text()
    assert '30' in curve.plan_preview.text() and 'desconocida' in curve.plan_preview.text()


def test_two_stroke_terminal_result_link_and_project_reset(window,tmp_path,monkeypatch):
    import hashlib,json
    from motorsim.desktop.services import new_design_project
    from motorsim.engine_configuration import identity
    context=window.context;page=window.pages[3]
    # Isolate publication of a reference; real result parsing is covered by
    # the live solver walkthrough, not this minimal callback record.
    monkeypatch.setattr(window.results,'open_runs',lambda *_:None)
    directory=tmp_path/'published';directory.mkdir()
    stored={'classification':'MAX_CYCLES_NONCONVERGED','bindings':{
        'project_id':context.project['project_id'],'identity_sha256':identity(context.engine())}}
    raw=json.dumps(stored).encode();(directory/'result.json').write_bytes(raw)
    page._done(dict(stored,artifact_directory=str(directory)))
    assert page.view_result.isEnabled()
    assert context.project['result_references'][0]['artifact_sha256']==hashlib.sha256(raw).hexdigest()
    assert context.dirty
    context.replace_project(new_design_project('different-project'))
    assert not page.view_result.isEnabled() and page.last_result_paths==[]


def test_reference_unapplied_draft_alone_blocks_close(window,monkeypatch):
    from PySide6.QtGui import QCloseEvent
    window.four_stroke_workspace.geometry.bore.setText('88')
    assert not window.four_stroke_context.dirty
    monkeypatch.setattr(QMessageBox,'exec',lambda *_:QMessageBox.StandardButton.Cancel)
    event=QCloseEvent();window.closeEvent(event)
    assert not event.isAccepted()
    assert window.four_stroke_workspace.geometry.bore.text()=='88'


def test_form_order_and_unit_case_survive_sorted_json(window):
    import json
    context=window.native_four_stroke.context
    context.replace_project(json.loads(json.dumps(context.project,sort_keys=True)))
    editor=window.native_four_stroke.editor
    assert list(editor.tables)[0]=='geometry'
    from PySide6.QtWidgets import QLabel
    labels=[w.text() for w in editor.findChildren(QLabel)]
    assert 'Presión de admisión (Pa)' in labels
    assert 'Temperatura de admisión (K)' in labels
