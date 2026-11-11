"""Maintainer-only source/frozen Qt walkthrough; no scientific validation claim.

Uses actual application commands, Windows Qt widgets and real bounded workers.
File pickers are substituted with isolated paths. Only license public keys are
injected in this process; the random test signing secret is never persisted.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fixtures',type=Path,required=True)
    args=parser.parse_args(argv);root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    for env,name in [('DINO_TEST_SETTINGS_ROOT','settings'),('DINO_ARTIFACT_ROOT','artifacts'),
                     ('DINO_LICENSE_ROOT','licenses'),('LOCALAPPDATA','localappdata')]:
        os.environ[env]=str(root/name)
    from unittest.mock import patch
    from PySide6.QtCore import Qt,QTimer,QEvent,QThreadPool
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication,QMessageBox,QFileDialog,QPushButton
    from .app import DinoDesktopWindow
    from .product import AboutDialog,product_info,create_diagnostics_bundle,RecoveryController
    from .services import new_design_project
    from .four_stroke_artifacts import assess_run_reference
    from .project_bundles import write_project_bundle,import_bundle
    from ..engine_project import load_project
    from ..licensing import license as licensing,ed25519
    app=QApplication.instance() or QApplication(['DinoIntegrationAcceptance'])
    app.setApplicationName('Dino Integration Acceptance')
    window=DinoDesktopWindow(new_design_project('integration-2t'))
    window.show();checks={};captures={};events=[];issues=[];queue=None

    def note(key,value=True):
        checks[key]=bool(value)
        events.append(dict(check=key,passed=bool(value),at=datetime.now(timezone.utc).isoformat()))
        if not value:raise AssertionError(key)

    def wait(predicate,seconds=120):
        deadline=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>deadline:raise TimeoutError('Qt operation did not finish')
            app.processEvents();time.sleep(.02)
        app.processEvents()

    def capture(tag,target=None):
        app.processEvents();path=root/(tag+'.png');(target or app.activeModalWidget() or window).grab().save(str(path))
        captures[tag]=dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def enter(field,text):
        field.setFocus()
        app.sendEvent(field,QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier))
        app.sendEvent(field,QKeyEvent(QEvent.Type.KeyRelease,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier))
        for char in text:
            app.sendEvent(field,QKeyEvent(QEvent.Type.KeyPress,0,Qt.KeyboardModifier.NoModifier,char))
            app.sendEvent(field,QKeyEvent(QEvent.Type.KeyRelease,0,Qt.KeyboardModifier.NoModifier,char))
        app.processEvents()

    def answer(tag,text=None):
        def act(attempt=0):
            modal=app.activeModalWidget()
            if modal is None:
                if attempt<50:QTimer.singleShot(50,lambda:act(attempt+1))
                return
            capture(tag,modal)
            if text:
                for button in modal.findChildren(QPushButton):
                    if button.text().replace('&','')==text:button.click();return
                issues.append('Modal button missing: '+text)
            modal.accept()
        QTimer.singleShot(50,act)

    try:
        note('windows_qt',app.platformName()=='windows')
        note('cp2_and_frontend_present',hasattr(window,'license_label') and hasattr(window,'experience'))
        window.resize(1360,820);capture('01-integrated-2t')
        # Exercise the actual CP2 menu callback, not only an isolated dialog.
        answer('02-license-menu');window.show_license()
        original=deepcopy(window.context.engine());changed=deepcopy(original);changed['display_name']='Integration revision'
        window.context.replace_engine(changed);window._undo_active();a=window.context.engine()==original
        window._redo_active();note('undo_redo',a and window.context.engine()['display_name']=='Integration revision')
        window.context.path=root/'two-stroke.json';note('save_2t',window.save_file())
        page=window.pages[3];page.cycles.setValue(1);page.budget.setValue(30)
        window.set_workspace_mode(2);answer('03-2t-confirm','Iniciar corrida');page.start_run(resume=False)
        note('real_2t_started',page.task is not None)
        wait(lambda:page.task is None)
        note('2t_terminal_link',bool(page.last_result_paths) and page.view_result.isEnabled() and bool(window.context.project['result_references']))
        page.view_result.click();wait(lambda:window.results.dataset is not None)
        capture('04-2t-real-result')
        note('save_2t_with_result',window.save_file())
        two_ref=deepcopy(window.context.project['result_references'][0])
        bundle=write_project_bundle(root/'two-stroke.dinobundle',window.context.project,family='2T',project_path=window.context.path)
        imported=import_bundle(bundle,root/'two-relocated')
        note('2t_portable_result_bytes',Path(two_ref['path']).read_bytes()==Path(imported['project']['result_references'][0]['path']).read_bytes())
        # Native point: pending text cannot submit the applied 86 mm geometry.
        window.context.dirty=False;window.new_example_native_4t();window.set_workspace_mode(0)
        native=window.native_four_stroke;editor=native.editor;sim=native.simulation
        enter(editor.fields[('geometry','bore_mm')],'87')
        answer('05-native-draft-cancel','Cancelar');sim.execute()
        note('native_pending_cannot_submit',sim.task is None and editor.has_pending_changes and native.context.engine()['geometry']['bore_mm']==86)
        native.context.changed.emit();note('result_notification_preserves_draft',editor.fields[('geometry','bore_mm')].text()=='87')
        note('native_apply',editor.apply());note('native_save',window._save_native_project(root/'native.json'))
        window.set_workspace_mode(2);sim.cycles.setValue(1);sim.wall.setValue(10);sim.execute()
        old_token=sim._task_token
        note('native_exact_input_and_lock',sim.task is not None and sim.task.config['geometry']['bore_mm']==87 and not editor.isEnabled())
        window._undo_active();note('native_shortcut_lock',native.context.engine()['geometry']['bore_mm']==87)
        capture('06-native-running');wait(lambda:sim.task is None)
        previous=sim.progress.text();sim._progress(old_token,{'cycle':999})
        note('late_native_progress_ignored',sim.progress.text()==previous)
        ref=deepcopy(native.context.project['run_references'][-1]);assessed=assess_run_reference(ref)
        note('real_native_result',assessed.verified and json.loads(assessed.snapshot['raw']['config'])['geometry']['bore_mm']==87)
        window.set_workspace_mode(1);capture('07-native-real-result')
        window._save_native_project()
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(root/'native.dinobundle'),'')):
            answer('08-export-receipt');window.export_project_bundle()
        (root/'imports').mkdir()
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(root/'native.dinobundle'),'')),patch.object(QFileDialog,'getExistingDirectory',return_value=str(root/'imports')):
            answer('09-import-receipt');window.import_project_bundle()
        imported_ref=native.context.project['run_references'][-1]
        destination=native.context.path.parent;actual_read=Path.read_bytes
        def isolated(path):
            if not path.resolve().is_relative_to(destination):raise FileNotFoundError('Original root unavailable for acceptance')
            return actual_read(path)
        with patch.object(Path,'read_bytes',isolated):relocated=assess_run_reference(imported_ref)
        note('native_bundle_without_origin',relocated.verified and relocated.snapshot['raw']==assessed.snapshot['raw'])
        note('save_after_import',window._save_native_project())
        before_path=native.context.path;before=before_path.read_bytes()
        window.set_workspace_mode(0);enter(editor.fields[('geometry','bore_mm')],'88');note('edit_for_failure',editor.apply())
        blocked=root/'blocked.json';blocked.mkdir();answer('10-save-failure')
        saved=window._save_native_project(blocked)
        note('save_failure_keeps_original',not saved and native.context.dirty and native.context.path==before_path and before_path.read_bytes()==before)
        note('recovery_snapshot',window.recovery_native.autosave() is not None)
        note('recovery_copy_available',bool(RecoveryController.pending('4Tnative')))
        enter(editor.fields[('geometry','bore_mm')],'87');editor.apply();window._save_native_project()
        # A native curve cancellation must release its slot before another family.
        window.set_workspace_mode(2);native.simulation_pages.setCurrentIndex(1);curve=native.curve
        curve.start_rpm.setValue(6000);curve.end_rpm.setValue(6500);curve.step_rpm.setValue(500);curve.cycles.setValue(1);curve.wall.setValue(10)
        curve.start_curve();QTimer.singleShot(100,curve.cancel);wait(lambda:not curve.running)
        note('native_cancelled',bool(curve.manifest_path) if hasattr(curve,'manifest_path') else 'CANCELLED' in curve.status.text())
        capture('11-native-cancelled');window._save_native_project()
        # Existing real reference queue remains a reference workflow, never native evidence.
        window.show_four_stroke_mode();window.set_workspace_mode(0)
        geometry=window.four_stroke_workspace.geometry;enter(geometry.bore,'invalid');geometry.apply_button.click()
        note('reference_error_visible',bool(geometry.error.text()))
        enter(geometry.bore,'56');geometry.apply_button.click()
        window.four_stroke_context.path=root/'reference.json';note('reference_save',window.save_four_stroke_file())
        from .batch_queue import FourStrokeBatchQueue
        queue=FourStrokeBatchQueue(window.four_stroke_context,path=root/'reference-queue.json')
        queue.add_curve([2500,3000]);queue.start(120)
        wait(lambda:queue.state!='RUNNING',150)
        note('real_reference_queue',all(item['status']=='DONE' for item in queue.items))
        window.set_workspace_mode(2);capture('12-reference-queue')
        window.start_four_stroke_run();wait(lambda:not window.four_stroke_execution.running,120)
        note('real_reference_point',window.four_stroke_results.result is not None)
        window.set_workspace_mode(1);capture('13-reference-result');window.save_four_stroke_file()
        # Explicitly synthetic presentation endpoints supplied externally, read-only.
        window._open(args.fixtures/'comparison.json');window.set_workspace_mode(1)
        results=native.results;results.result_tabs.setCurrentWidget(results.compare_tab)
        results.compare_b.setCurrentIndex(1);note('eligible_pair_preflight',results.compare_button.isEnabled())
        results.compare_button.click();note('eligible_synthetic_comparison',results.comparison is not None)
        capture('14-synthetic-presentation-comparison')
        comparison=results.comparison
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(root/'comparison.pdf'),'')),patch('motorsim.desktop.four_stroke_desktop.QDesktopServices',SimpleNamespace(openUrl=lambda *_:True)):
            results.export_comparison_report_pdf()
        note('pdf_report',(root/'comparison.pdf').read_bytes().startswith(b'%PDF'))
        window._open(args.fixtures/'legacy.json')
        note('legacy_not_promoted',bool(native.results.legacy_loaded) and not native.results.loaded)
        note('legacy_comparison_disabled',not native.results.compare_button.isEnabled())
        window.set_workspace_mode(1);capture('15-legacy-preserved')
        # Four product licensing states, with an ephemeral test public key in memory.
        secret=os.urandom(32);public=ed25519.public_key(secret)
        for state in ('TRIAL','TRIAL_EXPIRED','INVALID_LICENSE','LICENSED'):
            license_root=root/('license-'+state);license_root.mkdir();os.environ['DINO_LICENSE_ROOT']=str(license_root)
            if state=='TRIAL_EXPIRED':
                (license_root/'trial.json').write_text(json.dumps(dict(schema='DINO_TRIAL_STATE_V1',started_at='2000-01-01T00:00:00+00:00',last_seen_at='2000-01-01T00:00:00+00:00')))
            elif state=='INVALID_LICENSE':(license_root/'license.json').write_text('{}')
            elif state=='LICENSED':
                payload=dict(schema='DINO_LICENSE_V1',product='Dino Desktop',license_type='PERPETUAL',activation='OFFLINE',license_id='acceptance-ephemeral',customer='Synthetic acceptance',issued_at=datetime.now(timezone.utc).isoformat())
                signed=root/'synthetic-acceptance.dinolicense';signed.write_text(json.dumps(licensing.sign_license(payload,secret,'acceptance-ephemeral')))
                from .license_dialog import LicenseDialog
                dialog=LicenseDialog(window,root=license_root,public_keys={'acceptance-ephemeral':public})
                answer('16-offline-activation');note('offline_activation',dialog.activate(signed));dialog.close()
            with patch.object(licensing,'VENDOR_PUBLIC_KEYS',{'acceptance-ephemeral':public}):
                status=licensing.license_status();window._refresh_license_label()
                note('license_state_'+state,status['state']==state and status['core_access_allowed'])
                note('save_allowed_'+state,window._save_native_project(root/(state+'.json')))
                capture('17-license-'+state)
        del secret
        update=root/'update.json';update.write_text(json.dumps(dict(schema='DINO_UPDATE_MANIFEST_V1',version='9.9.9',source_commit='a'*40,channel='engineering',zip_sha256='b'*64,dino2t_exe_sha256='c'*64,worker_exe_sha256='d'*64,released_at='2026-11-11T12:00:00+00:00')))
        answer('18-manual-update');note('manual_offline_update',window.check_for_updates(update))
        about=AboutDialog(product_info(),window);about.show();capture('19-about',about);about.close()
        from .onboarding import OnboardingDialog
        guide=OnboardingDialog(window);guide.show();capture('20-onboarding',guide);guide.close()
        diagnostic=create_diagnostics_bundle(root/'diagnostics.zip',include_project=True,project=native.context.project)
        note('diagnostic_zip',Path(diagnostic).is_file())
        window.resize(980,740);window.set_workspace_mode(0);capture('21-compact')
        note('context_all_families',window.project_header.isVisible())
        # Close and reopen the imported project in a new actual Qt window.
        imported_path=before_path
        for context in (window.context,window.four_stroke_context,native.context):context.dirty=False
        note('close_window',window.close());app.processEvents()
        window=DinoDesktopWindow(new_design_project('reopen-host'));window.show();window._open(imported_path)
        note('reopen_imported',window.native_four_stroke.context.engine()['geometry']['bore_mm']==87 and bool(window.native_four_stroke.results.loaded))
        capture('22-reopened')
        note('workers_idle',not window.native_four_stroke.running and window.pages[3].task is None and not window.four_stroke_execution.running and queue.state!='RUNNING')
    except Exception:
        issues.append(traceback.format_exc())
    finally:
        try:
            if queue is not None:queue.shutdown(10000)
            window.native_four_stroke.shutdown(15000)
            window.four_stroke_execution.shutdown(15000)
            if window.pages[3].task is not None:window.pages[3].cancel_run()
            QThreadPool.globalInstance().waitForDone(15000);app.processEvents()
            window.native_four_stroke.editor.discard_draft()
            window.four_stroke_workspace.refresh(window.four_stroke_context.project);window.experience.reference_loaded()
            for context in (window.context,window.four_stroke_context,window.native_four_stroke.context):context.dirty=False
            window.close();app.processEvents()
        except Exception:issues.append(traceback.format_exc())
    receipt=dict(schema='DINO_FRONTEND_COMMERCIAL_QT_ACCEPTANCE_V1',result='PASS' if checks and all(checks.values()) and not issues else 'FAIL',frozen=bool(getattr(sys,'frozen',False)),product=product_info(),qt_platform=app.platformName(),checks=checks,captures=captures,events=events,issues=issues,fixture_policy='Comparison endpoints synthetic presentation only; license keys ephemeral test-only; real bounded solver runs are integration evidence, not validation.',scientific_validation='NOT_PERFORMED',human_uat='PENDING_UAT')
    (root/'acceptance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=receipt['result'],receipt=str(root/'acceptance.json'),checks=len(checks),issues=issues),ensure_ascii=False))
    return 0 if receipt['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
