"""Read-only integrity verification for a FAST_RECIPE_V1 diagnostic receipt."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motorsim.fast_recipe_v1 import canonical_bytes, read_recipe, sha256  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", nargs="?", type=Path,
                        default=ROOT / "results/full-rpm-sweep-v1/fast-recipe-v1-benchmark-receipt.json")
    args = parser.parse_args()
    receipt_path = args.receipt.resolve()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    root = Path(receipt["artifact_root"])
    errors: list[str] = []
    runner_sha = hashlib.sha256((ROOT / "scripts/benchmark_full_rpm_sweep_v1_fast_recipe.py").read_bytes()).hexdigest()
    module_sha = hashlib.sha256((ROOT / "motorsim/fast_recipe_v1.py").read_bytes()).hexdigest()
    if runner_sha != receipt.get("runner_sha256"):
        errors.append("current benchmark runner hash differs from receipt")
    if module_sha != receipt.get("fast_recipe_module_sha256"):
        errors.append("current FAST module hash differs from receipt")
    identity_path = ROOT / "results/full-rpm-sweep-v1/fast-recipe-v1-identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if identity.get("runner_sha256") != runner_sha or identity.get("module_sha256") != module_sha:
        errors.append("implementation identity hash mismatch")
    checked = 0
    for scale in receipt.get("scales", []):
        workers = scale["requested_workers"]
        for job in scale.get("results", []):
            checked += 1
            out = root / f"workers-{workers}" / job["task_id"]
            job_receipt = json.loads((out / "job-receipt.json").read_text(encoding="utf-8"))
            for key in ("task_id", "configuration_sha256", "scenario", "recipe_sha256",
                        "checkpoint_sha256"):
                if job_receipt.get(key) != job.get(key):
                    errors.append(f"{job['task_id']}: worker receipt mismatch: {key}")
            if job["scenario"] == "B_FAST_PROVISIONAL":
                if job["audit_recomputed"] or job["primary_sha256"] is not None:
                    errors.append(f"{job['task_id']}: provisional scenario emitted audited evidence")
            if job["recipe_sha256"]:
                recipe_name = "cycle-recipe-audited.json" if job["scenario"] == "C_FAST_AUDITED" else "cycle-recipe.json"
                recipe_path = out / recipe_name
                payload = recipe_path.read_bytes()
                if sha256(payload) != job["recipe_file_sha256"]:
                    errors.append(f"{job['task_id']}: recipe file hash mismatch")
                recipe = read_recipe(recipe_path, expected_file_sha256=job["recipe_file_sha256"])
                if recipe.get("recipe_sha256") != job["recipe_sha256"]:
                    errors.append(f"{job['task_id']}: recipe canonical hash mismatch")
                if recipe.get("next_cycle_checkpoint_sha256") != job["checkpoint_sha256"]:
                    errors.append(f"{job['task_id']}: checkpoint hash mismatch")
            if job["primary_sha256"]:
                primary_path = out / "primary.json.gz"
                primary = json.loads(gzip.decompress(primary_path.read_bytes()))
                if sha256(canonical_bytes(primary)) != job["primary_sha256"]:
                    errors.append(f"{job['task_id']}: primary canonical hash mismatch")
                if job["audit_status"] != "PASS" or job["audit_recomputed"] is not True:
                    errors.append(f"{job['task_id']}: audited scenario lacks recomputed PASS")
            if sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) != job["artifact_bytes"]:
                errors.append(f"{job['task_id']}: artifact byte count mismatch")
    if receipt.get("campaign_started") is not False or receipt.get("rpm_campaign_points_started") != 0:
        errors.append("receipt indicates campaign activity")
    result = {"status": "PASS" if not errors else "FAIL",
              "receipt": str(receipt_path), "artifact_root": str(root),
              "jobs_checked": checked, "errors": errors,
              "campaign_points_started": receipt.get("rpm_campaign_points_started")}
    print(json.dumps(result, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
