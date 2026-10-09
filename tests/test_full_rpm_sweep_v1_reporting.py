from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.summarize_full_rpm_sweep_v1 import summarize_campaign


def test_partial_campaign_exports_valid_csv_json_and_plots_without_zero_fills(tmp_path):
    root = tmp_path / "campaign"
    valid_dir = root / "A_PRIME_MESH_0" / "rpm-04000"
    invalid_dir = root / "B_PRIME_MESH_0" / "rpm-04000"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    outputs = {
        "BMEP": {"status": "DEFINED", "value": 420000.0},
        "brake_power": {"status": "DEFINED", "value": 10000.0},
        "indicated_power": {"status": "DEFINED", "value": 12000.0},
        "brake_torque": {"status": "DEFINED", "value": 23.87},
        "indicated_torque": {"status": "DEFINED", "value": 28.65},
        "IMEP": {"status": "DEFINED", "value": 600000.0},
        "FMEP": {"status": "DEFINED", "value": 180000.0},
        "ISFC": {"status": "DEFINED", "value": 300.0},
        "BSFC": {"status": "DEFINED", "value": 360.0},
        "AFR": {"status": "DEFINED", "value": 49.0},
        "lambda": {"status": "DEFINED", "value": 3.33},
        "phi": {"status": "DEFINED", "value": 0.3},
    }
    valid_result = {
        "classification": "PERIOD_1", "cycles_completed": 9, "converged_cycle": 9,
        "bindings": {"point_configuration_sha256": "a" * 64},
        "engineering_outputs": {"outputs": outputs},
        "hard_gates": {"primary_admissible": True, "primary_replay_audit": True,
                       "scavenging_partition": {"classification": "PASS"},
                       "conservation": {"passed": True}},
        "performance_metrics": {"mean_cycle_seconds": 1.0},
        "scavenging": {"metrics": {"ratios": {
            "delivery_ratio": {"value": 0.2, "status": "AVAILABLE"},
            "trapping_efficiency": {"value": None, "status": "UNDEFINED",
                                    "reason": "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"},
            "charging_efficiency": {"value": None, "status": "UNDEFINED",
                                    "reason": "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"},
            "scavenging_efficiency": {"value": None, "status": "UNDEFINED",
                                      "reason": "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"},
        }}}
    }
    (valid_dir / "result.json").write_text(json.dumps(valid_result), encoding="utf-8")
    (invalid_dir / "result.json").write_text(json.dumps({
        "classification": "NO_CONVERGENCE_WITHIN_HORIZON",
        "cycles_completed": 111, "engineering_outputs": None,
    }), encoding="utf-8")
    points = []
    for variant in ("A_PRIME_MESH_0", "B_PRIME_MESH_0"):
        for rpm in (1000, 4000):
            directory = root / variant / f"rpm-{rpm:05d}"
            result_path = (str((directory / "result.json").relative_to(root))
                           if (directory / "result.json").is_file() else None)
            points.append({"variant_id": variant, "rpm": rpm,
                           "classification": "NOT_STARTED", "result_path": result_path})
    (root / "campaign.json").write_text(json.dumps({
        "campaign_id": "test", "campaign_status": "PARTIAL_IN_PROGRESS",
        "campaigns_started": 1, "completed_or_checkpointed_points": points,
    }), encoding="utf-8")
    report = summarize_campaign(root)
    assert report["curves_are_partial"] is True
    assert report["classification_counts"]["PERIOD_1"] == 1
    assert report["classification_counts"]["NO_CONVERGENCE_WITHIN_HORIZON"] == 1
    with (root / report["csv"]).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    invalid = next(row for row in rows if row["classification"] == "NO_CONVERGENCE_WITHIN_HORIZON")
    assert invalid["brake_power"] == ""
    assert invalid["BSFC"] == ""
    assert invalid["BSFC_status"] == "NOT_VALID_FOR_NONCONVERGED_POINT"
    assert len(report["plots"]) == 4
    assert all((root / plot).is_file() for plot in report["plots"])
