import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "results/engine-physics-v1/r2-offline"


def test_r2_offline_manifest_is_review_and_four_point():
    manifest = json.loads((ARTIFACT / "manifest.json").read_text())
    assert manifest["status"] == "REVIEW"
    assert manifest["gate"]["all_periodic"] is True
    assert manifest["gate"]["all_hard_gates_pass"] is True
    assert manifest["gate"]["external_review_task"] == "EP-R2-EXTERNAL-REVIEW"
    assert [point["cycle"] for point in manifest["points"]] == [73, 88, 34, 38]


def test_r2_outputs_have_contractual_status_units_definition_and_source():
    manifest = json.loads((ARTIFACT / "manifest.json").read_text())
    required = {
        "trapped_air", "trapped_fuel", "delivered_air", "delivered_fuel",
        "AFR", "lambda", "phi", "fuel_burned", "fuel_unburned",
        "chemical_heat", "exhaust_temperature", "DR", "TE", "SE", "CE",
        "residual_purity", "burned_purity", "cylinder_indicated_work", "IMEP",
        "crankcase_gas_work", "net_piston_gas_work", "FMEP", "BMEP",
        "indicated_power", "indicated_torque", "brake_power", "brake_torque",
        "ISFC", "BSFC",
    }
    for point in manifest["points"]:
        assert required == set(point["outputs"])
        for item in point["outputs"].values():
            assert item["status"] in {"DEFINED", "UNDEFINED"}
            assert item["units"]
            assert item["definition_version"]
            assert item["source"]
            if item["status"] == "UNDEFINED":
                assert item["value"] is None
                assert item["reason"]
        assert point["outputs"]["TE"]["status"] == "UNDEFINED"


def test_r2_partition_residuals_and_hard_gates():
    manifest = json.loads((ARTIFACT / "manifest.json").read_text())
    for point in manifest["points"]:
        assert point["hard_physical_gate"]["classification"] == "PASS"
        assert point["scavenging_partition"]["gross_partition"]["status"] == "NOT_APPLICABLE"
        assert point["scavenging_partition"]["species_closure"]["passed"] is True
        assert point["scavenging_partition"]["species_closure"]["max_abs_residual_kg"] <= 1e-12
