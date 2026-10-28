"""Bounded end-to-end A/B dispatch feasibility; one cycle, no periodicity claim."""
from __future__ import annotations

import concurrent.futures
import json
import multiprocessing
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run_curve(spec: dict) -> dict:
    from motorsim.power_curve_sweep import run_power_curve
    return run_power_curve(**spec)


def _run_serial(specs):
    started = time.perf_counter()
    results = [_run_curve(spec) for spec in specs]
    return time.perf_counter() - started, results


def _run_parallel(specs):
    started = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=multiprocessing.get_context("spawn")) as executor:
        futures = [executor.submit(_run_curve, spec) for spec in specs]
        results = [future.result() for future in futures]
    return time.perf_counter() - started, results


def _rows(curves):
    return {(curve["bindings"]["variant_label"], point["rpm"]): point
            for curve in curves for point in curve["points"]}


def main():
    from motorsim.engine_project import load_project
    from motorsim.desktop.preferences import artifact_root
    import psutil

    if psutil.virtual_memory().available < 3 * 1024**3:
        raise RuntimeError("Insufficient available memory for two isolated 1 GiB workers")
    project = load_project(ROOT / "configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json")
    variants = [("A_original", project["variants"]["A_original"]),
                ("B_header_plus20", project["variants"]["B_header_plus20"])]
    root = Path(artifact_root()).expanduser().resolve()
    cases = []
    for case_id, rpms in (("low", (5000, 6000)), ("high", (7000, 8000))):
        specs = []
        for label, engine in variants:
            specs.append({"document": engine, "project_id": project["project_id"],
                "variant_label": label, "artifact_root": str(root),
                "start_rpm": rpms[0], "stop_rpm": rpms[-1], "step_rpm": rpms[1]-rpms[0],
                "max_cycles": 1, "point_budget_seconds": 120,
                "total_budget_seconds": 240, "memory_limit_mib": 1024,
                "sweep_id": f"desktop-ab-p1-{case_id}-serial-{uuid.uuid4().hex[:10]}"})
        serial_wall, serial = _run_serial(specs)
        parallel_specs = [{**spec, "sweep_id": spec["sweep_id"].replace("serial", "parallel")}
                          for spec in specs]
        parallel_wall, parallel = _run_parallel(parallel_specs)
        serial_rows, parallel_rows = _rows(serial), _rows(parallel)
        comparisons = []
        for key in sorted(serial_rows):
            a, b = serial_rows[key], parallel_rows[key]
            comparisons.append({"variant": key[0], "rpm": key[1],
                "serial_status": a.get("status"), "parallel_status": b.get("status"),
                "serial_cycles": a.get("cycles_completed"), "parallel_cycles": b.get("cycles_completed"),
                "checkpoint_equal": a.get("checkpoint_sha256") == b.get("checkpoint_sha256"),
                "serial_checkpoint_sha256": a.get("checkpoint_sha256"),
                "parallel_checkpoint_sha256": b.get("checkpoint_sha256")})
        cases.append({"case_id": case_id, "rpms": list(rpms), "serial_wall_seconds": serial_wall,
            "parallel_wall_seconds": parallel_wall,
            "speedup": serial_wall/parallel_wall if parallel_wall else None,
            "points": comparisons,
            "all_checkpoints_equal": all(item["checkpoint_equal"] for item in comparisons),
            "all_one_cycle": all(item["serial_cycles"] == item["parallel_cycles"] == 1
                                  for item in comparisons)})
    output = {"schema": "DINO_DESKTOP_AB_DISPATCH_FEASIBILITY_V1",
        "max_cycles_per_point": 1, "periodicity_evaluated": False,
        "worker_count": 2, "per_worker_memory_limit_mib": 1024,
        "project": project["project_id"], "variant_ids": [item[0] for item in variants],
        "artifact_root": str(root), "cases": cases,
        "interpretation": "Bounded dispatch feasibility only; one-cycle checkpoints are not periodic performance results.",
        "acceptance_2x_both_cases": all(case["speedup"] >= 2.0 for case in cases),
        "state_equivalence": all(case["all_checkpoints_equal"] and case["all_one_cycle"] for case in cases)}
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
