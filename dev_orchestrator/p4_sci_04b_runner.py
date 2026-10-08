"""Generate P4-SCI-04B artifacts B2+C2"""
import json, math, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dev_orchestrator.p4_sci_04b import (run_b2, B2_EPS, B2_SIGMA, B2_X0, B2_L_TRUNC, B2_L_EXT, B2_AREA, B2_SENSOR, B2_CFL, B2_N_LEVELS, B2_T_FINAL, C0, P0, EOS,
    C2_VOLUME, C2_AREA, C2_L_DUCT, C2_N_DUCT, C2_SENSOR, C2_T_FINAL, C2_CFL_LEVELS, solve_c2_one, c2_initial_riemann_check)
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.boundary import Boundary

OUT = Path("results/p4-sci-04b-intermediate-benchmarks-20260923")
B2_DIR = OUT/"b2"
C2_DIR = OUT/"c2"
for d in [OUT,B2_DIR,C2_DIR]:
    d.mkdir(parents=True, exist_ok=True)
start_total=time.perf_counter()
# B2
print("Running B2 ...")
b2_results,b2_total = run_b2()
# Actually run_b2 is defined in p4_sci_04b? we have run_b2 there? We defined run_b2 in p4_sci_04b? We defined run_b2? In file we have run_b2 but not exported? Let's import correctly: we defined function run_b2 in p4_sci_04b.py as run_b2? Check: we defined def run_b2(): returns results. But we named run_b2? In code above we have def run_b2(): but we wrote run_b2? Let's see file defines def run_b2(): yes at bottom? Actually file defines def run_b2(): but we wrote def run_b2(): at line ?? We defined def run_b2(): but in file we defined def run_b2(): after b2_truncated_vs... Let's ensure import works. If not, we call manually.
