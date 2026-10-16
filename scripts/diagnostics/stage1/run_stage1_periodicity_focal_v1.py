"""Preregistered, single-point Stage 1 periodicity diagnostic.

Default invocation performs only the bound preflight. A simulation requires
both the explicit execution flag and the exact frozen preregistration hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from motorsim.engine_configuration import resolve_for_operating_point
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration
from motorsim.exploratory_workflow import preflight, run_exploratory
from motorsim.desktop.preferences import repository_root_containing

PROTOCOL = ROOT / "results/dino-stage1-scientific-readiness/preregistration/stage1-diagnostic-protocol-v1.json"
PROJECT = ROOT / "examples/projects/dino-2t-exhaust-comparison.dino2t.json"
VARIANT = "Escape original"
RPM = 3000
CELLS_PER_SECTION = 8
MAX_CYCLES = 8
BUDGET_SECONDS = 600
MEMORY_LIMIT_MIB = 2048
RUN_ID = "stage1-original-3000rpm-mesh8-periodicity-v1"


def _sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _load_configuration():
    project = load_project(PROJECT)
    source = project["variants"][VARIANT]
    sections = source["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    refined = refine_exhaust_configuration(source, [1] * len(sections))
    refined = refine_exhaust_configuration(refined, [CELLS_PER_SECTION] * len(sections))
    effective = resolve_for_operating_point(refined, rpm=RPM)
    preflight_result = preflight(
        refined,
        rpm=RPM,
        max_cycles=MAX_CYCLES,
        budget_seconds=BUDGET_SECONDS,
        memory_limit_mib=MEMORY_LIMIT_MIB,
    )
    return project, refined, effective, preflight_result


def artifact_root() -> Path:
    base = Path(os.environ.get("DINO_ARTIFACT_ROOT", Path.home() / "Dino-artifacts")).expanduser().resolve()
    if repository_root_containing(base) is not None:
        raise RuntimeError("DINO_ARTIFACT_ROOT is inside a Git repository; refusing output")
    root = base / "dino-stage1-scientific-readiness" / "v1"
    if repository_root_containing(root) is not None:
        raise RuntimeError("Stage 1 artifact root is inside a Git repository; refusing output")
    return root


def validate_binding(protocol: dict, effective: dict, preflight_result: dict, *, runner_sha256: str,
                     project_sha256: str) -> None:
    expected = protocol["frozen_binding"]
    checks = {
        "runner_sha256": (runner_sha256, expected["runner_sha256"]),
        "project_sha256": (project_sha256, expected["project_sha256"]),
        "configuration_sha256": (preflight_result["configuration_sha256"], expected["configuration_sha256"]),
        "identity_sha256": (preflight_result["identity_sha256"], expected["identity_sha256"]),
        "mechanical_loss_model_sha256": (preflight_result["mechanical_loss_model_sha256"], expected["mechanical_loss_model_sha256"]),
        "fuel_id": (preflight_result["fuel_id"], expected["fuel_id"]),
    }
    mismatches = [key for key, (actual, frozen) in checks.items() if actual != frozen]
    actual_sources = effective["source_hashes"]
    if actual_sources != expected["solver_source_hashes"]:
        mismatches.append("solver_source_hashes")
    if mismatches:
        raise RuntimeError("FAIL_CLOSED preregistration binding mismatch: " + ", ".join(mismatches))
    if preflight_result.get("status") != "PASS" or preflight_result.get("solver_steps") != 0:
        raise RuntimeError("FAIL_CLOSED no-solver preflight did not PASS with zero steps")


def run(*, execute: bool, preregistration_sha256: str | None, resume: bool) -> dict:
    invocation_started = time.monotonic()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    project, refined, effective, check = _load_configuration()
    root = artifact_root()
    source_file_hash = _sha(Path(__file__))
    project_file_hash = _sha(PROJECT)
    validate_binding(protocol, effective, check, runner_sha256=source_file_hash,
                     project_sha256=project_file_hash)
    output = {
        "schema": "DINO_STAGE1_PERIODICITY_PREFLIGHT_V1",
        "classification": "PREFLIGHT_ONLY_NO_SOLVER_STEPS",
        "preflight": check,
        "project_sha256": project_file_hash,
        "runner_sha256": source_file_hash,
        "artifact_root": str(root),
        "protocol_sha256": _sha(PROTOCOL),
        "configuration_sha256": check["configuration_sha256"],
        "identity_sha256": check["identity_sha256"],
    }
    if not execute:
        return output
    authorization = protocol.get("authorization", {})
    if (authorization.get("solver_execution_authorized_within_this_single_point_scope") is not True or
            authorization.get("campaign_authorization") is not False):
        raise RuntimeError("FAIL_CLOSED protocol does not authorize this single-point diagnostic")
    actual_preregistration_sha256 = _sha(PROTOCOL)
    if preregistration_sha256 != actual_preregistration_sha256:
        raise RuntimeError("FAIL_CLOSED execution requires the exact preregistration SHA-256")
    run_directory = root / "exploratory-workflow-v1" / project["project_id"] / RUN_ID
    report = root / "reports" / f"{RUN_ID}.json"
    cumulative_prior = 0.0
    if resume:
        checkpoint = run_directory / "checkpoint.json"
        if not checkpoint.is_file() or not report.is_file():
            raise RuntimeError("FAIL_CLOSED resume requires a prior report and point checkpoint")
        previous = json.loads(report.read_text(encoding="utf-8"))
        if (previous.get("protocol_sha256") != actual_preregistration_sha256 or
                previous.get("configuration_sha256") != check["configuration_sha256"] or
                previous.get("identity_sha256") != check["identity_sha256"]):
            raise RuntimeError("FAIL_CLOSED prior report binding mismatch")
        cumulative_prior = float(previous.get("cumulative_wall_seconds", 0.0))
    elif run_directory.exists() or report.exists():
        raise RuntimeError("FAIL_CLOSED point artifacts already exist; explicit compatible resume is required")
    invocation_overhead = time.monotonic() - invocation_started
    remaining_budget = BUDGET_SECONDS - cumulative_prior - invocation_overhead
    if remaining_budget <= 0:
        raise RuntimeError("FAIL_CLOSED preregistered cumulative wall budget is exhausted")
    run_started = invocation_started
    result = run_exploratory(
        refined,
        project_id=project["project_id"],
        run_id=RUN_ID,
        artifact_root=root,
        rpm=RPM,
        max_cycles=MAX_CYCLES,
        budget_seconds=remaining_budget,
        memory_limit_mib=MEMORY_LIMIT_MIB,
        resume=resume,
        variant_label=f"{VARIANT} / {CELLS_PER_SECTION} cells per section",
    )
    output.update({
        "schema": "DINO_STAGE1_PERIODICITY_DIAGNOSTIC_RESULT_V1",
        "classification": result["classification"],
        "status": result["status"],
        "periodicity": result["periodicity"],
        "cycles_completed": result["cycles_completed"],
        "elapsed_seconds": result["elapsed_seconds"],
        "result_sha256": result["result_sha256"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "artifact_directory": result["artifact_directory"],
        "cycles": result["cycles"],
        "resume_requested": resume,
        "simulation_started": True,
        "scientific_validation": "NOT_CLAIMED",
        "spatial_independence": "NOT_ESTABLISHED_BY_THIS_SINGLE_MESH_POINT",
    })
    report.parent.mkdir(parents=True, exist_ok=True)
    call_wall_seconds = time.monotonic() - run_started
    output["call_wall_seconds"] = call_wall_seconds
    output["cumulative_wall_seconds"] = cumulative_prior + call_wall_seconds
    temp = report.with_name(f".{report.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, report)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
    output["report_path"] = str(report)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-authorized-diagnostic", action="store_true",
                        help="execute the one preregistered point; default is no-solver preflight")
    parser.add_argument("--preregistration-sha256")
    parser.add_argument("--resume", action="store_true",
                        help="resume only this point from a valid existing checkpoint")
    args = parser.parse_args()
    if args.resume and not args.execute_authorized_diagnostic:
        parser.error("--resume requires --execute-authorized-diagnostic")
    if args.execute_authorized_diagnostic and not args.preregistration_sha256:
        parser.error("execution requires --preregistration-sha256")
    try:
        result = run(execute=args.execute_authorized_diagnostic,
                     preregistration_sha256=args.preregistration_sha256,
                     resume=args.resume)
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
