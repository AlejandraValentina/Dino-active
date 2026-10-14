"""Bounded, single-cycle exhaust sensitivity diagnostic for Dino Desktop.

This is a diagnostic harness, not an RPM campaign. It compares the two
versioned variants in the starter project at 3000/4000 RPM and repeats the
base 3000 RPM point once to measure deterministic replay reproducibility.
All run primaries and checkpoints are written outside Git.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote

PROJECT = Path(__file__).resolve().parents[2] / "examples/projects/dino-2t-exhaust-comparison.dino2t.json"
EXPECTED_VARIANTS = ("Escape original", "Escape modified +20 mm")
sys.path.insert(0, str(PROJECT.parents[2]))

from motorsim.engine_configuration import canonical_json, identity, resolve_for_operating_point
from motorsim.engine_project import load_project
from motorsim.engine_variants import compare_configurations
from motorsim.exploratory_workflow import preflight, run_exploratory
from motorsim.integrated_2t import (audit_integrated_cycle_primary,
                                    make_integrated_engineering_output)
from motorsim.mechanical import MechanicalLossModel


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _trace(primary: dict, effective: dict) -> dict:
    audit = audit_integrated_cycle_primary(
        primary, preserve_precycle_p7_baseline=True)
    if audit.get("status") != "PASS" or audit.get("recomputed") is not True:
        raise ValueError("offline primary replay audit did not PASS")
    loss = MechanicalLossModel.from_dict(effective["mechanical_loss_model"])
    outputs = make_integrated_engineering_output(
        primary,
        displacement_m3=primary["swept_displacement_m3"],
        mechanical_loss_model=loss,
        load=effective["operating_conditions"]["load"],
        periodicity_status="NOT_EVALUATED")
    angles = outputs["crank_angle_trace"]["angle_deg"]
    channels = outputs["crank_angle_trace"]["channels"]
    return {"audit": audit, "angles_deg": angles, "channels": channels}


def _delta(left: dict, right: dict, channel: str) -> dict:
    a = dict(zip(left["angles_deg"], left["channels"][channel]["values"]))
    b = dict(zip(right["angles_deg"], right["channels"][channel]["values"]))
    common = sorted(a.keys() & b.keys())
    if len(common) < 2:
        return {"common_samples": len(common), "status": "INSUFFICIENT_EXACT_ANGLE_OVERLAP"}
    diffs = [a[angle] - b[angle] for angle in common]
    return {"common_samples": len(common), "left_samples": len(a),
            "right_samples": len(b), "max_abs_difference": max(map(abs, diffs)),
            "rms_difference": math.sqrt(math.fsum(value * value for value in diffs) / len(diffs)),
            "comparison": "EXACT_COMMON_CRANK_ANGLES_NO_INTERPOLATION"}


def run(*, artifact_root: Path, run_prefix: str, budget_seconds: float,
        memory_limit_mib: int) -> dict:
    project = load_project(PROJECT)
    if set(EXPECTED_VARIANTS) - set(project["variants"]):
        raise ValueError("starter project is missing the two registered diagnostic variants")
    variants = {name: project["variants"][name] for name in EXPECTED_VARIANTS}
    base_name, modified_name = EXPECTED_VARIANTS
    base, modified = variants[base_name], variants[modified_name]
    differences = compare_configurations(base, modified)
    allowed_prefixes = (
        "/native_configuration/geometry_identity/chamber/sections/1/length_mm",
        "/native_configuration/ducts/",
        "/native_configuration/duct_species/exhaust/",
    )
    diff_paths = [row["path"] for row in differences]
    if (not all(path.startswith(allowed_prefixes) for path in diff_paths) or
            base["operating_conditions"] != modified["operating_conditions"] or
            base["mechanical_loss_model"] != modified["mechanical_loss_model"]):
        raise ValueError("the variants differ outside the controlled exhaust geometry and derived state")

    deadline = time.monotonic() + budget_seconds
    specs = [(base_name, 3000.0, "base-3000-r1"),
             (modified_name, 3000.0, "modified-3000-r1"),
             (base_name, 4000.0, "base-4000-r1"),
             (modified_name, 4000.0, "modified-4000-r1"),
             (base_name, 3000.0, "base-3000-repeat")]
    runs = []
    traces = {}
    for variant_label, rpm, suffix in specs:
        remaining = deadline - time.monotonic()
        if remaining < 2.0:
            runs.append({"variant": variant_label, "rpm": rpm, "run_id": f"{run_prefix}-{suffix}",
                         "classification": "NOT_STARTED_BUDGET_EXHAUSTED_BEFORE_PREFLIGHT"})
            continue
        run_id = f"{run_prefix}-{suffix}"
        doc = variants[variant_label]
        check = preflight(doc, rpm=rpm, max_cycles=1,
                          budget_seconds=min(600.0, remaining),
                          memory_limit_mib=memory_limit_mib)
        effective = resolve_for_operating_point(doc, rpm=rpm)
        started = time.monotonic()
        try:
            result = run_exploratory(
                doc, project_id=project["project_id"], run_id=run_id,
                artifact_root=artifact_root, rpm=rpm, max_cycles=1,
                budget_seconds=min(600.0, max(1.0, remaining)),
                memory_limit_mib=memory_limit_mib, variant_label=variant_label)
            row = {"variant": variant_label, "rpm": rpm, "run_id": run_id,
                   "preflight": check, "classification": result["classification"],
                   "status": result["status"], "cycles_completed": result["cycles_completed"],
                   "periodicity": result["periodicity"], "elapsed_seconds": result["elapsed_seconds"],
                   "wall_seconds_including_offline_analysis": time.monotonic()-started,
                   "identity_sha256": result["bindings"]["identity_sha256"],
                   "configuration_sha256": result["bindings"]["configuration_sha256"],
                   "source_hashes": result["bindings"]["source_hashes"],
                   "result_sha256": result["result_sha256"],
                   "checkpoint_sha256": result["checkpoint_sha256"],
                   "artifact_directory": result["artifact_directory"],
                   "cycle_records": result["cycles"]}
            if result["cycles_completed"] == 1:
                cycle = result["cycles"][0]
                primary_path = Path(result["artifact_directory"]) / cycle["artifact"]
                payload = gzip.decompress(primary_path.read_bytes())
                if _sha_bytes(payload) != cycle["primary_sha256"]:
                    raise ValueError("cycle primary SHA-256 does not match run manifest")
                primary = json.loads(payload)
                trace = _trace(primary, effective)
                row["primary_sha256"] = cycle["primary_sha256"]
                row["primary_audit"] = trace["audit"]
                row["conservation"] = primary["conservation"]
                row["engineering_metric_status"] = {
                    name: record["status"] for name, record in
                    result["cycles"][0]["engineering_output"]["cycle_metrics"].items()
                }
                traces[(variant_label, rpm, suffix)] = trace
            runs.append(row)
        except Exception as exc:
            runs.append({"variant": variant_label, "rpm": rpm, "run_id": run_id,
                         "preflight": check, "classification": "DIAGNOSTIC_EXECUTION_ERROR",
                         "error": f"{type(exc).__name__}: {exc}",
                         "wall_seconds": time.monotonic()-started})

    comparisons = {}
    for rpm in (3000.0, 4000.0):
        a = traces.get((base_name, rpm, "base-3000-r1" if rpm==3000 else "base-4000-r1"))
        b = traces.get((modified_name, rpm, "modified-3000-r1" if rpm==3000 else "modified-4000-r1"))
        if a is None or b is None:
            comparisons[str(int(rpm))] = {"status":"MISSING_OR_INCOMPLETE_POINT"}
            continue
        selected = ["cylinder_pressure_pa"]
        selected += [f"duct:exhaust:cell:{i}:pressure_pa" for i in range(5)]
        selected += [f"duct:exhaust:face:{i}:mass_flow_kg_s" for i in range(6)]
        comparisons[str(int(rpm))] = {name:_delta(a,b,name) for name in selected
                                      if name in a["channels"] and name in b["channels"]}
    repeat_a = traces.get((base_name,3000.0,"base-3000-r1"))
    repeat_b = traces.get((base_name,3000.0,"base-3000-repeat"))
    repeat = {"status":"MISSING_OR_INCOMPLETE_REPEAT"}
    if repeat_a is not None and repeat_b is not None:
        repeat = {"same_primary_sha256": None, "channel_comparisons": {}}
        first = next((r for r in runs if r["run_id"].endswith("base-3000-r1")), None)
        second = next((r for r in runs if r["run_id"].endswith("base-3000-repeat")), None)
        repeat["same_primary_sha256"] = bool(first and second and
            first.get("primary_sha256") == second.get("primary_sha256"))
        for name in ("cylinder_pressure_pa", "duct:exhaust:cell:1:pressure_pa",
                     "duct:exhaust:face:2:mass_flow_kg_s"):
            if name in repeat_a["channels"] and name in repeat_b["channels"]:
                repeat["channel_comparisons"][name] = _delta(repeat_a, repeat_b, name)

    report = {"schema":"DINO_DESIGN_VALIDATION_V1_EXHAUST_DIAGNOSTIC_REPORT_V1",
        "classification":"EXPLORATORY_DIAGNOSTIC_NOT_EXPERIMENTAL_VALIDATION",
        "project_path":str(PROJECT), "project_sha256":_sha_bytes(PROJECT.read_bytes()),
        "project_id":project["project_id"], "run_prefix":run_prefix,
        "diagnostic_budget_seconds":budget_seconds, "memory_limit_mib":memory_limit_mib,
        "run_ids_are_single_point_not_campaign":True, "cycles_per_run":1,
        "operating_points_rpm":[3000,4000], "configured_variants":list(EXPECTED_VARIANTS),
        "controlled_variant_diff_paths":diff_paths,
        "solver_diagnostics":{"runs":runs,"exhaust_pressure_and_mass_flow_comparisons":comparisons,
            "repeatability":repeat},
        "claims":{"periodicity":"NOT_ESTABLISHED_BY_ONE_CYCLE",
            "steady_performance_comparison":"NOT_VALID; transient power/torque are not used",
            "experimental_validation":"NOT_PERFORMED",
            "predictive_validation":"NOT_CLAIMED",
            "interpolation":"NONE; compare exact common crank-angle samples only"},
        "wall_seconds_total":budget_seconds-(deadline-time.monotonic()),
        "diagnostic_script_sha256":_sha_bytes(Path(__file__).read_bytes())}
    report_path=artifact_root/"reports"/f"{run_prefix}-report.json"
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"report_path":str(report_path),"classification":report["classification"],
            "wall_seconds_total":report["wall_seconds_total"],
            "run_summaries":[{"run_id":r["run_id"],"classification":r["classification"],
                "elapsed_seconds":r.get("elapsed_seconds"),"cycles_completed":r.get("cycles_completed"),
                "artifact_directory":r.get("artifact_directory")} for r in runs],
            "comparisons":comparisons,"repeatability":repeat,
            "claims":report["claims"]}


def main() -> int:
    default_root=Path(os.environ.get("DINO_ARTIFACT_ROOT",r"E:\Dino-artifacts")) / "dino-design-validation-v1"
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root",type=Path,default=default_root)
    parser.add_argument("--run-prefix",required=True)
    parser.add_argument("--budget-seconds",type=float,default=570.0)
    parser.add_argument("--memory-limit-mib",type=int,default=2048)
    args=parser.parse_args()
    if not 30.0<=args.budget_seconds<=600.0:
        parser.error("budget-seconds must be between 30 and 600")
    if args.run_prefix and not all(c.isalnum() or c in "._-" for c in args.run_prefix):
        parser.error("run-prefix must be a safe path component")
    print(json.dumps(run(artifact_root=args.artifact_root,run_prefix=args.run_prefix,
                         budget_seconds=args.budget_seconds,memory_limit_mib=args.memory_limit_mib),
                     ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
