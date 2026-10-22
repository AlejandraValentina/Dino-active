"""Authorized Desktop interaction demonstration; no alternative simulation service.

Duplicates through project dialog, edits through exhaust table, invokes existing
execution buttons, selects two history rows and saves/reopens their comparison.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser();parser.add_argument('--artifacts',type=Path,required=True)
parser.add_argument('--view-only',action='store_true');args=parser.parse_args()
os.environ['DINO_ARTIFACT_ROOT']=str(args.artifacts)
os.environ['DINO_TEST_SETTINGS_ROOT']=str(args.artifacts/'settings')
from PySide6.QtCore import QTimer,QItemSelectionModel
from PySide6.QtWidgets import QApplication,QMessageBox,QInputDialog
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.engine_project import load_project,save_project
from motorsim.engine_variants import escape_sections,compare_configurations

args.artifacts.mkdir(parents=True,exist_ok=True)
app=QApplication([])
project_path=args.artifacts/'exhaust-comparison.dino.json'
window=DinoDesktopWindow(load_project(project_path if args.view_only else ROOT/'configs/reference_cases/functional_reed_125cc_v1.dino.json'))
window.resize(1360,900);window.show();execution=window.pages[3]
start=time.monotonic();state={'phase':'history' if args.view_only else 'duplicateA','names':['A_original','B_header_plus20'],'recovered':False}
run_paths=[args.artifacts/'exploratory-workflow-v1/functional-reed-125cc-v1'/name for name in ('ab-A-9000','ab-B-9000')]
receipt={'scope':'DELIVERY2_ENGINEERING_AB_ONLY','solver_steps_mocked':False,'interaction':[]}


def dialog_tick():
    for widget in app.topLevelWidgets():
        if isinstance(widget,QInputDialog) and widget.isVisible():
            widget.setTextValue(state['names'].pop(0));widget.accept()
        elif isinstance(widget,QMessageBox) and widget.isVisible():
            if widget.windowTitle()=='Confirmación de ejecución':
                next(b for b in widget.buttons() if widget.buttonRole(b)==QMessageBox.ButtonRole.AcceptRole).click()
            else:
                state['error']=widget.windowTitle()+': '+widget.text();widget.reject()


def capture(name,widget=None):
    app.processEvents();(widget or window).grab().save(str(args.artifacts/name))


def tick():
    try:
        if state.get('error'):raise RuntimeError(state['error'])
        phase=state['phase']
        if phase=='duplicateA':
            state['phase']='duplicateB';window.context.select_variant(None)
            window.component_nav.setCurrentIndex(5);window.pages[2].duplicate.click()
            assert window.context.selected_variant=='A_original'
            receipt['interaction'].append('duplicate A through existing dialog')
        elif phase=='duplicateB':
            state['phase']='edit';window.pages[2].duplicate.click()
            assert window.context.selected_variant=='B_header_plus20'
        elif phase=='edit':
            window.component_nav.setCurrentIndex(2);page=window.pages[1]
            page.table.item(0,1).setText('103.0');page.save_current_button.click()
            assert escape_sections(window.context.engine())[0]['length_mm']==103
            assert len(next(d for d in window.context.engine()['native_configuration']['ducts'] if d['id']=='exhaust')['mesh']['volumes'])==31
            receipt['geometry_changes']=compare_configurations(window.context.project['variants']['A_original'],window.context.engine())
            window.context.path=project_path;assert window.save_file()
            capture('01-edited-exhaust.png');receipt['interaction'].append('table edit header83to103mm and save existing variant')
            state['phase']='startA'
        elif phase in ('startA','startB'):
            index=0 if phase=='startA' else 1
            window.context.select_variant(('A_original','B_header_plus20')[index])
            execution.rpm.setValue(9000);execution.cycles.setValue(30);execution.budget.setValue(300);execution.memory.setValue(512)
            execution.run_id.setText(('ab-A-9000','ab-B-9000')[index])
            assert execution.start.isEnabled(),execution.preflight_label.text()
            state['phase']='waitA' if index==0 else 'waitB'
            execution.start.click();receipt['interaction'].append('existing execution start '+str(index))
        elif phase in ('waitA','waitB') and execution.task is None:
            index=0 if phase=='waitA' else 1
            if not (run_paths[index]/'result.json').exists():raise RuntimeError(execution.output.toPlainText()[-2500:])
            result=json.loads((run_paths[index]/'result.json').read_text())
            if result['status']=='FAILED_CLOSED':raise RuntimeError(result.get('failure'))
            receipt[('A','B')[index]]=dict(classification=result['classification'],cycles=result['cycles_completed'],elapsed_seconds=result['elapsed_seconds'],periodicity=result['periodicity'])
            print(json.dumps({('A','B')[index]:receipt[('A','B')[index]]}),flush=True)
            state['phase']='startB' if index==0 else 'history'
        elif phase=='history':
            window.context.select_variant('B_header_plus20')
            window.results.baseline_selector.setCurrentIndex(window.results.baseline_selector.findData('A_original'))
            window.set_workspace_mode(1);window.analysis_history.activate();window.analysis_history.refresh();state['phase']='select'
        elif phase=='select':
            history=window.analysis_history
            if len(history.entries)!=2:return
            model=history.table.selectionModel();model.clearSelection()
            for i in range(2):model.select(history.table.model().index(i,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
            assert history.compare_button.isEnabled()
            history.compare_button.click();state['phase']='loaded'
            receipt['interaction'].append('select two history rows and compare')
        elif phase=='loaded' and window.results.dataset:
            assert len(window.results.dataset['points'])==2
            assert len(window.results.trace_plot.series)==2
            window.results.show_point(window.results.dataset['points'][0])
            window.results.baseline_selector.setCurrentIndex(window.results.baseline_selector.findData('A_original'))
            window.results._update_engineering_compare()
            capture('02-comparison.png');capture('03-pressure-overlay.png',window.results.trace_group)
            capture('04-engineering-differences.png',window.results.compare_group)
            window.results.compare_table.scrollToBottom()
            capture('06-transient-comparison.png',window.results.compare_group)
            index=window.results.trace_metric.findData('duct:exhaust:face:0:mass_flow_kg_s')
            window.results.trace_metric.setCurrentIndex(index);capture('05-flow-overlay.png',window.results.trace_group)
            receipt['comparison_notice']=window.results.compare_notice.text()
            receipt['plotted_series']=len(window.results.trace_plot.series)
            receipt['visible_comparison']=[[window.results.compare_table.item(i,j).text() for j in range(5)] for i in range(window.results.compare_table.rowCount())]
            if args.view_only:
                state['phase']='finish'
            else:
                assert window.analysis_history.save_comparison()
                assert window.save_file()
                window.results.dataset=None
                window._open(project_path)
                state['phase']='recover'
        elif phase=='recover':
            assert window.analysis_history.restore_comparison()
            receipt['interaction'].append('reopen saved project and recover hash-bound comparison')
            state['phase']='recovered'
        elif phase=='recovered' and window.results.dataset:
            assert len(window.results.dataset['points'])==2
            receipt['saved_comparison_recovered']=True;state['phase']='finish'
        elif phase=='finish':
            receipt['wall_s']=time.monotonic()-start
            (args.artifacts/'desktop-comparison-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
            print(json.dumps(receipt,ensure_ascii=False),flush=True);app.quit()
        if time.monotonic()-start>650:raise TimeoutError('Desktop A/B demonstration guard')
    except BaseException as exc:
        (args.artifacts/'desktop-error.txt').write_text(repr(exc),encoding='utf-8')
        print(repr(exc),flush=True)
        if execution.cancel_event is not None:execution.cancel_event.set()
        app.exit(1)


dialogs=QTimer();dialogs.timeout.connect(dialog_tick);dialogs.start(100)
timer=QTimer();timer.timeout.connect(tick);timer.start(400)
raise SystemExit(app.exec())
