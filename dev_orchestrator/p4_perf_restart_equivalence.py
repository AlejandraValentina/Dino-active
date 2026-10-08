"""RESTART_BINARY_EQUIVALENCE_PASS test"""
import json, gzip, time, hashlib, tempfile
from pathlib import Path
import numpy as np
from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.hybrid_fast import run_cycle
from motorsim.hybrid_exhaust import LegacySources
from motorsim.gas1d.eos import IdealGas
from motorsim.checkpoint import save_restart, load_restart

def prepare(dx):
    model = LegacySources()
    mesh = exhaust_mesh(segments('straight'), dx)
    p,T,Y = model.case.initial_pty[3]
    eos = IdealGas()
    U = eos.conservative((p/(eos.R*T),0.,p,Y))
    pipe = [tuple(v*u for u in U) for v in mesh.volumes]
    state = model.initial_state()[:9]
    return model, mesh, pipe, state

def run_one_cycle(mesh, pipe, state, begin):
    row = run_cycle(mesh, pipe, state, begin, backend='NUMBA_FUSED', cfl=0.4)
    return row

def compare_rows(rowA, rowB):
    # Compare state 0D
    stateA = np.array(rowA['state'], dtype=np.float64)
    stateB = np.array(rowB['state'], dtype=np.float64)
    # pipe arrays
    cellsA = np.array(rowA['cells'], dtype=np.float64)
    cellsB = np.array(rowB['cells'], dtype=np.float64)
    # work
    workA = rowA['work_indicated_J']
    workB = rowB['work_indicated_J']
    # port_integral, external, inventories, sensor outputs, balances, counts
    def max_abs(a,b):
        return np.max(np.abs(np.array(a)-np.array(b))) if len(a)==len(b) else float('inf')
    def max_rel(a,b):
        a=np.array(a,dtype=np.float64); b=np.array(b,dtype=np.float64)
        denom = np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-12)
        return np.max(np.abs(a-b)/denom)
    metrics = {}
    metrics['state_max_abs'] = float(np.max(np.abs(stateA-stateB)))
    metrics['state_max_rel'] = float(np.max(np.abs(stateA-stateB)/np.maximum(np.maximum(np.abs(stateA), np.abs(stateB)),1e-12)))
    metrics['cells_max_abs'] = float(np.max(np.abs(cellsA-cellsB)))
    metrics['cells_max_rel'] = float(np.max(np.abs(cellsA-cellsB)/np.maximum(np.maximum(np.abs(cellsA), np.abs(cellsB)),1e-12)))
    metrics['work_abs'] = abs(workA-workB)
    metrics['work_rel'] = abs(workA-workB)/max(abs(workA),abs(workB),1)
    metrics['port_exchange_max_abs'] = max_abs(rowA['port_integral'], rowB['port_integral'])
    metrics['port_exchange_max_rel'] = max_rel(rowA['port_integral'], rowB['port_integral'])
    metrics['global_balance_max_abs'] = max_abs(rowA['global_balance'], rowB['global_balance'])
    # inventories: initial/final?
    metrics['final_inventory_max_abs'] = max_abs(rowA['final_inventory'], rowB['final_inventory'])
    # sensor: last history point sensors
    histA = rowA['history'][-1]
    histB = rowB['history'][-1]
    # sensors are tuple of 3 sensors each 4 values
    # compare p_cyl, T_cyl, etc.
    sA = histA.get('sensors', histA.get('sensors_p_u_M_Y'))
    sB = histB.get('sensors', histB.get('sensors_p_u_M_Y'))
    if sA and sB:
        metrics['sensor_max_abs'] = float(np.max(np.abs(np.array(sA)-np.array(sB))))
    else:
        metrics['sensor_max_abs'] = 0
    # counts
    metrics['counts_equal'] = (rowA['segments'][0]['result']['counts'] == rowB['segments'][0]['result']['counts'])
    # balances
    metrics['max_global_balance_diff'] = abs(rowA['global_balance'][0]-rowB['global_balance'][0])
    # Check accepted/rejected steps equal via history len
    metrics['history_len_equal'] = len(rowA['history']) == len(rowB['history'])
    # Exact equality?
    exact = all(v==0 or v<1e-15 for k,v in metrics.items() if 'max_abs' in k or 'abs' in k)
    # Actually require exact for state/cells/work
    exact_state = metrics['state_max_abs']==0 and metrics['cells_max_abs']==0 and metrics['work_abs']==0
    return metrics, exact_state

def test_one(N, dx):
    print(f"=== RESTART equivalence N={N} ===", flush=True)
    model, mesh, pipe, state = prepare(dx)
    begin = 180.0
    # Run 1 cycle to get known state
    row1 = run_one_cycle(mesh, pipe, state, begin)
    s1 = row1['state']
    c1 = row1['cells']
    angle1 = row1['end']
    # Path A: direct continue 1 cycle
    rowA = run_one_cycle(mesh, c1, s1, angle1)
    # Path B: save restart, reload, continue
    with tempfile.TemporaryDirectory() as tmp:
        restart_dir = Path(tmp)/"restart"
        config = dict(dx_target=dx, backend='NUMBA_FUSED', cfl=0.4, config_hash='test')
        save_restart(s1, c1, cycle=1, angle=angle1, config=config, out_dir=restart_dir, compressed=False)
        # close/recreate: reload
        meta, s1_reload, c1_reload = load_restart(restart_dir)
        # c1_reload is np array, need to convert to list of tuples for run_cycle which expects list of tuples?
        # run_cycle handles both np array and list? In exhaust_numpy, it does np.array(initial) so ok
        # But we pass as np array or list; both work (exhaust_numpy does np.array(initial))
        # Use reload arrays directly
        c1_reload_list = c1_reload.tolist()
        s1_reload_list = s1_reload.tolist()
        rowB = run_one_cycle(mesh, c1_reload_list, s1_reload_list, angle1)
    metrics, exact = compare_rows(rowA, rowB)
    print(f"N{N} metrics:", json.dumps(metrics, indent=2), flush=True)
    print(f"N{N} exact_state={exact}", flush=True)
    # Also check inventories etc
    passed = exact and metrics['history_len_equal'] and metrics['counts_equal']
    # If not exact, report max_abs
    if not exact:
        print(f"FAIL: not exact, max_abs state {metrics['state_max_abs']}, cells {metrics['cells_max_abs']}, work {metrics['work_abs']}", flush=True)
    else:
        print(f"PASS: exact equality", flush=True)
    return metrics, passed

if __name__ == "__main__":
    # Warm JIT
    m, mesh, pipe, state = prepare(0.75/100)
    _ = run_one_cycle(mesh, pipe, state, 180.0)
    print("Warm done", flush=True)
    m250, p250 = test_one(250, 0.75/250)
    m400, p400 = test_one(400, 0.75/400)
    result = dict(
        N250=dict(metrics=m250, passed=p250),
        N400=dict(metrics=m400, passed=p400),
        overall_pass=p250 and p400,
        gate="RESTART_BINARY_EQUIVALENCE_PASS" if (p250 and p400) else "RESTART_BINARY_EQUIVALENCE_FAIL"
    )
    out = Path("results/p4-perf-01-20260922/restart_equivalence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(f"Result gate {result['gate']}", flush=True)
    # Also emit to console for gate
    if not result['overall_pass']:
        raise SystemExit(1)
