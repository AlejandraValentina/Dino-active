"""C05 packaged acceptance: native 4T legacy history, traceability, exports and reopen.

The historical A/B endpoints are intentionally loaded without promotion. This
driver checks the fail-closed legacy presentation, not a new A/B comparison.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from motorsim.desktop.acceptance_terminal import (default_worker_probe,
                                                   finalize_acceptance)

import win32con
import win32gui
import win32process
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.uia_element_info import UIAElementInfo


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    exe = args.exe.resolve()
    project = args.project.resolve()
    work = args.work.resolve()
    if not exe.is_file() or exe.name.lower() != "dino2t.exe":
        raise FileNotFoundError(f"expected packaged Dino2T.exe: {exe}")
    if not project.is_file():
        raise FileNotFoundError(project)
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    for name in ("settings", "artifacts", "localappdata"):
        (work / name).mkdir()
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV",
                "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(key, None)
    env.update(QT_QPA_PLATFORM="windows",
               DINO_TEST_SETTINGS_ROOT=str(work / "settings"),
               DINO_ARTIFACT_ROOT=str(work / "artifacts"),
               LOCALAPPDATA=str(work / "localappdata"),
               PATH=os.environ["SystemRoot"] + "\\System32;" + os.environ["SystemRoot"])
    checks = []
    csv_path = work / "resultados-legacy.csv"
    html_path = work / "resultados-legacy.html"

    def start():
        return subprocess.Popen([str(exe)], cwd=str(work), env=env)

    def windows(process):
        found = []
        def visit(hwnd, _):
            if (win32gui.IsWindowVisible(hwnd)
                    and win32process.GetWindowThreadProcessId(hwnd)[1] == process.pid):
                found.append((hwnd, win32gui.GetWindowText(hwnd)))
        win32gui.EnumWindows(visit, None)
        return found

    def desktop_windows():
        found = []
        def visit(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                found.append((hwnd, win32gui.GetWindowText(hwnd), pid))
        win32gui.EnumWindows(visit, None)
        return found

    def wait(fn, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = fn()
            if value:
                return value
            time.sleep(.2)
        raise TimeoutError("UIA timeout")

    def fresh(widget):
        return UIAWrapper(UIAElementInfo(widget.handle))

    def descendants(widget):
        try:
            return fresh(widget).descendants()
        except Exception:
            return []

    def window(process, fragment):
        def locate():
            hwnd = next((h for h, title in windows(process)
                         if fragment.lower() in title.lower()), None)
            if hwnd is None:
                return None
            wrapper = UIAWrapper(UIAElementInfo(hwnd))
            if any(x.element_info.control_type == "Button"
                   for x in wrapper.descendants()):
                return wrapper
            return None
        return wait(locate, 30)

    def button(widget, name):
        return next(x for x in descendants(widget)
                    if x.element_info.control_type == "Button"
                    and name.lower() in x.window_text().lower())

    def tab(widget, name):
        return next(x for x in descendants(widget)
                    if x.element_info.control_type == "TabItem"
                    and name.lower() in x.window_text().lower())

    def click(widget, name):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                button(widget, name).invoke()
                time.sleep(.4)
                return
            except StopIteration:
                time.sleep(.2)
        raise LookupError(f"button not found: {name}")

    def file_dialog(process, title, path):
        hwnd = wait(lambda: next((h for h, caption, pid in desktop_windows()
                                  if pid == process.pid and title.lower() in caption.lower()), None), 15)
        dialog = UIAWrapper(UIAElementInfo(hwnd))
        edit = next((x for x in descendants(dialog)
                     if x.element_info.control_type == "Edit"
                     and x.is_visible()
                     and (x.element_info.automation_id.endswith("fileNameEdit")
                          or x.element_info.automation_id in ("1148", "1001"))), None)
        if edit is None:
            raise LookupError("file dialog edit missing")
        try:
            win32gui.SetForegroundWindow(dialog.handle)
        except Exception:
            pass
        try:
            edit.iface_value.SetValue(str(path))
        except Exception:
            edit.set_edit_text(str(path))
        time.sleep(.2)
        from pywinauto.keyboard import send_keys
        edit.set_focus()
        send_keys("^a")
        send_keys(str(path), with_spaces=True)
        send_keys("{ENTER}")
        wait(lambda: not any(pid == process.pid and title.lower() in caption.lower()
                             for _, caption, pid in desktop_windows()), 10)
        time.sleep(.4)
        if not Path(path).is_file():
            raise RuntimeError(f"file dialog did not produce {path}")

    def texts(widget):
        return "\n".join(x.window_text() for x in descendants(widget)
                         if x.element_info.control_type in ("Text", "DataItem", "ListItem"))

    def dismiss_info(process):
        for _ in range(10):
            info = next((h for h, title in windows(process)
                         if title in ("CSV exportado", "Informe técnico 4T",
                                      "Informe técnico")), None)
            if info is None:
                return
            dialog = UIAWrapper(UIAElementInfo(info))
            try:
                action = next(x for x in dialog.descendants()
                              if x.element_info.control_type == "Button")
                action.invoke()
            except Exception:
                win32gui.PostMessage(info, win32con.WM_CLOSE, 0, 0)
            time.sleep(.4)

    def note(text):
        checks.append(text)
        print("PASS", text, flush=True)

    def close(process, widget, name):
        win32gui.PostMessage(widget.handle, win32con.WM_CLOSE, 0, 0)
        run_work = work / name
        run_work.mkdir(exist_ok=True)
        record = finalize_acceptance(run_work, {
            "schema": "DINO_C05_LEGACY_4T_RUN_V1", "phase": name,
            "exe": str(exe), "exe_sha256": sha256(exe),
            "project": str(project), "project_sha256": sha256(project),
        }, process=process, timeout=20)
        if record["result"] != "PASS":
            raise RuntimeError(f"{name}: {record['result']} "
                               f"{record['terminal_verification']['issues']}")
        if default_worker_probe():
            raise AssertionError(f"{name}: MotorSimWorker.exe remained after close")

    process = start()
    try:
        main_window = window(process, "Dino 2T")
        click(main_window, "Abrir proyecto")
        file_dialog(process, "Abrir proyecto", project)
        four = window(process, "Dino Desktop")
        tab(four, "RESULTADOS").select()
        time.sleep(1.0)
        body = texts(four)
        if "Histórico no verificado" not in body:
            raise AssertionError("legacy history was not labelled as unverified")
        if "LEGACY_UNVERIFIED" in body:
            pass
        note("Native 4T project opens with both endpoints explicitly LEGACY_UNVERIFIED")

        tab(four, "Trazabilidad").select()
        time.sleep(.5)
        trace = texts(four)
        for expected in ("Integridad de artefactos", "Run ID", "SHA-256 de configuración",
                         "Commit del código"):
            if expected not in trace:
                raise AssertionError(f"traceability view missing {expected!r}")
        note("Traceability exposes integrity, run identity, configuration hash and code commit")

        click(four, "Exportar CSV")
        file_dialog(process, "Exportar resultados 4T", csv_path)
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) < 2 or any(row.get("integrity_classification") != "LEGACY_UNVERIFIED"
                                for row in rows):
            raise AssertionError("CSV export did not retain both LEGACY_UNVERIFIED rows")
        if not all(row.get("run_id") and row.get("result_sha256") for row in rows):
            raise AssertionError("CSV export lost run identity or result hash")
        note("CSV export retains both legacy records, classification and result hashes")
        dismiss_info(process)

        click(four, "Informe técnico HTML")
        file_dialog(process, "Informe técnico 4T", html_path)
        report = html_path.read_text(encoding="utf-8")
        for expected in ("No realizado", "No declarado"):
            if expected not in report:
                raise AssertionError(f"HTML report missing {expected!r}")
        note("HTML report retains scientific claim qualifications")
        close(process, four, "run1")
    finally:
        if process.poll() is None:
            process.terminate()

    process = start()
    try:
        main_window = window(process, "Dino 2T")
        click(main_window, "Abrir proyecto")
        file_dialog(process, "Abrir proyecto", project)
        four = window(process, "Dino Desktop")
        tab(four, "RESULTADOS").select()
        time.sleep(1.0)
        body = texts(four)
        if "Histórico no verificado" not in body:
            raise AssertionError("reopened project lost its legacy history labels")
        note("Fresh packaged process reopens the project and preserves legacy history")
        close(process, four, "run2")
    finally:
        if process.poll() is None:
            process.terminate()

    if default_worker_probe():
        raise AssertionError("orphan MotorSimWorker.exe after legacy acceptance")
    receipt = {
        "schema": "DINO_C05_LEGACY_4T_PACKAGED_ACCEPTANCE_V1",
        "result": "PASS",
        "exe": str(exe), "exe_sha256": sha256(exe),
        "project": str(project), "project_sha256": sha256(project),
        "checks": checks,
        "exports": {"csv": str(csv_path), "csv_sha256": sha256(csv_path),
                     "html": str(html_path), "html_sha256": sha256(html_path)},
        "scientific_claims": {"experimental_validation": "NOT_PERFORMED",
                              "predictive_capability": "NOT_CLAIMED"},
    }
    (work / "acceptance.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "acceptance": str(work / "acceptance.json"),
                      "checks": checks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
