"""Diagnostic-only FAST_RECIPE_V1 benchmark; never starts campaign points."""
from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import json
import multiprocessing
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.fast_recipe_v1 import (  # noqa: E402
    advance_cycle, build_recipe, canonical_bytes, read_recipe,
    reconstruct_primary, sha256, write_recipe_atomic,
)
from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, _solver_dependency_hashes,
    audit_integrated_cycle_primary, make_integrated_cycle_primary,
    _integrated_nominal_step_end, _integrated_scheduled_angles,
)
from scripts.full_rpm_sweep_v1_campaign import (  # noqa: E402
    PREREGISTRATION, _configuration_for, _parallel_worker_plan, _read_json,
)

RESERVE_PER_WORKER = 512 * 1024 * 1024


def _atomic_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                          allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_primary(path: Path, value: dict) -> int:
    payload = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                zipped.write(payload)
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path.stat().st_size


def _resource_sampler(stop: list[bool], samples: list[dict]) -> None:
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        while not stop[0]:
            samples.append({"rss_bytes": int(proc.memory_info().rss),
                            "cpu_percent": float(proc.cpu_percent(interval=0.2))})
    except (ImportError, OSError):
        return


def _job(task: dict) -> dict:
    t_start = time.perf_counter()
    out = Path(task["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    stop, samples = [False], []
    sampler = threading.Thread(target=_resource_sampler, args=(stop, samples), daemon=True)
    sampler.start()
    try:
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            cpu0 = proc.cpu_times()
            rss0 = int(proc.memory_info().rss)
        except (ImportError, OSError):
            psutil, proc, cpu0, rss0 = None, None, None, None
        cfg = _configuration_for(task["variant"], task["rpm"])
        config_sha = sha256(canonical_bytes(cfg))
        engine = IntegratedEngine2T.from_configuration_dict(cfg)
        start = engine.snapshot()
        runner_sha = task["capture_runner_sha256"]
        stages: dict[str, float] = {}
        t = time.perf_counter()
        accepted, rejected = advance_cycle(
            engine, 1, capture_trace=task["variant_name"] == "A_CONVENTIONAL",
            profile_capture=task["variant_name"] == "A_CONVENTIONAL",
            max_wall_seconds=task["timeout_seconds"], timing=stages)
        advance_wall = time.perf_counter() - t
        terminal = engine.snapshot() if task["variant_name"] == "A_CONVENTIONAL" else engine.fast_recipe_terminal_state()
        if task["variant_name"] != "A_CONVENTIONAL":
            engine.compact_fast_recipe_cycle()
            next_checkpoint = engine.snapshot()
            t = time.perf_counter()
            recipe = build_recipe(configuration=cfg, cycle_index=1,
                                  cycle_start_snapshot=start,
                                  accepted_steps=accepted, rejected_trials=rejected,
                                  terminal_state=terminal,
                                  next_cycle_checkpoint=next_checkpoint,
                                  capture_runner_sha256=runner_sha)
            stages["recipe_build_seconds"] = time.perf_counter() - t
            checkpoint = recipe["next_cycle_checkpoint"]
            checkpoint_sha = recipe["next_cycle_checkpoint_sha256"]
            t = time.perf_counter()
            restored = IntegratedEngine2T.from_configuration_dict(cfg)
            restored.restore(checkpoint)
            control = IntegratedEngine2T.from_configuration_dict(cfg)
            control.restore(checkpoint)
            target = _integrated_nominal_step_end(
                restored, restored.crank_angle_unwrapped_deg, 720.0,
                _integrated_scheduled_angles(restored, 720.0))
            delta = target - restored.crank_angle_unwrapped_deg
            dt = delta / (6.0 * restored.reference_rpm)
            restored.step(dt, delta, capture_trace=False)
            control.step(dt, delta, capture_trace=False)
            if canonical_bytes(restored.fast_recipe_terminal_state()) != canonical_bytes(
                    control.fast_recipe_terminal_state()):
                raise RuntimeError("FAST cycle-boundary checkpoint continuation mismatch")
            stages["checkpoint_restore_continuation_seconds"] = time.perf_counter() - t
            t = time.perf_counter()
            recipe_file_sha = write_recipe_atomic(out / "cycle-recipe.json", recipe)
            stages["recipe_write_seconds"] = time.perf_counter() - t
        else:
            recipe = None
            recipe_file_sha = None
            checkpoint_sha = None

        primary = None
        audit = None
        if task["variant_name"] == "A_CONVENTIONAL":
            t = time.perf_counter()
            primary = make_integrated_cycle_primary(
                engine, start, terminal, 1, rejected_trials=rejected,
                runner_sha256=runner_sha)
            stages["primary_construction_seconds"] = time.perf_counter() - t
            t = time.perf_counter()
            audit = audit_integrated_cycle_primary(primary)
            stages["independent_audit_seconds"] = time.perf_counter() - t
            if audit.get("status") != "PASS" or audit.get("recomputed") is not True:
                raise RuntimeError("conventional primary independent audit failed")
            t = time.perf_counter()
            primary_bytes = _write_primary(out / "primary.json.gz", primary)
            stages["primary_output_seconds"] = time.perf_counter() - t
        elif task["variant_name"] == "C_FAST_AUDITED":
            t = time.perf_counter()
            loaded = read_recipe(out / "cycle-recipe.json", expected_file_sha256=recipe_file_sha)
            stages["recipe_read_validation_seconds"] = time.perf_counter() - t
            t = time.perf_counter()
            primary = reconstruct_primary(loaded)
            stages["canonical_reconstruction_seconds"] = time.perf_counter() - t
            t = time.perf_counter()
            audit = audit_integrated_cycle_primary(primary)
            stages["independent_audit_seconds"] = time.perf_counter() - t
            if audit.get("recomputed") is not True:
                raise RuntimeError("FAST reconstructed primary was not independently recomputed")
            t = time.perf_counter()
            primary_bytes = _write_primary(out / "primary.json.gz", primary)
            stages["primary_output_seconds"] = time.perf_counter() - t
            recipe["status"] = "AUDITED"
            recipe.pop("recipe_sha256", None)
            recipe["recipe_sha256"] = sha256(canonical_bytes(recipe))
            recipe_file_sha = write_recipe_atomic(out / "cycle-recipe-audited.json", recipe)
        else:
            # Provisional path deliberately emits no primary or scientific result.
            primary_bytes = 0
            if recipe["status"] != "CAPTURED_UNAUDITED":
                raise RuntimeError("provisional FAST recipe lost UNAUDITED status")

        primary_canonical_sha = sha256(canonical_bytes(primary)) if primary is not None else None
        scientific = None
        if primary is not None:
            evidence = primary.get("evidence_binding", {})
            scientific = {k: v for k, v in primary.items() if k != "evidence_binding"}
            scientific["evidence_binding"] = {
                k: v for k, v in evidence.items() if k != "runner_sha256"}
        process_cpu = None
        if proc is not None:
            cpu1 = proc.cpu_times()
            process_cpu = float((cpu1.user - cpu0.user) + (cpu1.system - cpu0.system))
        scientific_projection_sha256 = (sha256(canonical_bytes(scientific))
                                        if scientific is not None else None)
        result = {
            "schema": "FAST_RECIPE_V1_DIAGNOSTIC_JOB_V1",
            "task_id": task["task_id"], "scenario": task["variant_name"],
            "point": task["point"], "rpm": task["rpm"],
            "configuration_sha256": config_sha,
            "solver_dependency_hashes": _solver_dependency_hashes(),
            "recipe_status": recipe["status"] if recipe else None,
            "recipe_sha256": recipe.get("recipe_sha256") if recipe else None,
            "recipe_file_sha256": recipe_file_sha,
            "checkpoint_sha256": checkpoint_sha,
            "accepted_steps": len(accepted), "rejected_trials": len(rejected),
            "primary_sha256": primary_canonical_sha,
            "primary_persisted_bytes": primary_bytes,
            "audit_status": audit.get("status") if audit else "NOT_RUN_PROVISIONAL",
            "audit_recomputed": audit.get("recomputed") if audit else False,
            "schedule_capture_seconds": stages.get("recipe_schedule_capture_seconds", 0.0),
            "trace_capture_seconds": stages.get("step_trace_capture_seconds", 0.0),
            "physical_advance_seconds": stages.get("physical_advance_seconds", advance_wall),
            "cycle_advance_wall_seconds": advance_wall,
            "stages_seconds": stages,
            "end_to_end_seconds": time.perf_counter() - t_start,
            "worker_process_cpu_seconds": process_cpu,
            "worker_initial_rss_bytes": rss0,
            "worker_peak_rss_bytes": max([rss0 or 0] + [s["rss_bytes"] for s in samples]),
            "worker_peak_cpu_percent": max([0.0] + [s["cpu_percent"] for s in samples]),
            "artifact_bytes": None,
            "worker_output_dir": str(out),
            "scientific_primary_projection_sha256": scientific_projection_sha256,
            "campaign_started": False, "rpm_campaign_points_started": 0,
        }
        _atomic_json(out / "job-receipt.json", result)
        return result
    finally:
        stop[0] = True
        sampler.join(timeout=2)


def t_start_guard():
    return time.perf_counter()


def _run_scale(requested: int, task_specs: list[dict], budget: int,
               timeout: int) -> dict:
    import threading
    try:
        import psutil
        available = int(psutil.virtual_memory().available)
        cpu_count = psutil.cpu_count(logical=True) or os.cpu_count() or 1
    except ImportError:
        available, cpu_count = budget, os.cpu_count() or 1
    plan = _parallel_worker_plan(
        requested, budget, available_memory_bytes=available,
        cpu_count=cpu_count, reserve_per_worker_bytes=RESERVE_PER_WORKER)
    if plan["effective_workers"] < requested:
        raise RuntimeError(f"requested {requested} workers but resource plan permits "
                           f"{plan['effective_workers']}; no oversubscription attempted")
    started = time.perf_counter()
    cpu_stop, cpu_samples = [False], []
    def sample_cpu() -> None:
        try:
            import psutil
            while not cpu_stop[0]:
                cpu_samples.append(psutil.cpu_percent(interval=0.5, percpu=True))
        except ImportError:
            return
    cpu_sampler = threading.Thread(target=sample_cpu, daemon=True)
    cpu_sampler.start()
    ctx = multiprocessing.get_context("spawn")
    results = []
    try:
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=plan["effective_workers"], mp_context=ctx) as pool:
            futures = {pool.submit(_job, task): task for task in task_specs}
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                results.append(future.result())
    finally:
        cpu_stop[0] = True
        cpu_sampler.join(timeout=2)
    wall = time.perf_counter() - started
    cpu = sum(r["worker_process_cpu_seconds"] or 0 for r in results)
    max_rss_sum = sum(sorted((r["worker_peak_rss_bytes"] or 0 for r in results), reverse=True)[:plan["effective_workers"]])
    for result in results:
        out = Path(result["worker_output_dir"])
        result["artifact_bytes"] = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
        result.pop("worker_output_dir")
    compare = {}
    for point in ("A4000", "B4000"):
        a = next((r for r in results if r["point"] == point and r["scenario"] == "A_CONVENTIONAL"), None)
        c = next((r for r in results if r["point"] == point and r["scenario"] == "C_FAST_AUDITED"), None)
        compare[point] = {
            "canonical_scientific_fields_equal": bool(a and c and
                a["scientific_primary_projection_sha256"] == c["scientific_primary_projection_sha256"]),
            "conventional_primary_sha256": a["primary_sha256"] if a else None,
            "fast_audited_primary_sha256": c["primary_sha256"] if c else None,
            "full_primary_sha_equal": bool(a and c and a["primary_sha256"] == c["primary_sha256"]),
            "provisional_capture_speedup": (a["end_to_end_seconds"] /
                next(r["end_to_end_seconds"] for r in results if r["point"] == point and r["scenario"] == "B_FAST_PROVISIONAL")) if a else None,
            "fully_audited_fast_speedup": (a["end_to_end_seconds"] / c["end_to_end_seconds"])
                if a and c else None,
        }
    return {"requested_workers": requested, "worker_plan": plan,
            "spawn_and_coordination_inclusive_wall_seconds": wall,
            "average_cpu_utilization_per_core_percent": [
                round(sum(row[i] for row in cpu_samples) / len(cpu_samples), 2)
                for i in range(min((len(row) for row in cpu_samples), default=0))],
            "worker_cpu_seconds_sum": cpu,
            "peak_worker_rss_sum_upper_bound_bytes": max_rss_sum,
            "max_individual_worker_peak_rss_bytes": max((r["worker_peak_rss_bytes"] or 0 for r in results), default=0),
            "results": sorted(results, key=lambda r: r["task_id"]),
            "scientific_comparison": compare}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", default="1,2,4")
    parser.add_argument("--memory-budget-mib", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    root = args.output_root or Path(os.environ.get("DINO_ARTIFACT_ROOT", r"E:\Dino-artifacts")) / "engine-physics-v1/fast-recipe-v1/diagnostics"
    root = root.resolve() / f"benchmark-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    if root.is_relative_to(ROOT.resolve()):
        parser.error("diagnostic artifacts must stay outside the repository")
    prereg = _read_json(ROOT / PREREGISTRATION)
    variants = {r["variant_id"]: r for r in prereg["variants"]}
    runner_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = {"schema": "FAST_RECIPE_V1_BENCHMARK_RECEIPT_V1",
              "implementation_identity": "FAST_RECIPE_V1",
              "campaign_started": False, "rpm_campaign_points_started": 0,
              "historical_v1_artifacts_modified": False,
              "campaign_authorized": False, "artifact_root": str(root),
              "runner_sha256": runner_sha,
              "fast_recipe_module_sha256": hashlib.sha256((ROOT / "motorsim/fast_recipe_v1.py").read_bytes()).hexdigest(),
              "solver_dependency_hashes": _solver_dependency_hashes(),
              "preregistration_sha256": hashlib.sha256((ROOT / PREREGISTRATION).read_bytes()).hexdigest(),
              "method": "one cycle per A4000/B4000; A conventional trace+primary+audit; B trace-free recipe capture/write only; C trace-free capture+recipe read+canonical reconstruction+existing independent audit+primary write; spawn workers; all coordinator timings include process startup and coordination",
              "memory_budget_bytes": args.memory_budget_mib * 1024 * 1024,
              "reserved_memory_per_worker_bytes": RESERVE_PER_WORKER,
              "scales": []}
    for workers in [int(x) for x in args.workers.split(",") if x.strip()]:
        tasks = []
        for point, variant_id, rpm in (("A4000", "A_PRIME_MESH_0", 4000),
                                       ("B4000", "B_PRIME_MESH_0", 4000)):
            for scenario in ("A_CONVENTIONAL", "B_FAST_PROVISIONAL", "C_FAST_AUDITED"):
                task_id = f"w{workers}-{point}-{scenario}"
                tasks.append({"task_id": task_id, "point": point,
                              "variant": variants[variant_id], "rpm": rpm,
                              "variant_name": scenario,
                              "output_dir": str(root / f"workers-{workers}" / task_id),
                              "capture_runner_sha256": runner_sha,
                              "timeout_seconds": args.timeout_seconds})
        scale = _run_scale(workers, tasks, report["memory_budget_bytes"], args.timeout_seconds)
        report["scales"].append(scale)
        # Single coordinator persists progress/manifest atomically after all workers stop.
        _atomic_json(root / "coordinator-manifest.json", report)
    baseline = next((r["spawn_and_coordination_inclusive_wall_seconds"]
                     for r in report["scales"] if r["requested_workers"] == 1), None)
    for row in report["scales"]:
        row["speedup_vs_one_worker"] = (baseline / row["spawn_and_coordination_inclusive_wall_seconds"]
                                         if baseline else None)
        row["campaign_projection_30_points"] = None
        row["projection_note"] = "Not estimated: one-cycle diagnostic does not model convergence cycles, periodicity or campaign orchestration."
    report["status"] = "DIAGNOSTIC_COMPLETE_NO_CAMPAIGN"
    _atomic_json(root / "benchmark-receipt.json", report)
    identity = {"schema": "MOTORSIM_IMPLEMENTATION_IDENTITY_V1",
                "implementation": "FAST_RECIPE_V1",
                "runner_sha256": runner_sha,
                "module_sha256": report["fast_recipe_module_sha256"],
                "solver_dependency_hashes": _solver_dependency_hashes(),
                "campaign_authorized": False, "artifact_root": str(root)}
    _atomic_json(ROOT / "results/full-rpm-sweep-v1/fast-recipe-v1-identity.json", identity)
    _atomic_json(ROOT / "results/full-rpm-sweep-v1/fast-recipe-v1-benchmark-receipt.json", report)
    print(json.dumps({"status": report["status"], "artifact_root": str(root),
                      "scales": [{"requested_workers": r["requested_workers"],
                                  "wall_seconds": r["spawn_and_coordination_inclusive_wall_seconds"],
                                  "worker_cpu_seconds_sum": r["worker_cpu_seconds_sum"],
                                  "scientific_comparison": r["scientific_comparison"]}
                                 for r in report["scales"]]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
