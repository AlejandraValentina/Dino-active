"""Read-only real Desktop demonstration of the completed scoped continuations."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--artifacts',type=Path,required=True)
p.add_argument('--captures',type=Path,required=True)
a=p.parse_args();a.captures.mkdir(parents=True,exist_ok=True)
os.environ['DINO_ARTIFACT_ROOT']=str(a.artifacts)
os.environ['DINO_TEST_SETTINGS_ROOT']=str(a.artifacts/'desktop-settings')
from PySide6.QtCore import QTimer,QItemSelectionModel
from PySide6.QtWidgets import QApplication,QScrollArea
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.engine_project import load_project

app=QApplication([]);project_path=a.artifacts/'periodic-rpm-curves.dino.json'
window=DinoDesktopWindow(load_project(project_path));window.context.path=project_path
window.resize(1360,900);window.show();window.context.select_variant('B_header_plus20')
window.results.baseline_selector.setCurrentIndex(window.results.baseline_selector.findData('A_original'))
pre=json.loads((a.artifacts/'preflight.json').read_bytes())
old_paths={str(Path(s['result']).parent.resolve()) for s in pre['sources']}
new_root=a.artifacts.resolve()
state={'phase':'activate'};start=time.monotonic();receipt=dict(schema='DINO_PERIODIC_CURVE_DESKTOP_VIEW_V1',solver_steps=0,captures=[],loads=[])


def capture(name,widget):
    path=a.captures/name;assert widget.grab().save(str(path));receipt['captures'].append(str(path))


def select(periodic):
    if not window.analysis_history.isVisible():window.history_toggle.click()
    history=window.analysis_history;model=history.table.selectionModel();model.clearSelection();chosen=[]
    for i,e in enumerate(history.entries):
        path=Path(e['run_directory']).resolve()
        include=path.is_relative_to(new_root) if periodic else str(path) in old_paths
        if include:
            model.select(history.table.model().index(i,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
            chosen.append(e)
    assert len(chosen)==6,[(e['variant'],e['rpm'],e['status']) for e in chosen]
    receipt['loads'].append(dict(kind='continued' if periodic else 'cycle30',runs=[e['run_directory'] for e in chosen]))
    window.results.dataset=None;history.open_button.click()


def tick():
    try:
        if time.monotonic()-start>240:raise TimeoutError('read-only Desktop load budget240s')
        phase=state['phase']
        if phase=='activate':
            window.set_workspace_mode(1);window.analysis_history.activate();window.analysis_history.refresh();state['phase']='select-new'
        elif phase=='select-new':
            if len(window.analysis_history.entries)<12:return
            select(True);state['phase']='new-loaded'
        elif phase=='new-loaded' and window.results.dataset:
            panel=window.results.power_curves;panel.exploratory_toggle.setChecked(True);app.processEvents()
            assert len(panel.rows)==6
            receipt['displayed_points']=[dict(variant=p['row']['variant_id'],rpm=p['rpm'],power=p['power'],torque=p['torque'],
                periodicity=p['periodicity'],classification=p['classification'],exploratory=p['exploratory']) for p in panel.rows]
            panel.points.selectRow(0);app.processEvents()
            capture('01-periodic-power-torque.png',panel.plot)
            capture('02-periodic-point-table.png',panel.points)
            capture('03-equal-rpm-comparison.png',panel.comparison)
            if window.analysis_history.isVisible():window.history_toggle.click()
            for scroll in window.findChildren(QScrollArea):
                if scroll.widget() is not None and scroll.widget().isAncestorOf(panel):
                    scroll.ensureWidgetVisible(panel.plot,0,0)
            app.processEvents()
            capture('04-desktop-periodic-curves.png',window)
            panel.export_csv(a.artifacts/'continued-power-torque.csv')
            index=window.results.trace_metric.findData('duct:exhaust:cell:0:pressure_pa')
            assert index>=0,'exhaust pressure channel missing'
            window.results.trace_metric.setCurrentIndex(index)
            for rpm in (8000,9000,10000):
                window.results.trace_rpm.setCurrentIndex(window.results.trace_rpm.findData(rpm));app.processEvents()
                assert len(window.results.trace_plot.series)==2
                capture(f'pressure-{rpm}.png',window.results.trace_group)
            panel.exploratory_toggle.setChecked(False);app.processEvents()
            assert all(p['power'] is None or not p['exploratory'] for c in panel.curves for p in c['points'])
            capture('05-periodic-only.png',panel.plot)
            state['phase']='select-old'
        elif phase=='select-old':
            window.analysis_history.activate();window.analysis_history.refresh();select(False);state['phase']='old-loaded'
        elif phase=='old-loaded' and window.results.dataset:
            panel=window.results.power_curves;panel.exploratory_toggle.setChecked(True);app.processEvents()
            assert len(panel.rows)==6 and all(p['exploratory'] for p in panel.rows)
            capture('06-original-exploratory-curves.png',panel.plot)
            panel.export_csv(a.artifacts/'original-cycle30-power-torque.csv')
            receipt['exploratory_history_preserved']=True;state['phase']='reload-new'
        elif phase=='reload-new':
            select(True);state['phase']='finish'
        elif phase=='finish' and window.results.dataset:
            assert len(window.results.power_curves.rows)==6
            receipt['saved_project_reopened']=True;receipt['wall_s']=time.monotonic()-start
            (a.artifacts/'desktop-view-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
            print(json.dumps(receipt,ensure_ascii=False),flush=True);app.quit()
    except BaseException as exc:
        (a.artifacts/'desktop-view-error.txt').write_text(repr(exc),encoding='utf-8');print(repr(exc),flush=True);app.exit(1)


timer=QTimer();timer.timeout.connect(tick);timer.start(500)
raise SystemExit(app.exec())
