"""Subprocess acotado; pytest completo/subset sin importar sus internals."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time

from .process_tree import ProcessTree


def run_command(argv, *, cwd, logs, name, timeout, kind='command', cancel=None):
    if timeout<=0: raise ValueError('Timeout positivo requerido')
    cancel=cancel or threading.Event()
    logs=Path(logs); logs.mkdir(parents=True,exist_ok=True)
    out,err=logs/(name+'.stdout.log'),logs/(name+'.stderr.log')
    started=time.monotonic(); tree=None
    result=dict(id=name,argv=list(argv),kind=kind,returncode=None,duration_seconds=0.,status='error',
                stdout_log=str(out),stderr_log=str(err),error='')
    try:
        with out.open('xb') as stdout,err.open('xb') as stderr:
            if argv[:3]==[sys.executable,'-m','pytest'] and importlib.util.find_spec('pytest') is None:
                raise OSError('pytest no está instalado en el intérprete de desarrollo.')
            if cancel.is_set(): result.update(status='cancelled',error='cancelled_by_user')
            else:
                tree=ProcessTree(argv,cwd,stdout,stderr)
                while tree.process.poll() is None:
                    if cancel.is_set(): result.update(status='cancelled',error='cancelled_by_user'); break
                    if time.monotonic()-started>=timeout: result.update(status='timeout',error='command_timeout'); break
                    time.sleep(.02)
                else:
                    code=tree.process.returncode
                    result.update(status='passed' if code==0 else 'failed',returncode=code)
                    if code==125: result.update(status='error',error='process_host_failed')
    except KeyboardInterrupt:
        cancel.set(); result.update(status='cancelled',error='cancelled_by_user')
    except OSError as exc:
        result.update(status='error',error=f'{type(exc).__name__}: {exc}')
    finally:
        if tree:
            tree.close()
            if result['returncode'] is None: result['returncode']=tree.process.returncode
        result['duration_seconds']=time.monotonic()-started
    return result


def run_pytest(paths=(), *, cwd, logs, timeout=30, cancel=None):
    return run_command([sys.executable,'-m','pytest',*paths],cwd=cwd,logs=logs,
                       name='pytest',timeout=timeout,kind='test',cancel=cancel)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout',type=float,default=30)
    parser.add_argument('--logs',type=Path,required=True)
    parser.add_argument('paths',nargs='*')
    args=parser.parse_args()
    result=run_pytest(args.paths,cwd=Path.cwd(),logs=args.logs,timeout=args.timeout)
    print(json.dumps(result,indent=2)); return 0 if result['status']=='passed' else 1


if __name__=='__main__': raise SystemExit(main())
