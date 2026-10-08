"""P4-PERF-01 checkpoint architecture: SUMMARY / RESTART / FULL_DEBUG

- SUMMARY: small JSON per cycle (default)
- RESTART: binary .npz + metadata.json (atomic)
- FULL_DEBUG: rich JSON gz only on demand
- Backward compat: read legacy .json.gz
- Atomic writes via temp file + rename
- Float64 exact preservation
"""
import json, gzip, hashlib, time, os
from pathlib import Path
import numpy as np

# --------------------------------------------------------------------
# Atomic write helpers (Windows safe)
# --------------------------------------------------------------------
def _atomic_write_bytes(path: Path, data: bytes):
    tmp = path.with_suffix(path.suffix + ".tmp")
    # Ensure parent exists
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    # flush not needed for write_bytes, but ensure sync
    try:
        os.replace(tmp, path)  # atomic on Windows/POSIX
    except:
        # fallback
        tmp.replace(path)

def _atomic_write_text(path: Path, text: str, encoding="utf-8"):
    _atomic_write_bytes(path, text.encode(encoding))

def _atomic_write_npz(path: Path, arrays: dict, compressed: bool = False):
    # Write to temp then rename; use file handle to avoid numpy extension appending
    tmp = path.parent / (path.name + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    # numpy will append .npz if given string without .npz, so use file object
    with open(tmp, 'wb') as f:
        if compressed:
            np.savez_compressed(f, **arrays)
        else:
            np.savez(f, **arrays)
    os.replace(tmp, path)

# --------------------------------------------------------------------
# SUMMARY — small per-cycle JSON
# --------------------------------------------------------------------
def make_summary(row: dict) -> dict:
    """Extract only necessary fields for convergence, balances, inventories, sensors, counts, provenance."""
    # Minimal fields: work, power, torque, global_balance, counts, history summary, sensor outputs, etc.
    # Keep history but not full snapshots/cells? For SUMMARY we keep only per-cycle aggregates, not full history arrays huge.
    # For convergence we need history for D1/D2 later? But we can store summary history: only angle, p_cyl, sensors, exchange, etc. compressed?
    # Keep history but trim to necessary: angle, p_cyl, sensors, exchange, etc. Already history is large but we can keep it; for SUMMARY we keep full history? But that is large (history ~10k entries). To make SUMMARY small we should keep only aggregates, not full history.
    # For now keep only aggregates + last history point.
    # But to support lag-2 we need full history? That's for evaluation, not per-cycle summary. For SUMMARY we store only metrics needed for next restart and lightweight analysis.
    # We'll store: work, global_balance, inventories, sensor summary, counts, phase, provenance.
    segs = row.get('segments', [])
    # Extract counts aggregated
    total_counts = {}
    for seg in segs:
        cc = seg.get('result', {}).get('counts', {})
        for k,v in cc.items():
            total_counts[k] = total_counts.get(k, 0) + v
    # Extract final inventories
    # row has state, cells, etc.
    s = row.get('state')
    c = row.get('cells')
    # Compute pipe sums if needed
    summary = dict(
        begin=row.get('begin'),
        end=row.get('end'),
        complete=row.get('complete'),
        reason=row.get('reason'),
        work_indicated_J=row.get('work_indicated_J'),
        power_indicated_W=row.get('power_indociated_W') if 'power_indociated_W' in row else row.get('power_indicated_W'),
        torque_indicated_Nm=row.get('torque_indicated_Nm'),
        global_balance=row.get('global_balance'),
        initial_inventory=row.get('initial_inventory'),
        final_inventory=row.get('final_inventory'),
        port_integral=row.get('port_integral'),
        external=row.get('external'),
        cycle_wall_seconds=row.get('cycle_wall_seconds'),
        solver_seconds=row.get('solver_seconds'),
        counts=total_counts,
        # provenance
        path=row.get('path'),
        mesh=row.get('segments', [{}])[0].get('result', {}).get('mesh') if row.get('segments') else None,
        # Keep only small provenance, not full snapshots
        config_hash=hashlib.sha256(json.dumps(dict(begin=row.get('begin'), work=row.get('work_indicated_J'))).encode()).hexdigest()[:12],
        timestamp=time.time(),
        backend=row.get('backend', 'NUMBA_FUSED'),
        cfl=row.get('cfl', 0.4),
    )
    # Remove large nested mesh if too big, keep only n
    if summary['mesh'] and isinstance(summary['mesh'], dict):
        summary['mesh_n'] = summary['mesh'].get('n')
        summary['mesh_dx'] = None
        del summary['mesh']
    # For history, keep only minimal for SUMMARY (not full decimated, to keep size small)
    if row.get('history'):
        h = row['history']
        summary['history_len'] = len(h)
        last = h[-1]
        # Handle different schema: hybrid_fast uses sensors_p_u_M_Y, p_port, Mach_port, mass_flux_port etc.
        # Keep generic minimal
        summary['last_point'] = dict(
            angle=last.get('angle'),
            p_cyl=last.get('p_cyl'),
            T_cyl=last.get('T_cyl'),
            m_cyl=last.get('m_cyl'),
            Y_cyl=last.get('Y_cyl'),
            sensors=last.get('sensors', last.get('sensors_p_u_M_Y')),
            port_pressure=last.get('port_pressure', last.get('p_port')),
            port_Mach=last.get('port_Mach', last.get('Mach_port')),
            exchange=last.get('exchange', [last.get('mass_flux_port'), last.get('energy_flux_port'), last.get('species_flux_port')]),
        )
        summary['first_point'] = dict(angle=h[0].get('angle'), p_cyl=h[0].get('p_cyl'))
    return summary

def save_summary(row: dict, path: Path):
    summ = make_summary(row)
    # Validate size: should be small (<200KB), we enforce check later
    txt = json.dumps(summ, indent=2)
    _atomic_write_text(path, txt)
    return summ, len(txt.encode())

def load_summary(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

# --------------------------------------------------------------------
# RESTART — binary .npz + metadata.json (atomic)
# --------------------------------------------------------------------
def save_restart(state, cells, cycle: int, angle: float, config: dict, out_dir: Path, compressed: bool = False, detector=None):
    """Save exactly necessary to continue: state 0D (9), pipe conservative arrays (n,4), cycle/angle, config hash, solver hash, backend, etc."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # state: list/tuple 9 floats, cells: list of tuples or np array (n,4)
    state_arr = np.array(state, dtype=np.float64)
    # cells may be list of tuples or list or np array
    if isinstance(cells, np.ndarray):
        cells_arr = cells.astype(np.float64)
    else:
        # cells is list of tuples (n,4) or list of lists
        cells_arr = np.array(cells, dtype=np.float64)
    # Ensure shapes
    assert state_arr.shape == (9,), f"state shape {state_arr.shape}"
    assert cells_arr.ndim == 2 and cells_arr.shape[1] == 4, f"cells shape {cells_arr.shape}"
    n = cells_arr.shape[0]
    # metadata
    meta = dict(
        cycle=cycle,
        angle=angle,
        n=n,
        dx_target=config.get('dx_target'),
        backend=config.get('backend', 'NUMBA_FUSED'),
        cfl=config.get('cfl', 0.4),
        config_hash=config.get('config_hash', ''),
        solver_hash=config.get('solver_hash', ''),
        timestamp=time.time(),
        float_dtype="float64",
        version="RESTART_V1",
    )
    if detector is not None:
        meta["detector"] = detector.to_json() if hasattr(detector, "to_json") else detector
    # Add provenance
    meta_path = out_dir / "metadata.json"
    npz_path = out_dir / "state.npz"
    # atomic writes
    _atomic_write_text(meta_path, json.dumps(meta, indent=2))
    _atomic_write_npz(npz_path, dict(state=state_arr, cells=cells_arr), compressed=compressed)
    return meta, state_arr.nbytes + cells_arr.nbytes, npz_path.stat().st_size

def load_restart(in_dir: Path):
    in_dir = Path(in_dir)
    meta = json.loads((in_dir / "metadata.json").read_text(encoding="utf-8"))
    data = np.load(in_dir / "state.npz")
    state = data["state"]
    cells = data["cells"]
    # Ensure float64
    assert state.dtype == np.float64
    assert cells.dtype == np.float64
    return meta, state, cells

def load_restart_legacy_json_gz(path: Path):
    """Backward compat: read historical .json.gz checkpoint (full row)."""
    import gzip
    data = json.loads(gzip.decompress(Path(path).read_bytes()))
    # Extract state/cells
    return data

# --------------------------------------------------------------------
# FULL_DEBUG — rich JSON gz only on demand
# --------------------------------------------------------------------
def save_full_debug(row: dict, path: Path):
    txt = json.dumps(row).encode()
    gz = gzip.compress(txt)
    _atomic_write_bytes(path, gz)
    return len(txt), len(gz)

def load_full_debug(path: Path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))

# --------------------------------------------------------------------
# Policy helpers
# --------------------------------------------------------------------
def should_write_restart(cycle: int, restart_every: int, is_final: bool = False, is_cancelled: bool = False, is_failed: bool = False):
    if is_final or is_cancelled or is_failed:
        return True
    if restart_every <= 1:
        return True
    return (cycle % restart_every == 0)

# --------------------------------------------------------------------
# Size guard for decision.json
# --------------------------------------------------------------------
def assert_decision_size(path: Path, max_kb: int = 100):
    size_kb = path.stat().st_size / 1024
    if size_kb > max_kb:
        raise ValueError(f"decision.json too large: {size_kb:.1f}KB > {max_kb}KB, should be lightweight. Move details to artifacts.")
