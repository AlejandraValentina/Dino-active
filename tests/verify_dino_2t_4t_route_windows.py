"""Check 2T/4T project routing in the packaged Windows desktop without solver work."""
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

from motorsim.desktop.acceptance_terminal import finalize_acceptance

import win32con
import win32gui
import win32process
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.uia_element_info import UIAElementInfo


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True)
    parser.add_argument("--project-2t",type=Path,required=True)
    parser.add_argument("--project-4t",type=Path,required=True)
    parser.add_argument("--work",type=Path,required=True)
    args=parser.parse_args()
    exe=args.exe.resolve();project2=args.project_2t.resolve();project4=args.project_4t.resolve();work=args.work.resolve()
    for path in (exe,project2,project4):
        if not path.is_file():raise FileNotFoundError(path)
    work.mkdir(parents=True,exist_ok=False)
    for name in ("settings","artifacts","localappdata"): (work/name).mkdir()
    env=os.environ.copy()
    for key in ("PYTHONPATH","PYTHONHOME","VIRTUAL_ENV","QT_PLUGIN_PATH","QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(key,None)
    env.update(QT_QPA_PLATFORM="windows",DINO_TEST_SETTINGS_ROOT=str(work/"settings"),
        DINO_ARTIFACT_ROOT=str(work/"artifacts"),LOCALAPPDATA=str(work/"localappdata"),
        PATH=os.environ["SystemRoot"]+"\\System32")
    cwd=work/"different working directory";cwd.mkdir()
    process=subprocess.Popen([str(exe)],cwd=cwd,env=env)
    checks=[];captures=[]

    def app_windows():
        found=[]
        def visit(hwnd,_):
            if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1]==process.pid:
                found.append(hwnd)
        win32gui.EnumWindows(visit,None)
        return found

    def wait(fn,seconds=25):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            time.sleep(.15)
        raise TimeoutError("timed out waiting for packaged UI state")

    def main_window(fragment):
        hwnd=wait(lambda:next((h for h in app_windows()
            if fragment.lower() in win32gui.GetWindowText(h).lower()),None))
        return UIAWrapper(UIAElementInfo(hwnd))

    def descendants(window):
        try:return window.descendants()
        except Exception:return []

    def button(window,fragment):
        return next(x for x in descendants(window) if x.element_info.control_type=="Button"
            and fragment.lower() in x.window_text().lower())

    def select_project(path,dialog_fragment):
        dialog_hwnd=wait(lambda:next((h for h in app_windows()
            if dialog_fragment.lower() in win32gui.GetWindowText(h).lower()),None),seconds=15)
        dialog=UIAWrapper(UIAElementInfo(dialog_hwnd))
        edit=next(x for x in descendants(dialog) if x.element_info.control_type=="Edit"
            and x.element_info.automation_id=="1148")
        edit.set_edit_text(str(path))
        action=next(x for x in descendants(dialog) if x.element_info.control_type=="Button"
            and x.element_info.automation_id=="1")
        action.invoke()
        wait(lambda:dialog_hwnd not in app_windows(),seconds=15)

    def open_project(window,path,first=False):
        title=win32gui.GetWindowText(window.handle)
        # The 2T shell says "Abrir proyecto…"; the 4T shell shortens this to
        # "Abrir…". Both use the same native project router.
        button(window,"Abrir proyecto" if "4T" not in title else "Abrir…").invoke()
        select_project(path,"Abrir proyecto")

    def capture(window,name,size):
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance() or QApplication([])
        win32gui.ShowWindow(window.handle,win32con.SW_RESTORE)
        win32gui.SetWindowPos(window.handle,win32con.HWND_TOPMOST,25,25,*size,win32con.SWP_SHOWWINDOW)
        time.sleep(.3)
        left,top,right,bottom=win32gui.GetWindowRect(window.handle)
        path=work/(name+".png")
        if not app.primaryScreen().grabWindow(0,left,top,right-left,bottom-top).save(str(path)):
            raise RuntimeError("failed to save packaged UI screenshot")
        captures.append({"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_px":[right-left,bottom-top]})

    def note(message):checks.append(message);print("PASS",message,flush=True)

    try:
        build=json.loads((exe.parent/"build.json").read_text(encoding="utf-8"))
        window=main_window("Dino 2T")
        visible=wait(lambda:app_windows() if len(app_windows())==1 else None,seconds=10)
        open_project(window,project2,first=True)
        window=main_window("dino-exhaust-comparison-starter")
        if "dino-exhaust-comparison-starter" not in win32gui.GetWindowText(window.handle):
            raise AssertionError("packaged Desktop did not route the existing native 2T project")
        if not any(x.window_text()=="MODELO" for x in descendants(window)):
            raise AssertionError("2T model workspace is missing from packaged desktop")
        note("Packaged app opens the existing native 2T project in MODELO without solver work")
        capture(window,"packaged-2t-project-1360x900",(1360,900))
        open_project(window,project4)
        window=main_window("4T")
        if "4T" not in win32gui.GetWindowText(window.handle):
            raise AssertionError("packaged project router did not switch to the 4T workspace")
        note("The same packaged app routes the native 4T project to the 4T workspace")
        open_project(window,project2)
        window=main_window("dino-exhaust-comparison-starter")
        if "dino-exhaust-comparison-starter" not in win32gui.GetWindowText(window.handle):
            raise AssertionError("packaged project router did not return to the 2T workspace")
        if len(app_windows())!=1:raise AssertionError("switching engine projects opened an extra app window")
        note("The same process returns to the saved 2T project with one main window")
        payload={"schema":"DINO_2T_4T_PACKAGED_ROUTING_ACCEPTANCE_V1",
            "exe":str(exe),"exe_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),
            "project_2t":str(project2),"project_2t_sha256":hashlib.sha256(project2.read_bytes()).hexdigest(),
            "project_4t":str(project4),"project_4t_sha256":hashlib.sha256(project4.read_bytes()).hexdigest(),
            "build":{"source_commit":build.get("source_commit"),"packaged_inputs_clean":build.get("packaged_inputs_clean"),
                "manifest_sha256":build.get("packaged_input_manifest_sha256"),"version":build.get("app_version")},
            "checks":checks,"captures":captures,"solver_runs":0}
        win32gui.PostMessage(window.handle,win32con.WM_CLOSE,0,0)
        record=finalize_acceptance(work,payload,process=process,timeout=15)
        if record["result"]!="PASS":
            raise RuntimeError(f"terminal acceptance {record['result']}: {record['terminal_verification']['issues']}")
        print(json.dumps({"result":"PASS","acceptance":str(work/"acceptance.json"),"checks":checks},ensure_ascii=False))
        return 0
    except Exception as exc:
        (work/"failure.txt").write_text(repr(exc),encoding="utf-8")
        raise
    finally:
        if process.poll() is None:process.terminate()


if __name__=="__main__":raise SystemExit(main())
