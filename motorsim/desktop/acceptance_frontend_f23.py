"""Maintainer acceptance through the real Windows application and public commands.

Presentation fixtures stay synthetic. Engineering runs are integration evidence.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,sys,time,traceback
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--fixtures',type=Path,required=True)
    args=parser.parse_args(argv);root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    for name,folder in (('DINO_ARTIFACT_ROOT','artifacts'),('DINO_RECOVERY_ROOT','recovery'),('DINO_TEST_SETTINGS_ROOT','settings'),('DINO_LICENSE_ROOT','license'),('LOCALAPPDATA','localappdata')):os.environ[name]=str(root/folder)
    from PySide6.QtCore import Qt,QEvent,QTimer,QThreadPool,QPointF
    from PySide6.QtGui import QKeyEvent,QMouseEvent
    from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox,QInputDialog
    from .app import DinoDesktopWindow
    from .services import new_design_project,_TASKS
    from .product import RecoveryController,product_info
    from .recovery_picker import RecoveryPicker
    app=QApplication.instance() or QApplication(['Dino F2 F3 Acceptance'])
    window=DinoDesktopWindow(new_design_project('f23-acceptance'));window.show()
    checks={};captures={};issues=[]
    def note(name,value):
        checks[name]=bool(value)
        if not value:raise AssertionError(name)
    def wait(predicate,seconds=120):
        end=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>end:raise TimeoutError('Application operation timed out')
            app.processEvents();time.sleep(.02)
        app.processEvents()
    def key(widget,value,mod=Qt.KeyboardModifier.NoModifier,text=''):
        widget.setFocus();app.sendEvent(widget,QKeyEvent(QEvent.Type.KeyPress,value,mod,text));app.sendEvent(widget,QKeyEvent(QEvent.Type.KeyRelease,value,mod,text));app.processEvents()
    def capture(name,target=None):
        for _ in range(3):app.processEvents();time.sleep(.02)
        path=root/(name+'.png');note('capture_'+name,(target or window).grab().save(str(path)))
        captures[name]=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    def clean():
        window.native_four_stroke.editor.discard_draft();window.pages[0].discard_draft();window.pages[1].discard_draft();window.four_stroke_workspace.refresh(window.four_stroke_context.project);window.experience.reference_loaded()
        for context in (window.context,window.native_four_stroke.context,window.four_stroke_context):context.dirty=False
    try:
        note('windows_platform',app.platformName()=='windows');window.resize(1360,820)
        navigator=window.experience.components;navigator.dock.show();navigator.activate('cylinder')
        key(navigator.map.buttons['ports'],Qt.Key.Key_Space)
        note('schematic_keyboard_routes_to_ports',window.component_nav.currentIndex()==1)
        window.component_nav.setCurrentIndex(7);note('editor_selection_updates_schematic',navigator.map.selected=='crankcase')
        capture('01-2t-components')
        # Actual serial queued workers, immutable snapshots, cancellation and reload.
        jobs=window.experience.jobs;manager=jobs.manager
        window.pages[3].cycles.setValue(1);window.pages[3].budget.setValue(30);note('queue_add_2t',jobs.enqueue_current())
        window.show_native_four_stroke_mode();window.native_four_stroke.simulation.cycles.setValue(1);window.native_four_stroke.simulation.wall.setValue(10);note('queue_add_native',jobs.enqueue_current())
        window.show_two_stroke_mode();note('queue_add_cancel_pending',jobs.enqueue_current());manager.cancel(manager.items[-1]['job_id'])
        def inspect_queue():capture('01b-point-queue',app.activeModalWidget());app.activeModalWidget().accept()
        QTimer.singleShot(50,inspect_queue);jobs.show();jobs.start()
        window.native_four_stroke.simulation.execute();note('queue_blocks_interactive_native',window.native_four_stroke.simulation.task is None)
        wait(lambda:manager.paused and not manager.running,150)
        note('real_serial_queue_completed',[i['status'] for i in manager.items]==['COMPLETED','COMPLETED','CANCELLED'])
        note('queue_results_bound',bool(window.context.project['result_references']) and bool(window.native_four_stroke.context.project['run_references']))
        from .engineering_jobs import EngineeringJobs
        loaded=json.loads(manager.path.read_text(encoding='utf-8'));note('queue_persistence',[(i['job_id'],i['configuration_sha256'],i['status']) for i in loaded['items']]==[(i['job_id'],i['configuration_sha256'],i['status']) for i in manager.items])
        window.show_native_four_stroke_mode();window.native_four_stroke.simulation.cycles.setValue(100);note('queue_add_cancel_active',jobs.enqueue_current());jobs.start();QTimer.singleShot(100,lambda:manager.cancel(manager.active_id) if manager.active_id else None)
        wait(lambda:not manager.running,30);note('real_active_queue_cancelled',manager.items[-1]['status']=='CANCELLED')
        note('queue_native_saved',window._save_native_project(root/'queued-native.json'))
        window.show_two_stroke_mode();window.context.path=root/'queued-two-stroke.json';note('queue_two_stroke_saved',window.save_file())
        initial_reference_count=len(window.context.project['result_references'])
        # Associate a real completed engineering run without rewriting or upgrading it.
        project=json.loads((args.baseline/'two-stroke.json').read_text(encoding='utf-8'));reference=project['result_references'][0];result_path=Path(reference['path']);original=result_path.read_bytes()
        with patch.object(QFileDialog,'getOpenFileNames',return_value=([str(result_path)],'')):window.experience.bind_external_result()
        wait(lambda:not _TASKS.tasks)
        note('external_result_bound',len(window.context.project['result_references'])==initial_reference_count+1)
        note('external_classification_preserved',window.context.project['result_references'][-1]['classification']==reference['classification'] and result_path.read_bytes()==original)
        errors=[];bad=root/'invalid';bad.mkdir();(bad/'result.json').write_text('{}')
        with patch.object(QFileDialog,'getOpenFileNames',return_value=([str(bad/'result.json')],'')),patch.object(QMessageBox,'warning',side_effect=lambda *a:errors.append(str(a[-1]))):
            window.experience.bind_external_result();wait(lambda:not _TASKS.tasks)
        note('invalid_external_result_rejected',bool(errors) and len(window.context.project['result_references'])==initial_reference_count+1)
        window.context.path=root/'bound-2t.json';note('bound_project_saved',window.save_file())
        window.set_workspace_mode(1);navigator.dock.hide();window.results.open_runs([str(result_path.parent)]);wait(lambda:not _TASKS.tasks and window.results.dataset is not None)
        window.results.power_curves.exploratory_toggle.setChecked(True)
        explorer=window.results.power_curves.sample_plot;window.results.power_curves.view_selector.setCurrentIndex(2)
        note('qualified_power_explorer_available',bool(explorer.sample_rows()))
        if explorer._points():
            original_point=explorer._points()[0][2];key(explorer,Qt.Key.Key_Right);note('2t_exact_sample_cursor',explorer.selected is not None and str(original_point['value']) in explorer.readout.text())
        explorer.write_samples(root/'two-stroke-samples.csv');note('real_samples_csv',(root/'two-stroke-samples.csv').is_file())
        capture('02-2t-explorer')
        window.results.result_tabs.setCurrentIndex(2);trace=window.results.trace_plot
        note('real_trace_available',bool(trace._points()))
        values=deepcopy(trace.series);key(trace,Qt.Key.Key_Right);before=trace._axis_ranges(trace._points());key(trace,Qt.Key.Key_Plus);after=trace._axis_ranges(trace._points())
        note('trace_keyboard_zoom_preserves_data',after[1]-after[0]<before[1]-before[0] and trace.series==values)
        key(trace,Qt.Key.Key_Home);note('trace_reset',trace._viewport is None)
        bounds=trace._axis_ranges(trace._points());center=QPointF(trace.rect().center())
        app.sendEvent(trace,QMouseEvent(QEvent.Type.MouseButtonPress,center,Qt.MouseButton.MiddleButton,Qt.MouseButton.MiddleButton,Qt.KeyboardModifier.NoModifier))
        app.sendEvent(trace,QMouseEvent(QEvent.Type.MouseMove,center+QPointF(25,10),Qt.MouseButton.NoButton,Qt.MouseButton.MiddleButton,Qt.KeyboardModifier.NoModifier))
        app.sendEvent(trace,QMouseEvent(QEvent.Type.MouseButtonRelease,center+QPointF(25,10),Qt.MouseButton.MiddleButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier))
        note('trace_pan_preserves_original_samples',trace._viewport is not None and trace._viewport[0]!=bounds[0] and trace.series==values)
        key(trace,Qt.Key.Key_Home)
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(root/'trace-export.png'),'')):trace.export_image()
        note('trace_png_export',(root/'trace-export.png').read_bytes().startswith(b'\x89PNG'))
        capture('03-2t-trace-cursor')
        def inspect_expanded():
            modal=app.activeModalWidget();plot=modal.findChild(type(trace));key(plot,Qt.Key.Key_Right);note('expanded_cursor_has_visible_values',bool(plot.readout.text()) and plot.readout.isVisible());capture('03b-expanded-trace',modal);modal.accept()
        QTimer.singleShot(50,inspect_expanded);trace.show_expanded()
        # Native linked selection, rename, history, exact differences, and eligible A/B.
        window._open(args.baseline/'native.json');window.set_workspace_mode(0);navigator.dock.show();navigator.activate('exhaust_valve')
        native=window.native_four_stroke;note('native_component_route',native.editor.sections.currentIndex()==list(native.editor.tables).index('exhaust_valve'))
        native.context.duplicate_variant(None,'variant-before');native.context.select_variant('variant-before');refs=deepcopy(native.context.project['run_references'])
        with patch.object(QInputDialog,'getText',return_value=('variant-after',True)):native.rename_variant()
        note('native_rename_and_references',native.context.selected_variant=='variant-after' and native.context.project['run_references']==refs)
        window._undo_active();note('native_rename_undo','variant-before' in native.context.project['variants']);window._redo_active()
        capture('04-native-components')
        note('native_variants_saved',window._save_native_project(root/'native-variants.json'))
        navigator.dock.hide();window._open(args.fixtures/'comparison.json');window.set_workspace_mode(1);results=native.results
        results.result_tabs.setCurrentWidget(results.compare_tab);results.compare_b.setCurrentIndex(1);results.compare_button.click()
        note('eligible_ab_overlay',results.comparison is not None and len(results.compare_pressure.series)==2)
        note('synthetic_origin_visible',all('SYNTHETIC' in str(p) for s in results.compare_pressure.series for p in s['points']))
        results.compare_views.setCurrentIndex(1);key(results.compare_pressure,Qt.Key.Key_Right);capture('05-native-ab-pressure')
        def inspect_ab():
            modal=app.activeModalWidget();plot=modal.findChild(type(results.compare_pressure));key(plot,Qt.Key.Key_Right);capture('05b-expanded-ab',modal);modal.accept()
        QTimer.singleShot(50,inspect_ab);results.compare_pressure.show_expanded()
        results.compare_b.setCurrentIndex(results.compare_a.currentIndex());note('same_run_pair_rejected',not results.compare_button.isEnabled() and not results.compare_pressure.series)
        # Real reference execution remains independent from native.
        window._open(args.baseline/'reference.json');window.set_workspace_mode(0);navigator.dock.show();navigator.activate('intake_valve')
        note('reference_component_route',window.four_stroke_workspace.tabs.currentIndex()==1 and 'sintética' in navigator.family.text())
        capture('06-reference-components');navigator.dock.hide();window.start_four_stroke_run();wait(lambda:not window.four_stroke_execution.running)
        reference_plot=window.four_stroke_results.angle;note('reference_actual_samples',bool(reference_plot._points()));window.set_workspace_mode(1);key(reference_plot,Qt.Key.Key_Right);capture('07-reference-cursor')
        # Reference0D is a dataclass: each named project must retain its own draft.
        from ..four_stroke_project import starter_project
        previous_reference=deepcopy(window.four_stroke_context.project);previous_path=window.four_stroke_context.path;draft_paths=[]
        for name in ('Recuperación referencia A','Recuperación referencia B'):
            window.four_stroke_context.replace_project(starter_project(name=name,rpm=3000),None);window.four_stroke_context.dirty=True
            draft_paths.append(window.recovery_4t.autosave());window.four_stroke_context.dirty=False
        note('reference_projects_have_distinct_recovery_paths',draft_paths[0]!=draft_paths[1] and all(path.exists() for path in draft_paths))
        note('reference_recovery_keeps_names',{'Recuperación referencia A','Recuperación referencia B'}.issubset({e['project_id'] for e in RecoveryController.pending('4T0D')}))
        window.four_stroke_context.replace_project(previous_reference,previous_path)
        # Compact resolutions and controls: actual application layouts, not isolated widgets.
        for family,switch in (('2t',window.show_two_stroke_mode),('native',window.show_native_four_stroke_mode),('reference',window.show_four_stroke_mode)):
            switch();navigator.dock.hide()
            for width,height in ((980,680),(1280,720)):
                window.resize(width,height);window.set_workspace_mode(0);app.processEvents()
                note(f'{family}_{width}_actual_size',window.width()<=width and window.height()<=height)
                note(f'{family}_{width}_header',window.project_header.isVisible() and window.project_header.geometry().width()<=window.centralWidget().width())
                capture(f'08-{family}-{width}')
        # Recovery preview in the actual application. Deferred drafts survive.
        clean();window._open(root/'native-variants.json');window.show_two_stroke_mode();window.context.path=root/'bound-2t.json'
        window.show_native_four_stroke_mode();native.context.path=root/'native-variants.json'
        controllers=(window.recovery_2t,window.recovery_native,window.recovery_4t)
        for controller in controllers:controller.context.dirty=True;controller.autosave();controller.context.dirty=False
        entries=[e for family in ('2T','4T0D','4Tnative') for e in RecoveryController.pending(family)]
        originals={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'bound-2t.json',root/'native-variants.json')}
        def defer():
            picker=app.activeModalWidget();note('recovery_selector_is_real_dialog',isinstance(picker,RecoveryPicker));note('recovery_all_families',picker.table.rowCount()>=3);picker.table.selectRow(1);note('recovery_preview',bool(picker.preview.toPlainText()));capture('09-recovery-preview',picker);picker.reject()
        QTimer.singleShot(50,defer);window._offer_recoveries()
        note('defer_preserves_all_drafts',len([e for family in ('2T','4T0D','4Tnative') for e in RecoveryController.pending(family)])==len(entries))
        def recover():
            picker=app.activeModalWidget();index=next(i for i,e in enumerate(picker.entries) if e['family']=='4Tnative');picker.table.selectRow(index);picker.open_button.click()
        QTimer.singleShot(50,recover);window._offer_recoveries()
        note('recovery_copy_has_no_original_path',native.context.path is None and native.context.dirty)
        with patch.object(QFileDialog,'getSaveFileName',return_value=('','')):note('recovery_save_as_cancelled',not window.save_file())
        note('recovery_original_bytes_intact',all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in originals.items()))
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(root/'recovered-copy.json'),'')):note('recovered_copy_saved',window.save_file())
        clean();note('window_closed',window.close());app.processEvents()
        window=DinoDesktopWindow(new_design_project('reopen-f23'));window.show()
        QTimer.singleShot(50,lambda:app.activeModalWidget().reject() if isinstance(app.activeModalWidget(),RecoveryPicker) else None)
        app.processEvents();window._open(root/'recovered-copy.json')
        note('queue_reopens_after_window_close',window.experience.jobs.manager is not None and len(window.experience.jobs.manager.items)>=4 and window.experience.jobs.manager.paused)
        note('recovery_persistence_reopen',window.native_four_stroke.context.path==root/'recovered-copy.json' and 'variant-after' in window.native_four_stroke.context.project['variants'])
    except Exception:issues.append(traceback.format_exc())
    finally:
        try:
            window.native_four_stroke.shutdown(15000);window.four_stroke_execution.shutdown(15000);QThreadPool.globalInstance().waitForDone(15000);clean();window.close();app.processEvents()
        except Exception:issues.append(traceback.format_exc())
    receipt=dict(schema='DINO_FRONTEND_F23_APPLICATION_ACCEPTANCE_V1',result='PASS' if checks and all(checks.values()) and not issues else 'FAIL',frozen=bool(getattr(sys,'frozen',False)),product=product_info(),checks=checks,captures=captures,issues=issues,human_uat='PENDING_UAT',scientific_validation='NOT_PERFORMED',fixture_policy='Real engineering integration runs plus explicitly synthetic native comparison fixtures; no experimental claims.')
    (root/'acceptance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result=receipt['result'],checks=len(checks),issues=issues),ensure_ascii=False))
    return 0 if receipt['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
