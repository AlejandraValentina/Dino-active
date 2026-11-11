"""Source-only UX walkthrough of an unmodified Dino GUI, with isolated data.

The loopback bridge is process-local audit tooling, not a product interface.
QTest sends real Qt mouse/keyboard events; explicitly recorded direct calls are
used only for fixture loading, state inspection and bounded capture setup.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import sys
import threading
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--port', type=int, default=18763)
    parser.add_argument('--request-file', type=Path)
    args = parser.parse_args()
    if args.request_file:
        payload = args.request_file.read_bytes()
        req = urllib.request.Request(f'http://127.0.0.1:{args.port}/', payload,
                                     {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=55) as response:
            print(response.read().decode('utf-8'))
        return
    if args.artifacts is None:
        parser.error('--artifacts required for server')
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=True)
    captures = ROOT / 'results/frontend-audit-v1/captures'
    captures.mkdir(parents=True, exist_ok=True)
    os.environ['DINO_TEST_SETTINGS_ROOT'] = str(root / 'settings')
    os.environ['DINO_ARTIFACT_ROOT'] = str(root / 'artifacts')
    os.environ.pop('QT_QPA_PLATFORM', None)
    from PySide6.QtCore import Qt, QTimer, QLocale
    from PySide6.QtWidgets import (QApplication, QWidget, QAbstractButton,
        QLabel, QComboBox, QLineEdit, QAbstractSpinBox, QTabWidget,
        QTableWidget, QPlainTextEdit, QTextBrowser, QDialog, QFileDialog,
        QMessageBox, QInputDialog, QListWidget)
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QAction
    from motorsim.desktop.app import DinoDesktopWindow

    app = QApplication(['DinoFrontendAudit'])
    app.setApplicationName('Dino 2T')
    app.setOrganizationName('Dino2T')
    QLocale.setDefault(QLocale('es_UY'))
    window = DinoDesktopWindow()
    window.show()
    pending = queue.Queue()
    journal_path = root / 'interaction-journal.jsonl'

    def journal(item):
        item['at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        with journal_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(item, ensure_ascii=False, default=str) + '\n')

    def inventory():
        rows = []
        for widget in app.allWidgets():
            if not widget.isVisible():
                continue
            if not isinstance(widget, (QAbstractButton, QLabel, QComboBox,
                    QLineEdit, QAbstractSpinBox, QTabWidget, QTableWidget,
                    QPlainTextEdit, QTextBrowser, QListWidget)):
                continue
            row = dict(id=id(widget), cls=type(widget).__name__,
                name=widget.objectName(), enabled=widget.isEnabled(),
                accessible=widget.accessibleName(),
                tooltip=widget.toolTip(),
                rect=[widget.x(), widget.y(), widget.width(), widget.height()])
            if hasattr(widget, 'text'):
                row['text'] = widget.text()
            if isinstance(widget, QComboBox):
                row['items'] = [widget.itemText(i) for i in range(widget.count())]
                row['current'] = widget.currentIndex()
            if isinstance(widget, QTabWidget):
                row['tabs'] = [widget.tabText(i) for i in range(widget.count())]
                row['current'] = widget.currentIndex()
            if isinstance(widget, QAbstractSpinBox):
                row['value'] = widget.value()
            if isinstance(widget, QTableWidget):
                row['headers'] = [widget.horizontalHeaderItem(i).text()
                    if widget.horizontalHeaderItem(i) else ''
                    for i in range(widget.columnCount())]
                row['rows'] = [[widget.item(r, c).text() if widget.item(r,c)
                    else '' for c in range(widget.columnCount())]
                    for r in range(min(widget.rowCount(), 40))]
            if isinstance(widget, (QPlainTextEdit, QTextBrowser)):
                row['text'] = widget.toPlainText()
            if isinstance(widget, QListWidget):
                row['items'] = [widget.item(i).text() for i in range(widget.count())]
            rows.append(row)
        return sorted(rows, key=lambda r:(r['cls'], r['name'], r.get('text','')))

    def capture(tag, target=None):
        QTest.qWait(120)
        target = target or app.activeModalWidget() or window
        image_path = captures / (tag + '.png')
        if not target.grab().save(str(image_path)):
            raise RuntimeError('Could not capture actual Qt window')
        state = dict(tag=tag, title=target.windowTitle(),
            platform=app.platformName(), size=[target.width(), target.height()],
            screen_dpr=target.devicePixelRatioF(),
            widgets=inventory())
        image_path.with_suffix('.json').write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        journal(dict(kind='capture', tag=tag,
                     sha256=hashlib.sha256(image_path.read_bytes()).hexdigest()))
        return str(image_path)

    def click(widget):
        if not widget.isVisible() or not widget.isEnabled():
            raise ValueError('Target is not visible and enabled')
        journal(dict(kind='mouse', target=type(widget).__name__,
                     text=widget.text() if hasattr(widget,'text') else '',
                     name=widget.objectName()))
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        QTest.qWait(100)

    def choose(combo, index):
        combo.setFocus()
        QTest.keyClick(combo, Qt.Key.Key_Home)
        for _ in range(index):
            QTest.keyClick(combo, Qt.Key.Key_Down)
        QTest.qWait(120)
        journal(dict(kind='keyboard-combo', name=combo.objectName(), index=index,
                     value=combo.currentText()))

    def enter(widget, text):
        widget.setFocus()
        QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(widget, str(text))
        QTest.keyClick(widget, Qt.Key.Key_Tab)
        QTest.qWait(100)
        journal(dict(kind='keyboard-entry', name=widget.objectName(), text=str(text)))

    def by_text(text):
        found = [w for w in app.allWidgets() if w.isVisible() and
                 isinstance(w,QAbstractButton) and w.text()==text]
        if len(found)!=1:
            raise ValueError(f'{len(found)} visible buttons matching {text!r}')
        return found[0]

    ns = dict(app=app, window=window, root=root, ROOT=ROOT, capture=capture,
        inventory=inventory, click=click, choose=choose, enter=enter,
        by_text=by_text, QTest=QTest, Qt=Qt, QTimer=QTimer, Path=Path,
        QDialog=QDialog, QFileDialog=QFileDialog, QMessageBox=QMessageBox,
        QInputDialog=QInputDialog, QTableWidget=QTableWidget,
        QComboBox=QComboBox, QLineEdit=QLineEdit, QAction=QAction,
        json=json, journal=journal)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            event = threading.Event()
            item = dict(payload=json.loads(self.rfile.read(int(
                self.headers['Content-Length']))), event=event)
            pending.put(item)
            event.wait(50)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(item.get('response', {'error':'timeout'}),
                                      ensure_ascii=False, default=str).encode('utf-8'))
        def log_message(self, *_):
            pass

    busy = False
    def poll():
        nonlocal busy
        if busy or pending.empty():
            return
        busy = True
        item = pending.get()
        payload = item['payload']
        journal(dict(kind='command', payload=payload))
        try:
            ns['result'] = None
            exec(payload['code'], ns)
            item['response'] = dict(ok=True, result=ns.get('result'))
        except Exception:
            item['response'] = dict(ok=False, error=traceback.format_exc())
        finally:
            journal(dict(kind='response', response=item['response']))
            item['event'].set()
            busy = False

    server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(60)
    (root/'ready.json').write_text(json.dumps(dict(pid=os.getpid(),
        platform=app.platformName(), port=args.port,
        screen=[app.primaryScreen().size().width(),app.primaryScreen().size().height()])),
        encoding='utf-8')
    app.exec()
    server.shutdown()


if __name__ == '__main__':
    main()
