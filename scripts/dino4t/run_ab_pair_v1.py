"""Execute the one preregistered synthetic Dino 4T A/B integration pair.

This bounded driver refuses to overwrite prior output and never retries. The
result is model sensitivity evidence only, not experimental validation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim import engine_platform
from motorsim.dino4t import api
from motorsim.desktop.four_stroke_comparison import ComparisonIneligible, build_comparison
from motorsim.desktop.four_stroke_desktop import _curve_binding
from motorsim.desktop.four_stroke_project import create_project, load_example
from motorsim.engine_project import save_project

PROTOCOL = "DINO4T_DESKTOP_AB_PAIR_V1"
PAIR_BUDGET_S = 720.0
POINT_BUDGET_S = 300.0
MAX_CYCLES = 20
BASE_CONFIG = ROOT / "configs/dino4t/example_single_cylinder_500cc.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")
    temporary.replace(path)


def _endpoint(config: dict, variant_id: str, out_root: Path, pair_started: float, index: int) -> dict:
    run_id = f"d4ab-v1-{index}-{hashlib.sha256((variant_id + str(time.time_ns())).encode()).hexdigest()[:12]}"
    run_root = out_root / "runs" / run_id
    artifacts = run_root / "artifacts"
    remaining = PAIR_BUDGET_S - (time.monotonic() - pair_started)
    if remaining <= 1.0:
        return {"run_id": run_id, "variant_id": variant_id, "skipped": "pair budget exhausted"}
    wall_limit = min(POINT_BUDGET_S, remaining)
    checked = engine_platform.validate_config("4T", config)
    if not checked["valid"] or checked.get("unknown_keys"):
        raise ValueError(f"prevalidated {variant_id} config unexpectedly invalid: {checked}")

    # A single API call per design. No warm start, retry, tolerance change or
    # continuation is permitted by the preregistered protocol.
    started = time.monotonic()
    envelope = api.run(config, out_dir=artifacts, max_cycles=MAX_CYCLES,
                       wall_limit_s=wall_limit)
    elapsed = time.monotonic() - started
    summary = envelope.get("summary")
    record = {"run_id": run_id, "variant_id": variant_id, "api": envelope.get("api"),
              "ok": envelope.get("ok"), "error": envelope.get("error"),
              "elapsed_including_api_artifacts_s": elapsed,
              "wall_limit_s": wall_limit, "summary": summary}
    if summary is None:
        _atomic_json(run_root / "api-error.json", record)
        return record

    summary_path = artifacts / "summary.json"
    config_path = artifacts / "config_resolved.json"
    trace_path = artifacts / "trace_last_cycle.csv"
    result_hash = _sha(summary_path)
    resolved = json.loads(config_path.read_text(encoding="utf-8"))
    meta = {
        "schema": "DINO4T_DESKTOP_RUN_V1", "run_id": run_id,
        "project_id": "dino4t-synthetic-ab-v1", "variant_id": variant_id,
        "api": envelope["api"], "result_sha256": result_hash,
        "config_sha256": summary["config_sha256"],
        "config_identity_sha256": engine_platform.identity("4T", resolved),
        "curve_binding_sha256": _curve_binding(resolved),
        "summary_path": str(summary_path.resolve()), "config_path": str(config_path.resolve()),
        "trace_path": str(trace_path.resolve()), "status": summary["status"],
        "periodicity_status": summary["periodicity"]["status"],
        "evidence_level": summary["evidence_level"], "claims": summary["claims"],
    }
    _atomic_json(run_root / "run.json", meta)
    return {**record, "result_sha256": result_hash, "config_sha256": summary["config_sha256"],
            "run_root": str(run_root.resolve()), "meta": meta}


def execute(out_root: Path) -> dict:
    if out_root.exists():
        raise FileExistsError(f"refusing to overwrite existing pair output: {out_root}")
    pair_started = time.monotonic()
    config_a = load_example()
    config_a["identifier"] = "dino4t-ab-v1-A-baseline"
    config_b = copy.deepcopy(config_a)
    config_b["identifier"] = "lift-8mm"
    config_b["intake_valve"]["lift"]["max_lift_mm"] = 8.0

    common = {"rpm": 6000.0, "equivalence_ratio": 1.0}
    for config in (config_a, config_b):
        config["operating_point"] = copy.deepcopy(common)
        config["numerics"]["max_cycles"] = MAX_CYCLES
        checked = engine_platform.validate_config("4T", config)
        if not checked["valid"] or checked.get("unknown_keys"):
            raise ValueError(f"preregistered config invalid before run: {checked}")

    receipt = {"schema": "DINO4T_AB_PAIR_EXECUTION_V1", "protocol": PROTOCOL,
        "protocol_path": "results/dino4t-ab-engineering-v1/preregistration/AB_PAIR_PROTOCOL_V1.md",
        "source_base_config": str(BASE_CONFIG.relative_to(ROOT)),
        "source_base_config_sha256": _sha(BASE_CONFIG),
        "source_code_commit": __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True,
            text=True).stdout.strip(),
        "synthetic_only": True, "experimental_validation": "NOT_PERFORMED",
        "predictive_capability": "NOT_CLAIMED",
        "conditions": {"rpm": 6000.0, "equivalence_ratio": 1.0, "max_cycles": MAX_CYCLES,
            "point_wall_cap_s": POINT_BUDGET_S, "pair_wall_cap_including_overhead_s": PAIR_BUDGET_S,
            "warm_start": False, "retries": 0,
            "A": "unchanged example configuration except identifier and fixed operating point",
            "B": "A with intake valve harmonic max_lift_mm changed from 10.0 to 8.0"},
        "runs": []}
    _atomic_json(out_root / "pair-receipt.json", receipt)
    run_a = _endpoint(config_a, "", out_root, pair_started, 1)
    receipt["runs"].append(run_a)
    _atomic_json(out_root / "pair-receipt.json", receipt)
    if time.monotonic() - pair_started < PAIR_BUDGET_S:
        run_b = _endpoint(config_b, "lift-8mm", out_root, pair_started, 2)
    else:
        run_b = {"variant_id": "lift-8mm", "skipped": "pair budget exhausted before start"}
    receipt["runs"].append(run_b)
    endpoints_for_compare = []
    for run in (run_a, run_b):
        meta = run.get("meta")
        if not meta:
            continue
        summary_path = Path(meta["summary_path"])
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        config = json.loads(Path(meta["config_path"]).read_text(encoding="utf-8"))
        trace = Path(meta["trace_path"])
        reference = {"run_id": meta["run_id"], "path": str(summary_path.resolve()),
            "result_sha256": meta["result_sha256"], "config_sha256": meta["config_sha256"],
            "status": meta["status"], "periodicity_status": meta["periodicity_status"],
            "variant_id": meta["variant_id"]}
        endpoints_for_compare.append({"summary": summary, "config": config, "meta": meta,
            "reference": reference, "trace_sha256": _sha(trace) if trace.exists() else None})
    refs = [endpoint["reference"] for endpoint in endpoints_for_compare]
    project = create_project("dino4t-synthetic-ab-v1", config_a,
        variants={"lift-8mm": config_b}, run_references=refs,
        scientific_validation_status="SYNTHETIC_UNVALIDATED")
    project_path = out_root / "dino4t-synthetic-ab-v1.dino.json"
    save_project(project_path, project)
    receipt["project"] = {"path": str(project_path.resolve()), "schema": project["schema"],
        "sha256": _sha(project_path), "run_references": len(refs)}
    receipt["elapsed_total_s"] = time.monotonic() - pair_started
    receipt["budget_remaining_s"] = PAIR_BUDGET_S - receipt["elapsed_total_s"]
    if len(endpoints_for_compare) == 2:
        try:
            comparison = build_comparison(*endpoints_for_compare)
        except ComparisonIneligible as exc:
            receipt["comparison"] = {"eligible": False, "reason": str(exc),
                "note": "No performance deltas calculated because at least one registered gate failed."}
        else:
            comparison_path = out_root / "comparison.json"
            _atomic_json(comparison_path, comparison)
            receipt["comparison"] = {"eligible": True, "path": str(comparison_path.resolve()),
                "sha256": _sha(comparison_path), "comparison_id": comparison["comparison_id"],
                "classification": comparison["classification"]}
    else:
        receipt["comparison"] = {"eligible": False,
            "reason": "Both results are required; no deltas computed."}
    _atomic_json(out_root / "pair-receipt.json", receipt)
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path,
        default=ROOT / "results/dino4t-ab-engineering-v1/runs")
    args = parser.parse_args(argv)
    try:
        receipt = execute(args.out_root)
    except (OSError, ValueError, FileExistsError) as exc:
        print(json.dumps({"protocol": PROTOCOL, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"protocol": PROTOCOL, "runs": [
        {"run_id": run.get("run_id"), "variant_id": run.get("variant_id"),
         "ok": run.get("ok"), "elapsed_s": run.get("elapsed_including_api_artifacts_s"),
         "status": (run.get("summary") or {}).get("status"),
         "periodicity": ((run.get("summary") or {}).get("periodicity") or {}).get("status"),
         "cycles": (run.get("summary") or {}).get("cycles_run"), "skipped": run.get("skipped")}
        for run in receipt["runs"]], "elapsed_total_s": receipt["elapsed_total_s"],
        "comparison": receipt["comparison"], "receipt": str((args.out_root / "pair-receipt.json").resolve())},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
