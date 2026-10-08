"""Recorrido automatizado visible; no representa aceptación manual de la usuaria."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scale', default='1')
parser.add_argument('--result', type=Path, help='Reabrir sin volver a calcular.')
parser.add_argument('--output', type=Path)
parser.add_argument('--cancel', action='store_true', help='Comprobar cancelación visible, sin completar otro ciclo.')
parser.add_argument('--suffix', default='', help='Identificar nuevas capturas sin sobrescribir las anteriores.')
args = parser.parse_args()
os.environ['QT_QPA_PLATFORM'] = 'windows'
os.environ['QT_SCALE_FACTOR'] = args.scale
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim import simulation_view
from motorsim.reference_results import load_result

app = QApplication([])
app.setApplicationName('MotorSim')
window = MainWindow()
window.name_edit.setText('PROYECTO DE PRUEBA — independiente del caso')
window.cycle_combo.setCurrentText('4T')
window.show()
window.tabs.setCurrentWidget(window.simulation_view)
window.raise_()
window.activateWindow()
view = window.simulation_view
original_project = window.project()
started = time.monotonic()
phase = 'load' if args.result and not args.cancel else 'run'
result_path = args.result
deadline = started+80


def capture(suffix):
    screen = window.screen()
    frame = window.frameGeometry()
    path = Path('docs/images')/f'motorsim-simulacion-{suffix}{args.suffix}.png'
    assert not path.exists(), f'No sobrescribir {path}'
    pixmap = screen.grabWindow(0, frame.x(), frame.y(), frame.width(), frame.height())
    assert not pixmap.isNull()
    assert pixmap.save(str(path))
    print('CAPTURE', path.resolve(), pixmap.width(), pixmap.height(), flush=True)


def tick():
    global phase, result_path
    try:
        assert time.monotonic() < deadline, 'Tiempo del recorrido excedido'
        if phase == 'run':
            assert args.output is not None
            simulation_view.new_output_path = lambda: args.output
            QTest.mouseClick(view.run_button, Qt.MouseButton.LeftButton)
            assert view.active
            first = view.process
            view.start()
            assert view.process is first
            phase = 'running'
        elif phase == 'running' and not view.active:
            if args.cancel:
                assert view.state_label.text() == 'Cancelado' and not view.forced
                assert load_result(view.output/'manifest.json')['status'] == 'cancelled'
                assert not view.angle_plot.points
                print('VISIBLE_CANCEL_OK', flush=True)
                view.open_result(path=args.result)
                assert view.result and view.result['status'] == 'converged'
                assert window.project() == original_project and window.dirty
                window.dirty = False
                window.close()
                app.quit()
                return
            assert view.result and view.result['status'] == 'converged', view.error_label.text()
            result_path = view.output/'manifest.json'
            assert window.project() == original_project and window.dirty
            phase = 'capture'
        elif phase == 'running' and args.cancel and 'RHS:' in view.progress_label.text():
            QTest.mouseClick(view.cancel_button, Qt.MouseButton.LeftButton)
        elif phase == 'load':
            view.open_result(path=result_path)
            assert view.result and view.result['status'] == 'converged', view.error_label.text()
            available = window.screen().availableGeometry()
            window.resize(min(1020, available.width()-40), min(760, available.height()-70))
            phase = 'capture'
        elif phase == 'capture':
            assert len(view.angle_plot.points) == 721 and len(view.pv_plot.points) == 721
            assert view.angle_plot.points[0][0] == 180 and view.angle_plot.points[-1][0] == 540
            capture(str(round(window.devicePixelRatioF()*100)))
            view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())
            phase = 'bottom'
        elif phase == 'bottom':
            capture(str(round(window.devicePixelRatioF()*100))+'-resultados')
            available = window.screen().availableGeometry()
            window.resize(700, min(650, available.height()-70))
            view.verticalScrollBar().setValue(0)
            phase = 'compact'
        elif phase == 'compact':
            assert view.horizontalScrollBar().maximum() == 0
            view.run_button.setFocus()
            QTest.keyClick(view.run_button, Qt.Key.Key_Tab)
            assert view.open_button.hasFocus()
            window.tabs.setCurrentIndex(0)
            window.tabs.setCurrentWidget(view)
            assert view.result['path'] == result_path.resolve()
            capture(str(round(window.devicePixelRatioF()*100))+'-compacta')
            view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())
            phase = 'compact-bottom'
        elif phase == 'compact-bottom':
            capture(str(round(window.devicePixelRatioF()*100))+'-compacta-resultados')
            print('VISIBLE_OK', json.dumps(dict(scale=args.scale, result=str(result_path.resolve()),
                device_pixel_ratio=window.devicePixelRatioF(),
                dirty_preserved=window.dirty, project_preserved=window.project() == original_project,
                horizontal_scroll=view.horizontalScrollBar().maximum())), flush=True)
            window.dirty = False
            window.close()
            app.quit()
    except Exception as exc:
        print('VISIBLE_ERROR', repr(exc), flush=True)
        if view.active:
            view.cancel()
        window.dirty = False
        window.close()
        if not view.active:
            app.exit(1)
        timer.stop()


timer = QTimer()
timer.setInterval(500)
timer.timeout.connect(tick)
timer.start()
sys.exit(app.exec())
