"""Offline contract checks for the preregistered AUD-15 Fixture D run."""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from motorsim.artifact_store import resolve_external_artifact


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/2t-commercial-core-20261002/aud-15-fixture-d-20261005-v1"


def _json_gz(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def test_fixture_d_preregistered_two_cycle_run_and_p7_geometry():
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["fixture_id"] == "D"
    assert manifest["horizon_cycles"] == manifest["output_cycle_count"] == 2
    assert manifest["restart_cycle"] == 1
    assert manifest["preregistration_commit"] == (
        "57dfa97032037a96ab3869cf46b7180f35bb77a0"
    )
    assert manifest["producer_commit"] == (
        "01172a2d7b2f7f97db9a7a46e12cf328962aef52"
    )

    replay = json.loads((RUN / "restart-audit.json").read_text(encoding="utf-8"))
    assert replay["status"] == "EXACT_REPLAY_PASS"
    assert replay["snapshot_equal"] is True
    assert replay["restart_cycle"] == 1
    assert replay["compared_terminal_cycle"] == 2

    artifact_manifest = ROOT / "artifacts/test-fixtures.json"
    cycles = [
        _json_gz(resolve_external_artifact(
            f"AUD15_FIXTURE_D_CYCLE_{index:03}", manifest_path=artifact_manifest
        ))
        for index in (1, 2)
    ]
    assert [(cycle["cycle_start_deg"], cycle["cycle_end_deg"]) for cycle in cycles] == [
        (0.0, 360.0), (360.0, 720.0)
    ]
    assert all(cycle["admissible"] is True for cycle in cycles)
    event_rows = [
        row
        for cycle in cycles
        for row in cycle["trajectory"]
        if row["angle_start_deg"] >= 350.0 - 1e-12
        and row["angle_end_deg"] <= 390.0 + 1e-12
    ]
    assert len(event_rows) == 160
    assert event_rows[0]["angle_start_deg"] == 350.0
    assert event_rows[-1]["angle_end_deg"] == 390.0
    assert all(
        abs(left["angle_end_deg"] - right["angle_start_deg"]) <= 1e-12
        for left, right in zip(event_rows, event_rows[1:])
    )
    stage_geometry = [geometry for row in event_rows for geometry in row["stage_geometry"]]
    assert len(stage_geometry) == 320
    assert all(geometry["exhaust_area_m2"] == 0.0 for geometry in stage_geometry)
    assert any(cycle["cycle_ledgers"]["p7_heat_added_J"] > 0.0 for cycle in cycles)
    assert all(cycle["contract"] == "REFERENCE_PERIODIC_CONVERGENCE_V1" for cycle in cycles)
