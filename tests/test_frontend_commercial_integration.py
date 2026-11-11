"""Combined product workflows; never numerical or experimental validation."""
import json
import os
from datetime import datetime,timezone
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import desktop_qsettings_isolation
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.license_dialog import LicenseDialog
from motorsim.licensing import license as licensing,ed25519

APP=QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path,monkeypatch):
    monkeypatch.setenv('DINO_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    monkeypatch.setenv('DINO_LICENSE_ROOT',str(tmp_path/'license'))
    w=DinoDesktopWindow()
    yield w
    w.native_four_stroke.editor.discard_draft()
    w.pages[0].discard_draft();w.pages[1].discard_draft()
    w.four_stroke_workspace.refresh(w.four_stroke_context.project);w.experience.reference_loaded()
    for context in (w.context,w.four_stroke_context,w.native_four_stroke.context):context.dirty=False
    w.close();APP.processEvents()


def test_license_menu_opens_actual_dialog_with_frontend_context(window):
    seen=[]
    def close():
        dialog=APP.activeModalWidget();seen.append(isinstance(dialog,LicenseDialog));dialog.accept()
    QTimer.singleShot(0,close)
    window.show_license()
    assert seen==[True]
    assert window.project_header is not None and 'TRIAL' in window.license_label.text()


@pytest.mark.parametrize('state',['TRIAL','TRIAL_EXPIRED','INVALID_LICENSE','LICENSED'])
def test_commercial_states_keep_save_and_project_access(window,tmp_path,monkeypatch,state):
    root=tmp_path/'license';root.mkdir(exist_ok=True)
    secret=os.urandom(32)
    monkeypatch.setattr(licensing,'VENDOR_PUBLIC_KEYS',{'integration-test':ed25519.public_key(secret)})
    if state=='TRIAL_EXPIRED':
        (root/'trial.json').write_text(json.dumps(dict(schema='DINO_TRIAL_STATE_V1',started_at='2000-01-01T00:00:00+00:00',last_seen_at='2000-01-01T00:00:00+00:00')))
    elif state=='INVALID_LICENSE':(root/'license.json').write_text('{}')
    elif state=='LICENSED':
        payload=dict(schema='DINO_LICENSE_V1',product='Dino Desktop',license_type='PERPETUAL',activation='OFFLINE',license_id='integration',customer='Synthetic test',issued_at=datetime.now(timezone.utc).isoformat())
        document=licensing.sign_license(payload,secret,'integration-test')
        (root/'license.json').write_text(json.dumps(document))
    status=licensing.license_status()
    assert status['state']==state and status['core_access_allowed']
    window._refresh_license_label()
    window.show_native_four_stroke_mode()
    context=window.native_four_stroke.context;context.dirty=True
    path=tmp_path/(state+'.json')
    assert window._save_native_project(path) and path.is_file()
    assert window.project_header is not None
    assert window.experience.project.text().startswith('Proyecto:')


def test_manual_update_works_in_reorganized_shell_without_network(window,tmp_path,monkeypatch):
    import socket
    monkeypatch.setattr(socket,'create_connection',lambda *_a,**_k:pytest.fail('network called'))
    monkeypatch.setattr(QMessageBox,'information',lambda *_a:None)
    path=tmp_path/'update.json'
    path.write_text(json.dumps(dict(schema='DINO_UPDATE_MANIFEST_V1',version='9.9.9',source_commit='a'*40,channel='engineering',zip_sha256='b'*64,dino2t_exe_sha256='c'*64,worker_exe_sha256='d'*64,released_at='2026-11-11T12:00:00+00:00')))
    assert window.check_for_updates(path)


def test_native_shortcuts_cannot_change_configuration_during_worker(window):
    from copy import deepcopy
    window.show_native_four_stroke_mode()
    context=window.native_four_stroke.context
    changed=deepcopy(context.engine());changed['geometry']['bore_mm']=87
    context.replace_engine(changed)
    window.native_four_stroke.simulation.task=object()  # active-slot boundary only
    try:
        window._refresh_history_actions()
        assert not window.undo_action.isEnabled()
        window._undo_active()
        assert context.engine()['geometry']['bore_mm']==87
    finally:window.native_four_stroke.simulation.task=None


def test_reference_shortcuts_are_disabled_while_execution_reserved(window):
    window.show_four_stroke_mode();context=window.four_stroke_context
    context.update(name='pending history')
    token=context.begin_execution('synthetic reservation test')
    try:
        assert not window.undo_action.isEnabled()
        window._undo_active()
        assert context.name=='pending history'
    finally:context.end_execution(token)
