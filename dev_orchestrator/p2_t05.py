"""Single contractual T05 gate after the three authorized implementation fixes."""
import argparse
import gzip
import json
from pathlib import Path
from motorsim.gas1d.verification import run_case
from .p2_campaign import write,invariants


def run(run_dir):
    checks=invariants()
    if not all(checks.values()):raise ValueError('Preservation failure')
    result=run_case('T05')
    art=run_dir/'artifacts'
    (art/'T05.json.gz').write_bytes(gzip.compress(json.dumps(result,allow_nan=False).encode(),mtime=0))
    write(art/'t05-summary.json',{k:v for k,v in result.items() if k not in ('result','mesh','reference','initial')})
    checks['T05']=result['status']=='PASS'
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason='Exact contractual T05') for k,v in checks.items()],metrics=dict(wall_seconds=result['result']['wall_seconds']),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);run(p.parse_args().run_dir)
