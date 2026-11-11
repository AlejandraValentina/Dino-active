"""Supervise only this acceptance process tree and persist terminal evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil


def main():
    split=sys.argv.index('--')
    parser=argparse.ArgumentParser()
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=600)
    args=parser.parse_args(sys.argv[1:split]);command=sys.argv[split+1:]
    env=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):
        env.pop(key,None)
    env['QT_QPA_PLATFORM']='windows'
    process=subprocess.Popen(command,env=env)
    owner=psutil.Process(process.pid);owned={};started=time.monotonic();timed_out=False
    while process.poll() is None:
        try:
            for child in owner.children(recursive=True):owned[(child.pid,child.create_time())]=child.name()
        except psutil.Error:pass
        if time.monotonic()-started>args.timeout:
            timed_out=True
            # Only exact PID+creation-time identities observed under this parent.
            for (pid,created),name in owned.items():
                try:
                    child=psutil.Process(pid)
                    if child.create_time()==created:child.terminate()
                except psutil.Error:pass
            process.terminate();break
        time.sleep(.1)
    try:code=process.wait(timeout=15)
    except subprocess.TimeoutExpired:process.kill();code=process.wait()
    def alive():
        values=[]
        for (pid,created),name in owned.items():
            try:
                child=psutil.Process(pid)
                if child.create_time()==created and child.is_running():values.append(dict(pid=pid,name=name))
            except psutil.Error:pass
        return values
    deadline=time.monotonic()+15
    while alive() and time.monotonic()<deadline:time.sleep(.1)
    remaining=alive()
    receipt=dict(schema='DINO_OWNED_PROCESS_TERMINAL_V1',command=command,exit_code=code,timed_out=timed_out,
        duration_s=round(time.monotonic()-started,3),observed_children=[dict(pid=pid,created_at=created,name=name) for (pid,created),name in owned.items()],
        remaining_owned_processes=remaining,scope='Only this parent tree; concurrent work preserved',
        result='PASS' if code==0 and not timed_out and not remaining else 'FAIL')
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    args.receipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))
    return 0 if receipt['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
