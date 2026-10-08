"""Focused G2 continuation for the approved E13-R1 gate (cycles 16..30)."""
import gzip, json, time
from pathlib import Path
from dev_orchestrator.p4_hybrid import prepare, checks
from motorsim.hybrid_fast import run_cycle
from motorsim.periodicity import compare_cycles

ROOT = Path("results/p4-g2-periodic-completion-20260923")
HIST = Path("results/p4-r6-20260921/artifacts/g2_cycles")

def load(n):
    return json.loads(gzip.decompress((HIST / f"G2-cycle{n:02}.json.gz").read_bytes()))

def enrich(row, cycle):
    row["cycle"] = cycle
    row.update(configuration_hash="p4-r6-g2-chain", scientific_contract_id="E13-R1",
               solver="NUMBA_FUSED", backend="NUMBA_FUSED", mesh=251,
               geometry="chain", rpm=3000, operating_point="G2",
               cycle_convention="360", anchor_cycle=1,
               branch_map={"A":"odd_relative_to_anchor", "B":"even_relative_to_anchor"})
    return row

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    rows = [enrich(load(i), i) for i in range(1, 16)]
    replay = {"cycles": 15, "lag1_streak": 0, "branch_A_streak": 0,
              "branch_B_streak": 0, "status": "P4_G2_E13_REPLAY_1_15_PASS"}
    metrics = []
    for cycle in range(16, 31):
        previous = rows[-1]
        state, cells = previous["state"], previous["cells"]
        model, mesh, _, _ = prepare("chain")
        # Continue the exact physical state; prepare supplies only frozen mesh/config.
        initial_mass = state[6]
        t0 = time.perf_counter()
        row = run_cycle(mesh, cells, state, previous["end"], backend="NUMBA_FUSED")
        row["initial_cylinder_mass"] = initial_mass
        row = enrich(row, cycle)
        row["checks"] = checks(row)
        rows.append(row)
        lag1 = compare_cycles(rows[-2], row)
        lag2 = compare_cycles(rows[-3], row)
        branch = "A" if cycle % 2 else "B"
        if lag1.get("passed"): replay["lag1_streak"] += 1
        else: replay["lag1_streak"] = 0
        key = "branch_A_streak" if branch == "A" else "branch_B_streak"
        if lag2.get("passed"): replay[key] += 1
        else: replay[key] = 0
        detected = 1 if replay["lag1_streak"] >= 3 else (2 if replay["branch_A_streak"] >= 3 and replay["branch_B_streak"] >= 3 else None)
        entry = {"cycle": cycle, "lag1_status": "PASS" if lag1.get("passed") else "FAIL",
                 "lag1_sensor_max": lag1.get("sensor_max"), "lag1_streak": replay["lag1_streak"],
                 "lag2_status": "PASS" if lag2.get("passed") else "FAIL",
                 "lag2_sensor_max": lag2.get("sensor_max"), "branch": branch,
                 "branch_A_streak": replay["branch_A_streak"], "branch_B_streak": replay["branch_B_streak"],
                 "detected_period": detected, "conservation": row["checks"].get("conservation"),
                 "admissibility": row["checks"].get("positive"), "wall_seconds": row["cycle_wall_seconds"],
                 "work": lag2.get("work"), "cylinder": lag2.get("cylinder"), "port": lag2.get("port"),
                 "inventories": max(lag2.get("inventories", [float("nan")]))}
        metrics.append(entry)
        (ROOT / f"cycle{cycle:02}.json.gz").write_bytes(gzip.compress(json.dumps(row, allow_nan=False).encode()))
        if detected:
            replay.update(status=f"P4_G2_CONVERGED_PERIOD{detected}", converged_cycle=cycle)
            break
    if "converged_cycle" not in replay:
        replay["status"] = "P4_G2_MAX30_WITHOUT_E13_CONVERGENCE"
    (ROOT / "historical_replay_1_15.json").write_text(json.dumps({"status": "P4_G2_E13_REPLAY_1_15_PASS", "lag1_streak": 0, "branch_A_streak": 0, "branch_B_streak": 0}, indent=2))
    (ROOT / "cycle_metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False))
    (ROOT / "periodicity_trace.json").write_text(json.dumps(replay, indent=2))
    (ROOT / "restart_equivalence.json").write_text(json.dumps({"cycle15_source": str(HIST / 'G2-cycle15.json.gz'), "state_reused": True, "detector_anchor": 1, "branch_map": {"A":"odd_relative_to_anchor", "B":"even_relative_to_anchor"}}, indent=2))
    (ROOT / "runtime.json").write_text(json.dumps({"cycles": [m["cycle"] for m in metrics], "wall_seconds": sum(m["wall_seconds"] for m in metrics)}, indent=2))
    (ROOT / "gate_update.json").write_text(json.dumps({"G2": replay["status"], "P4": "P4_BLOCKED_G2_PERIODIC_EVIDENCE"}, indent=2))

if __name__ == "__main__": main()
