"""C05 packaged acceptance: 4T 0D RPM curve, persistence, reopen and cancellation.

External maintainer driver. It starts the packaged Dino2T.exe twice, uses only
the 4T 0D reference workspace, and verifies the project-local curve reference.
"""
from __future__ import annotations

import argparse
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
from motorsim.four_stroke_project import save_project, starter_project

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
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()
    exe = args.exe.resolve()
    work = args.work.resolve()
    if not exe.is_file() or exe.name.lower() != "dino2t.exe":
        raise FileNotFoundError(f"expected packaged Dino2T.exe: {exe}")
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
    project_path = work / "proyecto-c05-4t.dino4t.json"
    save_project(project_path, starter_project(rpm=3000))
    checks = []
    captures = []

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

    def window(process, fragment):
        def locate():
            hwnd = next((h for h, title in windows(process)
                         if fragment.lower() in title.lower()), None)
            if hwnd is None:
                return None
            wrapper = UIAWrapper(UIAElementInfo(hwnd))
            if any(x.element_info.control_type == "Button"
                   for x in descendants(wrapper)):
                return wrapper
            return None
        return wait(locate, 30)

    def descendants(widget):
        try:
            return widget.descendants()
        except Exception:
            return []

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
                time.sleep(.3)
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
        edit.set_edit_text(str(path))
        time.sleep(.2)
        action = next((x for x in descendants(dialog)
                       if x.element_info.control_type == "Button"
                       and x.element_info.automation_id == "1"), None)
        if action is not None:
            action.invoke()
        else:
            edit.set_focus()
            from pywinauto.keyboard import send_keys
            send_keys("{ENTER}")
        wait(lambda: not any(pid == process.pid and title.lower() in caption.lower()
                             for _, caption, pid in desktop_windows()), 10)
        time.sleep(.3)
        if not Path(path).is_file():
            raise RuntimeError(f"file dialog did not produce {path}")

    def top(widget, width=1360, height=900):
        win32gui.ShowWindow(widget.handle, win32con.SW_RESTORE)
        win32gui.SetWindowPos(widget.handle, win32con.HWND_TOPMOST, 25, 25,
                              width, height, win32con.SWP_SHOWWINDOW)
        try:
            win32gui.SetForegroundWindow(widget.handle)
        except Exception:
            pass
        time.sleep(.4)

    def _fresh(widget):
        return UIAWrapper(UIAElementInfo(widget.handle))

    def texts(widget):
        return "\n".join(x.window_text() for x in descendants(_fresh(widget))
                         if x.element_info.control_type in ("Text", "DataItem"))

    def status_text(widget):
        values = [x.window_text() for x in descendants(_fresh(widget))
                  if x.element_info.control_type in ("Text", "DataItem")
                  and "curva 4t" in x.window_text().lower()]
        return values[-1] if values else ""

    def capture(widget, name, width=1360, height=900):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        win32gui.ShowWindow(widget.handle, win32con.SW_RESTORE)
        win32gui.SetWindowPos(widget.handle, win32con.HWND_TOPMOST, 25, 25,
                              width, height, win32con.SWP_SHOWWINDOW)
        time.sleep(.3)
        left, top, right, bottom = win32gui.GetWindowRect(widget.handle)
        path = work / (name + ".png")
        image = app.primaryScreen().grabWindow(0, left, top, right - left, bottom - top)
        if not image.save(str(path)):
            raise RuntimeError(f"screenshot failed: {path}")
        captures.append({"path": str(path), "sha256": sha256(path),
                         "size_px": [right - left, bottom - top]})

    def note(text):
        checks.append(text)
        print("PASS", text, flush=True)

    def close(process, widget, name, payload):
        win32gui.PostMessage(widget.handle, win32con.WM_CLOSE, 0, 0)
        run_work = work / name
        run_work.mkdir(exist_ok=True)
        record = finalize_acceptance(run_work, payload, process=process,
                                     timeout=20)
        if record["result"] != "PASS":
            raise RuntimeError(f"{name}: {record['result']} "
                               f"{record['terminal_verification']['issues']}")
        if default_worker_probe():
            raise AssertionError(f"{name}: MotorSimWorker.exe remained after close")

    process = start()
    try:
        main_window = window(process, "Dino 2T")
        click(main_window, "Modo 4T 0D")
        four = window(process, "Dino 4T 0D")
        click(four, "Abrir 4T")
        file_dialog(process, "Abrir proyecto 4T", project_path)
        four = window(process, "Dino 4T 0D")
        note("Packaged app opens the saved 4T 0D reference project")

        top(four)
        tab(four, "Curva RPM 4T").select()
        time.sleep(.3)
        click(four, "Calcular curva")
        wait(lambda: "vinculada" in status_text(four)
             or "falló" in status_text(four).lower()
             or "no vigente" in status_text(four).lower(), args.timeout)
        status = status_text(four)
        if "vinculada" not in status:
            raise AssertionError(f"4T curve did not link: {status}")
        if "completa" not in status or "3 puntos" not in status:
            raise AssertionError(f"4T curve did not report three converged points: {status}")
        body = texts(four)
        if "2500" not in body or "3000" not in body or "converged" not in body:
            raise AssertionError(f"4T curve table is not populated: {body[:1200]}")
        note("Packaged 4T 0D curve completed and linked three RPM points")
        capture(four, "c05-4t-curve-complete-1360x900")
        click(four, "Guardar 4T")
        references = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            saved = json.loads(project_path.read_text(encoding="utf-8"))
            references = saved.get("curve_references", [])
            if references:
                break
            time.sleep(.5)
        if len(references) != 1 or references[0]["status"] != "converged":
            raise AssertionError("4T curve reference was not persisted")
        series_path = project_path.parent / references[0]["series_path"]
        if not series_path.is_file():
            raise AssertionError(f"missing project-local series: {series_path}")
        if sha256(series_path) != references[0]["series_sha256"]:
            raise AssertionError("project-local series hash mismatch")
        note("4T curve reference is project-local, hash-bound and persisted")
        close(process, four, "run1", {
            "schema": "DINO_C05_4T_CURVE_RUN_V1", "phase": "complete-and-save",
            "project": str(project_path), "project_sha256": sha256(project_path),
            "series": str(series_path), "series_sha256": sha256(series_path),
        })
    finally:
        if process.poll() is None:
            process.terminate()

    process = start()
    try:
        main_window = window(process, "Dino 2T")
        click(main_window, "Modo 4T 0D")
        four = window(process, "Dino 4T 0D")
        click(four, "Abrir 4T")
        file_dialog(process, "Abrir proyecto 4T", project_path)
        four = window(process, "Dino 4T 0D")
        top(four)
        tab(four, "Curva RPM 4T").select()
        time.sleep(3.0)
        restored = ""
        for _ in range(5):
            restored = status_text(four)
            if "restaurada" in restored and "3 puntos" in restored:
                break
            time.sleep(2.0)
        if "restaurada" not in restored or "3 puntos" not in restored:
            raise AssertionError(
                f"reopened 4T curve not restored; hwnd={four.handle} "
                f"title={win32gui.GetWindowText(four.handle)!r} status={restored!r}")
        note("Saved 4T project reopened with its curve reference restored")
        capture(four, "c05-4t-curve-reopened-1360x900")

        # Cancel a second curve promptly and verify a terminal partial result remains.
        click(four, "Calcular curva")
        wait(lambda: "Ejecutando" in status_text(four) or "punto" in status_text(four), 30)
        cancel = next(x for x in descendants(_fresh(four))
                      if x.element_info.control_type == "Button"
                      and x.window_text().strip().lower() == "cancelar")
        wait(lambda: cancel.is_enabled(), 30)
        cancel.invoke()
        wait(lambda: "cancelada" in status_text(four).lower()
             or "parcial" in status_text(four).lower(), 180)
        click(four, "Guardar 4T")
        references = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            saved = json.loads(project_path.read_text(encoding="utf-8"))
            references = saved.get("curve_references", [])
            if len(references) >= 2:
                break
            time.sleep(.5)
        if len(references) < 2:
            raise AssertionError("cancelled curve was not persisted as a partial reference")
        latest = references[-1]
        if latest["status"] not in ("cancelled", "stopped"):
            raise AssertionError(f"cancelled curve status={latest['status']}")
        partial = project_path.parent / latest["series_path"]
        if not partial.is_file() or sha256(partial) != latest["series_sha256"]:
            raise AssertionError("cancelled partial series is missing or altered")
        note("Cancelled 4T curve is terminal, partial and persisted without a worker")
        capture(four, "c05-4t-curve-cancelled-1360x900")
        close(process, four, "run2", {
            "schema": "DINO_C05_4T_CURVE_RUN_V1", "phase": "reopen-and-cancel",
            "project": str(project_path), "project_sha256": sha256(project_path),
            "partial_series": str(partial), "partial_series_sha256": sha256(partial),
        })
    finally:
        if process.poll() is None:
            process.terminate()

    if default_worker_probe():
        raise AssertionError("orphan MotorSimWorker.exe after both packaged runs")
    receipt = {
        "schema": "DINO_C05_4T_CURVE_PACKAGED_ACCEPTANCE_V1",
        "result": "PASS",
        "exe": str(exe), "exe_sha256": sha256(exe),
        "project": str(project_path), "project_sha256": sha256(project_path),
        "checks": checks, "captures": captures,
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
