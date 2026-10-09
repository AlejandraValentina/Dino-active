"""Diagnostic-only IMPL2 evidence and Windows spawn parallelism benchmark.

Runs one complete cycle from the existing A4000/B4000 configurations. It does
not call the campaign runner, touch campaign manifests, or start RPM points.
Artifacts are written under DINO_ARTIFACT_ROOT (outside Git).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import statistics
import sys
import time
from multiprocessing import get_context
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.full_rpm_evidence_impl2 import (  # noqa: E402
    canonical_bytes,
    decode_segmented_primary,
    encode_segmented_primary,
)
from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T,
    _solver_dependency_hashes,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
)
from scripts.full_rpm_sweep_v1_campaign import (  # noqa: E402
    _advance_to_bounded,
    _configuration_for,
    PREREGISTRATION,
    _read_json,
)


def _atomic_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, sort_keys=True, indent=2,
                         ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_gzip_atomic(path: Path, payload: bytes) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                stream.write(payload)
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path.stat().st_size


def _read_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rb") as stream:
        return json.loads(stream.read().decode("utf-8"))


def _rss() -> int | None:
    try:
        import psutil
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError):
        return None


def _diagnostic_task(task: dict) -> dict:
    """A process owns one engine, config, evidence pair, and output directory."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        process_cpu_start = process.cpu_times()
        rss_stage = {"process_start": int(process.memory_info().rss)}
    except (ImportError, OSError):
        psutil = None
        process = None
        process_cpu_start = None
        rss_stage = {}
    variant = task["variant"]
    rpm = int(task["rpm"])
    out = Path(task["output_dir"])
    cfg = _configuration_for(variant, rpm)
    cfg_bytes = canonical_bytes(cfg)
    cfg_sha = hashlib.sha256(cfg_bytes).hexdigest()
    engine = IntegratedEngine2T.from_configuration_dict(cfg)
    if process is not None:
        rss_stage["engine_constructed"] = int(process.memory_info().rss)
    start_snapshot = engine.snapshot()
    rejected: list[dict] = []
    t0 = time.perf_counter()
    _advance_to_bounded(engine, 360.0, rejected, time.monotonic() + task["timeout_seconds"])
    solver_s = time.perf_counter() - t0
    end_snapshot = engine.snapshot()
    t0 = time.perf_counter()
    primary = make_integrated_cycle_primary(
        engine, start_snapshot, end_snapshot, 1,
        rejected_trials=rejected, runner_sha256=task["runner_sha256"])
    build_s = time.perf_counter() - t0
    if process is not None:
        rss_stage["primary_constructed"] = int(process.memory_info().rss)
    primary_bytes = canonical_bytes(primary)
    primary_sha = hashlib.sha256(primary_bytes).hexdigest()

    # Reference path: independent existing audit + canonical JSON and atomic
    # compressed persistence, preserving the v1-compatible primary payload.
    t0 = time.perf_counter()
    legacy_bytes = _write_gzip_atomic(out / "legacy-primary.json.gz", primary_bytes)
    legacy_io_s = time.perf_counter() - t0
    legacy_file_sha = hashlib.sha256((out / "legacy-primary.json.gz").read_bytes()).hexdigest()
    t0 = time.perf_counter()
    legacy_loaded = _read_gzip_json(out / "legacy-primary.json.gz")
    legacy_read_parse_s = time.perf_counter() - t0
    if hashlib.sha256(canonical_bytes(legacy_loaded)).hexdigest() != primary_sha:
        raise ValueError("persisted legacy primary changed its canonical hash")
    t0 = time.perf_counter()
    legacy_audit = audit_integrated_cycle_primary(legacy_loaded)
    legacy_audit_s = time.perf_counter() - t0
    # IMPL2 prototype: transpose trajectory, persist, reconstruct canonical
    # primary, then invoke the same independent auditor on the rebuilt object.
    t0 = time.perf_counter()
    segment = encode_segmented_primary(primary)
    segment_encode_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    segment_payload = canonical_bytes(segment)
    segment_bytes = _write_gzip_atomic(
        out / "segmented-primary.json.gz", segment_payload)
    segment_sha = hashlib.sha256(segment_payload).hexdigest()
    segment_file_sha = hashlib.sha256(
        (out / "segmented-primary.json.gz").read_bytes()).hexdigest()
    segment_io_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    segment_loaded = _read_gzip_json(out / "segmented-primary.json.gz")
    segment_read_parse_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    reconstructed = decode_segmented_primary(segment_loaded)
    reconstruction_s = time.perf_counter() - t0
    reconstructed_sha = hashlib.sha256(canonical_bytes(reconstructed)).hexdigest()
    if reconstructed_sha != primary_sha:
        raise ValueError("segmented reconstruction changed canonical primary")
    t0 = time.perf_counter()
    segmented_audit = audit_integrated_cycle_primary(reconstructed)
    segmented_audit_s = time.perf_counter() - t0
    if (legacy_audit.get("status") != "PASS" or
            segmented_audit.get("status") != "PASS" or
            legacy_audit.get("recomputed") is not True or
            segmented_audit.get("recomputed") is not True):
        raise ValueError("independent primary audit failed")

    if process is not None:
        rss_stage["audited_and_reconstructed"] = int(process.memory_info().rss)
        process_cpu_end = process.cpu_times()
        cpu_s = float((process_cpu_end.user - process_cpu_start.user) +
                      (process_cpu_end.system - process_cpu_start.system))
    else:
        cpu_s = None
    result = {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_DIAGNOSTIC_TASK_V1",
        "task_id": task["task_id"], "variant_id": variant["variant_id"],
        "rpm": rpm, "configuration_sha256": cfg_sha,
        "solver_dependency_hashes": _solver_dependency_hashes(),
        "primary_sha256": primary_sha,
        "reconstructed_primary_sha256": reconstructed_sha,
        "primary_audit_passed": legacy_audit.get("status") == "PASS",
        "reconstructed_primary_audit_passed": segmented_audit.get("status") == "PASS",
        "canonical_equality": primary_sha == reconstructed_sha,
        "trajectory_rows": len(primary["trajectory"]),
        "accepted_steps": engine.accepted_steps,
        "rejected_trials": len(rejected),
        "solver_seconds": solver_s,
        "primary_construction_seconds": build_s,
        "legacy_audit_seconds": legacy_audit_s,
        "legacy_atomic_write_seconds": legacy_io_s,
        "legacy_read_parse_seconds": legacy_read_parse_s,
        "legacy_compressed_bytes": legacy_bytes,
        "legacy_file_sha256": legacy_file_sha,
        "segmented_encode_seconds": segment_encode_s,
        "segmented_atomic_write_seconds": segment_io_s,
        "segmented_read_parse_seconds": segment_read_parse_s,
        "segmented_reconstruction_seconds": reconstruction_s,
        "segmented_independent_audit_seconds": segmented_audit_s,
        "segmented_bytes": segment_bytes,
        "segmented_payload_sha256": segment_sha,
        "segmented_file_sha256": segment_file_sha,
        "legacy_path_seconds": (solver_s + build_s + legacy_io_s +
                                legacy_read_parse_s + legacy_audit_s),
        "segmented_path_seconds": (solver_s + build_s + segment_encode_s + segment_io_s +
                                   segment_read_parse_s + reconstruction_s +
                                   segmented_audit_s),
        "worker_process_cpu_seconds": cpu_s,
        "worker_rss_stage_bytes": rss_stage,
        "worker_rss_bytes": max(rss_stage.values(), default=_rss()),
    }
    result["coordinator_receipt_bytes"] = len(canonical_bytes(result))
    _atomic_json(out / "task-receipt.json", result)
    return result


def _cpu_sampler(stop: list[bool], samples: list[list[float]]) -> None:
    try:
        import psutil
        while not stop[0]:
            samples.append(psutil.cpu_percent(interval=0.5, percpu=True))
    except ImportError:
        return


def _run_scale(tasks: list[dict], workers: int, memory_budget_bytes: int,
               timeout_seconds: int) -> dict:
    import threading
    try:
        import psutil
        available = int(psutil.virtual_memory().available)
    except ImportError:
        available = memory_budget_bytes
    per_worker_reserve = 512 * 1024 * 1024
    memory_workers = max(1, min(workers, memory_budget_bytes // per_worker_reserve,
                                available // per_worker_reserve))
    effective = max(1, min(memory_workers, len(tasks)))
    stop, samples = [False], []
    sampler = threading.Thread(target=_cpu_sampler, args=(stop, samples), daemon=True)
    sampler.start()
    started = time.perf_counter()
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=effective, mp_context=get_context("spawn"))
    futures = {executor.submit(_diagnostic_task, task): task for task in tasks}
    results = []
    pending = set(futures)
    try:
        while pending:
            done, pending = concurrent.futures.wait(
                pending, timeout=min(0.5, timeout_seconds),
                return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                results.append(future.result())
            if time.perf_counter() - started > timeout_seconds:
                for future in pending:
                    future.cancel()
                raise TimeoutError(f"diagnostic scale {workers} workers timed out")
    except BaseException:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=True)
    finally:
        stop[0] = True
        sampler.join(timeout=2)
    elapsed = time.perf_counter() - started
    total_cpu = sum((r["worker_process_cpu_seconds"] or 0) for r in results)
    return {
        "requested_workers": workers, "effective_workers": effective,
        "memory_budget_bytes": memory_budget_bytes,
        "available_memory_at_start_bytes": available,
        "reserved_memory_per_worker_bytes": per_worker_reserve,
        "wall_seconds": elapsed, "worker_cpu_seconds_sum": total_cpu,
        "average_cpu_utilization_per_core_percent": ([
            round(sum(row[i] for row in samples) / len(samples), 2)
            for i in range(min((len(row) for row in samples), default=0))]
            if samples else None),
        "max_observed_worker_rss_bytes": max(
            (r["worker_rss_bytes"] or 0 for r in results), default=None),
        "results": sorted(results, key=lambda r: r["task_id"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", default="1,2,4",
                        help="diagnostic worker counts; never a campaign switch")
    parser.add_argument("--memory-budget-mib", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    artifact_root = (args.output_root or Path(os.environ.get(
        "DINO_ARTIFACT_ROOT", r"E:\Dino-artifacts")) /
        "engine-physics-v1/full-rpm-sweep-v1-impl2/diagnostics/fast-evidence-multiprocess")
    if artifact_root.resolve().is_relative_to(ROOT.resolve()):
        parser.error("diagnostic artifacts must remain outside the repository")
    prereg = _read_json(ROOT / PREREGISTRATION)
    variants = {row["variant_id"]: row for row in prereg["variants"]}
    selected = [("A_PRIME_MESH_0", 4000), ("B_PRIME_MESH_0", 4000)]
    runner_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_FAST_EVIDENCE_MULTIPROCESS_BENCHMARK_V1",
        "campaign_started": False,
        "rpm_points_started": 0,
        "historical_v1_artifacts_modified": False,
        "artifact_root": str(artifact_root),
        "runner_sha256": runner_sha,
        "preregistration_sha256": hashlib.sha256(canonical_bytes(prereg)).hexdigest(),
        "solver_dependency_hashes": _solver_dependency_hashes(),
        "method": ("two diagnostic repeats each for A4000/B4000; one complete cycle; "
                   "legacy and lossless segmented paths independently replay-audited"),
        "scales": [],
    }
    task_index = 0
    for requested in [int(x.strip()) for x in args.workers.split(",") if x.strip()]:
        tasks = []
        for repeat in (1, 2):
            for variant_id, rpm in selected:
                task_index += 1
                task_id = f"w{requested}-r{repeat}-{variant_id}-{rpm}"
                tasks.append({
                    "task_id": task_id, "variant": variants[variant_id], "rpm": rpm,
                    "output_dir": str(artifact_root / task_id),
                    "runner_sha256": runner_sha,
                    "timeout_seconds": args.timeout_seconds,
                })
        report["scales"].append(_run_scale(
            tasks, requested, args.memory_budget_mib * 1024 * 1024,
            args.timeout_seconds))
        _atomic_json(artifact_root / "benchmark-progress.json", report)
    scale_results = report["scales"]
    if scale_results:
        serial = next((row for row in scale_results if row["requested_workers"] == 1), None)
        for row in scale_results:
            row["multiprocess_speedup_vs_one_worker"] = (
                serial["wall_seconds"] / row["wall_seconds"]
                if serial and row["wall_seconds"] else None)
    report["status"] = "DIAGNOSTIC_COMPLETE_NO_CAMPAIGN"
    _atomic_json(artifact_root / "benchmark-report.json", report)
    print(json.dumps({"status": report["status"], "artifact_root": str(artifact_root),
                      "scales": [{k: v for k, v in row.items() if k != "results"}
                                 for row in report["scales"]]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
