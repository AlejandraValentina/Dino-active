"""Run the preregistered one-shot evidence recovery for KT100 V2."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.reference_harness.campaign import run_fixed_points
from motorsim.reference_harness.evidence import configuration_hash, source_binding, write_json_gzip
from scripts.build_kt100_open_end_plenum_v2 import build

PREREGISTRATION = ROOT / "results/2t-commercial-core-20261002/preregistration/KT100_V2_EVIDENCE_RECOVERY_R1.json"
OUTPUT = ROOT / "results/kt100-hybrid-model-fixture-v2-harness-20261002-r6-open-end-plenum-v2-recovery-r1"
RPMS = (5000, 7000, 9000, 11000, 13000)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _committed_receipt():
    relative = PREREGISTRATION.relative_to(ROOT).as_posix()
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative],
                      cwd=ROOT, check=False).returncode != 0:
        raise RuntimeError("recovery preregistration has uncommitted changes")
    commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=ROOT, text=True, encoding="utf-8").strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                   cwd=ROOT, check=True)
    committed = json.loads(subprocess.check_output(
        ["git", "show", f"{commit}:{relative}"], cwd=ROOT,
        text=True, encoding="utf-8"))
    current = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if committed != current:
        raise RuntimeError("working recovery preregistration differs from its frozen commit")
    return current


def validate_inputs():
    receipt = _committed_receipt()
    if receipt.get("schema") != "KT100_V2_EVIDENCE_RECOVERY_R1_PREREGISTRATION_V1":
        raise RuntimeError("recovery preregistration schema mismatch")
    if receipt.get("status") != "PREREGISTERED_BEFORE_RECOVERY_CAMPAIGN":
        raise RuntimeError("recovery is not preregistered")
    if receipt.get("campaign", {}).get("runs") != 1:
        raise RuntimeError("recovery campaign must be exactly one run")
    if receipt.get("campaign", {}).get("output") != OUTPUT.relative_to(ROOT).as_posix() + "/":
        raise RuntimeError("recovery output differs from its frozen destination")
    if receipt.get("campaign", {}).get("retry_allowed") is not False:
        raise RuntimeError("recovery retry policy must remain disabled")
    if receipt.get("runner_sha256") != _sha256_text(Path(__file__)):
        raise RuntimeError("recovery runner differs from its preregistered hash")
    if receipt.get("recovery_change", {}).get("configuration_sha256") != _sha256(
            ROOT / "configs/fixtures/kt100_open_end_plenum_v2.json"):
        raise RuntimeError("frozen V2 configuration bytes changed")

    recovery = receipt.get("recovery_change", {})
    expected_sources = recovery.get("source_binding_after_evidence_fix")
    if expected_sources != source_binding():
        raise RuntimeError("product source binding differs from the preregistered recovery")
    before_sources = recovery.get("source_binding_original_r6")
    changed_sources = sorted(key for key in expected_sources
                             if before_sources.get(key) != expected_sources[key])
    if changed_sources != ["motorsim/reference_harness/evidence.py"]:
        raise RuntimeError(f"unexpected product-source delta since R6: {changed_sources}")

    old_root = ROOT / "results/kt100-hybrid-model-fixture-v2-harness-20261002-r6-open-end-plenum-v2"
    original = receipt["original_campaign"]
    if original.get("authorized_runs") != 1 or original.get("actual_runs") != 1:
        raise RuntimeError("original campaign authorization/count differs")
    if set(original.get("points", {})) != {str(rpm) for rpm in RPMS}:
        raise RuntimeError("original campaign point set differs")
    expected_campaign_hash = receipt["original_campaign"]["campaign_summary_sha256"]
    if _sha256(old_root / "campaign-summary.json.gz") != expected_campaign_hash:
        raise RuntimeError("original R6 campaign summary changed")
    for rpm in RPMS:
        point = old_root / f"rpm-{rpm}"
        expected_point = receipt["original_campaign"]["points"][str(rpm)]
        actual_names = sorted(path.name for path in point.iterdir() if path.is_file())
        if actual_names != sorted(expected_point["files"]):
            raise RuntimeError(f"unexpected original R6 files at {rpm} RPM: {actual_names}")
        for filename, expected_hash in expected_point["files"].items():
            if _sha256(point / filename) != expected_hash:
                raise RuntimeError(f"original R6 artifact changed: {rpm}/{filename}")
        with gzip.open(point / "manifest.json.gz", "rt", encoding="utf-8") as stream:
            manifest = json.load(stream)
        if manifest["configuration_sha256"] != expected_point["configuration_sha256"]:
            raise RuntimeError(f"original config identity changed at {rpm} RPM")
        if manifest["source_sha256"] != before_sources:
            raise RuntimeError(f"original source binding changed at {rpm} RPM")
        if list(point.glob("cycle-*.json.gz")) or list(point.glob("*trajectory*")) or list(point.glob("*checkpoint*")):
            raise RuntimeError(f"R6 unexpectedly has recoverable primary data at {rpm} RPM")

    config = build()
    if receipt.get("frozen_campaign") != {
            "rpms": list(RPMS),
            "cfl": config["numerics"]["cfl"],
            "mesh_target_m": config["numerics"]["dx_target_m"],
            "max_cycles": config["numerics"]["max_cycles"],
            "precision": config["numerics"]["float_format"],
            "fastmath": False,
            "parallel": False,
            "convergence_contract": config["convergence_contract"],
            "boundary": "OPEN_END_PLENUM_V2",
            "provenance": "SYNTHETIC_ASSUMPTION",
            "p4_dependency": "CONDITIONAL_ON_P4",
    }:
        raise RuntimeError("frozen campaign controls differ")
    for rpm in RPMS:
        point = deepcopy(config)
        point["operating_point"]["rpm"] = rpm
        if configuration_hash(point) != recovery["configuration_sha256_by_rpm"][str(rpm)]:
            raise RuntimeError(f"campaign configuration hash changed at {rpm} RPM")
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite or rerun recovery output: {OUTPUT}")
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    config = validate_inputs()
    if args.validate_only:
        print("KT100_V2_EVIDENCE_RECOVERY_R1 preregistration/input gate PASS")
        return
    results = run_fixed_points(config, OUTPUT, rpms=RPMS)
    write_json_gzip(OUTPUT / "campaign-summary.json.gz", results)
    for result in results:
        print(result["rpm"], result["classification"],
              result["complete_cycles"], result["converged_cycle"])


if __name__ == "__main__":
    main()
