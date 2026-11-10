"""C05 packaged acceptance: frozen MotorSimWorker.exe for 2T and 4T reference runs.

This is an external maintainer driver, not shipped with Dino. It starts only
the frozen worker, waits for each process, verifies the produced manifests and
does not run a scientific campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from motorsim.desktop.acceptance_terminal import (default_worker_probe,
                                                   finalize_acceptance)
from motorsim.storage import load_project
from motorsim.reference_results import load_result, project_inputs
from motorsim.sweep import load_sweep


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_worker(worker, args, work, name, timeout):
    work.mkdir(parents=True, exist_ok=True)
    stdout = (work / "stdout.log").open("wb")
    stderr = (work / "stderr.log").open("wb")
    try:
        process = subprocess.Popen([str(worker), *map(str, args)],
                                   stdout=stdout, stderr=stderr)
        payload = {
            "schema": "DINO_C05_FROZEN_WORKER_RUN_V1",
            "name": name,
            "worker": str(worker),
            "worker_sha256": sha256(worker),
            "arguments": [str(item) for item in args],
        }
        record = finalize_acceptance(work, payload, process=process,
                                     timeout=timeout,
                                     worker_probe=lambda image: [])
    finally:
        stdout.close()
        stderr.close()
    if record["result"] != "PASS":
        raise RuntimeError(f"{name}: {record['result']} "
                           f"{record['terminal_verification']['issues']} "
                           f"stderr={stderr.name}")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True,
                        help="packaged MotorSim/Ejemplos directory")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args()
    worker = args.worker.resolve()
    examples = args.examples.resolve()
    work = args.work.resolve()
    if not worker.is_file() or worker.name.lower() != "motorsimworker.exe":
        raise FileNotFoundError(f"expected frozen MotorSimWorker.exe: {worker}")
    if work.exists():
        raise FileExistsError(work)

    project = load_project(examples / "EJEMPLO_SINTETICO_4T_REFERENCIA.json")
    project_2t = load_project(examples / "EJEMPLO_SINTETICO_2T_REFERENCIA.json")
    origin = {"kind": "project", "project_name": project.name,
              "source_path": None, "dirty": False}
    origin_2t = {"kind": "project", "project_name": project_2t.name,
                 "source_path": None, "dirty": False}
    point_inputs = project_inputs(project, origin, rpm=3000)
    sweep_inputs = project_inputs(project, origin, rpm=2500)
    sweep_2t = project_inputs(project_2t, origin_2t, rpm=2500)
    (work / "worker-2t").mkdir(parents=True)
    (work / "worker-2t-curve").mkdir()
    (work / "worker-4t-point").mkdir()
    (work / "worker-4t-curve").mkdir()
    (work / "worker-2t-curve" / "request.json").write_text(
        json.dumps({"common_inputs": sweep_2t, "rpms": [2500, 3000, 3500]},
                   ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (work / "worker-4t-point" / "request.json").write_text(
        json.dumps(point_inputs, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (work / "worker-4t-curve" / "request.json").write_text(
        json.dumps({"common_inputs": sweep_inputs, "rpms": [2500, 3000, 3500]},
                   ensure_ascii=False, sort_keys=True), encoding="utf-8")

    records = [
        run_worker(worker, ["--cycle", "2T", "--output",
                            work / "worker-2t" / "output"],
                   work / "worker-2t", "2T reference point", args.timeout),
        run_worker(worker, ["--cycle", "2T", "--output",
                            work / "worker-2t-curve" / "output",
                            "--sweep-input",
                            work / "worker-2t-curve" / "request.json"],
                   work / "worker-2t-curve", "2T reference curve", args.timeout),
        run_worker(worker, ["--cycle", "4T", "--output",
                            work / "worker-4t-point" / "output",
                            "--project-input",
                            work / "worker-4t-point" / "request.json"],
                   work / "worker-4t-point", "4T reference point", args.timeout),
        run_worker(worker, ["--cycle", "4T", "--output",
                            work / "worker-4t-curve" / "output",
                            "--sweep-input",
                            work / "worker-4t-curve" / "request.json"],
                   work / "worker-4t-curve", "4T reference curve", args.timeout),
    ]

    check_2t = load_result(work / "worker-2t" / "output" / "manifest.json")
    if check_2t["status"] != "converged":
        raise AssertionError(f"2T reference point status={check_2t['status']}")
    check_4t = load_result(work / "worker-4t-point" / "output" / "manifest.json")
    if check_4t["status"] != "converged":
        raise AssertionError(f"4T reference point status={check_4t['status']}")
    if not check_4t.get("manifest", {}).get("model_version"):
        raise AssertionError("4T reference point has no model_version")
    curve_2t = load_sweep(work / "worker-2t-curve" / "output" / "series.json")
    if curve_2t["index"]["state"] != "converged":
        raise AssertionError(f"2T curve status={curve_2t['index']['state']}")
    if [point["state"] for point in curve_2t["index"]["points"]] != ["converged"] * 3:
        raise AssertionError("2T curve has non-converged points")
    curve = load_sweep(work / "worker-4t-curve" / "output" / "series.json")
    if curve["index"]["state"] != "converged":
        raise AssertionError(f"4T curve status={curve['index']['state']}")
    if [point["state"] for point in curve["index"]["points"]] != ["converged"] * 3:
        raise AssertionError("4T curve has non-converged points")
    workers = default_worker_probe()
    if workers:
        raise AssertionError(f"orphan or unverifiable worker processes: {workers}")

    receipt = {
        "schema": "DINO_C05_FROZEN_WORKER_ACCEPTANCE_V1",
        "result": "PASS",
        "worker": str(worker),
        "worker_sha256": sha256(worker),
        "examples": str(examples),
        "checks": [
            "Frozen 2T reference point converged",
            "Frozen 2T reference curve converged three of three points",
            "Frozen 4T reference point converged with model metadata",
            "Frozen 4T reference curve converged three of three points",
            "No MotorSimWorker.exe remained after terminal waits",
        ],
        "runs": records,
        "outputs": {
            "2t_manifest_sha256": sha256(work / "worker-2t" / "output" / "manifest.json"),
            "2t_series_sha256": sha256(work / "worker-2t-curve" / "output" / "series.json"),
            "4t_manifest_sha256": sha256(work / "worker-4t-point" / "output" / "manifest.json"),
            "4t_series_sha256": sha256(work / "worker-4t-curve" / "output" / "series.json"),
        },
        "scientific_claims": {
            "experimental_validation": "NOT_PERFORMED",
            "predictive_capability": "NOT_CLAIMED",
        },
    }
    (work / "frozen-worker-acceptance.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "receipt": str(work / "frozen-worker-acceptance.json")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
