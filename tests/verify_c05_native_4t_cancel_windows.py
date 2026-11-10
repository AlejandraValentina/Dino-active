"""C05 packaged acceptance: native 4T QRunnable cancellation and close."""
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
    exe = args.exe.resolve(); project = args.project.resolve(); work = args.work.resolve()
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
    before = sha256(project)

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
        from pywinauto.keyboard import send_keys
        edit.set_focus()
        send_keys("^a")
        send_keys(str(path), with_spaces=True)
        send_keys("{ENTER}")
        wait(lambda: not any(pid == process.pid and title.lower() in caption.lower()
                             for _, caption, pid in desktop_windows()), 10)
        time.sleep(.4)

    def texts(widget):
        return "\n".join(x.window_text() for x in descendants(widget)
                         if x.element_info.control_type in ("Text", "DataItem", "ListItem"))

    def dismiss_discard(process):
        for _ in range(20):
            if process.poll() is not None:
                return
            hwnd = next((h for h, title in windows(process)
                         if "cambios sin guardar" in title.lower()), None)
            if hwnd is None:
                time.sleep(.3)
                continue
            dialog = UIAWrapper(UIAElementInfo(hwnd))
            for label in ("Descartar", "Discard"):
                candidate = next((x for x in dialog.descendants()
                                  if x.element_info.control_type == "Button"
                                  and label.lower() in x.window_text().lower()), None)
                if candidate is not None:
                    candidate.invoke()
                    time.sleep(.5)
                    break
            else:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(.5)

    process = subprocess.Popen([str(exe)], cwd=str(work), env=env)
    try:
        main_window = window(process, "Dino 2T")
        click(main_window, "Abrir proyecto")
        file_dialog(process, "Abrir proyecto", project)
        four = window(process, "Dino Desktop")
        tab(four, "SIMULAR").select()
        time.sleep(.5)
        click(four, "Ejecutar punto 4T")
        wait(lambda: "Ciclo " in texts(four), 120)
        click(four, "Cancelar al final del ciclo")
        wait(lambda: "CANCELADA" in texts(four).upper()
             or "CANCELADA" in texts(four), 240)
        body = texts(four)
        if "CANCELADA" not in body.upper():
            raise AssertionError(f"native 4T cancellation not terminal: {body[:1200]}")
        if button(four, "Cancelar al final del ciclo").is_enabled():
            raise AssertionError("cancel remained enabled after terminal return")
        if not button(four, "Ejecutar punto 4T").is_enabled():
            raise AssertionError("start did not return after cancellation")
        if default_worker_probe():
            raise AssertionError("orphan MotorSimWorker.exe after native cancellation")
        after = sha256(project)
        if after != before:
            raise AssertionError("native 4T cancellation modified the saved project")
        win32gui.PostMessage(four.handle, win32con.WM_CLOSE, 0, 0)
        dismiss_discard(process)
        run_work = work / "run1"
        run_work.mkdir(exist_ok=True)
        record = finalize_acceptance(run_work, {
            "schema": "DINO_C05_NATIVE_4T_CANCEL_V1",
            "exe": str(exe), "exe_sha256": sha256(exe),
            "project": str(project), "project_sha256_before": before,
            "project_sha256_after": after,
            "checks": ["Native 4T run cancelled at a cycle boundary",
                       "Terminal partial result retained by the app",
                       "No orphan worker and project file unchanged"],
        }, process=process, timeout=20)
        if record["result"] != "PASS":
            raise RuntimeError(f"terminal acceptance {record['result']}: "
                               f"{record['terminal_verification']['issues']}")
    finally:
        if process.poll() is None:
            process.terminate()
    print(json.dumps({"result": "PASS", "acceptance": str(work / "run1" / "acceptance.json")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
