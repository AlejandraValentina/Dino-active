"""Reproduce the contact control using the integrated engine's plenum resolve path."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.diagnostics import outlet_front_control_v1 as harness
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from scripts.agents.storage_preflight import check_storage_requirements


class Adapter(OpenEndPlenumV2Boundary):
    def __init__(self,kind,**kwargs):
        if kind!='reservoir':raise ValueError('unsupported diagnostic kind')
        super().__init__(**kwargs)

    def flux(self,interior,normal,eos):
        resolved=self.resolve(interior,normal,eos);a=eos.sound_speed(resolved.state);u=resolved.state[1]
        return eos.flux(resolved.state),(u-a,u+a),None


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    check_storage_requirements([(args.output,4*1024**2)])
    if args.output.exists():raise FileExistsError('preserve earlier evidence')
    old=harness.Boundary;start=time.perf_counter()
    try:
        harness.Boundary=Adapter
        cases=[harness.run_case(n,False,True,'v2',1.,start+120) for n in (32,64,128)]
        cases.append(harness.run_case(128,False,True,'v2',.5,start+120))
    finally:harness.Boundary=old
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(schema='DINO_ACTUAL_PLENUM_FRONT_CONTROL_V1',cases=cases,
        wall_s=time.perf_counter()-start,boundary='OpenEndPlenumV2Boundary.resolve then eos.flux as IntegratedEngine2T._external_face',experimental_validation=False),indent=2)+'\n',encoding='utf-8')
