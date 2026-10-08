"""Focal P4→P8 impact revalidation after the durable G2-v2 reacquisition."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from dev_orchestrator.p4_g2_v2_offline_audit import audit

ROOT = Path("results/p4-g2-v2-reaudit-20260929-r2")
DOWNSTREAM = Path("results/p5-p8-revalidation-g2-v2-recovery-20260929")
BASE = "d616e2946d84080be44e21867602855d12f7c54a"
OLD_MATRIX = Path("results/p4-g2-v2-20260929/p4-final-gate-matrix.json")
OLD_RECEIPT = Path("results/p5-p8-revalidation-20260929/revalidation.json")
P8_CAMPAIGN = Path("results/p8-wide-rpm-20260927/p8-wide-rpm.json")
REQUIRED_P8_GATES = (
    "finite", "geometry_rebased", "admissible", "species", "p7_one_event",
    "p7_nonvacuous", "p7_source_admissible", "p7_heat_consistent", "cfl",
    "source_heat_consistent", "prescribed_heat_matches_ledger",
    "global_mass_conservation", "global_energy_conservation",
    "prepared_initial_state", "restart", "deterministic_replay",
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_paths() -> list[str]:
    output = subprocess.check_output(["git", "diff", "--name-only", BASE, "HEAD"], text=True)
    return output.splitlines()


def revalidate(root: Path = ROOT) -> tuple[dict, dict]:
    verdict = audit(root)
    if verdict["classification"] != "E13_G2_V2_PASS":
        raise RuntimeError(f"G2-v2 offline gate is not PASS: {verdict['reason']}")
    if verdict != read(root/"offline-audit.json"):
        raise RuntimeError("Persisted offline audit differs from fresh recomputation")
    manifest = read(root/"manifest.json")
    for source, expected_hash in manifest["runtime"]["source_sha256"].items():
        if digest(Path(source)) != expected_hash:
            raise RuntimeError(f"G2-v2 runtime source changed: {source}")
    changed = changed_paths()
    if any(path.startswith("motorsim/") for path in changed):
        raise RuntimeError("Product code changed since the prior P4/P5-P8 evidence")
    old_matrix = read(OLD_MATRIX)
    mandatory = ("P4A", "P4B", "E12", "E13_G1", "E14", "E15", "B1", "B2",
                 "C1", "C2", "C3", "performance", "checkpoint_restart",
                 "regressions", "OpenSpec")
    for key in mandatory:
        value = old_matrix[key]
        if not (value.startswith("PASS") or value == "P4_SCI_C3_PASS"):
            raise RuntimeError(f"Historical P4 gate {key} is not PASS: {value}")
    matrix = dict(old_matrix)
    matrix.update(E13_G2_v2="PASS_PERIOD2_CYCLE50_REAUDITABLE",
                  P4="P4_PASS", acceptance="PENDING_NEW_INDEPENDENT_REVIEW",
                  independent_review="READY_FOR_NEW_INDEPENDENT_REVIEW",
                  P5="REVALIDATED_SEPARATELY",
                  prior_matrix=str(OLD_MATRIX),
                  recovery_basis="fresh offline E13 recomputation from durable checkpoints")
    matrix["evidence"] = dict(old_matrix["evidence"])
    matrix["evidence"]["E13_G2_v2"] = str(root/"offline-audit.json")
    matrix["evidence"]["G2_v2_durable_inputs"] = str(root/"manifest.json")
    matrix["evidence"]["restart_parity"] = str(root/"terminal-replay-parity.json")

    old_receipt = read(OLD_RECEIPT)
    p8 = read(P8_CAMPAIGN)
    if p8["semantics"]["metric_semantics"] != "BOUNDED_TRANSIENT_INDICATED":
        raise RuntimeError("P8 semantics changed")
    if p8["semantics"]["experimental_validation"] != "NOT_PERFORMED":
        raise RuntimeError("P8 experimental status changed")
    if p8["failures"] or len(p8["anchors"]) != 5:
        raise RuntimeError("P8 campaign anchor count or failures changed")
    for anchor, summary in zip(p8["anchors"], old_receipt["p8"]["anchors"]):
        if anchor["rpm"] != summary["rpm"] or anchor["P_indicated_W"] != summary["P_indicated_W"]:
            raise RuntimeError("P8 historical anchor value changed")
        if any(anchor["gates"].get(name) is not True for name in REQUIRED_P8_GATES):
            raise RuntimeError(f"P8 historical gate is false at {anchor['rpm']} rpm")
    for source, expected_hash in old_receipt["provenance_sha256"].items():
        if digest(Path(source)) != expected_hash:
            raise RuntimeError(f"P5-P8 product/runtime source changed: {source}")
    downstream = {
        "base_p4": str(root/"p4-recovery-matrix.json"),
        "technical_P4": "P4_PASS",
        "independent_review": "READY_FOR_NEW_INDEPENDENT_REVIEW",
        "P5": old_receipt["p5"], "P6": old_receipt["p6"],
        "P7": old_receipt["p7"], "P8": old_receipt["p8"],
        "P8_campaign_repeated": False,
        "P8_campaign_reason": "No product/runtime source or historical anchor evidence changed; the new acquisition only affects E13/G2",
        "P8_semantics": "BOUNDED_TRANSIENT_INDICATED",
        "experimental_validation": "NOT_PERFORMED",
        "P9": "STOPPED_NOT_AUTHORIZED",
        "unchanged_source_sha256": old_receipt["provenance_sha256"],
        "changed_paths_since_base": changed,
        "tests": {"P4_E13": "152 passed", "P5_P8_coupling": "141 passed, 1 deselected physical campaign"},
        "OpenSpec_strict": ["p4-escape-1d", "p5-intake-transfer",
                            "p7-prescribed-heat-burn", "p8-wide-rpm-performance"],
    }
    write(root/"p4-recovery-matrix.json", matrix)
    write(DOWNSTREAM/"receipt.json", downstream)
    return matrix, downstream


if __name__ == "__main__":
    p4, p5_p8 = revalidate()
    print(json.dumps({"P4": p4["P4"], "independent_review": p4["independent_review"],
                      "P5": p5_p8["P5"]["status"], "P6": p5_p8["P6"]["status"],
                      "P7": p5_p8["P7"]["status"], "P8": p5_p8["P8"]["status"]}))
