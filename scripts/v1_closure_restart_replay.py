"""Exact C11 checkpoint/restart and offline-replay qualification for A'/B'.

This is a bounded one-cycle verification on the C12-sufficient mesh. It is not
either prime's 20-cycle acceptance campaign and makes no periodicity claim.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, audit_integrated_cycle_primary,
    make_integrated_cycle_primary, make_integrated_engineering_output,
)
from motorsim.mechanical import MechanicalLossModel  # noqa: E402
from scripts.produce_integrated_cycle_evidence import advance_to  # noqa: E402

R2_DIR = Path("results/2t-v1-closure-20261006/mesh-study-r2")
OUT_DIR = Path("results/2t-v1-closure-20261006/restart-replay-c11")
FIXTURES = ("FIXTURE_A_PRIME", "FIXTURE_B_PRIME")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_gzip_json(path: Path, value: object) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(canonical(value))


def read_gzip_json(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def committed_json(relative: str) -> dict:
    payload = subprocess.run(
        ["git", "show", f"HEAD:{relative}"], cwd=ROOT,
        capture_output=True, check=True).stdout
    return json.loads(payload.decode("utf-8-sig"))


def run_fixture(fixture_id: str, runner_sha: str) -> dict:
    c12 = committed_json((R2_DIR / "result.json").as_posix())
    prereg = committed_json((R2_DIR / "preregistration.json").as_posix())
    if c12.get("overall_status") != "PASS":
        raise ValueError("C11 requires the committed C12 mesh sufficiency PASS")
    if prereg.get("status") != "PREREGISTERED_NOT_RUN":
        raise ValueError("C11 C12 preregistration identity is invalid")
    entry = next(row for row in prereg["fixtures"][fixture_id]
                 if row["mesh_level"] == c12["decisions"][fixture_id][
                     "sufficient_mesh_level"])
    wrapper = committed_json(entry["fixture_config_path"])
    engine_config = wrapper["engine_configuration"]
    continuous = IntegratedEngine2T.from_configuration_dict(engine_config)
    split = IntegratedEngine2T.from_configuration_dict(engine_config)
    start = continuous.snapshot()
    if canonical(start) != canonical(split.snapshot()):
        raise ValueError(f"{fixture_id}: initial snapshots differ")

    continuous_rejections: list[dict] = []
    advance_to(continuous, 360.0, continuous_rejections)
    continuous_end = continuous.snapshot()
    continuous_primary = make_integrated_cycle_primary(
        continuous, start, continuous_end, 1,
        rejected_trials=continuous_rejections, runner_sha256=runner_sha)

    split_rejections: list[dict] = []
    advance_to(split, 180.0, split_rejections)
    midpoint = split.snapshot()
    restarted = IntegratedEngine2T.from_configuration_dict(engine_config)
    restarted.restore(midpoint)
    restored_midpoint = restarted.snapshot()
    if canonical(midpoint) != canonical(restored_midpoint):
        raise ValueError(f"{fixture_id}: checkpoint restore changed midpoint state")
    advance_to(restarted, 360.0, split_rejections)
    restarted_end = restarted.snapshot()
    restarted_primary = make_integrated_cycle_primary(
        restarted, start, restarted_end, 1,
        rejected_trials=split_rejections, runner_sha256=runner_sha)

    if canonical(continuous_end) != canonical(restarted_end):
        raise ValueError(f"{fixture_id}: continuous/restart terminal snapshots differ")
    if canonical(continuous_primary) != canonical(restarted_primary):
        raise ValueError(f"{fixture_id}: continuous/restart full primaries differ")
    continuous_audit = audit_integrated_cycle_primary(continuous_primary)
    restarted_audit = audit_integrated_cycle_primary(restarted_primary)
    if continuous_audit.get("recomputed") is not True or restarted_audit.get(
            "recomputed") is not True:
        raise ValueError(f"{fixture_id}: offline replay did not recompute the cycle")

    loss_model = MechanicalLossModel.from_dict(wrapper["mechanical_loss_model"])
    continuous_output = make_integrated_engineering_output(
        continuous_primary, mechanical_loss_model=loss_model)
    restarted_output = make_integrated_engineering_output(
        restarted_primary, mechanical_loss_model=loss_model)
    if canonical(continuous_output) != canonical(restarted_output):
        raise ValueError(f"{fixture_id}: continuous/restart engineering outputs differ")

    c12_primary = read_gzip_json(
        ROOT / R2_DIR / fixture_id.lower() / f"mesh-{entry['mesh_level']}-cycle-1.json.gz")
    replay_bound_fields = (
        "configuration_hash", "configuration_identity", "cycle_start_deg",
        "cycle_end_deg", "start_state", "terminal_state", "trajectory",
        "cycle_ledgers", "conservation", "observables", "port_closure_snapshots",
    )
    c12_equivalent = all(
        canonical(continuous_primary[key]) == canonical(c12_primary[key])
        for key in replay_bound_fields)
    if not c12_equivalent:
        raise ValueError(f"{fixture_id}: C11 continuous run differs from C12 mesh primary")

    return {
        "fixture_id": fixture_id,
        "mesh_level": entry["mesh_level"],
        "engine_configuration_sha256": entry["engine_configuration_sha256"],
        "c12_primary_equivalent_fields": list(replay_bound_fields),
        "c12_primary_equivalent": c12_equivalent,
        "midpoint_checkpoint_angle_deg": 180.0,
        "midpoint_checkpoint_sha256": sha(canonical(midpoint)),
        "terminal_snapshot_equal": True,
        "full_cycle_primary_equal": True,
        "accepted_steps": len(continuous_primary["trajectory"]),
        "rejected_trials": len(continuous_primary["rejected_trials"]),
        "ledger_equal": canonical(continuous_primary["cycle_ledgers"]) ==
                        canonical(restarted_primary["cycle_ledgers"]),
        "species_equal": canonical(continuous_end["state"]["species"]) ==
                         canonical(restarted_end["state"]["species"]),
        "outputs_equal": True,
        "continuous_offline_audit": continuous_audit,
        "restart_offline_audit": restarted_audit,
        "primary": continuous_primary,
        "checkpoint": midpoint,
    }


def run() -> dict:
    if (ROOT / OUT_DIR).exists():
        raise ValueError("C11 evidence directory already exists; preserving prior evidence")
    runner_sha = sha(Path(__file__).read_bytes())
    results = {fixture_id: run_fixture(fixture_id, runner_sha)
               for fixture_id in FIXTURES}
    out = ROOT / OUT_DIR
    out.mkdir(parents=True)
    evidence = {}
    for fixture_id, result in results.items():
        fixture_dir = out / fixture_id.lower()
        fixture_dir.mkdir()
        primary = result.pop("primary")
        checkpoint = result.pop("checkpoint")
        write_gzip_json(fixture_dir / "continuous-cycle-1.json.gz", primary)
        write_gzip_json(fixture_dir / "checkpoint-180deg.json.gz", checkpoint)
        evidence[fixture_id] = result
    report = {
        "schema": "MOTORSIM_2T_V1_C11_RESTART_REPLAY_RESULT_V1",
        "status": "PASS",
        "dependency": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4",
        "c12_result_sha256": sha(canonical(committed_json((R2_DIR / "result.json").as_posix()))),
        "runner_sha256": runner_sha,
        "fixtures": evidence,
    }
    (out / "result.json").write_bytes(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"],
                      "fixtures": {key: {
                          "accepted_steps": value["accepted_steps"],
                          "rejected_trials": value["rejected_trials"],
                          "c12_primary_equivalent": value["c12_primary_equivalent"],
                      } for key, value in result["fixtures"].items()}}, sort_keys=True))
