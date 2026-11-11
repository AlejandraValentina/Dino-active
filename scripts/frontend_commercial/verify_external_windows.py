"""Experimental external keyboard/UIA diagnostic; NOT an accepted gate here.

Retained to reproduce Windows foreground/native-picker automation limitations.
Use acceptance_frontend_commercial plus verify_recovery_windows for the accepted
Qt/application and external recovery routes. No product bytes are changed here.
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from motorsim.desktop.acceptance_terminal import (default_worker_probe,
                                                   finalize_acceptance)
from motorsim.desktop.four_stroke_project import project_from_example as native_project
from motorsim.desktop.product import recovery_root
from motorsim.desktop.services import new_design_project
from motorsim.engine_project import save_project as save_engine_project
from motorsim.four_stroke_project import save_project as save_reference_project, starter_project

import win32con
import win32api
import win32gui
import win32process
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.controls.win32_controls import EditWrapper as NativeEditWrapper
from pywinauto.keyboard import send_keys as raw_send_keys
from pywinauto.controls.hwndwrapper import HwndWrapper
from pywinauto.uia_element_info import UIAElementInfo


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    exe = args.exe.resolve(); work = args.work.resolve()
    if not exe.is_file() or exe.name.lower() != "dino2t.exe":
        raise FileNotFoundError(f"expected packaged Dino2T.exe: {exe}")
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    for name in ("settings", "artifacts", "localappdata"):
        (work / name).mkdir()
    os.environ["DINO_TEST_SETTINGS_ROOT"] = str(work / "settings")
    os.environ["DINO_ARTIFACT_ROOT"] = str(work / "artifacts")
    os.environ.pop("DINO_RECOVERY_ROOT", None)
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

    def note(text):
        checks.append(text); print("PASS", text, flush=True)

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

    def focus(handle):
        current=win32api.GetCurrentThreadId()
        target=win32process.GetWindowThreadProcessId(handle)[0]
        foreground=win32gui.GetForegroundWindow()
        foreground_thread=win32process.GetWindowThreadProcessId(foreground)[0] if foreground else target
        attached=[]
        try:
            for thread in {target,foreground_thread}-{current}:
                win32process.AttachThreadInput(current,thread,True);attached.append(thread)
            win32gui.ShowWindow(handle,win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(handle)
        finally:
            for thread in attached:win32process.AttachThreadInput(current,thread,False)
        wait(lambda: win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1] == process.pid, 5)

    def send_keys(value, **kwargs):
        # Never type into another session when Windows foreground focus changes.
        if win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1] != process.pid:
            owned=windows(process)
            if not owned:raise RuntimeError('no owned foreground window available')
            focus(owned[0][0])
        raw_send_keys(value, **kwargs)

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

    def click(widget, name):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            candidate = next((x for x in descendants(widget)
                              if x.element_info.control_type in ("Button", "CheckBox")
                              and name.lower() in x.window_text().lower()), None)
            if candidate is not None:
                try:
                    focus(widget.handle)
                except Exception:
                    pass
                if candidate.element_info.control_type == "CheckBox":
                    candidate.set_focus()
                    send_keys("{SPACE}")
                else:
                    candidate.invoke()
                time.sleep(.5)
                return
            time.sleep(.2)
        raise LookupError(f"control not found: {name}")

    def file_dialog(process, title, path, *, require_file=True):
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
            focus(dialog.handle)
        except Exception:
            pass
        # UIA Value.SetValue can report success without changing this native
        # common-dialog edit. Verify its actual Win32 text before accepting.
        if not edit.handle or win32gui.GetClassName(edit.handle).lower()!='edit':
            raise LookupError('native filename Edit HWND missing')
        native_edit=NativeEditWrapper(edit.handle)
        native_edit.set_edit_text(str(path))
        actual=native_edit.text_block()
        if actual!=str(path):
            raise RuntimeError('native filename text did not match isolated target: '+repr(actual))
        time.sleep(.2)
        # The native filename value is set once through UIA. Invoke the dialog's
        # own default action instead of globally typing the path a second time.
        buttons=[x for x in descendants(dialog)
                 if x.element_info.control_type == "Button" and x.is_enabled()]
        action=next((x for x in buttons if x.element_info.automation_id=='1'),None)
        if action is None:
            names=('guardar','save') if 'guardar' in title.lower() or 'exportar' in title.lower() else ('abrir','open')
            action=next((x for x in buttons if x.element_info.automation_id!='DropDown'
                         and x.window_text().replace('&','').lower() in names),None)
        if action is None:
            raise LookupError("file dialog default action missing")
        print('FILE_DIALOG',title,action.window_text(),action.element_info.automation_id,str(path),flush=True)
        action.invoke()
        try:
            wait(lambda: not any(pid == process.pid and title.lower() in caption.lower()
                                 for _, caption, pid in desktop_windows()), 40)
        except TimeoutError:
            detail=[]
            for handle,caption in windows(process):
                wrapper=UIAWrapper(UIAElementInfo(handle))
                detail.append(dict(caption=caption,controls=[dict(type=x.element_info.control_type,
                    name=x.window_text(),id=x.element_info.automation_id) for x in descendants(wrapper)]))
            (work / "file-dialog-failure.json").write_text(json.dumps(detail,ensure_ascii=False,indent=2),encoding="utf-8")
            # Pillow is optional in the pinned automation environment. Preserve
            # the original failure even when no image backend is installed.
            try:
                image=dialog.capture_as_image()
                if image is not None:image.save(str(work / 'file-dialog-failure.png'))
            except Exception:pass
            raise
        time.sleep(.4)
        if require_file and not Path(path).is_file():
            raise RuntimeError(f"file dialog did not produce {path}")

    def texts(widget):
        return "\n".join(x.window_text() for x in descendants(widget)
                         if x.element_info.control_type in ("Text", "DataItem", "ListItem", "TabItem"))

    def engine_selector(window):
        return next(x for x in descendants(window)
                    if x.element_info.control_type == "ComboBox"
                    and x.element_info.automation_id.endswith("engineFamilySelector"))

    def select_engine(window, index):
        try:
            focus(window.handle)
        except Exception:
            pass
        combo = engine_selector(window)
        combo.click_input()
        time.sleep(.3)
        send_keys("{HOME}")
        for _ in range(index):
            send_keys("{DOWN}")
        send_keys("{ENTER}")
        time.sleep(1.0)

    def dismiss_messages(process, fragments):
        for _ in range(10):
            match = next((h for h, title in windows(process)
                          if any(fragment.lower() in title.lower() for fragment in fragments)), None)
            if match is None:
                return
            try:
                focus(match)
            except Exception:
                pass
            send_keys("{ENTER}")
            time.sleep(.4)

    def dismiss_discard(process):
        idle = 0
        for _ in range(40):
            if process.poll() is not None:
                return
            match = next((h for h, title in windows(process)
                          if "cambios" in title.lower()), None)
            if match is None:
                idle += 1
                if idle >= 5:
                    return
                time.sleep(.3); continue
            idle = 0
            dialog = UIAWrapper(UIAElementInfo(match))
            clicked = False
            for label in ("Descartar", "Discard", "No guardar"):
                candidate = next((x for x in dialog.descendants()
                                  if x.element_info.control_type == "Button"
                                  and label.lower() in x.window_text().lower()), None)
                if candidate is not None:
                    candidate.invoke(); clicked = True; break
            if not clicked:
                win32gui.PostMessage(match, win32con.WM_CLOSE, 0, 0)
            time.sleep(.5)

    # Project fixtures for recent/open checks.
    p2t = work / "recent-2t.dino2t.json"
    save_engine_project(p2t, new_design_project("recent-2t"))
    p0d = work / "recent-4t0d.dino4t.json"
    save_reference_project(p0d, starter_project(name="recent-4t0d", rpm=3000))
    pnative = work / "recent-native.dino.json"
    save_engine_project(pnative, native_project("recent-native"))

    process = start()
    try:
        main_window = window(process, "Dino 2T")
        selector = engine_selector(main_window)
        if selector is None:
            raise AssertionError("engine selector missing")

        # About (F1) must be available in every engine mode.
        for index, name in ((0, "2T"), (1, "4T nativo"), (2, "4T 0D")):
            select_engine(main_window, index)
            title = win32gui.GetWindowText(main_window.handle)
            expected = ("Dino 2T" if index == 0 else
                        "Dino Desktop" if index == 1 else "Dino 4T 0D")
            if expected.lower() not in title.lower():
                raise AssertionError(f"engine family {name} did not activate: {title}")
            if index == 1:
                click(main_window, "SIMULAR")
                time.sleep(.6)
                nav = texts(main_window)
                if "Curva de potencia / torque" not in nav:
                    raise AssertionError("native 4T RPM curve tab missing from integrated workspace")
            try:
                focus(main_window.handle)
            except Exception:
                pass
            send_keys("{F1}")
            about_hwnd = wait(lambda: next((h for h, title in windows(process)
                                            if "acerca de dino" in title.lower()), None), 15)
            about = UIAWrapper(UIAElementInfo(about_hwnd))
            about_text = "\n".join(x.window_text() for x in about.descendants())
            for expected in ("Producto", "Build y procedencia", "Estado científico",
                             "Licencias", "Soporte"):
                if expected not in about_text:
                    raise AssertionError(f"About is incomplete in {name}: {about_text[:800]}")
            send_keys("{ESC}"); time.sleep(.4)
        note("About opens and preserves scientific status in all three modes")

        # Diagnostics (Ctrl+Shift+D) in all three modes.
        for index, name in ((0, "2t"), (1, "4tnative"), (2, "4t0d")):
            select_engine(main_window, index)
            try:
                focus(main_window.handle)
            except Exception:
                pass
            target = work / f"diagnostico-{name}.zip"
            send_keys("^+d")
            file_dialog(process, "Exportar diagnóstico", target, require_file=False)
            dismiss_messages(process, ("Diagnóstico", "Diagnostico"))
            wait(lambda: target.is_file(), 10)
            if not target.is_file():
                raise AssertionError(f"diagnostics ZIP missing for {name}")
        note("Diagnostics export completes in all three modes")
        dismiss_messages(process, ("Diagnóstico", "Diagnostico"))

        # Open one project per family through the unified router.
        for index, path, fragment in ((0, p2t, "Dino 2T"),
                                      (2, p0d, "Dino 4T 0D"),
                                      (1, pnative, "Dino Desktop")):
            main_window = window(process, "Dino")
            select_engine(main_window, index)
            try:
                focus(main_window.handle)
            except Exception:
                pass
            send_keys("^o")
            file_dialog(process, "Abrir proyecto", path)
            time.sleep(1.2)
            title = win32gui.GetWindowText(main_window.handle)
            if fragment.lower() not in title.lower():
                raise AssertionError(f"unified router did not open {path.name}: {title}")
        note("Unified router opens 2T, 4T 0D and native 4T projects")

        # Recent settings are written per family.
        from motorsim.desktop.product import RecentProjects
        recent = RecentProjects()
        if str(p2t.resolve()) not in recent.items("2T"):
            raise AssertionError("2T recent project missing")
        if str(p0d.resolve()) not in recent.items("4T0D"):
            raise AssertionError("4T 0D recent project missing")
        if str(pnative.resolve()) not in recent.items("4Tnative"):
            raise AssertionError("native 4T recent project missing")
        note("Recent projects are recorded independently for 2T, 4T 0D and native 4T")

        # Native curve tab is part of the integrated workspace.
        native_window = window(process, "Dino Desktop")
        click(native_window, "SIMULAR")
        time.sleep(.6)
        nav = texts(native_window)
        if "Curva de potencia / torque" not in nav:
            raise AssertionError("native 4T RPM curve tab missing from integrated workspace")
        note("Unified native 4T workspace exposes the RPM power/torque curve")

        win32gui.PostMessage(main_window.handle, win32con.WM_CLOSE, 0, 0)
        dismiss_discard(process)
        run1 = work / "run1"; run1.mkdir()
        record = finalize_acceptance(run1, {
            "schema": "DINO_C05_COMMERCIAL_INTEGRATED_RUN_V1", "phase": "unified-cp0",
            "exe": str(exe), "exe_sha256": sha256(exe),
            "checks": list(checks),
        }, process=process, timeout=20)
        if record["result"] != "PASS":
            raise RuntimeError(f"first process terminal check: {record['terminal_verification']}")
        if process.poll() is None:
            raise AssertionError("first Dino2T process remained alive after terminal wait")
    finally:
        if process.poll() is None:
            process.terminate()

    # Seed one recovery draft per family and verify copy semantics.
    roots = recovery_root()
    originals = {}
    payloads = {
        "2T": new_design_project("recovery-2t"),
        "4T0D": starter_project(name="recovery-4t0d", rpm=3000).to_dict(),
        "4Tnative": native_project("recovery-native"),
    }
    for family, project in payloads.items():
        original = work / f"original-{family}.json"
        if family == "4T0D":
            save_reference_project(original, starter_project(name="original-4t0d", rpm=3000))
        else:
            save_engine_project(original, project)
        originals[family] = originals.get(family, {})
        originals[family]["path"] = original
        originals[family]["sha256"] = sha256(original)
        payload = {"schema": "DINO_RECOVERY_V1", "family": family,
                   "project_id": project.get("project_id", project.get("name")),
                   "original_path": str(original), "saved_at": "2026-11-10T00:00:00+00:00",
                   "project": project}
        (roots / f"{family}-seed.json").write_text(json.dumps(payload), encoding="utf-8")

    process = start()
    try:
        main_window = window(process, "Dino 2T")
        for _ in range(3):
            prompt_hwnd = wait(lambda: next((h for h, title in windows(process)
                                             if "borrador de recuperación" in title.lower()), None), 30)
            try:
                focus(prompt_hwnd)
            except Exception:
                pass
            send_keys("{ENTER}"); time.sleep(.6)
        note("All three recovery drafts are offered and accepted")

        # Recovery restores as copies without a save path.
        select_engine(main_window, 1)
        if "recovery-native" not in win32gui.GetWindowText(main_window.handle):
            raise AssertionError("native recovery did not restore")
        select_engine(main_window, 2)
        if "recovery-4t0d" not in win32gui.GetWindowText(main_window.handle):
            raise AssertionError("4T 0D recovery did not restore")
        select_engine(main_window, 0)
        if "recovery-2t" not in win32gui.GetWindowText(main_window.handle):
            raise AssertionError("2T recovery did not restore")
        note("Recovered drafts restore in 2T, 4T 0D and native 4T modes")

        for index, title in ((0, "Guardar proyecto como"),
                             (1, "Guardar motor 4T nativo"),
                             (2, "Guardar proyecto 4T como")):
            select_engine(main_window, index)
            try:
                focus(main_window.handle)
            except Exception:
                pass
            send_keys("^s")
            dialog = wait(lambda: next((h for h, caption in windows(process)
                                        if title.lower() in caption.lower()), None), 10)
            win32gui.PostMessage(dialog, win32con.WM_CLOSE, 0, 0)
            time.sleep(.4)
        note("Recovered drafts require Save As in all three modes (no original path bound)")

        for family, value in originals.items():
            if sha256(value["path"]) != value["sha256"]:
                raise AssertionError(f"recovery overwrote original {family}")
        note("Recovery did not modify any original project file")

        win32gui.PostMessage(main_window.handle, win32con.WM_CLOSE, 0, 0)
        dismiss_discard(process)
        run2 = work / "run2"; run2.mkdir()
        record = finalize_acceptance(run2, {
            "schema": "DINO_C05_COMMERCIAL_INTEGRATED_RUN_V1", "phase": "recovery",
            "exe": str(exe), "exe_sha256": sha256(exe),
            "checks": list(checks),
        }, process=process, timeout=20)
        if record["result"] != "PASS":
            raise RuntimeError(f"second process terminal check: {record['terminal_verification']}")
        if process.poll() is None:
            raise AssertionError("second Dino2T process remained alive after terminal wait")
    finally:
        if process.poll() is None:
            process.terminate()

    if default_worker_probe():
        raise AssertionError("orphan MotorSimWorker.exe after integrated acceptance")
    receipt = {
        "schema": "DINO_C05_COMMERCIAL_INTEGRATED_ACCEPTANCE_V1",
        "result": "PASS", "exe": str(exe), "exe_sha256": sha256(exe),
        "checks": checks,
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
