import ast
import ctypes
import os
from pathlib import Path
import runpy
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

from dev_orchestrator.contracts import BASE
from dev_orchestrator.runners.run_tests import run_command,run_pytest


def alive(pid):
    if os.name=='nt':
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; kernel.OpenProcess.restype=w.HANDLE
        kernel.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
        kernel.CloseHandle.argtypes=[w.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle: return False
        try:
            code=w.DWORD()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally: kernel.CloseHandle(handle)
    try: os.kill(pid,0); return True
    except ProcessLookupError: return False


class ProcessIsolationTests(unittest.TestCase):
    def test_runtime_no_orchestrator_imports(self):
        for path in (BASE.parent/'motorsim').rglob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
                self.assertFalse(any(n.split('.')[0]=='dev_orchestrator' for n in names),str(path))

    def test_packaging_excludes_both_entrypoints(self):
        calls=[]
        def analysis(*args,**kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(datas=[],binaries=[],pure=[],scripts=[])
        spec=BASE.parent/'packaging/MotorSim.spec'
        with patch.dict(os.environ,{'MOTORSIM_BUILD_INPUTS':str(BASE.parent/'build/windows/mock-inputs')}):
            runpy.run_path(str(spec),init_globals=dict(SPECPATH=str(spec.parent),Analysis=analysis,
                PYZ=lambda *a,**k:None,EXE=lambda *a,**k:None,COLLECT=lambda *a,**k:None))
        self.assertEqual(len(calls),2)
        for c in calls:
            self.assertIn('dev_orchestrator',c['excludes'])
            self.assertFalse(any('dev_orchestrator' in str(x) for x in c['datas']))
        build=(BASE.parent/'packaging/build_windows.py').read_text(encoding='utf-8')
        self.assertIn("'dev_orchestrator' in part.lower()",build)

    def test_timeout_and_cancellation_kill_descendants(self):
        for cancelled in (False,True):
            with self.subTest(cancelled=cancelled),tempfile.TemporaryDirectory() as folder:
                root=Path(folder); pidfile=root/'pid.txt'; event=threading.Event()
                script="import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); pathlib.Path('pid.txt').write_text(str(p.pid)); time.sleep(30)"
                def trigger():
                    end=time.monotonic()+5
                    while not pidfile.exists() and time.monotonic()<end: time.sleep(.01)
                    event.set()
                thread=threading.Thread(target=trigger) if cancelled else None
                if thread: thread.start()
                result=run_command([sys.executable,'-c',script],cwd=root,logs=root/'logs',name='tree',timeout=2,cancel=event)
                if thread: thread.join(timeout=6)
                self.assertEqual(result['status'],'cancelled' if cancelled else 'timeout')
                self.assertTrue(pidfile.exists()); pid=int(pidfile.read_text())
                end=time.monotonic()+3
                while alive(pid) and time.monotonic()<end: time.sleep(.02)
                self.assertFalse(alive(pid),'El descendiente sobrevivió al cierre del Job/grupo')

    def test_stdout_stderr_and_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_command([sys.executable,'-c',"import sys; print('out'); print('err',file=sys.stderr); sys.exit(7)"],
                cwd=folder,logs=Path(folder)/'logs',name='exit',timeout=3)
            self.assertEqual(result['returncode'],7); self.assertEqual(result['status'],'failed')
            self.assertIn('out',Path(result['stdout_log']).read_text()); self.assertIn('err',Path(result['stderr_log']).read_text())

    def test_pytest_full_and_subset_are_subprocess_commands(self):
        with patch('dev_orchestrator.runners.run_tests.run_command',return_value={'status':'passed'}) as command:
            run_pytest(cwd=BASE,logs=BASE/'runs')
            self.assertEqual(command.call_args.args[0],[sys.executable,'-m','pytest'])
            run_pytest(['tests/test_x.py','-k','case'],cwd=BASE,logs=BASE/'runs',timeout=7)
            self.assertEqual(command.call_args.args[0][-3:],['tests/test_x.py','-k','case'])
            self.assertEqual(command.call_args.kwargs['timeout'],7)
