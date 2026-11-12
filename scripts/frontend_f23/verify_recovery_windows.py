"""External packaged recovery acceptance using UIA Invoke, without global keys."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading
ROOT=Path(os.environ.get('DINO_FRONTEND_SOURCE_ROOT',Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(ROOT))
import win32gui,win32process,win32con
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.uia_element_info import UIAElementInfo
from motorsim.desktop.services import new_design_project
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.four_stroke_project import starter_project,save_project as save_reference
from motorsim.engine_project import save_project


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path,required=True);parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args();args.work.mkdir(parents=True,exist_ok=False);checks={};records=[]
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def wait(fn,seconds=40):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=fn()
            if value:return value
            time.sleep(.2)
        raise TimeoutError('UIA Invoke acceptance timeout')
    for family in ('2T','4T0D','4Tnative'):
        work=args.work/family;work.mkdir();env=os.environ.copy()
        for key,name in [('DINO_TEST_SETTINGS_ROOT','settings'),('DINO_ARTIFACT_ROOT','artifacts'),('DINO_LICENSE_ROOT','licenses'),('DINO_RECOVERY_ROOT','recovery'),('LOCALAPPDATA','local'),('USERPROFILE','profile')]:
            (work/name).mkdir();env[key]=str(work/name)
        original=work/'original.json'
        if family=='2T':project=new_design_project('recovery-2T');save_project(original,project)
        elif family=='4Tnative':project=project_from_example('recovery-native');save_project(original,project)
        else:
            doc=starter_project(name='recovery-reference',rpm=3000);save_reference(original,doc);project=doc.to_dict()
        digest=sha(original)
        payload=dict(schema='DINO_RECOVERY_V1',family=family,project_id=project.get('project_id',project.get('name')),original_path=str(original),saved_at='2026-11-12T00:00:00+00:00',project=project)
        (work/'recovery'/f'{family}-seed.json').write_text(json.dumps(payload),encoding='utf-8')
        for key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):env.pop(key,None)
        p=subprocess.Popen([str(args.exe.resolve())],cwd=work,env=env)
        def windows():
            found=[]
            def visit(h,_):
                if win32gui.IsWindowVisible(h) and win32process.GetWindowThreadProcessId(h)[1]==p.pid:
                    found.append((h,win32gui.GetWindowText(h)))
            win32gui.EnumWindows(visit,None);return found
        def locate(fragment):return next((h for h,t in windows() if fragment.casefold() in t.casefold()),None)
        def controls(handle):return UIAWrapper(UIAElementInfo(handle)).descendants()
        def press(handle,fragments):
            buttons=[x for x in controls(handle) if x.element_info.control_type=='Button']
            button=next((x for x in buttons if any(f in x.window_text().replace('&','').casefold() for f in fragments)),None)
            if button is None:raise RuntimeError('UIA button missing: '+repr([x.window_text() for x in buttons]))
            button.invoke()
        try:
            prompt=wait(lambda:locate('Borradores de recuperación'))
            press(prompt,('abrir copia recuperada',))
            expected={'2T':'recovery-2T','4T0D':'recovery-reference','4Tnative':'recovery-native'}[family]
            main_handle=wait(lambda:next((h for h,t in windows() if expected in t),None))
            checks[family+'_restored']=True
            print('PASS',family,'restored by actual recovery prompt',flush=True)
            # Trigger the actual common Save button. A recovered copy must ask
            # for a new path instead of writing to original_path.
            save=wait(lambda:next((x for x in controls(main_handle) if x.element_info.control_type=='Button' and x.window_text().replace('&','').casefold()=='guardar'),None))
            errors=[]
            def invoke_save():
                import pythoncom
                pythoncom.CoInitializeEx(0)
                try:save.invoke()
                except Exception as exc:errors.append(str(exc))
                finally:pythoncom.CoUninitialize()
            thread=threading.Thread(target=invoke_save,daemon=True);thread.start()
            caption={'2T':'Guardar proyecto como','4T0D':'Guardar proyecto 4T como','4Tnative':'Guardar motor 4T nativo'}[family]
            dialog=wait(lambda:next((h for h,t in windows() if h!=main_handle and caption.casefold() in t.casefold()),None))
            checks[family+'_requires_save_as']=True
            win32gui.PostMessage(dialog,win32con.WM_CLOSE,0,0)
            wait(lambda:not (win32gui.IsWindow(dialog) and win32gui.IsWindowVisible(dialog)));thread.join(timeout=10)
            if errors:raise RuntimeError(str(errors))
            checks[family+'_original_intact']=sha(original)==digest
            if not checks[family+'_original_intact']:raise AssertionError('Recovery overwrote original')
            win32gui.PostMessage(main_handle,win32con.WM_CLOSE,0,0)
            deadline=time.monotonic()+20
            while p.poll() is None and time.monotonic()<deadline:
                changed=locate('Cambios')
                if changed:press(changed,('descart','discard','no guardar'))
                time.sleep(.2)
            code=p.wait(timeout=10);checks[family+'_closed']=code==0
            records.append(dict(family=family,exit_code=code,original_sha256=digest))
            print('PASS',family,'Save As, original bytes and clean exit',flush=True)
        finally:
            if p.poll() is None:p.terminate();p.wait(timeout=10)
    result=dict(schema='DINO_PACKAGED_RECOVERY_UIA_V1',result='PASS' if all(checks.values()) else 'FAIL',checks=checks,processes=records,exe=str(args.exe),exe_sha256=sha(args.exe),method='External UIA Invoke and scoped WM_CLOSE; no global input/focus or filename typing',scientific_validation='NOT_PERFORMED')
    (args.work/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False));return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
