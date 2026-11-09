"""C02/C04 integrity contracts: no-op editor identity, safe state context and terminal acceptance order."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication

from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_project import create_project, project_from_example
from motorsim.desktop.four_stroke_desktop import FourStrokeConfigEditor, FourStrokeResults
from motorsim.desktop.four_stroke_artifacts import RunAssessment
from motorsim.dino4t import api, runner
from c01_c03_fixtures import endpoint_factory

APP = QApplication.instance() or QApplication([])
ROOT = Path(__file__).resolve().parents[1]


def test_noop_editor_apply_preserves_exact_source_identity():
    project = project_from_example("c02-noop")
    context = DesktopContext(project)
    config = deepcopy(context.engine())
    config["geometry"]["rod_mm"] = 180.12345678912345
    context.replace_engine(config)
    editor = FourStrokeConfigEditor(context)
    editor.apply()
    assert context.engine()["geometry"]["rod_mm"] == 180.12345678912345
    table = editor.tables["geometry"]
    row = next(i for i in range(table.rowCount()) if table.item(i, 0).text().endswith("diámetro (mm)"))
    table.item(row, 1).setText("87.5")
    editor.apply()
    assert context.engine()["geometry"]["bore_mm"] == 87.5
    assert context.engine()["geometry"]["rod_mm"] == 180.12345678912345
    editor.close(); APP.processEvents()


def test_raw_or_midcycle_state_is_rejected_without_solver():
    state = {"ducts": {}, "cyl": object(), "plen": {}}
    with pytest.raises(ValueError, match="initial_state must"):
        runner.validate_initial_state(state)
    mid = {"schema": runner.STATE_CONTEXT_SCHEMA, "state": state,
           "complete_cycle": False, "model_id": runner.MODEL_ID}
    with pytest.raises(ValueError, match="mid-cycle"):
        runner.validate_initial_state(mid)
    good = {**mid, "complete_cycle": True, "theta_deg": 0.0, "phase_deg": 0.0,
            "cycles_completed": 1, "config_sha256": "a" * 64,
            "topology_sha256": "b" * 64}
    assert runner.validate_initial_state(good) is state
    config = json.loads((ROOT / "configs/dino4t/example_single_cylinder_500cc.json").read_text(encoding="utf-8"))
    envelope = api.run(config, initial_state=state, max_cycles=1)
    assert envelope["error"]["code"] == "OPTION_INVALID"
    assert envelope["summary"] is None


def test_verified_pressure_uses_crank_angle_and_refresh_clears_stale(tmp_path, monkeypatch):
    endpoint = endpoint_factory(tmp_path / "fixtures")("A")
    project = create_project("c02-results", endpoint["config"],
                             run_references=[endpoint["reference"]])
    results = FourStrokeResults(DesktopContext(project))
    results.select_run(0)
    assert results.pressure_plot.series
    assert results.pressure_plot.series[0]["x_label"] == "Ángulo de cigüeñal (°)"
    monkeypatch.setattr("motorsim.desktop.four_stroke_artifacts.assess_run_reference",
                        lambda reference: RunAssessment("UNAVAILABLE"))
    results.refresh()
    assert results.summary.rowCount() == 0
    assert results.trace_table.rowCount() == 0
    assert results.pressure_plot.series == []
