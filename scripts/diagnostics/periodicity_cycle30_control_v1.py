"""One additional cycle; no retry loop of further cycle extensions."""
import argparse
from functools import partial
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.periodicity_extension_v4 import load_native_source,run


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--configuration-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.source,a.configuration_source,a.output,first_cycle=30,last_cycle=30,solver_budget=20,admission_budget=23,
        source_loader=partial(load_native_source,cycle=29,prefix='run'),schema='DINO_FINAL_PERIODIC_STREAK_CONTROL_V1'))
