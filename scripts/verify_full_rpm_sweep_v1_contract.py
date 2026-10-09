"""Read-only identity audit for the preregistered FULL_RPM_SWEEP_V1 inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.full_rpm_sweep_v1 import rpm_points  # noqa: E402
from motorsim.integrated_2t import _solver_dependency_hashes  # noqa: E402
from motorsim.mechanical_loss_binding_v1 import canonical_sha256  # noqa: E402
from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT_V2, STREAK, THRESHOLDS,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit() -> dict:
    path = ROOT / "results/full-rpm-sweep-v1/preregistration.json"
    prereg = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "schema": prereg.get("schema") == "FULL_RPM_SWEEP_V1_PREREGISTRATION",
        "campaign_not_started": prereg.get("campaigns_started") == 0,
        "rpm_grid": rpm_points(prereg) == tuple(prereg["rpm_grid"]["points_rpm"]),
        "rpm_point_count": len(rpm_points(prereg)) == 15,
        "solver_hashes": prereg.get("solver_dependency_hashes") == _solver_dependency_hashes(),
        "periodicity_contract": (prereg.get("periodicity", {}).get("contract") == CONTRACT_V2 and
                                 prereg.get("periodicity", {}).get("streak") == STREAK and
                                 prereg.get("periodicity", {}).get("thresholds") == THRESHOLDS and
                                 prereg.get("periodicity", {}).get("thresholds_sha256") ==
                                 canonical_sha256(THRESHOLDS)),
    }
    variants = []
    for row in prereg.get("variants", []):
        fixture_path = (ROOT / row["source_fixture_path"]).resolve()
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = fixture.get("mechanical_loss_model")
        config = fixture.get("engine_configuration")
        local = {
            "fixture_file_hash": _sha(fixture_path.read_bytes()) == row.get("fixture_sha256"),
            "fixture_id": fixture.get("fixture_id") == row.get("fixture_id"),
            "engine_configuration_hash": (canonical_sha256(config) ==
                                           row.get("engine_configuration_sha256") ==
                                           row.get("declared_configuration_sha256")),
            "explicit_fixture_loss_model": isinstance(model, dict) and bool(model.get("terms")),
            "loss_model_hash": canonical_sha256(model) == row.get("mechanical_loss_model_sha256"),
            "loss_model_equals_preregistered": canonical_sha256(model) ==
                                                canonical_sha256(row.get("mechanical_loss_model")),
            "fuel_snapshot_sha": config["fuel_coupled_combustion"]["fuel_snapshot"].get("sha256") ==
                                 row.get("fuel", {}).get("sha256"),
            "mixture_ratio": (config["atmosphere_species"][0] /
                              config["atmosphere_species"][1] ==
                              row.get("mixture_input", {}).get(
                                  "air_to_fuel_pseudo_species_mass_ratio")),
            "model_source_provenance": all(
                term.get("provenance") not in (None, "UNKNOWN")
                for term in model["terms"]),
        }
        variants.append({"variant_id": row.get("variant_id"),
                         "checks": local, "all_pass": all(local.values())})
    checks["two_variants"] = len(variants) == 2
    result = {"schema": "FULL_RPM_SWEEP_V1_PREREGISTRATION_AUDIT",
              "campaigns_started": 0,
              "checks": checks,
              "variants": variants,
              "all_pass": all(checks.values()) and all(v["all_pass"] for v in variants)}
    return result


if __name__ == "__main__":
    result = audit()
    print(json.dumps({"all_pass": result["all_pass"],
                      "variants": len(result["variants"]),
                      "rpm_points": len(rpm_points(json.loads(
                          (ROOT / "results/full-rpm-sweep-v1/preregistration.json")
                          .read_text(encoding="utf-8"))))}, sort_keys=True))
    raise SystemExit(0 if result["all_pass"] else 1)
