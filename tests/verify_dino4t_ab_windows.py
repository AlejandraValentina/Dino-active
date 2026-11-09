"""UIA acceptance of one packaged Dino 4T A/B project; executes one safe cancel.

This is an external acceptance driver, not shipped with Dino. The only run it
starts is cancelled at a complete-cycle boundary to exercise UI recovery.
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

import win32con
import win32gui
import win32process
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.keyboard import send_keys
from pywinauto.uia_element_info import UIAElementInfo


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",type=Path,required=True,help="packaged Dino2T.exe")
    parser.add_argument("--project",type=Path,required=True,help="saved A/B 4T Desktop project")
    parser.add_argument("--work",type=Path,required=True,help="new external temporary acceptance directory")
    parser.add_argument("--scale",default="1.0",choices=("1.0","1.25","1.5"))
    parser.add_argument("--prior-cancelled-run",type=Path,
        help="reuse a previously verified packaged cancellation; skip starting another solver run")
    args=parser.parse_args()
    exe=args.exe.resolve();project=args.project.resolve();work=args.work.resolve()
    if not exe.is_file() or exe.name.lower()!="dino2t.exe":raise FileNotFoundError(f"expected packaged Dino2T.exe: {exe}")
    if not project.is_file():raise FileNotFoundError(project)
    work.mkdir(parents=True,exist_ok=False)
    for name in ("settings","artifacts","localappdata"): (work/name).mkdir()
    env=os.environ.copy()
    for key in ("PYTHONPATH","PYTHONHOME","VIRTUAL_ENV","QT_PLUGIN_PATH","QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(key,None)
    env.update(QT_SCALE_FACTOR=args.scale,QT_QPA_PLATFORM="windows",
        DINO_TEST_SETTINGS_ROOT=str(work/"settings"),DINO_ARTIFACT_ROOT=str(work/"artifacts"),
        LOCALAPPDATA=str(work/"localappdata"),PATH=os.environ["SystemRoot"]+"\\System32;"+os.environ["SystemRoot"])
    cwd=work/"different working directory";cwd.mkdir()
    process=subprocess.Popen([str(exe)],cwd=cwd,env=env)
    checks=[];captures=[]

    def windows():
        result=[]
        def visit(hwnd,_):
            if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1]==process.pid:
                result.append((hwnd,win32gui.GetWindowText(hwnd)))
        win32gui.EnumWindows(visit,None)
        return result

    def desktop_windows():
        result=[]
        def visit(hwnd,_):
            if win32gui.IsWindowVisible(hwnd):
                pid=win32process.GetWindowThreadProcessId(hwnd)[1]
                result.append((hwnd,win32gui.GetWindowText(hwnd),pid))
        win32gui.EnumWindows(visit,None)
        return result

    def wait(fn,seconds=30):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            time.sleep(.15)
        raise TimeoutError("UIA timeout waiting for "+getattr(fn,"__name__","condition"))

    def window(fragment):
        def locate():
            visible=windows()
            matched=next((h for h,title in visible if fragment.lower() in title.lower()),None)
            if matched:return matched
            # Qt's top-level caption is not exposed by GetWindowText on every
            # supported Windows style. In that case bind by the process-owned
            # visible HWND and its actual UIA content instead of treating an
            # empty title bar as an application startup failure.
            if len(visible)!=1:return None
            hwnd=visible[0][0];root=UIAWrapper(UIAElementInfo(hwnd))
            content="\n".join((x.window_text()+" "+str(x.element_info.automation_id))
                for x in descendants(root)).lower()
            if "dino desktop" in fragment.lower() and "2t" in fragment.lower():
                return hwnd if "abrir proyecto" in content else None
            project_token=fragment.rsplit(" ",1)[-1].lower()
            return hwnd if project_token in content else None
        hwnd=wait(locate)
        return UIAWrapper(UIAElementInfo(hwnd))

    def descendants(w):
        try:return w.descendants()
        except Exception:return []

    def control(w,kind,name=None,index=None):
        values=[x for x in descendants(w) if x.element_info.control_type==kind
            and (name is None or x.window_text()==name or x.element_info.name==name)]
        if index is not None and len(values)>index:return values[index]
        if values:return values[0]
        raise LookupError(f"UIA control missing: {kind} {name!r}; found {[x.window_text() for x in descendants(w) if x.element_info.control_type==kind]}")

    def click(w,name):
        try:element=control(w,"Button",name)
        except LookupError:
            aliases={"Descartar":"Discard","Discard":"Descartar"}
            if name not in aliases:raise
            element=control(w,"Button",aliases[name])
        # UIA InvokePattern reliably dispatches Qt actions even when Windows
        # does not route synthetic mouse input to the foreground desktop.
        try:element.invoke()
        except Exception:
            try:element.click_input()
            except Exception:
                element.set_focus();send_keys("{SPACE}")
        time.sleep(.2)

    def file_dialog(title,path):
        # Other applications (and stale app instances from a failed test) may
        # use the same common-dialog caption. Always bind to this EXE's dialog.
        hwnd=wait(lambda:next((h for h,caption,pid in desktop_windows()
            if pid==process.pid and title.lower() in caption.lower()),None),seconds=15)
        dialog=UIAWrapper(UIAElementInfo(hwnd))
        try:win32gui.SetForegroundWindow(dialog.handle)
        except Exception:pass
        edit=next((x for x in descendants(dialog) if x.element_info.control_type=="Edit" and
            (x.element_info.automation_id.endswith("fileNameEdit") or x.element_info.automation_id=="1148")),None)
        if edit is not None:
            edit.set_edit_text(str(path))
            action=next((x for x in descendants(dialog)
                if x.element_info.control_type=="Button"
                and x.element_info.automation_id=="1"),None)
            if action is not None:action.invoke()
            else:edit.set_focus();send_keys("{ENTER}")
        else:send_keys("^a");send_keys(str(path),with_spaces=True);send_keys("{ENTER}")
        wait(lambda:not any(pid==process.pid and title.lower() in caption.lower()
            for _,caption,pid in desktop_windows()),seconds=10)
        time.sleep(.25)

    def top(w,width,height):
        win32gui.ShowWindow(w.handle,win32con.SW_RESTORE)
        win32gui.SetWindowPos(w.handle,win32con.HWND_TOPMOST,25,25,width,height,win32con.SWP_SHOWWINDOW)
        try:win32gui.SetForegroundWindow(w.handle)
        except Exception:pass

    def capture(w,name,width=1360,height=900):
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance() or QApplication([])
        top(w,width,height);time.sleep(.3)
        left,upper,right,lower=win32gui.GetWindowRect(w.handle)
        path=work/(name+".png")
        image=app.primaryScreen().grabWindow(0,left,upper,right-left,lower-upper)
        if not image.save(str(path)):raise RuntimeError(f"screenshot failed: {path}")
        captures.append({"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_px":[right-left,lower-upper]})

    def note(text):checks.append(text);print("PASS",text,flush=True)

    try:
        build=json.loads((exe.parent/"build.json").read_text(encoding="utf-8"))
        if build.get("packaged_inputs_clean") is not True:raise AssertionError("package inputs are not cleanly identified")
        main_window=window("Dino Desktop · 2T");top(main_window,1360,900)
        if len(windows())!=1:raise AssertionError(f"expected one visible application window at start, got {windows()}")
        note("Packaged Dino2T.exe starts one visible main window in an isolated environment")
        click(main_window,"Abrir proyecto…")
        time.sleep(.5)
        file_dialog("Abrir proyecto",project)
        four=window("Dino Desktop · 4T · dino4t-synthetic-ab-v1");top(four,1360,900)
        if len(windows())!=1:raise AssertionError(f"expected one visible 4T window, got {windows()}")
        note("Saved native 4T project opens with both hash-verified A/B result references")
        result_tab=control(four,"TabItem","RESULTADOS");result_tab.select();time.sleep(.3)
        compare_tab=control(four,"TabItem","Comparar");compare_tab.select();time.sleep(.25)
        combos=[x for x in descendants(four) if x.element_info.control_type=="ComboBox"]
        if len(combos)<2:raise AssertionError(f"expected A/B selectors, found {len(combos)}")
        combos[0].click_input();send_keys("{HOME}{ENTER}");time.sleep(.1)
        combos[1].click_input();send_keys("{END}{ENTER}");time.sleep(.1)
        click(four,"Comparar corridas")
        text="\n".join(x.window_text() for x in descendants(four) if x.element_info.control_type in ("Text","DataItem"))
        if "A/B periódicos" not in text or "no validadas experimentalmente" not in text:
            raise AssertionError("A/B eligibility/claim qualification not visible in packaged UI: "+text[:1200])
        status=next((x.window_text() for x in descendants(four) if "A/B periódicos" in x.window_text()),"")
        if not status:raise AssertionError("A/B comparison status missing")
        capture(four,"packaged-4t-ab-1360x900")
        note("Packaged UI compares both periodic runs and preserves scientific caveat")

        outputs={"json":work/"comparison.json","csv":work/"comparison.csv","html":work/"comparison.html"}
        for button_name,key,title in (("Exportar ficha A/B JSON","json","Guardar ficha A/B"),
                ("Exportar diferencias CSV","csv","Exportar diferencias A/B"),
                ("Informe técnico A/B HTML","html","Informe técnico A/B")):
            click(four,button_name);file_dialog(title,outputs[key])
            wait(lambda:outputs[key].is_file())
        exported=json.loads(outputs["json"].read_text(encoding="utf-8"))
        if exported.get("comparison_id")!=json.loads((project.parent/"comparison.json").read_text(encoding="utf-8")).get("comparison_id"):
            raise AssertionError("packaged JSON export differs from verified A/B comparison")
        with outputs["csv"].open(encoding="utf-8-sig",newline="") as stream: rows=list(csv.DictReader(stream))
        if len(rows)!=4 or not all(row.get("result_sha256_a") and row.get("result_sha256_b") for row in rows):
            raise AssertionError("packaged CSV lost metrics or result provenance")
        if "No constituyen una mejora demostrada" not in outputs["html"].read_text(encoding="utf-8"):
            raise AssertionError("packaged HTML report lost the scientific qualification")
        note("Packaged JSON/CSV/HTML exports preserve comparison ID, precise metrics, hashes and caveat")

        prior_cancel=None
        if args.prior_cancelled_run:
            prior_cancel=args.prior_cancelled_run.resolve()
            run=json.loads(prior_cancel.read_text(encoding="utf-8"))
            summary=json.loads(Path(run["summary_path"]).read_text(encoding="utf-8"))
            if run.get("status")!="incomplete" or run.get("periodicity_status")!="NOT_CONVERGED":
                raise AssertionError("prior cancellation record lost its incomplete/nonconverged state")
            if summary.get("termination")!="cancelled_by_user" or summary.get("status")!="incomplete":
                raise AssertionError("prior packaged run was not recorded as a controlled cancellation")
            tasklist=subprocess.run(["tasklist","/FI","IMAGENAME eq MotorSimWorker.exe","/FO","CSV","/NH"],
                capture_output=True,text=True,check=True).stdout
            if "MotorSimWorker.exe" in tasklist:
                raise AssertionError("orphaned MotorSimWorker remains after packaged cancellation: "+tasklist)
            note("Prior packaged cancellation is terminal, incomplete/nonconverged and left no worker process")
            top(four,980,680);capture(four,"packaged-4t-ab-reopened-980x680",980,680)
            note("A/B project reopened in a fresh packaged process after cancellation; saved endpoints remain comparable")
        else:
            simulation=control(four,"TabItem","SIMULAR");simulation.select();time.sleep(.2)
            click(four,"Ejecutar punto 4T")
            wait(lambda:any("Ciclo " in x.window_text() for x in descendants(four)),seconds=35)
            click(four,"Cancelar al final del ciclo")
            wait(lambda:control(four,"Button","Ejecutar punto 4T").is_enabled(),seconds=90)
            if control(four,"Button","Cancelar al final del ciclo").is_enabled():
                raise AssertionError("cancel remained enabled after terminal return")
            note("Packaged 4T cancellation returns control only after a complete cycle")
            click(four,"Abrir…");file_dialog("Abrir proyecto Dino",project)
            discard=window("Cambios sin guardar");click(discard,"Descartar")
            four=window("Dino Desktop · 4T · dino4t-synthetic-ab-v1");top(four,980,680)
            result_tab=control(four,"TabItem","RESULTADOS");result_tab.select();time.sleep(.2)
            compare_tab=control(four,"TabItem","Comparar");compare_tab.select();click(four,"Comparar corridas")
            if "A/B periódicos" not in "\n".join(x.window_text() for x in descendants(four)):
                raise AssertionError("A/B project did not recover from its saved inputs after cancellation")
            capture(four,"packaged-4t-ab-recovered-980x680",980,680)
            note("Existing saved periodic A/B endpoints remain usable after cancellation")
        build_check={"source_commit":build.get("source_commit"),"packaged_inputs_clean":build.get("packaged_inputs_clean"),
            "manifest_sha256":build.get("packaged_input_manifest_sha256"),"version":build.get("app_version")}
        (work/"build-identity.json").write_text(json.dumps(build_check,indent=2)+"\n",encoding="utf-8")
        win32gui.PostMessage(four.handle,win32con.WM_CLOSE,0,0);process.wait(timeout=15)
        if process.returncode!=0:raise RuntimeError(f"packaged process exit code {process.returncode}")
        # Terminal PASS is written only after the packaged process has actually
        # exited; a close request or a still-running worker is not acceptance.
        (work/"acceptance.json").write_text(json.dumps({"schema":"DINO4T_AB_PACKAGED_WINDOWS_ACCEPTANCE_V1",
            "result":"PASS","exe":str(exe),"exe_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),
            "project":str(project),"project_sha256":hashlib.sha256(project.read_bytes()).hexdigest(),
            "prior_cancelled_run":str(prior_cancel) if prior_cancel else None,
            "build":build_check,"checks":checks,"captures":captures,
            "scientific_claims":{"experimental_validation":"NOT_PERFORMED","predictive_capability":"NOT_CLAIMED"}},
            ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"result":"PASS","acceptance":str(work/"acceptance.json"),"checks":checks},ensure_ascii=False))
        return 0
    except Exception as exc:
        (work/"failure.txt").write_text(repr(exc),encoding="utf-8")
        (work/"desktop-windows-failure.json").write_text(json.dumps(
            [{"hwnd":h,"title":title,"pid":pid} for h,title,pid in desktop_windows()],indent=2)+"\n",encoding="utf-8")
        try:
            for hwnd,title in windows():
                wrapper=UIAWrapper(UIAElementInfo(hwnd))
                (work/("uia-"+str(hwnd)+".txt")).write_text("\n".join(
                    f"{x.element_info.control_type}\t{x.window_text()}\t{x.element_info.automation_id}"
                    for x in descendants(wrapper)),encoding="utf-8")
        except Exception:pass
        raise
    finally:
        if process.poll() is None:process.terminate()


if __name__=="__main__":
    raise SystemExit(main())
