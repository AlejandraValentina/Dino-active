"""F2/F3 interaction contracts. Presentation fixtures are explicitly synthetic."""
import os,csv,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import desktop_qsettings_isolation
import pytest
from copy import deepcopy
from PySide6.QtWidgets import QApplication,QInputDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from motorsim.desktop.plot import CurvePlot
from motorsim.desktop.four_stroke_results import FourStrokeCurve
from motorsim.desktop.recovery_picker import RecoveryPicker
from motorsim.desktop.variant_explorer import differences
from motorsim.desktop.app import DinoDesktopWindow

APP=QApplication.instance() or QApplication([])

def key(widget,value):
    APP.sendEvent(widget,QKeyEvent(QKeyEvent.Type.KeyPress,value,Qt.KeyboardModifier.NoModifier))


def test_cursor_uses_exact_samples_across_duplicate_names_and_gaps(tmp_path):
    plot=CurvePlot();samples=[dict(rpm=1000,value=3.141592653589793,status='SYNTHETIC_PRESENTATION'),dict(rpm=1500,value=None,reason='NOT_CONVERGED'),dict(rpm=2000,value=5.0)]
    second=dict(rpm=1300,value=99.0)
    plot.set_series([dict(name='A',unit='kW',connect=False,points=samples),dict(name='A',unit='kW',points=[second])])
    selected=[];plot.pointSelected.connect(selected.append)
    for _ in range(3):key(plot,Qt.Key.Key_Right)
    assert selected==[samples[0],samples[2],second]
    assert selected[0] is samples[0]
    assert '99.0 kW' in plot.readout.text()
    plot.write_samples(tmp_path/'samples.csv')
    with open(tmp_path/'samples.csv',encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==4 and rows[1]['value']=='' and rows[1]['status_or_reason']=='NOT_CONVERGED'
    assert json.loads(rows[0]['original_sample_json'])==samples[0]


def test_viewport_changes_no_values_or_contract():
    plot=CurvePlot();series=[dict(name='A',connect=False,unit='Pa',points=[dict(rpm=1,value=5),dict(rpm=3,value=9)])];before=deepcopy(series)
    plot.set_series(series);initial=plot._axis_ranges(plot._points());plot.zoom(.5)
    zoomed=plot._axis_ranges(plot._points())
    assert zoomed[1]-zoomed[0]==pytest.approx((initial[1]-initial[0])/2)
    assert series==before and plot.series[0]['connect'] is False
    key(plot,Qt.Key.Key_Home);assert plot._viewport is None
    assert plot._axis_ranges(plot._points())==initial


def test_native_tuple_adapter_never_connects_forbidden_points():
    plot=FourStrokeCurve('Native','RPM','kW');plot.connect_points=False
    plot.set_points([(1000,2),(1500,None),(2000,3)])
    assert not plot.series[0]['connect'] and len(plot.sample_rows())==3
    plot.resize(700,350);plot.grab();assert plot._points()[0][2]['value']==2


def test_recovery_preview_selection_and_defer_do_not_mutate():
    entries=[dict(family='2T',project_id='one',saved_at='2026-11-12',original_path='one.json',project={'value':1}),dict(family='4Tnative',project_id='two',project={'value':2})]
    before=deepcopy(entries);picker=RecoveryPicker(entries);picker.table.selectRow(1)
    assert '2' in picker.preview.toPlainText()
    picker.reject();assert picker.selected_entry is None and entries==before
    picker.open_selected();assert picker.selected_entry==entries[1] and entries==before


def test_exact_variant_differences_preserve_precision_and_array_paths():
    assert differences({'a':[1,2],'float':1.00000000000001},{'a':[1,3],'float':1.00000000000002})==[('a.1',2,3),('float',1.00000000000001,1.00000000000002)]


@pytest.fixture(scope='module')
def window(tmp_path_factory):
    root=tmp_path_factory.mktemp('f23');os.environ['DINO_ARTIFACT_ROOT']=str(root/'artifacts');os.environ['DINO_RECOVERY_ROOT']=str(root/'recovery')
    w=DinoDesktopWindow();w.show();APP.processEvents()
    yield w
    w.native_four_stroke.editor.discard_draft();w.pages[0].discard_draft();w.pages[1].discard_draft();w.four_stroke_workspace.refresh(w.four_stroke_context.project);w.experience.reference_loaded()
    for c in (w.context,w.native_four_stroke.context,w.four_stroke_context):c.dirty=False
    w.close();APP.processEvents()


def test_component_navigation_all_families_and_reverse_selection(window):
    w=window;nav=w.experience.components;nav.dock.show()
    w.show_two_stroke_mode();nav.activate('exhaust');assert w.component_nav.currentIndex()==2
    nav.activate('ports');assert w.component_nav.currentIndex()==1
    w.component_nav.setCurrentIndex(7);assert nav.map.selected=='crankcase'
    w.show_native_four_stroke_mode();nav.activate('exhaust_valve');assert w.native_four_stroke.editor.sections.currentIndex()==list(w.native_four_stroke.editor.tables).index('exhaust_valve')
    w.show_four_stroke_mode();nav.activate('intake');assert w.four_stroke_workspace.tabs.currentIndex()==2
    assert 'sintética' in nav.family.text()


def test_native_rename_preserves_historical_references_and_undo(window,monkeypatch):
    w=window;w.show_native_four_stroke_mode();context=w.native_four_stroke.context
    context.duplicate_variant(None,'original');context.select_variant('original');before=deepcopy(context.project['run_references'])
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:('renamed',True))
    w.native_four_stroke.rename_variant()
    assert context.selected_variant=='renamed' and context.project['run_references']==before
    context.undo();assert 'original' in context.project['variants'] and 'renamed' not in context.project['variants']


def test_native_overlay_reverifies_pair_and_keeps_synthetic_origin(tmp_path):
    from c01_c03_fixtures import endpoint_factory
    from motorsim.desktop.four_stroke_comparison import build_comparison
    from motorsim.desktop.comparison_plot import comparison_pressure_series
    make=endpoint_factory(tmp_path);a=make('A');b=make('B');comparison=build_comparison(a,b)
    series=comparison_pressure_series([a['reference'],b['reference']],comparison)
    assert len(series)==2 and all(len(s['points'])==3 for s in series)
    assert all('SYNTHETIC' in str(p) for s in series for p in s['points'])
    bad=dict(comparison,comparison_id='0'*64)
    with pytest.raises(ValueError):comparison_pressure_series([a['reference'],b['reference']],bad)


def test_external_binding_rejects_unverified_metadata(tmp_path):
    from motorsim.desktop.result_binding import verified_references
    (tmp_path/'result.json').write_text(json.dumps({'schema':'bad','classification':'MEASURED','bindings':{'identity_sha256':'a'*64}}))
    with pytest.raises((ValueError,KeyError,OSError)):verified_references([tmp_path])


def test_application_queue_freezes_input_and_excludes_interactive_native(window):
    import threading,time
    from PySide6.QtCore import QThreadPool
    w=window;w.show_native_four_stroke_mode();jobs=w.experience.jobs;manager=jobs.manager
    native=w.native_four_stroke;native.simulation.cycles.setValue(1);native.simulation.wall.setValue(10)
    entered=threading.Event();release=threading.Event()
    def execute(job,root,cancel,progress):entered.set();release.wait(3);return None
    previous=manager.executor;manager.executor=execute
    try:
        assert jobs.enqueue_current();frozen=json.loads(manager.items[-1]['configuration']);jobs.start()
        deadline=time.monotonic()+3
        while not entered.is_set() and time.monotonic()<deadline:APP.processEvents();time.sleep(.005)
        assert entered.is_set() and manager.running
        native.simulation.execute();assert native.simulation.task is None
        config=deepcopy(native.context.engine());config['geometry']['bore_mm']+=.25;native.context.replace_engine(config)
        assert json.loads(manager.task.job['configuration'])==frozen
        assert not manager.shutdown(1)
        release.set()
        while manager.running and time.monotonic()<deadline+3:APP.processEvents();time.sleep(.005)
        assert not manager.running and manager.items[-1]['status']=='CANCELLED'
        assert not getattr(native.context,'queued_execution_active',False)
    finally:
        release.set();manager.shutdown(2000);QThreadPool.globalInstance().waitForDone(2000);manager.executor=previous
