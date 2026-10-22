"""Drive existing Desktop sweep dialogs and history for owner-authorized delivery2B.

No solver mocks, replacement coordinator, or separate plotting implementation.
The prepared project explicitly references the two immutable9000RPM results.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--view-only',action='store_true');args=p.parse_args()
os.environ['DINO_ARTIFACT_ROOT']=str(args.artifacts)
os.environ['DINO_TEST_SETTINGS_ROOT']=str(args.artifacts/'settings')
from PySide6.QtCore import QTimer,QItemSelectionModel
from PySide6.QtWidgets import QApplication,QDialog,QSpinBox,QCheckBox,QMessageBox
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.engine_project import load_project
from motorsim.desktop.run_history import list_project_runs

app=QApplication([]);window=DinoDesktopWindow(load_project(args.artifacts/'rpm-curves.dino.json'))
window.context.path=args.artifacts/'rpm-curves.dino.json';window.resize(1360,900);window.show()
execution=window.pages[3];start=time.monotonic()
state=dict(phase='history' if args.view_only else 'startA',confirmed=set())
receipt=dict(schema='DINO_DESKTOP_RPM_CURVE_DEMO_V1',solver_mocked=False,grid=[8000,9000,10000],new_point_cap_s=300,variant_aggregate_cap_s=650,memory_mib=512,sequential=True,series=[])


def dialogs():
    for w in app.topLevelWidgets():
        if isinstance(w,QDialog) and w.isVisible() and w.windowTitle()=='Preparar curva RPM · EXPLORATORY':
            for name,value in [('curveStartRpm',8000),('curveStopRpm',10000),('curveStepRpm',1000),('curveCycles',30),('curvePointBudget',300),('curveTotalBudget',650),('curveMemory',512)]:
                w.findChild(QSpinBox,name).setValue(value)
            w.findChild(QCheckBox,'curveReuseCompleted').setChecked(True)
            w.findChild(QCheckBox,'curveOpenEndpointHold').setChecked(True)
            w.accept()
        elif isinstance(w,QMessageBox) and w.isVisible():
            if w.windowTitle()=='Confirmar barrido RPM':
                import ast
                reused=ast.literal_eval(w.text().split('Reutilizar sin cálculo: ',1)[1].split(' RPM',1)[0])
                if reused!=[9000]:
                    state['error']='9000 reuse missing from confirmation';w.done(QMessageBox.StandardButton.No);continue
                state['confirmed'].add(window.context.selected_variant)
                w.grab().save(str(args.artifacts/f"confirmation-{window.context.selected_variant}.png"))
                w.button(QMessageBox.StandardButton.Yes).click()
            else:
                state['error']=w.windowTitle()+': '+w.text();w.reject()


def capture(name,widget):
    app.processEvents();widget.grab().save(str(args.artifacts/name))


def tick():
    try:
        if state.get('error'):raise RuntimeError(state['error'])
        phase=state['phase']
        if phase in ('startA','startB'):
            variant='A_original' if phase=='startA' else 'B_header_plus20'
            window.context.select_variant(variant)
            execution.rpm.setValue(9000);execution.cycles.setValue(30);execution.budget.setValue(300);execution.memory.setValue(512)
            execution.refresh()
            assert execution.sweep.isEnabled(),execution.preflight_label.text()
            window.results.baseline_selector.setCurrentIndex(window.results.baseline_selector.findData('A_original'))
            entries=list_project_runs(window.context.project,args.artifacts);execution.set_history_entries(entries)
            eligible=[e for e in entries if e['variant']==variant and e['status']=='COMPLETE']
            assert [e['rpm'] for e in eligible]==[9000],eligible
            state['phase']='waitA' if phase=='startA' else 'waitB'
            execution.sweep.click()
        elif phase in ('waitA','waitB') and execution.task is None:
            variant='A_original' if phase=='waitA' else 'B_header_plus20'
            files=list((args.artifacts/'dino-power-curve-v1'/window.context.project['project_id']).glob('*/series.json'))
            found=[(path,json.loads(path.read_text())) for path in files if json.loads(path.read_text())['bindings']['variant_label']==variant]
            assert len(found)==1,execution.output.toPlainText()[-2500:]
            path,series=found[0]
            assert variant in state['confirmed'] and series['status']!='FAILED_CLOSED',series
            reused=[point for point in series['points'] if point.get('reused')]
            assert len(reused)==1 and reused[0]['rpm']==9000
            receipt['series'].append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),variant=variant,status=series['status'],elapsed_s=series['elapsed_seconds'],points=series['points']))
            assert sum(s['elapsed_s'] for s in receipt['series'])<=1300
            assert window.save_file()
            print(json.dumps(dict(completed_variant=variant,status=series['status'],elapsed_s=series['elapsed_seconds'])),flush=True)
            state['phase']='startB' if phase=='waitA' else 'history'
        elif phase=='history':
            window.context.select_variant('B_header_plus20');window.results.baseline_selector.setCurrentIndex(window.results.baseline_selector.findData('A_original'))
            window.set_workspace_mode(1);window.analysis_history.activate();window.analysis_history.refresh();state['phase']='select'
        elif phase=='select':
            history=window.analysis_history
            if len(history.entries)<6:return
            assert len(history.entries)==6
            model=history.table.selectionModel();model.clearSelection()
            for i in range(len(history.entries)):model.select(history.table.model().index(i,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
            history.open_button.click();state['phase']='loaded'
        elif phase=='loaded' and window.results.dataset:
            panel=window.results.power_curves
            assert len(panel.rows)==6
            values=[p for c in panel.curves for p in c['points'] if p['power'] is not None]
            assert values and all(p['exploratory'] or p['row'].get('brake_power_status')=='DEFINED' for p in values)
            panel.points.selectRow(0);app.processEvents()
            capture('01-power-torque-curves.png',panel.plot)
            capture('02-rpm-points.png',panel.points)
            capture('03-equal-rpm-deltas.png',panel.comparison)
            capture('04-global-and-observed-stability.png',panel.stability_notice)
            capture('05-desktop-results.png',window)
            receipt['displayed_points']=[dict(variant=p['row']['variant_id'],rpm=p['rpm'],power=p['power'],torque=p['torque'],unit=panel.unit_selector.currentData(),exploratory=p.get('exploratory'),status=p['row']['classification'],periodicity=p['row']['periodicity']) for p in panel.rows]
            for rpm in [8000,9000,10000]:
                window.results.trace_rpm.setCurrentIndex(window.results.trace_rpm.findData(rpm));app.processEvents()
                assert len(window.results.trace_plot.series)==2
                capture(f'pressure-{rpm}.png',window.results.trace_group)
            panel.export_csv(args.artifacts/'exploratory-power-torque.csv')
            panel.exploratory_toggle.setChecked(False);app.processEvents()
            assert all(p['power'] is None or not p.get('exploratory') for c in panel.curves for p in c['points'])
            capture('06-periodic-only.png',panel.plot);panel.exploratory_toggle.setChecked(True)
            if not args.view_only:
                window.results.dataset=None;window._open(window.context.path);state['phase']='reopen'
            else:state['phase']='finish'
        elif phase=='reopen':
            window.context.select_variant('B_header_plus20');window.set_workspace_mode(1);window.analysis_history.refresh();state['phase']='select-reopened'
        elif phase=='select-reopened':
            if len(window.analysis_history.entries)!=6:return
            model=window.analysis_history.table.selectionModel();model.clearSelection()
            for i in range(6):model.select(window.analysis_history.table.model().index(i,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
            window.analysis_history.open_button.click();state['phase']='verify-reopened'
        elif phase=='verify-reopened' and window.results.dataset:
            assert len(window.results.power_curves.rows)==6
            receipt['saved_project_reopened_six_results']=True;state['phase']='finish'
        elif phase=='finish':
            receipt['wall_s']=time.monotonic()-start
            target='desktop-view-receipt.json' if args.view_only else 'desktop-execution-receipt.json'
            (args.artifacts/target).write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
            print(json.dumps(receipt,ensure_ascii=False),flush=True);app.quit()
        if time.monotonic()-start>1500:raise TimeoutError('Desktop overall guard1500s; no new campaign')
    except BaseException as exc:
        (args.artifacts/'desktop-error.txt').write_text(repr(exc),encoding='utf-8');print(repr(exc),flush=True)
        if execution.cancel_event is not None:execution.cancel_event.set()
        app.exit(1)


dialog_timer=QTimer();dialog_timer.timeout.connect(dialogs);dialog_timer.start(100)
timer=QTimer();timer.timeout.connect(tick);timer.start(500)
raise SystemExit(app.exec())
