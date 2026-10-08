"""Grupo POSIX o Job Windows kill-on-close; no mata procesos ajenos."""
import os
import signal
import subprocess
import sys
import time


class ProcessTree:
    def __init__(self, argv, cwd, stdout, stderr):
        self.process=None; self.job=None
        if os.name!='nt':
            self.process=subprocess.Popen(argv,cwd=cwd,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            return
        import ctypes as c
        from ctypes import wintypes as w
        class Basic(c.Structure):
            _fields_=[('PerProcessUserTimeLimit',c.c_longlong),('PerJobUserTimeLimit',c.c_longlong),
                ('LimitFlags',w.DWORD),('MinimumWorkingSetSize',c.c_size_t),('MaximumWorkingSetSize',c.c_size_t),
                ('ActiveProcessLimit',w.DWORD),('Affinity',c.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
        class IO(c.Structure): _fields_=[(x,c.c_ulonglong) for x in ('read','write','other','read_bytes','write_bytes','other_bytes')]
        class Extended(c.Structure):
            _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',c.c_size_t),
                ('JobMemoryLimit',c.c_size_t),('PeakProcessMemoryUsed',c.c_size_t),('PeakJobMemoryUsed',c.c_size_t)]
        self.kernel=c.WinDLL('kernel32',use_last_error=True)
        k=self.kernel
        k.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR]; k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]; k.SetInformationJobObject.restype=w.BOOL
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]; k.AssignProcessToJobObject.restype=w.BOOL
        k.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]; k.TerminateJobObject.restype=w.BOOL
        k.QueryInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.c_void_p]; k.QueryInformationJobObject.restype=w.BOOL
        k.CloseHandle.argtypes=[w.HANDLE]; k.CloseHandle.restype=w.BOOL
        self.job=k.CreateJobObjectW(None,None)
        if not self.job: raise c.WinError(c.get_last_error())
        try:
            limits=Extended(); limits.BasicLimitInformation.LimitFlags=0x2000
            if not k.SetInformationJobObject(self.job,9,c.byref(limits),c.sizeof(limits)): raise c.WinError(c.get_last_error())
            # El host no lanza comandos hasta recibir GO; evita la carrera de asignación.
            from pathlib import Path
            host=Path(__file__).with_name('process_host.py')
            self.process=subprocess.Popen([sys.executable,str(host),*argv],cwd=cwd,stdin=subprocess.PIPE,
                stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
            if not k.AssignProcessToJobObject(self.job,w.HANDLE(int(self.process._handle))): raise c.WinError(c.get_last_error())
            self.process.stdin.write(b'GO\n'); self.process.stdin.flush(); self.process.stdin.close()
        except BaseException:
            if self.process and self.process.poll() is None:
                self.process.kill(); self.process.wait(timeout=5)
            self.close()
            raise

    def close(self):
        if os.name=='nt':
            if self.job:
                import ctypes as c
                from ctypes import wintypes as w
                try:
                    if not self.kernel.TerminateJobObject(self.job,1): raise c.WinError(c.get_last_error())
                    # BASIC_ACCOUNTING_INFORMATION: cuatro LARGE_INTEGER y cuatro DWORD.
                    info=c.create_string_buffer(48); deadline=time.monotonic()+5
                    while True:
                        if not self.kernel.QueryInformationJobObject(self.job,1,info,48,None): raise c.WinError(c.get_last_error())
                        if w.DWORD.from_buffer(info,40).value==0: break
                        if time.monotonic()>=deadline: raise TimeoutError('Job descendants did not terminate within cleanup timeout')
                        time.sleep(.01)
                finally:
                    self.kernel.CloseHandle(self.job); self.job=None
        elif self.process:
            try: os.killpg(self.process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        if self.process and self.process.poll() is None: self.process.wait(timeout=5)
